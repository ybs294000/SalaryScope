"""
loader.py
=========
Loads model bundles (model.pkl, columns.pkl, schema.json) from HuggingFace.
Optionally loads aliases.json if present in the same bundle folder.

aliases.json — optional sidecar
--------------------------------
Provides display labels for selectbox model values without polluting schema.json.
Useful when a field has many values (e.g. 118 countries) where inline aliases
would make schema.json unreadable and hard to maintain.

Format:
    {
        "field_name": {
            "model_value": "Display Label",
            ...
        }
    }

Aliases are merged into the relevant schema fields at load time.
After merging, the rest of the system (schema_parser, predictor) needs no
knowledge of aliases.json — they work entirely through the enriched schema dict.

If aliases.json is absent from the bundle folder, loading continues normally.
No error is raised — the file is purely optional.

Security
--------
- model.pkl / columns.pkl are loaded via joblib, which uses pickle internally.
  Pickle CAN execute arbitrary code. We mitigate this via:
    1. File-size check before loading (MAX_MODEL_FILE_BYTES guard).
    2. Bundles are admin-only uploads — access control enforced at upload time.
    3. We log a security notice on every load for audit visibility.
    4. We do NOT deserialize files from user-supplied paths.
  This is acceptable risk in an admin-controlled internal system.
  For zero-trust environments, consider ONNX or safe-tensors formats.

Caching
-------
- Bundles are cached in st.session_state keyed by model_id.
- Cache is invalidated if the model_id changes or on explicit reload.
- This avoids re-downloading on every Streamlit rerun.
"""

from __future__ import annotations

import io
import json
import logging
import os
import tempfile
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_MODEL_FILE_BYTES = 200 * 1024 * 1024   # 200 MB — per pkl file
MAX_SCHEMA_BYTES     = 512 * 1024           # 512 KB — schema should be tiny
MAX_COLUMNS_BYTES    = 10  * 1024 * 1024   # 10 MB  — columns list
MAX_ALIASES_BYTES    = 512 * 1024           # 512 KB — alias maps are text-only

BUNDLE_CACHE_KEY = "mh_bundle_cache"  # session_state key

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ModelBundle:
    """
    Holds all components of a loaded model bundle.

    Attributes
    ----------
    model_id    : Registry id string
    model       : Deserialized sklearn-compatible estimator
    columns     : Ordered list of expected feature names
    schema      : Parsed schema dict
    model_meta  : Raw registry entry dict for this model
    """

    __slots__ = ("model_id", "model", "columns", "schema", "model_meta", "has_aliases")

    def __init__(
        self,
        model_id: str,
        model: Any,
        columns: list[str],
        schema: dict,
        model_meta: dict,
        has_aliases: bool = False,
    ) -> None:
        self.model_id    = model_id
        self.model       = model
        self.columns     = columns
        self.schema      = schema        # aliases already merged in if present
        self.model_meta  = model_meta
        self.has_aliases = has_aliases   # True if aliases.json was found and merged


