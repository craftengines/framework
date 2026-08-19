"""Model Context Protocol (MCP) Server Handler for Craft Framework.

Category: Core Framework (Agents / MCP).
Relations:
  - Exposes JSON-RPC 2.0 compliant tools/list, tools/call, resources/list endpoints.
  - Backs `MCP` facade (`craft.facades.MCP`).
References:
  - Guide: `documentation/agents_mcp.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from engine.agents.tool import AgentTool


class MCPServer:
    """Model Context Protocol Server for autonomous AI agents and IDEs."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        self._tools: Dict[str, AgentTool] = {}

    def register_tool(self, tool: AgentTool) -> None:
        """Register an AgentTool with the MCP server."""
        self._tools[tool.name] = tool

    def get_tools(self, user: Optional[Any] = None) -> List[Dict[str, Any]]:
        """List all MCP tools available to the given user."""
        available: List[Dict[str, Any]] = []
        for tool in self._tools.values():
            if tool.authorize(user):
                available.append(tool.schema())
        return available

    def handle_request(self, payload: Dict[str, Any], user: Optional[Any] = None) -> Dict[str, Any]:
        """Handle a standard JSON-RPC 2.0 MCP request."""
        req_id = payload.get("id", 1)
        method = payload.get("method", "")
        params = payload.get("params", {})

        if method == "tools/list":
            tools = self.get_tools(user)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools},
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self._tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool '{tool_name}' not found.",
                    },
                }

            tool = self._tools[tool_name]
            try:
                result = tool.run(user=user, **arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result) if not isinstance(result, str) else result,
                            }
                        ]
                    },
                }
            except PermissionError as perm_err:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32003,
                        "message": str(perm_err),
                    },
                }
            except Exception as err:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution failed: {err}",
                    },
                }

        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "craft-engine-mcp",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not supported.",
            },
        }
