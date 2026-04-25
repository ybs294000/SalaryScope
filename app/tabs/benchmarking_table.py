"""
hr_tools/benchmarking_table.py
-------------------------------
Salary Benchmarking Table.

For a selected job title and location, produces a grid of model
predictions across all experience levels and employment types.
Helps HR establish internal salary bands.

Overrides can be applied per-cell. The final table can be exported
as a CSV for use in internal compensation documentation.

Standalone: removing this file removes only this sub-tab.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.tabs.hr_tools.predict_helpers import (
    predict_app1,
    predict_app2,
)


# Labels used in the grid rows
_APP1_EXPERIENCE_LABELS = {
    "Entry (0-3 yrs)":  (1.5, 0),
    "Mid (3-7 yrs)":    (5.0, 0),
    "Senior (7-15 yrs)": (10.0, 1),
    "Lead (15+ yrs)":   (18.0, 1),
}

_EDUCATION_LABELS = {
    "High School": 0,
    "Bachelor":    1,
    "Master":      2,
    "PhD":         3,
}


def render_benchmarking_table(**kwargs):

    is_app1 = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Salary Benchmarking Table")
    st.caption(
        "Generate a market-rate reference grid for a role across experience levels. "
        "Use this to define or validate your internal compensation bands. "
        "You can override any individual cell if the model estimate does not match "
        "your internal data."
    )

    st.divider()

    if is_app1:
        _render_app1_bench(kwargs, title_features)
    else:
        _render_app2_bench(kwargs, title_features)


# ---------------------------------------------------------------------------
# App 1 benchmarking
# ---------------------------------------------------------------------------

def _render_app1_bench(kwargs, title_features):

    app1_model             = kwargs.get("app1_model")
    app1_salary_band_model = kwargs.get("app1_salary_band_model")
    app1_job_titles        = kwargs.get("app1_job_titles", [])
    app1_countries         = kwargs.get("app1_countries", [])
    app1_genders           = kwargs.get("app1_genders", ["Male", "Female", "Other"])
    SALARY_BAND_LABELS     = kwargs.get("SALARY_BAND_LABELS", {})

    if app1_model is None:
        st.warning("Model 1 is not loaded.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        job_title = st.selectbox("Job Title", app1_job_titles, key="bt_a1_job")
    with col2:
        country = st.selectbox("Country", app1_countries, key="bt_a1_country")
    with col3:
        gender = st.selectbox("Gender (for model input)", app1_genders, key="bt_a1_gender")
        education = st.selectbox(
            "Education Level",
            list(_EDUCATION_LABELS.keys()),
            index=1,
            key="bt_a1_edu",
        )

    edu_val = _EDUCATION_LABELS[education]
    age = 30  # neutral fixed value for benchmarking grid

    rows = []
    for exp_label, (yrs, senior) in _APP1_EXPERIENCE_LABELS.items():
        res = predict_app1(
            model=app1_model,
            salary_band_model=app1_salary_band_model,
            job_title=job_title,
            country=country,
            years_experience=yrs,
            education_level=edu_val,
            age=age,
            gender=gender,
            is_senior=senior,
            title_features=title_features,
            SALARY_BAND_LABELS=SALARY_BAND_LABELS,
        )
        rows.append({
            "Experience Level": exp_label,
            "Model Estimate (USD)": res["predicted_usd"],
            "Salary Band": res["band_label"] or "—",
        })

    _render_bench_output(rows, job_title, country, key_prefix="bt_a1")


# ---------------------------------------------------------------------------
# App 2 benchmarking
# ---------------------------------------------------------------------------

def _render_app2_bench(kwargs, title_features):

    app2_model              = kwargs.get("app2_model")
    app2_job_titles         = kwargs.get("app2_job_titles", [])
    app2_experience_levels  = kwargs.get("app2_experience_levels", [])
    app2_employment_types   = kwargs.get("app2_employment_types", [])
    app2_company_sizes      = kwargs.get("app2_company_sizes", [])
    app2_remote_ratios      = kwargs.get("app2_remote_ratios", [0, 50, 100])
    app2_country_display_options = kwargs.get("app2_country_display_options", [])
    app2_employee_residence_display_options = kwargs.get("app2_employee_residence_display_options", [])
    EXPERIENCE_MAP    = kwargs.get("EXPERIENCE_MAP", {})
    EMPLOYMENT_MAP    = kwargs.get("EMPLOYMENT_MAP", {})
    COMPANY_SIZE_MAP  = kwargs.get("COMPANY_SIZE_MAP", {})
    REMOTE_MAP        = kwargs.get("REMOTE_MAP", {})
    EXPERIENCE_REVERSE = kwargs.get("EXPERIENCE_REVERSE", {})
    EMPLOYMENT_REVERSE = kwargs.get("EMPLOYMENT_REVERSE", {})
    COMPANY_SIZE_REVERSE = kwargs.get("COMPANY_SIZE_REVERSE", {})

    if app2_model is None:
        st.warning("Model 2 is not loaded.")
        return

    exp_display    = [EXPERIENCE_MAP.get(e, e) for e in app2_experience_levels]
    emp_display    = [EMPLOYMENT_MAP.get(e, e) for e in app2_employment_types]
    size_display   = [COMPANY_SIZE_MAP.get(s, s) for s in app2_company_sizes]
    remote_display = [REMOTE_MAP.get(r, str(r)) for r in app2_remote_ratios]

    col1, col2, col3 = st.columns(3)
    with col1:
        job_title = st.selectbox("Job Title", app2_job_titles, key="bt_a2_job")
        loc_sel   = st.selectbox("Company Location", app2_country_display_options, key="bt_a2_loc")
    with col2:
        emp_sel    = st.selectbox("Employment Type", emp_display, key="bt_a2_emp")
        res_sel    = st.selectbox("Employee Residence", app2_employee_residence_display_options, key="bt_a2_res")
    with col3:
        size_sel   = st.selectbox("Company Size", size_display, key="bt_a2_size")
        remote_sel = st.selectbox("Work Mode", remote_display, key="bt_a2_remote")

    loc_code  = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
    res_code  = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
    rem_val   = app2_remote_ratios[remote_display.index(remote_sel)]

    rows = []
    for exp_disp in exp_display:
        res = predict_app2(
            model=app2_model,
            job_title=job_title,
            experience_level=exp_disp,
            employment_type=emp_sel,
            company_location=loc_code,
            employee_residence=res_code,
            remote_ratio=rem_val,
            company_size=size_sel,
            title_features=title_features,
            EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
            EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
            COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
        )
        rows.append({
            "Experience Level": exp_disp,
            "Model Estimate (USD)": res["predicted_usd"],
            "Salary Band": "—",
        })

    country_label = loc_sel
    _render_bench_output(rows, job_title, country_label, key_prefix="bt_a2")


# ---------------------------------------------------------------------------
# Shared output
# ---------------------------------------------------------------------------

def _render_bench_output(rows: list[dict], job_title: str, location: str, key_prefix: str):

    st.divider()
    st.markdown(f"#### Benchmark Grid — {job_title} — {location}")
    st.caption(
        "The table below shows model estimates per experience level. "
        "Use the override columns to enter your internal band values. "
        "Band Min / Max are optional guidance fields for your compensation documentation."
    )

    # Build editable override table using st.data_editor
    df = pd.DataFrame(rows)
    df["Model Estimate (USD)"] = df["Model Estimate (USD)"].round(0).astype(int)
    df["HR Override (USD)"] = df["Model Estimate (USD)"]  # default = model
    df["Band Min (USD)"] = (df["Model Estimate (USD)"] * 0.9).round(-2).astype(int)
    df["Band Max (USD)"] = (df["Model Estimate (USD)"] * 1.15).round(-2).astype(int)
    df["Internal Notes"] = ""

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=["Experience Level", "Model Estimate (USD)", "Salary Band"],
        column_config={
            "Model Estimate (USD)": st.column_config.NumberColumn(format="$%d"),
            "HR Override (USD)":    st.column_config.NumberColumn(format="$%d", help="Enter your internal band midpoint here."),
            "Band Min (USD)":       st.column_config.NumberColumn(format="$%d"),
            "Band Max (USD)":       st.column_config.NumberColumn(format="$%d"),
            "Internal Notes":       st.column_config.TextColumn(help="e.g. 'Aligned to Grade 4 pay scale'"),
        },
        key=f"{key_prefix}_editor",
    )

    # Delta column
    edited["vs Model (%)"] = (
        (edited["HR Override (USD)"] - edited["Model Estimate (USD)"])
        / edited["Model Estimate (USD)"] * 100
    ).round(1)

    st.markdown("#### Visualisation")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Model Estimate",
        x=edited["Experience Level"],
        y=edited["Model Estimate (USD)"],
        marker_color="#4F8EF7",
    ))
    fig.add_trace(go.Bar(
        name="HR Override",
        x=edited["Experience Level"],
        y=edited["HR Override (USD)"],
        marker_color="#60A5FA",
        opacity=0.7,
    ))
    # Band range as error-bar style
    fig.add_trace(go.Scatter(
        name="Band Min",
        x=edited["Experience Level"],
        y=edited["Band Min (USD)"],
        mode="markers",
        marker_symbol="triangle-up",
        marker_color="#93C5FD",
        marker_size=10,
    ))
    fig.add_trace(go.Scatter(
        name="Band Max",
        x=edited["Experience Level"],
        y=edited["Band Max (USD)"],
        mode="markers",
        marker_symbol="triangle-down",
        marker_color="#CBD5E1",
        marker_size=10,
    ))
    fig.update_layout(
        barmode="group",
        yaxis_title="Annual Salary (USD)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#C9D1D9",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, b=20),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        label=":material/download: Export Benchmark Table (CSV)",
        data=edited.to_csv(index=False),
        file_name=f"salary_benchmark_{job_title.replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"{key_prefix}_export",
    )
