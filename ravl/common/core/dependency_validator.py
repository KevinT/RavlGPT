#!/usr/bin/env python3
"""
Dependency Validator

Validates that generated code only attempts to install whitelisted packages.
Enforces security by requiring explicit user approval for runtime pip installations.
"""

import re
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib
from pathlib import Path
from typing import Dict, Optional, Tuple, List


class DependencyValidator:
    """
    Validates generated code against a whitelist of approved dependencies.

    Responsibilities:
    - Scan generated code for pip install commands
    - Extract package names and versions
    - Resolve whitelist with inheritance (loop → parent → project)
    - Validate packages are approved and versions are in range
    - Provide helpful error messages for unapproved packages
    """

    def __init__(self, loop_dir: Path, project_root: Path):
        """
        Initialize validator

        Args:
            loop_dir: Path to the current loop directory
            project_root: Path to project root
        """
        self.loop_dir = loop_dir
        self.project_root = project_root

    def validate_generated_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that generated code only uses whitelisted dependencies

        Args:
            code: The generated Python code to validate

        Returns:
            Tuple of (is_valid, error_message)
            - If valid: (True, None)
            - If invalid: (False, helpful_error_message)
        """
        # Extract pip install commands from code
        pip_installs = self._extract_pip_installs(code)

        if not pip_installs:
            # No pip install commands, nothing to validate
            return (True, None)

        # Load whitelist
        whitelist = self._resolve_whitelist()
        if whitelist is None:
            return (
                False,
                self._error_no_whitelist()
            )

        # Validate each pip install
        for package_name, version in pip_installs:
            is_approved, error_msg = self._validate_package(
                package_name, version, whitelist
            )
            if not is_approved:
                return (False, error_msg)

        # All packages validated successfully
        return (True, None)

    def validate_requirements_file(self, requirements_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that requirements.txt only contains whitelisted packages

        Args:
            requirements_path: Path to generated requirements.txt

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not requirements_path.exists():
            return (True, None)

        # Read requirements file
        with open(requirements_path, 'r') as f:
            lines = f.readlines()

        # Load whitelist
        whitelist = self._resolve_whitelist()
        if whitelist is None:
            return (False, self._error_no_whitelist())

        # Parse each requirement line
        unapproved_packages = []
        for line in lines:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Parse package name and version
            # Format: "package==version" or "package"
            if '==' in line:
                package_name, version = line.split('==', 1)
            else:
                package_name = line
                version = "latest"

            # Validate against whitelist
            is_approved, error_msg = self._validate_package(
                package_name.strip(), version.strip(), whitelist
            )

            if not is_approved:
                unapproved_packages.append((package_name, version))

        # Return results
        if unapproved_packages:
            return (False, self._error_requirements_not_approved(unapproved_packages))

        return (True, None)

    def _extract_pip_installs(self, code: str) -> List[Tuple[str, str]]:
        """
        Extract pip install commands from code

        Returns:
            List of (package_name, version) tuples
        """
        installs = []

        # Pattern 1: subprocess.check_call(['pip', 'install', 'package==version'])
        pattern1 = r"subprocess\.check_call\(\s*\[.*?'pip'.*?'install'.*?'([^'=]+)(?:==([^']+))?'.*?\]\s*\)"
        # Pattern 2: subprocess.run(['pip', 'install', 'package==version'])
        pattern2 = r"subprocess\.run\(\s*\[.*?'pip'.*?'install'.*?'([^'=]+)(?:==([^']+))?'.*?\].*?\)"
        # Pattern 3: sys.executable, '-m', 'pip', 'install'
        pattern3 = r"\[.*?sys\.executable.*?'-m'.*?'pip'.*?'install'.*?'([^'=]+)(?:==([^']+))?'.*?\]"

        for pattern in [pattern1, pattern2, pattern3]:
            matches = re.finditer(pattern, code, re.DOTALL)
            for match in matches:
                package_name = match.group(1)
                version = match.group(2) if match.group(2) else "latest"
                installs.append((package_name, version))

        return installs

    def _resolve_whitelist(self) -> Optional[Dict[str, Dict[str, str]]]:
        """
        Resolve whitelist with inheritance model

        Resolution order:
        1. Loop-level config/ravl.toml (allowed_dependencies section)
        2. Parent loop config/ravl.toml (if nested)
        3. Project loops config ravl_loops/config/ravl.toml (project defaults)
        4. Framework config .ravl/config/framework_defaults.toml (framework defaults)

        Returns:
            Whitelist dict or None if not found anywhere
        """
        # Try loop-level ravl.toml
        loop_config_file = self.loop_dir / 'config' / 'ravl.toml'
        if loop_config_file.exists():
            whitelist = self._extract_allowed_dependencies(loop_config_file)
            if whitelist:
                return whitelist

        # Try parent loop (if nested)
        parent_path = self._find_parent_loop()
        if parent_path:
            parent_config_file = parent_path / 'config' / 'ravl.toml'
            if parent_config_file.exists():
                whitelist = self._extract_allowed_dependencies(parent_config_file)
                if whitelist:
                    return whitelist

        # Try project-level defaults (ravl_loops/config/ravl.toml)
        project_loops_config = self.project_root / 'ravl_loops' / 'config' / 'ravl.toml'
        if project_loops_config.exists():
            whitelist = self._extract_allowed_dependencies(project_loops_config)
            if whitelist:
                return whitelist

        # Try framework defaults (.ravl/config/framework_defaults.toml)
        framework_config = self.project_root / '.ravl' / 'config' / 'framework_defaults.toml'
        if framework_config.exists():
            whitelist = self._extract_allowed_dependencies(framework_config)
            if whitelist:
                return whitelist

        return None

    def _find_parent_loop(self) -> Optional[Path]:
        """
        Find parent loop if this is a nested loop

        Returns:
            Path to parent loop or None if top-level
        """
        # Count 'child_loops' in path
        child_loops_indices = [
            i for i, part in enumerate(self.loop_dir.parts)
            if part == 'child_loops'
        ]

        if len(child_loops_indices) >= 1:
            # Nested loop: parent is everything before the last 'child_loops'
            last_child_loops_idx = child_loops_indices[-1]
            parent_path = Path(*self.loop_dir.parts[:last_child_loops_idx])
            return parent_path

        return None

    def _extract_allowed_dependencies(self, ravl_yml_file: Path) -> Optional[Dict[str, Dict[str, str]]]:
        """
        Extract allowed_dependencies section from a ravl.toml file

        Args:
            ravl_yml_file: Path to ravl.toml

        Returns:
            Whitelist dict (allowed_dependencies section) or None if not present or error
        """
        try:
            with open(ravl_yml_file, 'rb') as f:
                config = tomllib.load(f) or {}
            return config.get('allowed_dependencies')
        except Exception:
            return None

    def _validate_package(
        self, package_name: str, version: str, whitelist: Dict[str, Dict[str, str]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a single package against whitelist

        Args:
            package_name: Name of package (e.g., 'google-api-python-client')
            version: Version string (e.g., '2.100.0' or 'latest')
            whitelist: Loaded whitelist dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if package is on whitelist
        if package_name not in whitelist:
            return (False, self._error_package_not_approved(package_name, version))

        # Get whitelist entry
        entry = whitelist[package_name]
        if not isinstance(entry, dict):
            # Simple entry without version constraints
            return (True, None)

        # Check version constraints if specified
        min_version = entry.get('min_version')
        max_version = entry.get('max_version')

        if version == 'latest':
            # 'latest' is always allowed if package is on whitelist
            return (True, None)

        if min_version or max_version:
            if not self._is_version_in_range(version, min_version, max_version):
                return (
                    False,
                    self._error_version_out_of_range(
                        package_name, version, min_version, max_version
                    )
                )

        return (True, None)

    def _is_version_in_range(
        self, version: str, min_v: Optional[str], max_v: Optional[str]
    ) -> bool:
        """
        Check if version is in range

        Args:
            version: Version to check (e.g., '2.100.0')
            min_v: Minimum version or None
            max_v: Maximum version or None

        Returns:
            True if in range
        """
        try:
            v_parts = [int(x) for x in version.split('.')[:3]]
            v_tuple = tuple(v_parts + [0] * (3 - len(v_parts)))

            if min_v:
                min_parts = [int(x) for x in min_v.split('.')[:3]]
                min_tuple = tuple(min_parts + [0] * (3 - len(min_parts)))
                if v_tuple < min_tuple:
                    return False

            if max_v:
                max_parts = [int(x) for x in max_v.split('.')[:3]]
                max_tuple = tuple(max_parts + [0] * (3 - len(max_parts)))
                if v_tuple > max_tuple:
                    return False

            return True
        except (ValueError, AttributeError):
            # If version parsing fails, reject it (safer default)
            return False

    def _error_no_whitelist(self) -> str:
        """Generate error message when no whitelist found"""
        search_locations = [
            f"  - Loop config: {self.loop_dir / 'config' / 'ravl.toml'} (allowed_dependencies section)",
            f"  - Project config: {self.project_root / 'ravl_loops' / 'config' / 'ravl.toml'} (allowed_dependencies section)",
            f"  - Framework config: {self.project_root / '.ravl' / 'config' / 'ravl.toml'} (allowed_dependencies section)"
        ]

        parent = self._find_parent_loop()
        if parent:
            search_locations.insert(
                1,
                f"  - Parent config: {parent / 'config' / 'ravl.toml'} (allowed_dependencies section)"
            )

        return f"""❌ Dependency whitelist not found

