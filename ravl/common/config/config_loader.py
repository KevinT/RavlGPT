#!/usr/bin/env python3
"""
Configuration Loader for RAVL Framework

Loads and caches framework configuration from .ravl/config/ravl.toml
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from utils.constants import DEFAULT_MAX_TOKENS
from utils.file_utils import load_toml_file, load_toml_file, save_toml_file, save_yaml_file


# Cache to avoid reloading config on every call
_config_cache: Optional[Dict[str, Any]] = None


def load_config_file(config_dir: Path, base_name: str = 'ravl') -> Dict[str, Any]:
    """
    Load configuration from TOML file.

    Args:
        config_dir: Directory containing config file
        base_name: Base name of config file (default: 'ravl')

    Returns:
        Parsed config dict, or empty dict if no config found
    """
    # Load TOML config
    toml_path = config_dir / f'{base_name}.toml'
    if toml_path.exists():
        try:
            config = load_toml_file(toml_path)
            return config or {}
        except Exception as e:
            print(f"Warning: Failed to load TOML config from {toml_path}: {e}")

    # No config found
    return {}


def save_config_file(config_dir: Path, data: Dict[str, Any], base_name: str = 'ravl', use_toml: bool = True):
    """
    Save configuration to TOML or YAML file.

    Args:
        config_dir: Directory to save config file
        data: Configuration data to save
        base_name: Base name of config file (default: 'ravl')
        use_toml: Whether to save as TOML (True) or YAML (False)
    """
    if use_toml:
        file_path = config_dir / f'{base_name}.toml'
        save_toml_file(file_path, data, create_dirs=True)
    else:
        file_path = config_dir / f'{base_name}.yml'
        save_yaml_file(file_path, data, create_dirs=True)


def load_framework_config() -> Dict[str, Any]:
    """
    Load and cache framework configuration from .ravl/config/ravl.toml

    Returns:
        Dict containing framework configuration
    """
    global _config_cache

    if _config_cache is None:
        config_dir = Path(__file__).parent.parent.parent / 'config'
        _config_cache = load_config_file(config_dir, 'ravl')

    return _config_cache


def get_max_tokens(key: str, default: int = DEFAULT_MAX_TOKENS) -> int:
    """
    Get max_tokens for specific use case from framework config

    Priority: Environment variables > ravl.toml > defaults

    Args:
        key: Config key under llm.max_tokens (e.g., 'code_generation')
        default: Fallback value if config not found

    Returns:
        Maximum tokens to use for this LLM call
    """
    # Check environment variable first (wizard overrides)
    env_var = f'RAVL_MAX_TOKENS_{key.upper()}'
    env_value = os.environ.get(env_var, '')

    if env_value:
        try:
            return int(env_value)
        except ValueError:
            pass  # Fall through to TOML/default

    # Fall back to TOML config
    config = load_framework_config()
    try:
        max_tokens = config.get('llm', {}).get('max_tokens', {}).get(key, default)
        return int(max_tokens)
    except (KeyError, ValueError, TypeError):
        return default


def get_prompt_normalization_config() -> Dict[str, Any]:
    """
    Get prompt normalization configuration.

    Priority: Environment variables > ravl.toml > defaults
    This allows wizard-configured overrides via .env

    Returns:
        Dict with keys: enabled (bool), min_block_size (int), enable_logging (bool)
    """
    config = load_framework_config()
    norm_config = config.get('llm', {}).get('prompt_normalization', {})

    # Check environment variables first (wizard overrides)
    env_enabled = os.environ.get('RAVL_PROMPT_NORMALIZATION_ENABLED', '').lower()
    env_min_block = os.environ.get('RAVL_PROMPT_NORMALIZATION_MIN_BLOCK_SIZE', '')
    env_logging = os.environ.get('RAVL_PROMPT_NORMALIZATION_ENABLE_LOGGING', '').lower()

    return {
        'enabled': env_enabled == 'true' if env_enabled else norm_config.get('enabled', True),
        'min_block_size': int(env_min_block) if env_min_block else norm_config.get('min_block_size', 200),
        'enable_logging': env_logging == 'true' if env_logging else norm_config.get('enable_logging', True)
    }


def reload_config() -> None:
    """
    Force reload of framework configuration

    Useful for testing or when config file is modified at runtime
    """
    global _config_cache
    _config_cache = None
