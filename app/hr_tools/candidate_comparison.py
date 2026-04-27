"""
hr_tools/candidate_comparison.py
---------------------------------
Candidate Comparison Tool.

HR enters profiles for 2-5 candidates. The tool predicts expected
salary for each and displays a side-by-side comparison.

Performance: override state is read from session_state before predict(),
so each candidate runs exactly one model.predict() call per render.

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

_EDUCATION_LABELS = {
    "High School": 0,
    "Bachelor":    1,
    "Master":      2,
    "PhD":         3,
}
_CC_APP1_STATE_KEY = "cc_a1_results_payload"
_CC_APP2_STATE_KEY = "cc_a2_results_payload"


def render_candidate_comparison(**kwargs):

    is_app1        = kwargs.get("is_app1", True)
    title_features = kwargs.get("title_features")

    st.markdown("### Candidate Comparison")
    st.caption(
        "Compare expected salary for up to 5 candidates side by side. "
        "Use the override checkbox per candidate to substitute a known expectation or counter-offer."
    )
    st.divider()

    n_candidates = st.number_input(
        "Number of candidates to compare",
        min_value=2, max_value=5, value=3, step=1,
        key="cc_n_candidates",
    )

    prev_n = st.session_state.get("cc_prev_n_candidates")
    if prev_n is not None and prev_n != int(n_candidates):
        st.session_state.pop(_CC_APP1_STATE_KEY, None)
        st.session_state.pop(_CC_APP2_STATE_KEY, None)
    st.session_state["cc_prev_n_candidates"] = int(n_candidates)

    if is_app1:
        _render_app1_comparison(kwargs, title_features, int(n_candidates))
    else:
        _render_app2_comparison(kwargs, title_features, int(n_candidates))


# ---------------------------------------------------------------------------
# App 1
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

    with st.form("cc_a1_form"):
        cols = st.columns(n)
        candidate_inputs = []

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

                ov_apply  = st.checkbox("Apply override", key=f"cc_a1_ov_apply_{i}")
                ov_val    = None
                ov_note   = ""
                if ov_apply:
                    ov_val  = st.number_input(
                        "Candidate expectation / override (USD)",
                        min_value=10_000, max_value=2_000_000,
                        value=st.session_state.get(f"cc_a1_ov_val_{i}", 80_000),
                        step=1_000,
                        key=f"cc_a1_ov_val_{i}",
                    )
                    ov_note = st.text_input(
                        "Override reason",
                        key=f"cc_a1_ov_reason_{i}",
                        placeholder="e.g. Candidate stated expectation",
                    )

                candidate_inputs.append({
                    "name": name,
                    "job": job,
                    "country": country,
                    "yrs": yrs,
                    "edu_lbl": edu_lbl,
                    "age": age,
                    "gender": gender,
                    "senior": senior,
                    "ov_apply": ov_apply,
                    "ov_val": ov_val,
                    "ov_note": ov_note,
                })

        submitted = st.form_submit_button("Compare Candidates", type="primary", width="stretch")

    if submitted:
        results = []
        for item in candidate_inputs:
            result = predict_app1(
                model=app1_model,
                salary_band_model=app1_salary_band_model,
                job_title=item["job"],
                country=item["country"],
                years_experience=item["yrs"],
                education_level=_EDUCATION_LABELS[item["edu_lbl"]],
                age=item["age"],
                gender=item["gender"],
                is_senior=item["senior"],
                title_features=title_features,
                SALARY_BAND_LABELS=SALARY_BAND_LABELS,
                override_usd=float(item["ov_val"]) if item["ov_apply"] and item["ov_val"] else None,
                override_reason=item["ov_note"],
            )
            results.append({"name": item["name"], "job": item["job"], "country": item["country"], "result": result})
        st.session_state[_CC_APP1_STATE_KEY] = results

    results = st.session_state.get(_CC_APP1_STATE_KEY)
    if not results:
        st.info("Enter candidate details and click Compare Candidates to generate the side-by-side comparison.")
        return

    st.caption("Update the candidate inputs and click Compare Candidates again whenever you want to refresh the comparison.")
    _render_comparison_output(results)


# ---------------------------------------------------------------------------
# App 2
# ---------------------------------------------------------------------------

def _render_app2_comparison(kwargs, title_features, n: int):

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

    with st.form("cc_a2_form"):
        cols = st.columns(n)
        candidate_inputs = []

        for i, col in enumerate(cols):
            with col:
                st.markdown(f"**Candidate {i + 1}**")
                name       = st.text_input("Name / ID", value=f"Candidate {i + 1}", key=f"cc_a2_name_{i}")
                job        = st.selectbox("Job Title", app2_job_titles, key=f"cc_a2_job_{i}")
                exp_sel    = st.selectbox("Experience Level", exp_display, key=f"cc_a2_exp_{i}")
                emp_sel    = st.selectbox("Employment Type", emp_display, key=f"cc_a2_emp_{i}")
                loc_sel    = st.selectbox("Company Location", app2_country_display_options, key=f"cc_a2_loc_{i}")
                res_sel    = st.selectbox("Residence", app2_employee_residence_display_options, key=f"cc_a2_res_{i}")
                size_sel   = st.selectbox("Company Size", size_display, key=f"cc_a2_size_{i}")
                remote_sel = st.selectbox("Work Mode", remote_display, key=f"cc_a2_remote_{i}")

                loc_code = loc_sel.split("(")[-1].rstrip(")") if "(" in loc_sel else loc_sel
                res_code = res_sel.split("(")[-1].rstrip(")") if "(" in res_sel else res_sel
                rem_val  = app2_remote_ratios[remote_display.index(remote_sel)]

                ov_apply = st.checkbox("Apply override", key=f"cc_a2_ov_apply_{i}")
                ov_val   = None
                ov_note  = ""
                if ov_apply:
                    ov_val  = st.number_input(
                        "Override (USD)",
                        min_value=10_000, max_value=2_000_000,
                        value=st.session_state.get(f"cc_a2_ov_val_{i}", 80_000),
                        step=1_000,
                        key=f"cc_a2_ov_val_{i}",
                    )
                    ov_note = st.text_input("Override reason", key=f"cc_a2_ov_reason_{i}")

                candidate_inputs.append({
                    "name": name,
                    "job": job,
                    "loc_sel": loc_sel,
                    "exp_sel": exp_sel,
                    "emp_sel": emp_sel,
                    "loc_code": loc_code,
                    "res_code": res_code,
                    "rem_val": rem_val,
                    "size_sel": size_sel,
                    "ov_apply": ov_apply,
                    "ov_val": ov_val,
                    "ov_note": ov_note,
                })

        submitted = st.form_submit_button("Compare Candidates", type="primary", width="stretch")

    if submitted:
        results = []
        for item in candidate_inputs:
            result = predict_app2(
                model=app2_model,
                job_title=item["job"],
                experience_level=item["exp_sel"],
                employment_type=item["emp_sel"],
                company_location=item["loc_code"],
                employee_residence=item["res_code"],
                remote_ratio=item["rem_val"],
                company_size=item["size_sel"],
                title_features=title_features,
                EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
                EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
                COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
                override_usd=float(item["ov_val"]) if item["ov_apply"] and item["ov_val"] else None,
                override_reason=item["ov_note"],
            )
            results.append({"name": item["name"], "job": item["job"], "country": item["loc_sel"], "result": result})
        st.session_state[_CC_APP2_STATE_KEY] = results

    results = st.session_state.get(_CC_APP2_STATE_KEY)
    if not results:
        st.info("Enter candidate details and click Compare Candidates to generate the side-by-side comparison.")
        return

    st.caption("Update the candidate inputs and click Compare Candidates again whenever you want to refresh the comparison.")
    _render_comparison_output(results)


# ---------------------------------------------------------------------------
# Shared output
# ---------------------------------------------------------------------------

def _render_comparison_output(results: list[dict]):

    if not results:
        return

    st.divider()
    st.markdown("#### Comparison Summary")

    names      = [r["name"] for r in results]
    model_vals = [r["result"]["predicted_usd"] for r in results]
    final_vals = [r["result"]["final_usd"] for r in results]

    m_cols = st.columns(len(results))
    for col, r in zip(m_cols, results):
        delta_str = None
        if r["result"]["override_applied"]:
            diff = r["result"]["final_usd"] - r["result"]["predicted_usd"]
            sign = "+" if diff >= 0 else ""
            delta_str = f"{sign}${diff:,.0f} vs model"
        col.metric(r["name"], f"${r['result']['final_usd']:,.0f}", delta=delta_str, delta_color="off")

    import plotly.graph_objects as go
    colorway = get_colorway()

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Model Estimate", x=names, y=model_vals, marker_color=colorway[0]))
    fig.add_trace(go.Bar(name="Final / Override", x=names, y=final_vals, marker_color=colorway[1] if len(colorway) > 1 else colorway[0], opacity=0.75))
    fig.update_layout(
        title_text="",
        barmode="group",
        yaxis_title="Annual Salary (USD)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=40, b=20),
        height=320,
    )
    apply_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if len(final_vals) > 1:
        spread = max(final_vals) - min(final_vals)
        st.info(
            f":material/swap_vert: Salary spread across candidates: **${spread:,.0f}**. "
            "A wide spread may indicate inconsistent role definitions or varying candidate seniority."
        )

    export_rows = [{
        "Candidate":            r["name"],
        "Job Title":            r["job"],
        "Model Estimate (USD)": round(r["result"]["predicted_usd"], 0),
        "Override Applied":     r["result"]["override_applied"],
        "Final Salary (USD)":   round(r["result"]["final_usd"], 0),
        "Notes":                r["result"]["note"],
    } for r in results]

    export_df = pd.DataFrame(export_rows)
    summary_lines = [
        f"Candidates compared: {len(results)}",
        f"Highest final salary: ${max(final_vals):,.0f}",
        f"Lowest final salary: ${min(final_vals):,.0f}",
    ]
    render_export_buttons(
        title="SalaryScope HR Tools — Candidate Comparison",
        file_stem="candidate_comparison",
        csv_df=export_df,
        summary_lines=summary_lines,
        key_prefix="cc_export",
        csv_label=":material/download: Download CSV",
        xlsx_label=":material/table_view: Download XLSX",
        pdf_label=":material/picture_as_pdf: Download PDF",
        docx_label=":material/description: Download DOCX",
    )
