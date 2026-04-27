"""
hr_tools/benchmarking_table.py
-------------------------------
Salary Benchmarking Table.

For a selected job title and location, produces a grid of model
predictions across all experience levels. Helps HR establish internal
salary bands.

Performance: predictions are cached via st.cache_data keyed on all
input parameters. Changing any input invalidates the cache for that
combination only. The chart re-renders only when the edited table
data changes, which Streamlit handles naturally because data_editor
returns a new object only on edit.

Standalone: removing this file removes only this sub-tab.
"""

import streamlit as st
import pandas as pd

from app.hr_tools.predict_helpers import (
    predict_app1,
    predict_app2,
)
from app.hr_tools.export_utils import render_export_buttons
from app.theme import apply_theme, get_colorway

_APP1_EXPERIENCE_LABELS = {
    "Entry (0-3 yrs)":   (1.5, 0),
    "Mid (3-7 yrs)":     (5.0, 0),
    "Senior (7-15 yrs)": (10.0, 1),
    "Lead (15+ yrs)":    (18.0, 1),
}

_EDUCATION_LABELS = {
    "High School": 0,
    "Bachelor":    1,
    "Master":      2,
    "PhD":         3,
}
_BT_APP1_STATE_KEY = "bt_a1_grid_payload"
_BT_APP2_STATE_KEY = "bt_a2_grid_payload"


# ---------------------------------------------------------------------------
# Cached prediction grids
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _cached_app1_grid(
    job_title, country, gender, edu_val,
    # model objects cannot be hashed by cache_data, so pass a hash key instead
    _model_hash: str,
    # Pass the actual model objects via a non-hashed argument by prefixing with _
    _model, _salary_band_model, _title_features, _SALARY_BAND_LABELS,
) -> list[dict]:
    """
    Compute the 4-row benchmarking grid for App 1.
    Result is cached; recomputed only when inputs change.
    _model_hash identifies which loaded model is in use so cache invalidates
    on model switch without trying to hash the model object itself.
    """
    rows = []
    for exp_label, (yrs, senior) in _APP1_EXPERIENCE_LABELS.items():
        res = predict_app1(
            model=_model,
            salary_band_model=_salary_band_model,
            job_title=job_title,
            country=country,
            years_experience=yrs,
            education_level=edu_val,
            age=30,
            gender=gender,
            is_senior=senior,
            title_features=_title_features,
            SALARY_BAND_LABELS=_SALARY_BAND_LABELS,
        )
        rows.append({
            "Experience Level":      exp_label,
            "Model Estimate (USD)":  res["predicted_usd"],
            "Salary Band":           res["band_label"] or "—",
        })
    return rows


@st.cache_data(show_spinner=False)
def _cached_app2_grid(
    job_title, emp_sel, loc_code, res_code, rem_val, size_sel,
    _model_hash: str,
    _model, _exp_display, _title_features,
    _EXPERIENCE_REVERSE, _EMPLOYMENT_REVERSE, _COMPANY_SIZE_REVERSE,
) -> list[dict]:
    """Compute the experience-level grid for App 2. Cached."""
    rows = []
    for exp_disp in _exp_display:
        res = predict_app2(
            model=_model,
            job_title=job_title,
            experience_level=exp_disp,
            employment_type=emp_sel,
            company_location=loc_code,
            employee_residence=res_code,
            remote_ratio=rem_val,
            company_size=size_sel,
            title_features=_title_features,
            EXPERIENCE_REVERSE=_EXPERIENCE_REVERSE,
            EMPLOYMENT_REVERSE=_EMPLOYMENT_REVERSE,
            COMPANY_SIZE_REVERSE=_COMPANY_SIZE_REVERSE,
        )
        rows.append({
            "Experience Level":      exp_disp,
            "Model Estimate (USD)":  res["predicted_usd"],
            "Salary Band":           "—",
        })
    return rows


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_benchmarking_table(**kwargs):

    is_app1        = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Salary Benchmarking Table")
    st.caption(
        "Generate a reference grid for a role across experience levels. "
        "Use this to define or validate your internal compensation bands. "
        "The grid is cached — it only recomputes when you change an input."
    )
    st.divider()

    if is_app1:
        _render_app1_bench(kwargs, title_features)
    else:
        _render_app2_bench(kwargs, title_features)


