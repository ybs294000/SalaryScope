"""
uploader.py
===========
Handles admin model bundle uploads to HuggingFace.

Supported bundle formats
------------------------
ONNX (preferred):
    model.onnx        -- ONNX model file
    columns.json      -- JSON array of feature column names (no pickle)
    schema.json       -- UI field definitions
    aliases.json      -- optional display label sidecar
    skills.json       -- optional per-bundle skills lexicon override
    job_titles.json   -- optional per-bundle job titles lexicon override
    resume_config.json -- optional per-bundle resume extraction config override

Pickle (legacy):
    model.pkl         -- sklearn-compatible estimator (joblib/pickle)
    columns.pkl       -- ordered feature column list (joblib/pickle)
    schema.json       -- UI field definitions
    aliases.json      -- optional display label sidecar
    skills.json       -- optional per-bundle skills lexicon override
    job_titles.json   -- optional per-bundle job titles lexicon override
    resume_config.json -- optional per-bundle resume extraction config override

resume_config.json
------------------
Optional sidecar that overrides resume extraction engine defaults for this
specific bundle.  Validated by validator.validate_resume_config() before upload.
See hub_resume_engine.py for full documentation of supported keys.

Format detection
----------------
The format is determined by which model file is provided:
  model.onnx present -> ONNX format (columns.json required)
  model.pkl  present -> Pickle format (columns.pkl required)

The registry entry records the format in the "bundle_format" field
("onnx" or "pickle") so loader.py can detect it at load time without
needing to probe the HuggingFace repo on every load.

Responsibilities
----------------
- Validate all files before upload.
- Generate unique versioned folder names.
- Upload files to HuggingFace.
- Build the registry entry dict.
- Never overwrite existing bundles.
- No Streamlit imports -- pure logic, testable offline.
"""

from __future__ import annotations

import datetime
import json
import logging
import random
import string
from typing import Optional

