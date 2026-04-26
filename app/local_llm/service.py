"""
High-level local LLM services for the SalaryScope assistant.
"""

from __future__ import annotations

from .client import LocalLLMError, LocalLLMTimeoutError, OllamaLocalClient
from .config import CLOUD_SAFE_MODELS, LocalLLMConfig, SUPPORTED_MODELS, get_cloud_active_model
from .deployment import deployment_label, is_local_runtime
from .hf_space_client import HFSpaceClient
from .knowledge import APP_DEVELOPER_TEXT, APP_LIMITATIONS_TEXT, APP_OVERVIEW_TEXT
from .prompts import (
    build_chat_system_prompt,
    build_chat_user_prompt,
    build_negotiation_script_prompts,
    build_resume_summary_prompts,
)

FAST_CHAT_MODES = {"App Help", "Prediction Companion"}
DRAFT_HEAVIER_MODES = {"Negotiation Assistant", "Resume Assistant", "Report Writer"}


def _resolve_generation_settings(mode: str, profile: str) -> tuple[float, int | None]:
    """
    Return (temperature, num_predict) tuned for local speed vs richness.
    """
    if profile == "Fast":
        if mode in FAST_CHAT_MODES:
            return 0.15, None
        return 0.2, None
    if profile == "Balanced":
        if mode in FAST_CHAT_MODES:
            return 0.2, None
        return 0.25, None
    if mode in FAST_CHAT_MODES:
        return 0.2, None
    return 0.3, None


def _resolve_cloud_generation_settings(mode: str, profile: str) -> tuple[float, int | None]:
    """
    Cloud path with no app-side response ceiling.
    """
    if profile == "Fast":
        if mode in FAST_CHAT_MODES:
            return 0.15, None
        return 0.2, None
    if profile == "Balanced":
        if mode in FAST_CHAT_MODES:
            return 0.2, None
        return 0.25, None
    if mode in FAST_CHAT_MODES:
        return 0.2, None
    return 0.3, None


