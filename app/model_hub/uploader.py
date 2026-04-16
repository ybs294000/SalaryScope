"""
uploader.py
===========
Handles admin model bundle uploads to HuggingFace.

Responsibilities
----------------
- Generate unique folder names: model_<timestamp>_<short_id>
- Upload model.pkl, columns.pkl, schema.json to a new folder
- Never overwrite existing bundles
- Validate bundle before uploading
- Build the registry entry dict for the new bundle
- No Streamlit imports — pure logic, testable offline

Security
--------
- File size limits enforced before upload.
- Only admins should call this module (enforced in the tab layer).
- No user-controlled path injection — folder names are always generated here.
"""

from __future__ import annotations

import datetime
import hashlib
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
MAX_SCHEMA_UPLOAD_BYTES  = 512  * 1024          # 512 KB
MAX_COLUMNS_UPLOAD_BYTES = 10   * 1024 * 1024   # 10  MB
MAX_ALIASES_UPLOAD_BYTES = 512  * 1024          # 512 KB — alias maps are text-only
# MAX_MODEL_FILE_BYTES imported from _hf_client (200 MB)


# ---------------------------------------------------------------------------
# Bundle upload
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
) -> UploadResult:
    """
    Validate and upload a complete model bundle to HuggingFace.

    Parameters
    ----------
    model_bytes   : Raw bytes of model.pkl
    columns_bytes : Raw bytes of columns.pkl
    schema_bytes  : Raw bytes of schema.json
    display_name  : Human-readable name for the model (shown in dropdown)
    description   : Optional description paragraph
    target        : Name of the predicted variable (e.g. 'salary_in_usd')
    uploaded_by   : Username of the admin performing the upload
    family_id     : Optional group ID for rollback/versioning grouping
    aliases_bytes : Optional raw bytes of aliases.json. If provided, validated
                    against the schema and uploaded to the same bundle folder.

    Returns
    -------
    UploadResult with folder info and the registry entry dict.

    Raises
    ------
    ValueError  on validation failures (user-fixable).
    RuntimeError on upload / network failures.
    """
    warnings: list[str] = []

    # --- Size checks ---
    _check_size(model_bytes,   MAX_MODEL_FILE_BYTES,   "model.pkl")
    _check_size(columns_bytes, MAX_COLUMNS_UPLOAD_BYTES, "columns.pkl")
    _check_size(schema_bytes,  MAX_SCHEMA_UPLOAD_BYTES,  "schema.json")

    # --- Schema validation ---
    schema, schema_issues = parse_schema_json(schema_bytes)
    if schema_issues:
        raise ValueError(
            "schema.json has validation errors:\n" + "\n".join(f"  - {i}" for i in schema_issues)
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

    # --- Schema vs columns consistency check ---
    sv_issues = validate_schema_vs_columns(schema, columns)
    if sv_issues:
        # These are warnings, not hard errors — model may handle internally
        warnings.extend(sv_issues)
        logger.warning("[Uploader] Schema–column warnings: %s", sv_issues)

    # --- Validate aliases if provided ---
    if aliases_bytes is not None:
        _check_size(aliases_bytes, MAX_ALIASES_UPLOAD_BYTES, "aliases.json")
        try:
            import json as _json
            aliases_parsed = _json.loads(aliases_bytes.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"aliases.json is not valid JSON: {exc}") from exc
        from app.model_hub.validator import validate_aliases
        alias_issues = validate_aliases(aliases_parsed, schema)
        if alias_issues:
            raise ValueError(
                "aliases.json has validation errors:\n"
                + "\n".join(f"  - {i}" for i in alias_issues)
            )

    # --- Generate unique folder ---
    folder_name = _generate_folder_name()
    folder_path = f"models/{folder_name}/"

    # --- Upload files ---
    _upload_one(folder_path + "schema.json",  schema_bytes,  "schema.json")
    _upload_one(folder_path + "columns.pkl",  columns_bytes, "columns.pkl")
    _upload_one(folder_path + "model.pkl",    model_bytes,   "model.pkl")
    if aliases_bytes is not None:
        _upload_one(folder_path + "aliases.json", aliases_bytes, "aliases.json")

    # --- Build registry entry ---
    now_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    registry_entry: dict = {
        "id":           folder_name,
        "display_name": display_name.strip(),
        "path":         folder_path,
        "description":  description.strip(),
        "target":       target.strip(),
        "active":       True,
        "version":      1,
        "uploaded_at":  now_iso,
        "uploaded_by":  uploaded_by,
        "size_bytes":   len(model_bytes) + len(columns_bytes) + len(schema_bytes),
        "schema_version": schema.get("version", "1.0"),
        "num_features":   len(columns),
        "num_inputs":     len(schema.get("fields", [])),
        "has_aliases":    aliases_bytes is not None,
    }
    if family_id:
        registry_entry["family_id"] = family_id.strip()

    logger.info("[Uploader] Bundle '%s' uploaded successfully.", folder_name)

    return UploadResult(
        folder_name    = folder_name,
        folder_path    = folder_path,
        registry_entry = registry_entry,
        warnings       = warnings,
    )


def upload_schema_only(
    schema_bytes: bytes,
    model_id: str,
    bundle_path: str,
) -> list[str]:
    """
    Upload only schema.json to an existing bundle folder.
    Used to update schema without re-uploading model files.

    Returns list of warnings.
    """
    _check_size(schema_bytes, MAX_SCHEMA_UPLOAD_BYTES, "schema.json")
    schema, issues = parse_schema_json(schema_bytes)
    if issues:
        raise ValueError("schema.json has validation errors:\n" + "\n".join(f"  - {i}" for i in issues))

    if not bundle_path.endswith("/"):
        bundle_path += "/"
    _upload_one(bundle_path + "schema.json", schema_bytes, "schema.json")
    return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def upload_aliases_only(
    aliases_bytes: bytes,
    model_id: str,
    bundle_path: str,
    schema: dict,
) -> None:
    """
    Upload or replace aliases.json in an existing bundle folder.
    Validates the aliases against the provided schema before uploading.
    Clears the session bundle cache for model_id so next load picks up
    the new aliases.

    Parameters
    ----------
    aliases_bytes : Raw bytes of the new aliases.json
    model_id      : Registry id of the target bundle (used for cache clearing)
    bundle_path   : Bundle folder path (e.g. 'models/model_20260415_abc123/')
    schema        : Parsed schema dict for this bundle (used for validation)
    """
    _check_size(aliases_bytes, MAX_ALIASES_UPLOAD_BYTES, "aliases.json")

    try:
        import json as _json
        aliases_parsed = _json.loads(aliases_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"aliases.json is not valid JSON: {exc}") from exc

    from app.model_hub.validator import validate_aliases
    issues = validate_aliases(aliases_parsed, schema)
    if issues:
        raise ValueError(
            "aliases.json has validation errors:\n"
            + "\n".join(f"  - {i}" for i in issues)
        )

    if not bundle_path.endswith("/"):
        bundle_path += "/"
    _upload_one(bundle_path + "aliases.json", aliases_bytes, "aliases.json")

    # Clear session cache so the next Load Model picks up the updated aliases
    try:
        from app.model_hub.loader import clear_bundle_cache
        clear_bundle_cache(model_id)
    except Exception:
        pass


def _generate_folder_name() -> str:
    """Generate model_<timestamp>_<short_id> — guaranteed unique."""
    ts      = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    short   = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"model_{ts}_{short}"


def _check_size(data: bytes, limit: int, label: str) -> None:
    if len(data) > limit:
        mb = len(data) / 1024 / 1024
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
