#!/usr/bin/env python3
"""
Configuration Loader for RAVL Framework

Loads and caches framework configuration from .ravl/config/ravl.yml
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


# Cache to avoid reloading config on every call
_config_cache: Optional[Dict[str, Any]] = None


def load_framework_config() -> Dict[str, Any]:
    """
    Load and cache framework configuration from .ravl/config/ravl.yml

    Returns:
        Dict containing framework configuration
    """
    global _config_cache

    if _config_cache is None:
        config_path = Path(__file__).parent.parent.parent / 'config' / 'ravl.yml'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    _config_cache = yaml.safe_load(f) or {}
            except Exception as e:
                # If config load fails, use empty dict
                print(f"Warning: Failed to load config from {config_path}: {e}")
                _config_cache = {}
        else:
            _config_cache = {}

    return _config_cache


def get_max_tokens(key: str, default: int = 8192) -> int:
    """
    Get max_tokens for specific use case from framework config

    Args:
        key: Config key under llm.max_tokens (e.g., 'code_generation')
        default: Fallback value if config not found

    Returns:
        Maximum tokens to use for this LLM call
    """
    config = load_framework_config()

    try:
        max_tokens = config.get('llm', {}).get('max_tokens', {}).get(key, default)
        return int(max_tokens)
    except (KeyError, ValueError, TypeError):
        return default


def reload_config() -> None:
    """
    Force reload of framework configuration

    Useful for testing or when config file is modified at runtime
    """
    global _config_cache
    _config_cache = None