def load_bundle(model_meta: dict, force_reload: bool = False) -> ModelBundle:
    """
    Load a model bundle from HuggingFace, with session_state caching.

    Parameters
    ----------
    model_meta   : A registry entry dict (must have 'id' and 'path').
    force_reload : If True, bypass session cache and re-download.

    Returns
    -------
    ModelBundle instance.

    Raises
    ------
    RuntimeError on any load failure (file missing, size exceeded, etc.).
    """
    import streamlit as st

    model_id = model_meta["id"]

    # Check cache
    if not force_reload:
        cache = st.session_state.get(BUNDLE_CACHE_KEY, {})
        if model_id in cache:
            logger.debug("Bundle '%s' served from session cache.", model_id)
            return cache[model_id]

    logger.info("[ModelHub] Loading bundle '%s' from HuggingFace.", model_id)

    bundle_path = model_meta.get("path", f"models/{model_id}/")
    if not bundle_path.endswith("/"):
        bundle_path += "/"

    # --- Download required files ---
    # schema.json and aliases.json: force=True — these may be updated after the
    # initial upload (push_schema_only / push_aliases_only) so we must never
    # serve a stale disk-cached copy.
    # model.pkl / columns.pkl: force=False — bundle folders are immutable once
    # written, so the HF local cache is always valid and avoids re-downloading
    # large files unnecessarily.
    schema_bytes  = _download_checked(bundle_path + "schema.json",  MAX_SCHEMA_BYTES,       "schema.json", force=True)
    columns_bytes = _download_checked(bundle_path + "columns.pkl",  MAX_COLUMNS_BYTES,      "columns.pkl", force=False)
    model_bytes   = _download_checked(bundle_path + "model.pkl",    MAX_MODEL_FILE_BYTES,   "model.pkl",   force=False)

    # --- Download optional aliases.json ---
    # force=True for the same reason as schema.json — it may be pushed separately.
    aliases_bytes = _download_optional(bundle_path + "aliases.json", MAX_ALIASES_BYTES, force=True)

    # --- Deserialize ---
    schema  = _parse_schema(schema_bytes,  model_id)
    columns = _parse_columns(columns_bytes, model_id)
    model   = _parse_model(model_bytes,    model_id)

    # --- Merge aliases into schema (if present) ---
    has_aliases = False
    if aliases_bytes is not None:
        aliases = _parse_aliases(aliases_bytes, model_id)
        schema  = _merge_aliases_into_schema(schema, aliases, model_id)
        has_aliases = True
        logger.info("[ModelHub] aliases.json merged into schema for '%s'.", model_id)

    bundle = ModelBundle(
        model_id    = model_id,
        model       = model,
        columns     = columns,
        schema      = schema,
        model_meta  = model_meta,
        has_aliases = has_aliases,
    )

    # Store in cache
    if BUNDLE_CACHE_KEY not in st.session_state:
        st.session_state[BUNDLE_CACHE_KEY] = {}
    st.session_state[BUNDLE_CACHE_KEY][model_id] = bundle

    logger.info("[ModelHub] Bundle '%s' loaded and cached.", model_id)
    return bundle


def clear_bundle_cache(model_id: Optional[str] = None) -> None:
    """Clear cached bundles. If model_id is None, clear all."""
    try:
        import streamlit as st
        if model_id is None:
            st.session_state.pop(BUNDLE_CACHE_KEY, None)
        else:
            cache = st.session_state.get(BUNDLE_CACHE_KEY, {})
            cache.pop(model_id, None)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _download_checked(path_in_repo: str, max_bytes: int, label: str,
                      force: bool = False) -> bytes:
    """
    Download file and enforce size limit before returning bytes.

    Parameters
    ----------
    force : Passed through to download_file_bytes. Set True for small metadata
            files (schema.json, aliases.json) that may be updated after initial
            upload. Leave False for large binaries (model.pkl, columns.pkl)
            that are immutable once written to a versioned bundle folder.
    """
    from app.model_hub._hf_client import download_file_bytes, file_size_bytes

    # Pre-flight size check (best-effort; HF API may not always return size)
    remote_size = file_size_bytes(path_in_repo)
    if remote_size is not None and remote_size > max_bytes:
        raise RuntimeError(
            f"Bundle file '{label}' is {remote_size / 1024 / 1024:.1f} MB, "
            f"which exceeds the {max_bytes // 1024 // 1024} MB safety limit. "
            "Reduce the model size or raise MAX_MODEL_FILE_BYTES."
        )

    try:
        data = download_file_bytes(path_in_repo, force=force)
    except FileNotFoundError:
        raise RuntimeError(
            f"Bundle is incomplete: '{label}' is missing at '{path_in_repo}'. "
            "Re-upload the full bundle (model.pkl + columns.pkl + schema.json)."
        )

    # Post-download size check (definitive)
    if len(data) > max_bytes:
        raise RuntimeError(
            f"'{label}' exceeds size limit after download "
            f"({len(data) / 1024 / 1024:.1f} MB > {max_bytes // 1024 // 1024} MB)."
        )

    return data


def _download_optional(path_in_repo: str, max_bytes: int,
                       force: bool = False) -> Optional[bytes]:
    """
    Attempt to download a file that may not exist.
    Returns bytes if found, None if the file is absent (404).
    Raises RuntimeError for auth errors or oversized files.
    """
    from app.model_hub._hf_client import download_file_bytes
    try:
        data = download_file_bytes(path_in_repo, force=force)
    except FileNotFoundError:
        return None   # file is optional — absence is fine
    if len(data) > max_bytes:
        raise RuntimeError(
            f"Optional file at '{path_in_repo}' exceeds size limit "
            f"({len(data) // 1024} KB > {max_bytes // 1024} KB)."
        )
    return data


