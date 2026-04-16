"""
validator.py
============
Validates schema.json structure and schema–columns consistency.

This module is pure Python — no Streamlit, no HuggingFace, no pickle.
It can be used standalone in offline tools or CI pipelines.

Validation layers
-----------------
1. Schema structural validation  — is schema.json well-formed?
2. Column consistency check      — does schema match columns.pkl?
3. Bundle completeness check     — are all required files present?
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed values for schema field metadata
# ---------------------------------------------------------------------------

ALLOWED_UI_TYPES  = {"slider", "selectbox", "text_input", "number_input", "checkbox"}
ALLOWED_TYPES     = {"int", "float", "category", "bool", "str"}
REQUIRED_SCHEMA_FIELD_KEYS = {"name", "type", "ui"}

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when validation fails. Message is user-friendly."""


def validate_schema(schema: dict) -> list[str]:
    """
    Validate a parsed schema dict.

    Returns a list of human-readable issue strings.
    An empty list means the schema is valid.

    Does NOT raise — callers decide what to do with issues.
    """
    issues: list[str] = []

    if not isinstance(schema, dict):
        return ["Schema must be a JSON object (dict)."]

    fields = schema.get("fields")
    if fields is None:
        return ["Schema is missing the required 'fields' key."]
    if not isinstance(fields, list):
        return ["'fields' must be a list."]
    if len(fields) == 0:
        issues.append("'fields' list is empty. At least one input field is required.")

    seen_names: set[str] = set()

    for i, field in enumerate(fields):
        prefix = f"Field #{i + 1}"
        if not isinstance(field, dict):
            issues.append(f"{prefix}: must be an object, got {type(field).__name__}.")
            continue

        name = field.get("name")
        if not name or not isinstance(name, str):
            issues.append(f"{prefix}: 'name' must be a non-empty string.")
        else:
            if name in seen_names:
                issues.append(f"Duplicate field name: '{name}'.")
            seen_names.add(name)
            prefix = f"Field '{name}'"

        ftype = field.get("type")
        if ftype not in ALLOWED_TYPES:
            issues.append(
                f"{prefix}: 'type' is '{ftype}', must be one of {sorted(ALLOWED_TYPES)}."
            )

        ui = field.get("ui")
        if ui not in ALLOWED_UI_TYPES:
            issues.append(
                f"{prefix}: 'ui' is '{ui}', must be one of {sorted(ALLOWED_UI_TYPES)}."
            )

        # Per-UI-type constraint checks
        if ui == "slider":
            _check_slider(field, prefix, issues)
        elif ui == "selectbox":
            _check_selectbox(field, prefix, issues)
        elif ui in ("number_input",):
            _check_number_input(field, prefix, issues)

    return issues


def _check_slider(field: dict, prefix: str, issues: list[str]) -> None:
    min_v = field.get("min")
    max_v = field.get("max")
    if min_v is None:
        issues.append(f"{prefix} (slider): 'min' is required.")
    if max_v is None:
        issues.append(f"{prefix} (slider): 'max' is required.")
    if min_v is not None and max_v is not None:
        if not isinstance(min_v, (int, float)):
            issues.append(f"{prefix} (slider): 'min' must be a number.")
        if not isinstance(max_v, (int, float)):
            issues.append(f"{prefix} (slider): 'max' must be a number.")
        if isinstance(min_v, (int, float)) and isinstance(max_v, (int, float)):
            if min_v >= max_v:
                issues.append(f"{prefix} (slider): 'min' ({min_v}) must be less than 'max' ({max_v}).")
            default = field.get("default")
            if default is not None and isinstance(default, (int, float)):
                if not (min_v <= default <= max_v):
                    issues.append(
                        f"{prefix} (slider): 'default' ({default}) is outside [min={min_v}, max={max_v}]."
                    )


