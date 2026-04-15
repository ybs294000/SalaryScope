"""
loader.py
=========
Loads model bundles (model.pkl, columns.pkl, schema.json) from HuggingFace.

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

    __slots__ = ("model_id", "model", "columns", "schema", "model_meta")

    def __init__(
        self,
        model_id: str,
        model: Any,
        columns: list[str],
        schema: dict,
        model_meta: dict,
    ) -> None:
        self.model_id   = model_id
        self.model      = model
        self.columns    = columns
        self.schema     = schema
        self.model_meta = model_meta


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

    # --- Download raw bytes ---
    schema_bytes  = _download_checked(bundle_path + "schema.json",  MAX_SCHEMA_BYTES,  "schema.json")
    columns_bytes = _download_checked(bundle_path + "columns.pkl",  MAX_COLUMNS_BYTES, "columns.pkl")
    model_bytes   = _download_checked(bundle_path + "model.pkl",    MAX_MODEL_FILE_BYTES, "model.pkl")

    # --- Deserialize ---
    schema  = _parse_schema(schema_bytes,  model_id)
    columns = _parse_columns(columns_bytes, model_id)
    model   = _parse_model(model_bytes,    model_id)

    bundle = ModelBundle(
        model_id   = model_id,
        model      = model,
        columns    = columns,
        schema     = schema,
        model_meta = model_meta,
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

def _download_checked(path_in_repo: str, max_bytes: int, label: str) -> bytes:
    """Download file and enforce size limit before returning bytes."""
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
        data = download_file_bytes(path_in_repo)
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
