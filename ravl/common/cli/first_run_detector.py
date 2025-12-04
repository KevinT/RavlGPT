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
    Get all configured API integrations by checking registry.

    Returns dict mapping API names to their environment variable names.
    Example: {'ClickUp': 'CLICKUP_API_TOKEN', 'GitHub': 'GITHUB_TOKEN'}
    """
    from ravl.common.integrations.api_credentials_registry import (
        get_all_registered_apis, get_all_env_var_options
    )

    apis = {}

    # Check each registered API
    for api_name in get_all_registered_apis():
        env_var_options = get_all_env_var_options(api_name)

        # Check if any of the expected env vars exist
        for var_name in env_var_options:
            if os.environ.get(var_name):
                # Use title case for display
                display_name = api_name.title()
                apis[display_name] = var_name
                break  # Found credentials for this API

    return apis
