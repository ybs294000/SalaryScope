"""
hr_tools/team_audit.py
-----------------------
Team Compensation Audit.

HR uploads a CSV of their current team. The tool runs batch model
predictions and flags employees whose current salary differs
significantly from the model estimate.

Performance:
    - Predictions are vectorised: the full feature DataFrame is built
      once and model.predict() is called once for the entire file,
      replacing the previous row-by-row loop.
    - Results are stored in st.session_state keyed on the uploaded
      file name + size, so the prediction batch does not re-run on
      every widget interaction (threshold slider, adjustment input).
    - Plotly and px are imported only inside _render_audit_output.

Standalone: removing this file removes only this sub-tab.
"""

import streamlit as st
import pandas as pd
import numpy as np

from app.hr_tools.predict_helpers import (
    batch_predict_app1,
    batch_predict_app2,
)
from app.theme import apply_theme, get_token

APP1_AUDIT_REQUIRED = [
    "Age", "Years of Experience", "Education Level",
    "Senior", "Gender", "Job Title", "Country",
    "Current Salary (USD)",
]

APP2_AUDIT_REQUIRED = [
    "experience_level", "employment_type", "job_title",
    "employee_residence", "remote_ratio", "company_location",
    "company_size", "current_salary_usd",
]

APP1_SAMPLE_DATA = pd.DataFrame([
    {"Age": 28, "Years of Experience": 3, "Education Level": 1, "Senior": 0, "Gender": "Male",   "Job Title": "Software Engineer",        "Country": "USA",    "Current Salary (USD)": 85000},
    {"Age": 35, "Years of Experience": 9, "Education Level": 2, "Senior": 1, "Gender": "Female", "Job Title": "Data Scientist",           "Country": "USA",    "Current Salary (USD)": 115000},
    {"Age": 42, "Years of Experience": 15,"Education Level": 3, "Senior": 1, "Gender": "Male",   "Job Title": "Director of Data Science", "Country": "Canada", "Current Salary (USD)": 140000},
    {"Age": 30, "Years of Experience": 5, "Education Level": 1, "Senior": 0, "Gender": "Female", "Job Title": "Marketing Analyst",        "Country": "UK",     "Current Salary (USD)": 60000},
    {"Age": 26, "Years of Experience": 1, "Education Level": 1, "Senior": 0, "Gender": "Male",   "Job Title": "Junior Software Engineer", "Country": "USA",    "Current Salary (USD)": 72000},
])

APP2_SAMPLE_DATA = pd.DataFrame([
    {"experience_level": "MI", "employment_type": "FT", "job_title": "Data Scientist",         "employee_residence": "US", "remote_ratio": 50,  "company_location": "US", "company_size": "M", "current_salary_usd": 112000},
    {"experience_level": "SE", "employment_type": "FT", "job_title": "Machine Learning Engineer","employee_residence": "US","remote_ratio": 100, "company_location": "US", "company_size": "L", "current_salary_usd": 145000},
    {"experience_level": "EN", "employment_type": "FT", "job_title": "Data Analyst",            "employee_residence": "GB", "remote_ratio": 0,   "company_location": "GB", "company_size": "M", "current_salary_usd": 48000},
    {"experience_level": "EX", "employment_type": "FT", "job_title": "Head of Data",            "employee_residence": "DE", "remote_ratio": 50,  "company_location": "DE", "company_size": "L", "current_salary_usd": 165000},
])

# Session state key prefix for cached audit results
_CACHE_KEY = "hr_audit_result"
_FILE_KEY  = "hr_audit_file_id"


