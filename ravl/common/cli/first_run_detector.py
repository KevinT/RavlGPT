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

    Priority:
    1. Framework config file (.ravl/config/llm.toml)
    2. Environment variable (RAVL_DEFAULT_LLM_PROVIDER)
    3. Auto-detect from API keys

    Returns:
        Provider name ("anthropic", "google", "openai", "ollama") or None
    """
    # Check framework config first
    from ravl.common.config.config_service import get_llm_provider_from_framework_config
    config_provider = get_llm_provider_from_framework_config()
    if config_provider:
        return config_provider

    # Check environment variable
    env_provider = os.environ.get('RAVL_DEFAULT_LLM_PROVIDER', '').lower()
    if env_provider:
        return env_provider

    # Auto-detect based on what keys are available (fallback only)
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


def get_all_mcp_servers_with_status() -> Dict[str, Dict[str, any]]:
    """
    Get all registered MCP servers with their detection status.

    Returns dict mapping server names to their metadata:
    {
        'Clickup': {
            'transport': 'sse',
            'url': 'http://localhost:3000',
            'env_var': 'CLICKUP_API_TOKEN',
            'detected': True,
            'config': {...full config...}
        },
        ...
    }
    """
    from ravl.common.integrations.mcp_registry import (
        get_all_registered_servers, get_mcp_server_config, get_env_var
    )

    servers = {}

    for server_name in get_all_registered_servers():
        config = get_mcp_server_config(server_name)
        env_var = get_env_var(server_name)

        # Use display name from config, or title case the server name
        display_name = config.get('name', server_name.title())

        # Check if credentials are available (if needed)
        detected = True
        if env_var:
            detected = bool(os.environ.get(env_var))

        servers[display_name] = {
            'transport': config.get('transport'),
            'url': config.get('url'),
            'command': config.get('command'),
            'env_var': env_var,
            'detected': detected,
            'config': config
        }

    return servers
