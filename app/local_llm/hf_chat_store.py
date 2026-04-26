"""
Hugging Face dataset-backed chat history storage.
Designed for low-volume academic use with whole-user JSON snapshots.
"""

from __future__ import annotations

import json
import os
import re
from io import BytesIO
from datetime import datetime
from typing import Any


def _get_secret(name: str, default: str = "") -> str:
    try:
        import streamlit as st
        val = st.secrets.get(name)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(name, default)


HF_CHAT_REPO_ID = _get_secret("HF_CHAT_REPO_ID", "")
HF_CHAT_TOKEN = _get_secret("HF_CHAT_TOKEN", "") or _get_secret("HF_TOKEN", "")


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _safe_username(username: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.@-]+", "_", username.strip())
    return cleaned or "anonymous"


def _repo_path(username: str) -> str:
    return f"ai_chat/{_safe_username(username)}.json"


def is_configured() -> bool:
    return bool(HF_CHAT_REPO_ID and HF_CHAT_TOKEN)


def _load_state(username: str) -> dict[str, Any]:
    if not is_configured():
        return {"conversations": [], "messages": {}, "next_conversation_id": 1, "next_message_id": 1}

    try:
        from huggingface_hub import hf_hub_download
        local_path = hf_hub_download(
            repo_id=HF_CHAT_REPO_ID,
            filename=_repo_path(username),
            repo_type="dataset",
            token=HF_CHAT_TOKEN,
            force_download=True,
        )
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"conversations": [], "messages": {}, "next_conversation_id": 1, "next_message_id": 1}


def _save_state(username: str, state: dict[str, Any], commit_message: str) -> None:
    if not is_configured():
        raise RuntimeError("HF chat storage is not configured.")

    try:
        from huggingface_hub import CommitOperationAdd, HfApi
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is required for HF chat storage.") from exc

    api = HfApi(token=HF_CHAT_TOKEN)
    data = json.dumps(state, indent=2, ensure_ascii=True).encode("utf-8")
    operation = CommitOperationAdd(
        path_in_repo=_repo_path(username),
        path_or_fileobj=BytesIO(data),
    )
    api.create_commit(
        repo_id=HF_CHAT_REPO_ID,
        repo_type="dataset",
        operations=[operation],
        commit_message=commit_message,
    )


def list_conversations(username: str) -> list[dict]:
    state = _load_state(username)
    rows = list(state.get("conversations", []))
    rows.sort(key=lambda x: (x.get("updated_at", ""), x.get("id", 0)), reverse=True)
    return rows


def get_conversation(username: str, conversation_id: int) -> dict | None:
    state = _load_state(username)
    for convo in state.get("conversations", []):
        if int(convo.get("id", -1)) == int(conversation_id):
            return convo
    return None


def create_conversation(username: str, *, title: str, mode: str, model_name: str, tone: str) -> int:
    state = _load_state(username)
    cid = int(state.get("next_conversation_id", 1))
    now = _utc_now()
    state["next_conversation_id"] = cid + 1
    state.setdefault("conversations", []).append(
        {
            "id": cid,
            "username": username,
            "title": title,
            "mode": mode,
            "model_name": model_name,
            "tone": tone,
            "created_at": now,
            "updated_at": now,
        }
    )
    state.setdefault("messages", {})[str(cid)] = []
    _save_state(username, state, commit_message=f"Create AI conversation {cid}")
    return cid


def update_conversation_meta(username: str, conversation_id: int, *, title: str | None = None, mode: str | None = None, model_name: str | None = None, tone: str | None = None) -> None:
    state = _load_state(username)
    for convo in state.get("conversations", []):
        if int(convo.get("id", -1)) == int(conversation_id):
            if title is not None:
                convo["title"] = title
            if mode is not None:
                convo["mode"] = mode
            if model_name is not None:
                convo["model_name"] = model_name
            if tone is not None:
                convo["tone"] = tone
            convo["updated_at"] = _utc_now()
            break
    _save_state(username, state, commit_message=f"Update AI conversation {conversation_id}")


def get_messages(username: str, conversation_id: int) -> list[dict]:
    state = _load_state(username)
    return list(state.get("messages", {}).get(str(conversation_id), []))


def add_message(username: str, conversation_id: int, *, role: str, content: str, context: dict | None = None) -> int:
    state = _load_state(username)
    mid = int(state.get("next_message_id", 1))
    now = _utc_now()
    state["next_message_id"] = mid + 1
    state.setdefault("messages", {}).setdefault(str(conversation_id), []).append(
        {
            "id": mid,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "context": context or {},
            "created_at": now,
        }
    )
    for convo in state.get("conversations", []):
        if int(convo.get("id", -1)) == int(conversation_id):
            convo["updated_at"] = now
            break
    _save_state(username, state, commit_message=f"Add AI message {mid}")
    return mid


def delete_conversation(username: str, conversation_id: int) -> None:
    state = _load_state(username)
    state["conversations"] = [
        c for c in state.get("conversations", [])
        if int(c.get("id", -1)) != int(conversation_id)
    ]
    state.get("messages", {}).pop(str(conversation_id), None)
    _save_state(username, state, commit_message=f"Delete AI conversation {conversation_id}")
