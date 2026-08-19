"""Tests for Agent Tools and Model Context Protocol (MCP) in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import Agent, MCP
from craft.agents.tool import AgentTool
from craft.agents.mcp import MCPServer


class CalculateDiscountTool(AgentTool):
    name = "calculate_discount"
    description = "Calculate percentage discount on an amount."
    parameters = {
        "amount": {"type": "number"},
        "percentage": {"type": "number"},
    }
    required = ["amount", "percentage"]

    def execute(self, amount: float, percentage: float) -> dict:
        discount = amount * (percentage / 100.0)
        return {"original": amount, "discount": discount, "final": amount - discount}


class AdminSecretTool(AgentTool):
    name = "admin_secret_action"
    description = "Perform restricted administrative operation."
    required_roles = ["admin"]

    def execute(self, action: str) -> dict:
        return {"status": "success", "action": action}


class TestMCPAgents:
    def test_agent_tool_schema_generation(self):
        tool = CalculateDiscountTool()
        schema = tool.schema()
        assert schema["name"] == "calculate_discount"
        assert "amount" in schema["parameters"]["properties"]
        assert "percentage" in schema["parameters"]["properties"]
        assert schema["parameters"]["required"] == ["amount", "percentage"]

    def test_mcp_server_initialize_and_tools_list(self):
        server = MCPServer()
        server.register_tool(CalculateDiscountTool())

        # 1. Initialize
        init_res = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert init_res["result"]["serverInfo"]["name"] == "craft-engine-mcp"

        # 2. Tools list
        list_res = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = list_res["result"]["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "calculate_discount"

    def test_mcp_server_tools_call_success(self):
        server = MCPServer()
        server.register_tool(CalculateDiscountTool())

        call_res = server.handle_request({
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "calculate_discount",
                "arguments": {"amount": 200.0, "percentage": 15.0},
            },
        })
        assert "result" in call_res
        content = call_res["result"]["content"][0]["text"]
        assert "170.0" in content

    def test_mcp_server_tool_rbac_authorization(self):
        server = MCPServer()
        server.register_tool(AdminSecretTool())

        # Unauthenticated/unauthorized caller should fail
        call_unauth = server.handle_request({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "admin_secret_action",
                "arguments": {"action": "wipe_cache"},
            },
        }, user=None)

        assert "error" in call_unauth
        assert call_unauth["error"]["code"] == -32003
        assert "Unauthorized" in call_unauth["error"]["message"]

    def test_mcp_facade_registration(self):
        Agent.register_tool(CalculateDiscountTool())
        res = MCP.handle_mcp({
            "jsonrpc": "2.0",
            "id": 99,
            "method": "tools/call",
            "params": {
                "name": "calculate_discount",
                "arguments": {"amount": 50.0, "percentage": 10.0},
            },
        })
        assert "result" in res
