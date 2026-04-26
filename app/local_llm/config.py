"""
Configuration helpers for the local Ollama-backed LLM prototype.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_MODEL = "llama3.2:1b"
DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_CLOUD_MODEL = "qwen2.5:0.5b"
SUPPORTED_MODELS = [
    "llama3.2:1b",
    "llama3.2:3b",
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen2.5:3b",
    "gemma2:2b",
    "smollm2:360m",
]

CLOUD_SAFE_MODELS = [
    "qwen2.5:0.5b",
    "smollm2:360m",
]


@dataclass(frozen=True)
class LocalLLMConfig:
    """
    Lightweight configuration for a locally hosted Ollama model.

    Environment variables can override the defaults without requiring changes
    to source code:
      - SALARYSCOPE_LLM_BASE_URL
      - SALARYSCOPE_LLM_MODEL
      - SALARYSCOPE_LLM_TIMEOUT
    """

    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: int = 120

    @classmethod
    def from_env(cls) -> "LocalLLMConfig":
        timeout_raw = os.getenv("SALARYSCOPE_LLM_TIMEOUT", "120").strip()
        try:
            timeout = max(5, int(timeout_raw))
        except ValueError:
            timeout = 120

        return cls(
            base_url=os.getenv("SALARYSCOPE_LLM_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
            model=os.getenv("SALARYSCOPE_LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            timeout_seconds=timeout,
        )


def get_cloud_active_model() -> str:
    """
    Return the single model currently intended for the HF Space backend.
    """
    raw = os.getenv("HF_SPACE_ACTIVE_MODEL", "").strip() or os.getenv("SPACE_MODEL_NAME", "").strip()
    if raw and raw in SUPPORTED_MODELS:
        return raw
    return DEFAULT_CLOUD_MODEL
