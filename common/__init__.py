"""
RAVL Common Framework

Auto-configures Python paths on import, eliminating the need for
manual path traversal in agent code.

Usage in agents:
    # Bootstrap project root first (only needed if not already in path)
    import sys
    from pathlib import Path
    _current = Path(__file__).resolve().parent
    while not (_current / '.ravl').exists():
        if _current == _current.parent:
            break
        _current = _current.parent
    if str(_current) not in sys.path:
        sys.path.insert(0, str(_current))

    # Now import framework - auto-configuration happens
    import ravl.common
    from ravl_base import BaseRAVLLoop
    from llm.llm_providers import LLMProviderFactory
"""

import sys
from pathlib import Path

# Auto-discover project root from framework location
_this_file = Path(__file__).resolve()  # .ravl/common/__init__.py
_common_dir = _this_file.parent         # .ravl/common/
_ravl_dir = _common_dir.parent          # .ravl/
_project_root = _ravl_dir.parent        # project root

# Ensure project root is in sys.path (for ravl package import)
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

# Ensure framework is in sys.path (idempotent)
_framework_path = str(_common_dir)
if _framework_path not in sys.path:
    sys.path.insert(0, _framework_path)

# Export paths for agents that need them
PROJECT_ROOT = _project_root
RAVL_DIR = _ravl_dir
RAVL_COMMON_DIR = _common_dir

# Convenience function for explicit setup (optional)
def setup_ravl_paths():
    """
    Explicitly setup RAVL paths.

    This is optional - paths are configured automatically on import.
    Call this if you want explicit control or to get path references.

    Returns:
        tuple: (project_root, ravl_dir, ravl_common_dir)
    """
    return PROJECT_ROOT, RAVL_DIR, RAVL_COMMON_DIR