def render_team_audit(**kwargs):

    is_app1        = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Team Compensation Audit")
    st.caption(
        "Upload your team's salary data to compare current compensation against model estimates. "
        "Predictions are run once on upload; changing thresholds or adjustments does not re-run them."
    )
    st.caption(
        ":material/info: No data is stored. All processing happens in your browser session."
    )
    st.divider()

    required_cols = APP1_AUDIT_REQUIRED if is_app1 else APP2_AUDIT_REQUIRED
    sample_df     = APP1_SAMPLE_DATA if is_app1 else APP2_SAMPLE_DATA

    st.download_button(
        label=":material/download: Download Sample CSV Template",
        data=sample_df.to_csv(index=False),
        file_name="team_audit_template.csv",
        mime="text/csv",
        key="ta_sample_download",
    )
    st.markdown(f"**Required columns:** `{'`, `'.join(required_cols)}`")

    uploaded = st.file_uploader("Upload team CSV", type=["csv"], key="ta_upload")

    if uploaded is None:
        st.info("Upload a CSV file to begin the audit.")
        # Clear any stale cached result if user removes the file
        st.session_state.pop(_CACHE_KEY, None)
        st.session_state.pop(_FILE_KEY, None)
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"Could not read the uploaded file: {exc}")
        return

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return

    # Unique ID for this file based on name and row count.
    # If the user uploads a different file the predictions are re-run.
    file_id = f"{uploaded.name}_{len(df)}_{is_app1}"

    if st.session_state.get(_FILE_KEY) != file_id:
        # New file — run vectorised batch prediction.
        st.info(f"Running predictions on {len(df)} records...")

        if is_app1:
            app1_model = kwargs.get("app1_model")
            if app1_model is None:
                st.warning("Model 1 is not loaded.")
                return
            estimates = batch_predict_app1(app1_model, df, title_features)
        else:
            app2_model           = kwargs.get("app2_model")
            EXPERIENCE_REVERSE   = kwargs.get("EXPERIENCE_REVERSE", {})
            EMPLOYMENT_REVERSE   = kwargs.get("EMPLOYMENT_REVERSE", {})
            COMPANY_SIZE_REVERSE = kwargs.get("COMPANY_SIZE_REVERSE", {})
            if app2_model is None:
                st.warning("Model 2 is not loaded.")
                return
            estimates = batch_predict_app2(
                app2_model, df, title_features,
                EXPERIENCE_REVERSE, EMPLOYMENT_REVERSE, COMPANY_SIZE_REVERSE,
            )

        result_df = df.copy()
        result_df["Model Estimate (USD)"] = estimates.round(0)
        result_df = result_df.dropna(subset=["Model Estimate (USD)"])
        result_df["Model Estimate (USD)"] = result_df["Model Estimate (USD)"].astype(int)

        st.session_state[_CACHE_KEY] = result_df
        st.session_state[_FILE_KEY]  = file_id
        st.success(f"Predictions complete — {len(result_df)} records processed.")
    else:
        result_df = st.session_state[_CACHE_KEY]
        st.success(f"{len(result_df)} records loaded from this session.")

    current_col = "Current Salary (USD)" if is_app1 else "current_salary_usd"

    # ------------------------------------------------------------------
    # Analysis controls — these run without re-triggering predictions
    # ------------------------------------------------------------------
    st.markdown("#### Audit Configuration")

    col_adj, col_under, col_over = st.columns(3)
    with col_adj:
        global_adj_pct = st.number_input(
            "Global model adjustment (%)", -50.0, 100.0, 0.0, 5.0,
            key="ta_adj_pct",
            help=(
                "If your salaries are systematically above/below the model, enter that % here. "
                "Example: 15 means the model typically underestimates your market by 15%."
            ),
        )
    with col_under:
        underpaid_threshold = st.number_input(
            "Underpaid threshold (%)", 1.0, 80.0, 15.0, 1.0,
            key="ta_under_threshold",
            help="Flag employees whose current salary is more than this % below the adjusted estimate.",
        )
    with col_over:
        overpaid_threshold = st.number_input(
            "Overpaid threshold (%)", 1.0, 80.0, 20.0, 1.0,
            key="ta_over_threshold",
            help="Flag employees whose current salary is more than this % above the adjusted estimate.",
        )

    # Apply adjustment and flag — pure pandas, no model calls
    adj_factor = 1 + global_adj_pct / 100.0
    result_df = result_df.copy()
    result_df["Adjusted Reference (USD)"] = (result_df["Model Estimate (USD)"] * adj_factor).round(0).astype(int)
    result_df["Delta vs Reference (USD)"] = (result_df[current_col] - result_df["Adjusted Reference (USD)"]).round(0)
    result_df["Delta vs Reference (%)"]   = (
        result_df["Delta vs Reference (USD)"] / result_df["Adjusted Reference (USD)"] * 100
    ).round(1)

    def _flag(pct):
        if pct < -underpaid_threshold:
            return "Potentially Underpaid"
        if pct > overpaid_threshold:
            return "Potentially Overpaid"
        return "Within Range"

    result_df["Flag"] = result_df["Delta vs Reference (%)"].apply(_flag)

    _render_audit_output(result_df, current_col, global_adj_pct)


