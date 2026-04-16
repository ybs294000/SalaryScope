"""
predictor.py
============
Runs predictions using a loaded ModelBundle.

Dual-format support
-------------------
ONNX bundles  (bundle.bundle_format == "onnx"):
    The model is an onnxruntime.InferenceSession.
    Input must be a float32 numpy array shaped [1, n_features].
    The first output node is read as the prediction scalar.

Pickle bundles (bundle.bundle_format == "pickle"):
    The model is an sklearn-compatible estimator.
    Input is a pd.DataFrame aligned to bundle.columns.
    model.predict() is called directly.

Feature vector construction
----------------------------
Identical for both formats — _build_feature_vector() returns an ordered
list of floats aligned to bundle.columns in all cases. The ONNX path
converts this to a float32 numpy array; the pickle path wraps it in a
one-row DataFrame.

No other module needs to know about the format distinction.
"""

from __future__ import annotations

import logging
from typing import Any

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

    Dispatches to the correct inference path based on bundle.bundle_format.

    Parameters
    ----------
    bundle    : ModelBundle instance (from loader.py).
    raw_input : {field_name: model_value} dict from render_schema_form().

    Returns
    -------
    PredictionResult.

    Raises
    ------
    RuntimeError if the model fails to produce a valid prediction.
    ValueError   if column alignment is critically broken.
    """
    warnings: list[str] = []

    # Step 1: build feature vector (format-agnostic)
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

    # Step 3: run inference via the correct path
    fmt = getattr(bundle, "bundle_format", "pickle")
    if fmt == "onnx":
        value = _predict_onnx(bundle.model, feature_vector, bundle.model_id)
    else:
        value = _predict_pickle(bundle.model, feature_vector, bundle.columns, bundle.model_id)

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
# Inference paths
# ---------------------------------------------------------------------------

def _predict_onnx(sess, feature_vector: list[float], model_id: str) -> float:
    """
    Run inference on an onnxruntime.InferenceSession.

    The session expects a float32 array of shape [1, n_features].
    The first output node is read regardless of its name.
    """
    try:
        import onnxruntime as rt
    except ImportError:
        raise RuntimeError(
            "onnxruntime is not installed. "
            "Add 'onnxruntime' to requirements.txt."
        )

    input_name  = sess.get_inputs()[0].name
    output_name = sess.get_outputs()[0].name

    X = np.array([feature_vector], dtype=np.float32)

    try:
        result = sess.run([output_name], {input_name: X})
    except Exception as exc:
        raise RuntimeError(
            f"ONNX inference failed for '{model_id}': {exc}. "
            "Ensure the model was exported with a compatible feature set."
        ) from exc

    # result is a list of arrays; first element, first row, first value
    raw = result[0]
    if hasattr(raw, "flat"):
        return float(next(iter(raw.flat)))
    return float(raw)


def _predict_pickle(model, feature_vector: list[float], columns: list[str],
                    model_id: str) -> float:
    """Run inference on an sklearn-compatible estimator via a one-row DataFrame."""
    import pandas as pd

    X = pd.DataFrame([feature_vector], columns=columns)

    try:
        raw_pred = model.predict(X)
    except Exception as exc:
        raise RuntimeError(
            f"Model prediction failed for '{model_id}': {exc}. "
            "Ensure the model was trained with a compatible feature set."
        ) from exc

    if hasattr(raw_pred, "__iter__"):
        raw_pred = list(raw_pred)
        if not raw_pred:
            raise RuntimeError("Model returned an empty prediction array.")
        return float(raw_pred[0])
    return float(raw_pred)


# ---------------------------------------------------------------------------
# Feature vector builder (format-agnostic)
# ---------------------------------------------------------------------------

def _build_feature_vector(
    raw_input: dict[str, Any],
    columns: list[str],
    schema: dict,
) -> tuple[list[float], list[str]]:
    """
    Build an ordered numeric feature vector aligned to columns.

    Strategy:
    1. Direct match: column name == field name → value passed through.
    2. OHE match:    column name == "<field_name>_<value>" → binary 0/1.
    3. Zero fill:    column not matched → 0.0 with a warning.

    Returns (feature_vector, warnings).
    """
    warnings: list[str] = []
    filled  : list[float] = []

    ohe_lookup: dict[str, float] = {}
    schema_fields = {
        f["name"]: f for f in schema.get("fields", []) if isinstance(f, dict)
    }

    for field_name, value in raw_input.items():
        field = schema_fields.get(field_name, {})
        if field.get("ui") == "selectbox":
            for possible_val in field.get("values", []):
                col_name = f"{field_name}_{possible_val}"
                ohe_lookup[col_name] = 1.0 if possible_val == value else 0.0

    missing_cols: list[str] = []

    for col in columns:
        if col in raw_input:
            filled.append(_to_float(raw_input[col]))
        elif col in ohe_lookup:
            filled.append(ohe_lookup[col])
        else:
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
