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
    def find_project_root(start_path: Optional[Path] = None, required: bool = True) -> Optional[Path]:
        """
        Find existing RAVL project root by looking for .ravl/ directory

        **IMPORTANT - SINGLE POINT OF TRUTH:**
        This finds where USER content (loops, data) lives, NOT where framework code lives.
        Framework code location is discovered via Python imports (doesn't need to be at project root).

        Searches up from start_path (or cwd) for a .ravl/ directory.
        Returns None if not found and required=False.

        Args:
            start_path: Starting path for search (default: cwd)
            required: If True, raise error when not found. If False, return None.

        Returns:
            Path to existing project root (directory containing .ravl/), or None if not found.
            When None, caller should use CWD as project root for creating new content.

        Raises:
            RuntimeError: If .ravl/ directory not found and required=True
        """
        current = (start_path or Path.cwd()).resolve()

        # Search up for .ravl/ directory
        while current != current.parent:
            if (current / '.ravl').exists():
                return current
            current = current.parent

        # Not found in project hierarchy
        # Don't fall back to framework installation - that's where framework code lives,
        # not where user content should be created!
        if required:
            raise RuntimeError(
                "Could not find RAVL project (.ravl/ directory). "
                "Are you in a RAVL project?"
            )

        # Return None to let caller use CWD as project root for user content
        return None

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
        """Print header message without status prefix"""
        # Print blank line before header
        print("", file=sys.stderr, flush=True)
        # Print header directly without [i] prefix
        if emoji:
            print(f" {emoji} {message}", file=sys.stderr, flush=True)
        else:
            print(f" {message}", file=sys.stderr, flush=True)
        # Print blank line after header
        print("", file=sys.stderr, flush=True)

    @staticmethod
    def format_emoji(config: dict) -> str:
        """Extract emoji from config or return default"""
        return config.get('emoji', '🔄')

    @staticmethod
    def format_name(config: dict) -> str:
        """Extract formatted name from config"""
        return config.get('description', config.get('name', 'Unknown'))
