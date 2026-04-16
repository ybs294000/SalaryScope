"""
loader.py
=========
Loads model bundles from HuggingFace.

Supported bundle formats
------------------------
ONNX (preferred — no arbitrary code execution on load):
    model.onnx   — ONNX serialised computation graph
    columns.json — JSON array of feature column names (plain text, no pickle)
    schema.json  — UI field definitions
    aliases.json — optional display label sidecar

Pickle (legacy — admin-controlled, acknowledged risk):
    model.pkl    — sklearn-compatible estimator (joblib/pickle)
    columns.pkl  — ordered feature column list (joblib/pickle)
    schema.json  — UI field definitions
    aliases.json — optional display label sidecar

Format detection
----------------
loader.py checks for model.onnx first. If found, the ONNX path is used and
columns.json is expected. If model.onnx is absent, it falls back to the pickle
path (model.pkl + columns.pkl). Both formats cache identically in session state.

The bundle format is recorded in ModelBundle.bundle_format ("onnx" or "pickle")
so predictor.py can call the correct inference API.

aliases.json — optional sidecar
--------------------------------
Provides display labels for selectbox model values without polluting schema.json.
Merged into the schema fields at load time; rest of the system is unaware.
Format: {"field_name": {"model_value": "Display Label", ...}}

Security comparison
-------------------
ONNX:   model.onnx loaded via onnxruntime — protobuf graph, no Python exec.
        columns.json — plain JSON, zero deserialization risk.
        schema.json / aliases.json — already JSON; no change.
        ONNX eliminates the primary attack surface of the pickle path.

Pickle: model.pkl / columns.pkl loaded via joblib (pickle internally).
        CAN execute arbitrary code. Mitigated by:
          1. File-size guard (MAX_MODEL_FILE_BYTES).
          2. Admin-only upload — access control enforced at upload time.
          3. Security notice logged on every load.
          4. No deserialisation from user-supplied paths.
        Acceptable risk in an admin-controlled internal system.

Caching
-------
Bundles are cached in st.session_state keyed by model_id.
Cache is invalidated on explicit reload or via clear_bundle_cache().
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_MODEL_FILE_BYTES = 200 * 1024 * 1024   # 200 MB — per model file
MAX_SCHEMA_BYTES     = 512 * 1024           # 512 KB
MAX_COLUMNS_BYTES    = 10  * 1024 * 1024   # 10 MB  — columns list (pkl or json)
MAX_ALIASES_BYTES    = 512 * 1024           # 512 KB

BUNDLE_CACHE_KEY = "mh_bundle_cache"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ModelBundle:
    """
    Holds all components of a loaded model bundle.

    Attributes
    ----------
    model_id      : Registry id string.
    model         : Loaded model object.
                    ONNX:   onnxruntime.InferenceSession
                    Pickle: sklearn-compatible estimator
    columns       : Ordered list of expected feature column names (strings).
    schema        : Parsed schema dict (aliases merged in if present).
    model_meta    : Raw registry entry dict.
    has_aliases   : True if aliases.json was found and merged.
    bundle_format : "onnx" or "pickle" — used by predictor.py.
    """

    __slots__ = (
        "model_id", "model", "columns", "schema",
        "model_meta", "has_aliases", "bundle_format",
    )

    def __init__(
        self,
        model_id: str,
        model: Any,
        columns: list[str],
        schema: dict,
        model_meta: dict,
        has_aliases: bool = False,
        bundle_format: str = "pickle",
    ) -> None:
        self.model_id      = model_id
        self.model         = model
        self.columns       = columns
        self.schema        = schema
        self.model_meta    = model_meta
        self.has_aliases   = has_aliases
        self.bundle_format = bundle_format   # "onnx" | "pickle"


def load_bundle(model_meta: dict, force_reload: bool = False) -> ModelBundle:
    """
    Load a model bundle from HuggingFace, with session_state caching.

    Tries ONNX format first (model.onnx + columns.json).
    Falls back to pickle format (model.pkl + columns.pkl) if ONNX files absent.

    Parameters
    ----------
    model_meta   : Registry entry dict (must have 'id' and 'path').
    force_reload : If True, bypass session cache and re-download.

    Returns
    -------
    ModelBundle instance.

    Raises
    ------
    RuntimeError on any load failure.
    """
    import streamlit as st

    model_id = model_meta["id"]

    # --- Session cache ---
    if not force_reload:
        cache = st.session_state.get(BUNDLE_CACHE_KEY, {})
        if model_id in cache:
            logger.debug("Bundle '%s' served from session cache.", model_id)
            return cache[model_id]

    logger.info("[ModelHub] Loading bundle '%s' from HuggingFace.", model_id)

    bundle_path = model_meta.get("path", f"models/{model_id}/")
    if not bundle_path.endswith("/"):
        bundle_path += "/"

    # --- schema.json + aliases.json always fetched fresh ---
    schema_bytes  = _download_checked(
        bundle_path + "schema.json", MAX_SCHEMA_BYTES, "schema.json", force=True,
    )
    aliases_bytes = _download_optional(
        bundle_path + "aliases.json", MAX_ALIASES_BYTES, force=True,
    )

    # --- Detect format: ONNX takes priority ---
    onnx_bytes = _download_optional(
        bundle_path + "model.onnx", MAX_MODEL_FILE_BYTES, force=False,
    )

    if onnx_bytes is not None:
        # ── ONNX path ──────────────────────────────────────────────────────
        logger.info("[ModelHub] ONNX bundle detected for '%s'.", model_id)
        columns_bytes = _download_checked(
            bundle_path + "columns.json", MAX_COLUMNS_BYTES, "columns.json", force=False,
        )
        schema   = _parse_schema(schema_bytes, model_id)
        columns  = _parse_columns_json(columns_bytes, model_id)
        model    = _parse_onnx(onnx_bytes, model_id)
        bundle_format = "onnx"
    else:
        # ── Pickle path (legacy) ────────────────────────────────────────────
        logger.info("[ModelHub] Pickle bundle for '%s' (ONNX not found).", model_id)
        columns_bytes = _download_checked(
            bundle_path + "columns.pkl", MAX_COLUMNS_BYTES, "columns.pkl", force=False,
        )
        model_bytes = _download_checked(
            bundle_path + "model.pkl", MAX_MODEL_FILE_BYTES, "model.pkl", force=False,
        )
        schema   = _parse_schema(schema_bytes, model_id)
        columns  = _parse_columns(columns_bytes, model_id)
        model    = _parse_model(model_bytes, model_id)
        bundle_format = "pickle"

    # --- Merge aliases (format-agnostic) ---
    has_aliases = False
    if aliases_bytes is not None:
        aliases  = _parse_aliases(aliases_bytes, model_id)
        schema   = _merge_aliases_into_schema(schema, aliases, model_id)
        has_aliases = True
        logger.info("[ModelHub] aliases.json merged for '%s'.", model_id)

    bundle = ModelBundle(
        model_id      = model_id,
        model         = model,
        columns       = columns,
        schema        = schema,
        model_meta    = model_meta,
        has_aliases   = has_aliases,
        bundle_format = bundle_format,
    )

    # --- Store in cache ---
    if BUNDLE_CACHE_KEY not in st.session_state:
        st.session_state[BUNDLE_CACHE_KEY] = {}
    st.session_state[BUNDLE_CACHE_KEY][model_id] = bundle

    logger.info("[ModelHub] Bundle '%s' (%s) loaded and cached.", model_id, bundle_format)
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
# Download helpers
# ---------------------------------------------------------------------------

def _download_checked(
    path_in_repo: str, max_bytes: int, label: str, force: bool = False,
) -> bytes:
    """Download file and enforce size limit. Raises RuntimeError if absent."""
    from app.model_hub._hf_client import download_file_bytes, file_size_bytes

    remote_size = file_size_bytes(path_in_repo)
    if remote_size is not None and remote_size > max_bytes:
        raise RuntimeError(
            f"'{label}' is {remote_size / 1024 / 1024:.1f} MB, "
            f"exceeds the {max_bytes // 1024 // 1024} MB limit."
        )

    try:
        data = download_file_bytes(path_in_repo, force=force)
    except FileNotFoundError:
        raise RuntimeError(
            f"Bundle is incomplete: '{label}' is missing at '{path_in_repo}'."
        )

    if len(data) > max_bytes:
        raise RuntimeError(
            f"'{label}' exceeds size limit after download "
            f"({len(data) / 1024 / 1024:.1f} MB > {max_bytes // 1024 // 1024} MB)."
        )
    return data


def _download_optional(
    path_in_repo: str, max_bytes: int, force: bool = False,
) -> Optional[bytes]:
    """Download a file that may not exist. Returns None on 404."""
    from app.model_hub._hf_client import download_file_bytes
    try:
        data = download_file_bytes(path_in_repo, force=force)
    except FileNotFoundError:
        return None
    if len(data) > max_bytes:
        raise RuntimeError(
            f"Optional file '{path_in_repo}' exceeds size limit "
            f"({len(data) // 1024} KB > {max_bytes // 1024} KB)."
        )
    return data


# ---------------------------------------------------------------------------
# Parsers — ONNX path
# ---------------------------------------------------------------------------

def _parse_onnx(data: bytes, model_id: str):
    """
    Load an ONNX model from raw bytes via onnxruntime.

    onnxruntime deserialises a protobuf computation graph — no arbitrary
    Python is executed, unlike pickle. This is the security advantage of
    the ONNX format.

    Returns an onnxruntime.InferenceSession.
    Raises RuntimeError on any failure.
    """
    try:
        import onnxruntime as rt
    except ImportError:
        raise RuntimeError(
            "onnxruntime is not installed. "
            "Add 'onnxruntime' to requirements.txt to use ONNX bundles."
        )

    logger.info(
        "[Security] Loading model.onnx for '%s' via onnxruntime. "
        "ONNX format — no arbitrary code execution on deserialisation.",
        model_id,
    )

    try:
        sess = rt.InferenceSession(data)
    except Exception as exc:
        raise RuntimeError(
            f"model.onnx for '{model_id}' could not be loaded by onnxruntime: {exc}. "
            "Ensure the file is a valid ONNX model."
        ) from exc

    return sess


def _parse_columns_json(data: bytes, model_id: str) -> list[str]:
    """
    Parse columns.json (plain JSON array of strings).
    Used by ONNX bundles in place of columns.pkl.
    """
    try:
        obj = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"columns.json for '{model_id}' is not valid JSON: {exc}"
        ) from exc

    if not isinstance(obj, list) or not all(isinstance(c, str) for c in obj):
        raise RuntimeError(
            f"columns.json for '{model_id}' must be a JSON array of strings. "
            f"Got: {type(obj).__name__}"
        )
    return obj


# ---------------------------------------------------------------------------
# Parsers — Pickle path (legacy)
# ---------------------------------------------------------------------------

def _parse_model(data: bytes, model_id: str) -> Any:
    logger.warning(
        "[Security] Deserializing model.pkl for '%s' via joblib (pickle). "
        "This is safe only if the bundle was uploaded by a trusted admin. "
        "Never accept model.pkl from untrusted sources. "
        "Consider converting to ONNX format for improved security.",
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

    if not hasattr(model, "predict"):
        raise RuntimeError(
            f"model.pkl for '{model_id}' does not have a 'predict' method. "
            "Only sklearn-compatible estimators are supported."
        )
    return model


def _parse_columns(data: bytes, model_id: str) -> list[str]:
    logger.info(
        "[Security] Deserializing columns.pkl for '%s' via joblib. "
        "Consider using columns.json in ONNX bundles to eliminate this pickle load.",
        model_id,
    )
    try:
        import joblib
        obj = joblib.load(io.BytesIO(data))
    except Exception as exc:
        raise RuntimeError(
            f"columns.pkl for '{model_id}' could not be deserialized: {exc}"
        ) from exc

    if hasattr(obj, "tolist"):
        obj = obj.tolist()
    if not isinstance(obj, list):
        raise RuntimeError(
            f"columns.pkl for '{model_id}' must contain a list of column names. "
            f"Got type: {type(obj).__name__}"
        )
    if not all(isinstance(c, str) for c in obj):
        raise RuntimeError(
            f"columns.pkl for '{model_id}' must be a list of strings."
        )
    return obj


# ---------------------------------------------------------------------------
# Parsers — format-agnostic
# ---------------------------------------------------------------------------

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


def _parse_aliases(data: bytes, model_id: str) -> dict:
    try:
        aliases = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(
            f"aliases.json for '{model_id}' is not valid JSON: {exc}"
        ) from exc
    if not isinstance(aliases, dict):
        raise RuntimeError(
            f"aliases.json for '{model_id}' must be a JSON object. "
            f"Got: {type(aliases).__name__}"
        )
    return aliases


def _merge_aliases_into_schema(schema: dict, aliases: dict, model_id: str) -> dict:
    """
    Merge aliases.json into schema fields. Returns a new schema dict.
    Sidecar wins over any inline aliases already in schema.json.
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
                "[ModelHub] aliases.json for '%s': field '%s' alias map is not a dict — skipped.",
                model_id, field_name,
            )
            continue
        if field_name not in field_index:
            logger.warning(
                "[ModelHub] aliases.json for '%s': field '%s' not in schema — skipped.",
                model_id, field_name,
            )
            continue
        idx = field_index[field_name]
        schema["fields"][idx]["aliases"] = alias_map
        logger.debug(
            "[ModelHub] Merged %d aliases into '%s' for model '%s'.",
            len(alias_map), field_name, model_id,
        )

    return schema
