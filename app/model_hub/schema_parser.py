"""
schema_parser.py
================
Converts schema.json field definitions into Streamlit UI widgets and
collects user input.

Column-based layout system
---------------------------
Fields are arranged in a responsive grid controlled by two schema keys:

Top-level schema keys (all optional — omitting any preserves old behaviour):

    "layout": {
        "columns": 2        # grid width: 1, 2, or 3 (default 1 = single column)
    }

Per-field keys (all optional):

    "row":      1           # integer; fields sharing a row value are placed
                            # in the same st.columns() row.  Fields without a
                            # "row" key each get their own row (old behaviour).
    "col_span": 1           # 1 or 2 — how many grid columns this field spans
                            # (only meaningful when layout columns >= 2).
                            # Default 1.  A span that exceeds remaining space
                            # in the row is clamped gracefully.

Backward compatibility
----------------------
- Any schema.json without "layout", "row", or "col_span" renders identically
  to the old single-column behaviour.  No schema migration needed.
- The validator accepts but does not require these keys.
- Models already in production (pharma, healthcare, STEM) continue to work.

Alias system
------------
A selectbox field may carry an "aliases" dict merged from aliases.json at
load time, or defined inline in schema.json for small alias sets:

    {
        "name":    "experience_level",
        "type":    "category",
        "ui":      "selectbox",
        "values":  ["EN", "MI", "SE"],
        "aliases": {
            "EN": "Entry Level (0-4 years)",
            "MI": "Mid-level (5-12 years)",
            "SE": "Senior (13-22 years)"
        }
    }

Rules:
- "values"  always holds MODEL values sent to the predictor.
- "aliases" maps model_value -> display_label shown in the selectbox.
- render_schema_form() always returns MODEL values, never display labels.

Result card label
-----------------
The top-level "result_label" key in schema.json overrides the target
variable name shown in the prediction result card:

    { "result_label": "Predicted Annual Salary (USD)", ... }

If absent, the result card uses the "target" field from the registry entry
(existing behaviour).

Supported UI types
------------------
  slider        -> st.slider        (int or float, requires min / max)
  selectbox     -> st.selectbox     (categorical, requires values list)
  text_input    -> st.text_input    (free text)
  number_input  -> st.number_input
  checkbox      -> st.checkbox      (bool)

Extending
---------
1. Add the new ui name to ALLOWED_UI_TYPES in validator.py.
2. Write a _widget_<type>(field, label, key, help_text) function here.
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
    Render Streamlit input widgets for all fields in schema["fields"].

    Respects optional layout hints ("layout", "row", "col_span") for
    multi-column grids.  Schemas without these keys render in a single
    column, exactly as before.

    Parameters
    ----------
    schema     : Parsed schema dict.  Aliases already merged by loader.py.
    key_prefix : Unique prefix for all widget keys.  Must be stable and
                 unique per model to prevent key collisions on reruns.

    Returns
    -------
    dict mapping field_name -> model value (alias-resolved).
    Values are typed per schema (int, float, str, bool).
    Pass directly to predictor.predict().
    """
    fields = schema.get("fields", [])
    if not fields:
        st.warning("This model has no input fields defined in its schema.")
        return {}

    # Number of grid columns (1 = old single-column, 2 or 3 = new grid)
    layout       = schema.get("layout") or {}
    grid_columns = int(layout.get("columns", 1))
    grid_columns = max(1, min(3, grid_columns))   # clamp to [1, 3]

    if grid_columns == 1:
        # ── Single-column path ───────────────────────────────────────────
        # Identical to the original implementation.  No grouping, no columns.
        return _render_fields_single_column(fields, key_prefix)
    else:
        # ── Multi-column grid path ───────────────────────────────────────
        return _render_fields_grid(fields, key_prefix, grid_columns)


def get_result_label(schema: dict, fallback: str) -> str:
    """
    Return the label to display on the prediction result card.

    Checks schema["result_label"] first; falls back to the supplied
    fallback string (typically the "target" field from the registry entry).

    Parameters
    ----------
    schema   : Parsed schema dict (may or may not have "result_label").
    fallback : String to use when "result_label" is absent or empty.
               Typically model_meta["target"] or "Predicted Value".

    Returns
    -------
    Non-empty string safe for display.
    """
    label = schema.get("result_label", "")
    if label and isinstance(label, str) and label.strip():
        return label.strip()
    return fallback or "Predicted Value"


