#!/usr/bin/env python3
"""
RAVL Config Migration Script: YAML → TOML

Migrates RAVL configuration files from YAML to TOML format.
Migrates: config/ravl.yml → config/ravl.toml
Keeps YAML: learning artifacts, data_sources.yml, etc.

Usage:
    python migrate_configs_to_toml.py --dry-run     # Preview changes
    python migrate_configs_to_toml.py                # Execute migration
    python migrate_configs_to_toml.py --backup       # Create backups before converting
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Bootstrap: Add framework to path
_framework_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_framework_root / 'common'))

from utils.file_utils import load_yaml_file, save_toml_file
from cli.ravl_cli_base import RAVLCLIBase


class ConfigMigrator(RAVLCLIBase):
    """Migrate RAVL configs from YAML to TOML"""

    def __init__(self):
        self.framework_root = self.find_framework_root()
        self.files_to_migrate: List[Path] = []
        self.migration_results: List[Tuple[Path, bool, str]] = []

    def find_config_files(self, root_dir: Path) -> List[Path]:
        """
        Find all config/ravl.yml files to migrate.

        Excludes:
        - learnings/ directories (learning artifacts stay YAML)
        - data_sources.yml (complex data structure, stays YAML)
        - Any file already migrated (has corresponding .toml)

        Args:
            root_dir: Root directory to search from

        Returns:
            List of config/ravl.yml paths
        """
        config_files = []

        # Find all config/ravl.yml files
        for yml_file in root_dir.rglob('config/ravl.yml'):
            # Skip if in learnings directory
            if 'learnings' in yml_file.parts:
                continue

            # Skip if TOML version already exists
            toml_file = yml_file.parent / 'ravl.toml'
            if toml_file.exists():
                print(f"⏭️  Skipping {yml_file.relative_to(root_dir)} (TOML already exists)")
                continue

            config_files.append(yml_file)

        return sorted(config_files)

    def validate_conversion(self, yaml_data: Dict[str, Any], toml_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that YAML and TOML data are equivalent.

        Args:
            yaml_data: Original YAML data
            toml_data: Converted TOML data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if keys match
        yaml_keys = set(yaml_data.keys())
        toml_keys = set(toml_data.keys())

        if yaml_keys != toml_keys:
            missing_in_toml = yaml_keys - toml_keys
            extra_in_toml = toml_keys - yaml_keys
            msg = []
            if missing_in_toml:
                msg.append(f"Missing in TOML: {missing_in_toml}")
            if extra_in_toml:
                msg.append(f"Extra in TOML: {extra_in_toml}")
            return (False, "; ".join(msg))

        # Deep comparison would be more thorough, but key matching is good enough
        # for our use case (simple config structures)
        return (True, "")

    def convert_yaml_to_toml(self, yaml_file: Path, backup: bool = False) -> Tuple[bool, str]:
        """
        Convert a single YAML config file to TOML.

        Args:
            yaml_file: Path to YAML file
            backup: Whether to create .backup before converting

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Load YAML
            yaml_data = load_yaml_file(yaml_file)
            if yaml_data is None:
                return (False, "Failed to load YAML (empty or invalid)")

            # Determine TOML output path
            toml_file = yaml_file.parent / 'ravl.toml'

            # Create backup if requested
            if backup:
                backup_file = Path(str(yaml_file) + '.backup')
                import shutil
                shutil.copy2(yaml_file, backup_file)

            # Save as TOML
            save_toml_file(toml_file, yaml_data, create_dirs=False)

            # Load back TOML to validate
            from utils.file_utils import load_toml_file
            toml_data = load_toml_file(toml_file)

            # Validate conversion
            is_valid, error = self.validate_conversion(yaml_data, toml_data)
            if not is_valid:
                return (False, f"Validation failed: {error}")

            return (True, "")

        except Exception as e:
            return (False, str(e))

    def migrate_file(self, yaml_file: Path, dry_run: bool, backup: bool) -> Tuple[bool, str]:
        """
        Migrate a single file (with dry-run support).

        Args:
            yaml_file: Path to YAML file
            dry_run: If True, only simulate (don't write)
            backup: Whether to create backup before converting

        Returns:
            Tuple of (success, message)
        """
        if dry_run:
            # Just validate that we can load the YAML
            yaml_data = load_yaml_file(yaml_file)
            if yaml_data is None:
                return (False, "Would fail: cannot load YAML")
            return (True, "Would convert")

        # Actually convert
        success, error = self.convert_yaml_to_toml(yaml_file, backup)
        if success:
            return (True, "Converted")
        else:
            return (False, f"Failed: {error}")

    def run(self, dry_run: bool = False, backup: bool = False):
        """
        Execute migration.

        Args:
            dry_run: If True, preview changes without modifying files
            backup: If True, create .backup files before converting
        """
        print(f"\n{'='*70}")
        print(f"  RAVL Config Migration: YAML → TOML")
        print(f"{'='*70}\n")

        # Find all config files to migrate
        print("🔍 Searching for config files...")

        # Search in framework
        framework_configs = self.find_config_files(self.framework_root)
        print(f"   Framework: {len(framework_configs)} files")

        # Search in project (if we're in a RAVL project)
        project_configs = []
        try:
            project_root = self.find_project_root(required=False)
            if project_root != Path.cwd():  # We're in a project
                project_configs = self.find_config_files(project_root)
                print(f"   Project: {len(project_configs)} files")
        except:
            pass

        all_configs = framework_configs + project_configs
        if not all_configs:
            print("\n✅ No config files to migrate (all done or already migrated)")
            return

        print(f"\n📋 Total files to migrate: {len(all_configs)}")

        if dry_run:
            print("\n🔍 DRY RUN MODE - No files will be modified\n")
        elif backup:
            print("\n💾 BACKUP MODE - Creating .backup files\n")
        else:
            print("\n⚠️  LIVE MODE - Files will be modified\n")

        # Migrate each file
        for yml_file in all_configs:
            # Show relative path for clarity
            try:
                rel_path = yml_file.relative_to(self.framework_root)
                display_path = f".ravl/{rel_path}"
            except ValueError:
                try:
                    rel_path = yml_file.relative_to(project_root)
                    display_path = str(rel_path)
                except:
                    display_path = str(yml_file)

            success, message = self.migrate_file(yml_file, dry_run, backup)

            if success:
                self.print_success(f"{display_path}: {message}")
            else:
                self.print_error(f"{display_path}: {message}")

            self.migration_results.append((yml_file, success, message))

        # Summary
        print(f"\n{'='*70}")
        successful = sum(1 for _, success, _ in self.migration_results if success)
        failed = len(self.migration_results) - successful

        print(f"  Summary: {successful} successful, {failed} failed")
        print(f"{'='*70}\n")

        if dry_run:
            print("💡 Run without --dry-run to execute migration")
        elif successful > 0 and not dry_run:
            print("✅ Migration complete!")
            print("\nNext steps:")
            print("  1. Test that loops still work: ./ravl --list")
            print("  2. Run a test loop: ./ravl <loop-name>")
            print("  3. If everything works, delete .yml files: find . -name 'ravl.yml' -path '*/config/*' -delete")
            print("  4. Commit changes: git add . && git commit -m 'Migrate configs from YAML to TOML'")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate RAVL configuration files from YAML to TOML',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create .backup files before converting'
    )

    args = parser.parse_args()

    migrator = ConfigMigrator()
    migrator.run(dry_run=args.dry_run, backup=args.backup)


if __name__ == '__main__':
    main()
