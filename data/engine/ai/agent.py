"""AI Agent Tool Execution and Orchestration for Craft Framework.

Category: Core Framework (AI / Agents).
Relations:
  - Used by `craft.facades.AI.agent(...)`.
  - Supports both functions and `AgentTool` instances.
References:
  - Guide: `documentation/ai.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from engine.ai.contracts import AIDriver, AIResponse, ToolCall


@dataclass
class AgentStep:
    step_number: int
    thought_or_message: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIAgentResult:
    final_response: str
    steps: List[AgentStep]
    total_steps: int
    success: bool
    error: Optional[str] = None


class AIAgent:
    """Autonomous agent orchestrator capable of multi-step tool execution."""

    def __init__(
        self,
        driver: AIDriver,
        tools: Optional[List[Any]] = None,
        system_prompt: Optional[str] = None,
        max_steps: int = 10,
        model: Optional[str] = None,
    ):
        self.driver = driver
        self.raw_tools = tools or []
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.model = model
        self._tool_registry: Dict[str, Any] = {}
        self._tool_schemas: List[Dict[str, Any]] = []

        self._register_tools(self.raw_tools)

    def _register_tools(self, tools: List[Any]) -> None:
        for t in tools:
            # Handle AgentTool class/instance or plain Python callable
            if hasattr(t, "name") and hasattr(t, "schema") and hasattr(t, "run"):
                name = t.name
                schema = t.schema() if callable(t.schema) else t.schema
                self._tool_registry[name] = t.run
                self._tool_schemas.append(schema)
            elif callable(t):
                name = getattr(t, "__name__", "tool")
                doc = inspect.getdoc(t) or f"Execute {name}"
                sig = inspect.signature(t)
                properties: Dict[str, Any] = {}
                required: List[str] = []

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

                    properties[param_name] = {"type": p_type}
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)

                schema = {
                    "name": name,
                    "description": doc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                }
                self._tool_registry[name] = t
                self._tool_schemas.append(schema)

    def run(self, prompt: str) -> AIAgentResult:
        """Execute the autonomous agent loop until completion or max_steps reached."""
        messages: List[Dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        steps: List[AgentStep] = []

        for step_idx in range(1, self.max_steps + 1):
            try:
                response: AIResponse = self.driver.chat(
                    messages=messages,
                    model=self.model,
                    tools=self._tool_schemas if self._tool_schemas else None,
                )
            except Exception as e:
                return AIAgentResult(
                    final_response="",
                    steps=steps,
                    total_steps=step_idx,
                    success=False,
                    error=str(e),
                )

            # If no tools called, we reached the final answer
            if not response.has_tool_calls:
                step = AgentStep(
                    step_number=step_idx,
                    thought_or_message=response.content,
                )
                steps.append(step)
                return AIAgentResult(
                    final_response=response.content,
                    steps=steps,
                    total_steps=step_idx,
                    success=True,
                )

            # Execute tool calls
            tool_outputs: Dict[str, Any] = {}
            for call in response.tool_calls:
                fn = self._tool_registry.get(call.name)
                if fn is None:
                    out = f"Error: Tool '{call.name}' is not registered."
                else:
                    try:
                        out = fn(**call.arguments)
                    except Exception as err:
                        out = f"Error executing tool '{call.name}': {err}"

                tool_outputs[call.name] = out
                # Feed tool result back into message thread
                messages.append({
                    "role": "assistant",
                    "content": f"Called tool: {call.name}({json.dumps(call.arguments)})",
                })
                messages.append({
                    "role": "user",
                    "content": f"Tool output [{call.name}]: {json.dumps(out) if not isinstance(out, str) else out}",
                })

            step = AgentStep(
                step_number=step_idx,
                thought_or_message=response.content,
                tool_calls=response.tool_calls,
                tool_outputs=tool_outputs,
            )
            steps.append(step)

        # Max steps exceeded
        return AIAgentResult(
            final_response=steps[-1].thought_or_message if steps else "Max steps reached without resolution.",
            steps=steps,
            total_steps=self.max_steps,
            success=False,
            error="Max steps limit reached.",
        )