Generated code requires pip to install packages, but no allowed_dependencies
section was found in ravl.toml files at these locations:

{chr(10).join(search_locations)}

To fix this, add an allowed_dependencies section to config/ravl.toml:

  allowed_dependencies:
    google-api-python-client:
      min_version: '2.100.0'
      max_version: '2.120.0'
    requests:
      min_version: '2.31.0'

Or add it to the project-level ravl_loops/config/ravl.toml if you want all loops to use it.

Then run the loop again."""

    def _error_package_not_approved(self, package_name: str, version: str) -> str:
        """Generate error message for unapproved package (user-friendly)"""
        whitelist_path = self._find_whitelist_path()
        return f"""❌ Package Not Approved: {package_name}

Your loop needs the '{package_name}' package, but you haven't approved it yet.

HOW TO FIX:
1. Open: {whitelist_path}
2. Find the 'allowed_dependencies:' section
3. Add these lines (keep the indentation):

   {package_name}:
     min_version: '{version}'
     max_version: '9.9.9'

4. Save the file
5. Run the loop again

WHY THIS STEP?
This helps you control what packages your loop uses. It's a safety check to
ensure you're only allowing packages you trust.

NEED HELP WITH VERSIONS?
- min_version: The oldest version that will work ({version} in this case)
- max_version: Prevents installing a version that might break things
- Using '{version}' to '9.9.9' allows patch updates while staying safe
"""

    def _error_version_out_of_range(
        self, package_name: str, version: str, min_v: Optional[str], max_v: Optional[str]
    ) -> str:
        """Generate error message for version out of range (user-friendly)"""
        range_str = f"{min_v or '0.0.0'} - {max_v or 'latest'}"
        whitelist_path = self._find_whitelist_path()
        return f"""❌ Version Not Approved: {package_name} v{version}

