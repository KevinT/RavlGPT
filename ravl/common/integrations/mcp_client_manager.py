#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025 Kevin Trethewey

"""
MCP Client Manager - Manages lifecycle of MCP server connections

Handles connecting to MCP servers, tool discovery, and tool execution.
Supports SSE, stdio, and HTTP transports.
"""

import os
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum


# Check if MCP package is available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    try:
        from mcp import SSEServerParameters
        from mcp.client.sse import sse_client
        SSE_AVAILABLE = True
    except ImportError:
        SSE_AVAILABLE = False
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    SSE_AVAILABLE = False


class ConnectionStatus(Enum):
    """MCP server connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPServerConnection:
    """Represents a connection to an MCP server."""
    server_name: str
    config: Dict
    client: Optional[Any] = None
    session: Optional[Any] = None
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    capabilities: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class MCPClientManager:
    """
    Manages MCP server connections and tool execution.

    Responsibilities:
    - Connect to registered MCP servers
    - Discover available tools via MCP protocol
    - Execute tool calls
    - Handle reconnection on failures
    - Cache tool results
    """

    def __init__(self):
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP package not installed. Install with: uv pip install mcp\n"
                "Or add 'mcp' to your loop's requirements.txt"
            )

        self.connections: Dict[str, MCPServerConnection] = {}
        self._tool_cache: Dict[str, Any] = {}

    def connect(self, server_name: str, config: Dict) -> bool:
        """
        Connect to an MCP server.

        Args:
            server_name: Name of the server (e.g., "clickup")
            config: Server configuration from registry

        Returns:
            True if connection successful
        """
        connection = MCPServerConnection(
            server_name=server_name,
            config=config,
            status=ConnectionStatus.CONNECTING
        )

        try:
            transport = config.get('transport')

            if transport == 'stdio':
                connection.client, connection.session = self._connect_stdio(config)
            elif transport == 'sse':
                if not SSE_AVAILABLE:
                    raise ImportError("SSE transport not available. Upgrade mcp package.")
                connection.client, connection.session = self._connect_sse(config)
            elif transport == 'http':
                raise NotImplementedError("HTTP transport not yet implemented")
            else:
                raise ValueError(f"Unknown transport: {transport}")

            # Discover capabilities
            connection.capabilities = self._discover_tools(connection.session)
            connection.status = ConnectionStatus.CONNECTED

            self.connections[server_name] = connection
            return True

        except Exception as e:
            connection.status = ConnectionStatus.ERROR
            connection.error_message = str(e)
            self.connections[server_name] = connection
            return False

    def _connect_stdio(self, config: Dict):
        """Connect to stdio-based MCP server."""
        command = config.get('command')
        args = config.get('args', [])

        if not command:
            raise ValueError("stdio transport requires 'command' field")

        # Get auth token from environment if needed
        env_var = config.get('env_var')
        env = os.environ.copy()
        if env_var and os.environ.get(env_var):
            env[env_var] = os.environ[env_var]

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        client = stdio_client(server_params)
        session = client.__enter__()
        return client, session

    def _connect_sse(self, config: Dict):
        """Connect to SSE-based MCP server."""
        url = config.get('url')

        if not url:
            raise ValueError("sse transport requires 'url' field")

        # Get auth token from environment if needed
        env_var = config.get('env_var')
        headers = {}
        if env_var and os.environ.get(env_var):
            headers['Authorization'] = f"Bearer {os.environ[env_var]}"

        server_params = SSEServerParameters(
            url=url,
            headers=headers if headers else None
        )

        client = sse_client(server_params)
        session = client.__enter__()
        return client, session

    def _discover_tools(self, session: Any) -> List[str]:
        """Discover available tools from MCP server."""
        try:
            tools_result = session.list_tools()
            return [tool.name for tool in tools_result.tools]
        except Exception:
            return []

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Any:
        """
        Call an MCP tool.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments as dict

        Returns:
            Tool result
        """
        connection = self.connections.get(server_name)

        if not connection:
            raise ValueError(f"Not connected to server: {server_name}")

        if connection.status != ConnectionStatus.CONNECTED:
            raise RuntimeError(f"Server {server_name} not connected: {connection.status.value}")

        # Check cache
        cache_key = f"{server_name}:{tool_name}:{hash(str(sorted(arguments.items())))}"
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]

        try:
            result = connection.session.call_tool(tool_name, arguments)

            # Cache result
            self._tool_cache[cache_key] = result

            return result

        except Exception as e:
            # Attempt reconnection on error
            if self.connect(server_name, connection.config):
                return self.call_tool(server_name, tool_name, arguments)
            else:
                raise RuntimeError(f"Tool call failed: {e}")

    def disconnect(self, server_name: str):
        """Disconnect from an MCP server."""
        connection = self.connections.get(server_name)
        if connection and connection.client:
            try:
                connection.client.__exit__(None, None, None)
            except Exception:
                pass
            connection.status = ConnectionStatus.DISCONNECTED

    def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for server_name in list(self.connections.keys()):
            self.disconnect(server_name)

    def get_status(self, server_name: str) -> Optional[ConnectionStatus]:
        """Get connection status for a server."""
        connection = self.connections.get(server_name)
        return connection.status if connection else None

    def get_capabilities(self, server_name: str) -> List[str]:
        """Get list of available tools for a server."""
        connection = self.connections.get(server_name)
        return connection.capabilities if connection else []

    def is_connected(self, server_name: str) -> bool:
        """Check if connected to a server."""
        status = self.get_status(server_name)
        return status == ConnectionStatus.CONNECTED if status else False
