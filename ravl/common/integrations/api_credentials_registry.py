#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
API Credentials Registry - Loads and queries api_credentials_registry.yml

Provides functions to query API credential metadata from the centralized YAML config.
This ensures consistent environment variable naming across:
- The ravl --config wizard
- Code generation (DSL guidance)
- API discovery
"""

from pathlib import Path
from typing import Dict, Optional
import yaml


_REGISTRY_CACHE: Optional[Dict] = None


def _load_registry() -> Dict:
    """Load and cache the API credentials registry from YAML."""
    global _REGISTRY_CACHE

    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    registry_path = Path(__file__).parent.parent.parent.parent / 'config' / 'api_credentials_registry.yml'

    if not registry_path.exists():
        return {}

    with open(registry_path, 'r') as f:
        _REGISTRY_CACHE = yaml.safe_load(f) or {}

    return _REGISTRY_CACHE


def get_api_config(api_name: str) -> Dict:
    """
    Get the complete configuration for an API (case-insensitive).

    Args:
        api_name: Name of the API (e.g., "ClickUp", "github", "Notion")

    Returns:
        Dict with all configuration fields for the API
    """
    registry = _load_registry()
    return registry.get(api_name.lower(), {})


def get_env_var(api_name: str) -> Optional[str]:
    """
    Get the environment variable name for an API.

    Args:
        api_name: Name of the API

    Returns:
        Environment variable name, or None if not in registry
    """
    config = get_api_config(api_name)
    return config.get('env_var')


def is_api_registered(api_name: str) -> bool:
    """
    Check if an API is in the registry.

    Args:
        api_name: Name of the API

    Returns:
        True if API is registered
    """
    return bool(get_api_config(api_name))


def is_api_configured(api_name: str) -> bool:
    """
    Check if API is registered AND env var exists in environment.

    Args:
        api_name: Name of the API

    Returns:
        True if API is registered and credential exists
    """
    import os

    config = get_api_config(api_name)
    if not config:
        return False

    env_var = config.get('env_var')
    return env_var and os.environ.get(env_var) is not None


def get_all_registered_apis() -> list:
    """
    Get list of all registered API names.

    Returns:
        List of API names (lowercase keys from registry)
    """
    registry = _load_registry()
    return list(registry.keys())


def add_api_to_registry(api_name: str, env_var: str, documentation: str = '', **custom_fields):
    """
    Add or update API in registry (saves to YAML).

    Args:
        api_name: Name of the API
        env_var: Environment variable name
        documentation: API documentation URL (Context7 preferred)
        **custom_fields: Any additional metadata (base_url, rate_limit, auth_type, etc.)
    """
    registry = _load_registry()

    api_key = api_name.lower()
    registry[api_key] = {
        'env_var': env_var,
        'documentation': documentation,
        **custom_fields  # Include any custom fields user provided
    }

    # Save back to YAML
    registry_path = Path(__file__).parent.parent.parent.parent / 'config' / 'api_credentials_registry.yml'
    with open(registry_path, 'w') as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)

    # Clear cache
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
