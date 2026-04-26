"""
High-level local LLM services for the SalaryScope assistant.
"""

from __future__ import annotations

from .client import LocalLLMError, LocalLLMTimeoutError, OllamaLocalClient
from .config import CLOUD_SAFE_MODELS, LocalLLMConfig, SUPPORTED_MODELS, get_cloud_active_model
from .deployment import deployment_label, is_local_runtime
from .hf_space_client import HFSpaceClient
from .prompts import (
    build_chat_system_prompt,
    build_chat_user_prompt,
    build_negotiation_script_prompts,
    build_resume_summary_prompts,
)

FAST_CHAT_MODES = {"App Help", "Prediction Companion"}
DRAFT_HEAVIER_MODES = {"Negotiation Assistant", "Resume Assistant", "Report Writer"}


def _resolve_generation_settings(mode: str, profile: str) -> tuple[float, int]:
    """
    Return (temperature, num_predict) tuned for local speed vs richness.
    """
    if profile == "Fast":
        if mode in FAST_CHAT_MODES:
            return 0.15, 180
        return 0.2, 160
    if profile == "Balanced":
        if mode in FAST_CHAT_MODES:
            return 0.2, 220
        return 0.25, 260
    if mode in FAST_CHAT_MODES:
        return 0.2, 220
    return 0.3, 360


def _resolve_cloud_generation_settings(mode: str, profile: str) -> tuple[float, int]:
    """
    Lighter defaults for the free HF Space path.
    """
    if profile == "Fast":
        if mode in FAST_CHAT_MODES:
            return 0.15, 96
        return 0.2, 140
    if profile == "Balanced":
        if mode in FAST_CHAT_MODES:
            return 0.2, 120
        return 0.25, 180
    if mode in FAST_CHAT_MODES:
        return 0.2, 140
    return 0.3, 220


def _looks_truncated(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    if cleaned.endswith(("...", "…", ":", ",", ";", " and", " or", " if", " we could explore")):
        return True
    if cleaned.count("[") != cleaned.count("]"):
        return True
    return cleaned[-1] not in {".", "!", "?", "\""}


def _client_for(model_name: str | None = None) -> OllamaLocalClient:
    config = LocalLLMConfig.from_env()
    if model_name:
        config = LocalLLMConfig(
            base_url=config.base_url,
            model=model_name,
            timeout_seconds=config.timeout_seconds,
        )
    return OllamaLocalClient(config)


def _space_client() -> HFSpaceClient:
    return HFSpaceClient()


def is_local_llm_available() -> tuple[bool, str]:
    """Return whether the local Ollama endpoint is reachable."""
    if is_local_runtime():
        return _client_for().is_available()
    return _space_client().is_available()


def get_backend_label() -> str:
    return "Local Ollama" if is_local_runtime() else "Hugging Face Space"


def list_local_models() -> list[str]:
    """Return locally available Ollama models."""
    detected = _client_for().list_models() if is_local_runtime() else []
    merged = []
    for name in [*SUPPORTED_MODELS, *detected]:
        if name not in merged:
            merged.append(name)
    return merged


def list_assistant_models() -> list[str]:
    """
    Return the models the UI should expose for the current deployment target.
    Local runs can show multiple Ollama options; cloud runs should expose the
    single deployed HF Space model plus tiny safe fallbacks for documentation.
    """
    if is_local_runtime():
        return list_local_models()
    active = get_cloud_active_model()
    models = [active]
    for name in CLOUD_SAFE_MODELS:
        if name not in models:
            models.append(name)
    return models


def generate_resume_summary(
    *,
    candidate_name: str,
    target_role: str,
    years_experience: str,
    education: str,
    skills_csv: str,
    resume_text: str,
    model_name: str | None = None,
) -> dict:
    system_prompt, user_prompt = build_resume_summary_prompts(
        candidate_name=candidate_name,
        target_role=target_role,
        years_experience=years_experience,
        education=education,
        skills_csv=skills_csv,
        resume_text=resume_text,
    )
    if is_local_runtime():
        client = _client_for(model_name)
        content = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.3, num_predict=260)
        model_used = client.config.model
    else:
        cloud_model = get_cloud_active_model()
        result = _space_client().predict(
            {
                "task": "resume_summary",
                "model_name": cloud_model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": 0.25,
                "num_predict": 140,
                "deployment": deployment_label(),
            }
        )
        content = str(result.get("content", "")).strip()
        if mode in DRAFT_HEAVIER_MODES and _looks_truncated(content):
            retry_messages = [{"role": "system", "content": system_prompt}]
            retry_messages.append(
                {
                    "role": "user",
                    "content": (
                        build_chat_user_prompt(
                            user_message=user_message,
                            context_note=context_note,
                        )
                        + "\n\nExtra instruction: rewrite the answer more compactly so it finishes cleanly. "
                          "If drafting an email, keep it under 120 words and include a short closing."
                    ),
                }
            )
            retry_result = _space_client().predict(
                {
                    "task": "assistant_chat",
                    "mode": mode,
                    "model_name": cloud_model,
                    "tone": tone,
                    "performance_profile": "Fast",
                    "context_note": context_note,
                    "messages": retry_messages,
                    "temperature": min(temperature, 0.2),
                    "num_predict": min(max(num_predict, 160), 200),
                    "deployment": deployment_label(),
                }
            )
            retry_content = str(retry_result.get("content", "")).strip()
            if retry_content:
                content = retry_content
        model_used = str(result.get("model", cloud_model))
    return {
        "mode": "Resume Assistant",
        "model": model_used,
        "content": content,
    }


