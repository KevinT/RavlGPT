"""
First-run detection for RAVL setup.

Checks if an LLM provider is configured. If not, setup is required.
"""

import os
from typing import Dict, Optional


def needs_setup() -> bool:
    """
    Check if RAVL needs initial setup.

    Returns True if no LLM provider is configured.
    """
    llm_keys = [
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'GOOGLE_API_KEY',
        'OLLAMA_BASE_URL'
    ]

    for key in llm_keys:
        if os.environ.get(key):
            return False

    return True


def get_configured_llm_provider() -> Optional[str]:
    """
    Get the currently configured default LLM provider.

    Returns the provider name or None if no default is set.
    """
    default = os.environ.get('RAVL_DEFAULT_LLM_PROVIDER', '').lower()

    if default:
        return default

    # Auto-detect based on what keys are available
    if os.environ.get('ANTHROPIC_API_KEY'):
        return 'anthropic'
    elif os.environ.get('OPENAI_API_KEY'):
        return 'openai'
    elif os.environ.get('GOOGLE_API_KEY'):
        return 'google'
    elif os.environ.get('OLLAMA_BASE_URL'):
        return 'ollama'

    return None


def get_configured_apis() -> Dict[str, str]:
    """
    Get all configured API integrations.

    Returns dict mapping API names to their environment variable names.
    Example: {'ClickUp': 'CLICKUP_API_TOKEN', 'GitHub': 'GITHUB_TOKEN'}
    """
    from ravl.common.integrations.api_credentials_registry import (
        get_all_registered_apis, get_env_var
    )

    apis = {}

    # Check each registered API
    for api_name in get_all_registered_apis():
        env_var = get_env_var(api_name)

        if env_var and os.environ.get(env_var):
            # Use title case for display
            display_name = api_name.title()
            apis[display_name] = env_var

    return apis


def get_all_apis_with_status() -> Dict[str, Dict[str, any]]:
    """
    Get all registered APIs with their detection status.

    Returns dict mapping API names to their metadata:
    {
        'ClickUp': {
            'env_var': 'CLICKUP_API_TOKEN',
            'detected': True,
            'config': {...full config...}
        },
        'GitHub': {
            'env_var': 'GITHUB_TOKEN',
            'detected': False,
            'config': {...full config...}
        },
        ...
    }
    """
    from ravl.common.integrations.api_credentials_registry import (
        get_all_registered_apis, get_api_config, get_env_var
    )

    apis = {}

    for api_name in get_all_registered_apis():
        config = get_api_config(api_name)
        env_var = get_env_var(api_name)

        display_name = api_name.title()
        apis[display_name] = {
            'env_var': env_var,
            'detected': bool(env_var and os.environ.get(env_var)),
            'config': config
        }

    return apis
