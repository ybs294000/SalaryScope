"""
hr_tools/hiring_budget.py
--------------------------
Hiring Budget Estimator.

HR inputs a role profile and headcount. The tool predicts salary for
that profile and computes projected annual payroll, with optional
employer cost additions (benefits, taxes, overhead) and an HR override.

Performance: one model.predict() call per render. Override widget is
rendered before prediction so the result value is passed in directly.

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

DEFAULT_BENEFITS_PCT   = 20.0
DEFAULT_OVERHEAD_PCT   = 10.0
DEFAULT_RECRUITING_USD = 5_000
_HB_APP1_STATE_KEY = "hb_a1_result_payload"
_HB_APP2_STATE_KEY = "hb_a2_result_payload"


def render_hiring_budget(**kwargs):

    is_app1        = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Hiring Budget Estimator")
    st.caption(
        "Estimate total annual payroll cost for an open role. "
        "Employer cost factors (benefits, overhead, recruiting) are adjustable. "
        "Use the override section if the model estimate does not match your internal salary bands."
    )
    st.divider()
    st.markdown("#### Role Profile")

    if is_app1:
        _render_app1_budget(kwargs, title_features)
    else:
        _render_app2_budget(kwargs, title_features)


# ---------------------------------------------------------------------------
# App 1
# ---------------------------------------------------------------------------

def _render_app1_budget(kwargs, title_features):

    app1_model             = kwargs.get("app1_model")
    app1_salary_band_model = kwargs.get("app1_salary_band_model")
    app1_job_titles        = kwargs.get("app1_job_titles", [])
    app1_countries         = kwargs.get("app1_countries", [])
    app1_genders           = kwargs.get("app1_genders", ["Male", "Female", "Other"])
    SALARY_BAND_LABELS     = kwargs.get("SALARY_BAND_LABELS", {})

    if app1_model is None:
        st.warning("Model 1 is not loaded. Switch to Model 1 using the model selector above.")
        return

    with st.form("hb_a1_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            job_title = st.selectbox("Job Title", app1_job_titles, key="hb_a1_job_title")
            country   = st.selectbox("Country", app1_countries, key="hb_a1_country")
        with col2:
            years_exp = st.number_input("Years of Experience", 0.0, 40.0, 5.0, 0.5, key="hb_a1_years_exp")
            education = st.selectbox(
                "Education Level",
                options=[0, 1, 2, 3],
                format_func=lambda x: {0: "High School", 1: "Bachelor", 2: "Master", 3: "PhD"}[x],
                index=1, key="hb_a1_education",
            )
        with col3:
            age       = st.number_input("Approximate Age", 18, 70, 30, key="hb_a1_age")
            gender    = st.selectbox("Gender", app1_genders, key="hb_a1_gender")
            is_senior = st.selectbox("Senior Role", [0, 1], format_func=lambda x: "Yes" if x else "No", key="hb_a1_senior")

        headcount = st.number_input("Number of Openings", 1, 500, 1, 1, key="hb_a1_headcount")

        st.markdown("#### Compensation Reference")
        st.caption("You can keep the model estimate or replace it with an internal reference value before running the budget.")
        col_ov1, col_ov2 = st.columns([1, 2])
        with col_ov1:
            apply_override = st.checkbox("Apply override", key="hb_a1_apply_override")
            override_val = None
            if apply_override:
                override_val = st.number_input(
                    "Override salary (USD / year)",
                    min_value=10_000,
                    max_value=2_000_000,
                    value=80_000,
                    step=1_000,
                    key="hb_a1_override_val",
                )
        with col_ov2:
            override_reason = st.text_input(
                "Reason for override",
                placeholder="e.g. Internal band policy, local market adjustment",
                key="hb_a1_override_reason",
            )

        st.markdown("#### Employer Cost Assumptions")
        st.caption("These assumptions affect only the projected budget, not the model estimate.")
        col_b, col_o, col_r = st.columns(3)
        with col_b:
            benefits_pct = st.number_input(
                "Benefits & PF (%)", 0.0, 100.0, DEFAULT_BENEFITS_PCT, 1.0,
                key="hb_benefits_pct",
                help="Health insurance, provident fund, and similar benefits as % of base.",
            )
        with col_o:
            overhead_pct = st.number_input(
                "Overhead (%)", 0.0, 100.0, DEFAULT_OVERHEAD_PCT, 1.0,
                key="hb_overhead_pct",
                help="Workspace, equipment, IT, and admin overhead as % of base.",
            )
        with col_r:
            recruiting_usd = st.number_input(
                "Recruiting Cost per Hire (USD)", 0, 200_000, DEFAULT_RECRUITING_USD, 500,
                key="hb_recruiting",
                help="One-time cost: agency fees, job boards, interview time.",
            )

        submitted = st.form_submit_button("Calculate Hiring Budget", type="primary", width="stretch")

    if submitted:
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
            override_usd=float(override_val) if apply_override and override_val else None,
            override_reason=override_reason,
        )
        st.session_state[_HB_APP1_STATE_KEY] = {
            "result": result,
            "headcount": headcount,
            "job_title": job_title,
            "benefits_pct": benefits_pct,
            "overhead_pct": overhead_pct,
            "recruiting_usd": recruiting_usd,
        }

    payload = st.session_state.get(_HB_APP1_STATE_KEY)
    if payload is None:
        st.info("Fill in the role profile and click Calculate Hiring Budget to generate the budget summary.")
        return

    st.caption("Update the form and click Calculate Hiring Budget again whenever you want to refresh the result.")
    _render_budget_output(**payload)


# ---------------------------------------------------------------------------
# App 2
# ---------------------------------------------------------------------------

def _render_app2_budget(kwargs, title_features):

    app2_model                              = kwargs.get("app2_model")
    app2_job_titles                         = kwargs.get("app2_job_titles", [])
    app2_experience_levels                  = kwargs.get("app2_experience_levels", [])
    app2_employment_types                   = kwargs.get("app2_employment_types", [])
    app2_company_sizes                      = kwargs.get("app2_company_sizes", [])
    app2_remote_ratios                      = kwargs.get("app2_remote_ratios", [0, 50, 100])
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
        st.warning("Model 2 is not loaded. Switch to Model 2 using the model selector above.")
        return

    exp_display    = [EXPERIENCE_MAP.get(e, e) for e in app2_experience_levels]
    emp_display    = [EMPLOYMENT_MAP.get(e, e) for e in app2_employment_types]
    size_display   = [COMPANY_SIZE_MAP.get(s, s) for s in app2_company_sizes]
    remote_display = [REMOTE_MAP.get(r, str(r)) for r in app2_remote_ratios]

    with st.form("hb_a2_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            job_title = st.selectbox("Job Title", app2_job_titles, key="hb_a2_job")
            exp_sel   = st.selectbox("Experience Level", exp_display, key="hb_a2_exp")
            emp_sel   = st.selectbox("Employment Type",  emp_display, key="hb_a2_emp")
        with col2:
            loc_sel = st.selectbox("Company Location", app2_country_display_options, key="hb_a2_loc")
            res_sel = st.selectbox("Employee Residence", app2_employee_residence_display_options, key="hb_a2_res")
        with col3:
            size_sel   = st.selectbox("Company Size", size_display, key="hb_a2_size")
            remote_sel = st.selectbox("Work Mode", remote_display, key="hb_a2_remote")

        headcount = st.number_input("Number of Openings", 1, 500, 1, 1, key="hb_a2_headcount")

        loc_code = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
        res_code = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
        rem_val  = app2_remote_ratios[remote_display.index(remote_sel)]

        st.markdown("#### Compensation Reference")
        st.caption("You can keep the model estimate or replace it with an internal reference value before running the budget.")
        col_ov1, col_ov2 = st.columns([1, 2])
        with col_ov1:
            apply_override = st.checkbox("Apply override", key="hb_a2_apply_override")
            override_val = None
            if apply_override:
                override_val = st.number_input(
                    "Override salary (USD / year)",
                    min_value=10_000,
                    max_value=2_000_000,
                    value=80_000,
                    step=1_000,
                    key="hb_a2_override_val",
                )
        with col_ov2:
            override_reason = st.text_input(
                "Reason for override",
                placeholder="e.g. Internal band policy, local market adjustment",
                key="hb_a2_override_reason",
            )

        st.markdown("#### Employer Cost Assumptions")
        st.caption("These assumptions affect only the projected budget, not the model estimate.")
        col_b, col_o, col_r = st.columns(3)
        with col_b:
            benefits_pct = st.number_input(
                "Benefits & PF (%)", 0.0, 100.0, DEFAULT_BENEFITS_PCT, 1.0,
                key="hb_a2_benefits_pct",
                help="Health insurance, provident fund, and similar benefits as % of base.",
            )
        with col_o:
            overhead_pct = st.number_input(
                "Overhead (%)", 0.0, 100.0, DEFAULT_OVERHEAD_PCT, 1.0,
                key="hb_a2_overhead_pct",
                help="Workspace, equipment, IT, and admin overhead as % of base.",
            )
        with col_r:
            recruiting_usd = st.number_input(
                "Recruiting Cost per Hire (USD)", 0, 200_000, DEFAULT_RECRUITING_USD, 500,
                key="hb_a2_recruiting",
                help="One-time cost: agency fees, job boards, interview time.",
            )

        submitted = st.form_submit_button("Calculate Hiring Budget", type="primary", width="stretch")

    if submitted:
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
            override_usd=float(override_val) if apply_override and override_val else None,
            override_reason=override_reason,
        )
        st.session_state[_HB_APP2_STATE_KEY] = {
            "result": result,
            "headcount": headcount,
            "job_title": job_title,
            "benefits_pct": benefits_pct,
            "overhead_pct": overhead_pct,
            "recruiting_usd": recruiting_usd,
        }

    payload = st.session_state.get(_HB_APP2_STATE_KEY)
    if payload is None:
        st.info("Fill in the role profile and click Calculate Hiring Budget to generate the budget summary.")
        return

    st.caption("Update the form and click Calculate Hiring Budget again whenever you want to refresh the result.")
    _render_budget_output(**payload)


# ---------------------------------------------------------------------------
# Shared output
# ---------------------------------------------------------------------------

def _render_budget_output(result: dict, headcount: int, job_title: str, benefits_pct: float, overhead_pct: float, recruiting_usd: float):
    base      = result["final_usd"]
    benefits  = base * benefits_pct / 100
    overhead  = base * overhead_pct / 100
    total_per = base + benefits + overhead
    total_all = total_per * headcount + recruiting_usd * headcount

    st.divider()
    st.markdown("#### Budget Summary")

    if result["override_applied"]:
        st.info(f":material/edit: Override active — {result['note']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Model Estimate", f"${result['predicted_usd']:,.0f}", help="Raw model output in USD / year.")
    m2.metric("Base Salary Used", f"${base:,.0f}", delta="Override" if result["override_applied"] else None, delta_color="off")
    m3.metric("Total Cost per Hire / year", f"${total_per:,.0f}", help="Base + benefits + overhead.")
    m4.metric(f"Total for {headcount} Hire{'s' if headcount > 1 else ''}", f"${total_all:,.0f}", help="Includes one-time recruiting cost.")

    if result["band_label"]:
        st.caption(f"Salary band: **{result['band_label']}**")

    st.markdown("#### Cost Breakdown per Hire")

    # Lazy import — plotly is only imported when this function actually executes.
    import plotly.graph_objects as go
    colorway = get_colorway()

    fig = go.Figure(go.Bar(
        x=["Base Salary", "Benefits & PF", "Overhead", "Recruiting (one-time)"],
        y=[base, benefits, overhead, float(recruiting_usd)],
        marker_color=[
            colorway[0],
            colorway[1] if len(colorway) > 1 else colorway[0],
            colorway[2] if len(colorway) > 2 else colorway[0],
            colorway[4] if len(colorway) > 4 else colorway[-1],
        ],
        text=[f"${v:,.0f}" for v in [base, benefits, overhead, float(recruiting_usd)]],
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_layout(
        title_text="",
        yaxis_title="USD",
        margin=dict(t=20, b=20),
        height=300,
    )
    apply_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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

    summary_lines = [
        f"Role: {job_title}",
        f"Openings: {headcount}",
        f"Reference basis: {'HR override' if result['override_applied'] else 'Model estimate'}",
        f"Total annual budget: ${total_all:,.0f}",
    ]
    render_export_buttons(
        title="SalaryScope HR Tools — Hiring Budget Summary",
        file_stem="hiring_budget",
        csv_df=export_df,
        summary_lines=summary_lines,
        key_prefix="hb_export",
        csv_label=":material/download: Download CSV",
        xlsx_label=":material/table_view: Download XLSX",
        pdf_label=":material/picture_as_pdf: Download PDF",
        docx_label=":material/description: Download DOCX",
    )
