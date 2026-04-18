"""
hub_batch_tab.py
================
Schema-driven Batch Prediction mode for Model Hub bundles.

Fixes applied in this version
------------------------------
1. No clear button.
   Fix: explicit "Clear Results" button wipes session state for this model.

2. Uploading a new file did not clear stale results from the previous run.
   Fix: file identity (name + size) is tracked in session state.  When it
   changes the stored results are cleared automatically before the new file
   is processed, so old output is never shown under a new upload.

3. Progress bar was instantiated inside _run_batch (a plain function called
   from the render function).  In some Streamlit execution paths this caused
   the progress bar to persist after completion.
   Fix: progress bar created and destroyed inside the render function only,
   passed as an argument to _run_batch.

Model-change isolation is already correct: every session key is suffixed with
model_id, so switching models always shows a clean tab.

Removal contract
----------------
  1. Delete this file.
  2. Remove the hub_batch_tab import from model_hub_tab.py.
  3. Remove the _render_hub_batch_mode(...) call in model_hub_tab.py.
No other files need touching.
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
import streamlit as st

from app.model_hub.predictor import predict
from app.model_hub.schema_parser import get_result_label
from app.model_hub.extended_modes.schema_plots import render_schema_plots

_MAX_ROWS   = 10_000
_KEY_PREFIX = "mh_ext_batch"


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _state_keys(model_id: str) -> dict[str, str]:
    return {
        "result":  f"{_KEY_PREFIX}_result_{model_id}",
        "file_id": f"{_KEY_PREFIX}_file_id_{model_id}",
    }


def _clear_batch_state(model_id: str) -> None:
    for key in _state_keys(model_id).values():
        st.session_state.pop(key, None)


def _file_identity(uploaded_file: Any) -> str | None:
    if uploaded_file is None:
        return None
    try:
        return f"{uploaded_file.name}:{uploaded_file.size}"
    except Exception:
        return getattr(uploaded_file, "name", None)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_hub_batch_mode(
    active_bundle: Any,
    selected_meta: dict,
    msg_fn: Any,
) -> None:
    """
    Render the schema-driven batch prediction panel.

    Parameters
    ----------
    active_bundle  : Loaded ModelBundle.
    selected_meta  : Registry metadata dict.
    msg_fn         : Callable(text, kind).
    """
    st.subheader(":material/batch_prediction: Batch Prediction")
    st.caption(
        "Upload a CSV or XLSX file. Each row must contain all fields defined "
        "in this model's schema. A predicted value column is appended to results."
    )

    schema   = active_bundle.schema
    fields   = schema.get("fields", [])
    plots    = schema.get("plots", [])
    model_id = active_bundle.model_id
    keys     = _state_keys(model_id)

    # --- Required columns guide ---
    with st.expander(":material/info: Required columns", expanded=False):
        required_cols = [f["name"] for f in fields]
        st.markdown("Your file must contain **all** of these column names (case-sensitive):")
        st.code(", ".join(required_cols))
        st.caption(
            "Extra columns are ignored. Column order does not matter. "
            f"Maximum {_MAX_ROWS:,} rows."
        )

    # --- Upload + controls row ---
    up_col, run_col, clr_col = st.columns([5, 2, 2])

    with up_col:
        uploaded = st.file_uploader(
            "Upload CSV or XLSX",
            type=["csv", "xlsx"],
            key=f"{_KEY_PREFIX}_upload_{model_id}",
            label_visibility="collapsed",
        )

    with run_col:
        run_clicked = st.button(
            ":material/play_arrow: Run",
            key=f"{_KEY_PREFIX}_run_{model_id}",
            type="primary",
            disabled=uploaded is None,
            use_container_width=True,
        )

    with clr_col:
        clear_clicked = st.button(
            ":material/delete_sweep: Clear",
            key=f"{_KEY_PREFIX}_clr_{model_id}",
            help="Clear results from the last run.",
            use_container_width=True,
        )

    if clear_clicked:
        _clear_batch_state(model_id)
        st.rerun()

    # --- Detect new file: auto-clear stale results when file changes ---
    current_file_id = _file_identity(uploaded)
    stored_file_id  = st.session_state.get(keys["file_id"])

    if current_file_id is not None and current_file_id != stored_file_id:
        # A different file has been selected since the last run.
        # Clear previous results so they are not shown under the new file.
        _clear_batch_state(model_id)
        st.session_state[keys["file_id"]] = current_file_id

    # --- Run ---
    if run_clicked and uploaded is not None:
        df, error = _load_file(uploaded)
        if error:
            msg_fn(error, "error")
            return

        valid, val_error = _validate_df(df, fields)
        if not valid:
            msg_fn(val_error, "error")
            return

        if len(df) > _MAX_ROWS:
            msg_fn(
                f"File contains {len(df):,} rows. "
                f"Maximum allowed is {_MAX_ROWS:,}. "
                "Please split the file and upload in smaller batches.",
                "error",
            )
            return

        # Progress bar lives here in render scope (not inside _run_batch)
        # so it is always in the correct Streamlit execution context.
        progress = st.progress(0, text="Running predictions...")
        result_df, warnings = _run_batch(df, active_bundle, fields, progress)
        progress.empty()

        result_label = get_result_label(
            schema,
            selected_meta.get("target", "predicted_value"),
        )
        col_name  = result_label.replace(" ", "_").lower()
        result_df = result_df.rename(columns={"predicted_value": col_name})

        st.session_state[keys["result"]]  = {
            "df":           result_df,
            "target_col":   col_name,
            "target_label": result_label,
            "warnings":     warnings,
        }
        st.session_state[keys["file_id"]] = current_file_id

    stored = st.session_state.get(keys["result"])
    if stored is None:
        return

    _render_batch_results(stored, fields, plots, model_id, msg_fn)


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def _load_file(uploaded_file: Any) -> tuple[pd.DataFrame | None, str | None]:
    """Load CSV or XLSX into a DataFrame. Returns (df, None) or (None, error)."""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            return None, "Unsupported file type. Please upload CSV or XLSX."
        return df, None
    except Exception as exc:
        return None, f"Could not read file: {exc}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_df(
    df: pd.DataFrame,
    fields: list[dict],
) -> tuple[bool, str | None]:
    """Check that all required schema field columns exist in the DataFrame."""
    if df is None or df.empty:
        return False, "The uploaded file is empty."

    required = [f["name"] for f in fields]
    missing  = [c for c in required if c not in df.columns]

    if missing:
        return (
            False,
            "Missing required columns: "
            + ", ".join(missing)
            + ". Please check the file format guide above.",
        )
    return True, None


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def _run_batch(
    df: pd.DataFrame,
    active_bundle: Any,
    fields: list[dict],
    progress: Any,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Run predict() on each row of df.

    Parameters
    ----------
    df            : Validated input DataFrame.
    active_bundle : Loaded ModelBundle.
    fields        : Schema fields list.
    progress      : st.progress bar instance created by the caller.

    Returns
    -------
    (result_df, warnings) where result_df has a "predicted_value" column appended.
    """
    result_df    = df.copy()
    predictions: list[float] = []
    all_warnings: list[str]  = []
    field_names  = [f["name"] for f in fields]

    # to_dict("records") preserves exact column names, including those with
    # spaces or hyphens that itertuples() would silently rename.
    records = df.to_dict("records")
    total   = len(records)

    for i, row_dict_raw in enumerate(records):
        row_dict = {name: row_dict_raw.get(name) for name in field_names}

        try:
            pred = predict(active_bundle, row_dict)
            predictions.append(pred.value)
            for w in pred.warnings:
                if w not in all_warnings:
                    all_warnings.append(w)
        except Exception as exc:
            predictions.append(float("nan"))
            msg = f"Row {i + 1}: {exc}"
            if msg not in all_warnings:
                all_warnings.append(msg)

        if (i + 1) % 100 == 0 or i == total - 1:
            progress.progress(
                (i + 1) / total,
                text=f"Processing row {i + 1} of {total:,}...",
            )

    result_df["predicted_value"] = predictions
    return result_df, all_warnings


