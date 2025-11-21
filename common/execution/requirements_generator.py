#!/usr/bin/env python3
"""
Requirements Generator

Analyzes generated Python code and extracts package imports to create requirements.txt.
Handles package name mapping (e.g., import google_auth_oauthlib -> package google-auth-oauthlib).
Optionally generates lock files using UV for reproducible dependency resolution.
"""

import re
import subprocess
from pathlib import Path
from typing import Set, Dict, Optional, Tuple


class RequirementsGenerator:
    """
    Generates requirements.txt from generated Python code.

    Maps Python import names to PyPI package names and tracks versions.
    """

    # Map of Python import names to PyPI package names
    IMPORT_TO_PACKAGE_MAP = {
        "common": "ravl-framework",  # RAVL framework utilities (llm_logger, etc.)
        "google": "google-api-python-client",
        "google_auth_oauthlib": "google-auth-oauthlib",
        "google_auth_httplib2": "google-auth-httplib2",
        "googleapiclient": "google-api-python-client",
        "google.oauth2": "google-auth",
        "google_auth": "google-auth",
        "requests": "requests",
        "anthropic": "anthropic",
        "yaml": "pyyaml",
        "PIL": "pillow",
        "cv2": "opencv-python",
        "bs4": "beautifulsoup4",
        "dotenv": "python-dotenv",
    }

    # Package versions (can be inferred from imports)
    DEFAULT_VERSIONS = {
        "ravl-framework": "0.1.0",  # RAVL framework (installed in editable mode)
        "google-api-python-client": "2.100.0",
        "google-auth": "2.30.0",
        "google-auth-oauthlib": "1.0.0",
        "google-auth-httplib2": "0.2.0",
        "requests": "2.31.0",
        "anthropic": "0.25.0",
        "pyyaml": "6.0.1",
        "pillow": "10.0.0",
        "opencv-python": "4.8.0",
        "beautifulsoup4": "4.12.0",
        "python-dotenv": "1.0.0",
    }

    @staticmethod
    def extract_imports(code: str) -> Set[str]:
        """
        Extract import statements from Python code

        Args:
            code: Python code as string

        Returns:
            Set of imported module names
        """
        imports = set()

        # Pattern 1: from X import Y (extract module name X)
        pattern1 = r"from\s+([\w\.]+)\s+import"
        for match in re.finditer(pattern1, code):
            module = match.group(1)
            imports.add(module.split(".")[0])

        # Pattern 2: import X (standalone imports, not from...import)
        # This regex matches "import X" only at start of line or after semicolon
        pattern2 = r"(?:^|;|\n)\s*import\s+([\w\.]+)"
        for match in re.finditer(pattern2, code, re.MULTILINE):
            module = match.group(1)
            # Skip standard library and local imports
            if not module.startswith("_"):
                imports.add(module.split(".")[0])

        return imports

    @staticmethod
    def map_to_packages(imports: Set[str]) -> Dict[str, str]:
        """
        Map import names to PyPI package names and versions

        Args:
            imports: Set of Python import names

        Returns:
            Dictionary of {package_name: version}
        """
        packages = {}

        for import_name in imports:
            # Skip local framework modules (ravl.*)
            # These are provided by the framework itself, not PyPI
            if import_name == "ravl" or import_name.startswith("ravl."):
                continue

            # Skip standard library modules
            if RequirementsGenerator._is_stdlib(import_name):
                continue

            # Try exact match first
            if import_name in RequirementsGenerator.IMPORT_TO_PACKAGE_MAP:
                package = RequirementsGenerator.IMPORT_TO_PACKAGE_MAP[import_name]

                # Skip ravl-framework - provided by execution environment
                if package == "ravl-framework":
                    continue

                version = RequirementsGenerator.DEFAULT_VERSIONS.get(package, "latest")
                packages[package] = version
            else:
                # Try heuristic: convert underscores to hyphens for PyPI
                package_name = import_name.replace("_", "-").lower()
                # Only add if it looks like a real package
                if len(package_name) > 2:
                    packages[package_name] = "latest"

        return packages

    @staticmethod
    def _is_stdlib(module_name: str) -> bool:
        """Check if module is Python standard library"""
        stdlib_modules = {
            "os", "sys", "re", "json", "yaml", "pickle", "datetime",
            "pathlib", "subprocess", "logging", "typing", "collections",
            "itertools", "functools", "io", "shutil", "tempfile", "random",
            "math", "statistics", "decimal", "fractions", "hashlib", "hmac",
            "base64", "codecs", "struct", "difflib", "string", "textwrap",
            "unicodedata", "bisect", "heapq", "queue", "threading", "multiprocessing",
            "socket", "ssl", "select", "email", "http", "urllib", "ftplib",
            "poplib", "imaplib", "smtplib", "uuid", "socketserver", "xmlrpc",
            "ipaddress", "argparse", "getopt", "unittest", "doctest",
            "pydoc", "ast", "symtable", "token", "keyword", "tokenize",
            "inspect", "types", "copy", "pprint", "reprlib", "enum",
            "dataclasses", "contextlib", "abc", "importlib", "pkgutil",
            "builtins", "warnings", "weakref", "array", "mmap",
            "glob", "fnmatch", "csv", "time", "traceback",
            "gzip", "bz2", "lzma", "zipfile", "tarfile", "configparser",
        }
        return module_name.lower() in stdlib_modules

    @staticmethod
    def generate_requirements(code: str) -> str:
        """
        Generate requirements.txt content from Python code

        Args:
            code: Generated Python code

        Returns:
            Requirements.txt content as string
        """
        imports = RequirementsGenerator.extract_imports(code)
        packages = RequirementsGenerator.map_to_packages(imports)

        # Sort packages alphabetically
        lines = [
            "# Auto-generated by RAVL - do not edit directly",
            "# This is used to install dependencies when the loop runs",
            "# Approval is controlled by allowed_dependencies in config/ravl.yml",
            "",
        ]

        for package in sorted(packages.keys()):
            version = packages[package]
            if version == "latest":
                lines.append(package)
            else:
                lines.append(f"{package}=={version}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def save_requirements(code: str, output_path: Path) -> bool:
        """
        Generate and save requirements.txt

        Args:
            code: Generated Python code
            output_path: Path to save requirements.txt

        Returns:
            True if successful, False otherwise
        """
        try:
            requirements_content = RequirementsGenerator.generate_requirements(code)

            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write requirements file
            with open(output_path, "w") as f:
                f.write(requirements_content)

            return True

        except Exception as e:
            print(f"Error generating requirements: {str(e)}")
            return False

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

    @staticmethod
    def generate_lock_file(requirements_path: Path, quiet: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Generate lock file from requirements.txt using UV

        Creates a .lock file with pinned dependencies for reproducible installs.
        Only works if UV is available - silently skips otherwise.

        Args:
            requirements_path: Path to requirements.txt file
            quiet: If True, suppress output

        Returns:
            Tuple of (success, error_message)
            - If UV not available: (True, None) - silently succeeds
            - If successful: (True, None)
            - If failed: (False, error_message)
        """
        # Check if UV is available
        if not RequirementsGenerator._detect_uv():
            # UV not available - this is OK, lock files are optional
            return (True, None)

        if not requirements_path.exists():
            # No requirements file - nothing to lock
            return (True, None)

        try:
            lock_path = requirements_path.with_suffix(".lock")

            # UV pip compile generates a lock file with pinned versions
            cmd = ["uv", "pip", "compile", str(requirements_path), "-o", str(lock_path)]

            if quiet:
                cmd.append("--quiet")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout
            )

            if result.returncode != 0:
                return (False, f"UV lock file generation failed: {result.stderr}")

            return (True, None)

        except subprocess.TimeoutExpired:
            return (False, "UV lock file generation timed out")
        except Exception as e:
            return (False, f"Error generating lock file: {str(e)}")
