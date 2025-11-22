#!/usr/bin/env python3
"""
Virtual Environment Manager

Handles venv lifecycle: detection, creation, activation, and dependency installation.
Abstracts away venv complexity from code execution.

Uses framework config to determine required Python version, ensuring compatibility
with dependencies (e.g., Anthropic library requires Python 3.9-3.13, not 3.14+).
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple

# Import Python version validator
import sys as _sys
_parent_dir = Path(__file__).parent.parent
_sys.path.insert(0, str(_parent_dir))
from utils.python_validator import find_required_python, get_venv_python_version, check_python_compatibility
from config.config_loader import load_framework_config
from cli.ravl_cli_base import RAVLCLIBase


class VenvManager:
    """
    Manages Python virtual environments for RAVL loops.

    Responsibilities:
    - Detect if venv exists at given path
    - Create venv if needed
    - Install requirements into venv
    - Get Python executable path for subprocess calls
    - Get activation command for shell scripts
    """

    def __init__(self, venv_path: Path):
        """
        Initialize venv manager

        Args:
            venv_path: Path to virtual environment directory
        """
        self.venv_path = Path(venv_path).resolve()
        self.python_executable = self._get_python_executable()
        self.pip_executable = self._get_pip_executable()
        self.has_uv = self._detect_uv()

    @staticmethod
    def _detect_uv() -> bool:
        """Check if UV is installed and available in PATH"""
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _create_venv_with_uv(self, python_version: str) -> Tuple[bool, Optional[str]]:
        """
        Create venv using UV (200x faster than Python's venv module)

        Args:
            python_version: Required Python version (e.g., "3.12")

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create parent directory if needed
            self.venv_path.parent.mkdir(parents=True, exist_ok=True)

            # UV can automatically install the required Python version
            cmd = ["uv", "venv", str(self.venv_path), "--python", python_version]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # UV is fast, 30s is plenty
            )

            if result.returncode != 0:
                return (False, f"UV venv creation failed: {result.stderr}")

            return (True, None)

        except subprocess.TimeoutExpired:
            return (False, "UV venv creation timed out")
        except Exception as e:
            return (False, f"Error creating venv with UV: {str(e)}")

    def _install_with_uv(self, requirements_path: Path, quiet: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Install requirements using UV (10-100x faster than pip)

        Args:
            requirements_path: Path to requirements.txt file
            quiet: If True, suppress output

        Returns:
            Tuple of (success, error_message)
        """
        if not requirements_path.exists():
            return (True, None)

        try:
            cmd = ["uv", "pip", "install", "-r", str(requirements_path)]

            if quiet:
                cmd.append("--quiet")

            # Set VIRTUAL_ENV to tell UV which venv to use
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(self.venv_path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                return (False, f"UV install failed: {result.stderr}")

            return (True, None)

        except subprocess.TimeoutExpired:
            return (False, "UV install timed out")
        except Exception as e:
            return (False, f"Error installing with UV: {str(e)}")

    def _get_python_executable(self) -> Path:
        """Get path to python executable in venv"""
        if sys.platform == "win32":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"

    def _get_pip_executable(self) -> Path:
        """Get path to pip executable in venv"""
        if sys.platform == "win32":
            return self.venv_path / "Scripts" / "pip.exe"
        else:
            return self.venv_path / "bin" / "pip"

    def exists(self) -> bool:
        """Check if venv already exists at this path"""
        return self.python_executable.exists()

    def create(self) -> Tuple[bool, Optional[str]]:
        """
        Create a new virtual environment and install RAVL framework.

        Uses UV if available (200x faster), falls back to Python's venv module.
        Uses the required Python version from framework config to ensure
        compatibility with dependencies.

        Returns:
            Tuple of (success, error_message)
            - If successful: (True, None)
            - If failed: (False, error_message)
        """
        try:
            # Load framework config to get required Python version
            config = load_framework_config()
            required_version = config.get('framework', {}).get('required_python_version', '3.12')

            # Prefer UV if available (much faster)
            if self.has_uv:
                print(f"📦 Creating venv with UV (Python {required_version})...")
                success, error = self._create_venv_with_uv(required_version)
                if success:
                    # Install RAVL framework in editable mode
                    success, error = self.install_framework()
                    if not success:
                        return (False, error)
                    return (True, None)
                else:
                    print(f"⚠️  UV venv creation failed, falling back to Python venv: {error}")

            # Fallback to traditional Python venv
            print(f"📦 Creating venv with Python's venv module...")

            # Find the required Python version
            python_path, error = find_required_python(required_version)
            if not python_path:
                return (False, f"Cannot create venv: {error}")

            # Create parent directory if needed
            self.venv_path.parent.mkdir(parents=True, exist_ok=True)

            # Create venv using the required Python version (not sys.executable)
            subprocess.run(
                [python_path, "-m", "venv", str(self.venv_path)],
                check=True,
                capture_output=True,
                timeout=60,
            )

            # Install RAVL framework in editable mode
            success, error = self.install_framework()
            if not success:
                return (False, error)

            return (True, None)

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to create venv at {self.venv_path}: {e.stderr.decode()}"
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Error creating venv: {str(e)}"
            return (False, error_msg)

    def detect_or_create(self) -> Tuple[bool, Optional[str]]:
        """
        Detect if venv exists, create if needed

        Returns:
            Tuple of (success, error_message)
        """
        if self.exists():
            # Venv exists, verify framework is installed
            if not self._is_framework_installed():
                success, error = self.install_framework()
                if not success:
                    return (False, error)
            return (True, None)

        return self.create()

    def _is_framework_installed(self) -> bool:
        """Check if RAVL framework is installed in this venv"""
        try:
            # Check if anthropic (key framework dependency) is importable
            result = subprocess.run(
                [str(self.python_executable), "-c", "import anthropic"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def install_framework(self) -> Tuple[bool, Optional[str]]:
        """
        Install RAVL framework in editable mode and its dependencies.

        This makes common.llm.llm_logger and other framework utilities available
        to generated code running in this venv.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Find framework root (works for both submodule and UV installation)
            framework_root = RAVLCLIBase.find_framework_root()

            # Check if pyproject.toml exists (modern package format)
            pyproject_toml = framework_root / "pyproject.toml"
            setup_py = framework_root / "setup.py"

            if not pyproject_toml.exists() and not setup_py.exists():
                return (False, f"RAVL framework package definition not found at {framework_root}")

            # Prefer UV if available (much faster)
            if self.has_uv:
                # UV pip install with editable mode
                cmd = ["uv", "pip", "install", "-e", str(framework_root), "--quiet"]

                # Set VIRTUAL_ENV to tell UV which venv to use
                env = os.environ.copy()
                env["VIRTUAL_ENV"] = str(self.venv_path)

                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    env=env,
                    timeout=120,
                )
            else:
                # Fallback to pip
                cmd = [str(self.pip_executable), "install", "-e", str(framework_root), "-q"]
                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    timeout=120,
                )

            # Also install framework requirements (pyyaml, anthropic, etc.)
            requirements_file = framework_root / "requirements.txt"
            if requirements_file.exists():
                success, error = self.install_requirements(requirements_file, quiet=True)
                if not success:
                    return (False, f"Framework installed but requirements failed: {error}")

            return (True, None)

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install RAVL framework: {e.stderr.decode()}"
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Error installing RAVL framework: {str(e)}"
            return (False, error_msg)

    def install_requirements(
        self, requirements_path: Path, quiet: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Install requirements into venv using UV (preferred) or pip (fallback)

        Args:
            requirements_path: Path to requirements.txt file
            quiet: If True, suppress output

        Returns:
            Tuple of (success, error_message)
        """
        if not requirements_path.exists():
            # No requirements to install
            return (True, None)

        # Prefer UV if available (10-100x faster)
        if self.has_uv:
            if not quiet:
                print(f"📦 Installing dependencies with UV...")
            success, error = self._install_with_uv(requirements_path, quiet=quiet)
            if success:
                return (True, None)
            else:
                if not quiet:
                    print(f"⚠️  UV install failed, falling back to pip: {error}")

        # Fallback to pip
        if not quiet:
            print(f"📦 Installing dependencies with pip...")

        try:
            cmd = [str(self.pip_executable), "install", "-r", str(requirements_path)]

            if quiet:
                cmd.append("-q")

            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=300,  # 5 minutes for large installs
            )

            return (True, None)

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install requirements: {e.stderr.decode()}"
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Error installing requirements: {str(e)}"
            return (False, error_msg)

    def get_activation_command(self) -> str:
        """
        Get shell command to activate venv

        Returns:
            Shell command (bash/zsh compatible)
        """
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "activate.bat")
        else:
            return f"source {self.venv_path / 'bin' / 'activate'}"

    def get_python_executable(self) -> str:
        """Get path to python executable (as string for subprocess calls)"""
        return str(self.python_executable)

    def get_pip_executable(self) -> str:
        """Get path to pip executable (as string for subprocess calls)"""
        return str(self.pip_executable)

    def get_environment_vars(self) -> dict:
        """
        Get environment variables for running code in venv

        Returns:
            Dictionary of environment variables with updated PATH and VIRTUAL_ENV
        """
        env = os.environ.copy()

        # Update PATH to prioritize venv binaries
        if sys.platform == "win32":
            bin_path = str(self.venv_path / "Scripts")
        else:
            bin_path = str(self.venv_path / "bin")

        env["PATH"] = f"{bin_path}{os.pathsep}{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(self.venv_path)

        # Remove CONDA settings if present (avoid conflicts)
        env.pop("CONDA_DEFAULT_ENV", None)
        env.pop("CONDA_PREFIX", None)

        return env

    def validate_venv(self) -> Tuple[bool, Optional[str]]:
        """
        Validate that existing venv uses compatible Python version.

        Checks if venv Python matches required version from framework config.
        If mismatch, venv should be deleted and recreated.

        Returns:
            Tuple of (is_valid, issue_description)
            - If valid: (True, None)
            - If invalid: (False, description_of_issue)
            - If doesn't exist: (False, "venv does not exist")
        """
        if not self.exists():
            return (False, "venv does not exist")

        # Get venv's Python version
        venv_version = get_venv_python_version(self.venv_path)
        if not venv_version:
            return (False, "could not determine venv Python version")

        # Check compatibility
        is_compatible, message = check_python_compatibility(str(self.python_executable))
        if not is_compatible:
            return (False, f"venv has incompatible Python {venv_version}: {message}")

        # Check if it matches required version from config
        config = load_framework_config()
        required_version = config.get('framework', {}).get('required_python_version', '3.12')

        # Extract major.minor from venv version
        venv_major_minor = ".".join(venv_version.split(".")[:2])

        if venv_major_minor != required_version:
            return (False, f"venv has Python {venv_version}, but {required_version} is required")

        return (True, None)

    def delete(self) -> Tuple[bool, Optional[str]]:
        """
        Delete the virtual environment directory.

        Used when venv needs to be recreated (e.g., wrong Python version).

        Returns:
            Tuple of (success, error_message)
        """
        if not self.venv_path.exists():
            return (True, None)  # Already gone

        try:
            shutil.rmtree(self.venv_path)
            return (True, None)

        except Exception as e:
            error_msg = f"Failed to delete venv at {self.venv_path}: {str(e)}"
            return (False, error_msg)
