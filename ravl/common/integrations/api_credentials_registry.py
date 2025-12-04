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
from typing import Dict, List, Optional
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


def get_api_metadata(api_name: str) -> Dict:
    """
    Get metadata for an API (case-insensitive).

    Args:
        api_name: Name of the API (e.g., "ClickUp", "github", "Notion")

    Returns:
        Dict with keys: env_var_names, preferred, prompt, documentation, auth_type
    """
    registry = _load_registry()
    return registry.get(api_name.lower(), {})


def get_preferred_env_var(api_name: str) -> str:
    """
    Get the preferred environment variable name for an API.

    Args:
        api_name: Name of the API

    Returns:
        Preferred env var name, or a generated name if not in registry
    """
    metadata = get_api_metadata(api_name)
    return metadata.get('preferred', f"{api_name.upper().replace(' ', '_')}_API_TOKEN")


def get_all_env_var_options(api_name: str) -> List[str]:
    """
    Get all possible environment variable names for an API.

    Args:
        api_name: Name of the API

    Returns:
        List of env var names (preferred first)
    """
    metadata = get_api_metadata(api_name)
    return metadata.get('env_var_names', [])


def get_prompt_text(api_name: str) -> str:
    """
    Get the prompt text for requesting the credential.

    Args:
        api_name: Name of the API

    Returns:
        User-friendly prompt text
    """
    metadata = get_api_metadata(api_name)
    return metadata.get('prompt', f"{api_name} API token")


def get_additional_vars(api_name: str) -> List[Dict]:
    """
    Get any additional variables needed for this API.

    Args:
        api_name: Name of the API

    Returns:
        List of dicts with keys: name, prompt, required
    """
    metadata = get_api_metadata(api_name)
    return metadata.get('additional_vars', [])


def is_api_registered(api_name: str) -> bool:
    """
    Check if an API is in the registry.

    Args:
        api_name: Name of the API

    Returns:
        True if API is registered
    """
    return bool(get_api_metadata(api_name))


def get_all_registered_apis() -> List[str]:
    """
    Get list of all registered API names.

    Returns:
        List of API names (lowercase keys from registry)
    """
    registry = _load_registry()
    return list(registry.keys())


def get_available_credentials(api_name: str) -> List[str]:
    """
    Check which env vars for this API actually exist in environment.

    Args:
        api_name: Name of the API

    Returns:
        List of found env vars, in order of preference
    """
    import os

    metadata = get_api_metadata(api_name)
    if not metadata:
        return []

    candidates = metadata.get('env_var_names', [])
    available = [name for name in candidates if os.environ.get(name)]

    return available


def add_api_to_registry(api_name: str, env_vars: List[str], **kwargs):
    """
    Add a new API to the registry (saves to YAML).

    Args:
        api_name: Name of the API
        env_vars: List of env var names (first is preferred)
        **kwargs: Additional metadata (prompt, documentation, auth_type, etc.)
    """
    registry = _load_registry()

    api_key = api_name.lower()
    registry[api_key] = {
        'env_var_names': env_vars,
        'preferred': env_vars[0] if env_vars else f"{api_name.upper()}_API_TOKEN",
        'prompt': kwargs.get('prompt', f"{api_name} API token"),
        'documentation': kwargs.get('documentation', ''),
        'auth_type': kwargs.get('auth_type', 'bearer_token')
    }

    # Save back to YAML
    registry_path = Path(__file__).parent.parent.parent.parent / 'config' / 'api_credentials_registry.yml'
    with open(registry_path, 'w') as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)

    # Clear cache
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