def _looks_truncated(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    if cleaned.endswith(("...", "…", ":", ",", ";", " and", " or", " if", " we could explore")):
        return True
    if cleaned.count("[") != cleaned.count("]"):
        return True
    return cleaned[-1] not in {".", "!", "?", "\""}


def _merge_continuation_text(initial: str, continuation: str) -> str:
    left = str(initial or "").rstrip()
    right = str(continuation or "").lstrip()
    if not left:
        return right
    if not right:
        return left
    if right[:40] and right[:40] in left:
        return left
    joiner = "" if left.endswith(("-", "/")) else " "
    return f"{left}{joiner}{right}".strip()


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _filter_recent_messages_for_context(
    recent_messages: list[dict] | None,
    *,
    mode: str,
    context_payload: dict | None,
) -> list[dict]:
    if not recent_messages:
        return []

    selected_context_label = str((context_payload or {}).get("selected_context_label") or "").strip()
    filtered_reversed: list[dict] = []
    started = False

    for item in reversed(recent_messages):
        context = item.get("context") or {}
        item_mode = str(context.get("mode") or "").strip()
        item_label = ""
        if isinstance(context.get("context_payload"), dict):
            item_label = str(context["context_payload"].get("selected_context_label") or "").strip()
        else:
            item_label = str(context.get("selected_context_label") or "").strip()

        mode_matches = item_mode == mode
        label_matches = (
            not selected_context_label
            or not item_label
            or item_label == selected_context_label
        )

        if mode_matches and label_matches:
            filtered_reversed.append(item)
            started = True
            continue

        if started:
            break

    return list(reversed(filtered_reversed))[-4:]


def _direct_prediction_companion_reply(user_message: str, context_payload: dict | None) -> str | None:
    payload = context_payload or {}
    predicted_salary = str(payload.get("predicted_salary_text") or "").strip()
    prediction_range = str(payload.get("prediction_range_text") or "").strip()
    job_title = str(payload.get("job_title") or "the current role").strip()
    location = str(payload.get("location") or "the current location").strip()
    experience = str(payload.get("years_experience") or "the current profile").strip()
    extra_context = str(payload.get("extra_context") or "").strip()
    message = _normalize_text(user_message)

    if not predicted_salary:
        return None

    wants_simple_explanation = any(
        phrase in message
        for phrase in (
            "explain the latest prediction",
            "explain latest prediction",
            "explain this prediction",
            "simple terms",
            "without changing the estimate",
            "what does the salary range",
            "what does the context shown",
            "what does this prediction mean",
        )
    )

    if not wants_simple_explanation:
        return None

    experience_phrase = ""
    if experience and experience.lower() != "not provided":
        experience_phrase = experience
        if any(ch.isdigit() for ch in experience) and "year" not in experience.lower() and "level" not in experience.lower():
            experience_phrase = f"{experience} years of experience"

    lines = [
        f"SalaryScope currently estimates {predicted_salary} for {job_title} in {location}.",
    ]
    if experience_phrase:
        lines.append(f"This estimate is based on the profile context currently shown in the app, including {experience_phrase}.")
    if prediction_range:
        lines.append(f"The companion range shown by the app is {prediction_range}.")
    if extra_context and extra_context.lower() != "none":
        lines.append(f"Additional context from the result: {extra_context}.")
    lines.append("This is the app's model-based estimate, useful as a structured reference for interpretation and discussion.")
    return " ".join(lines)


def _direct_app_help_reply(user_message: str) -> str | None:
    message = _normalize_text(user_message)
    overview_phrases = (
        "what is this application",
        "what is this app",
        "what is salaryscope",
        "what does this application do",
        "tell me about this application",
        "explain this application",
    )
    limitation_phrases = (
        "what are your limitations",
        "what are the limitations",
        "limitations of this app",
        "limitations of salaryscope",
        "what can you not do",
    )
    wants_overview = any(phrase in message for phrase in overview_phrases)
    wants_limitations = any(phrase in message for phrase in limitation_phrases)
    wants_joke = any(
        phrase in message
        for phrase in (
            "tell me a joke",
            "say a joke",
            "make me laugh",
            "joke",
        )
    )
    wants_developer = any(
        phrase in message
        for phrase in (
            "who is the developer",
            "who developed this app",
            "who made this app",
            "who built this app",
            "developer of this app",
            "why was it made",
            "why was this app made",
            "why did you make this app",
        )
    )

    parts: list[str] = []
    if wants_joke:
        parts.append(
            "Quick one: SalaryScope does not ask for a raise itself because it already has too many prediction tabs to manage."
        )
    if wants_developer:
        parts.append(APP_DEVELOPER_TEXT)
    if wants_overview and not any(
        phrase in message for phrase in ("how should i use", "how do i use", "walk me through", "compare", "difference between")
    ):
        parts.append(APP_OVERVIEW_TEXT)
    if wants_limitations:
        parts.append(APP_LIMITATIONS_TEXT)

    if parts:
        return "\n\n".join(parts)

    return None


def _continue_cloud_response(
    *,
    mode: str,
    cloud_model: str,
    system_prompt: str,
    messages: list[dict],
    content: str,
    temperature: float,
    num_predict: int | None,
) -> str:
    if not _looks_truncated(content):
        return content

    continuation_messages = list(messages)
    continuation_messages.append({"role": "assistant", "content": content})
    continuation_messages.append(
        {
            "role": "user",
            "content": (
                "Continue exactly from where you stopped. Return only the remaining text, "
                "avoid repeating earlier lines, and finish with a complete final sentence."
            ),
        }
    )
    continuation_result = _space_client().predict(
        {
            "task": "assistant_chat",
            "mode": mode,
            "model_name": cloud_model,
            "messages": continuation_messages,
            "temperature": min(temperature, 0.2),
            "num_predict": num_predict,
            "deployment": deployment_label(),
        }
    )
    continuation = str(continuation_result.get("content", "")).strip()
    return _merge_continuation_text(content, continuation) if continuation else content


def _client_for(model_name: str | None = None) -> OllamaLocalClient:
    config = LocalLLMConfig.from_env()
    if model_name:
        config = LocalLLMConfig(
            base_url=config.base_url,
            model=model_name,
            timeout_seconds=config.timeout_seconds,
        )
    return OllamaLocalClient(config)


def _continue_local_response(
    *,
    client: OllamaLocalClient,
    messages: list[dict[str, str]],
    content: str,
    temperature: float,
    num_predict: int | None,
    timeout_seconds: int | None = None,
) -> str:
    if not _looks_truncated(content):
        return content

    continuation_messages = list(messages)
    continuation_messages.append({"role": "assistant", "content": content})
    continuation_messages.append(
        {
            "role": "user",
            "content": (
                "Continue exactly from where you stopped. Return only the remaining text, "
                "avoid repeating earlier lines, and finish with a complete final sentence."
            ),
        }
    )
    continuation = client.chat_messages(
        messages=continuation_messages,
        temperature=min(temperature, 0.2),
        num_predict=num_predict,
        timeout_seconds=timeout_seconds,
    )
    return _merge_continuation_text(content, continuation) if continuation else content


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
        content = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.3, num_predict=None)
        content = _continue_local_response(
            client=client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            content=content,
            temperature=0.3,
            num_predict=None,
            timeout_seconds=max(client.config.timeout_seconds, 180),
        )
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
                "num_predict": None,
                "deployment": deployment_label(),
            }
        )
        content = str(result.get("content", "")).strip()
        content = _continue_cloud_response(
            mode="Resume Assistant",
            cloud_model=cloud_model,
            system_prompt=system_prompt,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            content=content,
            temperature=0.25,
            num_predict=None,
        )
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
        content = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.45, num_predict=None)
        content = _continue_local_response(
            client=client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            content=content,
            temperature=0.45,
            num_predict=None,
            timeout_seconds=max(client.config.timeout_seconds, 300),
        )
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
                "num_predict": None,
                "deployment": deployment_label(),
            }
        )
        content = str(result.get("content", "")).strip()
        content = _continue_cloud_response(
            mode="Negotiation Assistant",
            cloud_model=cloud_model,
            system_prompt=system_prompt,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            content=content,
            temperature=0.35,
            num_predict=None,
        )
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
    direct_reply = None
    if mode == "App Help":
        direct_reply = _direct_app_help_reply(user_message)
    elif mode == "Prediction Companion":
        direct_reply = _direct_prediction_companion_reply(user_message, context_payload)
    if direct_reply is not None:
        return {
            "mode": mode,
            "model": "deterministic-app-context",
            "performance_profile": performance_profile,
            "content": direct_reply,
        }

    filtered_recent_messages = _filter_recent_messages_for_context(
        recent_messages,
        mode=mode,
        context_payload=context_payload,
    )

    system_prompt = build_chat_system_prompt(
        mode=mode,
        tone=tone,
        context_payload=context_payload,
    )

    messages = [{"role": "system", "content": system_prompt}]
    for item in filtered_recent_messages:
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
            content = _continue_local_response(
                client=client,
                messages=messages,
                content=content,
                temperature=temperature,
                num_predict=num_predict,
                timeout_seconds=max(client.config.timeout_seconds, 180),
            )
        except LocalLLMTimeoutError:
            retry_messages = [{"role": "system", "content": system_prompt}]
            for item in filtered_recent_messages[-2:]:
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
            retry_predict = num_predict
            content = client.chat_messages(
                messages=retry_messages,
                temperature=retry_temperature,
                num_predict=retry_predict,
                timeout_seconds=max(client.config.timeout_seconds, 180),
            )
            content = _continue_local_response(
                client=client,
                messages=retry_messages,
                content=content,
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
        content = _continue_cloud_response(
            mode=mode,
            cloud_model=cloud_model,
            system_prompt=system_prompt,
            messages=messages,
            content=content,
            temperature=temperature,
            num_predict=num_predict,
        )
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
