from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_MODEL_NAME = os.getenv("SPACE_MODEL_NAME", "qwen2.5:3b").strip() or "qwen2.5:3b"
MAX_INPUT_CHARS = int(os.getenv("SPACE_MAX_INPUT_CHARS", "12000"))

MODEL_MAP = {
    "qwen2.5:3b": "Qwen/Qwen2.5-3B-Instruct",
    "gemma2:2b": "google/gemma-2-2b-it",
    "llama3.2:1b": "meta-llama/Llama-3.2-1B-Instruct",
    "llama3.2:3b": "meta-llama/Llama-3.2-3B-Instruct",
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
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model_name, tokenizer, model


def _trim_text(text: str) -> str:
    text = str(text or "").strip()
    if len(text) <= MAX_INPUT_CHARS:
        return text
    return text[:MAX_INPUT_CHARS]


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    if isinstance(payload.get("messages"), list):
        out = []
        for item in payload["messages"]:
            role = str(item.get("role", "user")).strip().lower()
            content = _trim_text(item.get("content", ""))
            if role in {"system", "user", "assistant"} and content:
                out.append({"role": role, "content": content})
        if out:
            return out

    system_prompt = _trim_text(payload.get("system_prompt", ""))
    user_prompt = _trim_text(payload.get("user_prompt", ""))
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    if user_prompt:
        msgs.append({"role": "user", "content": user_prompt})
    return msgs


def _build_prompt(tokenizer, messages: list[dict[str, str]]) -> str:
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    prompt_parts = []
    for item in messages:
        prompt_parts.append(f"{item['role'].upper()}: {item['content']}")
    prompt_parts.append("ASSISTANT:")
    return "\n\n".join(prompt_parts)


def _generate(payload: dict[str, Any]) -> dict[str, Any]:
    active_model_name, tokenizer, model = _load_model_bundle()
    requested_model = _normalize_model_name(payload.get("model_name"))

    messages = _extract_messages(payload)
    if not messages:
        return {
            "content": "No valid prompt content was provided.",
            "model": active_model_name,
            "active_repo": MODEL_MAP[active_model_name],
        }

    prompt_text = _build_prompt(tokenizer, messages)
    inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True)

    requested_num_predict = int(payload.get("num_predict", 220) or 220)
    max_new_tokens = max(48, min(requested_num_predict, 320))
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


def predict(payload: dict[str, Any]) -> dict[str, Any]:
    return _generate(payload)


with gr.Blocks(title="SalaryScope HF Space Assistant") as demo:
    gr.Markdown(
        """
        # SalaryScope HF Space Assistant
        This Space exposes a small API endpoint used by SalaryScope when running on Streamlit Cloud.
        """
    )

    input_box = gr.JSON(label="Request Payload")
    output_box = gr.JSON(label="Response Payload")
    run_btn = gr.Button("Run")
    run_btn.click(fn=predict, inputs=input_box, outputs=output_box, api_name="/predict")


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch()
