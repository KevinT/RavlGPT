#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
RAVL-NEW-LOOP - Create a new RAVL loop from scratch

Create a new RAVL loop with custom content and configuration without cloning from templates.
Supports both top-level and nested loop creation with dot-notation syntax.

Usage:
    ravl --new <loop-name> --content <markdown-content> [--config <config-data>]

Arguments:
    loop-name               Name or nested path for the new loop
                            Simple: my_loop
                            Nested (dot notation): parent.child.my_loop
                            (Automatically converts dots to ravl_loops/ separators)

Required Options:
    --content TEXT          Markdown content for ravl_loop.md (required)
                            Can be inline string or multiline

Optional Options:
    --config TEXT           Configuration for config/ravl.toml
                            Format: YAML or JSON (auto-detected, converted to TOML)
                            Example YAML: 'description: My loop\\nemoji: 🔥'
                            Example JSON: '{"description": "My loop", "emoji": "🔥"}'
    --target PATH           Target directory (default: project_root/ravl_loops/)
    --help                  Show this help message

Examples:
    # RECOMMENDED: Use single quotes for content with special characters
    ravl --new my_loop --content 'Write `Hello RAVL!` to `./output/file.md`'

    # Simple content (framework enhances at runtime)
    ravl --new my_loop --content 'Analyze data and generate report'

    # Create nested loop under existing parent (dot notation)
    ravl --new org_context.my_child --content 'Process user data from API'
    # Creates: ravl_loops/org_context/ravl_loops/my_child/

    # Alternative: Escape backticks with backslashes in double quotes
    ravl --new my_loop --content "Write \\`Hello RAVL!\\` to \\`./output/file.md\\`"

    # Create with custom configuration (YAML)
    ravl --new my_loop \\
        --content 'Analyze data' \\
        --config 'description: Custom description\\nemoji: 🎯\\ntype: markdown'

    # Create with custom configuration (JSON)
    ravl --new my_loop \\
        --content 'Process data' \\
        --config '{"description": "Custom description", "emoji": "🎯"}'

    # Create deeply nested loop
    ravl --new frontier_delivery.context_management.strategy_alignment \\
        --content 'Align strategy with context'
    # Creates: ravl_loops/frontier_delivery/ravl_loops/context_management/ravl_loops/strategy_alignment/

    # AVOID: Backticks in double quotes (shell executes them as commands!)
    ravl --new my_loop --content "Write `Hello RAVL!` here"  # ❌ Shell runs `Hello RAVL!`

Path Resolution:
    Dot notation is converted to hierarchical structure with ravl_loops/ separators:
    - my_loop → ravl_loops/my_loop/
    - parent.child → ravl_loops/parent/ravl_loops/child/
    - a.b.c → ravl_loops/a/ravl_loops/b/ravl_loops/c/

