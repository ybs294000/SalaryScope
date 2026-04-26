"""
Hugging Face Space API client for cloud inference.
Uses the official queue-based Gradio HTTP flow documented by Hugging Face.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from .client import LocalLLMError, LocalLLMTimeoutError


def _get_secret(name: str, default: str = "") -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(name, default)


HF_SPACE_URL = _get_secret("HF_SPACE_URL", "").rstrip("/")
HF_SPACE_API_NAME = _get_secret("HF_SPACE_API_NAME", "/predict")
HF_SPACE_TOKEN = _get_secret("HF_SPACE_TOKEN", "") or _get_secret("HF_TOKEN", "")
HF_SPACE_TIMEOUT = int(_get_secret("HF_SPACE_TIMEOUT", "120") or "120")
HF_SPACE_POLL_INTERVAL = float(_get_secret("HF_SPACE_POLL_INTERVAL", "1.5") or "1.5")


class HFSpaceClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_name: str | None = None,
        token: str | None = None,
        timeout_seconds: int | None = None,
    ):
        self.base_url = (base_url or HF_SPACE_URL).rstrip("/")
        self.api_name = (api_name or HF_SPACE_API_NAME).lstrip("/")
        self.token = token if token is not None else HF_SPACE_TOKEN
        self.timeout_seconds = timeout_seconds or HF_SPACE_TIMEOUT

    def is_available(self) -> tuple[bool, str]:
        if not self.base_url:
            return False, "HF Space URL is not configured."
        try:
            response = requests.get(
                f"{self.base_url}/gradio_api/openapi.json",
                timeout=min(10, self.timeout_seconds),
                headers=self._headers(),
            )
            response.raise_for_status()
            return True, "Hugging Face Space is reachable."
        except requests.RequestException as exc:
            return False, f"HF Space not reachable: {exc}"

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url:
            raise LocalLLMError("HF Space URL is not configured.")

        submit_url = f"{self.base_url}/gradio_api/call/{self.api_name}"
        result_url_prefix = f"{self.base_url}/gradio_api/call/{self.api_name}"

        try:
            submit_response = requests.post(
                submit_url,
                json={"data": [payload]},
                headers=self._headers(content_type=True),
                timeout=self.timeout_seconds,
            )
            submit_response.raise_for_status()
            body = submit_response.json()
            event_id = body.get("event_id")
            if not event_id:
                raise LocalLLMError("HF Space response did not include an event_id.")
        except requests.exceptions.ReadTimeout as exc:
            raise LocalLLMTimeoutError(
                f"HF Space request timed out after {self.timeout_seconds} seconds."
            ) from exc
        except requests.RequestException as exc:
            raise LocalLLMError(f"HF Space request failed: {exc}") from exc
        except ValueError as exc:
            raise LocalLLMError("HF Space returned invalid JSON.") from exc

        deadline = time.time() + self.timeout_seconds
        result_url = f"{result_url_prefix}/{event_id}"

        try:
            with requests.get(
                result_url,
                headers=self._headers(),
                stream=True,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                last_data = None
                for raw_line in response.iter_lines(decode_unicode=True):
                    if time.time() > deadline:
                        raise LocalLLMTimeoutError(
                            f"HF Space response timed out after {self.timeout_seconds} seconds."
                        )
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line.startswith("data: "):
                        payload_str = line[6:]
                        try:
                            last_data = json.loads(payload_str)
                        except json.JSONDecodeError:
                            last_data = payload_str
                    if line == "event: complete":
                        continue
                if last_data is None:
                    raise LocalLLMError("HF Space returned no completion payload.")
        except requests.exceptions.ReadTimeout as exc:
            raise LocalLLMTimeoutError(
                f"HF Space response timed out after {self.timeout_seconds} seconds."
            ) from exc
        except requests.RequestException as exc:
            raise LocalLLMError(f"HF Space result polling failed: {exc}") from exc

        if isinstance(last_data, list) and last_data:
            result = last_data[0]
        else:
            result = last_data

        if isinstance(result, dict):
            return result
        if isinstance(result, str):
            return {"content": result}
        return {"content": str(result)}

    def _headers(self, *, content_type: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers
