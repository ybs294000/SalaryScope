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

    # Optional top-level layout key
    layout = schema.get("layout")
    if layout is not None:
        if not isinstance(layout, dict):
            issues.append("'layout' must be an object, e.g. {\"columns\": 2}.")
        else:
            cols = layout.get("columns")
            if cols is not None:
                if not isinstance(cols, int) or cols not in (1, 2, 3):
                    issues.append("'layout.columns' must be the integer 1, 2, or 3.")

    # Optional top-level result_label key
    result_label = schema.get("result_label")
    if result_label is not None:
        if not isinstance(result_label, str) or not result_label.strip():
            issues.append("'result_label' must be a non-empty string when present.")

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

        # Optional layout positioning keys
        row_val = field.get("row")
        if row_val is not None:
            try:
                int(row_val)
            except (TypeError, ValueError):
                issues.append(
                    f"{prefix}: 'row' must be an integer when present, got {row_val!r}."
                )

        span_val = field.get("col_span")
        if span_val is not None:
            try:
                span_int = int(span_val)
                if span_int < 1 or span_int > 3:
                    issues.append(
                        f"{prefix}: 'col_span' must be 1, 2, or 3 when present, got {span_val!r}."
                    )
            except (TypeError, ValueError):
                issues.append(
                    f"{prefix}: 'col_span' must be an integer when present, got {span_val!r}."
                )
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
# resume_config.json validation
# ---------------------------------------------------------------------------

# Keys allowed at the top level of resume_config.json and their expected types.
# All keys are optional -- the file is a selective override, not a full spec.
_RESUME_CONFIG_TOP_LEVEL: dict[str, type | tuple] = {
    "scoring":            dict,
    "extractors":         dict,
    "field_name_mapping": list,
    "preprocessing":      dict,
}

# Keys allowed inside the "scoring" block
_SCORING_KEYS: dict[str, type | tuple] = {
    "experience_max":   (int, float),
    "education_max":    (int, float),
    "skills_max":       (int, float),
    "skills_per_point": (int, float),
    "thresholds":       dict,
    "edu_map":          dict,
}

# Keys allowed inside the "extractors" block
_EXTRACTOR_KEYS: set[str] = {
    "experience",
    "education",
    "senior_flag",
    "remote_ratio",
    "employment_type",
    "job_title",
    "age",
}