from app.model_hub._hf_client import (
    upload_file_bytes,
    file_size_bytes,
    MAX_MODEL_FILE_BYTES,
)
from app.model_hub.validator import (
    validate_bundle_files,
    validate_schema,
    validate_schema_vs_columns,
    parse_schema_json,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Size limits
# ---------------------------------------------------------------------------
MAX_SCHEMA_UPLOAD_BYTES   = 512  * 1024          # 512 KB
MAX_COLUMNS_UPLOAD_BYTES  = 10   * 1024 * 1024   # 10 MB
MAX_ALIASES_UPLOAD_BYTES  = 512  * 1024          # 512 KB
MAX_RESUME_CONFIG_BYTES   = 256  * 1024          # 256 KB -- config is small JSON
# MAX_MODEL_FILE_BYTES imported from _hf_client (200 MB) -- applies to both formats


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

class UploadResult:
    """Result of a successful bundle upload."""

    __slots__ = ("folder_name", "folder_path", "registry_entry", "warnings")

    def __init__(
        self,
        folder_name: str,
        folder_path: str,
        registry_entry: dict,
        warnings: list[str],
    ) -> None:
        self.folder_name    = folder_name
        self.folder_path    = folder_path
        self.registry_entry = registry_entry
        self.warnings       = warnings


# ---------------------------------------------------------------------------
# Bundle upload — ONNX path
# ---------------------------------------------------------------------------

def upload_bundle_onnx(
    onnx_bytes: bytes,
    columns_json_bytes: bytes,
    schema_bytes: bytes,
    display_name: str,
    description: str = "",
    target: str = "prediction",
    uploaded_by: str = "admin",
    family_id: Optional[str] = None,
    aliases_bytes: Optional[bytes] = None,
    resume_config_bytes: Optional[bytes] = None,
) -> UploadResult:
    """
    Validate and upload an ONNX bundle to HuggingFace.

    Parameters
    ----------
    onnx_bytes           : Raw bytes of model.onnx
    columns_json_bytes   : Raw bytes of columns.json (JSON array of strings)
    schema_bytes         : Raw bytes of schema.json
    display_name         : Human-readable name for the model dropdown
    description          : Optional description
    target               : Name of the predicted variable (e.g. 'salary_in_usd')
    uploaded_by          : Admin username
    family_id            : Optional rollback group id
    aliases_bytes        : Optional raw bytes of aliases.json
    resume_config_bytes  : Optional raw bytes of resume_config.json.
                           When provided, it is validated before upload and
                           stored as resume_config.json in the bundle folder.
                           Enables per-model resume extraction overrides without
                           changing schema.json or the global engine defaults.

    Returns
    -------
    UploadResult.

    Raises
    ------
    ValueError  on validation failures.
    RuntimeError on upload / network failures.
    """
    warnings: list[str] = []

    # --- Size checks ---
    _check_size(onnx_bytes,         MAX_MODEL_FILE_BYTES,   "model.onnx")
    _check_size(columns_json_bytes, MAX_COLUMNS_UPLOAD_BYTES, "columns.json")
    _check_size(schema_bytes,       MAX_SCHEMA_UPLOAD_BYTES,  "schema.json")

    # --- Validate ONNX model loads ---
    try:
        import onnxruntime as rt
        sess = rt.InferenceSession(onnx_bytes)
        n_inputs = len(sess.get_inputs()[0].shape or [])
    except ImportError:
        raise ValueError(
            "onnxruntime is not installed — cannot validate model.onnx. "
            "Add 'onnxruntime' to requirements.txt."
        )
    except Exception as exc:
        raise ValueError(f"model.onnx could not be loaded by onnxruntime: {exc}") from exc

    # --- Validate columns.json ---
    try:
        columns = json.loads(columns_json_bytes.decode("utf-8"))
        if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
            raise ValueError("columns.json must be a JSON array of strings.")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"columns.json is not valid JSON: {exc}") from exc

    # --- Schema validation ---
    schema, schema_issues = parse_schema_json(schema_bytes)
    if schema_issues:
        raise ValueError(
            "schema.json has validation errors:\n"
            + "\n".join(f"  - {i}" for i in schema_issues)
        )

    # --- Schema vs columns consistency ---
    sv_issues = validate_schema_vs_columns(schema, columns)
    if sv_issues:
        warnings.extend(sv_issues)

    # --- Validate aliases if provided ---
    if aliases_bytes is not None:
        _check_size(aliases_bytes, MAX_ALIASES_UPLOAD_BYTES, "aliases.json")
        aliases_parsed, aliases_issues = _parse_and_validate_aliases(aliases_bytes, schema)
        if aliases_issues:
            raise ValueError(
                "aliases.json has validation errors:\n"
                + "\n".join(f"  - {i}" for i in aliases_issues)
            )

    # --- Validate resume_config if provided ---
    if resume_config_bytes is not None:
        _check_size(resume_config_bytes, MAX_RESUME_CONFIG_BYTES, "resume_config.json")
        rc_issues = _parse_and_validate_resume_config(resume_config_bytes)
        if rc_issues:
            raise ValueError(
                "resume_config.json has validation errors:\n"
                + "\n".join(f"  - {i}" for i in rc_issues)
            )

    # --- Generate folder and upload ---
    folder_name = _generate_folder_name()
    folder_path = f"models/{folder_name}/"

    _upload_one(folder_path + "schema.json",   schema_bytes,       "schema.json")
    _upload_one(folder_path + "columns.json",  columns_json_bytes, "columns.json")
    _upload_one(folder_path + "model.onnx",    onnx_bytes,         "model.onnx")
    if aliases_bytes is not None:
        _upload_one(folder_path + "aliases.json", aliases_bytes, "aliases.json")
    if resume_config_bytes is not None:
        _upload_one(folder_path + "resume_config.json", resume_config_bytes, "resume_config.json")

    # --- Build registry entry ---
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    registry_entry: dict = {
        "id":                folder_name,
        "display_name":      display_name.strip(),
        "path":              folder_path,
        "description":       description.strip(),
        "target":            target.strip(),
        "active":            True,
        "version":           1,
        "uploaded_at":       now_iso,
        "uploaded_by":       uploaded_by,
        "size_bytes":        len(onnx_bytes) + len(columns_json_bytes) + len(schema_bytes),
        "schema_version":    schema.get("version", "1.0"),
        "num_features":      len(columns),
        "num_inputs":        len(schema.get("fields", [])),
        "has_aliases":       aliases_bytes is not None,
        "has_resume_config": resume_config_bytes is not None,
        "bundle_format":     "onnx",
    }
    if family_id:
        registry_entry["family_id"] = family_id.strip()

    logger.info("[Uploader] ONNX bundle '%s' uploaded successfully.", folder_name)

    return UploadResult(
        folder_name    = folder_name,
        folder_path    = folder_path,
        registry_entry = registry_entry,
        warnings       = warnings,
    )


# ---------------------------------------------------------------------------
# Bundle upload — Pickle path (legacy)
# ---------------------------------------------------------------------------

