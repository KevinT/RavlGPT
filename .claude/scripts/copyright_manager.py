#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Copyright Header Manager for RAVL Project

Utilities for checking, adding, and validating copyright headers
across the codebase.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

class CopyrightManager:
    """Manage copyright headers across the codebase."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize copyright manager.

        Args:
            project_root: Path to project root (auto-detected if None)
        """
        self.project_root = project_root or self._find_project_root()
        self.config_path = self.project_root / '.copyright-config.json'
        self.config = self._load_config()

    def _find_project_root(self) -> Path:
        """Find project root by looking for .copyright-config.json."""
        current = Path(__file__).resolve()

        # Walk up directory tree
        for parent in [current] + list(current.parents):
            if (parent / '.copyright-config.json').exists():
                return parent

        # Fallback: assume script is in .claude/scripts/
        return current.parent.parent.parent

    def _load_config(self) -> Dict:
        """Load copyright configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )

        with open(self.config_path) as f:
            return json.load(f)

    def get_header_text(self) -> str:
        """Get the copyright header as a string."""
        return '\n'.join(self.config['header_template']) + '\n'

    def has_header(self, filepath: Path) -> bool:
        """Check if file has MPL 2.0 copyright header.

        Args:
            filepath: Path to file to check

        Returns:
            True if file has header, False otherwise
        """
        if not filepath.exists():
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read(500)  # Read first 500 chars

            # Remove comment markers and newlines for easier matching
            import re
            content_normalized = content.replace('#', '').replace('\n', ' ')
            # Normalize multiple spaces to single space
            content_normalized = re.sub(r'\s+', ' ', content_normalized)

            # Check for key phrases
            has_mpl = 'Mozilla Public License' in content_normalized
            has_copyright = 'Copyright (c)' in content

            return has_mpl and has_copyright

        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
            return False

    def validate_header(self, filepath: Path) -> Tuple[bool, Optional[str]]:
        """Validate that header is correctly formatted.

        Args:
            filepath: Path to file to validate

        Returns:
            (is_valid, error_message) tuple
        """
        if not self.has_header(filepath):
            return False, "Missing copyright header"

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [f.readline() for _ in range(15)]

            header_text = self.get_header_text()
            file_start = ''.join(lines)

            # Skip shebang if present
            if lines[0].startswith('#!'):
                file_start = ''.join(lines[1:])

            # Check if header appears early in file
            if header_text not in file_start:
                return False, "Header exists but is incorrectly formatted or positioned"

            return True, None

        except Exception as e:
            return False, f"Could not validate: {e}"

    def add_header(self, filepath: Path, dry_run: bool = False) -> bool:
        """Add copyright header to file if missing.

        Args:
            filepath: Path to file
            dry_run: If True, don't actually modify file

        Returns:
            True if header was added (or would be added in dry_run)
        """
        if self.has_header(filepath):
            return False  # Already has header

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if file has shebang
            lines = content.split('\n')
            has_shebang = lines[0].startswith('#!')

            # Build new content
            header = self.get_header_text()

            if has_shebang:
                # Insert after shebang
                new_content = lines[0] + '\n' + header + '\n' + '\n'.join(lines[1:])
            else:
                # Insert at beginning
                new_content = header + '\n' + content

            if not dry_run:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)

            return True

        except Exception as e:
            print(f"Error adding header to {filepath}: {e}", file=sys.stderr)
            return False

    def scan_priority(self, priority: str) -> List[Dict]:
        """Scan files for a specific priority level.

        Args:
            priority: Priority level (e.g., 'priority_1')

        Returns:
            List of dicts with file info: {path, has_header, valid}
        """
        if priority not in self.config['file_patterns']:
            raise ValueError(f"Unknown priority: {priority}")

        priority_config = self.config['file_patterns'][priority]
        results = []

        for rel_path in priority_config['files']:
            filepath = self.project_root / rel_path
            has_header = self.has_header(filepath)
            is_valid, error = self.validate_header(filepath) if has_header else (False, None)

            results.append({
                'path': rel_path,
                'absolute_path': filepath,
                'exists': filepath.exists(),
                'has_header': has_header,
                'valid': is_valid,
                'error': error
            })

        return results

    def scan_all(self) -> Dict[str, List[Dict]]:
        """Scan all priority levels.

        Returns:
            Dict mapping priority level to results
        """
        all_results = {}

        for priority in self.config['file_patterns'].keys():
            all_results[priority] = self.scan_priority(priority)

        return all_results

    def print_status(self, results: Dict[str, List[Dict]]) -> None:
        """Print formatted status report.

        Args:
            results: Results from scan_all()
        """
        print("=" * 70)
        print("COPYRIGHT HEADER STATUS")
        print("=" * 70)

        total_files = 0
        total_with_headers = 0
        total_valid = 0

        for priority, files in results.items():
            priority_config = self.config['file_patterns'][priority]
            description = priority_config['description']

            print(f"\n{priority.upper().replace('_', ' ')}: {description}")
            print("-" * 70)

            for file_info in files:
                total_files += 1

                if not file_info['exists']:
                    status = "⚠️  NOT FOUND"
                elif file_info['valid']:
                    status = "✅ VALID"
                    total_with_headers += 1
                    total_valid += 1
                elif file_info['has_header']:
                    status = "⚠️  INVALID"
                    total_with_headers += 1
                else:
                    status = "❌ MISSING"

                print(f"  {status} {file_info['path']}")

                if file_info.get('error'):
                    print(f"           {file_info['error']}")

        print("\n" + "=" * 70)
        print(f"SUMMARY: {total_valid}/{total_files} valid, "
              f"{total_with_headers}/{total_files} have headers")
        print("=" * 70)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Manage copyright headers in RAVL project'
    )
    parser.add_argument(
        'action',
        choices=['check', 'add', 'validate'],
        help='Action to perform'
    )
    parser.add_argument(
        '--file',
        type=Path,
        help='Specific file to process'
    )
    parser.add_argument(
        '--priority',
        help='Priority level (e.g., priority_1, priority_2)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    manager = CopyrightManager()

    if args.action == 'check':
        if args.priority:
            results = {args.priority: manager.scan_priority(args.priority)}
        else:
            results = manager.scan_all()
        manager.print_status(results)

    elif args.action == 'add':
        if args.file:
            added = manager.add_header(args.file, dry_run=args.dry_run)
            if added:
                print(f"{'Would add' if args.dry_run else 'Added'} header to {args.file}")
            else:
                print(f"Header already exists in {args.file}")
        elif args.priority:
            files = manager.scan_priority(args.priority)
            for file_info in files:
                if not file_info['has_header'] and file_info['exists']:
                    added = manager.add_header(
                        file_info['absolute_path'],
                        dry_run=args.dry_run
                    )
                    if added:
                        print(f"{'Would add' if args.dry_run else 'Added'} "
                              f"header to {file_info['path']}")
        else:
            print("Error: Must specify --file or --priority")
            sys.exit(1)

    elif args.action == 'validate':
        if args.file:
            is_valid, error = manager.validate_header(args.file)
            if is_valid:
                print(f"✅ {args.file} has valid header")
            else:
                print(f"❌ {args.file}: {error}")
                sys.exit(1)
        else:
            results = manager.scan_all()
            manager.print_status(results)


if __name__ == '__main__':
    main()
