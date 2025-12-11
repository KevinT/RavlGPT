#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
Interactive Dependency Approver

Provides interactive workflow for approving unapproved dependencies during loop execution.
When `--interactive` flag is set, prompts user to approve dependencies in batch and
automatically updates config files with appropriate version constraints.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict

try:
    import tomllib
except ImportError:
    import tomli as tomllib

import tomli_w


class InteractiveDependencyApprover:
    """
    Handles interactive approval workflow for unapproved dependencies.

    When a loop requires packages not yet in the whitelist, this class:
    1. Displays a formatted batch approval prompt
    2. Collects user approval (y/n)
    3. Writes approved packages to loop config with major version ranges
    """

    def __init__(self, loop_dir: Path, validator):
        """
        Initialize interactive dependency approver.

        Args:
            loop_dir: Path to loop directory
            validator: DependencyValidator instance for whitelist checking
        """
        self.loop_dir = Path(loop_dir)
        self.validator = validator

    def get_unapproved_packages(self, requirements_path: Path) -> List[Tuple[str, str]]:
        """
        Extract unapproved packages from requirements.txt file.

        Args:
            requirements_path: Path to generated requirements.txt

        Returns:
            List of (package_name, version) tuples for unapproved packages
        """
        # Delegate to validator which has whitelist resolution logic
        return self.validator.get_unapproved_packages(requirements_path)

    def prompt_for_approval(self, packages: List[Tuple[str, str]]) -> Optional[Dict[str, str]]:
        """
        Display approval prompt and get user response.

        Args:
            packages: List of (package_name, version) tuples needing approval

        Returns:
            Dict mapping package_name to version if approved, None if declined
        """
        if not packages:
            return {}

        # Display the approval prompt
        self._display_approval_prompt(packages)

        # Get user input
        try:
            response = input("Approve these packages? [y/N]: ").strip().lower()

            if response in ['y', 'yes']:
                # Convert list to dict for return
                return {pkg: ver for pkg, ver in packages}
            else:
                return None

        except (KeyboardInterrupt, EOFError):
            # Handle Ctrl+C or Ctrl+D gracefully
            print("\n\n❌ Approval cancelled by user.", file=sys.stderr)
            return None

    def write_approvals(self, packages: Dict[str, str]) -> Tuple[bool, str]:
        """
        Write approved packages to config/ravl.toml with version constraints.

        Args:
            packages: Dict mapping package_name to version

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            config_path = self._get_config_path()

            # Read existing config or create new one
            if config_path.exists():
                with open(config_path, 'rb') as f:
                    config = tomllib.load(f)
            else:
                config = {}

            # Ensure allowed_dependencies section exists
            if 'allowed_dependencies' not in config:
                config['allowed_dependencies'] = {}

            # Add each package with version constraints
            for package_name, version in packages.items():
                min_version, max_version = self._calculate_version_range(version)

                config['allowed_dependencies'][package_name] = {
                    'min_version': min_version,
                    'max_version': max_version
                }

            # Write back to file
            with open(config_path, 'wb') as f:
                tomli_w.dump(config, f)

            return (True, "")

        except PermissionError as e:
            return (False, f"Permission denied writing to {config_path}: {e}")
        except Exception as e:
            return (False, f"Error writing approvals: {e}")

    def _calculate_version_range(self, version: str) -> Tuple[str, str]:
        """
        Calculate major version range from a version string.

        Args:
            version: Version string (e.g., "1.2.3", "60.2", "latest")

        Returns:
            Tuple of (min_version, max_version)

        Examples:
            "1.2.3" → ("1.2.3", "1.999.999")
            "60.2" → ("60.2", "60.999.999")
            "latest" → ("0.0.0", "999.999.999")
        """
        if version == "latest":
            # For latest, allow any version
            return ("0.0.0", "999.999.999")

        # Parse version parts
        parts = version.split('.')

        if len(parts) == 0:
            # Invalid version, default to wide range
            return (version, "999.999.999")

        try:
            major = parts[0]

            # Min version is the detected version
            min_version = version

            # Max version allows any minor/patch within same major
            max_version = f"{major}.999.999"

            return (min_version, max_version)

        except (ValueError, IndexError):
            # If parsing fails, return original version with wide max
            return (version, "999.999.999")

    def _display_approval_prompt(self, packages: List[Tuple[str, str]]) -> None:
        """
        Display formatted approval prompt to stderr.

        Args:
            packages: List of (package_name, version) tuples to display
        """
        print("\n", file=sys.stderr)
        print("🔐 DEPENDENCY APPROVAL REQUIRED", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"Your loop requires {len(packages)} package(s) that are not yet approved:\n", file=sys.stderr)

        # List packages with numbers
        for idx, (package_name, version) in enumerate(packages, 1):
            # Right-pad package name for alignment
            padded_name = package_name.ljust(30)
            print(f"  {idx}. {padded_name} (version: {version})", file=sys.stderr)

        print("\n" + "-" * 70, file=sys.stderr)
        print("VERSION CONSTRAINTS (major version range):", file=sys.stderr)

        for package_name, version in packages:
            min_ver, max_ver = self._calculate_version_range(version)
            print(f"  • {package_name} {version} → allows {min_ver} to {max_ver}", file=sys.stderr)

        print("\n" + "-" * 70, file=sys.stderr)
        print("SECURITY NOTE: Only approve packages you trust.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("", file=sys.stderr)

    def display_success_message(self, packages: Dict[str, str]) -> None:
        """
        Display success message after approval.

        Args:
            packages: Dict of approved packages
        """
        config_path = self._get_config_path()

        print("\n", file=sys.stderr)
        print("✅ PACKAGES APPROVED", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(f"Approved {len(packages)} package(s) and saved to:", file=sys.stderr)
        print(f"  {config_path}", file=sys.stderr)
        print("\n" + "-" * 70, file=sys.stderr)
        print("NEXT STEPS:", file=sys.stderr)
        print("  • Installing approved packages...", file=sys.stderr)
        print("  • Continuing with loop execution...", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print("", file=sys.stderr)

    def _get_config_path(self) -> Path:
        """
        Get path to loop-level config file, creating parent dirs if needed.

        Returns:
            Path to config/ravl.toml in loop directory
        """
        config_dir = self.loop_dir / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)

        return config_dir / 'ravl.toml'
