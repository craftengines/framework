"""AI SDK Configuration for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

default = os.getenv("AI_DEFAULT_DRIVER", "mock")

drivers = {
    "gemini": {
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "embed_model": os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004"),
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "embed_model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
    },
    "claude": {
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
    },
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
    },
    "mock": {
        "model": "mock-ai-model",
    },
}
