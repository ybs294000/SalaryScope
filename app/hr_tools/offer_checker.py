"""
hr_tools/offer_checker.py
--------------------------
Offer Competitiveness Checker.

HR inputs a role profile and their planned offer salary. The tool
predicts the model-estimated market rate and shows the delta.

Performance: override state is read from session_state before predict()
so exactly one model.predict() call is made per render.

Standalone: removing this file removes only this sub-tab.
"""

import streamlit as st
import pandas as pd

from app.hr_tools.predict_helpers import (
    predict_app1,
    predict_app2,
    render_override_widget,
)


def render_offer_checker(**kwargs):

    is_app1        = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Offer Competitiveness Checker")
    st.caption(
        "Enter a planned offer and compare it against the model's salary estimate for the role. "
        "If the model estimate does not reflect your internal data, use the override to substitute "
        "your own reference figure."
    )
    st.caption(
        ":material/info: The model was trained on a publicly available dataset. "
        "Treat the result as a directional guide, not a definitive market benchmark."
    )
    st.divider()

    if is_app1:
        _render_app1_checker(kwargs, title_features)
    else:
        _render_app2_checker(kwargs, title_features)


# ---------------------------------------------------------------------------
# App 1
# ---------------------------------------------------------------------------

def _render_app1_checker(kwargs, title_features):

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
        job     = st.selectbox("Job Title", app1_job_titles, key="oc_a1_job")
        country = st.selectbox("Country", app1_countries, key="oc_a1_country")
    with col2:
        yrs = st.number_input("Years of Experience", 0.0, 40.0, 5.0, 0.5, key="oc_a1_yrs")
        edu = st.selectbox(
            "Education Level", [0, 1, 2, 3],
            format_func=lambda x: {0: "High School", 1: "Bachelor", 2: "Master", 3: "PhD"}[x],
            index=1, key="oc_a1_edu",
        )
    with col3:
        age    = st.number_input("Age", 18, 70, 30, key="oc_a1_age")
        gender = st.selectbox("Gender", app1_genders, key="oc_a1_gender")
        senior = st.selectbox("Senior Role", [0, 1], format_func=lambda x: "Yes" if x else "No", key="oc_a1_senior")

    # Read override state before predict — one predict() call only.
    override_active = st.session_state.get("oc_a1_apply_override", False)
    override_val    = st.session_state.get("oc_a1_override_val", None) if override_active else None
    override_reason = st.session_state.get("oc_a1_override_reason", "") if override_active else ""

    result = predict_app1(
        model=app1_model,
        salary_band_model=app1_salary_band_model,
        job_title=job,
        country=country,
        years_experience=yrs,
        education_level=edu,
        age=age,
        gender=gender,
        is_senior=senior,
        title_features=title_features,
        SALARY_BAND_LABELS=SALARY_BAND_LABELS,
        override_usd=float(override_val) if override_active and override_val else None,
        override_reason=override_reason,
    )

    render_override_widget("oc_a1", result["predicted_usd"])
    _render_checker_output(result, key_prefix="oc_a1", job_title=job)


# ---------------------------------------------------------------------------
# App 2
# ---------------------------------------------------------------------------

def _render_app2_checker(kwargs, title_features):

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

    col1, col2, col3 = st.columns(3)
    with col1:
        job     = st.selectbox("Job Title", app2_job_titles, key="oc_a2_job")
        exp_sel = st.selectbox("Experience Level", exp_display, key="oc_a2_exp")
        emp_sel = st.selectbox("Employment Type", emp_display, key="oc_a2_emp")
    with col2:
        loc_sel = st.selectbox("Company Location", app2_country_display_options, key="oc_a2_loc")
        res_sel = st.selectbox("Employee Residence", app2_employee_residence_display_options, key="oc_a2_res")
    with col3:
        size_sel   = st.selectbox("Company Size", size_display, key="oc_a2_size")
        remote_sel = st.selectbox("Work Mode", remote_display, key="oc_a2_remote")

    loc_code = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
    res_code = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
    rem_val  = app2_remote_ratios[remote_display.index(remote_sel)]

    override_active = st.session_state.get("oc_a2_apply_override", False)
    override_val    = st.session_state.get("oc_a2_override_val", None) if override_active else None
    override_reason = st.session_state.get("oc_a2_override_reason", "") if override_active else ""

    result = predict_app2(
        model=app2_model,
        job_title=job,
        experience_level=exp_sel,
        employment_type=emp_sel,
        company_location=loc_code,
        employee_residence=res_code,
        remote_ratio=rem_val,
        company_size=size_sel,
        title_features=title_features,
        EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
        EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
        COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
        override_usd=float(override_val) if override_active and override_val else None,
        override_reason=override_reason,
    )

    render_override_widget("oc_a2", result["predicted_usd"])
    _render_checker_output(result, key_prefix="oc_a2", job_title=job)