def upload_bundle(
    model_bytes: bytes,
    columns_bytes: bytes,
    schema_bytes: bytes,
    display_name: str,
    description: str = "",
    target: str = "prediction",
    uploaded_by: str = "admin",
    family_id: Optional[str] = None,
    aliases_bytes: Optional[bytes] = None,
    resume_config_bytes: Optional[bytes] = None,
) -> UploadResult:
    """
    Validate and upload a pickle bundle to HuggingFace.

    Parameters
    ----------
    model_bytes          : Raw bytes of model.pkl
    columns_bytes        : Raw bytes of columns.pkl
    schema_bytes         : Raw bytes of schema.json
    display_name         : Human-readable name for the model dropdown
    description          : Optional description
    target               : Name of the predicted variable
    uploaded_by          : Admin username
    family_id            : Optional rollback group id
    aliases_bytes        : Optional raw bytes of aliases.json
    resume_config_bytes  : Optional raw bytes of resume_config.json.
                           When provided, it is validated before upload and
                           stored as resume_config.json in the bundle folder.
                           Enables per-model resume extraction overrides without
                           changing schema.json or the global engine defaults.

    Returns
    -------
    UploadResult.

    Raises
    ------
    ValueError  on validation failures.
    RuntimeError on upload / network failures.
    """
    warnings: list[str] = []

    # --- Size checks ---
    _check_size(model_bytes,   MAX_MODEL_FILE_BYTES,    "model.pkl")
    _check_size(columns_bytes, MAX_COLUMNS_UPLOAD_BYTES, "columns.pkl")
    _check_size(schema_bytes,  MAX_SCHEMA_UPLOAD_BYTES,  "schema.json")

    # --- Schema validation ---
    schema, schema_issues = parse_schema_json(schema_bytes)
    if schema_issues:
        raise ValueError(
            "schema.json has validation errors:\n"
            + "\n".join(f"  - {i}" for i in schema_issues)
        )

    # --- columns.pkl deserialization (for cross-validation) ---
    import io
    try:
        import joblib
        columns = joblib.load(io.BytesIO(columns_bytes))
        if hasattr(columns, "tolist"):
            columns = columns.tolist()
        if not isinstance(columns, list):
            raise ValueError("columns.pkl must contain a list of column name strings.")
    except Exception as exc:
        raise ValueError(f"columns.pkl could not be read: {exc}") from exc

    # --- Schema vs columns consistency ---
    sv_issues = validate_schema_vs_columns(schema, columns)
    if sv_issues:
        warnings.extend(sv_issues)
        logger.warning("[Uploader] Schema–column warnings: %s", sv_issues)

    # --- Validate aliases if provided ---
    if aliases_bytes is not None:
        _check_size(aliases_bytes, MAX_ALIASES_UPLOAD_BYTES, "aliases.json")
        aliases_parsed, aliases_issues = _parse_and_validate_aliases(aliases_bytes, schema)
        if aliases_issues:
            raise ValueError(
                "aliases.json has validation errors:\n"
                + "\n".join(f"  - {i}" for i in aliases_issues)
            )

    # --- Validate resume_config if provided ---
    if resume_config_bytes is not None:
        _check_size(resume_config_bytes, MAX_RESUME_CONFIG_BYTES, "resume_config.json")
        rc_issues = _parse_and_validate_resume_config(resume_config_bytes)
        if rc_issues:
            raise ValueError(
                "resume_config.json has validation errors:\n"
                + "\n".join(f"  - {i}" for i in rc_issues)
            )

    # --- Generate folder and upload ---
    folder_name = _generate_folder_name()
    folder_path = f"models/{folder_name}/"

    _upload_one(folder_path + "schema.json",  schema_bytes,  "schema.json")
    _upload_one(folder_path + "columns.pkl",  columns_bytes, "columns.pkl")
    _upload_one(folder_path + "model.pkl",    model_bytes,   "model.pkl")
    if aliases_bytes is not None:
        _upload_one(folder_path + "aliases.json", aliases_bytes, "aliases.json")
    if resume_config_bytes is not None:
        _upload_one(folder_path + "resume_config.json", resume_config_bytes, "resume_config.json")

    # --- Build registry entry ---
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    registry_entry: dict = {
        "id":                folder_name,
        "display_name":      display_name.strip(),
        "path":              folder_path,
        "description":       description.strip(),
        "target":            target.strip(),
        "active":            True,
        "version":           1,
        "uploaded_at":       now_iso,
        "uploaded_by":       uploaded_by,
        "size_bytes":        len(model_bytes) + len(columns_bytes) + len(schema_bytes),
        "schema_version":    schema.get("version", "1.0"),
        "num_features":      len(columns),
        "num_inputs":        len(schema.get("fields", [])),
        "has_aliases":       aliases_bytes is not None,
        "has_resume_config": resume_config_bytes is not None,
        "bundle_format":     "pickle",
    }
    if family_id:
        registry_entry["family_id"] = family_id.strip()

    logger.info("[Uploader] Pickle bundle '%s' uploaded successfully.", folder_name)

    return UploadResult(
        folder_name    = folder_name,
        folder_path    = folder_path,
        registry_entry = registry_entry,
        warnings       = warnings,
    )


# ---------------------------------------------------------------------------
# Schema / aliases push (format-agnostic)
# ---------------------------------------------------------------------------