def _check_selectbox(field: dict, prefix: str, issues: list[str]) -> None:
    values = field.get("values")
    if values is None:
        issues.append(f"{prefix} (selectbox): 'values' list is required.")
        return
    if not isinstance(values, list):
        issues.append(f"{prefix} (selectbox): 'values' must be a list.")
        return
    if len(values) == 0:
        issues.append(f"{prefix} (selectbox): 'values' cannot be empty.")
    for v in values:
        if not isinstance(v, str):
            issues.append(f"{prefix} (selectbox): all values must be strings, got {type(v).__name__}.")
            break

    # Alias validation — aliases must map known model values to display labels
    aliases = field.get("aliases")
    if aliases is not None:
        if not isinstance(aliases, dict):
            issues.append(
                f"{prefix} (selectbox): 'aliases' must be an object mapping "
                "model_value -> display_label."
            )
        else:
            value_set = set(values or [])
            orphan_keys = [k for k in aliases if k not in value_set]
            if orphan_keys:
                issues.append(
                    f"{prefix} (selectbox): 'aliases' contains key(s) not present in "
                    f"'values': {orphan_keys}. Every alias key must be a valid model value."
                )
            non_string_labels = [
                k for k, v in aliases.items() if not isinstance(v, str)
            ]
            if non_string_labels:
                issues.append(
                    f"{prefix} (selectbox): alias labels must be strings. "
                    f"Non-string labels found for keys: {non_string_labels}."
                )


def _check_number_input(field: dict, prefix: str, issues: list[str]) -> None:
    min_v = field.get("min")
    max_v = field.get("max")
    if min_v is not None and max_v is not None:
        if isinstance(min_v, (int, float)) and isinstance(max_v, (int, float)):
            if min_v >= max_v:
                issues.append(
                    f"{prefix} (number_input): 'min' ({min_v}) must be less than 'max' ({max_v})."
                )


# ---------------------------------------------------------------------------
# Schema–columns consistency
# ---------------------------------------------------------------------------

def validate_schema_vs_columns(schema: dict, columns: list[str]) -> list[str]:
    """
    Check that schema fields align with the expected model columns.

    OHE-aware: a selectbox field named 'job_title' with values
    ['Data Scientist', 'ML Engineer'] is considered matched when columns.pkl
    contains 'job_title_Data Scientist' and 'job_title_ML Engineer'.
    This is the sklearn get_dummies / pd.get_dummies convention.

    Rules applied
    -------------
    - Direct match:   schema field name == column name  → matched
    - OHE match:      selectbox field  → checks for <name>_<value> columns
    - Truly missing:  neither direct nor OHE match found → error
    - Extra columns:  columns not covered by schema at all → info note
      (these are filled with 0.0 by the predictor — acceptable for
       engineered features not exposed to the user)

    Returns list of issue strings. Empty list = consistent bundle.
    """
    issues: list[str] = []
    column_set = set(columns)

    fields = [f for f in schema.get("fields", []) if isinstance(f, dict) and "name" in f]

    # Track which columns are "accounted for" by the schema
    accounted: set[str] = set()
    truly_missing: list[str] = []

    for field in fields:
        name = field["name"]
        ui   = field.get("ui")

        # --- Direct match ---
        if name in column_set:
            accounted.add(name)
            continue

        # --- OHE match (selectbox expands to <name>_<value> columns) ---
        if ui == "selectbox":
            # "values" always holds MODEL values (not alias labels),
            # so OHE expansion produces the correct column names.
            values    = field.get("values", [])
            ohe_cols  = [f"{name}_{v}" for v in values]
            matched   = [c for c in ohe_cols if c in column_set]
            if matched:
                accounted.update(matched)
                continue
            # OHE columns not found either — genuinely missing
            truly_missing.append(
                f"'{name}' (selectbox): neither direct column nor OHE columns "
                f"({ohe_cols[:3]}{'...' if len(ohe_cols) > 3 else ''}) found in columns.pkl"
            )
            continue

        # --- No match at all ---
        truly_missing.append(
            f"'{name}' ({ui}): not found in columns.pkl"
        )

    if truly_missing:
        issues.append(
            "The following schema fields have no matching column(s) in columns.pkl "
            "and will cause prediction errors:\n  " + "\n  ".join(truly_missing)
        )

    # Extra columns — not an error, just informational
    unaccounted = [c for c in columns if c not in accounted]
    if unaccounted:
        issues.append(
            f"columns.pkl has {len(unaccounted)} column(s) not covered by any schema field "
            f"(e.g. {unaccounted[:3]}{'...' if len(unaccounted) > 3 else ''}). "
            "These will be set to 0.0 at prediction time. "
            "This is normal for engineered/interaction features not shown in the UI."
        )

    return issues


