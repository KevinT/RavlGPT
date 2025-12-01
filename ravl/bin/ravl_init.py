#!/usr/bin/env python3
"""
Initialize a new RAVL project.
Creates ravl_loops/ directory structure and basic configuration.

Usage:
    ravl --init

This command initializes a new RAVL project in the current directory by creating:
- ravl_loops/ directory (the project marker)
- ravl_loops/config/ravl.toml (basic project configuration)
- README.md (if not already present)

Note: Loops create their own learning directories and output directories as needed.
ravl_learning/ and data/ directories are NOT required during init.
"""

import sys
from pathlib import Path


def main():
    """Initialize a new RAVL project in current directory."""
    cwd = Path.cwd()

    # Check if project already exists
    if (cwd / 'ravl_loops').exists():
        print(f"Error: RAVL project already exists in {cwd}")
        print("ravl_loops/ directory found.")
        sys.exit(1)

    print(f"Initializing RAVL project in: {cwd}")
    print()

    # Create directory structure
    (cwd / 'ravl_loops').mkdir()
    print("✓ Created ravl_loops/")

    # Create basic config
    config_dir = cwd / 'ravl_loops' / 'config'
    config_dir.mkdir(parents=True)

    config_file = config_dir / 'ravl.toml'
    config_file.write_text('''# RAVL Project Configuration
[project]
name = "My RAVL Project"
version = "1.0.0"
''')
    print("✓ Created ravl_loops/config/ravl.toml")

    # Create README
    readme = cwd / 'README.md'
    if not readme.exists():
        readme.write_text('''# RAVL Project

This is a RAVL (Reflect-Act-Verify-Learn) project.

## Getting Started

1. Create a new loop: `ravl --clone template_name ravl_loops/my_loop`
2. Run your loop: `ravl my_loop`
3. View loop health: `ravl --loop-health my_loop`

## Directory Structure

- `ravl_loops/` - Loop definitions (each loop stores its own learning artifacts)

Note: Loops create their own learning directories and output directories as needed.
''')
        print("✓ Created README.md")

    print()
    print("✅ RAVL project initialized successfully!")
    print()
    print("Next steps:")
    print("  1. Run 'ravl --config' to configure settings")
    print("  2. Run 'ravl --clone' to create your first loop")
    print("  3. Run 'ravl --list' to see available templates")


if __name__ == '__main__':
    main()
