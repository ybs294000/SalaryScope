"""
Minimal Ollama HTTP client used by the local LLM prototype.
"""

from __future__ import annotations

from typing import Any

import requests
from requests.exceptions import ReadTimeout

from .config import LocalLLMConfig


class LocalLLMError(RuntimeError):
    """Raised when the local LLM request fails."""


class LocalLLMTimeoutError(LocalLLMError):
    """Raised when the local LLM request times out."""


class OllamaLocalClient:
    """Small wrapper around Ollama's local chat API."""

    def __init__(self, config: LocalLLMConfig | None = None):
        self.config = config or LocalLLMConfig.from_env()

    def is_available(self) -> tuple[bool, str]:
        """
        Check whether the local Ollama server is reachable.
        """
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=min(5, self.config.timeout_seconds),
            )
            response.raise_for_status()
            body = response.json()
            models = body.get("models", []) or []
            return True, f"Ollama is reachable. {len(models)} local model(s) detected."
        except requests.RequestException as exc:
            return False, f"Ollama not reachable at {self.config.base_url}: {exc}"
        except ValueError:
            return True, "Ollama is reachable."

    def list_models(self) -> list[str]:
        """
        Return locally available Ollama model names.
        """
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=min(5, self.config.timeout_seconds),
            )
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            return [self.config.model]

        names = []
        for item in body.get("models", []) or []:
            name = str(item.get("name", "")).strip()
            if name:
                names.append(name)
        return names or [self.config.model]

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        num_predict: int | None = None,
        timeout_seconds: int | None = None,
    ) -> str:
        """
        Send a single-turn chat request and return the model response text.
        """
        return self.chat_messages(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            num_predict=num_predict,
            timeout_seconds=timeout_seconds,
        )

    def chat_messages(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        num_predict: int | None = None,
        timeout_seconds: int | None = None,
    ) -> str:
        """
        Send a multi-message chat request and return the model response text.
        """
        options: dict[str, Any] = {
            "temperature": temperature,
        }
        if num_predict is not None:
            options["num_predict"] = num_predict

        payload: dict[str, Any] = {
            "model": self.config.model,
            "stream": False,
            "options": options,
            "messages": messages,
        }
        timeout_value = timeout_seconds or self.config.timeout_seconds

        try:
            response = requests.post(
                f"{self.config.base_url}/api/chat",
                json=payload,
                timeout=timeout_value,
            )
            response.raise_for_status()
            body = response.json()
        except ReadTimeout as exc:
            raise LocalLLMTimeoutError(
                f"Local Ollama request timed out after {timeout_value} seconds."
            ) from exc
        except requests.RequestException as exc:
            raise LocalLLMError(f"Local Ollama request failed: {exc}") from exc
        except ValueError as exc:
            raise LocalLLMError("Local Ollama returned non-JSON output.") from exc

        message = body.get("message", {})
        content = str(message.get("content", "")).strip()
        if not content:
            raise LocalLLMError("Local Ollama returned an empty response.")
        return content