# ---------------------------------------------------------------------------
# Results renderer
# ---------------------------------------------------------------------------

def _render_batch_results(
    stored: dict,
    fields: list[dict],
    plots: list[dict],
    model_id: str,
    msg_fn: Any,
) -> None:
    df           = stored["df"]
    target_col   = stored["target_col"]
    target_label = stored["target_label"]
    warnings     = stored.get("warnings", [])

    st.divider()
    st.subheader(":material/insights: Batch Results")

    # Summary metrics
    valid_preds = df[target_col].dropna()
    if not valid_preds.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows Processed", f"{len(df):,}")
        c2.metric(f"Avg {target_label}", _fmt_val(valid_preds.mean(), target_label))
        c3.metric(f"Min {target_label}", _fmt_val(valid_preds.min(), target_label))
        c4.metric(f"Max {target_label}", _fmt_val(valid_preds.max(), target_label))

    for w in warnings:
        msg_fn(w, "warning")

    # Preview table
    with st.expander(":material/table: Results Preview (first 500 rows)", expanded=True):
        st.dataframe(df.head(500), use_container_width=True)

    # Downloads
    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            ":material/download: Download CSV",
            data      = csv_bytes,
            file_name = f"batch_results_{model_id}.csv",
            mime      = "text/csv",
            key       = f"mh_ext_batch_dl_csv_{model_id}",
        )

    with dl_col2:
        xlsx_buffer = io.BytesIO()
        df.to_excel(xlsx_buffer, index=False)
        xlsx_buffer.seek(0)
        st.download_button(
            ":material/download: Download XLSX",
            data      = xlsx_buffer.getvalue(),
            file_name = f"batch_results_{model_id}.xlsx",
            mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key       = f"mh_ext_batch_dl_xlsx_{model_id}",
        )

    # Schema-declared charts
    if plots:
        st.divider()
        st.subheader(":material/bar_chart: Charts")
        render_schema_plots(
            plots         = plots,
            result_value  = None,
            raw_input     = {},
            batch_df      = df.copy(),
            schema_fields = fields,
        )

    # Auto-generated prediction distribution (always shown when predictions exist).
    # Uses the same theme pipeline as schema_plots.py and the main batch tab:
    #   get_colorway()[0]  -- active first chart color
    #   get_token(...)     -- semantic token for bar outline
    #   apply_theme(fig)   -- full layout pass (backgrounds, grid, fonts)
    #   theme=None         -- prevents Streamlit overriding the theme
    if not valid_preds.empty:
        import plotly.express as px
        from app.theme import apply_theme, get_colorway, get_token
        st.divider()
        st.subheader(":material/analytics: Prediction Distribution")
        fig = px.histogram(
            df, x=target_col, nbins=40,
            title=f"{target_label} Distribution",
            labels={target_col: target_label},
            color_discrete_sequence=[get_colorway()[0]],
        )
        fig.update_traces(
            marker_line_width = 0.8,
            marker_line_color = get_token("surface_overlay", "#1B2230"),
        )
        apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True, theme=None)


# ---------------------------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------------------------

def _fmt_val(value: float, target_label: str) -> str:
    """Format a scalar summary value based on target name heuristics."""
    tl = target_label.lower()
    if any(kw in tl for kw in ("salary", "wage", "income", "pay", "usd", "price", "cost")):
        return f"${value:,.0f}"
    if any(kw in tl for kw in ("pct", "percent", "rate", "ratio")):
        return f"{value:.2f}%"
    if abs(value) >= 1_000:
        return f"{value:,.2f}"
    return f"{value:.4f}"