# ---------------------------------------------------------------------------
# Layout renderers
# ---------------------------------------------------------------------------

def _render_fields_single_column(
    fields: list[dict],
    key_prefix: str,
) -> dict[str, Any]:
    """
    Original single-column rendering.
    Each field gets its own row.  No columns(), no grouping.
    """
    collected: dict[str, Any] = {}
    for field in fields:
        if not isinstance(field, dict) or "name" not in field:
            continue
        name, value = _render_one_field(field, key_prefix)
        if name is not None:
            collected[name] = value
    return collected


def _render_fields_grid(
    fields: list[dict],
    key_prefix: str,
    grid_columns: int,
) -> dict[str, Any]:
    """
    Multi-column grid rendering.

    Fields are grouped into rows using the optional "row" integer key.
    Within each row, fields are placed into st.columns() slots according
    to their "col_span" value (default 1).

    Grouping rules:
    - Fields with a "row" key are grouped together by that value.
    - Fields without a "row" key form their own single-field rows
      (same as single-column behaviour, just rendered inside a column).
    - Row integers are sorted ascending so the author controls order.

    Span rules:
    - col_span=1 occupies one column slot.
    - col_span=2 occupies two column slots (clamped to remaining space).
    - A field that would overflow the row starts a new row automatically.
    - Checkboxes always default to col_span=1.
    - Sliders default to col_span matching the full row width so they
      have enough horizontal space to be readable.
    """
    collected: dict[str, Any] = {}

    # Separate fields that have a "row" key from those that do not
    ungrouped: list[dict] = []
    row_groups: dict[int, list[dict]] = {}

    for field in fields:
        if not isinstance(field, dict) or "name" not in field:
            continue
        row_key = field.get("row")
        if row_key is None:
            ungrouped.append(field)
        else:
            try:
                row_int = int(row_key)
            except (TypeError, ValueError):
                ungrouped.append(field)
                continue
            row_groups.setdefault(row_int, []).append(field)

    # Build an ordered sequence of render units.
    # Each unit is a list of fields that belong in the same st.columns() call.
    render_units: list[list[dict]] = []

    # Ungrouped fields come first in the order they appear in "fields"
    for field in ungrouped:
        render_units.append([field])

    # Grouped rows sorted by row integer
    for row_int in sorted(row_groups.keys()):
        render_units.append(row_groups[row_int])

    # Render each unit
    for unit in render_units:
        collected.update(_render_row(unit, key_prefix, grid_columns))

    return collected


def _render_row(
    row_fields: list[dict],
    key_prefix: str,
    grid_columns: int,
) -> dict[str, Any]:
    """
    Render one logical row of fields into st.columns() slots.

    Packs fields left-to-right.  When a field's col_span would exceed the
    remaining space in the row, it wraps into a new st.columns() call.
    """
    collected: dict[str, Any] = {}

    # Resolve col_span for every field in the row
    spans = [_resolve_span(f, grid_columns) for f in row_fields]

    # Split into physical rows if spans overflow grid_columns
    physical_rows: list[list[tuple[dict, int]]] = []
    current_row: list[tuple[dict, int]] = []
    current_used = 0

    for field, span in zip(row_fields, spans):
        if current_used + span > grid_columns:
            if current_row:
                physical_rows.append(current_row)
            current_row = [(field, span)]
            current_used = span
        else:
            current_row.append((field, span))
            current_used += span

    if current_row:
        physical_rows.append(current_row)

    # Render each physical row
    for phys_row in physical_rows:
        # Build column ratios from spans
        ratios = []
        for _, span in phys_row:
            ratios.append(span)
        # Pad with a filler column if the row is not full, so widgets
        # do not stretch to fill the entire width when the row is sparse.
        total_span = sum(ratios)
        if total_span < grid_columns:
            ratios.append(grid_columns - total_span)
            has_filler = True
        else:
            has_filler = False

        cols = st.columns(ratios)
        for col_idx, (field, _) in enumerate(phys_row):
            with cols[col_idx]:
                name, value = _render_one_field(field, key_prefix)
                if name is not None:
                    collected[name] = value
        # filler column is empty — nothing to render in it

    return collected


