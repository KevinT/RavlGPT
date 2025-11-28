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
    Example: {'ClickUp': 'CLICKUP_API_TOKEN', 'GitHub': 'GITHUB_API_TOKEN'}
    """
    apis = {}

    for key, value in os.environ.items():
        if key.endswith('_API_TOKEN') and value:
            # Convert CLICKUP_API_TOKEN -> ClickUp
            api_name = key.replace('_API_TOKEN', '').replace('_', ' ').title().replace(' ', '')
            apis[api_name] = key

    return apis
