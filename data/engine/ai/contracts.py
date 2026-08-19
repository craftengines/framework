"""AI SDK Contracts and Data Structures for Craft Framework.

Category: Core Framework (AI).
Relations:
  - Backs `AI` facade (`craft.facades.AI`).
  - Used by `craft.ai.manager.AIManager` and Agent Tool Callers.
References:
  - Guide: `documentation/ai.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol


@dataclass
class ToolCall:
    """Represents a tool or function call requested by an LLM."""
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None


@dataclass
class AIResponse:
    """Unified response from any AI provider."""
    content: str
    model: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    raw_response: Any = None
    finish_reason: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class EmbeddingResponse:
    """Unified response containing vector embeddings."""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int] = field(default_factory=dict)

    @property
    def vector(self) -> List[float]:
        """Convenience property for single text embeddings."""
        return self.embeddings[0] if self.embeddings else []


class AIDriver(Protocol):
    """Protocol that every AI driver must implement."""

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> AIResponse:
        """Send chat messages and get an AIResponse."""
        ...

    def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate vector embeddings for input text(s)."""
        ...
