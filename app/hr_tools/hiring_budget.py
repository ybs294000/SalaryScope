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
    render_override_widget,
)

DEFAULT_BENEFITS_PCT   = 20.0
DEFAULT_OVERHEAD_PCT   = 10.0
DEFAULT_RECRUITING_USD = 5_000


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

    # Read override state BEFORE running prediction so only one predict() call is needed.
    # We pass a placeholder estimate (0) on the first render; the widget shows the
    # actual estimate from session state on subsequent renders via the number_input value.
    # Because the override expander is collapsed by default, the checkbox starts False
    # and the returned override_val is None, so predict() uses the model output.
    # On the first render the model_estimate shown in the caption will be correct because
    # render_override_widget receives the true model estimate computed below after widget reads.
    # To achieve this without double-predict we read widget state from session_state directly.

    override_key    = "hb_a1_apply_override"
    override_active = st.session_state.get(override_key, False)
    override_val    = st.session_state.get("hb_a1_override_val", None) if override_active else None
    override_reason = st.session_state.get("hb_a1_override_reason", "") if override_active else ""

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
        override_usd=float(override_val) if override_active and override_val else None,
        override_reason=override_reason,
    )

    # Now render the override widget — it will show the correct model estimate in its caption.
    render_override_widget("hb_a1", result["predicted_usd"])

    _render_budget_output(result, headcount, job_title)


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

    override_active = st.session_state.get("hb_a2_apply_override", False)
    override_val    = st.session_state.get("hb_a2_override_val", None) if override_active else None
    override_reason = st.session_state.get("hb_a2_override_reason", "") if override_active else ""

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
        override_usd=float(override_val) if override_active and override_val else None,
        override_reason=override_reason,
    )

    render_override_widget("hb_a2", result["predicted_usd"])
    _render_budget_output(result, headcount, job_title)


# ---------------------------------------------------------------------------
# Shared output
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
        height=300,
    )
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

    st.download_button(
        label=":material/download: Export Budget Summary (CSV)",
        data=export_df.to_csv(index=False),
        file_name="hiring_budget.csv",
        mime="text/csv",
        key="hb_export",
    )