# ---------------------------------------------------------------------------
# Alias map validation
# ---------------------------------------------------------------------------

def validate_aliases(aliases: dict, schema: dict) -> list[str]:
    """
    Validate an aliases dict against a parsed schema.

    Rules:
    - aliases must be a dict of {field_name: {model_value: label}}.
    - Every field_name must exist in the schema.
    - Every model_value in an alias sub-dict must exist in the field's 'values'.
    - Labels must be non-empty strings.
    - Duplicate labels within a single field are flagged (ambiguous reverse lookup).

    Returns list of issue strings. Empty = valid.
    """
    issues: list[str] = []

    if not isinstance(aliases, dict):
        return ["aliases.json must be a JSON object (dict)."]

    field_map = {
        f["name"]: f
        for f in schema.get("fields", [])
        if isinstance(f, dict) and "name" in f
    }

    for field_name, alias_map in aliases.items():
        prefix = f"aliases['{field_name}']"

        if field_name not in field_map:
            issues.append(f"{prefix}: field '{field_name}' does not exist in schema.json.")
            continue

        if not isinstance(alias_map, dict):
            issues.append(f"{prefix}: must be a dict of {{model_value: label}}, got {type(alias_map).__name__}.")
            continue

        field      = field_map[field_name]
        allowed    = set(field.get("values", []))
        seen_labels: set[str] = set()

        for model_val, label in alias_map.items():
            if allowed and model_val not in allowed:
                issues.append(
                    f"{prefix}['{model_val}']: model value not in schema 'values' list. "
                    f"Allowed: {sorted(allowed)[:8]}{'...' if len(allowed) > 8 else ''}."
                )
            if not isinstance(label, str) or not label.strip():
                issues.append(f"{prefix}['{model_val}']: label must be a non-empty string.")
            else:
                if label in seen_labels:
                    issues.append(
                        f"{prefix}: duplicate display label '{label}' — "
                        "two model values map to the same label, which breaks reverse lookup."
                    )
                seen_labels.add(label)

    return issues


# ---------------------------------------------------------------------------
# Bundle completeness
# ---------------------------------------------------------------------------

def validate_bundle_files(file_names: list[str]) -> list[str]:
    """
    Given a list of file names (not paths) in an upload batch,
    return missing required file names.

    Accepts two valid bundle formats:

    ONNX format   — model.onnx  + columns.json + schema.json
    Pickle format — model.pkl   + columns.pkl  + schema.json

    A mix (e.g. model.onnx + columns.pkl) is treated as invalid.
    Returns sorted list of missing required file names, or a format
    error message if the model/columns pairing is inconsistent.
    """
    provided = set(file_names)

    has_onnx_model   = "model.onnx"   in provided
    has_pickle_model = "model.pkl"    in provided
    has_json_cols    = "columns.json" in provided
    has_pkl_cols     = "columns.pkl"  in provided
    has_schema       = "schema.json"  in provided

    missing: list[str] = []

    if not has_schema:
        missing.append("schema.json")

    if has_onnx_model:
        # ONNX format: need columns.json
        if not has_json_cols:
            missing.append("columns.json")
    elif has_pickle_model:
        # Pickle format: need columns.pkl
        if not has_pkl_cols:
            missing.append("columns.pkl")
    else:
        # No model file at all
        missing.append("model.onnx  (or  model.pkl)")

    return sorted(missing)


def detect_bundle_format(file_names: list[str]) -> str:
    """
    Return "onnx", "pickle", or "unknown" based on uploaded file names.
    Called by the upload panel UI to show the correct format label.
    """
    provided = set(file_names)
    if "model.onnx" in provided:
        return "onnx"
    if "model.pkl" in provided:
        return "pickle"
    return "unknown"


# ---------------------------------------------------------------------------
# JSON schema round-trip helper
# ---------------------------------------------------------------------------

def parse_schema_json(raw: str | bytes) -> tuple[dict, list[str]]:
    """
    Parse raw JSON string/bytes into a schema dict and validate it.
    Returns (schema_dict, issues_list).
    schema_dict is {} if JSON is invalid.
    """
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {}, ["File is not valid UTF-8 text."]
    try:
        schema = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, [f"Invalid JSON: {exc}"]
    issues = validate_schema(schema)
    return schema, issues
