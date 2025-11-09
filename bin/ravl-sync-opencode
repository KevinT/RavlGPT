#!/usr/bin/env python3
"""
RAVL-SYNC-OPENCODE - Sync RAVL commands to OpenCode

Creates and updates OpenCode slash commands for all RAVL CLI tools.

Usage:
    ravl-sync-opencode [options]

Options:
    --check     Check if commands are up-to-date without modifying
    --force     Overwrite all commands without prompting

Description:
    This command ensures .opencode/command/ contains up-to-date slash commands
    for all RAVL CLI tools. It:
    - Creates missing command files
    - Updates outdated command files
    - Validates command definitions
    - Reports status for each command

Examples:
    ravl-sync-opencode              # Interactive sync (prompts for overwrites)
    ravl-sync-opencode --check      # Check status only
    ravl-sync-opencode --force      # Force update all
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Bootstrap: Find .ravl framework
_current = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_current / 'common'))
sys.path.insert(0, str(_current / 'common' / 'cli'))

from ravl_cli_base import RAVLCLIBase


class RAVLSyncOpenCodeCommand(RAVLCLIBase):
    """Sync RAVL commands to OpenCode"""

    def __init__(self):
        """Initialize command"""
        self.project_root = self.find_project_root()
        self.opencode_command_dir = self.project_root / '.opencode' / 'command'
        self.ravl_bin_dir = self.project_root / '.ravl' / 'bin'

    def run(self, args: argparse.Namespace):
        """
        Execute command

        Args:
            args: Parsed command-line arguments
        """
        # Ensure .opencode/command/ exists
        self.opencode_command_dir.mkdir(parents=True, exist_ok=True)

        # Discover commands dynamically
        commands = self._discover_commands()

        if not commands:
            self.print_warning("No RAVL commands found to sync")
            return

        # Process each command
        results = []
        for cmd_name, cmd_def in commands.items():
            status = self._sync_command(cmd_name, cmd_def, args)
            results.append((cmd_name, status))

        # Handle legacy rename: list-ravls.md -> ravl-list.md
        legacy_file = self.opencode_command_dir / 'list-ravls.md'
        if legacy_file.exists():
            self._handle_legacy_rename(legacy_file, args)
            results.append(('list-ravls', 'renamed'))

        # Print summary
        self._print_summary(results, args.check)

        # Exit with error if any issues in check mode
        if args.check:
            issues = [r for r in results if r[1] in ('missing', 'outdated', 'error')]
            if issues:
                sys.exit(1)

    def _discover_commands(self) -> Dict[str, Dict[str, str]]:
        """
        Discover all RAVL commands in .ravl/bin/

        Returns:
            Dictionary of command definitions keyed by command name
        """
        commands = {}

        # Scan .ravl/bin/ for RAVL commands
        if not self.ravl_bin_dir.exists():
            return commands

        for cmd_file in sorted(self.ravl_bin_dir.iterdir()):
            # Skip non-files and files not starting with 'ravl'
            if not cmd_file.is_file() or not cmd_file.name.startswith('ravl'):
                continue
            
            # Skip commands containing 'claude'
            if 'claude' in cmd_file.name.lower():
                continue

            # Skip backup files
            if cmd_file.name.endswith(('.bak', '.swp', '~')):
                continue

            # Parse command definition from docstring
            cmd_def = self._parse_docstring(cmd_file)
            if cmd_def:
                commands[cmd_file.name] = cmd_def

        return commands

    def _parse_docstring(self, cmd_file: Path) -> Optional[Dict[str, str]]:
        """
        Parse command definition from Python docstring

        Args:
            cmd_file: Path to command file

        Returns:
            Command definition dict or None if parsing fails
        """
        try:
            with open(cmd_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract docstring (first triple-quoted string)
            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if not docstring_match:
                return None

            docstring = docstring_match.group(1).strip()
            lines = docstring.split('\n')

            # Extract components
            description = None
            usage_lines = []
            example_lines = []
            in_usage = False
            in_examples = False

            for line in lines:
                stripped = line.strip()

                # Title line: "COMMAND-NAME - Description"
                if ' - ' in stripped and not description:
                    description = stripped.split(' - ', 1)[1].strip()
                    continue

                # Section markers
                if stripped.startswith('Usage:'):
                    in_usage = True
                    in_examples = False
                    continue
                elif stripped.startswith('Examples:'):
                    in_examples = True
                    in_usage = False
                    continue
                elif stripped.endswith(':') and stripped[0].isupper():
                    # Other section (Arguments, Options, etc.)
                    in_usage = False
                    in_examples = False
                    continue

                # Collect usage lines
                if in_usage and stripped:
                    usage_lines.append(stripped)

                # Collect example lines
                if in_examples and stripped:
                    example_lines.append(stripped)

            # Build command pattern from usage
            command_pattern = None
            if usage_lines:
                # Get first usage line and convert to relative path
                usage = usage_lines[0]
                cmd_name = cmd_file.name

                # Determine path prefix
                if cmd_name in ['ravl', 'ravl-list']:
                    # Top-level commands in PATH
                    command_pattern = usage
                else:
                    # Commands in .ravl/bin/
                    # Replace command name with relative path
                    command_pattern = usage.replace(cmd_name, f'./.ravl/bin/{cmd_name}', 1)

            # Return None if we couldn't extract minimum info
            if not description or not command_pattern:
                return None

            return {
                'description': description,
                'command': command_pattern,
                'examples': example_lines if example_lines else []
            }

        except Exception as e:
            self.print_error(f"Error parsing {cmd_file.name}: {e}")
            return None

    def _sync_command(
        self,
        cmd_name: str,
        cmd_def: Dict[str, str],
        args: argparse.Namespace
    ) -> str:
        """
        Sync a single command

        Args:
            cmd_name: Command name (e.g., 'ravl', 'ravl-list')
            cmd_def: Command definition dict
            args: Parsed arguments

        Returns:
            Status: 'created', 'updated', 'current', 'skipped', 'error'
        """
        cmd_file = self.opencode_command_dir / f'{cmd_name}.md'
        expected_content = self._generate_command_file(cmd_def)

        try:
            # Check if file exists
            if not cmd_file.exists():
                if args.check:
                    return 'missing'
                # Create new file
                with open(cmd_file, 'w', encoding='utf-8') as f:
                    f.write(expected_content)
                return 'created'

            # Check if content matches
            with open(cmd_file, 'r', encoding='utf-8') as f:
                current_content = f.read()

            if current_content == expected_content:
                return 'current'

            # Content differs
            if args.check:
                return 'outdated'

            # Update file (with prompt unless --force)
            if not args.force:
                if not self._confirm_overwrite(cmd_name):
                    return 'skipped'

            with open(cmd_file, 'w', encoding='utf-8') as f:
                f.write(expected_content)
            return 'updated'

        except Exception as e:
            self.print_error(f"Error processing {cmd_name}: {e}")
            return 'error'

    def _generate_command_file(self, cmd_def: Dict[str, str]) -> str:
        """
        Generate OpenCode command file content

        Args:
            cmd_def: Command definition

        Returns:
            Command file content
        """
        content = f"""---
