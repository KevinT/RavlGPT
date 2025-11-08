#!/usr/bin/env python3
"""
Python Version Validator

Finds and validates Python installations for RAVL venv creation.
Ensures compatible Python versions are used (avoiding Python 3.14+ which has
dependency compatibility issues with Anthropic/Pydantic).
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def find_required_python(required_version: str = "3.12") -> Tuple[Optional[str], Optional[str]]:
    """
    Find the required Python version executable.

    Args:
        required_version: Python version to find (e.g., "3.12", "3.11")

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
        f"  Or update .ravl/config/ravl.yml to specify an available Python version."
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

    Currently: Python 3.9-3.13 are compatible, 3.14+ have issues with Anthropic library.

    Args:
        python_path: Path to Python executable

    Returns:
        Tuple of (is_compatible, version_or_warning)
    """
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

            # Check compatibility
            if major == 3 and 9 <= minor <= 13:
                return (True, full_version)
            elif major == 3 and minor >= 14:
                return (False, f"Python {full_version} has compatibility issues (use 3.9-3.13)")
            else:
                return (False, f"Python {full_version} is too old (minimum 3.9)")

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
