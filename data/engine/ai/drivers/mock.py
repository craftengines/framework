"""Mock AI Driver for unit testing and local offline execution in Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Union

from engine.ai.contracts import AIResponse, EmbeddingResponse, ToolCall
from engine.ai.drivers.base import BaseAIDriver


class MockAIDriver(BaseAIDriver):
    """Deterministic in-memory mock AI driver."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {"model": "mock-ai-model", "embed_model": "mock-embed-model"})
        self.canned_responses: List[str] = []
        self.canned_tool_calls: List[List[ToolCall]] = []

    def queue_response(self, text: str) -> MockAIDriver:
        """Queue a canned response text."""
        self.canned_responses.append(text)
        return self

    def queue_tool_call(self, name: str, arguments: Dict[str, Any]) -> MockAIDriver:
        """Queue a canned tool call response."""
        self.canned_tool_calls.append([ToolCall(name=name, arguments=arguments, id="call_mock_1")])
        return self

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> AIResponse:
        active_model = model or self.default_model

        if self.canned_tool_calls:
            calls = self.canned_tool_calls.pop(0)
            return AIResponse(
                content="",
                model=active_model,
                tool_calls=calls,
                finish_reason="tool_calls",
            )

        if self.canned_responses:
            content = self.canned_responses.pop(0)
        else:
            last_msg = messages[-1].get("content", "") if messages else ""
            content = f"Mock response for: {last_msg}"

        return AIResponse(
            content=content,
            model=active_model,
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )

    def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        norm = self._normalize_texts(texts)
        active_model = model or self.default_embed_model

        embeddings: List[List[float]] = []
        for t in norm:
            # Generate deterministic 16-dimension float vector using sha256 hash
            h = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [float(b) / 255.0 for b in h[:16]]
            # Normalize vector length
            norm_val = sum(x * x for x in vec) ** 0.5 or 1.0
            vec = [x / norm_val for x in vec]
            embeddings.append(vec)

        return EmbeddingResponse(
            embeddings=embeddings,
            model=active_model,
            usage={"total_tokens": sum(len(t) for t in norm)},
        )
