"""
Storage router: local SQLite when local, HF dataset repo for logged-in cloud users.
"""

from __future__ import annotations

from .deployment import is_local_runtime
from . import storage as sqlite_store
from . import hf_chat_store as hf_store


def _use_hf(username: str) -> bool:
    return (not is_local_runtime()) and username != "local_anonymous" and hf_store.is_configured()


def init_chat_storage() -> None:
    sqlite_store.init_chat_db()


def list_conversations(username: str) -> list[dict]:
    return hf_store.list_conversations(username) if _use_hf(username) else sqlite_store.list_conversations(username)


def get_conversation(username: str, conversation_id: int) -> dict | None:
    return hf_store.get_conversation(username, conversation_id) if _use_hf(username) else sqlite_store.get_conversation(conversation_id)


def create_conversation(username: str, *, title: str, mode: str, model_name: str, tone: str) -> int:
    return (
        hf_store.create_conversation(username, title=title, mode=mode, model_name=model_name, tone=tone)
        if _use_hf(username)
        else sqlite_store.create_conversation(username=username, title=title, mode=mode, model_name=model_name, tone=tone)
    )


def update_conversation_meta(username: str, conversation_id: int, *, title: str | None = None, mode: str | None = None, model_name: str | None = None, tone: str | None = None) -> None:
    if _use_hf(username):
        hf_store.update_conversation_meta(username, conversation_id, title=title, mode=mode, model_name=model_name, tone=tone)
    else:
        sqlite_store.update_conversation_meta(conversation_id, title=title, mode=mode, model_name=model_name, tone=tone)


def get_messages(username: str, conversation_id: int) -> list[dict]:
    return hf_store.get_messages(username, conversation_id) if _use_hf(username) else sqlite_store.get_messages(conversation_id)


def add_message(username: str, conversation_id: int, *, role: str, content: str, context: dict | None = None) -> int:
    return (
        hf_store.add_message(username, conversation_id, role=role, content=content, context=context)
        if _use_hf(username)
        else sqlite_store.add_message(conversation_id, role=role, content=content, context=context)
    )


def delete_conversation(username: str, conversation_id: int) -> None:
    if _use_hf(username):
        hf_store.delete_conversation(username, conversation_id)
    else:
        sqlite_store.delete_conversation(conversation_id, username=username)


def record_export(username: str, conversation_id: int | None, *, export_type: str, file_name: str) -> None:
    if _use_hf(username):
        return
    sqlite_store.record_export(conversation_id, export_type=export_type, file_name=file_name)