description: {cmd_def['description']}
permission:
  bash: allow
---

```bash
{cmd_def['command']}
```
"""

        # Add examples if provided
        if 'examples' in cmd_def and cmd_def['examples']:
            content += "\n## Examples\n\n```bash\n"
            content += "\n".join(cmd_def['examples'])
            content += "\n```\n"

        return content

    def _handle_legacy_rename(self, legacy_file: Path, args: argparse.Namespace):
        """Handle renaming list-ravls.md to ravl-list.md"""
        new_file = self.opencode_command_dir / 'ravl-list.md'

        if args.check:
            self.print_warning(f"Legacy file exists: {legacy_file.name} (should be renamed)")
            return

        # Check if new file already exists
        if new_file.exists():
            # Both exist - just delete legacy
            self.print_info(f"Removing legacy file: {legacy_file.name}")
            legacy_file.unlink()
        else:
            # Rename legacy to new
            self.print_info(f"Renaming: {legacy_file.name} -> {new_file.name}")
            legacy_file.rename(new_file)

    def _confirm_overwrite(self, cmd_name: str) -> bool:
        """
        Prompt user to confirm overwrite

        Args:
            cmd_name: Command name

        Returns:
            True if user confirms, False otherwise
        """
        print(f"\n⚠️  Command file differs: {cmd_name}.md", file=sys.stderr)
        print("   Overwrite with latest definition? [y/N] ", end='', file=sys.stderr)

        try:
            response = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("", file=sys.stderr)
            return False

        return response in ('y', 'yes')

    def _print_summary(self, results: List[Tuple[str, str]], check_only: bool):
        """
        Print summary of sync results

        Args:
            results: List of (command_name, status) tuples
            check_only: Whether this was a check-only run
        """
        print("", file=sys.stderr)
        self.print_header("OpenCode Command Sync", "🔄")

        # Group by status
        by_status: Dict[str, List[str]] = {}
        for cmd_name, status in results:
            by_status.setdefault(status, []).append(cmd_name)

        # Print each category
        status_info = {
            'current': ('✅', 'Up-to-date'),
            'created': ('✨', 'Created'),
            'updated': ('🔄', 'Updated'),
            'missing': ('❌', 'Missing'),
            'outdated': ('⚠️', 'Outdated'),
            'skipped': ('⏭️', 'Skipped'),
            'renamed': ('📝', 'Renamed'),
            'error': ('❌', 'Error')
        }

        for status in ['current', 'created', 'updated', 'missing', 'outdated', 'skipped', 'renamed', 'error']:
            if status in by_status:
                emoji, label = status_info[status]
                commands = by_status[status]
                print(f"{emoji} {label}:", file=sys.stderr)
                for cmd in commands:
                    print(f"   - {cmd}.md", file=sys.stderr)
                print("", file=sys.stderr)

        # Summary message
        total = len(results)
        if check_only:
            issues = len([r for r in results if r[1] in ('missing', 'outdated', 'error')])
            if issues:
                self.print_warning(f"{issues}/{total} commands need sync")
                print("   Run without --check to sync", file=sys.stderr)
            else:
                self.print_success(f"All {total} commands are up-to-date")
        else:
            updated = len([r for r in results if r[1] in ('created', 'updated', 'renamed')])
            if updated:
                self.print_success(f"Synced {updated}/{total} commands")
            else:
                self.print_success(f"All {total} commands were already up-to-date")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Sync RAVL commands to OpenCode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if commands are up-to-date without modifying'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite all commands without prompting'
    )

    args = parser.parse_args()

    command = RAVLSyncOpenCodeCommand()
    command.run(args)


if __name__ == '__main__':
    main()