Note: Parent loops in the path must exist. Create parent loops first if needed.
"""

import sys
import re
import argparse
import json
import toml
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Bootstrap: Find .ravl framework
_current = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_current / 'common'))
sys.path.insert(0, str(_current / 'common' / 'cli'))

from ravl_cli_base import RAVLCLIBase
from loop_discovery import LoopDiscovery
from utils.file_utils import save_toml_file


class RAVLNewLoopCommand(RAVLCLIBase):
    """Create a new RAVL loop from scratch"""

    def __init__(self, project_loops_dir: Optional[Path] = None):
        """Initialize command

        Args:
            project_loops_dir: Optional custom path for project loops
        """
        # Get project root (uses CWD as fallback if outside RAVL project)
        # Works identically for UV installation or .ravl submodule
        self.project_root = self.find_project_root(required=False)

        # Always use ravl_loops/ convention for consistency
        # Works identically whether using UV installation or .ravl submodule
        self.project_loops_dir = project_loops_dir if project_loops_dir else (self.project_root / 'ravl_loops')

        self.discovery = LoopDiscovery(self.project_root, loops_dir=project_loops_dir)

    def run(self, args: argparse.Namespace):
        """
        Execute command

        Args:
            args: Parsed command-line arguments
        """
        loop_path_spec = args.loop_name
        content = args.content
        config_data = args.config if hasattr(args, 'config') and args.config else None
        target_dir = args.target if hasattr(args, 'target') and args.target else None

        # If no content provided, delegate to ravl --clone empty_loop_template
        if not content:
            self._delegate_to_clone(args)
            return  # _delegate_to_clone exits, but return for clarity

        # Validate content wasn't mangled by shell
        is_valid, error_msg = self._validate_content(content)
        if not is_valid:
            self.print_error(error_msg)
            print(f"\n  Tip: Check your shell quoting. Use single quotes for complex content.", file=sys.stderr)
            sys.exit(1)

        # Default target_dir to project_loops_dir if not specified
        if not target_dir:
            target_dir = str(self.project_loops_dir)

        # Parse path spec (dot notation or slash notation)
        path_segments = self._parse_path_spec(loop_path_spec)
        if not path_segments:
            self.print_error(f"Invalid loop path: {loop_path_spec}\n"
                           "  Use dot notation (parent.child.my_loop) or simple name (my_loop)")
            sys.exit(1)

        loop_name = path_segments[-1]  # Last segment is loop name
        parent_segments = path_segments[:-1]  # Everything before is parent hierarchy

        # Validate all segments (loop name and parents)
        for segment in path_segments:
            if not self._is_valid_loop_name(segment):
                self.print_error(f"Invalid loop name segment: {segment}\n"
                               f"  All segments must be lowercase snake_case (e.g., my_loop, user_sync)\n"
                               f"  Invalid characters or format detected")
                sys.exit(1)

        # Determine target location
        target_base = Path(target_dir).resolve()

        # Validate parent chain if nested
        if parent_segments:
            success, error_msg = self._validate_parent_chain(parent_segments, target_base)
            if not success:
                self.print_error(error_msg)
                sys.exit(1)

        # Build full nested path with ravl_loops/ separators
        target_path = self._build_nested_path(target_base, parent_segments, loop_name)

        # Check if already exists
        if target_path.exists():
            self.print_error(f"Loop already exists: {target_path}\n"
                           f"  Delete the existing loop first or choose a different name")
            sys.exit(1)

        # Parse and merge config
        config = self._parse_config(config_data)

        # Add defaults if not provided
        if 'type' not in config:
            config['type'] = 'markdown'
        if 'emoji' not in config:
            config['emoji'] = '➿'
        if 'description' not in config:
            config['description'] = f"RAVL loop: {loop_name}"

        self.print_info(f"Creating new RAVL loop: {loop_name}")
        target_display = target_path.relative_to(self.project_root) if target_path.is_relative_to(self.project_root) else target_path
        print(f"   Location: {target_display}", file=sys.stderr)
        if parent_segments:
            print(f"   Nested under: {'.'.join(parent_segments)}", file=sys.stderr)
        print(f"   Type: {config['type']}", file=sys.stderr)
        print(f"   Emoji: {config['emoji']}", file=sys.stderr)

        try:
            # Create directory structure
            target_path.mkdir(parents=True, exist_ok=False)
            (target_path / 'config').mkdir(exist_ok=True)

            # Write config/ravl.toml
            config_file = target_path / 'config' / 'ravl.toml'
            save_toml_file(config_file, config, create_dirs=False)

            # Write ravl_loop.md
            loop_file = target_path / 'ravl_loop.md'
            with open(loop_file, 'w') as f:
                f.write(content)

            self.print_success(f"Created {loop_name}")
            print(f"\nNext steps:", file=sys.stderr)
            print(f"  1. Review the loop content:", file=sys.stderr)
            print(f"     {target_display}/ravl_loop.md", file=sys.stderr)
            print(f"  2. Configure if needed:", file=sys.stderr)
            print(f"     {target_display}/config/ravl.toml", file=sys.stderr)
            print(f"  3. Run it:", file=sys.stderr)
            # Use dot notation path for display
            run_path = '.'.join(path_segments)
            print(f"     ravl {run_path} --mode fast", file=sys.stderr)
            print(f"\nNote: Learning artifacts (learnings/) will be auto-created on first run", file=sys.stderr)

        except Exception as e:
            self.print_error(f"Failed to create loop: {e}")
            # Clean up partial creation
            if target_path.exists():
                import shutil
                shutil.rmtree(target_path)
            sys.exit(1)

    def _delegate_to_clone(self, args: argparse.Namespace):
        """
        Delegate to ravl --clone empty_loop_template when --content is omitted

        This provides a simpler workflow for users who just want to create a loop
        with placeholder content rather than writing custom content upfront.

        Args:
            args: Parsed command-line arguments from ravl --new
        """
        import subprocess

        # The template is nested: templates/child_loops/empty_loop_template
        # But ravl-clone can find it by searching recursively in template directories
        source_name = 'empty_loop_template'

        # Build clone command
        framework_root = self.find_framework_root()
        clone_script = framework_root / 'bin' / 'ravl_clone.py'

        clone_cmd = [sys.executable, str(clone_script), source_name, args.loop_name]

        # Pass through compatible arguments
        if hasattr(args, 'target') and args.target:
            clone_cmd.extend(['--target', args.target])

        # Warn about unsupported arguments
        if hasattr(args, 'config') and args.config:
            self.print_warning("--config is not supported when delegating to clone.\n"
                             "  Edit config/ravl.toml after loop creation.")

        self.print_info(f"No --content provided, delegating to: ravl --clone {source_name} {args.loop_name}")

        # Execute clone command
        result = subprocess.run(clone_cmd)
        sys.exit(result.returncode)

    def _parse_path_spec(self, path_spec: str) -> list[str]:
        """
        Parse path specification into segments

        Supports both dot notation (parent.child.my_loop) and slash notation (parent/child/my_loop)

        Args:
            path_spec: Path specification string

        Returns:
            List of path segments, or empty list if invalid
        """
        if not path_spec:
            return []

        # Support both . and / as separators (normalize to .)
        normalized = path_spec.replace('/', '.')
        segments = normalized.split('.')

        # Filter out empty segments
        segments = [s.strip() for s in segments if s.strip()]

        return segments

    def _validate_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that content wasn't mangled by shell command substitution

        Detects signs of shell interference:
        - Empty or suspiciously short content (< 10 chars)

        Does NOT validate RAVL structure (framework enhances simple content at runtime)

        Args:
            content: Content string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not content or len(content.strip()) < 10:
            return (False,
                    "Content is empty or suspiciously short\n"
                    "  This often happens when shell interprets backticks (`) as command substitution\n"
                    "  \n"
                    "  Solutions:\n"
                    "    1. Use single quotes to prevent shell expansion:\n"
                    "       --content 'Write `Hello RAVL!` to file'\n"
                    "  \n"
                    "    2. Or escape backticks in double quotes:\n"
                    "       --content \"Write \\\\`Hello RAVL!\\\\` to file\"\n"
                    "  \n"
                    f"  Received: {repr(content[:100])}\n"
                    f"  Length: {len(content)} chars")

        return (True, None)

    def _is_valid_loop_name(self, name: str) -> bool:
        """Check if loop name is valid snake_case"""
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))

    def _build_nested_path(self, base_path: Path, parent_segments: list[str], loop_name: str) -> Path:
        """
        Build physical path for new loop using actual parent location from LoopDiscovery

        Uses LoopDiscovery to find the actual parent location, then creates child under it.
        This ensures children are created in the correct location even when parents
        are nested deep in the hierarchy.

        Args:
            base_path: Base directory (e.g., project_root/ravl_loops/)
            parent_segments: List of parent loop names in hierarchy
            loop_name: Final loop name

        Returns:
            Full path with ravl_loops/ separators inserted

        Example:
            base_path = /project/ravl_loops/
            parent_segments = ['delivery_enablement_system']
            loop_name = 'my_loop'
            If delivery_enablement_system lives at: experimental/delivery_enablement_system/
            Returns: /project/ravl_loops/experimental/ravl_loops/delivery_enablement_system/ravl_loops/my_loop/
        """
        if not parent_segments:
            # No parent - create directly under base_path
            return base_path / loop_name

        # Use LoopDiscovery to find the actual parent location
        parent_path_str = '.'.join(parent_segments)
        try:
            parent_loop_dir = self.discovery.find_loop(parent_path_str)
            # Create child under parent's ravl_loops/ subdirectory
            return parent_loop_dir / 'ravl_loops' / loop_name
        except ValueError:
            # Parent not found - validation should have caught this, but fall back to naive path
            # This shouldn't happen if _validate_parent_chain was called first
            current_path = base_path
            for parent in parent_segments:
                current_path = current_path / parent / 'ravl_loops'
            return current_path / loop_name

    def _validate_parent_chain(self, parent_segments: list[str], base_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that all parents in the chain are valid RAVL loops

        Uses LoopDiscovery to find parent loops, allowing them to exist anywhere in the hierarchy.
        This is consistent with how execution commands find loops.

        Args:
            parent_segments: List of parent loop names in hierarchy
            base_path: Base path to start from (e.g., project_root/ravl_loops/)

        Returns:
            Tuple of (success, error_message)

        Validation:
            - Each parent must exist and be findable by LoopDiscovery
            - Each parent must be a valid RAVL loop (has config/ravl.toml)
        """
        for i, parent in enumerate(parent_segments):
            # Build parent path up to this point (dot notation)
            parent_path_str = '.'.join(parent_segments[:i+1])

            try:
                # Use LoopDiscovery to find the parent loop (can find it anywhere)
                parent_loop_dir = self.discovery.find_loop(parent_path_str)

                # Validate it's a proper RAVL loop
                if not self._is_valid_ravl_loop(parent_loop_dir):
                    return (False,
                           f"Parent directory exists but is not a valid RAVL loop: {parent}\n"
                           f"  Path: {parent_loop_dir}\n"
                           f"  Expected: {parent_loop_dir}/config/ravl.toml\n"
                           f"  \n"
                           f"  Fix: Ensure {parent} is a complete RAVL loop with config")

            except ValueError as e:
                # LoopDiscovery couldn't find the parent
                return (False,
                       f"Parent loop not found: {parent}\n"
                       f"  Full parent path: {parent_path_str}\n"
                       f"  \n"
                       f"  {str(e)}\n"
                       f"  \n"
                       f"  Create the parent loop first:\n"
                       f"    ravl --new {parent_path_str} --content \"...\"")

        return (True, None)

    def _is_valid_ravl_loop(self, path: Path) -> bool:
        """
        Check if directory is a valid RAVL loop

        Valid loops must have config/ravl.toml
        """
        config_file = path / 'config' / 'ravl.toml'
        return config_file.exists()

    def _parse_config(self, config_data: Optional[str]) -> Dict[str, Any]:
        """
        Parse configuration from string (YAML or JSON)

        Args:
            config_data: Configuration string (YAML or JSON format)

        Returns:
            Parsed configuration dictionary

        Raises:
            ValueError: If config is invalid
        """
        if not config_data:
            return {}

        # Try JSON first (has clear markers: { })
        if config_data.strip().startswith('{'):
            try:
                return json.loads(config_data)
            except json.JSONDecodeError as e:
                self.print_error(f"Invalid JSON config: {e}")
                sys.exit(1)

        # Try YAML (more flexible)
        try:
            result = toml.load(config_data)
            if not isinstance(result, dict):
                self.print_error(f"Config must be a dictionary/object, got: {type(result).__name__}")
                sys.exit(1)
            return result
        except yaml.YAMLError as e:
            self.print_error(f"Invalid YAML config: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Create a new RAVL loop from scratch',
        usage='%(prog)s <loop-name> --content <markdown-content> [options]',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('loop_name', help='Name or path for the new loop (use dot notation: parent.child.my_loop)')
    parser.add_argument('--content', required=False, help='Markdown content for ravl_loop.md (optional - delegates to empty_loop_template if omitted)')
    parser.add_argument('--config', help='Configuration as YAML or JSON string')
    parser.add_argument('--target', help='Target directory (default: project_root/ravl_loops/)')
    parser.add_argument(
        '--loop-dir',
        type=str,
        default=None,
        help='Override loop directory (highest priority: CLI > .env > default)'
    )

    args = parser.parse_args()

    # Resolve loop directory if provided
    resolved_loops_dir = None
    if args.loop_dir:
        resolved_loops_dir = Path(args.loop_dir).expanduser().resolve()

    command = RAVLNewLoopCommand(project_loops_dir=resolved_loops_dir)
    command.run(args)


if __name__ == '__main__':
    main()
