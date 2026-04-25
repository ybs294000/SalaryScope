"""
hr_tools/team_audit.py
-----------------------
Team Compensation Audit.

HR uploads a CSV of their current team. The tool runs batch model
predictions for each employee, computes the delta between their
current salary and the model estimate, and flags potential outliers.

CSV format:
    App 1 columns: Age, Years of Experience, Education Level, Senior,
                   Gender, Job Title, Country, Current Salary (USD)
    App 2 columns: experience_level, employment_type, job_title,
                   employee_residence, remote_ratio, company_location,
                   company_size, current_salary_usd

A global HR override multiplier is available (e.g. "our salaries run
15% above model") to adjust the reference line without per-row overrides.

Threshold sliders allow HR to define what counts as "underpaid" or
"overpaid" for their organisation.

Standalone: removing this file removes only this sub-tab.
"""

import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from app.hr_tools.predict_helpers import (
    predict_app1,
    predict_app2,
)


# ---------------------------------------------------------------------------
# Column specs
# ---------------------------------------------------------------------------

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
    {
        "Age": 28, "Years of Experience": 3, "Education Level": 1,
        "Senior": 0, "Gender": "Male", "Job Title": "Software Engineer",
        "Country": "USA", "Current Salary (USD)": 85000,
    },
    {
        "Age": 35, "Years of Experience": 9, "Education Level": 2,
        "Senior": 1, "Gender": "Female", "Job Title": "Data Scientist",
        "Country": "USA", "Current Salary (USD)": 115000,
    },
    {
        "Age": 42, "Years of Experience": 15, "Education Level": 3,
        "Senior": 1, "Gender": "Male", "Job Title": "Director of Data Science",
        "Country": "Canada", "Current Salary (USD)": 140000,
    },
    {
        "Age": 30, "Years of Experience": 5, "Education Level": 1,
        "Senior": 0, "Gender": "Female", "Job Title": "Marketing Analyst",
        "Country": "UK", "Current Salary (USD)": 60000,
    },
    {
        "Age": 26, "Years of Experience": 1, "Education Level": 1,
        "Senior": 0, "Gender": "Male", "Job Title": "Junior Software Engineer",
        "Country": "USA", "Current Salary (USD)": 72000,
    },
])

APP2_SAMPLE_DATA = pd.DataFrame([
    {
        "experience_level": "MI", "employment_type": "FT",
        "job_title": "Data Scientist", "employee_residence": "US",
        "remote_ratio": 50, "company_location": "US",
        "company_size": "M", "current_salary_usd": 112000,
    },
    {
        "experience_level": "SE", "employment_type": "FT",
        "job_title": "Machine Learning Engineer", "employee_residence": "US",
        "remote_ratio": 100, "company_location": "US",
        "company_size": "L", "current_salary_usd": 145000,
    },
    {
        "experience_level": "EN", "employment_type": "FT",
        "job_title": "Data Analyst", "employee_residence": "GB",
        "remote_ratio": 0, "company_location": "GB",
        "company_size": "M", "current_salary_usd": 48000,
    },
    {
        "experience_level": "EX", "employment_type": "FT",
        "job_title": "Head of Data", "employee_residence": "DE",
        "remote_ratio": 50, "company_location": "DE",
        "company_size": "L", "current_salary_usd": 165000,
    },
])


