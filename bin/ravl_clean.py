#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL-CLEAN - Clean learning files for a RAVL loop

Remove all learning files for a specified RAVL loop, optionally including
all child loop learning files. Useful for restarting iterative learning,
testing, or cleaning up after experimentation.

Usage:
    ravl-clean <loop-name> [options]

Options:
    --include-children  Also delete learning files from child loops
    --dry-run          Show what would be deleted without making changes
    --force            Don't prompt for confirmation (use with caution!)
    --loop-dir PATH    Override loop directory path (highest priority: CLI > .env > default)
    --help            Show this help message

Examples:
    # Cleana single loop with confirmation
    ravl-clean team_alpha_raci_data_in

    # Cleanloop and all children
    ravl-clean strategy_guardian --include-children

    # Preview what would be deleted
    ravl-clean team_alpha_raci_data_in --dry-run

    # Cleanwithout confirmation (be careful!)
    ravl-clean team_alpha_raci_data_in --force

    # Cleanfrom custom loop directory
    ravl-clean my_loop --loop-dir /custom/path
"""

import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

# Bootstrap: Find .ravl framework
_current = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_current / 'common'))
sys.path.insert(0, str(_current / 'common' / 'cli'))

from ravl_cli_base import RAVLCLIBase
from loop_discovery import LoopDiscovery
from ravl_runner import RAVLRunner


class RAVLResetCommand(RAVLCLIBase):
    """Reset learning files for RAVL loops"""

    def __init__(self, loops_dir: Optional[Path] = None):
        """Initialize reset command

        Args:
            loops_dir: Optional custom path for project loops
        """
        # Find project root (uses CWD as fallback if outside RAVL project)
        self.project_root = self.find_project_root(required=False)
        self.discovery = LoopDiscovery(self.project_root, loops_dir=loops_dir)
        self.stats = {
            'files_deleted': 0,
            'dirs_deleted': 0,
            'paths': []
        }

    def run(self, args: argparse.Namespace):
        """
        Execute reset command

        Args:
            args: Parsed command-line arguments
        """
        try:
            # 1. Find the loop
            self.print_info(f"Finding loop: {args.loop_name}")
            loop_path = self.discovery.find_loop(args.loop_name)
            self.print_success(f"Found loop at: {loop_path}")

            # 2. Collect learning paths to delete
            self.print_info("Scanning for learning directories...")
            paths_to_delete = self._collect_paths_to_delete(
                loop_path,
                include_children=args.include_children
            )

            if not paths_to_delete:
                self.print_warning("No learning files found to delete")
                return

            # 3. Show preview
            self._show_deletion_preview(paths_to_delete, args.dry_run)

            # 4. Get confirmation (unless --force or --dry-run)
            if not args.dry_run and not args.force and not self._confirm_deletion():
                self.print_info("Reset cancelled by user")
                return

            # 5. Perform deletion (unless --dry-run)
            if args.dry_run:
                self.print_header("DRY RUN MODE - No changes made", "⏭️")
                self._report_results(args.dry_run)
            else:
                self.print_header("Deleting learning files...", "🗑️")
                self._delete_paths(paths_to_delete)
                self._report_results(args.dry_run)

        except FileNotFoundError as e:
            self.print_error(f"Loop not found: {args.loop_name}")
            sys.exit(1)
        except Exception as e:
            self.print_error(f"Error during reset: {e}")
            sys.exit(1)

    def _collect_paths_to_delete(
        self,
        loop_path: Path,
        include_children: bool = False
    ) -> List[Path]:
        """
        Collect all learning paths to delete

        Args:
            loop_path: Path to the loop directory
            include_children: Whether to include child loop learnings

        Returns:
            List of paths to delete
        """
        paths = []

        # Load loop config to check for custom learning_path
        try:
            config = self.discovery.load_config(loop_path)
        except:
            config = {}

        # Resolve the learning path using the same logic as the runner
        learnings_path = RAVLRunner.resolve_learning_path(
            loop_dir=loop_path,
            loop_config=config,
            project_root=self.project_root
        )

        if learnings_path.exists():
            paths.append(learnings_path)

        # Add child loops if requested
        if include_children:
            child_learnings = self._find_child_loop_learnings(loop_path)
            paths.extend(child_learnings)

        return paths

    def _find_child_loop_learnings(self, loop_path: Path) -> List[Path]:
        """
        Recursively find learning directories in child loops

        Args:
            loop_path: Path to search for child loops

        Returns:
            List of learning directory paths from child loops
        """
        child_learnings = []

        # Look for ravl_loops subdirectory
        ravl_loops_dir = loop_path / 'ravl_loops'
        if not ravl_loops_dir.exists():
            return child_learnings

        # Recursively search for child loops
        for child_dir in ravl_loops_dir.iterdir():
            if not child_dir.is_dir() or child_dir.name.startswith('.'):
                continue

            try:
                # Load child loop config and resolve its learning path
                child_config = self.discovery.load_config(child_dir)
                child_learning_path = RAVLRunner.resolve_learning_path(
                    loop_dir=child_dir,
                    loop_config=child_config,
                    project_root=self.project_root
                )

                if child_learning_path.exists():
                    child_learnings.append(child_learning_path)
            except Exception:
                # If we can't resolve, skip this child
                pass

            # Recursively check for grandchildren
            child_learnings.extend(self._find_child_loop_learnings(child_dir))

        return child_learnings

    def _show_deletion_preview(self, paths: List[Path], is_dry_run: bool):
        """
        Show what will be deleted

        Args:
            paths: List of paths to delete
            is_dry_run: Whether this is a dry-run
        """
        if is_dry_run:
            self.print_header("DRY RUN - Preview of what would be deleted", "👀")
        else:
            self.print_header("Preview - These directories will be deleted:", "👀")

        total_files = 0
        total_dirs = 0

        print("\n📋 Paths to delete:", file=sys.stderr)
        for path in paths:
            print(f"   • {path}", file=sys.stderr)

            # Count files and dirs
            if path.exists():
                for item in path.rglob('*'):
                    if item.is_file():
                        total_files += 1
                    elif item.is_dir():
                        total_dirs += 1

        print(f"\n   📊 Total: {total_files} files, {total_dirs} directories", file=sys.stderr)
        print()

        self.stats['files_deleted'] = total_files
        self.stats['dirs_deleted'] = total_dirs
        self.stats['paths'] = paths

    def _confirm_deletion(self) -> bool:
        """
        Prompt user for confirmation

        Returns:
            True if user confirms, False otherwise
        """
        response = input("⚠️  Confirm deletion? This cannot be undone. [y/N]: ").strip().lower()
        return response in ['y', 'yes']

    def _delete_paths(self, paths: List[Path]):
        """
        Delete the specified paths

        Args:
            paths: List of paths to delete
        """
        for path in paths:
            if not path.exists():
                self.print_warning(f"Path does not exist, skipping: {path}")
                continue

            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    self.print_success(f"Deleted: {path}")
                else:
                    path.unlink()
                    self.print_success(f"Deleted: {path}")
            except Exception as e:
                self.print_error(f"Failed to delete {path}: {e}")

    def _report_results(self, is_dry_run: bool):
        """
        Report deletion results

        Args:
            is_dry_run: Whether this was a dry-run
        """
        mode_str = "would delete" if is_dry_run else "deleted"
        print()
        self.print_header(f"✨ Reset complete!", "✨")
        print(
            f"   {mode_str.capitalize()} {self.stats['files_deleted']} files "
            f"and {self.stats['dirs_deleted']} directories",
            file=sys.stderr
        )

        if is_dry_run:
            self.print_info("Use without --dry-run to actually delete")
        else:
            self.print_info("Learning history reset. Loop ready for fresh iteration!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Reset learning files for a RAVL loop',
        add_help=False  # We'll handle help manually for custom formatting
    )

    parser.add_argument(
        'loop_name',
        nargs='?',
        help='Name or path of the RAVL loop to reset'
    )

    parser.add_argument(
        '--include-children',
        action='store_true',
        help='Also delete learning files from all child loops'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without making changes'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help="Don't prompt for confirmation"
    )

    parser.add_argument(
        '--help',
        '-h',
        action='store_true',
        help='Show this help message'
    )
    parser.add_argument(
        '--loop-dir',
        type=str,
        default=None,
        help='Override loop directory path (highest priority: CLI > .env > default)'
    )

    args = parser.parse_args()

    # Handle help
    if args.help or not args.loop_name:
        print(__doc__)
        sys.exit(0 if args.help else 1)

    # Resolve loop directory if provided
    resolved_loops_dir = None
    if args.loop_dir:
        resolved_loops_dir = Path(args.loop_dir).expanduser().resolve()

    # Run the command
    command = RAVLResetCommand(loops_dir=resolved_loops_dir)
    command.run(args)


if __name__ == '__main__':
    main()
