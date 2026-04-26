from __future__ import annotations

import os
import json
from functools import lru_cache
from typing import Any

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_MODEL_NAME = os.getenv("SPACE_MODEL_NAME", "qwen2.5:0.5b").strip() or "qwen2.5:0.5b"
MAX_INPUT_CHARS = int(os.getenv("SPACE_MAX_INPUT_CHARS", "5000"))
MAX_NEW_TOKENS_CAP = int(os.getenv("SPACE_MAX_NEW_TOKENS", "360"))

MODEL_MAP = {
    "qwen2.5:0.5b": "Qwen/Qwen2.5-0.5B-Instruct",
    "qwen2.5:1.5b": "Qwen/Qwen2.5-1.5B-Instruct",
    "qwen2.5:3b": "Qwen/Qwen2.5-3B-Instruct",
    "gemma2:2b": "google/gemma-2-2b-it",
    "llama3.2:1b": "meta-llama/Llama-3.2-1B-Instruct",
    "llama3.2:3b": "meta-llama/Llama-3.2-3B-Instruct",
    "smollm2:360m": "HuggingFaceTB/SmolLM2-360M-Instruct",
}


def _normalize_model_name(requested: str | None) -> str:
    raw = (requested or DEFAULT_MODEL_NAME).strip()
    return raw if raw in MODEL_MAP else DEFAULT_MODEL_NAME


@lru_cache(maxsize=1)
def _load_model_bundle() -> tuple[str, Any, Any]:
    model_name = _normalize_model_name(DEFAULT_MODEL_NAME)
    repo_id = MODEL_MAP[model_name]

    tokenizer = AutoTokenizer.from_pretrained(repo_id)
    model = AutoModelForCausalLM.from_pretrained(
        repo_id,
        torch_dtype="auto",
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model_name, tokenizer, model


def _trim_text(text: str) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= MAX_INPUT_CHARS:
        return cleaned
    return cleaned[:MAX_INPUT_CHARS]


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_messages = payload.get("messages")
    if isinstance(raw_messages, list):
        messages = []
        for item in raw_messages:
            role = str(item.get("role", "user")).strip().lower()
            content = _trim_text(item.get("content", ""))
            if role in {"system", "user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        if messages:
            return messages

    system_prompt = _trim_text(payload.get("system_prompt", ""))
    user_prompt = _trim_text(payload.get("user_prompt", ""))
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
    return messages


def _build_prompt(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    prompt_parts = [f"{item['role'].upper()}: {item['content']}" for item in messages]
    prompt_parts.append("ASSISTANT:")
    return "\n\n".join(prompt_parts)


def _generate_response(payload: dict[str, Any]) -> dict[str, Any]:
    active_model_name, tokenizer, model = _load_model_bundle()
    requested_model = _normalize_model_name(payload.get("model_name"))
    messages = _extract_messages(payload)

    if not messages:
        return {
            "content": "No valid prompt content was provided.",
            "model": active_model_name,
            "active_repo": MODEL_MAP[active_model_name],
            "requested_model": requested_model,
            "task": str(payload.get("task", "assistant_chat")),
        }

    prompt_text = _build_prompt(tokenizer, messages)
    inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True)
    requested_num_predict = int(payload.get("num_predict", 180) or 180)
    max_new_tokens = max(48, min(requested_num_predict, MAX_NEW_TOKENS_CAP))
    temperature = float(payload.get("temperature", 0.2) or 0.2)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0.05,
            temperature=max(temperature, 0.01),
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    prompt_len = inputs["input_ids"].shape[1]
    generated_ids = output_ids[0][prompt_len:]
    content = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    if not content:
        content = "I could not generate a response for that request."

    return {
        "content": content,
        "model": active_model_name,
        "active_repo": MODEL_MAP[active_model_name],
        "requested_model": requested_model,
        "task": str(payload.get("task", "assistant_chat")),
    }


def predict(payload_json: str | None) -> dict[str, Any]:
    try:
        payload = json.loads(str(payload_json or "").strip() or "{}")
    except json.JSONDecodeError as exc:
        return {
            "content": "The request payload was not valid JSON.",
            "error": str(exc),
            "model": _normalize_model_name(DEFAULT_MODEL_NAME),
            "active_repo": MODEL_MAP[_normalize_model_name(DEFAULT_MODEL_NAME)],
            "task": "assistant_chat",
        }

    request_payload = payload if isinstance(payload, dict) else {}
    try:
        return _generate_response(request_payload)
    except Exception as exc:
        fallback_model = _normalize_model_name(DEFAULT_MODEL_NAME)
        return {
            "content": (
                "The Hugging Face assistant backend could not complete this request. "
                "Try a smaller model or restart the Space."
            ),
            "error": str(exc),
            "model": fallback_model,
            "active_repo": MODEL_MAP[fallback_model],
            "task": str(request_payload.get("task", "assistant_chat")),
        }


api_view = gr.Interface(
    fn=predict,
    inputs=gr.Textbox(label="Request Payload", lines=12),
    outputs=gr.JSON(label="Response Payload"),
    api_name="predict",
    allow_flagging="never",
    title="SalaryScope HF Space Assistant",
    description=(
        "This Space exposes a small JSON API endpoint used by SalaryScope "
        "when running on Streamlit Cloud."
    ),
)


if __name__ == "__main__":
    api_view.queue(default_concurrency_limit=1).launch(ssr_mode=False, show_api=True)
