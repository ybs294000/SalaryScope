"""
predictor.py
============
Runs predictions using a loaded ModelBundle.

Responsibilities
----------------
- Build a feature DataFrame from raw user input using columns.pkl ordering.
- Validate inputs against expected columns.
- Call model.predict() and return structured results.
- No Streamlit. No HuggingFace. Pure prediction logic only.

Schema–column handling strategy
--------------------------------
The schema defines UI-visible fields.
columns.pkl defines the EXACT feature vector expected by the model.

These may differ:
- The model may require one-hot-encoded columns (e.g. job_title_Data Scientist)
  that are not present as raw schema field names.
- The predictor handles this via an encoding step.

Current encoding support
------------------------
1. Direct mapping: schema field name == column name → value passed through.
2. One-hot encoding: for selectbox fields, the column name is expected to be
   in the form  <field_name>_<value>  (sklearn get_dummies convention).
   The predictor creates the correct binary columns.
3. Missing columns: filled with 0.0 (safe default for most models).

If the model uses a custom preprocessing pipeline (Pipeline with ColumnTransformer),
it handles encoding internally — pass raw values directly and the pipeline takes over.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prediction result
# ---------------------------------------------------------------------------

class PredictionResult:
    """Holds the outcome of a prediction call."""

    __slots__ = ("value", "model_id", "target", "warnings", "raw_input", "feature_vector")

    def __init__(
        self,
        value: float,
        model_id: str,
        target: str,
        warnings: list[str],
        raw_input: dict[str, Any],
        feature_vector: list[float],
    ) -> None:
        self.value          = value
        self.model_id       = model_id
        self.target         = target
        self.warnings       = warnings
        self.raw_input      = raw_input
        self.feature_vector = feature_vector


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def predict(bundle, raw_input: dict[str, Any]) -> PredictionResult:
    """
    Run a prediction using a ModelBundle.

    Parameters
    ----------
    bundle    : ModelBundle instance (from loader.py).
    raw_input : {field_name: value} dict from schema_parser.render_schema_form().

    Returns
    -------
    PredictionResult.

    Raises
    ------
    RuntimeError if the model fails to produce a valid prediction.
    ValueError   if column alignment is critically broken.
    """
    warnings: list[str] = []

    # Step 1: build feature vector
    feature_vector, build_warnings = _build_feature_vector(
        raw_input=raw_input,
        columns=bundle.columns,
        schema=bundle.schema,
    )
    warnings.extend(build_warnings)

    # Step 2: validate shape
    if len(feature_vector) != len(bundle.columns):
        raise ValueError(
            f"Feature vector length {len(feature_vector)} does not match "
            f"expected {len(bundle.columns)} columns. "
            "This is a schema–columns mismatch. Re-upload a consistent bundle."
        )

    # Step 3: predict
    import pandas as pd
    X = pd.DataFrame([feature_vector], columns=bundle.columns)

    try:
        raw_pred = bundle.model.predict(X)
    except Exception as exc:
        raise RuntimeError(
            f"Model prediction failed: {exc}. "
            "Ensure the model was trained with a compatible feature set."
        ) from exc

    # Step 4: extract scalar
    if hasattr(raw_pred, "__iter__"):
        raw_pred = list(raw_pred)
        if len(raw_pred) == 0:
            raise RuntimeError("Model returned an empty prediction array.")
        value = float(raw_pred[0])
    else:
        value = float(raw_pred)

    if not np.isfinite(value):
        raise RuntimeError(
            f"Model returned a non-finite prediction ({value}). "
            "Check the input values and model health."
        )

    target = bundle.model_meta.get("target", "prediction")

    return PredictionResult(
        value=value,
        model_id=bundle.model_id,
        target=target,
        warnings=warnings,
        raw_input=raw_input,
        feature_vector=feature_vector,
    )


# ---------------------------------------------------------------------------
# Feature vector builder
# ---------------------------------------------------------------------------

def _build_feature_vector(
    raw_input: dict[str, Any],
    columns: list[str],
    schema: dict,
) -> tuple[list[float], list[str]]:
    """
    Build an ordered numeric feature vector aligned to columns.

    Strategy:
    1. Try direct match: column name == field name.
    2. Try one-hot match: column name == "<field_name>_<field_value>".
    3. Fill with 0.0 if no match found. Warn once.

    Returns (feature_vector, warnings).
    """
    warnings: list[str] = []
    filled  : list[float] = []

    # Build a reverse lookup: for selectbox fields, remember (field_name, value)
    ohe_lookup: dict[str, float] = {}
    schema_fields = {f["name"]: f for f in schema.get("fields", []) if isinstance(f, dict)}

    for field_name, value in raw_input.items():
        field = schema_fields.get(field_name, {})
        if field.get("ui") == "selectbox":
            # Build one-hot columns from this value
            for possible_val in field.get("values", []):
                col_name = f"{field_name}_{possible_val}"
                ohe_lookup[col_name] = 1.0 if possible_val == value else 0.0

    missing_cols: list[str] = []

    for col in columns:
        # Direct match
        if col in raw_input:
            filled.append(_to_float(raw_input[col]))
            continue

        # One-hot match
        if col in ohe_lookup:
            filled.append(ohe_lookup[col])
            continue

        # Fallback — fill with 0.0
        missing_cols.append(col)
        filled.append(0.0)

    if missing_cols:
        warnings.append(
            f"{len(missing_cols)} column(s) not matched by schema inputs and filled with 0.0: "
            f"{missing_cols[:10]}{'...' if len(missing_cols) > 10 else ''}. "
            "Update schema to include all required fields."
        )

    return filled, warnings


def _to_float(value: Any) -> float:
    """Safely convert any user input to float."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
