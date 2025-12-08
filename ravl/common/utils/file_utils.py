"""File I/O utilities for RAVL framework

Consolidates common file operations (YAML, JSON, TOML loading/saving) to reduce duplication.
"""

import json
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

# TOML support: use tomllib (Python 3.11+) or tomli (fallback)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# TOML writing support
try:
    import tomli_w
except ImportError:
    tomli_w = None


def load_yaml_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load and parse a YAML file.

    Args:
        file_path: Path to YAML file to load

    Returns:
        Parsed YAML content as dict, or None if file doesn't exist
    """
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise IOError(f"Failed to load YAML file {file_path}: {e}")


def save_yaml_file(file_path: Path, data: Dict[str, Any], create_dirs: bool = True):
    """
    Save data to a YAML file.

    Args:
        file_path: Path where YAML should be saved
        data: Data to save
        create_dirs: Whether to create parent directories if needed
    """
    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_toml_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load and parse a TOML file.

    Args:
        file_path: Path to TOML file to load

    Returns:
        Parsed TOML content as dict, or None if file doesn't exist

    Raises:
        IOError: If TOML support is not available (tomli/tomllib not installed)
    """
    if not file_path.exists():
        return None

    if tomllib is None:
        raise IOError("TOML support not available. Install tomli: uv pip install tomli")

    try:
        with open(file_path, 'rb') as f:  # Note: TOML requires binary mode
            return tomllib.load(f)
    except Exception as e:
        raise IOError(f"Failed to load TOML file {file_path}: {e}")


def save_toml_file(file_path: Path, data: Dict[str, Any], create_dirs: bool = True):
    """
    Save data to a TOML file.

    Args:
        file_path: Path where TOML should be saved
        data: Data to save
        create_dirs: Whether to create parent directories if needed

    Raises:
        IOError: If TOML writing support is not available (tomli-w not installed)
    """
    if tomli_w is None:
        raise IOError("TOML writing support not available. Install tomli-w: uv pip install tomli-w")

    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'wb') as f:  # Note: TOML requires binary mode
        tomli_w.dump(data, f)


def load_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load and parse a JSON file.

    Args:
        file_path: Path to JSON file to load

    Returns:
        Parsed JSON content as dict, or None if file doesn't exist
    """
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise IOError(f"Failed to load JSON file {file_path}: {e}")


def save_json_file(file_path: Path, data: Dict[str, Any], create_dirs: bool = True, indent: int = 2):
    """
    Save data to a JSON file.

    Args:
        file_path: Path where JSON should be saved
        data: Data to save
        create_dirs: Whether to create parent directories if needed
        indent: JSON indentation level (None for compact)
    """
    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def find_timestamped_files(
    directory: Path,
    pattern: str = 'model-*.yml',
    reverse: bool = True
) -> List[Path]:
    """
    Find timestamped files in a directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match (default: 'model-*.yml')
        reverse: Whether to sort in reverse chronological order

    Returns:
        List of matching paths, sorted by timestamp
    """
    if not directory.exists():
        return []

    files = list(directory.glob(pattern))
    return sorted(files, reverse=reverse)


def append_to_jsonl(file_path: Path, data: Dict[str, Any], create_dirs: bool = True):
    """
    Append a JSON object as a line to a JSONL (JSON Lines) file.

    Args:
        file_path: Path to JSONL file
        data: Data to append as JSON line
        create_dirs: Whether to create parent directories if needed
    """
    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')
