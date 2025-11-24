#!/usr/bin/env python3
"""
RAVL Venv Initializer

Creates the framework venv with correct Python version and dependencies.
Called automatically by ravl-wrapper if venv doesn't exist.
"""

import sys
from pathlib import Path

# Add framework common directory to path
_script_dir = Path(__file__).parent
_common_dir = _script_dir.parent.parent / 'ravl' / 'common'
sys.path.insert(0, str(_common_dir))

from execution.venv_manager import VenvManager
from config.config_loader import load_framework_config

def main():
    """Create framework venv if it doesn't exist"""
    # Get venv path from config or use default
    config = load_framework_config()
    venv_path = Path(_script_dir).parent / 'venv'

    print(f"🔧 Initializing RAVL framework venv at {venv_path}...", file=sys.stderr)

    # Create venv with correct Python version
    venv_manager = VenvManager(venv_path)

    # Check if it already exists and is valid
    if venv_manager.exists():
        is_valid, issue = venv_manager.validate_venv()
        if is_valid:
            print(f"✅ Venv already exists and is valid", file=sys.stderr)
            return 0
        else:
            print(f"⚠️  Existing venv has issues: {issue}", file=sys.stderr)
            print(f"🔧 Recreating venv with correct Python version...", file=sys.stderr)
            success, error = venv_manager.delete()
            if not success:
                print(f"❌ Failed to delete old venv: {error}", file=sys.stderr)
                return 1

    # Create new venv
    success, error = venv_manager.create()
    if not success:
        print(f"❌ Failed to create venv: {error}", file=sys.stderr)
        return 1

    print(f"✅ Framework venv created successfully", file=sys.stderr)
    required_version = config.get('framework', {}).get('required_python_version', '3.12')
    print(f"   Python version: {required_version}", file=sys.stderr)
    print(f"   Path: {venv_path}", file=sys.stderr)
    return 0

if __name__ == '__main__':
    sys.exit(main())
