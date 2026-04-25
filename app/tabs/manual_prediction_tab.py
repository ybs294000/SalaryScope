import streamlit as st
import pandas as pd
import numpy as np

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
from app.utils.currency_utils import render_currency_converter, get_active_currency, get_active_rates
from app.utils.tax_utils import render_tax_adjuster
from app.utils.col_utils import render_col_adjuster
from app.utils.ctc_utils import render_ctc_adjuster
from app.utils.takehome_utils import render_takehome_adjuster
from app.utils.savings_utils import render_savings_adjuster
from app.utils.loan_utils import render_loan_adjuster
from app.utils.budget_utils import render_budget_planner
from app.utils.investment_utils import render_investment_estimator
from app.utils.emergency_fund_utils import render_emergency_fund_planner
from app.utils.lifestyle_utils import render_lifestyle_split
from app.utils.fire_utils import render_fire_calculator
from app.utils.feedback import feedback_ui
from app.theme import (
    salary_card_html,
    salary_level_card_html,
    career_stage_card_html,
    association_insight_card_html,
    apply_theme,
    get_colorway,
    get_token,
)
from app.core.database import save_prediction
from app.utils.salary_card import render_salary_card_download


def render_manual_prediction_tab(
    IS_APP1,
    # App 1 resources
    app1_model,
    app1_metadata,
    app1_classifier_metadata,
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
    app1_generate_manual_pdf,
    # App 2 resources
    app2_model,
    app2_metadata,
    app2_job_titles,
    app2_experience_levels,
    app2_employment_types,
    app2_company_sizes,
    app2_remote_ratios,
    app2_country_display_options,
    app2_employee_residence_display_options,
    app2_generate_manual_pdf,
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
    # ------------------------------------------------------------------
    # APP 1 — Manual Prediction
    # ------------------------------------------------------------------
    if IS_APP1:
        col1, col2 = st.columns(2)

        with col1:
            #age = st.number_input("Age", 18, 70, 30)
            age = st.slider("Age", 18, 70, 30)

            edu_options = [0, 1, 2, 3]
            default_edu = 1  # Bachelor's
            education = st.selectbox(
                "Education Level",
                edu_options,
                index=edu_options.index(default_edu),
                format_func=lambda x: {
                    0: "High School",
                    1: "Bachelor's Degree",
                    2: "Master's Degree",
                    3: "PhD"
                }[x]
            )
            gender = st.selectbox("Gender", app1_genders)
            #job_title = st.selectbox("Job Title", app1_job_titles)
            default_job_a1 = "Software Engineer"
            job_title = st.selectbox(
                "Job Title",
                app1_job_titles,
                index=app1_job_titles.index(default_job_a1) if default_job_a1 in app1_job_titles else 0
            )
        with col2:
            #experience = st.number_input("Years of Experience", 0.0, 40.0, 5.0, 0.5)
            experience = st.slider("Years of Experience", 0.0, 40.0, 5.0, step=0.5)
            senior = st.selectbox(
                "Senior Position",
                [0, 1],
                format_func=lambda x: "Yes" if x == 1 else "No"
            )
            default_country_a1 = "USA"

            country = st.selectbox(
                "Country",
                app1_countries,
                index=app1_countries.index(default_country_a1) if default_country_a1 in app1_countries else 0
            )
        st.caption("If your country is not listed, select 'Other'.")
        st.divider()

        if st.button("Predict Salary", width='stretch', type="primary"):

            minimum_working_age = 18
            if age - experience < minimum_working_age:
                st.error(
                    "Years of experience is not realistic for the selected age. "
                    "Please ensure experience aligns with a reasonable working age."
                )
                st.stop()

            input_df = pd.DataFrame([{
                "Age": age,
                "Years of Experience": experience,
                "Education Level": education,
                "Senior": senior,
                "Gender": gender,
                "Job Title": job_title,
                "Country": country
            }])

            prediction = app1_model.predict(input_df)[0]

            band_pred = app1_salary_band_model.predict(input_df)[0]
            salary_band_label = SALARY_BAND_LABELS.get(band_pred, "Unknown")

            # ==============================
            # MAP INPUT → ASSOCIATION FORMAT (A1)
            # ==============================
            edu_map_a1 = {
                0: "High School",
                1: "Bachelor",
                2: "Master",
                3: "PhD"
            }
            education_cat_a1 = edu_map_a1.get(education, "Unknown")
            if experience <= 2:
                exp_cat_a1 = "Entry"
            elif experience <= 5:
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
            job_group_a1 = map_job_group_a1(job_title)

            assoc_text_a1_improved = get_assoc_insight_a1_improved(
                education_cat_a1,
                exp_cat_a1,
                country,
                job_group_a1,
                band_pred,
                assoc_rules_a1_v2,
                years_experience=experience   # <-- REQUIRED
            )

            # Predict cluster
            cluster_pred_a1 = app1_cluster_model_a1.predict(
                pd.DataFrame([{
                    "Years of Experience": experience,
                    "Education Level": education
                }])
            )[0]

            # Map to stage label
            stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})
            career_stage_label = stage_map.get(int(cluster_pred_a1), "Unknown")

            a1 = load_app1_analytics()
            std_dev = a1["residual_std"]
            lower_bound = max(prediction - 1.96 * std_dev, 0)
            upper_bound = prediction + 1.96 * std_dev

            input_details = {
                "Age": age,
                "Years of Experience": experience,
                "Education Level": {0: "High School", 1: "Bachelor's Degree",
                                    2: "Master's Degree", 3: "PhD"}[education],
                "Senior Position": "Yes" if senior == 1 else "No",
                "Gender": gender,
                "Job Title": job_title,
                "Country": country
            }
            # Save prediction AFTER input_details exists
            if st.session_state.get("logged_in"):
                save_prediction(
                    st.session_state.username,
                    "Random Forest",
                    input_details,
                    float(prediction)
                )
            st.session_state.manual_prediction_result = {
                "input_details": input_details,
                "prediction": prediction,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "salary_band_label": salary_band_label,
                "career_stage_label": career_stage_label,
                "assoc_text_a1_improved" : assoc_text_a1_improved

            }
            st.session_state.manual_pdf_buffer = None
            st.session_state.manual_pdf_ready = False

        if st.session_state.manual_prediction_result is not None:
            data = st.session_state.manual_prediction_result
            prediction = data["prediction"]
            lower_bound = data["lower_bound"]
            upper_bound = data["upper_bound"]
            salary_band_label = data["salary_band_label"]
            career_stage_label = data["career_stage_label"]
            assoc_text_a1_improved = data["assoc_text_a1_improved"]
            monthly = prediction / 12
            weekly = prediction / 52
            hourly = prediction / (52 * 40)

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

        
            #st.divider()
            #st.markdown("<h3 style='text-align: center;'>Estimated Salary Level</h3>", unsafe_allow_html=True)
            #st.markdown(salary_level_card_html(salary_band_label), unsafe_allow_html=True)
            # -------------------------------------------------------
            # CAREER STAGE (CLUSTER MODEL)
            # -------------------------------------------------------

            #st.divider()
            #st.markdown("<h3 style='text-align: center;'>Career Stage</h3>", unsafe_allow_html=True)

            # Display UI (same style as salary band)
            #st.markdown(career_stage_card_html(career_stage_label), unsafe_allow_html=True)

          #  st.caption(
          #      "Career stage is determined using an unsupervised clustering model based on "
          #      "experience and education. It represents your relative position in career progression."
          #  )


            # -------------------------------------------------------
            # ASSOCIATION INSIGHT (APP 1)
            # -------------------------------------------------------
            st.divider()

            st.markdown("<h3 style='text-align: center;'>Pattern Insight (Data Association)</h3>", unsafe_allow_html=True)

            st.markdown(association_insight_card_html(assoc_text_a1_improved), unsafe_allow_html=True)

            st.caption(
                "This insight is generated using association rule mining (Apriori algorithm), "
                "identifying patterns between education, experience, job role, and salary levels."
            )
            st.caption("Note: This insight reflects general dataset patterns and may not always align with individual predictions.")

            st.divider()
            st.subheader(":material/account_balance: Salary Insights & Financial Planning Tools")
            render_currency_converter(usd_amount=prediction, location_hint=country, widget_key="manual_a1")
            active_currency = get_active_currency("manual_a1")
            active_rates    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction, location_hint=country, widget_key="manual_a1_tax",
                                converted_currency=active_currency, rates=active_rates)
            render_col_adjuster(gross_usd=prediction, work_country=country, widget_key="manual_a1_col")
 
            render_ctc_adjuster(gross_usd=prediction, location_hint=country, widget_key="manual_a1_ctc")
            th = render_takehome_adjuster(gross_usd=prediction, location_hint=country,
                                           widget_key="manual_a1_th", net_usd=None)
            net_monthly = th.get("net_monthly", prediction / 12)
            sav_a1 = render_savings_adjuster(net_monthly_usd=net_monthly, location_hint=country,
                                     widget_key="manual_a1_sav", gross_usd=prediction)
            render_loan_adjuster(net_monthly_usd=net_monthly, location_hint=country,
                                 widget_key="manual_a1_loan", gross_usd=prediction)
            render_budget_planner(net_monthly_usd=net_monthly, location_hint=country,
                                  widget_key="manual_a1_budget", gross_usd=prediction)
            monthly_savings_a1 = sav_a1.get("savings", net_monthly * 0.20) if sav_a1 else net_monthly * 0.20
            render_investment_estimator(monthly_savings_usd=monthly_savings_a1, location_hint=country,
                                        widget_key="manual_a1_inv", net_monthly_usd=net_monthly)
            render_emergency_fund_planner(net_monthly_usd=net_monthly, location_hint=country,
                                          widget_key="manual_a1_ef", gross_usd=prediction)
            render_lifestyle_split(net_monthly_usd=net_monthly, location_hint=country,
                                   widget_key="manual_a1_lifestyle", gross_usd=prediction)

            render_fire_calculator(
                annual_salary_usd=prediction,
                location_hint=country,
                widget_key="manual_a1_fire",
                net_monthly_usd=net_monthly,
                savings_monthly_usd=monthly_savings_a1,
            )
            st.divider()
            st.subheader(":material/handshake: Salary Negotiation Tips")

            negotiation_tips_a1 = generate_negotiation_tips_app1(
                prediction=prediction,
                salary_band_label=salary_band_label,
                career_stage_label=career_stage_label,
                experience=data["input_details"]["Years of Experience"],
                job_title=data["input_details"]["Job Title"],
                country=data["input_details"]["Country"],
                senior=1 if data["input_details"]["Senior Position"] == "Yes" else 0,
                market_type="info"   # Model 1 has no market comparison, so default to info
            )

            render_negotiation_tips(negotiation_tips_a1)

            st.caption("These tips help you approach salary discussions effectively based on your experience and role.")

            st.divider()
            insights_a1 = generate_insights_app1(data["input_details"])
            recs_a1 = generate_recommendations_app1(data["input_details"])
            st.subheader(":material/tips_and_updates: Career Recommendations")
            render_recommendations(recs_a1)
            st.caption("These recommendations focus on long-term career growth and skill development based on your profile.")

            # ==============================================
            # FEEDBACK
            # ==============================================
            st.divider()
            feedback_ui(prediction, "Random Forest", data["input_details"])            
            # ---------------- PDF GENERATION ----------------
            st.divider()
            if st.button("Prepare PDF Report", width='stretch'):
                st.session_state.manual_pdf_buffer = app1_generate_manual_pdf(
                    data["input_details"], data["prediction"], data["lower_bound"], data["upper_bound"],
                    data["salary_band_label"], app1_metadata, app1_classifier_metadata, data["career_stage_label"], app1_cluster_metadata_a1
                )
                st.session_state.manual_pdf_ready = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.manual_pdf_ready:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.manual_pdf_ready:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.manual_pdf_buffer,
                    file_name="salary_prediction_report.pdf",
                    mime="application/pdf",
                    width='stretch'
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True
                )
            # ------------- SALARY CARD DOWNLOAD (App 1) -------------
            render_salary_card_download(
                predicted_usd = data["prediction"],
                job_title     = data["input_details"]["Job Title"],
                location      = data["input_details"]["Country"],
                model_name    = "Model 1 — General Salary",
                band_label    = data["salary_band_label"],
                career_stage  = data["career_stage_label"],
                key           = "card_dl_manual_a1",
            )                
    # ------------------------------------------------------------------
    # APP 2 — Manual Prediction
    # ------------------------------------------------------------------
    else:

        col1, col2 = st.columns(2)

        with col1:
            experience_label = st.selectbox(
                "Experience Level",
                [EXPERIENCE_MAP[x] for x in ["EN", "MI", "SE", "EX"] if x in app2_experience_levels]
            )
            experience_level = EXPERIENCE_REVERSE[experience_label]

            employment_label = st.selectbox(
                "Employment Type",
                [EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types]
            )
            employment_type = EMPLOYMENT_REVERSE[employment_label]

            default_job = "Data Scientist"

            job_title_a2 = st.selectbox(
                "Job Title",
                app2_job_titles,
                index=app2_job_titles.index(default_job) if default_job in app2_job_titles else 0
            )

            default_res = "United States (US)"

            employee_residence_label = st.selectbox(
                "Employee Residence",
                app2_employee_residence_display_options,
                index=app2_employee_residence_display_options.index(default_res)
                if default_res in app2_employee_residence_display_options else 0
            )
            if employee_residence_label == "Other":
                employee_residence = "Other"
            elif "(" in employee_residence_label:
                employee_residence = employee_residence_label.split("(")[-1].replace(")", "").strip()
            else:
                employee_residence = employee_residence_label

        with col2:
            remote_label = st.selectbox(
                "Work Mode",
                [REMOTE_MAP[x] for x in [0, 50, 100] if x in app2_remote_ratios]
            )
            remote_ratio = REMOTE_REVERSE[remote_label]

            default_loc = "United States (US)"

            company_location_label = st.selectbox(
                "Company Location",
                app2_country_display_options,
                index=app2_country_display_options.index(default_loc)
                if default_loc in app2_country_display_options else 0
            )
            if "(" in company_location_label:
                company_location = company_location_label.split("(")[-1].replace(")", "").strip()
            else:
                company_location = company_location_label

            company_size_label = st.selectbox(
                "Company Size",
                [COMPANY_SIZE_MAP[x] for x in app2_company_sizes]
            )
            company_size = COMPANY_SIZE_REVERSE[company_size_label]

        st.caption("Select employee residence from the list. If the country is not listed, choose 'Other'.")
        st.divider()

        if st.button("Predict Salary", width='stretch', type="primary"):

            try:
                junior_a2, senior_a2, exec_a2, is_mgmt_a2, domain_a2 = title_features(job_title_a2)
                exp_x_domain_a2 = f"{experience_level}_{domain_a2}"

                input_df_a2 = pd.DataFrame([{
                    "experience_level": experience_level,
                    "employment_type": employment_type,
                    "job_title": job_title_a2,
                    "employee_residence": employee_residence,
                    "remote_ratio": int(remote_ratio),
                    "company_location": company_location,
                    "company_size": company_size,
                    "title_is_junior": junior_a2,
                    "title_is_senior": senior_a2,
                    "title_is_exec": exec_a2,
                    "title_is_mgmt": is_mgmt_a2,
                    "title_domain": domain_a2,
                    "exp_x_domain": exp_x_domain_a2
                }])

                pred_log_a2 = app2_model.predict(input_df_a2)[0]
                prediction_a2 = float(np.expm1(pred_log_a2))

                #xgb_model_a2 = app2_model.named_steps["model"]
                #booster_a2 = xgb_model_a2.get_booster()
                #processed_input_a2 = app2_model.named_steps["preprocessor"].transform(input_df_a2)
                #import xgboost as xgb
                #dmatrix_a2 = xgb.DMatrix(processed_input_a2)
                #tree_predictions_log_a2 = []
                #for i in range(xgb_model_a2.n_estimators):
                #    tree_pred = booster_a2.predict(dmatrix_a2, iteration_range=(i, i + 1))[0]
                #    tree_predictions_log_a2.append(tree_pred)
                #tree_predictions_log_a2 = np.array(tree_predictions_log_a2)
                #tree_predictions_usd_a2 = np.expm1(tree_predictions_log_a2)
                #std_dev_a2 = float(np.std(tree_predictions_usd_a2))
                #lower_bound_a2 = max(prediction_a2 - 1.96 * std_dev_a2, 0.0)
                #upper_bound_a2 = prediction_a2 + 1.96 * std_dev_a2

                if employee_residence == "Other":
                    res_display = "Other"
                else:
                    res_name = COUNTRY_NAME_MAP.get(employee_residence)
                    res_display = f"{res_name} ({employee_residence})" if res_name else employee_residence
                
                loc_name = COUNTRY_NAME_MAP.get(company_location)
                loc_display = f"{loc_name} ({company_location})" if loc_name else company_location

                input_details_a2 = {
                    "Experience Level": experience_label,
                    "Employment Type": employment_label,
                    "Job Title": job_title_a2,
                    "Employee Residence": res_display,
                    "Work Mode": remote_label,
                    "Company Location": loc_display,
                    "Company Size": company_size_label
                }
                if st.session_state.get("logged_in"):
                    save_prediction(
                        st.session_state.username,
                        "XGBoost",
                        input_details_a2,
                        float(prediction_a2)
                    )

                st.session_state.manual_prediction_result = {
                    "input_details": input_details_a2,
                    "prediction": prediction_a2,
                  #  "lower_bound": lower_bound_a2,
                  #  "upper_bound": upper_bound_a2
                }
                st.session_state.manual_pdf_buffer = None
                st.session_state.manual_pdf_ready = False

            except Exception as e:
                st.error("Prediction failed. Please check input values.")
                st.exception(e)
                st.session_state.manual_prediction_result = None
                st.session_state.manual_pdf_buffer = None

        if st.session_state.manual_prediction_result is not None:
            data_a2 = st.session_state.manual_prediction_result
            prediction_a2 = data_a2["prediction"]
            #lower_bound_a2 = data_a2["lower_bound"]
            #upper_bound_a2 = data_a2["upper_bound"]
            monthly_a2 = prediction_a2 / 12
            weekly_a2 = prediction_a2 / 52
            hourly_a2 = prediction_a2 / (52 * 40)

            st.markdown("<h3 style='text-align: center;'>Estimated Annual Salary</h3>", unsafe_allow_html=True)
            st.markdown(salary_card_html(f"${prediction_a2:,.2f}"), unsafe_allow_html=True)

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Breakdown (Approximate)</h3>", unsafe_allow_html=True)
            col_m2, col_w2, col_h2 = st.columns(3)
            col_m2.metric("Monthly (Approx)", f"${monthly_a2:,.2f}")
            col_w2.metric("Weekly (Approx)", f"${weekly_a2:,.2f}")
            col_h2.metric("Hourly (Approx, 40hr/week)", f"${hourly_a2:,.2f}")
            #st.divider()
            #st.markdown("<h3 style='text-align: center;'>Likely Salary Range (95% Confidence Interval)</h3>", unsafe_allow_html=True)
            #col_low2, col_high2 = st.columns(2)
            #col_low2.metric("Lower Estimate", f"${lower_bound_a2:,.2f}")
            #col_high2.metric("Upper Estimate", f"${upper_bound_a2:,.2f}")
            #st.caption("Range estimated using variation across individual trees in the XGBoost model.")

            st.divider()
            st.subheader(":material/account_balance: Salary Insights & Financial Planning Tools")
            render_currency_converter(usd_amount=prediction_a2, location_hint=company_location, widget_key="manual_a2")
            active_currency_a2 = get_active_currency("manual_a2")
            active_rates_a2    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction_a2, location_hint=company_location, widget_key="manual_a2_tax",
                                converted_currency=active_currency_a2, rates=active_rates_a2)
            render_col_adjuster(gross_usd=prediction_a2, work_country=company_location, widget_key="manual_a2_col")
 
            render_ctc_adjuster(gross_usd=prediction_a2, location_hint=company_location, widget_key="manual_a2_ctc")
            th_a2 = render_takehome_adjuster(gross_usd=prediction_a2, location_hint=company_location,
                                           widget_key="manual_a2_th", net_usd=None)
            net_monthly_a2 = th_a2.get("net_monthly_a2", prediction_a2 / 12)
            sav_a2 = render_savings_adjuster(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                     widget_key="manual_a2_sav", gross_usd=prediction_a2)

            render_loan_adjuster(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                 widget_key="manual_a2_loan", gross_usd=prediction_a2)
            render_budget_planner(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                  widget_key="manual_a2_budget", gross_usd=prediction_a2)
            monthly_savings_a2 = sav_a2.get("savings", net_monthly_a2 * 0.20) if sav_a2 else net_monthly_a2 * 0.20
            render_investment_estimator(monthly_savings_usd=monthly_savings_a2, location_hint=company_location,
                                        widget_key="manual_a2_inv", net_monthly_usd=net_monthly_a2)
            render_emergency_fund_planner(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                          widget_key="manual_a2_ef", gross_usd=prediction_a2)
            render_lifestyle_split(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                   widget_key="manual_a2_lifestyle", gross_usd=prediction_a2)
            render_fire_calculator(
                annual_salary_usd=prediction_a2,
                location_hint=company_location,
                widget_key="manual_a2_fire",
                net_monthly_usd=net_monthly_a2,
                savings_monthly_usd=monthly_savings_a2,
            )
           # render_currency_converter(
           #     usd_amount=prediction_a2,       # or prediction_a2 for App 2
           #     location_hint=company_location,       # or company_location for App 2
           #     widget_key="manual_a2",      # use "manual_a2", "resume_a1", "resume_a2" per call-site
           # )

            # =====================================================
            # SMART INSIGHTS (APP 2)
            # =====================================================

            insights_a2 = generate_insights_app2(
                data_a2["input_details"],
                prediction_a2,
                df_app2,
                title_features
            )

            recs_a2 = generate_recommendations_app2(
                data_a2["input_details"],
                prediction_a2,
                df_app2,
                title_features
            )

            #st.divider()
            #st.subheader("Smart Insights")

            # Market message
            #if insights["market_type"] == "success":
            #    st.success(insights["market_msg"])
            #elif insights["market_type"] == "warning":
            #    st.warning(insights["market_msg"])
            #else:
            #    st.info(insights["market_msg"])

            # Role
            #st.caption(f"Domain Focus: {insights['role']}")
            st.divider()

            st.subheader(":material/handshake: Salary Negotiation Tips")

            negotiation_tips_a2 = generate_negotiation_tips_app2(
                prediction=prediction_a2,
                experience_label=data_a2["input_details"]["Experience Level"],
                company_size_label=data_a2["input_details"]["Company Size"],
                remote_label=data_a2["input_details"]["Work Mode"],
                company_location=company_location,   # ISO code already available in scope
                job_title=data_a2["input_details"]["Job Title"],
                role=insights_a2["role"],               # already computed from insights_engine
                market_type=insights_a2["market_type"]  # already computed from insights_engine
            )

            render_negotiation_tips(negotiation_tips_a2)
            st.caption("These tips help you approach salary discussions effectively based on your experience and role.")

            # Recommendations
            st.divider()
            st.subheader(":material/lightbulb: Career Recommendations")
            render_recommendations(recs_a2)
            st.caption("These recommendations focus on long-term career growth and skill development based on your profile.")

            # ==============================================
            # FEEDBACK
            # ==============================================
            st.divider()
            feedback_ui(prediction_a2, "XGBoost", data_a2["input_details"])

            # ---------------- PDF GENERATION ----------------
            st.divider()
            if st.button("Prepare PDF Report", width='stretch'):
                st.session_state.manual_pdf_buffer = app2_generate_manual_pdf(
                    data_a2["input_details"], data_a2["prediction"],
                    None, None, app2_metadata
                )
                st.session_state.manual_pdf_ready = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.manual_pdf_ready:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.manual_pdf_ready:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.manual_pdf_buffer,
                    file_name="salary_prediction_report.pdf",
                    mime="application/pdf",
                    width='stretch'
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True
                )