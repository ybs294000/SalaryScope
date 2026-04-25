"""
hr_tools/hiring_budget.py
--------------------------
Hiring Budget Estimator.

HR inputs a role profile and headcount. The tool predicts salary for
that profile and computes projected annual payroll, with optional
employer cost additions (benefits, taxes, overhead) and an HR override.

Standalone: removing this file removes only this sub-tab.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.hr_tools.predict_helpers import (
    predict_app1,
    predict_app2,
    render_override_widget,
)


# ---------------------------------------------------------------------------
# Employer cost assumptions — HR can adjust these
# ---------------------------------------------------------------------------
DEFAULT_BENEFITS_PCT   = 20.0   # % of base salary (health, PF, etc.)
DEFAULT_OVERHEAD_PCT   = 10.0   # % of base salary (equipment, workspace, admin)
DEFAULT_RECRUITING_USD = 5_000  # one-time per hire


def render_hiring_budget(**kwargs):

    is_app1       = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Hiring Budget Estimator")
    st.caption(
        "Estimate total annual payroll cost for an open role. "
        "Employer cost factors (benefits, overhead, recruiting) are adjustable. "
        "Use the override section if the model estimate does not match your internal salary bands."
    )

    st.divider()

    # ------------------------------------------------------------------
    # Section 1: Role profile
    # ------------------------------------------------------------------
    st.markdown("#### Role Profile")

    if is_app1:
        _render_app1_budget(kwargs, title_features)
    else:
        _render_app2_budget(kwargs, title_features)


# ---------------------------------------------------------------------------
# App 1 budget flow
# ---------------------------------------------------------------------------

def _render_app1_budget(kwargs, title_features):

    app1_model            = kwargs.get("app1_model")
    app1_salary_band_model = kwargs.get("app1_salary_band_model")
    app1_job_titles        = kwargs.get("app1_job_titles", [])
    app1_countries         = kwargs.get("app1_countries", [])
    app1_genders           = kwargs.get("app1_genders", ["Male", "Female", "Other"])
    SALARY_BAND_LABELS     = kwargs.get("SALARY_BAND_LABELS", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        job_title = st.selectbox(
            "Job Title",
            app1_job_titles,
            key="hb_a1_job_title",
        )
        country = st.selectbox(
            "Country",
            app1_countries,
            key="hb_a1_country",
        )

    with col2:
        years_exp = st.number_input(
            "Years of Experience",
            min_value=0.0, max_value=40.0, value=5.0, step=0.5,
            key="hb_a1_years_exp",
        )
        education = st.selectbox(
            "Education Level",
            options=[0, 1, 2, 3],
            format_func=lambda x: {0: "High School", 1: "Bachelor", 2: "Master", 3: "PhD"}[x],
            index=1,
            key="hb_a1_education",
        )

    with col3:
        age = st.number_input(
            "Approximate Age",
            min_value=18, max_value=70, value=30,
            key="hb_a1_age",
        )
        gender = st.selectbox(
            "Gender",
            app1_genders,
            key="hb_a1_gender",
        )
        is_senior = st.selectbox(
            "Senior Role",
            options=[0, 1],
            format_func=lambda x: "Yes" if x == 1 else "No",
            key="hb_a1_senior",
        )

    headcount = st.number_input(
        "Number of Openings",
        min_value=1, max_value=500, value=1, step=1,
        key="hb_a1_headcount",
    )

    if app1_model is None:
        st.warning("Model 1 is not loaded. Switch to Model 1 using the model selector above.")
        return

    # Initial prediction without override to get model estimate for widget default
    initial = predict_app1(
        model=app1_model,
        salary_band_model=app1_salary_band_model,
        job_title=job_title,
        country=country,
        years_experience=years_exp,
        education_level=education,
        age=age,
        gender=gender,
        is_senior=is_senior,
        title_features=title_features,
        SALARY_BAND_LABELS=SALARY_BAND_LABELS,
        override_usd=None,
    )

    override_val, override_reason = render_override_widget("hb_a1", initial["predicted_usd"])

    result = predict_app1(
        model=app1_model,
        salary_band_model=app1_salary_band_model,
        job_title=job_title,
        country=country,
        years_experience=years_exp,
        education_level=education,
        age=age,
        gender=gender,
        is_senior=is_senior,
        title_features=title_features,
        SALARY_BAND_LABELS=SALARY_BAND_LABELS,
        override_usd=override_val,
        override_reason=override_reason,
    )

    _render_budget_output(result, headcount, job_title)


# ---------------------------------------------------------------------------
# App 2 budget flow
# ---------------------------------------------------------------------------

def _render_app2_budget(kwargs, title_features):

    app2_model              = kwargs.get("app2_model")
    app2_job_titles         = kwargs.get("app2_job_titles", [])
    app2_experience_levels  = kwargs.get("app2_experience_levels", [])
    app2_employment_types   = kwargs.get("app2_employment_types", [])
    app2_company_sizes      = kwargs.get("app2_company_sizes", [])
    app2_remote_ratios      = kwargs.get("app2_remote_ratios", [0, 50, 100])
    app2_country_display_options           = kwargs.get("app2_country_display_options", [])
    app2_employee_residence_display_options = kwargs.get("app2_employee_residence_display_options", [])
    EXPERIENCE_MAP    = kwargs.get("EXPERIENCE_MAP", {})
    EMPLOYMENT_MAP    = kwargs.get("EMPLOYMENT_MAP", {})
    COMPANY_SIZE_MAP  = kwargs.get("COMPANY_SIZE_MAP", {})
    REMOTE_MAP        = kwargs.get("REMOTE_MAP", {})
    EXPERIENCE_REVERSE = kwargs.get("EXPERIENCE_REVERSE", {})
    EMPLOYMENT_REVERSE = kwargs.get("EMPLOYMENT_REVERSE", {})
    COMPANY_SIZE_REVERSE = kwargs.get("COMPANY_SIZE_REVERSE", {})

    exp_display   = [EXPERIENCE_MAP.get(e, e) for e in app2_experience_levels]
    emp_display   = [EMPLOYMENT_MAP.get(e, e) for e in app2_employment_types]
    size_display  = [COMPANY_SIZE_MAP.get(s, s) for s in app2_company_sizes]
    remote_display = [REMOTE_MAP.get(r, str(r)) for r in app2_remote_ratios]

    col1, col2, col3 = st.columns(3)

    with col1:
        job_title = st.selectbox("Job Title", app2_job_titles, key="hb_a2_job")
        exp_sel   = st.selectbox("Experience Level", exp_display, key="hb_a2_exp")
        emp_sel   = st.selectbox("Employment Type",  emp_display, key="hb_a2_emp")

    with col2:
        loc_sel  = st.selectbox("Company Location", app2_country_display_options, key="hb_a2_loc")
        res_sel  = st.selectbox("Employee Residence", app2_employee_residence_display_options, key="hb_a2_res")

    with col3:
        size_sel   = st.selectbox("Company Size", size_display, key="hb_a2_size")
        remote_sel = st.selectbox("Work Mode", remote_display, key="hb_a2_remote")

    headcount = st.number_input(
        "Number of Openings",
        min_value=1, max_value=500, value=1, step=1,
        key="hb_a2_headcount",
    )

    loc_code  = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
    res_code  = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
    rem_val   = app2_remote_ratios[remote_display.index(remote_sel)]

    if app2_model is None:
        st.warning("Model 2 is not loaded. Switch to Model 2 using the model selector above.")
        return

    initial = predict_app2(
        model=app2_model,
        job_title=job_title,
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
    )

    override_val, override_reason = render_override_widget("hb_a2", initial["predicted_usd"])

    result = predict_app2(
        model=app2_model,
        job_title=job_title,
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
        override_usd=override_val,
        override_reason=override_reason,
    )

    _render_budget_output(result, headcount, job_title)


# ---------------------------------------------------------------------------
# Shared budget output section
# ---------------------------------------------------------------------------

def _render_budget_output(result: dict, headcount: int, job_title: str):

    st.divider()
    st.markdown("#### Employer Cost Assumptions")
    st.caption(
        "Adjust these to match your organisation's actual cost structure. "
        "They do not affect the model prediction — only the total cost projection."
    )

    col_b, col_o, col_r = st.columns(3)
    with col_b:
        benefits_pct = st.number_input(
            "Benefits & PF (%)",
            min_value=0.0, max_value=100.0,
            value=DEFAULT_BENEFITS_PCT, step=1.0,
            key="hb_benefits_pct",
            help="Percentage of base salary added for health insurance, provident fund, and similar benefits.",
        )
    with col_o:
        overhead_pct = st.number_input(
            "Overhead (%)",
            min_value=0.0, max_value=100.0,
            value=DEFAULT_OVERHEAD_PCT, step=1.0,
            key="hb_overhead_pct",
            help="Percentage of base salary for workspace, equipment, IT, and admin overhead.",
        )
    with col_r:
        recruiting_usd = st.number_input(
            "Recruiting Cost per Hire (USD)",
            min_value=0, max_value=200_000,
            value=DEFAULT_RECRUITING_USD, step=500,
            key="hb_recruiting",
            help="One-time cost per hire: agency fees, job boards, interview time, etc.",
        )

    base      = result["final_usd"]
    benefits  = base * benefits_pct / 100
    overhead  = base * overhead_pct / 100
    total_per = base + benefits + overhead
    total_all = total_per * headcount + recruiting_usd * headcount

    st.divider()
    st.markdown("#### Budget Summary")

    if result["override_applied"]:
        st.info(f":material/edit: Override active — {result['note']}", icon=None)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Model Estimate", f"${result['predicted_usd']:,.0f}", help="Raw model output in USD / year.")
    m2.metric(
        "Base Salary Used",
        f"${base:,.0f}",
        delta="Override" if result["override_applied"] else None,
        delta_color="off",
    )
    m3.metric("Total Cost per Hire / year", f"${total_per:,.0f}", help="Base + benefits + overhead.")
    m4.metric(
        f"Total for {headcount} Hire{'s' if headcount > 1 else ''}",
        f"${total_all:,.0f}",
        help="Includes one-time recruiting cost per hire.",
    )

    if result["band_label"]:
        st.caption(f"Salary band: **{result['band_label']}**")

    # Breakdown chart
    st.markdown("#### Cost Breakdown per Hire")

    fig = go.Figure(go.Bar(
        x=["Base Salary", "Benefits & PF", "Overhead", "Recruiting (one-time)"],
        y=[base, benefits, overhead, float(recruiting_usd)],
        marker_color=["#4F8EF7", "#60A5FA", "#93C5FD", "#CBD5E1"],
        text=[f"${v:,.0f}" for v in [base, benefits, overhead, float(recruiting_usd)]],
        textposition="outside",
    ))
    fig.update_layout(
        yaxis_title="USD",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#C9D1D9",
        margin=dict(t=20, b=20),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Export
    export_df = pd.DataFrame([{
        "Job Title":             job_title,
        "Openings":              headcount,
        "Model Estimate (USD)":  round(result["predicted_usd"], 0),
        "Base Used (USD)":       round(base, 0),
        "Override Applied":      result["override_applied"],
        "Benefits & PF (USD)":   round(benefits, 0),
        "Overhead (USD)":        round(overhead, 0),
        "Cost per Hire (USD)":   round(total_per, 0),
        "Recruiting Cost (USD)": recruiting_usd,
        "Total Budget (USD)":    round(total_all, 0),
        "Notes":                 result["note"],
    }])

    st.download_button(
        label=":material/download: Export Budget Summary (CSV)",
        data=export_df.to_csv(index=False),
        file_name="hiring_budget.csv",
        mime="text/csv",
        key="hb_export",
    )
