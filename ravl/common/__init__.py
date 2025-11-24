"""
RAVL Common Framework

Auto-configures framework paths on import.
"""

import sys
from pathlib import Path

# Discover framework root from this file's location
_this_file = Path(__file__).resolve()  # common/__init__.py
_common_dir = _this_file.parent         # common/
_framework_root = _common_dir.parent    # Framework root

# Add framework common/ to sys.path for imports
if str(_common_dir) not in sys.path:
    sys.path.insert(0, str(_common_dir))
