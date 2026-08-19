"""Google Gemini AI Driver for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

import httpx

from engine.ai.contracts import AIResponse, EmbeddingResponse, ToolCall
from engine.ai.drivers.base import BaseAIDriver


class GeminiAIDriver(BaseAIDriver):
    """Google Gemini AI Driver using direct REST API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

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
            raise ValueError("GEMINI_API_KEY is not set in environment or config/ai.py")

        url = f"{self.base_url}/models/{active_model}:generateContent?key={self.api_key}"

        contents: List[Dict[str, Any]] = []
        system_instruction: Optional[Dict[str, Any]] = None

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": text}]}
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [{"text": text}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if tools:
            # Map standard tools to Gemini functionDeclarations format
            func_decls = []
            for t in tools:
                func_decls.append({
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                })
            payload["tools"] = [{"functionDeclarations": func_decls}]

        resp = httpx.post(url, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return AIResponse(content="", model=active_model, raw_response=data)

        first_cand = candidates[0]
        content_parts = first_cand.get("content", {}).get("parts", [])
        text_content = ""
        tool_calls: List[ToolCall] = []

        for p in content_parts:
            if "text" in p:
                text_content += p["text"]
            if "functionCall" in p:
                fc = p["functionCall"]
                tool_calls.append(ToolCall(
                    name=fc.get("name", ""),
                    arguments=fc.get("args", {}),
                ))

        usage_meta = data.get("usageMetadata", {})
        usage = {
            "prompt_tokens": usage_meta.get("promptTokenCount", 0),
            "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            "total_tokens": usage_meta.get("totalTokenCount", 0),
        }

        return AIResponse(
            content=text_content,
            model=active_model,
            tool_calls=tool_calls,
            finish_reason=first_cand.get("finishReason"),
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
            raise ValueError("GEMINI_API_KEY is not set")

        url = f"{self.base_url}/models/{active_model}:batchEmbedContents?key={self.api_key}"
        requests = [{"model": f"models/{active_model}", "content": {"parts": [{"text": t}]}} for t in norm]
        payload = {"requests": requests}

        resp = httpx.post(url, json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()

        embeddings = [item.get("values", []) for item in data.get("embeddings", [])]
        return EmbeddingResponse(embeddings=embeddings, model=active_model, raw_response=data)
