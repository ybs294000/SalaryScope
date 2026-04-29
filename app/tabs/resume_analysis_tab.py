import streamlit as st
from app.theme import (
    salary_card_html, salary_level_card_html, career_stage_card_html,
    resume_score_card_html, association_insight_card_html,
    apply_theme, get_colorway, get_token, get_gauge_colors,
)

import pandas as pd
import numpy as np

from app.core.resume_analysis import (
    extract_text_from_pdf,
    extract_resume_features,
    calculate_resume_score,
    extract_resume_features_a2,
    calculate_resume_score_a2,
    APP2_ALLOWED_ISO_CODES_A2,
)
from app.core.resume_screening import (
    calculate_resume_screening_app1,
    calculate_resume_screening_app2,
)
from app.tabs.offer_letter_tab import render_offer_letter_tab
from app.core.insights_engine import generate_insights_app2, generate_insights_app1
from app.utils.recommendations import (
    generate_recommendations_app1,
    generate_recommendations_app2,
    render_recommendations,
)
from app.utils.negotiation_tips import (
    generate_negotiation_tips_app1,
    generate_negotiation_tips_app2,
    render_negotiation_tips,
)
from app.utils.currency_utils import (
    render_currency_converter,
    get_active_currency,
    get_active_rates,
    currency_dropdown_options,
    parse_currency_option,
    guess_currency,
    get_exchange_rates,
)
from app.utils.tax_utils import render_tax_adjuster
from app.utils.col_utils import render_col_adjuster
from app.core.database import save_prediction

from app.utils.salary_card import render_salary_card_download
from app.utils.currency_report_exports import (
    build_resume_export_pdf,
    build_resume_export_docx,
)

try:
    from app.core.resume_lang import detect_resume_language, render_language_badge
    _LANG_DETECT_AVAILABLE = True
except ImportError:
    _LANG_DETECT_AVAILABLE = False
    def detect_resume_language(text): return {}
    def render_language_badge(result): pass


