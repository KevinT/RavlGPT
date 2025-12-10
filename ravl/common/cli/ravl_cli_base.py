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
    def find_project_root(start_path: Optional[Path] = None, required: bool = True) -> Path:
        """
        Find RAVL project root by looking for ravl_loops/ directory.

        **IMPORTANT - SINGLE POINT OF TRUTH:**
        This finds where USER content (loops, data) lives, NOT where framework code lives.
        A RAVL project is identified by the presence of ravl_loops/ directory.
        Framework code location is discovered via Python imports (doesn't need to be at project root).

        Note: .ravl/ directory does NOT exist in UV installations and is optional even in
        submodule installs. The correct project marker is ravl_loops/.

        Args:
            start_path: Starting path for search (default: cwd)
            required: If True, raise error when ravl_loops/ not found.
                     If False, return CWD as default project root.

        Returns:
            Path to project root (directory containing ravl_loops/),
            or CWD if ravl_loops/ not found and required=False.

        Raises:
            RuntimeError: If ravl_loops/ directory not found and required=True
        """
        current = (start_path or Path.cwd()).resolve()

        # Search up for ravl_loops/ directory (project marker)
        while current != current.parent:
            if (current / 'ravl_loops').exists():
                return current
            current = current.parent

        # Not found
        if required:
            raise RuntimeError(
                "Could not find RAVL project (no ravl_loops/ directory). "
                "Are you in a RAVL project? Use 'ravl --init' to create one."
            )

        # Fallback: CWD for commands that don't need a project
        return Path.cwd().resolve()

    @staticmethod
    def find_framework_root() -> Path:
        """
        Find framework installation root (where framework code lives).

        **IMPORTANT - SEPARATE FROM PROJECT ROOT:**
        This finds where FRAMEWORK code lives, NOT where user content lives.
        Framework location is discovered via Python imports (__file__).

        Works identically for:
        - Submodule installation: Returns path to .ravl/ directory
        - UV installation: Returns path to site-packages directory

        Returns:
            Path to framework root directory
        """
        # This file is at: ravl/common/cli/ravl_cli_base.py
        # Framework root is 3 levels up: ravl/common/cli/ → ravl/common/ → ravl/ → .ravl/
        return Path(__file__).resolve().parent.parent.parent.parent

    @staticmethod
    def get_installation_type() -> str:
        """
        Detect how RAVL is installed.

        Returns:
            'submodule': Installed as .ravl git submodule
            'package': Installed via UV/pip as Python package
        """
        try:
            import ravl
            framework_path = Path(ravl.__file__).parent.parent

            # Check if we're in a .ravl directory structure
            if framework_path.name == '.ravl' or '.ravl' in framework_path.parts:
                return 'submodule'
            return 'package'
        except ImportError:
            # Fallback: check if we're running from source
            framework_root = RAVLCLIBase.find_framework_root()
            if framework_root.name == '.ravl':
                return 'submodule'
            return 'package'

    @staticmethod
    def get_config_path() -> Path:
        """
        Get configuration file path based on installation type.

        Returns:
            Submodule: <project>/.ravl/config/llm.toml
            Package: ~/.config/ravl/llm.toml
        """
        install_type = RAVLCLIBase.get_installation_type()

        if install_type == 'submodule':
            # Find project root and use .ravl/ if it exists
            try:
                project_root = RAVLCLIBase.find_project_root(required=False)
                ravl_dir = project_root / '.ravl' / 'config'
                if ravl_dir.exists():
                    return ravl_dir / 'llm.toml'
            except Exception:
                pass

        # Package install or fallback: Use user config directory
        config_dir = Path.home() / '.config' / 'ravl'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'llm.toml'

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
