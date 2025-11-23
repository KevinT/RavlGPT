#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL-CLONE - Clone a RAVL loop from templates, examples, or existing loops

Clone RAVL loops from available sources: templates, examples, or existing loops in your project.
If multiple matches exist, you'll be prompted to select which one to clone.

Supports nested destination paths with automatic child_loops/ separator insertion.

Usage:
    ravl-clone <loop-name> [options]
    ravl-clone <loop-name> <new-name> [options]
    ravl-clone <loop-name> <parent.child.new-name> [options]

Arguments:
    loop-name           Name or path of the loop to clone (e.g., strategic_coherence or strategic_coherence.content_coherence)
    new-name            New name or nested path for the cloned loop
                        Simple: my_loop
                        Nested: parent.my_loop or parent.child.my_loop
                        (Automatically inserts child_loops/ separators between hierarchy levels)

Options:
    --target PATH       Target directory (default: project_root/ravl_loops/)
    --description TEXT  Description for the cloned loop
    --help              Show this help message

Examples:
    # Clone to root level
    ravl-clone strategic_coherence my_handbook_monitoring

    # Clone to nested location under existing parent
    ravl-clone strategic_coherence frontier_delivery.my_monitoring
    # Creates: ravl_loops/frontier_delivery/child_loops/my_monitoring/

    # Clone to deeply nested location
    ravl-clone content_coherence frontier_delivery.context_management.my_checker
    # Creates: ravl_loops/frontier_delivery/child_loops/context_management/child_loops/my_checker/

    # Clone child from nested template to nested destination
    ravl-clone strategic_coherence.content_coherence frontier_delivery.strategic_coherence.content_coherence
    # Creates: ravl_loops/frontier_delivery/child_loops/strategic_coherence/child_loops/content_coherence/

    # Clone to custom directory
    ravl-clone data_ingress my_api --target ./custom_dir/

Search sources (all available):
1. Templates in .ravl/templates/
2. Examples in .ravl/docs/examples/
3. Existing RAVL loops in ravl_loops/