def generate_negotiation_script(
    *,
    job_title: str,
    location: str,
    years_experience: str,
    predicted_salary_text: str,
    target_salary_text: str = "",
    negotiation_style: str = "Professional and confident",
    extra_context: str = "",
    model_name: str | None = None,
) -> dict:
    system_prompt, user_prompt = build_negotiation_script_prompts(
        job_title=job_title,
        location=location,
        years_experience=years_experience,
        predicted_salary_text=predicted_salary_text,
        target_salary_text=target_salary_text,
        negotiation_style=negotiation_style,
        extra_context=extra_context,
    )
    if is_local_runtime():
        client = _client_for(model_name)
        content = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.45, num_predict=320)
        model_used = client.config.model
    else:
        cloud_model = get_cloud_active_model()
        result = _space_client().predict(
            {
                "task": "negotiation_script",
                "model_name": cloud_model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": 0.35,
                "num_predict": 160,
                "deployment": deployment_label(),
            }
        )
        content = str(result.get("content", "")).strip()
        model_used = str(result.get("model", cloud_model))
    return {
        "mode": "Negotiation Assistant",
        "model": model_used,
        "content": content,
    }


def generate_assistant_reply(
    *,
    mode: str,
    user_message: str,
    context_payload: dict | None,
    recent_messages: list[dict] | None = None,
    tone: str = "Professional and grounded",
    model_name: str | None = None,
    context_note: str = "",
    performance_profile: str = "Balanced",
) -> dict:
    """
    Generate a multi-turn assistant response grounded in SalaryScope context.
    """
    system_prompt = build_chat_system_prompt(
        mode=mode,
        tone=tone,
        context_payload=context_payload,
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in (recent_messages or [])[-4:]:
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append(
        {
            "role": "user",
            "content": build_chat_user_prompt(
                user_message=user_message,
                context_note=context_note,
            ),
        }
    )

    temperature, num_predict = (
        _resolve_generation_settings(mode, performance_profile)
        if is_local_runtime()
        else _resolve_cloud_generation_settings(mode, performance_profile)
    )
    if is_local_runtime():
        client = _client_for(model_name)
        try:
            content = client.chat_messages(
                messages=messages,
                temperature=temperature,
                num_predict=num_predict,
            )
        except LocalLLMTimeoutError:
            retry_messages = [{"role": "system", "content": system_prompt}]
            for item in (recent_messages or [])[-2:]:
                role = str(item.get("role", "")).strip().lower()
                content_prev = str(item.get("content", "")).strip()
                if role in {"user", "assistant"} and content_prev:
                    retry_messages.append({"role": role, "content": content_prev})
            retry_messages.append(
                {
                    "role": "user",
                    "content": (
                        build_chat_user_prompt(
                            user_message=user_message,
                            context_note=context_note,
                        )
                        + "\n\nExtra instruction: reply in 3 to 5 short sentences only."
                    ),
                }
            )
            retry_temperature = min(temperature, 0.15)
            retry_predict = min(num_predict, 120)
            content = client.chat_messages(
                messages=retry_messages,
                temperature=retry_temperature,
                num_predict=retry_predict,
                timeout_seconds=max(client.config.timeout_seconds, 180),
            )
        model_used = client.config.model
    else:
        cloud_model = get_cloud_active_model()
        result = _space_client().predict(
            {
                "task": "assistant_chat",
                "mode": mode,
                "model_name": cloud_model,
                "tone": tone,
                "performance_profile": performance_profile,
                "context_note": context_note,
                "messages": messages,
                "temperature": temperature,
                "num_predict": num_predict,
                "deployment": deployment_label(),
            }
        )
        content = str(result.get("content", "")).strip()
        model_used = str(result.get("model", cloud_model))
    return {
        "mode": mode,
        "model": model_used,
        "performance_profile": performance_profile,
        "content": content,
    }


__all__ = [
    "LocalLLMError",
    "generate_assistant_reply",
    "generate_negotiation_script",
    "generate_resume_summary",
    "is_local_llm_available",
    "list_assistant_models",
    "list_local_models",
    "get_backend_label",
]
