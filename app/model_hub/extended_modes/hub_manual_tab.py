"""
hub_manual_tab.py
=================
Schema-driven Manual Prediction mode for Model Hub bundles.

This module renders an input form entirely from the loaded bundle's
schema.json, runs a single prediction, and optionally renders any charts
declared under the ``plots`` key in the schema.

It is self-contained and has no imports from app_resume.py, the main tab
files, or any tab-specific business logic.  All it needs is a loaded
ModelBundle object (from app.model_hub.loader) and the shared _msg helper.

Removal contract
----------------
To remove this mode completely:
  1. Delete this file.
  2. Remove the ``hub_manual_tab`` import from model_hub_tab.py.
  3. Remove the ``_render_hub_manual_mode(...)`` call in model_hub_tab.py.
No other files need touching.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.model_hub.predictor import predict
from app.model_hub.schema_parser import render_schema_form, get_result_label
from app.model_hub.extended_modes.schema_plots import render_schema_plots


# Currency converter is optional -- works without it if unavailable.
try:
    from app.utils.currency_utils import render_currency_converter
    _CURRENCY_AVAILABLE = True
except Exception:
    _CURRENCY_AVAILABLE = False


def render_hub_manual_mode(
    active_bundle: Any,
    selected_meta: dict,
    msg_fn: Any,
) -> None:
    """
    Render the schema-driven manual prediction panel.

    Parameters
    ----------
    active_bundle  : A loaded ModelBundle object.
    selected_meta  : Registry metadata dict for the selected model.
    msg_fn         : Callable(text, kind) -- the _msg helper from the caller.
    """
    st.subheader(":material/edit_note: Manual Prediction")
    st.caption(
        "Fill in the fields below to predict a single outcome. "
        "The form is generated from this model's schema."
    )

    schema = active_bundle.schema
    fields = schema.get("fields", [])
    plots  = schema.get("plots", [])
    model_id = active_bundle.model_id

    form_key   = f"mh_ext_manual_form_{model_id}"
    result_key = f"mh_ext_manual_result_{model_id}"

    with st.form(key=form_key):
        raw_input = render_schema_form(
            schema     = schema,
            key_prefix = f"mh_ext_manual_{model_id}",
        )
        submitted = st.form_submit_button(
            ":material/play_arrow: Predict",
            type="primary",
        )

    if submitted:
        try:
            prediction = predict(active_bundle, raw_input)
            result_label = get_result_label(
                schema,
                selected_meta.get("target", "Predicted Value"),
            )
            st.session_state[result_key] = {
                "value":     prediction.value,
                "model_id":  prediction.model_id,
                "target":    result_label,
                "warnings":  prediction.warnings,
                "raw_input": prediction.raw_input,
            }
        except (RuntimeError, ValueError) as exc:
            msg_fn(f"Prediction failed: {exc}", "error")
            st.session_state.pop(result_key, None)

    stored = st.session_state.get(result_key)
    if stored is None:
        return

    _render_single_result(stored, fields, plots, msg_fn)


# ---------------------------------------------------------------------------
# Result renderer
# ---------------------------------------------------------------------------

def _render_single_result(
    stored: dict,
    fields: list[dict],
    plots: list[dict],
    msg_fn: Any,
) -> None:
    """Render the result card, warnings, input summary, charts, and currency."""
    value     = stored["value"]
    model_id  = stored["model_id"]
    target    = stored.get("target", "Predicted Value")
    warnings  = stored.get("warnings", [])
    raw_input = stored.get("raw_input", {})

    st.divider()
    st.subheader(":material/insights: Prediction Result")

    from app.theme import hub_result_card_html
    formatted = _format_prediction(value, target)
    st.markdown(hub_result_card_html(formatted, target), unsafe_allow_html=True)

    for w in warnings:
        msg_fn(w, "warning")

    with st.expander(":material/list: Input Summary", expanded=False):
        for k, v in raw_input.items():
            st.text(f"{k}: {v}")

    # Schema-declared charts for single-prediction mode.
    # Only plots that do NOT require batch_df are rendered here.
    single_plots = [p for p in plots if p.get("type") in ("gauge", "bar", "horizontal_bar")]
    if single_plots:
        st.divider()
        st.subheader(":material/bar_chart: Charts")
        render_schema_plots(
            plots        = single_plots,
            result_value = value,
            raw_input    = raw_input,
            batch_df     = None,
            schema_fields = fields,
        )

    # Currency conversion (optional, non-intrusive).
    if _CURRENCY_AVAILABLE:
        _location_hint = _guess_location_from_inputs(raw_input)
        render_currency_converter(
            usd_amount    = value,
            location_hint = _location_hint,
            widget_key    = f"mh_ext_manual_currency_{model_id}",
            show_breakdown = True,
        )


def _format_prediction(value: float, target: str) -> str:
    """Format a prediction value based on target name heuristics."""
    tl = target.lower()
    if any(kw in tl for kw in ("salary", "wage", "income", "pay", "usd", "price", "cost", "revenue")):
        return f"${value:,.2f}"
    if any(kw in tl for kw in ("pct", "percent", "rate", "ratio")):
        return f"{value:.2f}%"
    if abs(value) >= 1_000_000:
        return f"{value:,.0f}"
    if abs(value) >= 100:
        return f"{value:,.2f}"
    return f"{value:.4f}"


def _guess_location_from_inputs(raw_input: dict) -> str | None:
    """Try to extract a country/location hint from common field names."""
    for field_name in ("country", "location", "employee_residence",
                       "company_location", "country_code"):
        if field_name in raw_input:
            return str(raw_input[field_name])
    return None