Your loop needs version {version}, but the approved range is: {range_str}

HOW TO FIX:
1. Open: {whitelist_path}
2. Find '{package_name}' in the 'allowed_dependencies:' section
3. Update the version range to include {version}:

   {package_name}:
     min_version: '{min_v or version}'
     max_version: '{max_v or '9.9.9'}'

4. Save the file
5. Run the loop again

WHAT HAPPENED?
Different versions of the same package can have different features or bugs.
The approved version range prevents problems from old or new versions.
"""

    def _error_requirements_not_approved(self, packages: List[Tuple[str, str]]) -> str:
        """Generate helpful error for unapproved packages in requirements.txt"""
        config_path = self.loop_dir / 'config' / 'ravl.toml'

        package_list = "\n".join([f"  - {name} (version: {ver})" for name, ver in packages])

        return f"""❌ Generated code requires packages that are not approved:

{package_list}

To approve these packages, add them to the whitelist in:
  {config_path}

Example configuration:

[allowed_dependencies.{packages[0][0]}]
min_version = "{packages[0][1]}"
max_version = "999.0.0"  # Adjust as needed

After adding to whitelist, run the loop again.
"""

    def _find_whitelist_path(self) -> Path:
        """Find which ravl.toml file contains the whitelist (for error messages)"""
        loop_config = self.loop_dir / 'config' / 'ravl.toml'
        if loop_config.exists() and self._extract_allowed_dependencies(loop_config):
            return loop_config

        parent = self._find_parent_loop()
        if parent:
            parent_config = parent / 'config' / 'ravl.toml'
            if parent_config.exists() and self._extract_allowed_dependencies(parent_config):
                return parent_config

        # Return the most relevant location for the error message
        return self.loop_dir / 'config' / 'ravl.toml'
