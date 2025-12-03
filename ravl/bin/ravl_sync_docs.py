#!/usr/bin/env python3
"""
Sync framework documentation to project.

Copies all documentation from framework docs/ to project ravl_loops/docs/.
Uses clean sync: removes existing docs first to ensure exact mirror.

Usage:
    ravl --sync-docs
"""

import sys
import shutil
from pathlib import Path

# Bootstrap framework path
_current = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_current))

from ravl.common.cli.ravl_cli_base import RAVLCLIBase


class RAVLSyncDocsCommand(RAVLCLIBase):
    """Sync framework documentation to project"""

    def __init__(self):
        # Find project root (where ravl_loops/ lives) - optional for sync-docs
        self.project_root = self.find_project_root(required=False)

        # If no project found, use current directory
        if not self.project_root:
            self.project_root = Path.cwd()
            print(f"⚠️  No RAVL project found. Creating ravl_loops/ in current directory.")

        # Find framework root (where docs source lives)
        self.framework_root = self.find_framework_root()

        # Source: Framework docs
        self.source_docs = self.framework_root / 'ravl' / 'docs'

        # Destination: Project docs
        self.dest_docs = self.project_root / 'ravl_loops' / 'docs'

    def run(self):
        """Execute sync operation"""
        if not self.source_docs.exists():
            self.print_error(f"Framework docs not found at: {self.source_docs}")
            sys.exit(1)

        # Show warning if creating new project structure
        if not (self.project_root / 'ravl_loops').exists():
            print("⚠️  No RAVL project found. Creating ravl_loops/ structure.")

        # Clean sync: Delete existing docs directory first
        if self.dest_docs.exists():
            shutil.rmtree(self.dest_docs)
            print(f"🗑️  Removed existing docs at {self.dest_docs}")

        # Create fresh destination directory
        self.dest_docs.mkdir(parents=True, exist_ok=True)

        # Copy all markdown files (recursively)
        copied = []
        for md_file in self.source_docs.rglob('*.md'):
            # Compute relative path from source root
            rel_path = md_file.relative_to(self.source_docs)
            dest_file = self.dest_docs / rel_path

            # Create parent directories if needed
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(md_file, dest_file)
            copied.append(rel_path)

        # Report results
        if copied:
            self.print_success(f"Synced {len(copied)} documentation files to {self.dest_docs}")
            print("\nCopied files:")
            for file in sorted(copied):
                print(f"  • {file}")
        else:
            self.print_warning("No documentation files found to sync")

        # Remind about gitignore
        gitignore = self.project_root / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text()
            if 'ravl_loops/docs/' not in content:
                print("\n💡 Tip: Consider adding 'ravl_loops/docs/' to .gitignore")
                print("   Framework docs are auto-generated and don't need version control")


def main():
    """Entry point"""
    command = RAVLSyncDocsCommand()
    command.run()


if __name__ == '__main__':
    main()