def render_resume_tab(
    IS_APP1,
    # App 1 resources
    app1_model,
    app1_salary_band_model,
    app1_cluster_model_a1,
    app1_cluster_metadata_a1,
    app1_job_titles,
    app1_countries,
    app1_genders,
    SALARY_BAND_LABELS,
    assoc_rules_a1_v2,
    get_assoc_insight_a1_improved,
    load_app1_analytics,
    app1_generate_resume_pdf,
    # App 2 resources
    app2_model,
    app2_job_titles,
    app2_experience_levels,
    app2_employment_types,
    app2_company_sizes,
    app2_remote_ratios,
    app2_country_display_options,
    app2_employee_residence_display_options,
    app2_generate_resume_pdf,
    df_app2,
    # Shared mappings
    EXPERIENCE_MAP,
    EMPLOYMENT_MAP,
    COMPANY_SIZE_MAP,
    REMOTE_MAP,
    COUNTRY_NAME_MAP,
    EXPERIENCE_REVERSE,
    EMPLOYMENT_REVERSE,
    COMPANY_SIZE_REVERSE,
    REMOTE_REVERSE,
    title_features,
):
    def _default_currency_option(options, preferred_code):
        preferred = (preferred_code or "USD").upper()
        return next((option for option in options if option.startswith(f"{preferred} — ")), options[0])

    def _screening_band_color(score: int) -> str:
        gauge = get_gauge_colors()
        if score >= 80:
            return gauge["safe"]
        if score >= 60:
            return gauge["warn"]
        return gauge["danger"]

    def _screening_ring_html(score: int, label: str, note: str) -> str:
        ring_color = _screening_band_color(score)
        track = get_token("border_subtle")
        text_main = get_token("text_primary")
        text_muted = get_token("text_secondary")
        clamped = max(0, min(100, int(score)))
        return (
            f"<div style='display:flex;justify-content:flex-start;width:100%;'>"
            f"<div style='display:flex;flex-direction:column;align-items:center;"
            f"background:linear-gradient(135deg,{get_token('util_card_start')} 0%,{get_token('util_card_end')} 100%);"
            f"border:1px solid {get_token('util_card_border')};border-radius:14px;padding:18px 18px 14px 18px;"
            f"width:min(100%, 280px);min-width:240px;'>"
            f"<div style='font-size:12px;color:{text_muted};font-weight:600;letter-spacing:0.4px;margin-bottom:10px;'>{label}</div>"
            f"<div style='width:138px;height:138px;border-radius:50%;"
            f"background:conic-gradient({ring_color} 0 {clamped}%, {track} {clamped}% 100%);"
            f"display:flex;align-items:center;justify-content:center;'>"
            f"<div style='width:102px;height:102px;border-radius:50%;background:{get_token('surface_raised')};"
            f"display:flex;flex-direction:column;align-items:center;justify-content:center;"
            f"border:1px solid {get_token('border_subtle')}'>"
            f"<div style='color:{ring_color};font-size:28px;font-weight:700;line-height:1;'>{clamped}%</div>"
            f"<div style='color:{text_muted};font-size:11px;margin-top:6px;'>Readiness</div>"
            f"</div></div>"
            f"<div style='color:{text_main};font-size:13px;font-weight:600;text-align:center;line-height:1.35;margin-top:12px;max-width:180px;'>{note}</div>"
            f"</div></div>"
        )

    def _screening_bar_html(label: str, score: int, note: str) -> str:
        color = _screening_band_color(score)
        track = get_token("border_subtle")
        text_main = get_token("text_primary")
        text_muted = get_token("text_secondary")
        clamped = max(0, min(100, int(score)))
        return (
            f"<div style='margin:10px 0 14px 0;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:6px;'>"
            f"<span style='color:{text_main};font-size:13px;font-weight:600;'>{label}</span>"
            f"<span style='color:{color};font-size:13px;font-weight:700;'>{clamped}/100</span>"
            f"</div>"
            f"<div style='background:{track};border-radius:999px;height:8px;width:100%;overflow:hidden;'>"
            f"<div style='background:{color};width:{clamped}%;height:8px;border-radius:999px;'></div>"
            f"</div>"
            f"<div style='color:{text_muted};font-size:12px;line-height:1.45;margin-top:6px;'>{note}</div>"
            f"</div>"
        )

    def _screening_summary_html(screening: dict) -> str:
        return (
            f"<div style='display:flex;gap:20px;align-items:center;flex-wrap:wrap;width:100%;'>"
            f"<div style='flex:0 1 280px;min-width:240px;'>"
            f"{_screening_ring_html(screening['overall_score'], 'Overall Screening Outlook', screening['overall_band'])}"
            f"</div>"
            f"<div style='flex:1 1 420px;min-width:320px;'>"
            f"{_screening_bar_html('ATS Readiness', screening['ats_readiness_score'], screening['score_notes']['ats_readiness'])}"
            f"{_screening_bar_html('Role Match', screening['role_match_score'], screening['score_notes']['role_match'])}"
            f"{_screening_bar_html('Parse Confidence', screening['parse_confidence_score'], screening['score_notes']['parse_confidence'])}"
            f"</div>"
            f"</div>"
        )

    def _render_resume_screening_block(screening: dict) -> None:
        st.divider()
        st.subheader(":material/fact_check: Resume Screening Readiness")
        st.write(screening["headline"])
        st.markdown(_screening_summary_html(screening), unsafe_allow_html=True)

        with st.expander("What these screening signals mean", expanded=False):
            st.write(screening["score_notes"]["ats_readiness"])
            st.write(screening["score_notes"]["role_match"])
            st.write(screening["score_notes"]["parse_confidence"])

        strengths_col, gaps_col = st.columns(2)
        with strengths_col:
            st.markdown("#### :material/thumb_up: Likely Strengths")
            for item in screening["strengths"]:
                st.write(f"- {item}")
        with gaps_col:
            st.markdown("#### :material/report_problem: Possible Screening Gaps")
            for item in screening["gaps"]:
                st.write(f"- {item}")

        st.markdown("#### :material/build: How to Improve This Resume for Screening")
        for item in screening["improvements"]:
            st.write(f"- {item}")

    def _app1_resume_extra_sections(result_payload):
        score_data = result_payload.get("resume_score_data", {})
        return [
            (
                "Profile Summary",
                pd.DataFrame(
                    [
                        (
                            "Summary",
                            f"This resume is classified as a {score_data.get('level', '')} profile with a total score of "
                            f"{score_data.get('total_score', 0)}/100. The predicted salary reflects the combined impact "
                            f"of experience, education, and detected skills."
                        )
                    ],
                    columns=["Type", "Details"],
                ),
            )
        ]

    def _app2_resume_extra_sections(result_payload):
        score_data = result_payload.get("resume_score_data_a2", {})
        return [
            (
                "Profile Summary",
                pd.DataFrame(
                    [
                        (
                            "Summary",
                            f"This resume is classified as a {score_data.get('level_a2', '')} profile with a total score of "
                            f"{score_data.get('total_score_a2', 0)}/100. The predicted salary reflects the combined impact "
                            f"of experience level, job role, and detected skills."
                        )
                    ],
                    columns=["Type", "Details"],
                ),
            )
        ]

    st.header(":material/description: Resume Analysis")
    st.caption(
        "Upload a resume PDF to automatically extract structured features using NLP. "
        "The extracted fields can be reviewed and edited before salary prediction."
    )

    # ROLLBACK: Offer Letter Parser integration
    # Remove this selector block and the import above to restore the original
    # single-flow Resume Analysis tab.
    document_mode = st.radio(
        "Choose a document type",
        options=["Resume PDF", "Offer Letter"],
        horizontal=True,
        key="resume_document_workflow_mode",
        help="Use Resume PDF for salary prediction from a resume, or Offer Letter to extract compensation details from an offer document.",
    )
    if document_mode == "Offer Letter":
        render_offer_letter_tab()
        return

    if not IS_APP1:
        # ----------------------------------------------------------------
        # APP 2 — Resume Analysis Tab (XGBoost DS Salary Model)
        # All variables/functions use _a2 suffix or app2_ prefix
        # ----------------------------------------------------------------
        # ==============================
        # FRAGMENT DEFINITIONS (APP 2)
        # ==============================

        @st.fragment
        def render_resume_editor_a2():
            feats_a2 = st.session_state.resume_features_a2

            with st.expander("View Extracted Resume Text"):
                st.text_area(
                    "Extracted Text",
                    st.session_state.resume_text_a2,
                    height=250,
                    key="resume_extracted_text_preview_a2"
                )

            st.subheader("Detected Features")
            st.caption("Review and edit the extracted fields before prediction.")

            col_ra1, col_ra2 = st.columns(2)

            # --- Experience Level ---
            exp_level_options_a2 = [
                x for x in ["EN", "MI", "SE", "EX"]
                if x in app2_experience_levels
            ]
            exp_level_display_a2 = [EXPERIENCE_MAP[x] for x in exp_level_options_a2]
            detected_exp_code_a2 = feats_a2.get("experience_level_a2", "MI")
            if detected_exp_code_a2 not in exp_level_options_a2:
                detected_exp_code_a2 = exp_level_options_a2[0]
            default_exp_idx_a2 = exp_level_options_a2.index(detected_exp_code_a2)

            with col_ra1:
                st.selectbox(
                    "Experience Level",
                    exp_level_display_a2,
                    index=default_exp_idx_a2,
                    key="resume_experience_level_a2"
                )
                st.selectbox(
                    "Employment Type",
                    [EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types],
                    index=[
                        EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"]
                        if x in app2_employment_types
                    ].index(
                        EMPLOYMENT_MAP.get(feats_a2.get("employment_type_a2", "FT"), "Full Time")
                    ) if EMPLOYMENT_MAP.get(feats_a2.get("employment_type_a2", "FT"), "Full Time") in [
                        EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types
                    ] else 0,
                    key="resume_employment_type_a2"
                )
                detected_job_a2 = feats_a2.get("job_title_a2", app2_job_titles[0])
                st.selectbox(
                    "Job Title",
                    app2_job_titles,
                    index=app2_job_titles.index(detected_job_a2)
                    if detected_job_a2 in app2_job_titles else 0,
                    key="resume_job_title_a2"
                )

                st.selectbox(
                    "Company Size",
                    [COMPANY_SIZE_MAP[x] for x in app2_company_sizes],
                    index=[COMPANY_SIZE_MAP[x] for x in app2_company_sizes].index(
                        COMPANY_SIZE_MAP.get(
                            feats_a2.get("company_size_a2", "M"), "Medium Company"
                        )
                    ) if COMPANY_SIZE_MAP.get(
                        feats_a2.get("company_size_a2", "M"), "Medium Company"
                    ) in [COMPANY_SIZE_MAP[x] for x in app2_company_sizes] else 0,
                    key="resume_company_size_a2"
                )
            # --- Employee Residence (country extracted from resume) ---
            detected_iso_a2 = feats_a2.get("employee_residence_a2", "US")

            # Build display label for detected country
            detected_res_name_a2 = COUNTRY_NAME_MAP.get(detected_iso_a2)
            if detected_res_name_a2:
                detected_res_display_a2 = f"{detected_res_name_a2} ({detected_iso_a2})"
            else:
                detected_res_display_a2 = detected_iso_a2

            if detected_res_display_a2 not in app2_employee_residence_display_options:
                detected_res_display_a2 = (
                    "United States (US)"
                    if "United States (US)" in app2_employee_residence_display_options
                    else app2_employee_residence_display_options[0]
                )

            with col_ra2:
                st.selectbox(
                    "Employee Residence",
                    app2_employee_residence_display_options,
                    index=app2_employee_residence_display_options.index(detected_res_display_a2),
                    key="resume_employee_residence_a2"
                )

                # Work mode
                remote_val_a2 = feats_a2.get("remote_ratio_a2", 0)
                remote_display_options_a2 = [
                    REMOTE_MAP[x] for x in [0, 50, 100] if x in app2_remote_ratios
                ]
                remote_detected_label_a2 = REMOTE_MAP.get(remote_val_a2, "On-site")
                if remote_detected_label_a2 not in remote_display_options_a2:
                    remote_detected_label_a2 = remote_display_options_a2[0]

                st.selectbox(
                    "Work Mode",
                    remote_display_options_a2,
                    index=remote_display_options_a2.index(remote_detected_label_a2),
                    key="resume_remote_ratio_a2"
                )

                # Company location — same as residence by default (can be edited)
                detected_loc_a2 = feats_a2.get("company_location_a2", "US")
                detected_loc_name_a2 = COUNTRY_NAME_MAP.get(detected_loc_a2)
                if detected_loc_name_a2:
                    detected_loc_display_a2 = f"{detected_loc_name_a2} ({detected_loc_a2})"
                else:
                    detected_loc_display_a2 = detected_loc_a2

                if detected_loc_display_a2 not in app2_country_display_options:
                    detected_loc_display_a2 = (
                        "United States (US)"
                        if "United States (US)" in app2_country_display_options
                        else app2_country_display_options[0]
                    )

                st.selectbox(
                    "Company Location",
                    app2_country_display_options,
                    index=app2_country_display_options.index(detected_loc_display_a2),
                    key="resume_company_location_a2"
                )


            st.caption(
                "Employee Residence and Company Location are auto-detected from the resume. "
                "They default to the same country — adjust if needed."
            )

        @st.fragment
        def render_resume_score_a2():
            score_a2 = st.session_state.resume_score_data_a2
            feats_a2 = st.session_state.resume_features_a2
            screening_a2 = calculate_resume_screening_app2(
                raw_text=st.session_state.resume_text_a2 or "",
                features=feats_a2,
                score_data=score_a2,
            )

            st.divider()
            st.subheader("Resume Score Breakdown")

            render_language_badge(st.session_state.get("resume_lang_a2", {}))

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Total Score", f"{score_a2['total_score_a2']}/100")
            col_s2.metric("Experience Score", score_a2["experience_score_a2"])
            col_s3.metric("Skills Score", score_a2["skills_score_a2"])
            col_s4.metric("Role Relevance", score_a2["title_score_a2"])

            st.caption(f"Profile Strength: {score_a2['level_a2']}")
            st.write(f"Experience: {score_a2['experience_note_a2']}")
            st.write(f"Skills: {score_a2['skills_note_a2']}")
            st.write(f"Role: {score_a2['title_note_a2']}")

            if score_a2["skills_detected_a2"]:
                st.markdown(
                    f"**DS/ML Skills Detected ({score_a2['ds_skill_count_a2']}):** "
                    f"{score_a2['skills_detected_str_a2']}"
                )
            else:
                st.markdown("**Detected Skills:** None")

            with st.expander("Detection Sources"):
                st.json(feats_a2["sources_a2"])

            _render_resume_screening_block(screening_a2)

        @st.fragment
        def render_resume_prediction_a2():
            st.divider()

            if st.button(
                "Predict Salary from Resume",
                type="primary",
                width="stretch",
                key="resume_predict_button_a2"
            ):
                # Read widget values from session state
                exp_level_label_a2 = st.session_state.resume_experience_level_a2
                experience_level_a2 = EXPERIENCE_REVERSE.get(exp_level_label_a2, "MI")

                emp_label_a2 = st.session_state.resume_employment_type_a2
                employment_type_a2 = EMPLOYMENT_REVERSE.get(emp_label_a2, "FT")

                job_title_a2 = st.session_state.resume_job_title_a2

                # Parse employee residence
                res_label_a2 = st.session_state.resume_employee_residence_a2
                if res_label_a2 == "Other":
                    employee_residence_a2 = "US"
                elif "(" in res_label_a2:
                    employee_residence_a2 = res_label_a2.split("(")[-1].replace(")", "").strip()
                else:
                    employee_residence_a2 = res_label_a2

                remote_label_a2 = st.session_state.resume_remote_ratio_a2
                remote_ratio_a2 = REMOTE_REVERSE.get(remote_label_a2, 0)

                # Parse company location
                loc_label_a2 = st.session_state.resume_company_location_a2
                if "(" in loc_label_a2:
                    company_location_a2 = loc_label_a2.split("(")[-1].replace(")", "").strip()
                else:
                    company_location_a2 = loc_label_a2

                company_size_label_a2 = st.session_state.resume_company_size_a2
                company_size_a2 = COMPANY_SIZE_REVERSE.get(company_size_label_a2, "M")

                score_a2 = st.session_state.resume_score_data_a2

                try:
                    junior_a2_r, senior_a2_r, exec_a2_r, is_mgmt_a2_r, domain_a2_r = title_features(job_title_a2)
                    exp_x_domain_a2_r = f"{experience_level_a2}_{domain_a2_r}"

                    input_df_a2_r = pd.DataFrame([{
                        "experience_level": experience_level_a2,
                        "employment_type": employment_type_a2,
                        "job_title": job_title_a2,
                        "employee_residence": employee_residence_a2,
                        "remote_ratio": int(remote_ratio_a2),
                        "company_location": company_location_a2,
                        "company_size": company_size_a2,
                        "title_is_junior": junior_a2_r,
                        "title_is_senior": senior_a2_r,
                        "title_is_exec": exec_a2_r,
                        "title_is_mgmt": is_mgmt_a2_r,
                        "title_domain": domain_a2_r,
                        "exp_x_domain": exp_x_domain_a2_r
                    }])

                    pred_log_a2_r = app2_model.predict(input_df_a2_r)[0]
                    prediction_a2_r = float(np.expm1(pred_log_a2_r))

                    # Build display labels
                    res_name_a2_r = COUNTRY_NAME_MAP.get(employee_residence_a2)
                    res_display_a2_r = (
                        f"{res_name_a2_r} ({employee_residence_a2})"
                        if res_name_a2_r else employee_residence_a2
                    )
                    loc_name_a2_r = COUNTRY_NAME_MAP.get(company_location_a2)
                    loc_display_a2_r = (
                        f"{loc_name_a2_r} ({company_location_a2})"
                        if loc_name_a2_r else company_location_a2
                    )

                    input_details_a2_r = {
                        "Experience Level": EXPERIENCE_MAP.get(experience_level_a2, experience_level_a2),
                        "Employment Type": EMPLOYMENT_MAP.get(employment_type_a2, employment_type_a2),
                        "Job Title": job_title_a2,
                        "Employee Residence": res_display_a2_r,
                        "Work Mode": REMOTE_MAP.get(remote_ratio_a2, str(remote_ratio_a2)),
                        "Company Location": loc_display_a2_r,
                        "Company Size": company_size_label_a2,
                        "Detected Skills": score_a2["skills_detected_str_a2"],
                        "Resume Score": score_a2["total_score_a2"]
                    }

                    if st.session_state.get("logged_in"):
                        save_prediction(
                            st.session_state.username,
                            "XGBoost Resume",
                            input_details_a2_r,
                            float(prediction_a2_r)
                        )

                    st.session_state.resume_prediction_result_a2 = {
                        "input_details_a2": input_details_a2_r,
                        "prediction_a2": prediction_a2_r,
                        "resume_score_data_a2": score_a2,
                        "company_location_code_a2": company_location_a2,
                        "experience_level_a2": experience_level_a2,
                        "job_title_a2": job_title_a2,
                    }
                    st.session_state.resume_pdf_buffer_a2 = None
                    st.session_state.resume_pdf_ready_a2 = False

                    st.rerun()

                except Exception as e_a2:
                    st.error("Prediction failed. Please check the input values.")
                    st.exception(e_a2)
                    st.session_state.resume_prediction_result_a2 = None

        @st.fragment
        def render_resume_results_a2():
            data_a2_r = st.session_state.resume_prediction_result_a2
            prediction_a2_r = data_a2_r["prediction_a2"]
            score_a2 = data_a2_r["resume_score_data_a2"]

            monthly_a2_r = prediction_a2_r / 12
            weekly_a2_r = prediction_a2_r / 52
            hourly_a2_r = prediction_a2_r / (52 * 40)

            st.divider()
            st.markdown(
                "<h3 style='text-align: center;'>Resume Profile Score</h3>",
                unsafe_allow_html=True
            )
            st.markdown(
resume_score_card_html(
                f"{score_a2['total_score_a2']}/100",
                level_str=f"{score_a2['level_a2']} Profile",
            ),
                unsafe_allow_html=True
            )

            st.markdown(
                "<h3 style='text-align: center;'>Estimated Annual Salary</h3>",
                unsafe_allow_html=True
            )
            st.markdown(
salary_card_html(f"${prediction_a2_r:,.2f}"),
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown(
                "<h3 style='text-align: center;'>Score Breakdown</h3>",
                unsafe_allow_html=True
            )
            c1a2, c2a2, c3a2 = st.columns(3)
            c1a2.metric("Experience", score_a2["experience_score_a2"])
            c2a2.metric("Skills", score_a2["skills_score_a2"])
            c3a2.metric("Role Relevance", score_a2["title_score_a2"])

            st.divider()
            st.markdown(
                "<h3 style='text-align: center;'>Breakdown (Approximate)</h3>",
                unsafe_allow_html=True
            )
            col_m_a2, col_w_a2, col_h_a2 = st.columns(3)
            col_m_a2.metric("Monthly (Approx)", f"${monthly_a2_r:,.2f}")
            col_w_a2.metric("Weekly (Approx)", f"${weekly_a2_r:,.2f}")
            col_h_a2.metric("Hourly (Approx, 40hr/week)", f"${hourly_a2_r:,.2f}")

            st.divider()
            #render_currency_converter(
            #    usd_amount=prediction_a2_r,
            #    location_hint=data_a2_r["company_location_code_a2"],
            #    widget_key="resume_a2",   
            #)
            render_currency_converter(usd_amount=prediction_a2_r, location_hint=data_a2_r["company_location_code_a2"], widget_key="resume_a2")
            active_currency_a2_r = get_active_currency("resume_a2")
            active_rates_a2_r    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction_a2_r, location_hint=data_a2_r["company_location_code_a2"], widget_key="resume_a2_tax",
                                converted_currency=active_currency_a2_r, rates=active_rates_a2_r)
            render_col_adjuster(gross_usd=prediction_a2_r, work_country=data_a2_r["company_location_code_a2"], widget_key="resume_a2_col")

            # --- Smart Insights & Negotiation Tips ---
            st.divider()
            insights_a2_r = generate_insights_app2(
                data_a2_r["input_details_a2"],
                prediction_a2_r,
                df_app2,
                title_features
            )

            recs_a2_r = generate_recommendations_app2(
                data_a2_r["input_details_a2"],
                prediction_a2_r,
                df_app2,
                title_features
            )
            st.markdown(
                "<h3 style='text-align: left;'>Salary Negotiation Tips</h3>",
                unsafe_allow_html=True
            )
            negotiation_tips_a2_r = generate_negotiation_tips_app2(
                prediction=prediction_a2_r,
                experience_label=data_a2_r["input_details_a2"]["Experience Level"],
                company_size_label=data_a2_r["input_details_a2"]["Company Size"],
                remote_label=data_a2_r["input_details_a2"]["Work Mode"],
                company_location=data_a2_r["company_location_code_a2"],
                job_title=data_a2_r["job_title_a2"],
                role=insights_a2_r["role"],
                market_type=insights_a2_r["market_type"]
            )
            render_negotiation_tips(negotiation_tips_a2_r)
            st.caption(
                "These tips help you approach salary discussions effectively "
                "based on your experience and role."
            )

            st.divider()
            st.subheader("Career Recommendations")
            render_recommendations(recs_a2_r)
            st.caption(
                "These recommendations focus on long-term career growth "
                "and skill development based on your profile."
            )
            # ---------------- PDF GENERATION ----------------
            st.divider()

            if st.button("Prepare PDF Report", width='stretch', key="resume_pdf_prepare_a2"):

                st.session_state.resume_pdf_buffer_a2 = app2_generate_resume_pdf(
                    st.session_state.resume_prediction_result_a2
                )

                st.session_state.resume_pdf_ready_a2 = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.resume_pdf_ready_a2:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.resume_pdf_ready_a2:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.resume_pdf_buffer_a2,
                    file_name="resume_salary_report_app2.pdf",
                    mime="application/pdf",
                    width='stretch',
                    key="resume_pdf_download_a2"
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True,
                    key="resume_pdf_disabled_a2"
                )

            st.divider()
            st.subheader("Additional Report Formats")
            st.caption(
                "Keep the current PDF above, or download the same summary as DOCX or in another currency."
            )
            resume_rate_data_a2 = get_exchange_rates()
            resume_currency_options_a2 = currency_dropdown_options()
            resume_default_option_a2 = _default_currency_option(
                resume_currency_options_a2,
                active_currency_a2_r or guess_currency(data_a2_r["company_location_code_a2"]),
            )
            resume_selected_option_a2 = st.selectbox(
                "Target currency for companion report",
                resume_currency_options_a2,
                index=resume_currency_options_a2.index(resume_default_option_a2),
                key="resume_a2_export_currency",
            )
            resume_target_currency_a2 = parse_currency_option(resume_selected_option_a2)
            st.caption(
                f"Selected currency: {resume_target_currency_a2}. Salary figures in these companion exports follow the chosen currency."
            )

            resume_docx_usd_a2 = build_resume_export_docx(
                data_a2_r,
                "USD",
                resume_rate_data_a2,
                "Resume Analysis",
                extra_sections=_app2_resume_extra_sections(data_a2_r),
            )
            resume_pdf_selected_a2 = build_resume_export_pdf(
                data_a2_r,
                resume_target_currency_a2,
                resume_rate_data_a2,
                "Resume Analysis",
                extra_sections=_app2_resume_extra_sections(data_a2_r),
            )
            resume_docx_selected_a2 = build_resume_export_docx(
                data_a2_r,
                resume_target_currency_a2,
                resume_rate_data_a2,
                "Resume Analysis",
                extra_sections=_app2_resume_extra_sections(data_a2_r),
            )

            resume_export_cols_a2 = st.columns(3)
            if resume_docx_usd_a2 is not None:
                with resume_export_cols_a2[0]:
                    st.download_button(
                        "Download Current Summary (DOCX)",
                        data=resume_docx_usd_a2,
                        file_name="resume_salary_report_app2.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="resume_a2_docx_usd_download",
                        width="stretch",
                    )
            with resume_export_cols_a2[1]:
                st.download_button(
                    "Download Selected Currency (PDF)",
                    data=resume_pdf_selected_a2,
                    file_name=f"resume_salary_report_app2_{resume_target_currency_a2.lower()}.pdf",
                    mime="application/pdf",
                    key="resume_a2_pdf_selected_download",
                    width="stretch",
                )
            with resume_export_cols_a2[2]:
                if resume_docx_selected_a2 is not None:
                    st.download_button(
                        "Download Selected Currency (DOCX)",
                        data=resume_docx_selected_a2,
                        file_name=f"resume_salary_report_app2_{resume_target_currency_a2.lower()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="resume_a2_docx_selected_download",
                        width="stretch",
                    )
                else:
                    st.button(
                        "Download Selected Currency (DOCX)",
                        disabled=True,
                        key="resume_a2_docx_selected_disabled",
                        width="stretch",
                    )
        # ==============================
        # FILE UPLOADER + RESET (APP 2)
        # ==============================

        uploaded_resume_a2 = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf"],
            key="resume_pdf_upload_a2"
        )

        if "last_resume_name_a2" not in st.session_state:
            st.session_state.last_resume_name_a2 = None

        current_resume_name_a2 = uploaded_resume_a2.name if uploaded_resume_a2 else None

        if current_resume_name_a2 != st.session_state.last_resume_name_a2:
            st.session_state.last_resume_name_a2 = current_resume_name_a2
            if uploaded_resume_a2 is None:
                st.session_state.resume_features_a2 = None
                st.session_state.resume_text_a2 = ""
                st.session_state.resume_score_data_a2 = None
                st.session_state.resume_prediction_result_a2 = None

                st.session_state.resume_pdf_ready_a2 = False
                st.session_state.resume_pdf_buffer_a2 = None
        for _key_a2 in [
            "resume_features_a2",
            "resume_text_a2",
            "resume_score_data_a2",
            "resume_prediction_result_a2"
        ]:
            if _key_a2 not in st.session_state:
                st.session_state[_key_a2] = None if _key_a2 != "resume_text_a2" else ""

        if "resume_pdf_ready_a2" not in st.session_state:
            st.session_state.resume_pdf_ready_a2 = False
        if "resume_pdf_buffer_a2" not in st.session_state:
            st.session_state.resume_pdf_buffer_a2 = None
        # ==============================
        # EXTRACTION BUTTON (APP 2)
        # ==============================

        if uploaded_resume_a2 is not None:
            if st.button(
                "Extract Resume Features",
                type="primary",
                width="stretch",
                key="resume_extract_button_a2"
            ):
                try:
                    with st.spinner("Extracting text and analysing resume..."):
                        raw_text_a2 = extract_text_from_pdf(uploaded_resume_a2)

                        if not raw_text_a2.strip():
                            st.error("Could not extract readable text from the PDF.")
                            st.stop()

                        st.session_state.resume_lang_a2 = detect_resume_language(raw_text_a2)

                        feats_a2 = extract_resume_features_a2(
                            raw_text=raw_text_a2,
                            allowed_job_titles_a2=app2_job_titles,
                            allowed_iso_codes_a2=list(APP2_ALLOWED_ISO_CODES_A2),
                        )
                        score_a2 = calculate_resume_score_a2(feats_a2)

                        st.session_state.resume_text_a2 = raw_text_a2
                        st.session_state.resume_features_a2 = feats_a2
                        st.session_state.resume_score_data_a2 = score_a2
                        st.session_state.resume_prediction_result_a2 = None

                    st.success("Resume processed successfully.")
                except Exception as e_extract_a2:
                    st.error("Failed to process the resume.")
                    st.exception(e_extract_a2)

        # ==============================
        # FRAGMENT CALL SITES (APP 2)
        # ==============================

        if st.session_state.resume_features_a2 is not None:
            render_resume_editor_a2()
            render_resume_score_a2()
            render_resume_prediction_a2()

        if st.session_state.resume_prediction_result_a2 is not None:
            render_resume_results_a2()    

    else:

        # ==============================
        # FRAGMENT DEFINITIONS
        # ==============================

        @st.fragment
        def render_resume_editor():
            features = st.session_state.resume_features

            with st.expander("View Extracted Resume Text"):
                st.text_area(
                    "Extracted Text",
                    st.session_state.resume_text,
                    height=250,
                    key="resume_extracted_text_preview"
                )

            st.subheader("Detected Features")
            st.caption("Review and edit the extracted fields before prediction.")

            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.slider("Age", 18, 70, 25, key="resume_age")
                st.selectbox(
                    "Education Level",
                    [0, 1, 2, 3],
                    index=[0, 1, 2, 3].index(int(features["education_level"])) if int(features["education_level"]) in [0, 1, 2, 3] else 1,
                    format_func=lambda x: {
                        0: "High School",
                        1: "Bachelor's Degree",
                        2: "Master's Degree",
                        3: "PhD"
                    }[x],
                    key="resume_education"
                )
                st.selectbox(
                    "Gender",
                    app1_genders,
                    key="resume_gender"
                )
                st.selectbox(
                    "Job Title",
                    app1_job_titles,
                    index=app1_job_titles.index(features["job_title"]) if features["job_title"] in app1_job_titles else 0,
                    key="resume_job_title"
                )

            with col_r2:
                st.slider(
                    "Years of Experience",
                    0.0, 40.0,
                    float(features["years_of_experience"]),
                    step=0.5,
                    key="resume_experience"
                )
                detected_senior_default = int(features["senior"])
                st.selectbox(
                    "Senior Position",
                    [0, 1],
                    index=[0, 1].index(detected_senior_default),
                    format_func=lambda x: "Yes" if x == 1 else "No",
                    key="resume_senior"
                )
                st.selectbox(
                    "Country",
                    app1_countries,
                    index=app1_countries.index(features["country"]) if features["country"] in app1_countries else 0,
                    key="resume_country"
                )

        @st.fragment
        def render_resume_score():
            score_data = st.session_state.resume_score_data
            features = st.session_state.resume_features
            screening = calculate_resume_screening_app1(
                raw_text=st.session_state.resume_text or "",
                features=features,
                score_data=score_data,
            )

            st.divider()
            st.subheader("Resume Score Breakdown")

            render_language_badge(st.session_state.get("resume_lang", {}))

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Total Score", f"{score_data['total_score']}/100")
            col_s2.metric("Experience Score", score_data["experience_score"])
            col_s3.metric("Education Score", score_data["education_score"])
            col_s4.metric("Skills Score", score_data["skills_score"])

            st.caption(f"Profile Strength: {score_data['level']}")
            st.write(f"Experience: {score_data['experience_note']}")
            st.write(f"Education: {score_data['education_note']}")
            st.write(f"Skills: {score_data['skills_note']}")

            if score_data["skills_detected"]:
                st.markdown("**Detected Skills:**")
                st.write(score_data["skills_detected_str"])
            else:
                st.markdown("**Detected Skills:** None")

            with st.expander("Detection Sources"):
                st.json(features["sources"])

            _render_resume_screening_block(screening)

        @st.fragment
        def render_resume_prediction():
            st.divider()

            if st.button("Predict Salary from Resume", type="primary", width='stretch', key="resume_predict_button"):

                resume_age = st.session_state.resume_age
                resume_experience = st.session_state.resume_experience
                resume_education = st.session_state.resume_education
                resume_senior = st.session_state.resume_senior
                resume_gender = st.session_state.resume_gender
                resume_job_title = st.session_state.resume_job_title
                resume_country = st.session_state.resume_country
                score_data = st.session_state.resume_score_data

                minimum_working_age = 18
                if resume_age - resume_experience < minimum_working_age:
                    st.error(
                        "Years of experience is not realistic for the selected age. "
                        "Please ensure experience aligns with a reasonable working age."
                    )
                    st.stop()

                input_df = pd.DataFrame([{
                    "Age": resume_age,
                    "Years of Experience": resume_experience,
                    "Education Level": resume_education,
                    "Senior": resume_senior,
                    "Gender": resume_gender,
                    "Job Title": resume_job_title,
                    "Country": resume_country
                }])

                prediction = app1_model.predict(input_df)[0]

                band_pred = app1_salary_band_model.predict(input_df)[0]
                salary_band_label = SALARY_BAND_LABELS.get(band_pred, "Unknown")

                edu_map_a1 = {
                    0: "High School",
                    1: "Bachelor",
                    2: "Master",
                    3: "PhD"
                }
                education_cat_a1 = edu_map_a1.get(resume_education, "Unknown")

                if resume_experience <= 2:
                    exp_cat_a1 = "Entry"
                elif resume_experience <= 5:
                    exp_cat_a1 = "Mid"
                else:
                    exp_cat_a1 = "Senior"

                def map_job_group_a1(title):
                    t = title.lower()
                    if any(x in t for x in ["engineer", "developer", "data", "scientist", "analyst", "architect", "it", "network"]):
                        return "Tech"
                    elif any(x in t for x in ["manager", "director", "vp", "chief", "ceo"]):
                        return "Management"
                    elif any(x in t for x in ["marketing", "sales", "brand", "advertising"]):
                        return "Marketing_Sales"
                    elif any(x in t for x in ["hr", "human resources", "recruit"]):
                        return "HR"
                    elif any(x in t for x in ["finance", "financial", "account"]):
                        return "Finance"
                    elif any(x in t for x in ["designer", "ux", "graphic", "creative"]):
                        return "Design"
                    else:
                        return "Operations"

                job_group_a1 = map_job_group_a1(resume_job_title)

                assoc_text_a1_improved = get_assoc_insight_a1_improved(
                    education_cat_a1,
                    exp_cat_a1,
                    resume_country,
                    job_group_a1,
                    band_pred,
                    assoc_rules_a1_v2,
                    years_experience=resume_experience
                )

                cluster_pred_a1 = app1_cluster_model_a1.predict(
                    pd.DataFrame([{
                        "Years of Experience": resume_experience,
                        "Education Level": resume_education
                    }])
                )[0]

                stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})
                career_stage_label = stage_map.get(int(cluster_pred_a1), "Unknown")

                a1 = load_app1_analytics()
                std_dev = a1["residual_std"]
                lower_bound = max(prediction - 1.96 * std_dev, 0)
                upper_bound = prediction + 1.96 * std_dev

                input_details = {
                    "Age": resume_age,
                    "Years of Experience": resume_experience,
                    "Education Level": {0: "High School", 1: "Bachelor's Degree", 2: "Master's Degree", 3: "PhD"}[resume_education],
                    "Senior Position": "Yes" if resume_senior == 1 else "No",
                    "Gender": resume_gender,
                    "Job Title": resume_job_title,
                    "Country": resume_country,
                    "Detected Skills": score_data["skills_detected_str"],
                    "Resume Score": score_data["total_score"]
                }

                if st.session_state.get("logged_in"):
                    save_prediction(
                        st.session_state.username,
                        "Random Forest Resume",
                        input_details,
                        float(prediction)
                    )

                st.session_state.resume_prediction_result = {
                    "input_details": input_details,
                    "prediction": prediction,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "salary_band_label": salary_band_label,
                    "career_stage_label": career_stage_label,
                    "assoc_text_a1_improved": assoc_text_a1_improved,
                    "resume_score_data": score_data
                }

                # SAME AS MANUAL TAB
                st.session_state.resume_pdf_buffer = None
                st.session_state.resume_pdf_ready = False

                st.rerun()

        @st.fragment
        def render_resume_results():
            data = st.session_state.resume_prediction_result
            prediction = data["prediction"]
            lower_bound = data["lower_bound"]
            upper_bound = data["upper_bound"]
            salary_band_label = data["salary_band_label"]
            career_stage_label = data["career_stage_label"]
            assoc_text_a1_improved = data["assoc_text_a1_improved"]
            score_data = data["resume_score_data"]

            monthly = prediction / 12
            weekly = prediction / 52
            hourly = prediction / (52 * 40)

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Resume Profile Score</h3>", unsafe_allow_html=True)
            st.markdown(
                resume_score_card_html(
                    f"{score_data['total_score']}/100",
                    level_str=f"{score_data['level']} Profile",
                ),
                unsafe_allow_html=True
            )

            st.markdown("<h3 style='text-align: center;'>Estimated Annual Salary</h3>", unsafe_allow_html=True)
            st.markdown(salary_card_html(f"${prediction:,.2f}"), unsafe_allow_html=True)

            st.markdown("<h3 style='text-align: center;'>Salary Context</h3>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("<h5 style='text-align: center;'>Salary Level</h5>", unsafe_allow_html=True)
                st.markdown(salary_level_card_html(salary_band_label), unsafe_allow_html=True)
            with col_b:
                st.markdown("<h5 style='text-align: center;'>Career Stage</h5>", unsafe_allow_html=True)
                st.markdown(career_stage_card_html(career_stage_label), unsafe_allow_html=True)
            st.caption(
                "Salary level represents your earning bracket, while career stage reflects your position "
                "based on experience and education."
            )

            st.divider()

            st.markdown("<h3 style='text-align: center;'>Pattern Insight (Data Association)</h3>", unsafe_allow_html=True)

            st.markdown(
association_insight_card_html(assoc_text_a1_improved),
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Score Breakdown</h3>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Experience", score_data["experience_score"])
            c2.metric("Education", score_data["education_score"])
            c3.metric("Skills", score_data["skills_score"])

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Breakdown (Approximate)</h3>", unsafe_allow_html=True)
            col_m, col_w, col_h = st.columns(3)
            col_m.metric("Monthly (Approx)", f"${monthly:,.2f}")
            col_w.metric("Weekly (Approx)", f"${weekly:,.2f}")
            col_h.metric("Hourly (Approx, 40hr/week)", f"${hourly:,.2f}")

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Likely Salary Range (95% Confidence Interval)</h3>", unsafe_allow_html=True)
            col_low, col_high = st.columns(2)
            col_low.metric("Lower Estimate", f"${lower_bound:,.2f}")
            col_high.metric("Upper Estimate", f"${upper_bound:,.2f}")

            st.caption("Range estimated using standard deviation of model residuals observed during training.")

         # 
          #  render_currency_converter(
          #      usd_amount=prediction,
          #      location_hint=data["input_details"]["Country"],  # or company_location_code_a2
          #      widget_key="resume_a1",   # or "resume_a2"
          #  )
            st.divider()
            render_currency_converter(usd_amount=prediction, location_hint=data["input_details"]["Country"], widget_key="resume_a1")
            active_currency_a1_r = get_active_currency("resume_a1")
            active_rates_a1_r    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction, location_hint=data["input_details"]["Country"], widget_key="resume_a1_tax",
                                converted_currency=active_currency_a1_r, rates=active_rates_a1_r)
            render_col_adjuster(gross_usd=prediction, work_country=data["input_details"]["Country"], widget_key="resume_a1_col")
            # -------------------------------------------------------
            # SALARY NEGOTIATION TIPS (APP 1 - RESUME)
            # -------------------------------------------------------
            st.divider()

            st.subheader(":material/handshake: Salary Negotiation Tips")

            negotiation_tips_a1_r = generate_negotiation_tips_app1(
                prediction=prediction,
                salary_band_label=salary_band_label,
                career_stage_label=career_stage_label,
                experience=data["input_details"]["Years of Experience"],
                job_title=data["input_details"]["Job Title"],
                country=data["input_details"]["Country"],
                senior=1 if data["input_details"]["Senior Position"] == "Yes" else 0,
                market_type="info"
            )

            render_negotiation_tips(negotiation_tips_a1_r)

            st.caption("These tips help you approach salary discussions effectively based on your experience and role.")

            st.divider()

            # -------------------------------------------------------
            # CAREER RECOMMENDATIONS (APP 1 - RESUME)
            # -------------------------------------------------------

            insights_a1_r = generate_insights_app1(data["input_details"])

            st.subheader(":material/tips_and_updates: Career Recommendations")

            recs_a1_r = generate_recommendations_app1(data["input_details"])
            render_recommendations(recs_a1_r)

            st.caption("These recommendations focus on long-term career growth and skill development based on your profile.")
            # ---------------- PDF GENERATION ----------------
            st.divider()

            if st.button("Prepare PDF Report", width='stretch', key="resume_pdf_prepare"):

                st.session_state.resume_pdf_buffer = app1_generate_resume_pdf(
                    st.session_state.resume_prediction_result
                )

                st.session_state.resume_pdf_ready = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.resume_pdf_ready:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.resume_pdf_ready:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.resume_pdf_buffer,
                    file_name="resume_salary_report.pdf",
                    mime="application/pdf",
                    width='stretch',
                    key="resume_pdf_download"
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True,
                    key="resume_pdf_disabled"
                )

            st.divider()
            st.subheader("Additional Report Formats")
            st.caption(
                "Keep the current PDF above, or download the same summary as DOCX or in another currency."
            )
            resume_rate_data = get_exchange_rates()
            resume_currency_options = currency_dropdown_options()
            resume_default_option = _default_currency_option(
                resume_currency_options,
                active_currency_a1_r or guess_currency(data["input_details"]["Country"]),
            )
            resume_selected_option = st.selectbox(
                "Target currency for companion report",
                resume_currency_options,
                index=resume_currency_options.index(resume_default_option),
                key="resume_a1_export_currency",
            )
            resume_target_currency = parse_currency_option(resume_selected_option)
            st.caption(
                f"Selected currency: {resume_target_currency}. Salary figures in these companion exports follow the chosen currency."
            )

            resume_docx_usd = build_resume_export_docx(
                data,
                "USD",
                resume_rate_data,
                "Resume Analysis",
                extra_sections=_app1_resume_extra_sections(data),
            )
            resume_pdf_selected = build_resume_export_pdf(
                data,
                resume_target_currency,
                resume_rate_data,
                "Resume Analysis",
                extra_sections=_app1_resume_extra_sections(data),
            )
            resume_docx_selected = build_resume_export_docx(
                data,
                resume_target_currency,
                resume_rate_data,
                "Resume Analysis",
                extra_sections=_app1_resume_extra_sections(data),
            )

            resume_export_cols = st.columns(3)
            if resume_docx_usd is not None:
                with resume_export_cols[0]:
                    st.download_button(
                        "Download Current Summary (DOCX)",
                        data=resume_docx_usd,
                        file_name="resume_salary_report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="resume_a1_docx_usd_download",
                        width="stretch",
                    )
            with resume_export_cols[1]:
                st.download_button(
                    "Download Selected Currency (PDF)",
                    data=resume_pdf_selected,
                    file_name=f"resume_salary_report_{resume_target_currency.lower()}.pdf",
                    mime="application/pdf",
                    key="resume_a1_pdf_selected_download",
                    width="stretch",
                )
            with resume_export_cols[2]:
                if resume_docx_selected is not None:
                    st.download_button(
                        "Download Selected Currency (DOCX)",
                        data=resume_docx_selected,
                        file_name=f"resume_salary_report_{resume_target_currency.lower()}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="resume_a1_docx_selected_download",
                        width="stretch",
                    )
                else:
                    st.button(
                        "Download Selected Currency (DOCX)",
                        disabled=True,
                        key="resume_a1_docx_selected_disabled",
                        width="stretch",
                    )
            # ------------- SALARY CARD DOWNLOAD (App 1 Resume) -------------
            render_salary_card_download(
                predicted_usd = data["prediction"],
                job_title     = data["input_details"]["Job Title"],
                location      = data["input_details"]["Country"],
                model_name    = "Model 1 — General Salary",
                band_label    = data["salary_band_label"],
                career_stage  = data["career_stage_label"],
                key           = "card_dl_resume_a1",
            )
        # ==============================
        # FILE UPLOADER + RESET LOGIC
        # ==============================

        uploaded_resume = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf"],
            key="resume_pdf_upload"
        )

        if "last_resume_name" not in st.session_state:
            st.session_state.last_resume_name = None

        current_resume_name = uploaded_resume.name if uploaded_resume else None

        if current_resume_name != st.session_state.last_resume_name:
            st.session_state.last_resume_name = current_resume_name

            st.session_state.resume_pdf_ready = False
            st.session_state.resume_pdf_buffer = None

            if uploaded_resume is None:
                st.session_state.resume_features = None
                st.session_state.resume_text = ""
                st.session_state.resume_score_data = None
                st.session_state.resume_prediction_result = None

        if "resume_features" not in st.session_state:
            st.session_state.resume_features = None
        if "resume_text" not in st.session_state:
            st.session_state.resume_text = ""
        if "resume_score_data" not in st.session_state:
            st.session_state.resume_score_data = None
        if "resume_prediction_result" not in st.session_state:
            st.session_state.resume_prediction_result = None

        if "resume_pdf_ready" not in st.session_state:
            st.session_state.resume_pdf_ready = False
        if "resume_pdf_buffer" not in st.session_state:
            st.session_state.resume_pdf_buffer = None
        # ==============================
        # EXTRACTION (no fragment — must trigger full rerun)
        # ==============================

        if uploaded_resume is not None:
            if st.button("Extract Resume Features", type="primary", width='stretch'):
                try:
                    with st.spinner("Extracting text and analyzing resume..."):
                        raw_text = extract_text_from_pdf(uploaded_resume)

                        if not raw_text.strip():
                            st.error("Could not extract readable text from the PDF.")
                            st.stop()

                        st.session_state.resume_lang = detect_resume_language(raw_text)

                        features = extract_resume_features(
                            raw_text=raw_text,
                            allowed_job_titles=app1_job_titles,
                            allowed_countries=app1_countries
                        )
                        score_data = calculate_resume_score(features)

                        st.session_state.resume_text = raw_text
                        st.session_state.resume_features = features
                        st.session_state.resume_score_data = score_data
                        st.session_state.resume_prediction_result = None

                    st.success("Resume processed successfully.")
                except Exception as e:
                    st.error("Failed to process the resume.")
                    st.exception(e)

        # ==============================
        # FRAGMENT CALL SITES
        # ==============================

        if st.session_state.resume_features is not None:
            render_resume_editor()
            render_resume_score()
            render_resume_prediction()

        if st.session_state.resume_prediction_result is not None:
            render_resume_results()
