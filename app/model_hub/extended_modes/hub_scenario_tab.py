"""
hub_scenario_tab.py
===================
Schema-driven Scenario Analysis for Model Hub bundles.

Root fix applied here
---------------------
The original implementation wrapped each scenario's input form in st.form().
st.form() only captures widget values when its submit button is clicked, so
"Run All Scenarios" without first clicking "Save Inputs" for every scenario
always used schema default values regardless of what the user typed.

Fix: scenario inputs are plain Streamlit widgets (no st.form wrapper).
Streamlit captures plain widget values on every rerun, so they are always
current when "Run All Scenarios" is clicked. The "Save Inputs" button is
removed. A results-clear button is added so users can reset between runs.

Scenario state is stored per (model_id, scenario_index) in session_state so
switching models starts fresh.

Removal contract
----------------
Delete this file and remove the hub_scenario_tab import and call in
model_hub_tab.py. No other files need changing.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.model_hub.predictor import predict
from app.model_hub.schema_parser import render_schema_form, get_result_label
from app.model_hub.extended_modes.schema_plots import render_schema_plots

_MAX_SCENARIOS = 5
_KEY_PREFIX    = "mh_ext_scenario"


def render_hub_scenario_mode(
    active_bundle: Any,
    selected_meta: dict,
    msg_fn: Any,
) -> None:
    """
    Render the schema-driven scenario analysis panel.

    Parameters
    ----------
    active_bundle  : Loaded ModelBundle.
    selected_meta  : Registry metadata dict.
    msg_fn         : Callable(text, kind).
    """
    st.subheader(":material/analytics: Scenario Analysis")
    st.caption(
        "Define up to 5 named scenarios. "
        "Edit any field directly, then click Run All Scenarios."
    )

    schema   = active_bundle.schema
    fields   = schema.get("fields", [])
    plots    = schema.get("plots", [])
    sweep    = schema.get("scenario_sweep")
    model_id = active_bundle.model_id

    scenarios_key = f"{_KEY_PREFIX}_scenarios_{model_id}"
    results_key   = f"{_KEY_PREFIX}_results_{model_id}"

    result_label = get_result_label(
        schema,
        selected_meta.get("target", "Predicted Value"),
    )

    if scenarios_key not in st.session_state:
        st.session_state[scenarios_key] = [_blank_scenario(1)]

    scenarios: list[dict] = st.session_state[scenarios_key]

    # --- Controls row ---
    ctrl_add, ctrl_clear, _ = st.columns([2, 2, 6])
    with ctrl_add:
        if st.button(
            ":material/add: Add Scenario",
            key=f"{_KEY_PREFIX}_add_{model_id}",
            disabled=len(scenarios) >= _MAX_SCENARIOS,
        ):
            scenarios.append(_blank_scenario(len(scenarios) + 1))
            st.session_state[scenarios_key] = scenarios
            st.rerun()

    with ctrl_clear:
        if st.button(
            ":material/delete_sweep: Clear Results",
            key=f"{_KEY_PREFIX}_clr_{model_id}",
            help="Remove the last run results so you can run fresh scenarios.",
        ):
            st.session_state.pop(results_key, None)
            st.rerun()

    # --- Scenario panels (plain widgets, no st.form) ---
    # Plain widgets: Streamlit captures their current value on every rerun,
    # so clicking Run All Scenarios always reads the live widget values
    # without the user needing to click any save/submit button first.
    inputs_per_scenario: dict[int, dict] = {}

    for idx in range(len(scenarios)):
        scenario  = scenarios[idx]
        s_name    = scenario.get("name", f"Scenario {idx + 1}")

        with st.expander(f":material/tune: {s_name}", expanded=(idx == 0)):
            name_col, rm_col = st.columns([8, 2])

            with name_col:
                new_name = st.text_input(
                    "Scenario name",
                    value=s_name,
                    key=f"{_KEY_PREFIX}_name_{model_id}_{idx}",
                )
                scenarios[idx]["name"] = new_name

            with rm_col:
                if len(scenarios) > 1:
                    if st.button(
                        ":material/delete: Remove",
                        key=f"{_KEY_PREFIX}_rm_{model_id}_{idx}",
                    ):
                        scenarios.pop(idx)
                        # Clear any stored inputs for this index
                        _clear_scenario_inputs(model_id, idx)
                        st.session_state[scenarios_key] = scenarios
                        st.session_state.pop(results_key, None)
                        st.rerun()

            # Render schema widgets directly (no st.form).
            # key_prefix is unique per (model_id, scenario_index) so each
            # scenario's widgets are independent.
            raw = render_schema_form(
                schema     = schema,
                key_prefix = f"{_KEY_PREFIX}_field_{model_id}_{idx}",
            )
            inputs_per_scenario[idx] = raw

    st.session_state[scenarios_key] = scenarios

    # --- Run all ---
    run_col, _ = st.columns([2, 8])
    with run_col:
        run_clicked = st.button(
            ":material/play_arrow: Run All Scenarios",
            key=f"{_KEY_PREFIX}_run_{model_id}",
            type="primary",
        )

    if run_clicked:
        results      = []
        all_warnings = []

        for idx, scenario in enumerate(scenarios):
            raw = inputs_per_scenario.get(idx, {})
            try:
                pred = predict(active_bundle, raw)
                for w in pred.warnings:
                    if w not in all_warnings:
                        all_warnings.append(w)
                results.append({
                    "scenario":  scenario.get("name", f"Scenario {idx + 1}"),
                    "predicted": pred.value,
                    "raw_input": pred.raw_input,
                    "warnings":  pred.warnings,
                })
            except (RuntimeError, ValueError) as exc:
                results.append({
                    "scenario":  scenario.get("name", f"Scenario {idx + 1}"),
                    "predicted": None,
                    "raw_input": raw,
                    "warnings":  [str(exc)],
                })

        st.session_state[results_key] = {
            "results":      results,
            "result_label": result_label,
            "warnings":     all_warnings,
        }

    stored = st.session_state.get(results_key)
    if stored is None:
        return

    _render_scenario_results(stored, fields, plots, sweep, model_id, active_bundle, msg_fn)


def _blank_scenario(n: int) -> dict:
    return {"name": f"Scenario {n}"}


def _clear_scenario_inputs(model_id: str, idx: int) -> None:
    """Remove session state keys belonging to the removed scenario index."""
    prefix = f"{_KEY_PREFIX}_field_{model_id}_{idx}"
    keys_to_remove = [k for k in st.session_state if k.startswith(prefix)]
    for k in keys_to_remove:
        del st.session_state[k]


def _render_scenario_results(
    stored: dict,
    fields: list[dict],
    plots: list[dict],
    sweep: dict | None,
    model_id: str,
    active_bundle: Any,
    msg_fn: Any,
) -> None:
    results      = stored["results"]
    result_label = stored["result_label"]
    warnings     = stored.get("warnings", [])

    for w in warnings:
        msg_fn(w, "warning")

    st.divider()
    st.subheader(":material/compare: Scenario Comparison")

    # --- Comparison table ---
    tbl_rows = []
    for r in results:
        val = r["predicted"]
        tbl_rows.append({
            "Scenario":   r["scenario"],
            result_label: _fmt_val(val, result_label) if val is not None else "Error",
        })

    tbl_df = pd.DataFrame(tbl_rows)
    st.dataframe(tbl_df, use_container_width=True, hide_index=True)

    # --- Bar chart ---
    chart_rows = [r for r in results if r["predicted"] is not None]
    if chart_rows:
        chart_df = pd.DataFrame({
            "Scenario":   [r["scenario"] for r in chart_rows],
            result_label: [r["predicted"] for r in chart_rows],
        })
        fig = px.bar(
            chart_df, x=result_label, y="Scenario", orientation="h",
            title=f"{result_label} by Scenario",
            color_discrete_sequence=["#4F8EF7"], text=result_label,
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(
            height        = max(300, len(chart_rows) * 80),
            paper_bgcolor = "rgba(0,0,0,0)",
            plot_bgcolor  = "rgba(0,0,0,0)",
            font_color    = "#CBD5E1",
            xaxis_title   = result_label,
            yaxis_title   = "",
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Schema-declared charts from scenario results ---
    if plots and chart_rows:
        scene_df_rows = []
        for r in chart_rows:
            row = {"scenario": r["scenario"], "predicted_value": r["predicted"]}
            row.update(r.get("raw_input") or {})
            scene_df_rows.append(row)
        if scene_df_rows:
            scene_df = pd.DataFrame(scene_df_rows)
            st.divider()
            st.subheader(":material/bar_chart: Additional Charts")
            render_schema_plots(
                plots         = plots,
                result_value  = None,
                raw_input     = {},
                batch_df      = scene_df,
                schema_fields = fields,
            )

    # --- Sensitivity sweep ---
    if sweep and chart_rows:
        _render_sweep(sweep, results, fields, active_bundle, result_label, model_id, msg_fn)

    # --- Export ---
    st.divider()
    export_df = pd.DataFrame([
        {
            "Scenario":   r["scenario"],
            result_label: r["predicted"],
            **{k: v for k, v in (r.get("raw_input") or {}).items()},
        }
        for r in results
    ])
    export_csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        ":material/download: Export Results (CSV)",
        data      = export_csv,
        file_name = f"scenario_results_{model_id}.csv",
        mime      = "text/csv",
        key       = f"mh_ext_scenario_dl_{model_id}",
    )


def _render_sweep(
    sweep: dict,
    results: list[dict],
    fields: list[dict],
    active_bundle: Any,
    result_label: str,
    model_id: str,
    msg_fn: Any,
) -> None:
    """Render sensitivity sweep declared in schema scenario_sweep."""
    st.divider()
    st.subheader(":material/tune: Sensitivity Sweep")

    sweep_field  = sweep.get("field")
    sweep_mode   = sweep.get("mode", "range")
    value_labels = sweep.get("value_labels", {})

    if not sweep_field:
        msg_fn("scenario_sweep is missing the 'field' key.", "warning")
        return

    field_label_map   = {f["name"]: f.get("label", f["name"]) for f in fields}
    sweep_field_label = field_label_map.get(sweep_field, sweep_field)

    valid_scenarios = [r for r in results if r["predicted"] is not None]
    if not valid_scenarios:
        return

    baseline_name = st.selectbox(
        "Baseline scenario",
        options=[r["scenario"] for r in valid_scenarios],
        key=f"mh_ext_sweep_baseline_{model_id}",
    )
    baseline       = next(r for r in valid_scenarios if r["scenario"] == baseline_name)
    baseline_input = dict(baseline.get("raw_input") or {})

    if sweep_mode == "range":
        lo         = float(sweep.get("min", 0))
        hi         = float(sweep.get("max", 100))
        steps      = int(sweep.get("steps", 50))
        sweep_vals = list(np.linspace(lo, hi, steps))
    else:
        sweep_vals = list(sweep.get("values", []))

    if not sweep_vals:
        msg_fn("scenario_sweep produced no sweep values.", "warning")
        return

    sweep_results = []
    for v in sweep_vals:
        inp = dict(baseline_input)
        inp[sweep_field] = v
        try:
            pred    = predict(active_bundle, inp)
            display = value_labels.get(str(v), str(v) if sweep_mode == "values" else v)
            sweep_results.append({"x": display, "y": pred.value})
        except Exception:
            pass

    if not sweep_results:
        msg_fn("Sweep produced no valid predictions.", "warning")
        return

    sweep_df = pd.DataFrame(sweep_results)
    import plotly.express as px
    if sweep_mode == "range":
        fig = px.line(sweep_df, x="x", y="y",
                      title=f"{result_label} vs {sweep_field_label} (baseline: {baseline_name})",
                      labels={"x": sweep_field_label, "y": result_label})
    else:
        fig = px.bar(sweep_df, x="x", y="y",
                     title=f"{result_label} by {sweep_field_label} (baseline: {baseline_name})",
                     labels={"x": sweep_field_label, "y": result_label},
                     color_discrete_sequence=["#4F8EF7"])

    fig.update_layout(
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font_color    = "#CBD5E1",
    )
    st.plotly_chart(fig, use_container_width=True)


def _fmt_val(value: float | None, target_label: str) -> str:
    if value is None:
        return "N/A"
    tl = target_label.lower()
    if any(kw in tl for kw in ("salary", "wage", "income", "pay", "usd")):
        return f"${value:,.2f}"
    if any(kw in tl for kw in ("pct", "percent", "rate")):
        return f"{value:.2f}%"
    if abs(value) >= 1_000:
        return f"{value:,.2f}"
    return f"{value:.4f}"