def _resolve_span(field: dict, grid_columns: int) -> int:
    """
    Return the column span for a field, clamped to [1, grid_columns].

    Sliders default to filling the row (grid_columns) so that the
    range track is wide enough to be usable.
    Checkboxes always default to 1.
    All others default to 1.
    """
    ui = field.get("ui", "text_input")

    # Author-specified span takes priority
    raw_span = field.get("col_span")
    if raw_span is not None:
        try:
            return max(1, min(grid_columns, int(raw_span)))
        except (TypeError, ValueError):
            pass

    # Sensible defaults by widget type
    if ui == "slider":
        return grid_columns   # sliders need width
    if ui == "checkbox":
        return 1
    return 1


# ---------------------------------------------------------------------------
# Single field renderer
# ---------------------------------------------------------------------------

def _render_one_field(
    field: dict,
    key_prefix: str,
) -> tuple[Optional[str], Any]:
    """
    Render a single field and return (name, value).
    Returns (None, None) on a malformed field so callers can skip it.
    """
    name      = field.get("name")
    if not name:
        return None, None

    ui        = field.get("ui", "text_input")
    label     = field.get("label") or _pretty_label(name)
    key       = f"{key_prefix}_{name}"
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

    return name, value


# ---------------------------------------------------------------------------
# Alias helpers
# ---------------------------------------------------------------------------

def _build_alias_map(field: dict) -> dict[str, str]:
    """Return {model_value: display_label}, or {} if no aliases defined."""
    return field.get("aliases") or {}


def _display_options(field: dict) -> list[str]:
    """
    Return selectbox option strings.
    Alias labels replace model values where defined; raw values shown otherwise.
    """
    alias_map = _build_alias_map(field)
    return [alias_map.get(v, v) for v in field.get("values", [])]


def _resolve_to_model_value(field: dict, display_label: str) -> str:
    """
    Convert a selected display label back to its model value.
    If no aliases, display_label is already the model value.
    Falls back to display_label if the inverse lookup misses.
    """
    alias_map = _build_alias_map(field)
    if not alias_map:
        return display_label
    inverse = {label: val for val, label in alias_map.items()}
    return inverse.get(display_label, display_label)


# ---------------------------------------------------------------------------
# Widget handlers
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
    """
    Selectbox that shows alias display labels but returns model values.

    Flow:
      1. _display_options() substitutes alias labels for model values.
      2. st.selectbox shows the labels.
      3. _resolve_to_model_value() converts the selection back to a model value.
    """
    model_values    = field.get("values", [])
    display_options = _display_options(field)

    default_model = field.get("default")
    idx = 0
    if default_model is not None and default_model in model_values:
        idx = model_values.index(default_model)

    selected_display = st.selectbox(
        label,
        options=display_options,
        index=idx,
        key=key,
        help=help_text,
    )
    return _resolve_to_model_value(field, selected_display)


def _widget_text_input(
    field: dict,
    label: str,
    key: str,
    help_text: Optional[str],
) -> str:
    default = str(field.get("default", ""))
    return st.text_input(label, value=default, key=key, help=help_text)


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
        label=label, value=default, step=step, key=key, help=help_text,
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
# Dispatch table
# ---------------------------------------------------------------------------

_WIDGET_DISPATCH = {
    "slider":       _widget_slider,
    "selectbox":    _widget_selectbox,
    "text_input":   _widget_text_input,
    "number_input": _widget_number_input,
    "checkbox":     _widget_checkbox,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pretty_label(name: str) -> str:
    """Convert snake_case to Title Case."""
    return name.replace("_", " ").title()


def _safe_default(field: dict) -> Any:
    """Type-safe fallback default for error recovery."""
    ftype = field.get("type", "str")
    if ftype == "int":   return int(field.get("default", 0))
    if ftype == "float": return float(field.get("default", 0.0))
    if ftype == "bool":  return bool(field.get("default", False))
    return str(field.get("default", ""))
