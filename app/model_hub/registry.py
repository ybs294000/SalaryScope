"""
registry.py
===========
Handles reading, writing, and validating models_registry.json from HuggingFace.

Design principles
-----------------
- No Streamlit dependency. Pure Python / requests only.
- Registry is fetched fresh on each call (with caching via caller).
- All mutations return a new dict; callers decide when to push.
- Fails explicitly on every edge case.

Registry schema
---------------
{
    "models": [
        {
            "id":           "model_20260415_ab12",
            "display_name": "Software Engineering Salaries (US)",
            "path":         "models/model_20260415_ab12/",
            "description":  "...",
            "target":       "salary_in_usd",
            "active":       true,
            "version":      1,
            "uploaded_at":  "2026-04-15T10:00:00Z",
            "uploaded_by":  "admin",
            "size_bytes":   12345,
            "schema_version": "1.0"
        }
    ]
}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.model_hub._hf_client import (
    REGISTRY_PATH,
    download_file_bytes,
    upload_file_bytes,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_REGISTRY_SIZE_BYTES = 256 * 1024  # 256 KB sanity cap on registry itself


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_registry(raw: bool = False) -> dict:
    """
    Fetch models_registry.json from HuggingFace.

    Returns parsed dict on success.
    Raises RuntimeError with a user-friendly message on any failure.
    If the file does not exist yet, returns an empty valid registry.
    """
    try:
        data = download_file_bytes(REGISTRY_PATH)
    except FileNotFoundError:
        logger.info("Registry not found on HuggingFace — returning empty registry.")
        return {"models": []}
    except Exception as exc:
        raise RuntimeError(f"Could not fetch model registry: {exc}") from exc

    if len(data) > MAX_REGISTRY_SIZE_BYTES:
        raise RuntimeError(
            f"Registry file exceeds safety limit ({len(data)} bytes). "
            "Something may be wrong with the repository."
        )

    try:
        parsed = json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Registry JSON is malformed: {exc}. "
            "Fix or reset models_registry.json in your HuggingFace repo."
        ) from exc

    if "models" not in parsed or not isinstance(parsed["models"], list):
        raise RuntimeError(
            "Registry is missing the top-level 'models' list. "
            "Expected: {\"models\": [...]}"
        )

    if raw:
        return parsed

    # Validate each entry minimally
    validated = []
    for entry in parsed["models"]:
        err = _validate_registry_entry(entry)
        if err:
            logger.warning("Skipping malformed registry entry %s: %s", entry.get("id"), err)
            continue
        validated.append(entry)

    return {"models": validated}


def _validate_registry_entry(entry: dict) -> Optional[str]:
    """Return error string if invalid, None if valid."""
    required = {"id", "display_name", "path"}
    missing = required - set(entry.keys())
    if missing:
        return f"Missing required keys: {missing}"
    if not isinstance(entry.get("active"), bool):
        entry.setdefault("active", True)  # default to active for backward compat
    return None


# ---------------------------------------------------------------------------
# Active model list
# ---------------------------------------------------------------------------

def get_active_models(registry: dict) -> list[dict]:
    """Return only active models from registry dict."""
    return [m for m in registry.get("models", []) if m.get("active", True)]


def get_model_by_id(registry: dict, model_id: str) -> Optional[dict]:
    """Look up a model entry by id. Returns None if not found."""
    for m in registry.get("models", []):
        if m.get("id") == model_id:
            return m
    return None


# ---------------------------------------------------------------------------
# Write / update
# ---------------------------------------------------------------------------

def add_model_to_registry(
    registry: dict,
    model_entry: dict,
) -> dict:
    """
    Return a new registry dict with model_entry appended.
    Does NOT push to HuggingFace — caller must call push_registry().
    Raises ValueError if a model with the same id already exists.
    """
    existing_ids = {m["id"] for m in registry.get("models", [])}
    if model_entry["id"] in existing_ids:
        raise ValueError(
            f"Model id '{model_entry['id']}' already exists in registry. "
            "Each upload must produce a unique id."
        )
    err = _validate_registry_entry(model_entry)
    if err:
        raise ValueError(f"Invalid model entry: {err}")

    new_registry = dict(registry)
    new_registry["models"] = list(registry.get("models", [])) + [model_entry]
    return new_registry


def set_model_active(registry: dict, model_id: str, active: bool) -> dict:
    """Toggle a model's active flag. Returns updated registry."""
    updated = []
    found = False
    for m in registry.get("models", []):
        if m["id"] == model_id:
            m = dict(m)
            m["active"] = active
            found = True
        updated.append(m)
    if not found:
        raise ValueError(f"Model '{model_id}' not found in registry.")
    return {"models": updated}


def rollback_to_version(registry: dict, model_id: str) -> dict:
    """
    Deactivate all models with the same base name except the given model_id,
    and activate the given model_id. Implements simple rollback by model family.

    A model family is identified by shared display_name prefix or explicit
    family_id field if present.
    """
    target = get_model_by_id(registry, model_id)
    if not target:
        raise ValueError(f"Model '{model_id}' not found.")

    family_name = target.get("family_id") or target.get("display_name", "")

    updated = []
    for m in registry.get("models", []):
        m = dict(m)
        is_family = (
            m.get("family_id") == family_name
            or m.get("display_name", "") == family_name
        )
        if is_family:
            m["active"] = m["id"] == model_id
        updated.append(m)

    return {"models": updated}


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------

def push_registry(registry: dict) -> None:
    """
    Serialize and push models_registry.json to HuggingFace.
    Raises RuntimeError on failure.
    """
    try:
        payload = json.dumps(registry, indent=2, ensure_ascii=False).encode("utf-8")
        upload_file_bytes(
            path_in_repo=REGISTRY_PATH,
            data=payload,
            commit_message="Update models_registry.json via Model Hub",
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to push registry: {exc}") from exc