def upload_resume_config_only(
    resume_config_bytes: bytes,
    model_id: str,
    bundle_path: str,
) -> None:
    """
    Upload or replace resume_config.json in an existing bundle folder.

    Validates the config before uploading.  Clears the session bundle cache
    for model_id so the next Load Model picks up the new configuration.

    Parameters
    ----------
    resume_config_bytes : Raw bytes of resume_config.json.
    model_id            : Registry model id (used for cache invalidation).
    bundle_path         : Bundle folder path in the HuggingFace repo
                          (e.g. 'models/model_20260415_ab12/').

    Raises
    ------
    ValueError   on validation failures.
    RuntimeError on upload failure.
    """
    _check_size(resume_config_bytes, MAX_RESUME_CONFIG_BYTES, "resume_config.json")
    rc_issues = _parse_and_validate_resume_config(resume_config_bytes)
    if rc_issues:
        raise ValueError(
            "resume_config.json has validation errors:\n"
            + "\n".join(f"  - {i}" for i in rc_issues)
        )
    if not bundle_path.endswith("/"):
        bundle_path += "/"
    _upload_one(bundle_path + "resume_config.json", resume_config_bytes, "resume_config.json")

    try:
        from app.model_hub.loader import clear_bundle_cache
        clear_bundle_cache(model_id)
    except Exception:
        pass


def upload_schema_only(
    schema_bytes: bytes,
    model_id: str,
    bundle_path: str,
) -> list[str]:
    """Upload only schema.json to an existing bundle folder."""
    _check_size(schema_bytes, MAX_SCHEMA_UPLOAD_BYTES, "schema.json")
    schema, issues = parse_schema_json(schema_bytes)
    if issues:
        raise ValueError(
            "schema.json has validation errors:\n"
            + "\n".join(f"  - {i}" for i in issues)
        )
    if not bundle_path.endswith("/"):
        bundle_path += "/"
    _upload_one(bundle_path + "schema.json", schema_bytes, "schema.json")
    return []


def upload_aliases_only(
    aliases_bytes: bytes,
    model_id: str,
    bundle_path: str,
    schema: dict,
) -> None:
    """
    Upload or replace aliases.json in an existing bundle folder.
    Validates the aliases against the provided schema before uploading.
    Clears the session bundle cache for model_id so the next Load Model
    picks up the new aliases.
    """
    _check_size(aliases_bytes, MAX_ALIASES_UPLOAD_BYTES, "aliases.json")
    _, issues = _parse_and_validate_aliases(aliases_bytes, schema)
    if issues:
        raise ValueError(
            "aliases.json has validation errors:\n"
            + "\n".join(f"  - {i}" for i in issues)
        )
    if not bundle_path.endswith("/"):
        bundle_path += "/"
    _upload_one(bundle_path + "aliases.json", aliases_bytes, "aliases.json")

    try:
        from app.model_hub.loader import clear_bundle_cache
        clear_bundle_cache(model_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_and_validate_aliases(
    aliases_bytes: bytes, schema: dict,
) -> tuple[dict, list[str]]:
    """Parse and validate aliases.json bytes. Returns (parsed_dict, issues)."""
    from app.model_hub.validator import validate_aliases
    try:
        aliases_parsed = json.loads(aliases_bytes.decode("utf-8"))
    except Exception as exc:
        return {}, [f"aliases.json is not valid JSON: {exc}"]
    issues = validate_aliases(aliases_parsed, schema)
    return aliases_parsed, issues


def _parse_and_validate_resume_config(resume_config_bytes: bytes) -> list[str]:
    """
    Parse and validate resume_config.json bytes.

    Returns a list of issue strings.  An empty list means the config is valid.
    Does not raise -- caller decides what to do with issues.
    """
    from app.model_hub.validator import validate_resume_config
    try:
        parsed = json.loads(resume_config_bytes.decode("utf-8"))
    except Exception as exc:
        return [f"resume_config.json is not valid JSON: {exc}"]
    return validate_resume_config(parsed)


def _generate_folder_name() -> str:
    """Generate model_<timestamp>_<short_id> — guaranteed unique."""
    ts    = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"model_{ts}_{short}"


def _check_size(data: bytes, limit: int, label: str) -> None:
    if len(data) > limit:
        mb     = len(data) / 1024 / 1024
        lim_mb = limit / 1024 / 1024
        raise ValueError(
            f"'{label}' is {mb:.1f} MB, exceeds the {lim_mb:.0f} MB upload limit. "
            "Compress or quantize the model before uploading."
        )
    if len(data) == 0:
        raise ValueError(f"'{label}' is empty. Upload was not completed correctly.")


def _upload_one(path_in_repo: str, data: bytes, label: str) -> None:
    try:
        upload_file_bytes(
            path_in_repo=path_in_repo,
            data=data,
            commit_message=f"Upload {label} for bundle {path_in_repo}",
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to upload '{label}': {exc}") from exc