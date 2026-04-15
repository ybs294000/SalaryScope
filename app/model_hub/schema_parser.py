"""
schema_parser.py
================
Converts schema.json field definitions into Streamlit UI components
and collects user input.

Design
------
- This is the ONLY place where schema → Streamlit widget mapping lives.
- If Streamlit API changes, only this file needs updating.
- No prediction logic, no HuggingFace, no registry concerns.
- Returns a plain dict of {field_name: value} — caller builds the DataFrame.

Supported UI types
------------------
  slider        -> st.slider   (int or float, requires min/max)
  selectbox     -> st.selectbox (categorical, requires values)
  text_input    -> st.text_input (free text)
  number_input  -> st.number_input
  checkbox      -> st.checkbox  (bool)

Extension
---------
To add a new UI type:
  1. Add its name to ALLOWED_UI_TYPES in validator.py.
  2. Add a handler function _widget_<type> below.
  3. Register it in _WIDGET_DISPATCH at the bottom.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import streamlit as st

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_schema_form(
    schema: dict,
    key_prefix: str = "mh_form",
) -> dict[str, Any]:
    """
    Render Streamlit input widgets for all fields in schema['fields'].

    Parameters
    ----------
    schema     : Parsed schema dict (validated before calling).
    key_prefix : Unique prefix for all widget keys. Use a stable, unique string
                 per model to prevent key collisions across Streamlit reruns.

    Returns
    -------
    dict mapping field_name -> user-supplied value.
    Values are typed according to the schema (int, float, str, bool).
    """
    fields = schema.get("fields", [])
    if not fields:
        st.warning("This model has no input fields defined in its schema.")
        return {}

    collected: dict[str, Any] = {}

    for field in fields:
        if not isinstance(field, dict) or "name" not in field:
            continue
        name   = field["name"]
        ui     = field.get("ui", "text_input")
        label  = field.get("label") or _pretty_label(name)
        key    = f"{key_prefix}_{name}"
        help_text = field.get("help", None)

        handler = _WIDGET_DISPATCH.get(ui)
        if handler is None:
            st.warning(
                f"Unknown UI type '{ui}' for field '{name}'. "
                "Rendered as text input fallback."
            )
            handler = _widget_text_input

        try:
            value = handler(field, label, key, help_text)
        except Exception as exc:
            st.error(
                f"Could not render widget for field '{name}': {exc}. "
                "Check schema.json for this model."
            )
            value = _safe_default(field)

        collected[name] = value

    return collected


# ---------------------------------------------------------------------------
# Widget handlers — one per UI type
# ---------------------------------------------------------------------------

def _widget_slider(
    field: dict,
    label: str,
    key: str,
    help_text: Optional[str],
) -> Any:
    ftype   = field.get("type", "int")
    min_v   = field["min"]
    max_v   = field["max"]
    step    = field.get("step")
    default = field.get("default", min_v)

    # Clamp default to [min, max]
    default = max(min_v, min(max_v, default))

    if ftype == "float":
        min_v   = float(min_v)
        max_v   = float(max_v)
        default = float(default)
        step    = float(step) if step is not None else (max_v - min_v) / 100.0
    else:
        min_v   = int(min_v)
        max_v   = int(max_v)
        default = int(default)
        step    = int(step) if step is not None else max(1, (max_v - min_v) // 100)

    return st.slider(
        label,
        min_value=min_v,
        max_value=max_v,
        value=default,
        step=step,
        key=key,
        help=help_text,
    )


def _widget_selectbox(
    field: dict,
    label: str,
    key: str,
    help_text: Optional[str],
) -> str:
    values  = field.get("values", [])
    default = field.get("default")
    idx     = 0
    if default and default in values:
        idx = values.index(default)

    return st.selectbox(
        label,
        options=values,
        index=idx,
        key=key,
        help=help_text,
    )


def _widget_text_input(
    field: dict,
    label: str,
    key: str,
    help_text: Optional[str],
) -> str:
    default = str(field.get("default", ""))
    return st.text_input(
        label,
        value=default,
        key=key,
        help=help_text,
    )


def _widget_number_input(
    field: dict,
    label: str,
    key: str,
    help_text: Optional[str],
) -> Any:
    ftype   = field.get("type", "float")
    min_v   = field.get("min", 0)
    max_v   = field.get("max", None)
    step    = field.get("step")
    default = field.get("default", min_v or 0)

    if ftype == "int":
        min_v   = int(min_v) if min_v is not None else 0
        max_v   = int(max_v) if max_v is not None else None
        default = int(default)
        step    = int(step) if step is not None else 1
    else:
        min_v   = float(min_v) if min_v is not None else 0.0
        max_v   = float(max_v) if max_v is not None else None
        default = float(default)
        step    = float(step) if step is not None else 1.0

    kwargs: dict[str, Any] = dict(
        label=label,
        value=default,
        step=step,
        key=key,
        help=help_text,
    )
    if min_v is not None:
        kwargs["min_value"] = min_v
    if max_v is not None:
        kwargs["max_value"] = max_v

    return st.number_input(**kwargs)


def _widget_checkbox(
    field: dict,
    label: str,
    key: str,
    help_text: Optional[str],
) -> bool:
    default = bool(field.get("default", False))
    return st.checkbox(label, value=default, key=key, help=help_text)


# ---------------------------------------------------------------------------
# Dispatch table — extend here for new UI types
# ---------------------------------------------------------------------------

_WIDGET_DISPATCH = {
    "slider":       _widget_slider,
    "selectbox":    _widget_selectbox,
    "text_input":   _widget_text_input,
    "number_input": _widget_number_input,
    "checkbox":     _widget_checkbox,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pretty_label(name: str) -> str:
    """Convert snake_case to Title Case for display."""
    return name.replace("_", " ").title()


def _safe_default(field: dict) -> Any:
    """Return a type-safe default value for a field, used as fallback."""
    ftype = field.get("type", "str")
    if ftype == "int":
        return int(field.get("default", 0))
    if ftype == "float":
        return float(field.get("default", 0.0))
    if ftype == "bool":
        return bool(field.get("default", False))
    return str(field.get("default", ""))
