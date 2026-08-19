"""Agent & MCP Manager for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engine.agents.mcp import MCPServer
from engine.agents.tool import AgentTool


class AgentManager:
    """Manager for Agent Tools and MCP Protocol."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self._server = MCPServer(app)

    def register_tool(self, tool: AgentTool) -> None:
        """Register a new AgentTool."""
        self._server.register_tool(tool)

    def get_server(self) -> MCPServer:
        """Get the underlying MCPServer instance."""
        return self._server

    def handle_mcp(self, payload: Dict[str, Any], user: Optional[Any] = None) -> Dict[str, Any]:
        """Process an MCP JSON-RPC payload."""
        return self._server.handle_request(payload, user=user)
