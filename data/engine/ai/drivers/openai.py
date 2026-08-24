"""OpenAI Driver for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from engine.ai.contracts import AIResponse, EmbeddingResponse, ToolCall
from engine.ai.drivers.base import BaseAIDriver


def _httpx():
    """The HTTP client, imported on use rather than on import.

    `engine/ai/manager.py` imports this module at boot, so a module-level
    `import httpx` made the whole framework unbootable wherever httpx was not
    installed — and it is not a runtime dependency. Every other optional
    backend here (boto3, redis, psycopg2, pymysql) is imported this way, with a
    message naming the package; this one was the exception.
    """
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ImportError(
            "The `httpx` package is required to call the OpenAI API. "
            "Install it with `pip install httpx`, or use the `mock` AI driver."
        ) from exc
    return httpx


class OpenAIDriver(BaseAIDriver):
    """OpenAI Driver using standard REST API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")

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
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]

        resp = _httpx().post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            return AIResponse(content="", model=active_model, raw_response=data)

        msg = choices[0].get("message", {})
        content = msg.get("content") or ""
        tool_calls: List[ToolCall] = []

        for tc in msg.get("tool_calls", []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            tool_calls.append(ToolCall(
                name=fn.get("name", ""),
                arguments=args,
                id=tc.get("id"),
            ))

        usage = data.get("usage", {})
        return AIResponse(
            content=content,
            model=active_model,
            tool_calls=tool_calls,
            finish_reason=choices[0].get("finish_reason"),
            usage=usage,
            raw_response=data,
        )

    def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        norm = self._normalize_texts(texts)
        active_model = model or self.default_embed_model
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": active_model, "input": norm}

        resp = _httpx().post(f"{self.base_url}/embeddings", headers=headers, json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        embeddings = [item.get("embedding", []) for item in data.get("data", [])]
        return EmbeddingResponse(embeddings=embeddings, model=active_model, usage=data.get("usage", {}))