# ---------------------------------------------------------------------------
# App 1
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

    with st.form("bt_a1_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            job_title = st.selectbox("Job Title", app1_job_titles, key="bt_a1_job")
        with col2:
            country = st.selectbox("Country", app1_countries, key="bt_a1_country")
        with col3:
            gender    = st.selectbox("Gender (for model input)", app1_genders, key="bt_a1_gender")
            education = st.selectbox("Education Level", list(_EDUCATION_LABELS.keys()), index=1, key="bt_a1_edu")
        submitted = st.form_submit_button("Generate Benchmark Grid", type="primary", width="stretch")

    if submitted:
        edu_val = _EDUCATION_LABELS[education]
        model_hash = str(id(app1_model))
        with st.spinner("Computing benchmark grid..."):
            rows = _cached_app1_grid(
                job_title, country, gender, edu_val,
                model_hash,
                app1_model, app1_salary_band_model, title_features, SALARY_BAND_LABELS,
            )
        st.session_state[_BT_APP1_STATE_KEY] = {
            "rows": rows,
            "job_title": job_title,
            "location": country,
            "key_prefix": "bt_a1",
        }

    payload = st.session_state.get(_BT_APP1_STATE_KEY)
    if payload is None:
        st.info("Select a role profile and click Generate Benchmark Grid to build the salary benchmarking table.")
        return

    st.caption("Update the role inputs and click Generate Benchmark Grid again whenever you want to refresh the table.")
    _render_bench_output(**payload)


# ---------------------------------------------------------------------------
# App 2
# ---------------------------------------------------------------------------

def _render_app2_bench(kwargs, title_features):

    app2_model              = kwargs.get("app2_model")
    app2_job_titles         = kwargs.get("app2_job_titles", [])
    app2_experience_levels  = kwargs.get("app2_experience_levels", [])
    app2_employment_types   = kwargs.get("app2_employment_types", [])
    app2_company_sizes      = kwargs.get("app2_company_sizes", [])
    app2_remote_ratios      = kwargs.get("app2_remote_ratios", [0, 50, 100])
    app2_country_display_options            = kwargs.get("app2_country_display_options", [])
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

    with st.form("bt_a2_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            job_title = st.selectbox("Job Title", app2_job_titles, key="bt_a2_job")
            loc_sel   = st.selectbox("Company Location", app2_country_display_options, key="bt_a2_loc")
        with col2:
            emp_sel = st.selectbox("Employment Type", emp_display, key="bt_a2_emp")
            res_sel = st.selectbox("Employee Residence", app2_employee_residence_display_options, key="bt_a2_res")
        with col3:
            size_sel   = st.selectbox("Company Size", size_display, key="bt_a2_size")
            remote_sel = st.selectbox("Work Mode", remote_display, key="bt_a2_remote")
        submitted = st.form_submit_button("Generate Benchmark Grid", type="primary", width="stretch")

    if submitted:
        loc_code = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
        res_code = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
        rem_val  = app2_remote_ratios[remote_display.index(remote_sel)]
        model_hash = str(id(app2_model))

        with st.spinner("Computing benchmark grid..."):
            rows = _cached_app2_grid(
                job_title, emp_sel, loc_code, res_code, rem_val, size_sel,
                model_hash,
                app2_model, tuple(exp_display), title_features,
                EXPERIENCE_REVERSE, EMPLOYMENT_REVERSE, COMPANY_SIZE_REVERSE,
            )
        st.session_state[_BT_APP2_STATE_KEY] = {
            "rows": rows,
            "job_title": job_title,
            "location": loc_sel,
            "key_prefix": "bt_a2",
        }

    payload = st.session_state.get(_BT_APP2_STATE_KEY)
    if payload is None:
        st.info("Select a role profile and click Generate Benchmark Grid to build the salary benchmarking table.")
        return

    st.caption("Update the role inputs and click Generate Benchmark Grid again whenever you want to refresh the table.")
    _render_bench_output(**payload)


# ---------------------------------------------------------------------------
# Shared output
# ---------------------------------------------------------------------------

def _render_bench_output(rows: list[dict], job_title: str, location: str, key_prefix: str):

    st.divider()
    st.markdown(f"#### Benchmark Grid — {job_title} — {location}")
    st.caption(
        "Edit the HR Override, Band Min, and Band Max columns directly in the table. "
        "Model Estimate and Salary Band are read-only."
    )

    df = pd.DataFrame(rows)
    df["Model Estimate (USD)"] = df["Model Estimate (USD)"].round(0).astype(int)
    df["HR Override (USD)"]    = df["Model Estimate (USD)"]
    df["Band Min (USD)"]       = (df["Model Estimate (USD)"] * 0.9).round(-2).astype(int)
    df["Band Max (USD)"]       = (df["Model Estimate (USD)"] * 1.15).round(-2).astype(int)
    df["Internal Notes"]       = ""

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        disabled=["Experience Level", "Model Estimate (USD)", "Salary Band"],
        column_config={
            "Model Estimate (USD)": st.column_config.NumberColumn(format="$%d"),
            "HR Override (USD)":    st.column_config.NumberColumn(format="$%d", help="Your internal band midpoint."),
            "Band Min (USD)":       st.column_config.NumberColumn(format="$%d"),
            "Band Max (USD)":       st.column_config.NumberColumn(format="$%d"),
            "Internal Notes":       st.column_config.TextColumn(help="e.g. Aligned to Grade 4 pay scale"),
        },
        key=f"{key_prefix}_editor",
    )

    edited["vs Model (%)"] = (
        (edited["HR Override (USD)"] - edited["Model Estimate (USD)"])
        / edited["Model Estimate (USD)"] * 100
    ).round(1)

    st.markdown("#### Visualisation")

    import plotly.graph_objects as go
    colorway = get_colorway()

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Model Estimate", x=edited["Experience Level"], y=edited["Model Estimate (USD)"], marker_color=colorway[0]))
    fig.add_trace(go.Bar(name="HR Override",    x=edited["Experience Level"], y=edited["HR Override (USD)"],    marker_color=colorway[1] if len(colorway) > 1 else colorway[0], opacity=0.7))
    fig.add_trace(go.Scatter(name="Band Min", x=edited["Experience Level"], y=edited["Band Min (USD)"], mode="markers", marker_symbol="triangle-up",   marker_color=colorway[2] if len(colorway) > 2 else colorway[0], marker_size=10))
    fig.add_trace(go.Scatter(name="Band Max", x=edited["Experience Level"], y=edited["Band Max (USD)"], mode="markers", marker_symbol="triangle-down", marker_color=colorway[4] if len(colorway) > 4 else colorway[-1], marker_size=10))
    fig.update_layout(
        title_text="",
        barmode="group",
        yaxis_title="Annual Salary (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, b=20),
        height=340,
    )
    apply_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    summary_lines = [
        f"Role: {job_title}",
        f"Location: {location}",
        "The table combines model estimates with editable HR band planning fields.",
    ]
    render_export_buttons(
        title="SalaryScope HR Tools — Salary Benchmarking Table",
        file_stem=f"salary_benchmark_{job_title.replace(' ', '_')}",
        csv_df=edited,
        summary_lines=summary_lines,
        key_prefix=f"{key_prefix}_export",
        csv_label=":material/download: Download CSV",
        xlsx_label=":material/table_view: Download XLSX",
        pdf_label=":material/picture_as_pdf: Download PDF",
        docx_label=":material/description: Download DOCX",
    )
