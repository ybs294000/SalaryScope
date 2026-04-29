from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from .validator import validate_question_set_payload, validate_registry_payload


BASE_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = BASE_DIR / "registry_ia.json"


class IALoadError(Exception):
    """Raised when a registry or question set cannot be loaded safely."""


@st.cache_data(show_spinner=False)
def _read_json_file(path_str: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    path = Path(path_str)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise IALoadError(f"{path.name} must contain a top-level JSON object.")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise IALoadError(f"Missing file: {path.name}")
    return _read_json_file(str(path), path.stat().st_mtime_ns)


def load_registry_bundle() -> dict[str, Any]:
    payload = _load_json(REGISTRY_PATH)
    errors, warnings, entries = validate_registry_payload(payload, base_dir=BASE_DIR)
    return {
        "payload": payload,
        "entries": entries,
        "errors": errors,
        "warnings": warnings,
        "path": REGISTRY_PATH,
    }


def load_question_set(entry: dict[str, Any]) -> dict[str, Any]:
    relative_path = entry.get("file")
    if not relative_path:
        raise IALoadError("Registry entry is missing its question-set file path.")

    path = (BASE_DIR / relative_path).resolve()
    if BASE_DIR not in path.parents and path != BASE_DIR:
        raise IALoadError("Question-set file path must stay within the interview prep package.")

    payload = _load_json(path)
    errors, warnings, normalized = validate_question_set_payload(payload)
    if normalized.get("set_id") and normalized["set_id"] != entry.get("set_id"):
        errors.append(
            f"Question-set file '{path.name}' uses set_id '{normalized['set_id']}' but the registry expects '{entry.get('set_id')}'."
        )
    if entry.get("question_count") and normalized.get("question_count") != entry.get("question_count"):
        warnings.append(
            f"Registry question count for '{entry.get('title', entry.get('set_id', 'set'))}' does not match the file contents."
        )
    return {
        "payload": normalized,
        "errors": errors,
        "warnings": warnings,
        "path": path,
    }