Note: Parent loops in the destination path must exist and be valid RAVL loops.
"""

import sys
import re
import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# Bootstrap: Find .ravl framework
_current = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_current / 'common'))
sys.path.insert(0, str(_current / 'common' / 'cli'))

from ravl_cli_base import RAVLCLIBase


class RAVLCloneCommand(RAVLCLIBase):
    """Clone a RAVL loop from templates or existing loops"""

    def __init__(self, project_loops_dir: Optional[Path] = None):
        """Initialize command

        Args:
            project_loops_dir: Optional custom path for project loops
        """
        # Find project root (uses CWD as fallback if outside RAVL project)
        self.project_root = self.find_project_root(required=False)

        # Find framework root (where templates/examples live)
        self.ravl_dir = self.find_framework_root()
        self.templates_dir = self.ravl_dir / 'ravl_loops' / 'templates'
        self.examples_dir = self.ravl_dir / 'ravl_loops' / 'examples'
        self.project_loops_dir = project_loops_dir if project_loops_dir else (self.project_root / 'ravl_loops')

    def run(self, args: argparse.Namespace):
        """
        Execute command

        Args:
            args: Parsed command-line arguments
        """
        source_name = args.loop_name

        # Determine new name - strip example prefix if no custom name provided
        if hasattr(args, 'new_name') and args.new_name:
            # User provided explicit name - use as-is
            new_name = args.new_name
        else:
            # No custom name - auto-strip example_n_ prefix from source
            base_source_name = source_name.split('.')[-1]  # Get last segment for nested paths
            stripped_name = self._strip_example_prefix(base_source_name)
            # Reconstruct full path if source was nested
            if '.' in source_name:
                parent_parts = source_name.split('.')[:-1]
                new_name = '.'.join(parent_parts + [stripped_name])
            else:
                new_name = stripped_name

        target_dir = args.target if hasattr(args, 'target') and args.target else None
        description = args.description if hasattr(args, 'description') and args.description else None

        # Default target_dir to project_loops_dir if not specified
        if not target_dir:
            target_dir = str(self.project_loops_dir)

        # Parse destination path for nested loop support
        if '.' in new_name:
            # Nested destination: parent.child.my_loop
            destination_segments = new_name.split('.')
            loop_name = destination_segments[-1]  # Last segment is loop name
            parent_segments = destination_segments[:-1]  # Everything before is parent hierarchy
        else:
            # Flat destination: my_loop
            loop_name = new_name
            parent_segments = []

        # Validate source name (can contain . for nested templates)
        # Split source_name by . and validate each segment
        source_segments = source_name.split('.')
        for segment in source_segments:
            if not self._is_valid_loop_name(segment):
                self.print_error(f"Invalid source loop name: {source_name}\n"
                               f"  Each segment must be lowercase snake_case (e.g., my_loop, user_sync)")
                sys.exit(1)

        # Validate loop name (last segment of destination)
        if not self._is_valid_loop_name(loop_name):
            self.print_error(f"Invalid loop name: {loop_name}\n"
                           f"  Loop names must be lowercase snake_case (e.g., fde_operating_strategy)")
            sys.exit(1)

        # Validate parent segments
        for segment in parent_segments:
            if not self._is_valid_loop_name(segment):
                self.print_error(f"Invalid parent name in path: {segment}\n"
                               f"  All path segments must be lowercase snake_case")
                sys.exit(1)

        # Find source loop(s)
        source_paths = self._find_all_loop_sources(source_name)
        if not source_paths:
            self.print_error(f"Loop not found: {source_name}")
            print(f"  Searched in: templates/, examples/, and existing RAVL loops", file=sys.stderr)
            sys.exit(1)

        # If multiple matches, ask user to select
        if len(source_paths) > 1:
            source_path = self._select_from_matches(source_paths)
        else:
            source_path = source_paths[0]

        # Determine target location
        if target_dir:
            target_base = Path(target_dir).resolve()
        else:
            target_base = self.project_root / 'ravl_loops'

        # Validate parent chain if nested destination
        if parent_segments:
            success, error_msg = self._validate_parent_chain(parent_segments, target_base)
            if not success:
                self.print_error(error_msg)
                sys.exit(1)

        # Build full nested path with child_loops/ separators
        target_path = self._build_nested_path(target_base, parent_segments, loop_name)

        # Check if already exists
        if target_path.exists():
            self.print_error(f"Already exists: {target_path}")
            sys.exit(1)

        # Create target parent and intermediate child_loops/ directories
        target_path.parent.mkdir(parents=True, exist_ok=True)

        self.print_info(f"Cloning RAVL loop: {source_name}")
        source_display = source_path.relative_to(self.project_root) if source_path.is_relative_to(self.project_root) else source_path
        target_display = target_path.relative_to(self.project_root) if target_path.is_relative_to(self.project_root) else target_path
        print(f"   Source: {source_display}", file=sys.stderr)
        print(f"   Target: {target_display}", file=sys.stderr)
        if parent_segments:
            print(f"   Nested under: {'.'.join(parent_segments)}", file=sys.stderr)
        if source_name != loop_name:
            # Check if this was auto-stripping
            source_base = source_name.split('/')[-1]
            if re.match(r'^example_\d+_', source_base) and not (hasattr(args, 'new_name') and args.new_name):
                print(f"   Auto-stripped prefix: {source_base} → {loop_name}", file=sys.stderr)
            else:
                print(f"   Renamed to: {loop_name}", file=sys.stderr)

        try:
            # Check if source has nested loops (is a parent loop)
            has_nested_loops = (source_path / 'child_loops').exists()
            if has_nested_loops:
                print(f"   ℹ️  Parent loop detected - will include nested child loops", file=sys.stderr)

            # Copy entire tree
            shutil.copytree(source_path, target_path)

            # If we renamed it, update config files
            if source_name != loop_name:
                self._update_loop_names(target_path, source_name, loop_name)

            # If description provided, update it
            if description:
                self._update_description(target_path, description)

            # Reset learning state (keep model structure but clear learnings)
            self._reset_learning_state(target_path)

            self.print_success(f"Cloned {source_name} to {new_name}")
            print(f"\nNext steps:", file=sys.stderr)
            print(f"  1. Configure the loop:", file=sys.stderr)
            target_display = target_path.relative_to(self.project_root) if target_path.is_relative_to(self.project_root) else target_path
            print(f"     Edit: {target_display}/config/", file=sys.stderr)
            print(f"  2. Run it:", file=sys.stderr)
            # Use hierarchical path for nested loops, simple name for flat loops
            run_path = new_name if not parent_segments else new_name
            print(f"     ./ravl {run_path}", file=sys.stderr)
            if has_nested_loops:
                print(f"  3. Or run child loops individually:", file=sys.stderr)
                child_loops = [d.name for d in (target_path / 'child_loops').iterdir() if d.is_dir() and (d / 'config' / 'ravl.yml').exists()]
                for child in child_loops:
                    # Show hierarchical path for nested child loops
                    child_run_path = f"{new_name}.{child}" if parent_segments else child
                    print(f"     ravl {child_run_path}", file=sys.stderr)

        except Exception as e:
            self.print_error(f"Failed to clone loop: {e}")
            # Clean up partial creation
            if target_path.exists():
                shutil.rmtree(target_path)
            sys.exit(1)

    def _find_nested_source(self, base_dir: Path, path_segments: list[str]) -> Optional[Path]:
        """
        Find a nested loop source by traversing hierarchical path

        Args:
            base_dir: Base directory to search in (templates_dir, examples_dir, etc.)
            path_segments: List of path segments (e.g., ['strategic_coherence', 'content_coherence'])

        Returns:
            Path if found and valid, None otherwise

        Example:
            base_dir = .ravl/templates/
            path_segments = ['strategic_coherence', 'content_coherence']
            Returns: .ravl/templates/strategic_coherence/child_loops/content_coherence/
        """
        if not base_dir.exists():
            return None

        current_path = base_dir

        # Traverse hierarchy with child_loops/ separators
        for i, segment in enumerate(path_segments):
            # Last segment is the target loop
            if i == len(path_segments) - 1:
                target_path = current_path / segment
                if target_path.is_dir() and self._is_valid_ravl_loop(target_path):
                    return target_path
            else:
                # Intermediate segments are parent loops
                parent_path = current_path / segment
                if not parent_path.is_dir():
                    return None
                # Move to child_loops/ subdirectory of parent
                current_path = parent_path / 'child_loops'
                if not current_path.is_dir():
                    return None

        return None

    def _find_all_loop_sources(self, loop_name: str) -> list[Path]:
        """
        Find all matches for a loop name in all sources

        Supports both simple names (my_loop) and nested paths (parent.child.my_loop)

        Args:
            loop_name: Name or path of loop to find
                       Examples: 'strategic_coherence' or 'strategic_coherence.content_coherence'

        Returns:
            List of paths to matching loops (sorted by source: templates, examples, project)
        """
        matches = []
        search_dirs = [
            (self.templates_dir, 'template'),
            (self.examples_dir, 'example'),
            (self.project_loops_dir, 'existing'),
        ]

        # Check if this is a nested source path
        is_nested_path = '.' in loop_name

        if is_nested_path:
            # Parse nested path into segments
            path_segments = loop_name.split('.')

            # Search in each source directory for nested path
            for search_dir, source_type in search_dirs:
                nested_path = self._find_nested_source(search_dir, path_segments)
                if nested_path:
                    matches.append(nested_path)
        else:
            # Simple name - use existing search logic
            for search_dir, source_type in search_dirs:
                if not search_dir.exists():
                    continue

                # Direct match
                direct_path = search_dir / loop_name
                if direct_path.is_dir() and self._is_valid_ravl_loop(direct_path):
                    matches.append(direct_path)

                # Search in subdirectories (for nested loops)
                for item in search_dir.rglob('*'):
                    if item.name == loop_name and item.is_dir() and self._is_valid_ravl_loop(item):
                        if item not in matches:  # Avoid duplicates
                            matches.append(item)

        return matches

    def _select_from_matches(self, matches: list[Path]) -> Path:
        """
        Prompt user to select from multiple matches

        Args:
            matches: List of matching loop paths

        Returns:
            Path selected by user
        """
        print(f"\nMultiple matches found. Which one do you want to clone?", file=sys.stderr)
        print("", file=sys.stderr)

        for idx, path in enumerate(matches, 1):
            rel_path = path.relative_to(self.project_root) if path.is_relative_to(self.project_root) else path
            print(f"  {idx}) {rel_path}", file=sys.stderr)

        print("", file=sys.stderr)

        while True:
            try:
                choice = input(f"Select [1-{len(matches)}]: ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(matches):
                    return matches[idx]
                else:
                    print(f"Invalid selection. Please enter a number between 1 and {len(matches)}.", file=sys.stderr)
            except (ValueError, EOFError, KeyboardInterrupt):
                self.print_error("Selection cancelled")
                sys.exit(1)

    def _is_valid_ravl_loop(self, path: Path) -> bool:
        """
        Check if directory is a valid RAVL loop

        Valid loops must have config/ravl.yml and either:
        - An implementation file (ravl_loop.md or ravl_loop.py), OR
        - A delegation directive in config/ravl.yml
        """
        config_file = path / 'config' / 'ravl.yml'

        if not config_file.exists():
            return False

        # Check for implementation files
        loop_file_md = path / 'ravl_loop.md'
        loop_file_py = path / 'ravl_loop.py'
        has_implementation = loop_file_md.exists() or loop_file_py.exists()

        if has_implementation:
            return True

        # Check if it's a delegation-only loop
        try:
            import yaml
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                # Valid if it has a delegate_to directive
                if config and 'delegate_to' in config:
                    return True
        except Exception:
            # If we can't parse the config, assume it's not valid
            pass

        return False

    def _is_valid_loop_name(self, name: str) -> bool:
        """Check if loop name is valid snake_case"""
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))

    def _strip_example_prefix(self, name: str) -> str:
        """
        Strip example_n_ prefix from loop name if present

        Args:
            name: Original loop name (e.g., 'example_2_intelligence_loop')

        Returns:
            Name with prefix removed (e.g., 'rugby_tips')

        Examples:
            'example_2_intelligence_loop' -> 'rugby_tips'
            'example_3_recursive_learning_loop' -> 'simple_learning_loop'
            'tech_news_curator' -> 'tech_news_curator' (unchanged)
        """
        import re
        # Match example_N_ where N is one or more digits
        match = re.match(r'^example_\d+_(.+)$', name)
        if match:
            return match.group(1)
        return name

    def _build_nested_path(self, base_path: Path, parent_segments: list[str], loop_name: str) -> Path:
        """
        Build physical path with child_loops/ separators for nested hierarchy

        Args:
            base_path: Base directory (e.g., project_root/ravl_loops/)
            parent_segments: List of parent loop names in hierarchy
            loop_name: Final loop name

        Returns:
            Full path with child_loops/ separators inserted

        Example:
            base_path = /project/ravl_loops/
            parent_segments = ['frontier_delivery', 'context_management']
            loop_name = 'my_loop'
            Returns: /project/ravl_loops/frontier_delivery/child_loops/context_management/child_loops/my_loop/
        """
        current_path = base_path

        for parent in parent_segments:
            current_path = current_path / parent / 'child_loops'

        return current_path / loop_name

    def _validate_parent_chain(self, parent_segments: list[str], base_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that all parents in the chain are valid RAVL loops

        Args:
            parent_segments: List of parent loop names in hierarchy
            base_path: Base path to start from (e.g., project_root/ravl_loops/)

        Returns:
            Tuple of (success, error_message)

        Validation:
            - Each parent must exist
            - Each parent must be a valid RAVL loop (has config/ravl.yml and implementation)
            - Intermediate child_loops/ directories are checked/created
        """
        current_path = base_path

        for i, parent in enumerate(parent_segments):
            parent_loop_dir = current_path / parent

            # Check if parent exists
            if not parent_loop_dir.exists():
                parent_path_str = '.'.join(parent_segments[:i+1])
                return (False,
                       f"Parent loop not found: {parent}\n"
                       f"  Expected at: {parent_loop_dir}\n"
                       f"  Full parent path: {parent_path_str}\n"
                       f"  \n"
                       f"  Create the parent loop first:\n"
                       f"    ./ravl-clone <template> {parent_path_str}")

            # Check if parent is a valid RAVL loop
            if not self._is_valid_ravl_loop(parent_loop_dir):
                return (False,
                       f"Parent directory exists but is not a valid RAVL loop: {parent}\n"
                       f"  Path: {parent_loop_dir}\n"
                       f"  Expected: {parent_loop_dir}/config/ravl.yml\n"
                       f"  Expected: {parent_loop_dir}/ravl_loop.py or ravl_loop.md\n"
                       f"  \n"
                       f"  Fix: Ensure {parent} is a complete RAVL loop with config and implementation")

            # Move to next level (child_loops/ subdirectory)
            current_path = parent_loop_dir / 'child_loops'

        return (True, None)

    def _update_loop_names(self, loop_path: Path, old_name: str, new_name: str):
        """
        Update internal references when renaming a loop

        Args:
            loop_path: Path to the cloned loop
            old_name: Original loop name
            new_name: New loop name
        """
        # Loop names are now derived from folder names, not stored in config
        # No need to update config files for renaming
        pass

    def _update_description(self, loop_path: Path, description: str):
        """
        Update description in config files

        Args:
            loop_path: Path to the cloned loop
            description: New description
        """
        import yaml

        # Update main config/ravl.yml
        config_file = loop_path / 'config' / 'ravl.yml'
        if config_file.exists():
            try:
                config = yaml.safe_load(config_file.read_text())
                if config:
                    config['description'] = description
                    with open(config_file, 'w') as f:
                        yaml.dump(config, f, default_flow_style=False)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not update description in {config_file.name}: {e}", file=sys.stderr)

    def _reset_learning_state(self, loop_path: Path):
        """
        Reset learning state for cloned loop by removing learnings directory

        Args:
            loop_path: Path to the cloned loop
        """
        import shutil

        # Remove entire learnings directory for fresh start
        learnings_dir = loop_path / 'learnings'
        if learnings_dir.exists():
            try:
                shutil.rmtree(learnings_dir)
                print(f"  [i]  Removed learnings for fresh start", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not remove learnings: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Clone a RAVL loop from templates, examples, or existing loops',
        usage='%(prog)s <loop-name> [new-name] [options]'
    )
    parser.add_argument('loop_name', help='Name of the loop to clone')
    parser.add_argument('new_name', nargs='?', help='Optional new name for the cloned loop')
    parser.add_argument('--target', help='Target directory (default: RAVL_DEFAULT_LOOP_DIRECTORY or project_root/ravl_loops/)')
    parser.add_argument('--description', help='Description for the cloned loop')
    parser.add_argument(
        '--loop-dir',
        type=str,
        default=None,
        help='Override loop directory for searching existing loops to clone (highest priority: CLI > .env > default)'
    )

    args = parser.parse_args()

    # Resolve loop directory if provided
    resolved_loops_dir = None
    if args.loop_dir:
        resolved_loops_dir = Path(args.loop_dir).expanduser().resolve()

    command = RAVLCloneCommand(project_loops_dir=resolved_loops_dir)
    command.run(args)


if __name__ == '__main__':
    main()