def _parse_aliases(data: bytes, model_id: str) -> dict:
    """
    Parse aliases.json bytes into a dict.

    Expected format:
        {
            "field_name": {
                "model_value": "Display Label",
                ...
            }
        }

    Returns the parsed dict. Raises RuntimeError if JSON is invalid.
    """
    try:
        aliases = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"aliases.json for '{model_id}' is not valid JSON: {exc}"
        ) from exc
    if not isinstance(aliases, dict):
        raise RuntimeError(
            f"aliases.json for '{model_id}' must be a JSON object "
            "mapping field names to alias dicts. Got: "
            f"{type(aliases).__name__}"
        )
    return aliases


def _merge_aliases_into_schema(schema: dict, aliases: dict, model_id: str) -> dict:
    """
    Merge alias mappings from aliases.json into the schema fields in-place
    (returns a new schema dict — original is not mutated).

    For each field named in aliases, the field's 'aliases' key is set to the
    alias sub-dict. Any aliases already defined inline in schema.json for that
    field are overwritten by the sidecar — the sidecar wins, because it is
    the dedicated place for large alias sets.

    Unknown field names in aliases.json are logged as warnings and ignored.
    """
    import copy
    schema = copy.deepcopy(schema)

    field_index = {
        f["name"]: i
        for i, f in enumerate(schema.get("fields", []))
        if isinstance(f, dict) and "name" in f
    }

    for field_name, alias_map in aliases.items():
        if not isinstance(alias_map, dict):
            logger.warning(
                "[ModelHub] aliases.json for '%s': field '%s' has a non-dict alias map — skipped.",
                model_id, field_name,
            )
            continue
        if field_name not in field_index:
            logger.warning(
                "[ModelHub] aliases.json for '%s': field '%s' not found in schema — skipped.",
                model_id, field_name,
            )
            continue
        idx = field_index[field_name]
        schema["fields"][idx]["aliases"] = alias_map
        logger.debug(
            "[ModelHub] Merged %d aliases into field '%s' for model '%s'.",
            len(alias_map), field_name, model_id,
        )

    return schema


def _parse_schema(data: bytes, model_id: str) -> dict:
    try:
        schema = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"schema.json for '{model_id}' is not valid JSON: {exc}"
        ) from exc

    if "fields" not in schema or not isinstance(schema["fields"], list):
        raise RuntimeError(
            f"schema.json for '{model_id}' must have a top-level 'fields' list."
        )
    return schema


def _parse_columns(data: bytes, model_id: str) -> list[str]:
    logger.info(
        "[Security] Deserializing columns.pkl for '%s' via joblib. "
        "Ensure this file originates from a trusted admin-controlled source.",
        model_id,
    )
    try:
        import joblib
        obj = joblib.load(io.BytesIO(data))
    except Exception as exc:
        raise RuntimeError(
            f"columns.pkl for '{model_id}' could not be deserialized: {exc}"
        ) from exc

    # Accept list or numpy array or pandas Index
    if hasattr(obj, "tolist"):
        obj = obj.tolist()
    if not isinstance(obj, list):
        raise RuntimeError(
            f"columns.pkl for '{model_id}' must contain a list of column names. "
            f"Got type: {type(obj).__name__}"
        )
    if not all(isinstance(c, str) for c in obj):
        raise RuntimeError(
            f"columns.pkl for '{model_id}' must be a list of strings. "
            "Each element must be a column name."
        )
    return obj


def _parse_model(data: bytes, model_id: str) -> Any:
    logger.warning(
        "[Security] Deserializing model.pkl for '%s' via joblib (pickle). "
        "This is safe only if the bundle was uploaded by a trusted admin. "
        "Never accept model.pkl from untrusted sources.",
        model_id,
    )
    try:
        import joblib
        model = joblib.load(io.BytesIO(data))
    except Exception as exc:
        raise RuntimeError(
            f"model.pkl for '{model_id}' could not be deserialized: {exc}. "
            "Ensure it was saved with a compatible version of scikit-learn / joblib."
        ) from exc

    # Basic sanity: must have a predict method
    if not hasattr(model, "predict"):
        raise RuntimeError(
            f"model.pkl for '{model_id}' does not have a 'predict' method. "
            "Only sklearn-compatible estimators are supported."
        )
    return model