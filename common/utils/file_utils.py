"""File I/O utilities for RAVL framework

Consolidates common file operations (YAML, JSON loading/saving) to reduce duplication.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


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
