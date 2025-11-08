#!/usr/bin/env python3
"""
RAVL CLI Base Utilities

Shared utilities for all RAVL CLI tools.
"""

import sys
from pathlib import Path
from typing import Optional


class RAVLCLIBase:
    """Base class with shared utilities for RAVL CLI tools"""

    @staticmethod
    def find_project_root(start_path: Optional[Path] = None) -> Path:
        """
        Find project root by looking for .ravl/ directory

        Args:
            start_path: Starting path for search (default: cwd)

        Returns:
            Path to project root

        Raises:
            RuntimeError: If .ravl/ directory not found
        """
        current = (start_path or Path.cwd()).resolve()

        while current != current.parent:
            if (current / '.ravl').exists():
                return current
            current = current.parent

        raise RuntimeError(
            "Could not find RAVL framework (.ravl/ directory). "
            "Are you in a RAVL project?"
        )

    @staticmethod
    def print_success(message: str):
        """Print success message with ✅"""
        print(f"✅ {message}", file=sys.stderr)

    @staticmethod
    def print_error(message: str):
        """Print error message with ❌"""
        print(f"❌ {message}", file=sys.stderr)

    @staticmethod
    def print_warning(message: str):
        """Print warning message with ⚠️"""
        print(f"⚠️  {message}", file=sys.stderr)

    @staticmethod
    def print_info(message: str):
        """Print info message with ℹ️"""
        print(f"ℹ️  {message}", file=sys.stderr)

    @staticmethod
    def print_header(message: str, emoji: str = "📚"):
        """Print header message"""
        print(f"\n{emoji} {message}\n", file=sys.stderr)

    @staticmethod
    def format_emoji(config: dict) -> str:
        """Extract emoji from config or return default"""
        return config.get('emoji', '🔄')

    @staticmethod
    def format_name(config: dict) -> str:
        """Extract formatted name from config"""
        return config.get('description', config.get('name', 'Unknown'))