def validate_resume_config(cfg: Any) -> list[str]:
    """
    Validate a parsed resume_config.json dict.

    Returns a list of human-readable issue strings.
    An empty list means the config is valid.

    Does NOT raise -- callers decide what to do with issues.

    resume_config.json is a selective override file. All keys are optional.
    Unrecognised keys at any level generate a warning, not an error, so that
    future engine versions can extend the format without breaking old validators.

    Supported top-level keys
    ------------------------
    scoring:            dict   -- override scoring rubric weights and thresholds
    extractors:         dict   -- override per-extractor keyword lists / params
    field_name_mapping: list   -- extra (keyword, extractor_id) pairs injected
                                  at the front of the field-name-to-extractor table
    preprocessing:      dict   -- override text preprocessing flags
    """
    issues: list[str] = []

    if not isinstance(cfg, dict):
        return ["resume_config.json must be a JSON object (dict)."]

    # Warn on unrecognised top-level keys (forward-compatible -- not an error)
    for k in cfg:
        if k not in _RESUME_CONFIG_TOP_LEVEL:
            issues.append(
                f"resume_config: unrecognised top-level key '{k}' will be ignored. "
                f"Supported keys: {sorted(_RESUME_CONFIG_TOP_LEVEL)}."
            )

    # --- scoring block ---
    scoring = cfg.get("scoring")
    if scoring is not None:
        if not isinstance(scoring, dict):
            issues.append("resume_config 'scoring' must be a dict.")
        else:
            for sk in scoring:
                if sk not in _SCORING_KEYS:
                    issues.append(
                        f"resume_config scoring: unrecognised key '{sk}' will be ignored."
                    )
            for key, expected in _SCORING_KEYS.items():
                val = scoring.get(key)
                if val is None:
                    continue
                if not isinstance(val, expected):
                    issues.append(
                        f"resume_config scoring['{key}'] must be {expected}, "
                        f"got {type(val).__name__}."
                    )
            # Validate scoring.thresholds structure if present
            thresholds = scoring.get("thresholds")
            if thresholds is not None and isinstance(thresholds, dict):
                for band_key, band_val in thresholds.items():
                    if not isinstance(band_val, dict):
                        issues.append(
                            f"resume_config scoring.thresholds['{band_key}'] must be a dict "
                            "with 'max' (number) and 'score' (int) and 'note' (str)."
                        )
                        continue
                    for req in ("max", "score", "note"):
                        if req not in band_val:
                            issues.append(
                                f"resume_config scoring.thresholds['{band_key}'] "
                                f"is missing required key '{req}'."
                            )
            # Validate edu_map if present
            edu_map = scoring.get("edu_map")
            if edu_map is not None and isinstance(edu_map, dict):
                for level_key, level_val in edu_map.items():
                    try:
                        int(level_key)
                    except (ValueError, TypeError):
                        issues.append(
                            f"resume_config scoring.edu_map key '{level_key}' must be "
                            "a string representation of an integer level (e.g. '0', '1')."
                        )
                    if not isinstance(level_val, (list, tuple)) or len(level_val) < 2:
                        issues.append(
                            f"resume_config scoring.edu_map['{level_key}'] must be a "
                            "two-element list [score, note_string]."
                        )
                    elif not isinstance(level_val[0], (int, float)):
                        issues.append(
                            f"resume_config scoring.edu_map['{level_key}'][0] "
                            "(score) must be a number."
                        )
                    elif not isinstance(level_val[1], str):
                        issues.append(
                            f"resume_config scoring.edu_map['{level_key}'][1] "
                            "(note) must be a string."
                        )

    # --- extractors block ---
    extractors = cfg.get("extractors")
    if extractors is not None:
        if not isinstance(extractors, dict):
            issues.append("resume_config 'extractors' must be a dict.")
        else:
            for ext_id, ext_cfg in extractors.items():
                if ext_id not in _EXTRACTOR_KEYS:
                    issues.append(
                        f"resume_config extractors: unrecognised extractor id '{ext_id}'. "
                        f"Supported: {sorted(_EXTRACTOR_KEYS)}. "
                        "This section will be ignored."
                    )
                if not isinstance(ext_cfg, dict):
                    issues.append(
                        f"resume_config extractors['{ext_id}'] must be a dict of params."
                    )
                    continue
                # experience extractor params
                if ext_id == "experience":
                    _val_list_of_str_or_num(ext_cfg, "patterns", issues,
                                           f"extractors.{ext_id}")
                    _val_number(ext_cfg, "max_years", issues, f"extractors.{ext_id}")
                # senior_flag extractor params
                if ext_id == "senior_flag":
                    _val_list_of_str(ext_cfg, "keywords", issues,
                                     f"extractors.{ext_id}")
                    _val_number(ext_cfg, "experience_threshold", issues,
                                f"extractors.{ext_id}")
                # remote_ratio extractor params
                if ext_id == "remote_ratio":
                    for subkey in ("remote_keywords", "hybrid_keywords", "onsite_keywords"):
                        _val_list_of_str(ext_cfg, subkey, issues,
                                         f"extractors.{ext_id}")
                # employment_type extractor params
                if ext_id == "employment_type":
                    for subkey in ("part_time_keywords", "freelance_keywords",
                                   "contract_keywords"):
                        _val_list_of_str(ext_cfg, subkey, issues,
                                         f"extractors.{ext_id}")
                # age extractor params
                if ext_id == "age":
                    _val_number(ext_cfg, "min_age", issues, f"extractors.{ext_id}")
                    _val_number(ext_cfg, "max_age", issues, f"extractors.{ext_id}")
                # job_title extractor params
                if ext_id == "job_title":
                    kw_fallback = ext_cfg.get("keyword_fallback")
                    if kw_fallback is not None:
                        if not isinstance(kw_fallback, list):
                            issues.append(
                                "resume_config extractors.job_title.keyword_fallback "
                                "must be a list of [keywords_list, title_string] pairs."
                            )
                        else:
                            for idx, pair in enumerate(kw_fallback):
                                if (
                                    not isinstance(pair, list)
                                    or len(pair) != 2
                                    or not isinstance(pair[0], list)
                                    or not isinstance(pair[1], str)
                                ):
                                    issues.append(
                                        f"resume_config extractors.job_title"
                                        f".keyword_fallback[{idx}] must be "
                                        "[[keyword, ...], title_string]."
                                    )

    # --- field_name_mapping ---
    fnm = cfg.get("field_name_mapping")
    if fnm is not None:
        if not isinstance(fnm, list):
            issues.append("resume_config 'field_name_mapping' must be a list.")
        else:
            for idx, entry in enumerate(fnm):
                if (
                    not isinstance(entry, list)
                    or len(entry) != 2
                    or not isinstance(entry[0], str)
                    or not isinstance(entry[1], str)
                ):
                    issues.append(
                        f"resume_config field_name_mapping[{idx}] must be "
                        "a two-element list [keyword_string, extractor_id_string]."
                    )

    # --- preprocessing block ---
    preprocessing = cfg.get("preprocessing")
    if preprocessing is not None:
        if not isinstance(preprocessing, dict):
            issues.append("resume_config 'preprocessing' must be a dict.")
        else:
            strip_urls = preprocessing.get("strip_urls")
            if strip_urls is not None and not isinstance(strip_urls, bool):
                issues.append(
                    "resume_config preprocessing.strip_urls must be a boolean."
                )
            max_len = preprocessing.get("max_text_length")
            if max_len is not None:
                if not isinstance(max_len, int) or max_len < 100:
                    issues.append(
                        "resume_config preprocessing.max_text_length must be an "
                        "integer >= 100."
                    )

    return issues


# ---------------------------------------------------------------------------
# Internal type-check helpers for validate_resume_config
# ---------------------------------------------------------------------------

def _val_list_of_str(d: dict, key: str, issues: list[str], prefix: str) -> None:
    val = d.get(key)
    if val is None:
        return
    if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
        issues.append(
            f"resume_config {prefix}.{key} must be a list of strings."
        )


def _val_list_of_str_or_num(d: dict, key: str, issues: list[str], prefix: str) -> None:
    val = d.get(key)
    if val is None:
        return
    if not isinstance(val, list):
        issues.append(f"resume_config {prefix}.{key} must be a list.")


def _val_number(d: dict, key: str, issues: list[str], prefix: str) -> None:
    val = d.get(key)
    if val is None:
        return
    if not isinstance(val, (int, float)):
        issues.append(
            f"resume_config {prefix}.{key} must be a number, got {type(val).__name__}."
        )


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