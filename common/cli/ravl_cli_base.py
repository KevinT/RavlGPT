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
        Find project root by looking for .ravl/ directory

        Searches up from start_path (or cwd) for a .ravl/ directory.
        If not found, falls back to the UV-installed framework directory.

        Args:
            start_path: Starting path for search (default: cwd)
            required: If True, raise error when not found. If False, return None.

        Returns:
            Path to project root (or framework installation root if outside project)

        Raises:
            RuntimeError: If .ravl/ directory not found and required=True (should never happen with fallback)
        """
        current = (start_path or Path.cwd()).resolve()

        # Search up for .ravl/ directory
        while current != current.parent:
            if (current / '.ravl').exists():
                return current
            current = current.parent

        # Not found in project hierarchy - fall back to framework installation directory
        # __file__ is this file (ravl_cli_base.py)
        # Use parents[N] to go up the directory tree:
        #   parents[0] = cli/, parents[1] = common/, parents[2] = .ravl/ OR site-packages/
        framework_dir = Path(__file__).resolve().parents[2]

        # Detect if running from source (.ravl/ directory) or installed package (site-packages/)
        if framework_dir.name == '.ravl' and (framework_dir / 'common').exists():
            # Running from source: .ravl/ directory exists
            # Return project root (parent of .ravl/)
            return framework_dir.parent
        elif (framework_dir / 'common').exists():
            # Running from installed package: flat structure in site-packages/
            # The framework_dir IS the root (no .ravl/ subdirectory)
            return framework_dir

        # Shouldn't reach here, but handle gracefully
        if required:
            raise RuntimeError(
                "Could not find RAVL framework (.ravl/ directory). "
                "Are you in a RAVL project?"
            )
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