def render_team_audit(**kwargs):

    is_app1        = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Team Compensation Audit")
    st.caption(
        "Upload your team's salary data to compare current compensation against model estimates. "
        "The tool flags employees who may be significantly underpaid or overpaid relative to "
        "the model's prediction for their profile. "
        "Use the adjustment and threshold controls to calibrate the analysis to your organisation."
    )
    st.caption(
        ":material/info: This tool does not write or store any data. "
        "All processing happens locally in your browser session."
    )

    st.divider()

    required_cols = APP1_AUDIT_REQUIRED if is_app1 else APP2_AUDIT_REQUIRED
    sample_df     = APP1_SAMPLE_DATA.copy() if is_app1 else APP2_SAMPLE_DATA.copy()

    # Download sample template
    sample_csv = sample_df.to_csv(index=False)
    st.download_button(
        label=":material/download: Download Sample CSV Template",
        data=sample_csv,
        file_name="team_audit_template.csv",
        mime="text/csv",
        key="ta_sample_download",
    )

    st.markdown(
        f"**Required columns:** `{'`, `'.join(required_cols)}`"
    )

    uploaded = st.file_uploader(
        "Upload team CSV",
        type=["csv"],
        key="ta_upload",
    )

    if uploaded is None:
        st.info("Upload a CSV file to begin the audit. Use the sample template above as a starting point.")
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

    st.success(f"Loaded {len(df)} records.")

    # ------------------------------------------------------------------
    # Analysis controls
    # ------------------------------------------------------------------
    st.markdown("#### Audit Configuration")

    col_adj, col_under, col_over = st.columns(3)

    with col_adj:
        global_adj_pct = st.number_input(
            "Global model adjustment (%)",
            min_value=-50.0, max_value=100.0,
            value=0.0, step=5.0,
            key="ta_adj_pct",
            help=(
                "Use this if your organisation's salary scale is systematically above or below "
                "the model's training distribution. "
                "Example: enter 15 if your salaries are typically 15% above the model estimate."
            ),
        )

    with col_under:
        underpaid_threshold = st.number_input(
            "Underpaid threshold (%)",
            min_value=1.0, max_value=80.0,
            value=15.0, step=1.0,
            key="ta_under_threshold",
            help="Flag employees whose current salary is more than this % below the adjusted model estimate.",
        )

    with col_over:
        overpaid_threshold = st.number_input(
            "Overpaid threshold (%)",
            min_value=1.0, max_value=80.0,
            value=20.0, step=1.0,
            key="ta_over_threshold",
            help="Flag employees whose current salary is more than this % above the adjusted model estimate.",
        )

    # ------------------------------------------------------------------
    # Run predictions
    # ------------------------------------------------------------------
    if is_app1:
        result_df = _run_app1_audit(df, kwargs, title_features)
    else:
        result_df = _run_app2_audit(df, kwargs, title_features)

    if result_df is None or result_df.empty:
        return

    # Apply global adjustment
    adj_factor = 1 + global_adj_pct / 100.0
    result_df["Adjusted Reference (USD)"] = (result_df["Model Estimate (USD)"] * adj_factor).round(0)

    current_col = "Current Salary (USD)" if is_app1 else "current_salary_usd"

    result_df["Delta vs Reference (USD)"] = (
        result_df[current_col] - result_df["Adjusted Reference (USD)"]
    ).round(0)

    result_df["Delta vs Reference (%)"] = (
        result_df["Delta vs Reference (USD)"] / result_df["Adjusted Reference (USD)"] * 100
    ).round(1)

    def _flag(delta_pct):
        if delta_pct < -underpaid_threshold:
            return "Potentially Underpaid"
        elif delta_pct > overpaid_threshold:
            return "Potentially Overpaid"
        else:
            return "Within Range"

    result_df["Flag"] = result_df["Delta vs Reference (%)"].apply(_flag)

    _render_audit_output(result_df, current_col, global_adj_pct)


# ---------------------------------------------------------------------------
# App 1 batch prediction
# ---------------------------------------------------------------------------

def _run_app1_audit(df: pd.DataFrame, kwargs: dict, title_features) -> pd.DataFrame | None:

    app1_model             = kwargs.get("app1_model")
    app1_salary_band_model = kwargs.get("app1_salary_band_model")
    SALARY_BAND_LABELS     = kwargs.get("SALARY_BAND_LABELS", {})

    if app1_model is None:
        st.warning("Model 1 is not loaded.")
        return None

    estimates = []
    progress = st.progress(0, text="Running predictions...")

    for i, row in df.iterrows():
        try:
            res = predict_app1(
                model=app1_model,
                salary_band_model=app1_salary_band_model,
                job_title=str(row.get("Job Title", "")),
                country=str(row.get("Country", "Other")),
                years_experience=float(row.get("Years of Experience", 5)),
                education_level=int(row.get("Education Level", 1)),
                age=int(row.get("Age", 30)),
                gender=str(row.get("Gender", "Male")),
                is_senior=int(row.get("Senior", 0)),
                title_features=title_features,
                SALARY_BAND_LABELS=SALARY_BAND_LABELS,
            )
            estimates.append(round(res["predicted_usd"], 0))
        except Exception:
            estimates.append(np.nan)

        progress.progress((i + 1) / len(df))

    progress.empty()

    result_df = df.copy()
    result_df["Model Estimate (USD)"] = estimates
    result_df = result_df.dropna(subset=["Model Estimate (USD)"])
    return result_df


# ---------------------------------------------------------------------------
# App 2 batch prediction
# ---------------------------------------------------------------------------

