"""Base AI Driver for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from engine.ai.contracts import AIResponse, EmbeddingResponse, ToolCall


class BaseAIDriver:
    """Base class for AI provider drivers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_model = config.get("model", "default")
        self.default_embed_model = config.get("embed_model", "default-embed")

    def _normalize_texts(self, texts: Union[str, List[str]]) -> List[str]:
        if isinstance(texts, str):
            return [texts]
        return list(texts)