# ---------------------------------------------------------------------------
# Output — plotly imported lazily here
# ---------------------------------------------------------------------------

def _render_audit_output(result_df: pd.DataFrame, current_col: str, global_adj_pct: float):

    import plotly.graph_objects as go
    import plotly.express as px

    st.divider()

    n_total     = len(result_df)
    n_underpaid = (result_df["Flag"] == "Potentially Underpaid").sum()
    n_overpaid  = (result_df["Flag"] == "Potentially Overpaid").sum()
    n_ok        = (result_df["Flag"] == "Within Range").sum()

    st.markdown("#### Audit Summary")

    if global_adj_pct != 0:
        sign = "+" if global_adj_pct >= 0 else ""
        st.info(
            f":material/tune: Global adjustment of {sign}{global_adj_pct:.0f}% applied. "
            "Adjusted reference figures are used for all flag calculations."
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Employees", n_total)
    m2.metric("Within Range", n_ok)
    m3.metric("Potentially Underpaid", n_underpaid, delta=f"-{n_underpaid}" if n_underpaid else None, delta_color="inverse")
    m4.metric("Potentially Overpaid",  n_overpaid,  delta=f"+{n_overpaid}"  if n_overpaid  else None, delta_color="off")

    st.markdown("#### Current Salary vs Model Reference")

    fig = px.scatter(
        result_df,
        x="Adjusted Reference (USD)",
        y=current_col,
        color="Flag",
        color_discrete_map={
            "Within Range":          get_token("accent_primary", "#4F8EF7"),
            "Potentially Underpaid": get_token("status_error", "#F87171"),
            "Potentially Overpaid":  get_token("status_success", "#34D399"),
        },
        hover_data=result_df.columns.tolist(),
        labels={"Adjusted Reference (USD)": "Model Reference (USD)", current_col: "Current Salary (USD)"},
    )

    max_val = max(result_df["Adjusted Reference (USD)"].max(), result_df[current_col].max())
    min_val = min(result_df["Adjusted Reference (USD)"].min(), result_df[current_col].min())
    fig.add_shape(type="line", x0=min_val, y0=min_val, x1=max_val, y1=max_val, line=dict(color=get_token("text_secondary", "#9CA3AF"), dash="dot"))
    fig.update_layout(
        title_text="",
        height=400,
        margin=dict(t=20, b=20),
    )
    apply_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Dots on the diagonal are at exact model parity. Above = paid more; below = paid less.")

    st.markdown("#### Salary Delta Distribution")

    fig2 = go.Figure(go.Histogram(
        x=result_df["Delta vs Reference (%)"],
        nbinsx=30,
        marker_color=get_token("accent_primary", "#4F8EF7"),
        opacity=0.8,
    ))
    fig2.add_vline(x=0, line_color=get_token("accent_hover", "#60A5FA"), line_dash="dash")
    fig2.update_layout(
        title_text="",
        xaxis_title="Delta vs Reference (%)",
        yaxis_title="Number of Employees",
        height=280,
        margin=dict(t=20, b=20),
    )
    apply_theme(fig2)
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    if n_underpaid > 0 or n_overpaid > 0:
        st.markdown("#### Flagged Records")
        flagged = result_df[result_df["Flag"] != "Within Range"]
        st.dataframe(
            flagged, use_container_width=True, hide_index=True,
            column_config={
                "Model Estimate (USD)":     st.column_config.NumberColumn(format="$%d"),
                "Adjusted Reference (USD)": st.column_config.NumberColumn(format="$%d"),
                current_col:               st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (USD)": st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (%)":   st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    with st.expander("View full audit table"):
        st.dataframe(
            result_df, use_container_width=True, hide_index=True,
            column_config={
                "Model Estimate (USD)":     st.column_config.NumberColumn(format="$%d"),
                "Adjusted Reference (USD)": st.column_config.NumberColumn(format="$%d"),
                current_col:               st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (USD)": st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (%)":   st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    st.download_button(
        label=":material/download: Export Full Audit (CSV)",
        data=result_df.to_csv(index=False),
        file_name="team_compensation_audit.csv",
        mime="text/csv",
        key="ta_export",
    )