# ---------------------------------------------------------------------------
# Shared checker output
# ---------------------------------------------------------------------------

def _render_checker_output(result: dict, key_prefix: str, job_title: str):

    reference = result["final_usd"]

    st.divider()
    st.markdown("#### Planned Offer")

    planned_offer = st.number_input(
        "Planned offer salary (USD / year)",
        min_value=10_000,
        max_value=2_000_000,
        value=int(round(reference / 1000) * 1000),
        step=1_000,
        key=f"{key_prefix}_planned_offer",
        help="Enter the salary you intend to offer the candidate.",
    )

    delta     = planned_offer - reference
    delta_pct = (delta / reference * 100) if reference else 0
    sign      = "+" if delta >= 0 else ""

    st.divider()
    st.markdown("#### Result")

    if result["override_applied"]:
        st.info(f":material/edit: Reference is HR override. {result['note']}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Reference Salary", f"${reference:,.0f}", help="Model estimate or HR override.")
    m2.metric("Planned Offer", f"${planned_offer:,.0f}")
    m3.metric("Offer vs Reference", f"{sign}{delta_pct:.1f}%", delta=f"{sign}${delta:,.0f}", delta_color="normal")

    gauge_min = int(reference * 0.6)
    gauge_max = int(reference * 1.4)

    import plotly.graph_objects as go

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=planned_offer,
        number={"prefix": "$", "valueformat": ",.0f"},
        delta={"reference": reference, "valueformat": ",.0f", "prefix": "$"},
        title={"text": f"Planned Offer vs Reference ({job_title})"},
        gauge={
            "axis": {"range": [gauge_min, gauge_max], "tickformat": "$,.0f"},
            "bar":  {"color": "#4F8EF7"},
            "steps": [
                {"range": [gauge_min, reference * 0.9],  "color": "#374151"},
                {"range": [reference * 0.9, reference * 1.1], "color": "#1F3A5F"},
                {"range": [reference * 1.1, gauge_max],  "color": "#1E3A3A"},
            ],
            "threshold": {"line": {"color": "#60A5FA", "width": 3}, "thickness": 0.85, "value": reference},
        },
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#C9D1D9",
        height=300,
        margin=dict(t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if delta_pct < -20:
        st.warning(
            ":material/arrow_downward: The planned offer is more than 20% below the reference estimate. "
            "Consider whether the profile inputs accurately represent the role, or use the override to "
            "provide a more appropriate reference figure."
        )
    elif delta_pct < -10:
        st.warning(
            ":material/arrow_downward: The planned offer is moderately below the reference estimate. "
            "Review whether benefits or non-cash compensation close the gap."
        )
    elif delta_pct <= 10:
        st.success(":material/check_circle: The planned offer is within 10% of the reference estimate.")
    else:
        st.success(":material/arrow_upward: The planned offer is above the reference estimate.")

    export_df = pd.DataFrame([{
        "Job Title":              job_title,
        "Reference Salary (USD)": round(reference, 0),
        "Override Applied":       result["override_applied"],
        "Model Estimate (USD)":   round(result["predicted_usd"], 0),
        "Planned Offer (USD)":    planned_offer,
        "Delta (USD)":            round(delta, 0),
        "Delta (%)":              round(delta_pct, 2),
        "Notes":                  result["note"],
    }])

    st.download_button(
        label=":material/download: Export Offer Analysis (CSV)",
        data=export_df.to_csv(index=False),
        file_name="offer_checker.csv",
        mime="text/csv",
        key=f"{key_prefix}_export",
    )
