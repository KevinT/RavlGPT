#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
MCP Servers Registry - Loads and queries mcp_servers_registry.yml

Provides functions to query MCP server metadata from the centralized YAML config.
This ensures consistent MCP server configuration across:
- The ravl --config wizard
- Code generation (DSL guidance)
- MCP client lifecycle management
"""

from pathlib import Path
from typing import Dict, Optional, List
import yaml


_REGISTRY_CACHE: Optional[Dict] = None


def _load_registry() -> Dict:
    """Load and cache the MCP servers registry from YAML."""
    global _REGISTRY_CACHE

    if _REGISTRY_CACHE is not None:
        return _REGISTRY_CACHE

    from ravl.common.cli.ravl_cli_base import RAVLCLIBase
    framework_root = RAVLCLIBase.find_framework_root()
    registry_path = framework_root / 'config' / 'mcp_servers_registry.yml'

    if not registry_path.exists():
        return {}

    with open(registry_path, 'r') as f:
        _REGISTRY_CACHE = yaml.safe_load(f) or {}

    return _REGISTRY_CACHE


def get_mcp_server_config(server_name: str) -> Dict:
    """
    Get the complete configuration for an MCP server (case-insensitive).

    Args:
        server_name: Name of the MCP server (e.g., "clickup", "github", "filesystem")

    Returns:
        Dict with all configuration fields for the server
    """
    registry = _load_registry()
    return registry.get(server_name.lower(), {})


def get_transport_type(server_name: str) -> Optional[str]:
    """
    Get the transport type (sse, stdio, http) for an MCP server.

    Args:
        server_name: Name of the MCP server

    Returns:
        Transport type string, or None if not in registry
    """
    config = get_mcp_server_config(server_name)
    return config.get('transport')


def get_connection_url(server_name: str) -> Optional[str]:
    """
    Get the connection URL for SSE/HTTP servers.

    Args:
        server_name: Name of the MCP server

    Returns:
        URL string, or None if not applicable (e.g., stdio transport)
    """
    config = get_mcp_server_config(server_name)
    return config.get('url')


def get_command_path(server_name: str) -> Optional[str]:
    """
    Get the executable path for stdio servers.

    Args:
        server_name: Name of the MCP server

    Returns:
        Command path string, or None if not applicable (e.g., sse transport)
    """
    config = get_mcp_server_config(server_name)
    return config.get('command')


def get_command_args(server_name: str) -> List[str]:
    """
    Get command arguments for stdio servers.

    Args:
        server_name: Name of the MCP server

    Returns:
        List of argument strings, empty list if none specified
    """
    config = get_mcp_server_config(server_name)
    return config.get('args', [])


def get_env_var(server_name: str) -> Optional[str]:
    """
    Get the environment variable name for authentication.

    Args:
        server_name: Name of the MCP server

    Returns:
        Environment variable name, or None if no auth required
    """
    config = get_mcp_server_config(server_name)
    return config.get('env_var')


def is_mcp_server_registered(server_name: str) -> bool:
    """
    Check if an MCP server is in the registry.

    Args:
        server_name: Name of the MCP server

    Returns:
        True if server is registered
    """
    return bool(get_mcp_server_config(server_name))


def get_all_registered_servers() -> List[str]:
    """
    Get list of all registered MCP server names.

    Returns:
        List of server names (lowercase keys from registry)
    """
    registry = _load_registry()
    return list(registry.keys())


def add_mcp_server_to_registry(
    server_name: str,
    transport: str,
    url: str = None,
    command: str = None,
    args: List[str] = None,
    env_var: str = None,
    **custom_fields
):
    """
    Add or update MCP server in registry (saves to YAML).

    Args:
        server_name: Name of the MCP server
        transport: Transport type (sse, stdio, http)
        url: Connection URL (for sse/http)
        command: Executable path (for stdio)
        args: Command arguments (for stdio)
        env_var: Environment variable for auth token
        **custom_fields: Any additional metadata (name, description, documentation, etc.)
    """
    registry = _load_registry()

    server_key = server_name.lower()
    config = {
        'transport': transport,
        **custom_fields
    }

    if url:
        config['url'] = url
    if command:
        config['command'] = command
    if args:
        config['args'] = args
    if env_var:
        config['env_var'] = env_var

    registry[server_key] = config

    # Save back to YAML
    from ravl.common.cli.ravl_cli_base import RAVLCLIBase
    framework_root = RAVLCLIBase.find_framework_root()
    registry_path = framework_root / 'config' / 'mcp_servers_registry.yml'
    with open(registry_path, 'w') as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)

    # Clear cache
    global _REGISTRY_CACHE
    _REGISTRY_CACHE = None