def _run_app2_audit(df: pd.DataFrame, kwargs: dict, title_features) -> pd.DataFrame | None:

    app2_model           = kwargs.get("app2_model")
    EXPERIENCE_REVERSE   = kwargs.get("EXPERIENCE_REVERSE", {})
    EMPLOYMENT_REVERSE   = kwargs.get("EMPLOYMENT_REVERSE", {})
    COMPANY_SIZE_REVERSE = kwargs.get("COMPANY_SIZE_REVERSE", {})

    if app2_model is None:
        st.warning("Model 2 is not loaded.")
        return None

    estimates = []
    progress = st.progress(0, text="Running predictions...")

    for i, row in df.iterrows():
        try:
            res = predict_app2(
                model=app2_model,
                job_title=str(row.get("job_title", "")),
                experience_level=str(row.get("experience_level", "MI")),
                employment_type=str(row.get("employment_type", "FT")),
                company_location=str(row.get("company_location", "US")),
                employee_residence=str(row.get("employee_residence", "US")),
                remote_ratio=int(row.get("remote_ratio", 0)),
                company_size=str(row.get("company_size", "M")),
                title_features=title_features,
                EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
                EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
                COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
            )
            estimates.append(round(res["predicted_usd"], 0))
        except Exception:
            estimates.append(np.nan)

        progress.progress((i + 1) / len(df))

    progress.empty()

    result_df = df.copy()
    result_df["Model Estimate (USD)"] = estimates
    result_df = result_df.dropna(subset=["Model Estimate (USD)"])
    return result_df


# ---------------------------------------------------------------------------
# Shared audit output
# ---------------------------------------------------------------------------

def _render_audit_output(result_df: pd.DataFrame, current_col: str, global_adj_pct: float):

    st.divider()

    n_total      = len(result_df)
    n_underpaid  = (result_df["Flag"] == "Potentially Underpaid").sum()
    n_overpaid   = (result_df["Flag"] == "Potentially Overpaid").sum()
    n_ok         = (result_df["Flag"] == "Within Range").sum()

    st.markdown("#### Audit Summary")

    if global_adj_pct != 0:
        sign = "+" if global_adj_pct >= 0 else ""
        st.info(
            f":material/tune: Global model adjustment of {sign}{global_adj_pct:.0f}% applied. "
            "Adjusted reference figures are used for all flag calculations."
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Employees", n_total)
    m2.metric("Within Range", n_ok)
    m3.metric("Potentially Underpaid", n_underpaid, delta=f"-{n_underpaid}" if n_underpaid > 0 else None, delta_color="inverse")
    m4.metric("Potentially Overpaid", n_overpaid, delta=f"+{n_overpaid}" if n_overpaid > 0 else None, delta_color="off")

    # Scatter: current vs reference
    st.markdown("#### Current Salary vs Model Reference")

    fig = px.scatter(
        result_df,
        x="Adjusted Reference (USD)",
        y=current_col,
        color="Flag",
        color_discrete_map={
            "Within Range":          "#4F8EF7",
            "Potentially Underpaid": "#F87171",
            "Potentially Overpaid":  "#34D399",
        },
        hover_data=result_df.columns.tolist(),
        labels={
            "Adjusted Reference (USD)": "Model Reference (USD)",
            current_col: "Current Salary (USD)",
        },
    )

    # 1:1 reference line
    max_val = max(result_df["Adjusted Reference (USD)"].max(), result_df[current_col].max())
    min_val = min(result_df["Adjusted Reference (USD)"].min(), result_df[current_col].min())
    fig.add_shape(
        type="line",
        x0=min_val, y0=min_val,
        x1=max_val, y1=max_val,
        line=dict(color="#9CA3AF", dash="dot"),
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#C9D1D9",
        height=420,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Dots on the diagonal line are at exact model parity. Above the line = paid more than reference; below = paid less.")

    # Distribution of deltas
    st.markdown("#### Salary Delta Distribution")

    fig2 = go.Figure(go.Histogram(
        x=result_df["Delta vs Reference (%)"],
        nbinsx=30,
        marker_color="#4F8EF7",
        opacity=0.8,
    ))
    fig2.add_vline(x=0, line_color="#60A5FA", line_dash="dash")
    fig2.update_layout(
        xaxis_title="Delta vs Reference (%)",
        yaxis_title="Number of Employees",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#C9D1D9",
        height=300,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Flagged records detail
    if n_underpaid > 0 or n_overpaid > 0:
        st.markdown("#### Flagged Records")
        flagged = result_df[result_df["Flag"] != "Within Range"].copy()

        # Colour flag column in display
        st.dataframe(
            flagged,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Model Estimate (USD)":       st.column_config.NumberColumn(format="$%d"),
                "Adjusted Reference (USD)":   st.column_config.NumberColumn(format="$%d"),
                current_col:                  st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (USD)":   st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (%)":     st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    # Full table
    with st.expander("View full audit table"):
        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Model Estimate (USD)":       st.column_config.NumberColumn(format="$%d"),
                "Adjusted Reference (USD)":   st.column_config.NumberColumn(format="$%d"),
                current_col:                  st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (USD)":   st.column_config.NumberColumn(format="$%d"),
                "Delta vs Reference (%)":     st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    # Export
    st.download_button(
        label=":material/download: Export Full Audit (CSV)",
        data=result_df.to_csv(index=False),
        file_name="team_compensation_audit.csv",
        mime="text/csv",
        key="ta_export",
    )
