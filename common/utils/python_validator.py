#!/usr/bin/env python3
"""
Python Version Validator

Finds and validates Python installations for RAVL venv creation.
Ensures compatible Python versions are used based on framework configuration.
"""

import shutil
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


def _load_framework_config() -> Dict[str, Any]:
    """
    Load framework configuration from .ravl/config/ravl.yml

    Returns:
        Dict with framework configuration, including min/max Python versions
    """
    # Find .ravl directory (should be parent of this file's grandparent)
    script_dir = Path(__file__).parent  # .ravl/common/utils
    ravl_dir = script_dir.parent.parent  # .ravl
    config_file = ravl_dir / 'config' / 'ravl.yml'

    if not config_file.exists():
        # Fallback to hardcoded defaults if config not found
        return {
            'framework': {
                'min_python_version': '3.9',
                'max_python_version': '3.14',
                'required_python_version': '3.12'
            }
        }

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            return config
    except Exception:
        # Fallback to defaults on error
        return {
            'framework': {
                'min_python_version': '3.9',
                'max_python_version': '3.14',
                'required_python_version': '3.12'
            }
        }


def find_required_python(required_version: str = "3.14") -> Tuple[Optional[str], Optional[str]]:
    """
    Find the required Python version executable.

    Args:
        required_version: Python version to find (e.g., "3.14", "3.13")

    Returns:
        Tuple of (python_path, error_message)
        - On success: (path_to_python, None)
        - On failure: (None, error_message_with_installation_instructions)
    """
    # Try to find the specific Python version
    python_cmd = f"python{required_version}"
    python_path = shutil.which(python_cmd)

    if python_path:
        # Verify it's actually the right version
        is_valid, actual_version = validate_python_version(python_path, required_version)
        if is_valid:
            return (python_path, None)
        else:
            return (None, f"Found {python_cmd} but version is {actual_version}, not {required_version}")

    # Not found - generate helpful error message
    if sys.platform == "darwin":  # macOS
        install_cmd = f"brew install python@{required_version}"
    elif sys.platform == "linux":
        install_cmd = f"sudo apt-get install python{required_version}"
    else:  # Windows
        install_cmd = f"Download from python.org and install Python {required_version}"

    error_msg = (
        f"Python {required_version} not found.\n"
        f"  Install: {install_cmd}\n"
        f"  Or update .ravl/config/ravl.toml to specify an available Python version."
    )

    return (None, error_msg)


def validate_python_version(python_path: str, expected_version: str) -> Tuple[bool, str]:
    """
    Check if a Python executable matches the expected version.

    Args:
        python_path: Path to Python executable
        expected_version: Expected version string (e.g., "3.12")

    Returns:
        Tuple of (is_valid, actual_version_string)
    """
    try:
        result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Output format: "Python 3.12.7"
        version_output = result.stdout.strip() or result.stderr.strip()

        # Extract version number (e.g., "3.12.7" -> "3.12")
        if "Python" in version_output:
            full_version = version_output.split()[1]  # "3.12.7"
            major_minor = ".".join(full_version.split(".")[:2])  # "3.12"

            is_match = major_minor == expected_version
            return (is_match, full_version)

        return (False, "unknown")

    except Exception as e:
        return (False, f"error: {e}")


def check_python_compatibility(python_path: str) -> Tuple[bool, str]:
    """
    Check if a Python version is compatible with RAVL's dependencies.

    Reads min/max Python versions from framework config (.ravl/config/ravl.yml).
    This ensures configuration is the single source of truth for version requirements.

    Args:
        python_path: Path to Python executable

    Returns:
        Tuple of (is_compatible, version_or_warning)
    """
    # Load config to get version constraints
    config = _load_framework_config()
    framework_config = config.get('framework', {})

    # Parse version constraints from config
    min_version_str = framework_config.get('min_python_version', '3.9')
    max_version_str = framework_config.get('max_python_version', '3.14')

    # Extract major.minor from version strings
    min_parts = min_version_str.split('.')
    min_major = int(min_parts[0])
    min_minor = int(min_parts[1])

    max_parts = max_version_str.split('.')
    max_major = int(max_parts[0])
    max_minor = int(max_parts[1])

    try:
        result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        version_output = result.stdout.strip() or result.stderr.strip()

        if "Python" in version_output:
            full_version = version_output.split()[1]  # "3.12.7"
            parts = full_version.split(".")
            major = int(parts[0])
            minor = int(parts[1])

            # Check compatibility against config values
            if major == min_major == max_major:
                # Same major version - check minor range
                if min_minor <= minor <= max_minor:
                    return (True, full_version)
                elif minor < min_minor:
                    return (False, f"Python {full_version} is too old (minimum {min_version_str})")
                else:
                    return (False, f"Python {full_version} exceeds maximum supported version (use {min_version_str}-{max_version_str})")
            elif major < min_major:
                return (False, f"Python {full_version} is too old (minimum {min_version_str})")
            else:
                return (False, f"Python {full_version} exceeds maximum supported version (use {min_version_str}-{max_version_str})")

        return (False, "unknown version")

    except Exception as e:
        return (False, f"error checking version: {e}")


def get_venv_python_version(venv_path: Path) -> Optional[str]:
    """
    Get the Python version of an existing venv.

    Args:
        venv_path: Path to virtual environment directory

    Returns:
        Version string (e.g., "3.12.7") or None if can't determine
    """
    # Locate Python executable in venv
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        return None

    try:
        result = subprocess.run(
            [str(python_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        version_output = result.stdout.strip() or result.stderr.strip()

        if "Python" in version_output:
            return version_output.split()[1]  # "3.12.7"

        return None

    except Exception:
        return None
