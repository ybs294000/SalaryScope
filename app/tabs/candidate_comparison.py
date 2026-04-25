"""
hr_tools/candidate_comparison.py
---------------------------------
Candidate Comparison Tool.

HR enters profiles for 2 to 5 candidates. The tool predicts expected
salary for each, displays a side-by-side comparison, and flags salary
spread across candidates. Each candidate can have an individual HR
override (e.g. to reflect a known expectation or counter-offer).

Standalone: removing this file removes only this sub-tab.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.tabs.hr_tools.predict_helpers import (
    predict_app1,
    predict_app2,
)


_EDUCATION_LABELS = {
    "High School": 0,
    "Bachelor":    1,
    "Master":      2,
    "PhD":         3,
}

_EDU_REVERSE = {v: k for k, v in _EDUCATION_LABELS.items()}


def render_candidate_comparison(**kwargs):

    is_app1 = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Candidate Comparison")
    st.caption(
        "Compare expected salary for up to 5 candidates side by side. "
        "Enter each candidate's profile and optionally override the model estimate "
        "with a known candidate expectation or counter-offer. "
        "Use this during offer planning to understand compensation spread across shortlisted candidates."
    )

    st.divider()

    n_candidates = st.number_input(
        "Number of candidates to compare",
        min_value=2, max_value=5, value=3, step=1,
        key="cc_n_candidates",
    )

    if is_app1:
        _render_app1_comparison(kwargs, title_features, int(n_candidates))
    else:
        _render_app2_comparison(kwargs, title_features, int(n_candidates))


# ---------------------------------------------------------------------------
# App 1 comparison
# ---------------------------------------------------------------------------

def _render_app1_comparison(kwargs, title_features, n: int):

    app1_model             = kwargs.get("app1_model")
    app1_salary_band_model = kwargs.get("app1_salary_band_model")
    app1_job_titles        = kwargs.get("app1_job_titles", [])
    app1_countries         = kwargs.get("app1_countries", [])
    app1_genders           = kwargs.get("app1_genders", ["Male", "Female", "Other"])
    SALARY_BAND_LABELS     = kwargs.get("SALARY_BAND_LABELS", {})

    if app1_model is None:
        st.warning("Model 1 is not loaded.")
        return

    cols = st.columns(n)
    results = []

    for i, col in enumerate(cols):
        with col:
            st.markdown(f"**Candidate {i + 1}**")
            name     = st.text_input("Name / ID", value=f"Candidate {i + 1}", key=f"cc_a1_name_{i}")
            job      = st.selectbox("Job Title", app1_job_titles, key=f"cc_a1_job_{i}")
            country  = st.selectbox("Country", app1_countries, key=f"cc_a1_country_{i}")
            yrs      = st.number_input("Years Exp.", 0.0, 40.0, 5.0, 0.5, key=f"cc_a1_yrs_{i}")
            edu_lbl  = st.selectbox("Education", list(_EDUCATION_LABELS.keys()), index=1, key=f"cc_a1_edu_{i}")
            age      = st.number_input("Age", 18, 70, 30, key=f"cc_a1_age_{i}")
            gender   = st.selectbox("Gender", app1_genders, key=f"cc_a1_gender_{i}")
            senior   = st.selectbox("Senior", [0, 1], format_func=lambda x: "Yes" if x else "No", key=f"cc_a1_senior_{i}")

            # Initial prediction
            init = predict_app1(
                model=app1_model,
                salary_band_model=app1_salary_band_model,
                job_title=job,
                country=country,
                years_experience=yrs,
                education_level=_EDUCATION_LABELS[edu_lbl],
                age=age,
                gender=gender,
                is_senior=senior,
                title_features=title_features,
                SALARY_BAND_LABELS=SALARY_BAND_LABELS,
            )

            st.caption(f"Model estimate: **${init['predicted_usd']:,.0f}**")

            apply_ov = st.checkbox("Apply override", key=f"cc_a1_ov_apply_{i}")
            ov_val   = None
            ov_note  = ""
            if apply_ov:
                ov_val  = st.number_input(
                    "Candidate expectation / override (USD)",
                    min_value=10_000, max_value=2_000_000,
                    value=int(round(init["predicted_usd"] / 1000) * 1000),
                    step=1_000,
                    key=f"cc_a1_ov_val_{i}",
                )
                ov_note = st.text_input(
                    "Override reason",
                    key=f"cc_a1_ov_reason_{i}",
                    placeholder="e.g. Candidate stated expectation",
                )

            final = predict_app1(
                model=app1_model,
                salary_band_model=app1_salary_band_model,
                job_title=job,
                country=country,
                years_experience=yrs,
                education_level=_EDUCATION_LABELS[edu_lbl],
                age=age,
                gender=gender,
                is_senior=senior,
                title_features=title_features,
                SALARY_BAND_LABELS=SALARY_BAND_LABELS,
                override_usd=ov_val,
                override_reason=ov_note,
            )

            results.append({
                "name":    name,
                "job":     job,
                "country": country,
                "yrs":     yrs,
                "edu":     edu_lbl,
                "result":  final,
            })

    _render_comparison_output(results)


# ---------------------------------------------------------------------------
# App 2 comparison
# ---------------------------------------------------------------------------

def _render_app2_comparison(kwargs, title_features, n: int):

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

    cols = st.columns(n)
    results = []

    for i, col in enumerate(cols):
        with col:
            st.markdown(f"**Candidate {i + 1}**")
            name    = st.text_input("Name / ID", value=f"Candidate {i + 1}", key=f"cc_a2_name_{i}")
            job     = st.selectbox("Job Title", app2_job_titles, key=f"cc_a2_job_{i}")
            exp_sel = st.selectbox("Experience Level", exp_display, key=f"cc_a2_exp_{i}")
            emp_sel = st.selectbox("Employment Type", emp_display, key=f"cc_a2_emp_{i}")
            loc_sel = st.selectbox("Company Location", app2_country_display_options, key=f"cc_a2_loc_{i}")
            res_sel = st.selectbox("Residence", app2_employee_residence_display_options, key=f"cc_a2_res_{i}")
            size_sel   = st.selectbox("Company Size", size_display, key=f"cc_a2_size_{i}")
            remote_sel = st.selectbox("Work Mode", remote_display, key=f"cc_a2_remote_{i}")

            loc_code = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
            res_code = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
            rem_val  = app2_remote_ratios[remote_display.index(remote_sel)]

            init = predict_app2(
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
            )

            st.caption(f"Model estimate: **${init['predicted_usd']:,.0f}**")

            apply_ov = st.checkbox("Apply override", key=f"cc_a2_ov_apply_{i}")
            ov_val   = None
            ov_note  = ""
            if apply_ov:
                ov_val  = st.number_input(
                    "Override (USD)",
                    min_value=10_000, max_value=2_000_000,
                    value=int(round(init["predicted_usd"] / 1000) * 1000),
                    step=1_000,
                    key=f"cc_a2_ov_val_{i}",
                )
                ov_note = st.text_input("Override reason", key=f"cc_a2_ov_reason_{i}")

            final = predict_app2(
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
                override_usd=ov_val,
                override_reason=ov_note,
            )

            results.append({
                "name":   name,
                "job":    job,
                "country": loc_sel,
                "yrs":    exp_sel,
                "edu":    size_sel,
                "result": final,
            })

    _render_comparison_output(results)


# ---------------------------------------------------------------------------
# Shared comparison output
# ---------------------------------------------------------------------------

def _render_comparison_output(results: list[dict]):

    if not results:
        return

    st.divider()
    st.markdown("#### Comparison Summary")

    names        = [r["name"] for r in results]
    model_vals   = [r["result"]["predicted_usd"] for r in results]
    final_vals   = [r["result"]["final_usd"] for r in results]
    overridden   = [r["result"]["override_applied"] for r in results]

    # Summary metrics
    m_cols = st.columns(len(results))
    for col, r in zip(m_cols, results):
        delta_str = None
        if r["result"]["override_applied"]:
            diff = r["result"]["final_usd"] - r["result"]["predicted_usd"]
            sign = "+" if diff >= 0 else ""
            delta_str = f"{sign}${diff:,.0f} vs model"
        col.metric(
            r["name"],
            f"${r['result']['final_usd']:,.0f}",
            delta=delta_str,
            delta_color="off",
        )

    # Bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Model Estimate",
        x=names,
        y=model_vals,
        marker_color="#4F8EF7",
    ))
    fig.add_trace(go.Bar(
        name="Final / Override",
        x=names,
        y=final_vals,
        marker_color="#60A5FA",
        opacity=0.75,
    ))
    fig.update_layout(
        barmode="group",
        yaxis_title="Annual Salary (USD)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#C9D1D9",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, b=20),
        height=340,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Spread analysis
    if len(final_vals) > 1:
        spread = max(final_vals) - min(final_vals)
        st.info(
            f":material/swap_vert: Salary spread across candidates: **${spread:,.0f}**. "
            "A wide spread may indicate inconsistent role definitions or varying candidate seniority."
        )

    # Export table
    export_rows = []
    for r in results:
        export_rows.append({
            "Candidate":             r["name"],
            "Job Title":             r["job"],
            "Model Estimate (USD)":  round(r["result"]["predicted_usd"], 0),
            "Override Applied":      r["result"]["override_applied"],
            "Final Salary (USD)":    round(r["result"]["final_usd"], 0),
            "Notes":                 r["result"]["note"],
        })

    export_df = pd.DataFrame(export_rows)

    st.download_button(
        label=":material/download: Export Comparison (CSV)",
        data=export_df.to_csv(index=False),
        file_name="candidate_comparison.csv",
        mime="text/csv",
        key="cc_export",
    )
