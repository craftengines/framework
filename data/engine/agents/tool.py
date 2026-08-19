"""Agent Tool Definition and Guard for Craft Framework.

Category: Core Framework (Agents / MCP).
Relations:
  - Used by `craft.ai.agent.AIAgent` and `craft.agents.mcp.MCPServer`.
  - Integrates with `craft.facades.Gate` and `craft.facades.Access` for RBAC enforcement.
References:
  - Guide: `documentation/agents_mcp.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional


class AgentTool:
    """Base class for declarative, RBAC-guarded tools for AI Agents and MCP."""

    name: str = "custom_tool"
    description: str = "Tool description."
    parameters: Dict[str, Any] = {}
    required: List[str] = []
    required_permissions: List[str] = []
    required_roles: List[str] = []

    def schema(self) -> Dict[str, Any]:
        """Generate OpenAI/MCP compatible tool definition schema."""
        props = self.parameters.copy() if self.parameters else {}
        req = list(self.required)

        # If parameters were not explicitly declared, infer from execute() method signature
        if not props and hasattr(self, "execute"):
            sig = inspect.signature(self.execute)
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                p_type = "string"
                if param.annotation == int:
                    p_type = "integer"
                elif param.annotation == float:
                    p_type = "number"
                elif param.annotation == bool:
                    p_type = "boolean"
                elif param.annotation in (dict, Dict):
                    p_type = "object"
                elif param.annotation in (list, List):
                    p_type = "array"

                props[param_name] = {"type": p_type}
                if param.default == inspect.Parameter.empty:
                    req.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": req,
            },
        }

    def authorize(self, user: Optional[Any] = None) -> bool:
        """Verify that the user or agent has permission to execute this tool."""
        if not self.required_permissions and not self.required_roles:
            return True

        if user is None:
            return False

        from engine.facades import Access

        for perm in self.required_permissions:
            if not Access.has_permission(user, perm):
                return False

        for role in self.required_roles:
            if not Access.has_role(user, role):
                return False

        return True

    def run(self, user: Optional[Any] = None, **kwargs: Any) -> Any:
        """Authorize and execute the tool."""
        if not self.authorize(user):
            raise PermissionError(
                f"Unauthorized: Execution of tool '{self.name}' requires permissions "
                f"{self.required_permissions} and roles {self.required_roles}."
            )
        return self.execute(**kwargs)

    def execute(self, **kwargs: Any) -> Any:
        """Concrete tool logic to be implemented by subclasses."""
        raise NotImplementedError("AgentTool must implement execute()")
