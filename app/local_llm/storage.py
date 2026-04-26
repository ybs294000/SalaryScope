"""
SQLite-backed local storage for assistant conversations and exports.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
DB_PATH = RUNTIME_DIR / "assistant_history.sqlite3"


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_chat_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                mode TEXT NOT NULL,
                model_name TEXT,
                tone TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                export_type TEXT NOT NULL,
                file_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ai_conversations(id)
            )
            """
        )


def create_conversation(
    *,
    username: str,
    title: str,
    mode: str,
    model_name: str,
    tone: str,
) -> int:
    now = _utc_now()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO ai_conversations (username, title, mode, model_name, tone, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (username, title, mode, model_name, tone, now, now),
        )
        return int(cur.lastrowid)


def update_conversation_meta(
    conversation_id: int,
    *,
    title: str | None = None,
    mode: str | None = None,
    model_name: str | None = None,
    tone: str | None = None,
) -> None:
    fields = []
    values = []
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if mode is not None:
        fields.append("mode = ?")
        values.append(mode)
    if model_name is not None:
        fields.append("model_name = ?")
        values.append(model_name)
    if tone is not None:
        fields.append("tone = ?")
        values.append(tone)
    fields.append("updated_at = ?")
    values.append(_utc_now())
    values.append(conversation_id)
    with _connect() as conn:
        conn.execute(
            f"UPDATE ai_conversations SET {', '.join(fields)} WHERE id = ?",
            values,
        )


def list_conversations(username: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, username, title, mode, model_name, tone, created_at, updated_at
            FROM ai_conversations
            WHERE username = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (username,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, username, title, mode, model_name, tone, created_at, updated_at
            FROM ai_conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()
    return dict(row) if row else None


def add_message(
    conversation_id: int,
    *,
    role: str,
    content: str,
    context: dict | None = None,
) -> int:
    now = _utc_now()
    ctx_json = json.dumps(context or {}, ensure_ascii=True)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO ai_messages (conversation_id, role, content, context_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, ctx_json, now),
        )
        conn.execute(
            "UPDATE ai_conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        return int(cur.lastrowid)


def get_messages(conversation_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, conversation_id, role, content, context_json, created_at
            FROM ai_messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["context"] = json.loads(item.get("context_json") or "{}")
        except json.JSONDecodeError:
            item["context"] = {}
        result.append(item)
    return result


def delete_conversation(conversation_id: int, *, username: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM ai_messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM ai_exports WHERE conversation_id = ?",
            (conversation_id,),
        )
        conn.execute(
            "DELETE FROM ai_conversations WHERE id = ? AND username = ?",
            (conversation_id, username),
        )


def record_export(conversation_id: int | None, *, export_type: str, file_name: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ai_exports (conversation_id, export_type, file_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, export_type, file_name, _utc_now()),
        )
