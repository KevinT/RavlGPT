#!/usr/bin/env python3
"""
RAVL CLI Base Utilities

Shared utilities for all RAVL CLI tools.
"""

import sys
from pathlib import Path
from typing import Optional

# Add utils to path for logging
_utils_dir = Path(__file__).parent.parent / 'utils'
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))
from logging_utils import log_message


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
        log_message(f"✅ {message}", status='success', indent=0)

    @staticmethod
    def print_error(message: str):
        """Print error message with ❌"""
        log_message(f"❌ {message}", status='error', indent=0)

    @staticmethod
    def print_warning(message: str):
        """Print warning message with ⚠️"""
        log_message(f"⚠️  {message}", status='error', indent=0)

    @staticmethod
    def print_info(message: str):
        """Print info message with ℹ️"""
        log_message(f"ℹ️  {message}", status='info', indent=0)

    @staticmethod
    def print_header(message: str, emoji: str = "📚"):
        """Print header message"""
        log_message(f"\n{emoji} {message}\n", status='info', indent=0)

    @staticmethod
    def format_emoji(config: dict) -> str:
        """Extract emoji from config or return default"""
        return config.get('emoji', '🔄')

    @staticmethod
    def format_name(config: dict) -> str:
        """Extract formatted name from config"""
        return config.get('description', config.get('name', 'Unknown'))
