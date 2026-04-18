from app.theme import get_colorway, get_continuous_scale, get_colorway_3_stages, get_token
"""
scenario_analysis_tab.py
------------------------
Renders the Scenario Analysis tab for both App 1 and App 2.

All external dependencies are injected via render_scenario_tab() so that:
  - No resources are loaded or cached here (zero double-loading)
  - No imports from app_resume.py (zero circular dependencies)
  - The inner logic is byte-for-byte identical to the original tab code

Usage in app_resume.py:
    from scenario_analysis_tab import render_scenario_tab

    with tab_objects[3]:
        render_scenario_tab(
            is_app1=IS_APP1,
            app1_model=app1_model if IS_APP1 else None,
            app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
            app1_cluster_model=app1_cluster_model_a1 if IS_APP1 else None,
            app1_cluster_metadata=app1_cluster_metadata_a1 if IS_APP1 else None,
            app1_analytics_loader=load_app1_analytics,
            app1_genders=app1_genders,
            app1_job_titles=app1_job_titles,
            app1_countries=app1_countries,
            app2_model=app2_model if not IS_APP1 else None,
            app2_job_titles=app2_job_titles,
            app2_experience_levels=app2_experience_levels,
            app2_employment_types=app2_employment_types,
            app2_company_sizes=app2_company_sizes,
            app2_remote_ratios=app2_remote_ratios,
            app2_country_display_options=app2_country_display_options,
            app2_employee_residence_display_options=app2_employee_residence_display_options,
            SALARY_BAND_LABELS=SALARY_BAND_LABELS,
            EXPERIENCE_MAP=EXPERIENCE_MAP,
            EMPLOYMENT_MAP=EMPLOYMENT_MAP,
            COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
            REMOTE_MAP=REMOTE_MAP,
            EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
            EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
            COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
            REMOTE_REVERSE=REMOTE_REVERSE,
            COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
            apply_theme=_apply_theme,
            colorway=_COLORWAY,
            title_features=title_features,
            app1_generate_scenario_pdf=app1_generate_scenario_pdf,
            app2_generate_scenario_pdf=app2_generate_scenario_pdf,
        )
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO


def render_scenario_tab(
    is_app1,
    # App 1 models and metadata
    app1_model,
    app1_salary_band_model,
    app1_cluster_model,
    app1_cluster_metadata,
    app1_analytics_loader,
    app1_genders,
    app1_job_titles,
    app1_countries,
    # App 2 model and dropdown data
    app2_model,
    app2_job_titles,
    app2_experience_levels,
    app2_employment_types,
    app2_company_sizes,
    app2_remote_ratios,
    app2_country_display_options,
    app2_employee_residence_display_options,
    # Lookup maps
    SALARY_BAND_LABELS,
    EXPERIENCE_MAP,
    EMPLOYMENT_MAP,
    COMPANY_SIZE_MAP,
    REMOTE_MAP,
    EXPERIENCE_REVERSE,
    EMPLOYMENT_REVERSE,
    COMPANY_SIZE_REVERSE,
    REMOTE_REVERSE,
    COUNTRY_NAME_MAP,
    # Shared helpers
    apply_theme,
    colorway,
    title_features,
    # PDF generators
    app1_generate_scenario_pdf,
    app2_generate_scenario_pdf,
):
    st.header(":material/analytics: Scenario Analysis & What-If Simulation")
    st.caption(
        "Build and compare multiple salary prediction scenarios side by side. "
        "Adjust parameters, run all scenarios at once, and explore how changes "
        "in experience, education, role, or location affect estimated salary."
    )

    # ------------------------------------------------------------------
    # APP 1 -- Scenario Analysis
    # ------------------------------------------------------------------
    if is_app1:

        st.subheader("Configure Scenarios")
        st.caption("Add up to 5 scenarios. Each scenario runs through both the salary regressor and salary level classifier.")

        if "scenarios_a1" not in st.session_state:
            st.session_state.scenarios_a1 = [
                {
                    "label": "Scenario 1",
                    "age": 28,
                    "experience": 3.0,
                    "education": 1,
                    "senior": 0,
                    "gender": app1_genders[0],
                    "job_title": "Software Engineer" if "Software Engineer" in app1_job_titles else app1_job_titles[0],
                    "country": "USA" if "USA" in app1_countries else app1_countries[0]
                }
            ]

        if st.button("Add Scenario", key="add_scenario_a1") and len(st.session_state.scenarios_a1) < 5:
            idx = len(st.session_state.scenarios_a1) + 1
            st.session_state.scenarios_a1.append({
                "label": f"Scenario {idx}",
                "age": 30,
                "experience": 5.0,
                "education": 1,
                "senior": 0,
                "gender": app1_genders[0],
                "job_title": "Software Engineer" if "Software Engineer" in app1_job_titles else app1_job_titles[0],
                "country": "USA" if "USA" in app1_countries else app1_countries[0]
            })

        to_delete = None

        for i, sc in enumerate(st.session_state.scenarios_a1):
            with st.container(border=True):
                col_lbl, col_del = st.columns([6, 1])
                with col_lbl:
                    sc["label"] = st.text_input(
                        "Scenario Name",
                        value=sc["label"],
                        key=f"sc_a1_label_{i}"
                    )
                with col_del:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    if len(st.session_state.scenarios_a1) > 1:
                        if st.button("Remove", key=f"sc_a1_del_{i}"):
                            to_delete = i

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    sc["age"] = st.slider(
                        "Age", 18, 70, sc["age"],
                        key=f"sc_a1_age_{i}"
                    )

                    sc["gender"] = st.selectbox(
                        "Gender", app1_genders,
                        index=app1_genders.index(sc["gender"]) if sc["gender"] in app1_genders else 0,
                        key=f"sc_a1_gender_{i}"
                    )

                with col_b:
                    sc["experience"] = st.slider(
                        "Years of Experience", 0.0, 40.0,
                        sc["experience"], step=0.5,
                        key=f"sc_a1_exp_{i}"
                    )
                    sc["senior"] = st.selectbox(
                        "Senior Position",
                        [0, 1],
                        index=sc["senior"],
                        format_func=lambda x: "Yes" if x == 1 else "No",
                        key=f"sc_a1_senior_{i}"
                    )
                with col_c:
                    sc["education"] = st.selectbox(
                        "Education Level",
                        [0, 1, 2, 3],
                        index=sc["education"],
                        format_func=lambda x: {
                            0: "High School",
                            1: "Bachelor's",
                            2: "Master's",
                            3: "PhD"
                        }[x],
                        key=f"sc_a1_edu_{i}"
                    )

                    sc["job_title"] = st.selectbox(
                        "Job Title", app1_job_titles,
                        index=app1_job_titles.index(sc["job_title"]) if sc["job_title"] in app1_job_titles else 0,
                        key=f"sc_a1_job_{i}"
                    )
                    sc["country"] = st.selectbox(
                        "Country", app1_countries,
                        index=app1_countries.index(sc["country"]) if sc["country"] in app1_countries else 0,
                        key=f"sc_a1_country_{i}"
                    )

        if to_delete is not None:
            st.session_state.scenarios_a1.pop(to_delete)
            st.rerun()

        st.divider()

        if st.button("Run All Scenarios", type="primary", width="stretch", key="run_scenarios_a1"):

            results_a1 = []
            errors_a1 = []

            for i, sc in enumerate(st.session_state.scenarios_a1):
                min_age = 18
                if sc["age"] - sc["experience"] < min_age:
                    errors_a1.append(
                        f"**{sc['label']}**: Years of experience is not realistic for the selected age."
                    )
                    continue

                input_df = pd.DataFrame([{
                    "Age": sc["age"],
                    "Years of Experience": sc["experience"],
                    "Education Level": sc["education"],
                    "Senior": sc["senior"],
                    "Gender": sc["gender"],
                    "Job Title": sc["job_title"],
                    "Country": sc["country"]
                }])

                pred = float(app1_model.predict(input_df)[0])
                band = app1_salary_band_model.predict(input_df)[0]
                band_label = SALARY_BAND_LABELS.get(band, "Unknown")

                cluster_pred = app1_cluster_model.predict(
                    pd.DataFrame([{
                        "Years of Experience": sc["experience"],
                        "Education Level": sc["education"]
                    }])
                )[0]
                stage_map = app1_cluster_metadata.get("cluster_stage_mapping", {})
                career_stage = stage_map.get(int(cluster_pred), "Unknown")

                a1_anal = app1_analytics_loader()
                std_dev = a1_anal["residual_std"]
                lower = max(pred - 1.96 * std_dev, 0)
                upper = pred + 1.96 * std_dev

                results_a1.append({
                    "Scenario": sc["label"],
                    "Job Title": sc["job_title"],
                    "Experience (yrs)": sc["experience"],
                    "Education": {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}[sc["education"]],
                    "Country": sc["country"],
                    "Senior": "Yes" if sc["senior"] == 1 else "No",
                    "Predicted Salary (USD)": round(pred, 2),
                    "Lower Bound": round(lower, 2),
                    "Upper Bound": round(upper, 2),
                    "Salary Level": band_label,
                    "Career Stage": career_stage,
                })

            for err in errors_a1:
                st.error(err)

            st.session_state.scenario_results_a1 = results_a1
            st.session_state.scenario_pdf_ready = False
            st.session_state.scenario_pdf_buffer = None

        # ------ RESULTS ------
        if "scenario_results_a1" in st.session_state and st.session_state.scenario_results_a1:

            @st.fragment
            def render_scenario_results_a1():
                results_a1 = st.session_state.scenario_results_a1
                res_df_a1 = pd.DataFrame(results_a1)

                st.caption("Results are based on model predictions learned from historical data and may reflect dataset-specific patterns.")

                st.divider()
                st.subheader("Comparison Table")
                st.dataframe(res_df_a1, width='stretch', hide_index=True)

                best_row = res_df_a1.loc[res_df_a1["Predicted Salary (USD)"].idxmax()]
                st.success(f"Highest predicted salary: {best_row['Scenario']} -- ${best_row['Predicted Salary (USD)']:,.0f}")

                st.divider()
                st.subheader("Predicted Salary Comparison")

                fig_sc_bar_a1 = px.bar(
                    res_df_a1,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Scenario",
                    title="Predicted Annual Salary by Scenario",
                    color_discrete_sequence=colorway,
                    text="Predicted Salary (USD)"
                )
                fig_sc_bar_a1.update_traces(
                    texttemplate="$%{text:,.0f}",
                    textposition="outside"
                )
                apply_theme(fig_sc_bar_a1)
                st.plotly_chart(fig_sc_bar_a1, width='stretch')
                st.caption("This chart compares predicted salaries across different user-defined scenarios.")

                st.divider()
                st.subheader("Salary Range (95% Confidence Interval)")

                fig_ci_a1 = go.Figure()
                for _, row in res_df_a1.iterrows():
                    fig_ci_a1.add_trace(go.Bar(
                        name=row["Scenario"],
                        x=[row["Scenario"]],
                        y=[row["Upper Bound"] - row["Lower Bound"]],
                        base=[row["Lower Bound"]],
                        text=f"${row['Predicted Salary (USD)']:,.0f}",
                        textposition="outside",
                    ))
                fig_ci_a1.add_trace(go.Scatter(
                    x=res_df_a1["Scenario"],
                    y=res_df_a1["Predicted Salary (USD)"],
                    mode="markers",
                    marker=dict(color=get_token("ci_marker", "#fef6e4"), size=10),
                    name="Point Estimate"
                ))
                apply_theme(fig_ci_a1, {
                    "title": "Salary Confidence Intervals per Scenario",
                    "barmode": "overlay",
                    "yaxis_title": "Salary (USD)"
                })
                st.plotly_chart(fig_ci_a1, width='stretch')

                st.divider()
                st.subheader("Salary Level Distribution Across Scenarios")

                _cw3s = get_colorway_3_stages()
                fig_band_sc_a1 = px.bar(
                    res_df_a1,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Salary Level",
                    title="Scenarios Colored by Salary Level",
                    color_discrete_map={
                        "Early Career Range": _cw3s[0],
                        "Professional Range": _cw3s[1],
                        "Executive Range": _cw3s[2]
                    }
                )
                apply_theme(fig_band_sc_a1)
                st.plotly_chart(fig_band_sc_a1, width='stretch')

                st.divider()
                st.subheader("Career Stage Across Scenarios")

                fig_stage_sc_a1 = px.bar(
                    res_df_a1,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Career Stage",
                    title="Scenarios Colored by Career Stage",
                    color_discrete_map={
                        "Entry Stage": get_colorway()[1], "Growth Stage": get_colorway()[0], "Leadership Stage": get_colorway()[3]
                    }
                )
                apply_theme(fig_stage_sc_a1)
                st.plotly_chart(fig_stage_sc_a1, width='stretch')

                st.divider()
                st.subheader("Experience vs Predicted Salary")

                fig_exp_sc_a1 = px.scatter(
                    res_df_a1,
                    x="Experience (yrs)",
                    y="Predicted Salary (USD)",
                    color="Scenario",
                    size="Predicted Salary (USD)",
                    hover_data=["Job Title", "Education", "Country", "Salary Level", "Career Stage"],
                    title="Experience vs Predicted Salary (Bubble = Salary Magnitude)",
                    color_discrete_sequence=colorway,
                    text="Scenario"
                )
                fig_exp_sc_a1.update_traces(textposition="top center")
                apply_theme(fig_exp_sc_a1)
                st.plotly_chart(fig_exp_sc_a1, width='stretch')

                st.divider()
                st.subheader("Salary Sensitivity -- Experience Sweep")
                st.caption(
                    "Pick one scenario as a baseline and see how predicted salary changes "
                    "as Years of Experience increases from 0 to 40, holding all other inputs fixed."
                )

                sweep_scenario_a1 = st.selectbox(
                    "Select Baseline Scenario for Sweep",
                    options=[sc["label"] for sc in st.session_state.scenarios_a1],
                    key="sweep_scenario_select_a1"
                )

                base_sc_a1 = next(
                    (s for s in st.session_state.scenarios_a1 if s["label"] == sweep_scenario_a1),
                    st.session_state.scenarios_a1[0]
                )

                sweep_exp_vals = [x * 0.5 for x in range(0, 81)]
                sweep_rows = []
                for exp_val in sweep_exp_vals:
                    sweep_df = pd.DataFrame([{
                        "Age": max(base_sc_a1["age"], int(18 + exp_val)),
                        "Years of Experience": exp_val,
                        "Education Level": base_sc_a1["education"],
                        "Senior": base_sc_a1["senior"],
                        "Gender": base_sc_a1["gender"],
                        "Job Title": base_sc_a1["job_title"],
                        "Country": base_sc_a1["country"]
                    }])
                    sweep_pred = float(app1_model.predict(sweep_df)[0])
                    sweep_rows.append({"Years of Experience": exp_val, "Predicted Salary (USD)": sweep_pred})

                sweep_df_plot = pd.DataFrame(sweep_rows)

                fig_sweep_a1 = px.line(
                    sweep_df_plot,
                    x="Years of Experience",
                    y="Predicted Salary (USD)",
                    title=f"Salary Sensitivity: Experience Sweep -- {sweep_scenario_a1}",
                    color_discrete_sequence=[get_colorway()[0]]
                )
                fig_sweep_a1.update_traces(line=dict(width=2.5))
                apply_theme(fig_sweep_a1)
                st.plotly_chart(fig_sweep_a1, width='stretch')
                st.caption("This chart shows how predicted salary changes as years of experience increase while all other factors remain constant.")

                st.divider()
                st.subheader("Salary Sensitivity -- Education Sweep")
                st.caption(
                    "See how predicted salary changes across each education level "
                    "for the selected baseline scenario."
                )

                edu_labels = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
                edu_sweep_rows = []
                for edu_val in [0, 1, 2, 3]:
                    edu_sweep_df = pd.DataFrame([{
                        "Age": base_sc_a1["age"],
                        "Years of Experience": base_sc_a1["experience"],
                        "Education Level": edu_val,
                        "Senior": base_sc_a1["senior"],
                        "Gender": base_sc_a1["gender"],
                        "Job Title": base_sc_a1["job_title"],
                        "Country": base_sc_a1["country"]
                    }])
                    edu_pred = float(app1_model.predict(edu_sweep_df)[0])
                    edu_sweep_rows.append({
                        "Education": edu_labels[edu_val],
                        "Predicted Salary (USD)": edu_pred
                    })

                edu_sweep_df_plot = pd.DataFrame(edu_sweep_rows)

                fig_edu_sweep_a1 = px.bar(
                    edu_sweep_df_plot,
                    x="Education",
                    y="Predicted Salary (USD)",
                    title=f"Salary by Education Level -- {sweep_scenario_a1}",
                    color="Education",
                    color_discrete_sequence=get_colorway()[:4],
                    text="Predicted Salary (USD)"
                )
                fig_edu_sweep_a1.update_traces(
                    texttemplate="$%{text:,.0f}",
                    textposition="outside"
                )
                fig_edu_sweep_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                apply_theme(fig_edu_sweep_a1)
                st.plotly_chart(fig_edu_sweep_a1, width='stretch')
                st.caption("This chart compares predicted salary across different education levels for the same baseline profile.")

                st.divider()
                st.subheader("Export Scenario Results")
                export_format_sc_a1 = st.selectbox(
                    "Select export format",
                    ["CSV", "XLSX", "JSON"],
                    key="sc_export_format_a1"
                )
                if export_format_sc_a1 == "CSV":
                    sc_file_data = res_df_a1.to_csv(index=False).encode("utf-8")
                    sc_file_name = "scenario_results.csv"
                    sc_mime = "text/csv"
                elif export_format_sc_a1 == "XLSX":
                    sc_buf = BytesIO()
                    res_df_a1.to_excel(sc_buf, index=False)
                    sc_file_data = sc_buf.getvalue()
                    sc_file_name = "scenario_results.xlsx"
                    sc_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    sc_file_data = res_df_a1.to_json(orient="records")
                    sc_file_name = "scenario_results.json"
                    sc_mime = "application/json"

                st.download_button(
                    "Download Scenario Results",
                    data=sc_file_data,
                    file_name=sc_file_name,
                    mime=sc_mime,
                    width="stretch"
                )
                # ---------------- PDF GENERATION (SCENARIO APP 1) ----------------
                st.divider()

                if st.button("Prepare PDF Report", width='stretch', key="scenario_pdf_prepare"):

                    st.session_state.scenario_pdf_buffer = app1_generate_scenario_pdf(
                        pd.DataFrame(st.session_state.scenario_results_a1)
                    )

                    st.session_state.scenario_pdf_ready = True
                    st.success("PDF is ready for download.")

                # Optional hint
                if not st.session_state.get("scenario_pdf_ready", False):
                    st.caption("Prepare the PDF to enable download.")

                # Download button (safe)
                if st.session_state.get("scenario_pdf_ready", False):
                    st.download_button(
                        label="Download Scenario Report (PDF)",
                        data=st.session_state.scenario_pdf_buffer,
                        file_name="scenario_analysis_app1.pdf",
                        mime="application/pdf",
                        width='stretch',
                        key="scenario_pdf_download"
                    )
                else:
                    st.button(
                        "Download Scenario Report (PDF)",
                        width='stretch',
                        disabled=True,
                        key="scenario_pdf_disabled"
                    )
            render_scenario_results_a1()

    # ------------------------------------------------------------------
    # APP 2 -- Scenario Analysis
    # ------------------------------------------------------------------
    else:

        st.subheader("Configure Scenarios")
        st.caption("Add up to 5 scenarios. Each scenario runs through the XGBoost salary regressor.")

        if "scenarios_a2" not in st.session_state:
            st.session_state.scenarios_a2 = [
                {
                    "label": "Scenario 1",
                    "experience_level": "SE",
                    "employment_type": "FT",
                    "job_title": "Data Scientist" if "Data Scientist" in app2_job_titles else app2_job_titles[0],
                    "employee_residence": "US",
                    "remote_ratio": 0,
                    "company_location": "US",
                    "company_size": "M"
                }
            ]

        if st.button("Add Scenario", key="add_scenario_a2") and len(st.session_state.scenarios_a2) < 5:
            idx = len(st.session_state.scenarios_a2) + 1
            st.session_state.scenarios_a2.append({
                "label": f"Scenario {idx}",
                "experience_level": "SE",
                "employment_type": "FT",
                "job_title": "Data Scientist" if "Data Scientist" in app2_job_titles else app2_job_titles[0],
                "employee_residence": "US",
                "remote_ratio": 0,
                "company_location": "US",
                "company_size": "M"
            })

        to_delete_a2 = None

        for i, sc in enumerate(st.session_state.scenarios_a2):
            with st.container(border=True):
                col_lbl, col_del = st.columns([6, 1])
                with col_lbl:
                    sc["label"] = st.text_input(
                        "Scenario Name",
                        value=sc["label"],
                        key=f"sc_a2_label_{i}"
                    )
                with col_del:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    if len(st.session_state.scenarios_a2) > 1:
                        if st.button("Remove", key=f"sc_a2_del_{i}"):
                            to_delete_a2 = i

                col_a2, col_b2, col_c2 = st.columns(3)

                exp_options_a2 = [x for x in ["EN", "MI", "SE", "EX"] if x in app2_experience_levels]
                emp_options_a2 = [x for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types]
                remote_options_a2 = [x for x in [0, 50, 100] if x in app2_remote_ratios]
                size_options_a2 = list(app2_company_sizes)

                with col_a2:
                    exp_display = st.selectbox(
                        "Experience Level",
                        [EXPERIENCE_MAP[x] for x in exp_options_a2],
                        index=exp_options_a2.index(sc["experience_level"]) if sc["experience_level"] in exp_options_a2 else 0,
                        key=f"sc_a2_exp_{i}"
                    )
                    sc["experience_level"] = EXPERIENCE_REVERSE.get(exp_display, "SE")

                    emp_display = st.selectbox(
                        "Employment Type",
                        [EMPLOYMENT_MAP[x] for x in emp_options_a2],
                        index=emp_options_a2.index(sc["employment_type"]) if sc["employment_type"] in emp_options_a2 else 0,
                        key=f"sc_a2_emp_{i}"
                    )
                    sc["employment_type"] = EMPLOYMENT_REVERSE.get(emp_display, "FT")

                with col_b2:
                    sc["job_title"] = st.selectbox(
                        "Job Title", app2_job_titles,
                        index=app2_job_titles.index(sc["job_title"]) if sc["job_title"] in app2_job_titles else 0,
                        key=f"sc_a2_job_{i}"
                    )

                    remote_display = st.selectbox(
                        "Work Mode",
                        [REMOTE_MAP[x] for x in remote_options_a2],
                        index=remote_options_a2.index(sc["remote_ratio"]) if sc["remote_ratio"] in remote_options_a2 else 0,
                        key=f"sc_a2_remote_{i}"
                    )
                    sc["remote_ratio"] = REMOTE_REVERSE.get(remote_display, 0)

                with col_c2:
                    # Employee residence
                    detected_res_a2_sc = COUNTRY_NAME_MAP.get(sc["employee_residence"])
                    detected_res_display_a2_sc = (
                        f"{detected_res_a2_sc} ({sc['employee_residence']})"
                        if detected_res_a2_sc else sc["employee_residence"]
                    )
                    if detected_res_display_a2_sc not in app2_employee_residence_display_options:
                        detected_res_display_a2_sc = (
                            "United States (US)"
                            if "United States (US)" in app2_employee_residence_display_options
                            else app2_employee_residence_display_options[0]
                        )
                    res_display_sc = st.selectbox(
                        "Employee Residence",
                        app2_employee_residence_display_options,
                        index=app2_employee_residence_display_options.index(detected_res_display_a2_sc),
                        key=f"sc_a2_res_{i}"
                    )
                    if res_display_sc == "Other":
                        sc["employee_residence"] = "US"
                    elif "(" in res_display_sc:
                        sc["employee_residence"] = res_display_sc.split("(")[-1].replace(")", "").strip()
                    else:
                        sc["employee_residence"] = res_display_sc

                    # Company location
                    detected_loc_a2_sc = COUNTRY_NAME_MAP.get(sc["company_location"])
                    detected_loc_display_a2_sc = (
                        f"{detected_loc_a2_sc} ({sc['company_location']})"
                        if detected_loc_a2_sc else sc["company_location"]
                    )
                    if detected_loc_display_a2_sc not in app2_country_display_options:
                        detected_loc_display_a2_sc = (
                            "United States (US)"
                            if "United States (US)" in app2_country_display_options
                            else app2_country_display_options[0]
                        )
                    loc_display_sc = st.selectbox(
                        "Company Location",
                        app2_country_display_options,
                        index=app2_country_display_options.index(detected_loc_display_a2_sc),
                        key=f"sc_a2_loc_{i}"
                    )
                    if "(" in loc_display_sc:
                        sc["company_location"] = loc_display_sc.split("(")[-1].replace(")", "").strip()
                    else:
                        sc["company_location"] = loc_display_sc

                    size_display_sc = st.selectbox(
                        "Company Size",
                        [COMPANY_SIZE_MAP[x] for x in size_options_a2],
                        index=size_options_a2.index(sc["company_size"]) if sc["company_size"] in size_options_a2 else 0,
                        key=f"sc_a2_size_{i}"
                    )
                    sc["company_size"] = COMPANY_SIZE_REVERSE.get(size_display_sc, "M")

        if to_delete_a2 is not None:
            st.session_state.scenarios_a2.pop(to_delete_a2)
            st.rerun()

        st.divider()

        if st.button("Run All Scenarios", type="primary", width="stretch", key="run_scenarios_a2"):

            results_a2 = []

            for sc in st.session_state.scenarios_a2:

                try:
                    jr, sr, ex, mg, dom = title_features(sc["job_title"])
                    exp_x_dom = f"{sc['experience_level']}_{dom}"

                    input_df_a2_sc = pd.DataFrame([{
                        "experience_level": sc["experience_level"],
                        "employment_type": sc["employment_type"],
                        "job_title": sc["job_title"],
                        "employee_residence": sc["employee_residence"],
                        "remote_ratio": int(sc["remote_ratio"]),
                        "company_location": sc["company_location"],
                        "company_size": sc["company_size"],
                        "title_is_junior": jr,
                        "title_is_senior": sr,
                        "title_is_exec": ex,
                        "title_is_mgmt": mg,
                        "title_domain": dom,
                        "exp_x_domain": exp_x_dom
                    }])

                    pred_log = app2_model.predict(input_df_a2_sc)[0]
                    pred_usd = float(np.expm1(pred_log))

                    res_name = COUNTRY_NAME_MAP.get(sc["employee_residence"], sc["employee_residence"])
                    loc_name = COUNTRY_NAME_MAP.get(sc["company_location"], sc["company_location"])

                    results_a2.append({
                        "Scenario": sc["label"],
                        "Job Title": sc["job_title"],
                        "Experience Level": EXPERIENCE_MAP.get(sc["experience_level"], sc["experience_level"]),
                        "Employment": EMPLOYMENT_MAP.get(sc["employment_type"], sc["employment_type"]),
                        "Work Mode": REMOTE_MAP.get(sc["remote_ratio"], str(sc["remote_ratio"])),
                        "Company Size": COMPANY_SIZE_MAP.get(sc["company_size"], sc["company_size"]),
                        "Residence": res_name,
                        "Company Location": loc_name,
                        "Predicted Salary (USD)": round(pred_usd, 2)
                    })

                except Exception as e_sc:
                    st.error(f"Prediction failed for **{sc['label']}**: {e_sc}")

            st.session_state.scenario_results_a2 = results_a2

            st.session_state.scenario_pdf_ready_a2 = False
            st.session_state.scenario_pdf_buffer_a2 = None

        # ------ RESULTS ------
        if "scenario_results_a2" in st.session_state and st.session_state.scenario_results_a2:

            @st.fragment
            def render_scenario_results_a2():
                results_a2 = st.session_state.scenario_results_a2
                res_df_a2 = pd.DataFrame(results_a2)
                st.caption("Results are based on model predictions learned from historical data and may reflect dataset-specific patterns.")

                st.divider()
                st.subheader("Comparison Table")
                st.dataframe(res_df_a2, width='stretch', hide_index=True)

                best_row_a2 = res_df_a2.loc[res_df_a2["Predicted Salary (USD)"].idxmax()]
                st.success(f"Highest predicted salary: {best_row_a2['Scenario']} -- ${best_row_a2['Predicted Salary (USD)']:,.0f}")

                st.divider()
                st.subheader("Predicted Salary Comparison")

                fig_sc_bar_a2 = px.bar(
                    res_df_a2,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Scenario",
                    title="Predicted Annual Salary by Scenario",
                    color_discrete_sequence=colorway,
                    text="Predicted Salary (USD)"
                )
                fig_sc_bar_a2.update_traces(
                    texttemplate="$%{text:,.0f}",
                    textposition="outside"
                )
                apply_theme(fig_sc_bar_a2)
                st.plotly_chart(fig_sc_bar_a2, width='stretch')
                st.caption("This chart compares predicted salaries across different user-defined scenarios.")

                st.divider()
                st.subheader("Salary by Experience Level")

                fig_exp_sc_a2 = px.bar(
                    res_df_a2,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Experience Level",
                    title="Scenarios Colored by Experience Level",
                    color_discrete_map={
                        "Entry Level": get_colorway()[1], "Mid Level": get_colorway()[0], "Senior Level": get_colorway()[3], "Executive Level": get_colorway()[4]
                    }
                )
                apply_theme(fig_exp_sc_a2)
                st.plotly_chart(fig_exp_sc_a2, width='stretch')
                st.caption("This chart shows how predicted salary varies across experience levels for different scenarios.")

                st.divider()
                st.subheader("Salary by Company Size")

                fig_size_sc_a2 = px.bar(
                    res_df_a2,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Company Size",
                    title="Scenarios Colored by Company Size",
                    color_discrete_map={
                        "Small Company": get_colorway()[1], "Medium Company": get_colorway()[0], "Large Company": get_colorway()[3]
                    }
                )
                apply_theme(fig_size_sc_a2)
                st.plotly_chart(fig_size_sc_a2, width='stretch')
                st.caption("This chart compares predicted salary across different company sizes for each scenario.")

                st.divider()
                st.subheader("Salary by Work Mode")

                fig_remote_sc_a2 = px.bar(
                    res_df_a2,
                    x="Scenario",
                    y="Predicted Salary (USD)",
                    color="Work Mode",
                    title="Scenarios Colored by Work Mode",
                    color_discrete_map={
                        "On-site": get_colorway()[1], "Hybrid": get_colorway()[0], "Fully Remote": get_colorway()[2]
                    }
                )
                apply_theme(fig_remote_sc_a2)
                st.plotly_chart(fig_remote_sc_a2, width='stretch')
                st.caption("This chart shows how predicted salary varies based on work mode (on-site, hybrid, remote).")

                st.divider()
                st.subheader("Salary Sensitivity -- Experience Level Sweep")
                st.caption(
                    "Pick one scenario as a baseline and see how predicted salary changes "
                    "across all four experience levels, holding all other inputs fixed."
                )

                sweep_scenario_a2 = st.selectbox(
                    "Select Baseline Scenario for Sweep",
                    options=[sc["label"] for sc in st.session_state.scenarios_a2],
                    key="sweep_scenario_select_a2"
                )

                base_sc_a2 = next(
                    (s for s in st.session_state.scenarios_a2 if s["label"] == sweep_scenario_a2),
                    st.session_state.scenarios_a2[0]
                )

                sweep_exp_rows_a2 = []
                for exp_code in ["EN", "MI", "SE", "EX"]:
                    jr2, sr2, ex2, mg2, dom2 = title_features(base_sc_a2["job_title"])
                    exp_x_dom2 = f"{exp_code}_{dom2}"
                    sweep_input = pd.DataFrame([{
                        "experience_level": exp_code,
                        "employment_type": base_sc_a2["employment_type"],
                        "job_title": base_sc_a2["job_title"],
                        "employee_residence": base_sc_a2["employee_residence"],
                        "remote_ratio": int(base_sc_a2["remote_ratio"]),
                        "company_location": base_sc_a2["company_location"],
                        "company_size": base_sc_a2["company_size"],
                        "title_is_junior": jr2,
                        "title_is_senior": sr2,
                        "title_is_exec": ex2,
                        "title_is_mgmt": mg2,
                        "title_domain": dom2,
                        "exp_x_domain": exp_x_dom2
                    }])
                    sw_pred = float(np.expm1(app2_model.predict(sweep_input)[0]))
                    sweep_exp_rows_a2.append({
                        "Experience Level": EXPERIENCE_MAP[exp_code],
                        "Predicted Salary (USD)": sw_pred
                    })

                sweep_exp_df_a2 = pd.DataFrame(sweep_exp_rows_a2)

                fig_sweep_exp_a2 = px.line(
                    sweep_exp_df_a2,
                    x="Experience Level",
                    y="Predicted Salary (USD)",
                    title=f"Salary Sensitivity: Experience Level Sweep -- {sweep_scenario_a2}",
                    markers=True,
                    color_discrete_sequence=[get_colorway()[0]],
                    text="Predicted Salary (USD)"
                )
                fig_sweep_exp_a2.update_traces(
                    texttemplate="$%{text:,.0f}",
                    textposition="top center"
                )
                fig_sweep_exp_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=["Entry Level", "Mid Level", "Senior Level", "Executive Level"]
                )
                apply_theme(fig_sweep_exp_a2)
                st.plotly_chart(fig_sweep_exp_a2, width='stretch')
                st.caption("This chart shows how predicted salary changes across experience levels while all other inputs remain constant.")

                st.divider()
                st.subheader("Salary Sensitivity -- Company Size Sweep")
                st.caption(
                    "See how predicted salary changes across company sizes "
                    "for the selected baseline scenario."
                )

                size_sweep_rows_a2 = []
                for size_code in ["S", "M", "L"]:
                    jr3, sr3, ex3, mg3, dom3 = title_features(base_sc_a2["job_title"])
                    exp_x_dom3 = f"{base_sc_a2['experience_level']}_{dom3}"
                    size_sweep_input = pd.DataFrame([{
                        "experience_level": base_sc_a2["experience_level"],
                        "employment_type": base_sc_a2["employment_type"],
                        "job_title": base_sc_a2["job_title"],
                        "employee_residence": base_sc_a2["employee_residence"],
                        "remote_ratio": int(base_sc_a2["remote_ratio"]),
                        "company_location": base_sc_a2["company_location"],
                        "company_size": size_code,
                        "title_is_junior": jr3,
                        "title_is_senior": sr3,
                        "title_is_exec": ex3,
                        "title_is_mgmt": mg3,
                        "title_domain": dom3,
                        "exp_x_domain": exp_x_dom3
                    }])
                    sz_pred = float(np.expm1(app2_model.predict(size_sweep_input)[0]))
                    size_sweep_rows_a2.append({
                        "Company Size": COMPANY_SIZE_MAP[size_code],
                        "Predicted Salary (USD)": sz_pred
                    })

                size_sweep_df_a2 = pd.DataFrame(size_sweep_rows_a2)

                fig_sweep_size_a2 = px.bar(
                    size_sweep_df_a2,
                    x="Company Size",
                    y="Predicted Salary (USD)",
                    title=f"Salary by Company Size -- {sweep_scenario_a2}",
                    color="Company Size",
                    color_discrete_sequence=get_colorway_3_stages(),
                    text="Predicted Salary (USD)"
                )
                fig_sweep_size_a2.update_traces(
                    texttemplate="$%{text:,.0f}",
                    textposition="outside"
                )
                fig_sweep_size_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=["Small Company", "Medium Company", "Large Company"]
                )
                apply_theme(fig_sweep_size_a2)
                st.plotly_chart(fig_sweep_size_a2, width='stretch')
                st.caption("This chart shows how predicted salary changes across company sizes for the selected baseline scenario.")

                st.divider()
                st.subheader("Export Scenario Results")
                export_format_sc_a2 = st.selectbox(
                    "Select export format",
                    ["CSV", "XLSX", "JSON"],
                    key="sc_export_format_a2"
                )
                if export_format_sc_a2 == "CSV":
                    sc_file_data_a2 = res_df_a2.to_csv(index=False).encode("utf-8")
                    sc_file_name_a2 = "scenario_results.csv"
                    sc_mime_a2 = "text/csv"
                elif export_format_sc_a2 == "XLSX":
                    sc_buf_a2 = BytesIO()
                    res_df_a2.to_excel(sc_buf_a2, index=False)
                    sc_file_data_a2 = sc_buf_a2.getvalue()
                    sc_file_name_a2 = "scenario_results.xlsx"
                    sc_mime_a2 = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    sc_file_data_a2 = res_df_a2.to_json(orient="records")
                    sc_file_name_a2 = "scenario_results.json"
                    sc_mime_a2 = "application/json"

                st.download_button(
                    "Download Scenario Results",
                    data=sc_file_data_a2,
                    file_name=sc_file_name_a2,
                    mime=sc_mime_a2,
                    width="stretch"
                )
                # ---------------- PDF GENERATION (SCENARIO APP 2) ----------------
                st.divider()

                if st.button("Prepare PDF Report", width='stretch', key="scenario_pdf_prepare_a2"):

                    st.session_state.scenario_pdf_buffer_a2 = app2_generate_scenario_pdf(
                        pd.DataFrame(st.session_state.scenario_results_a2)
                    )

                    st.session_state.scenario_pdf_ready_a2 = True
                    st.success("PDF is ready for download.")

                # Optional hint
                if not st.session_state.get("scenario_pdf_ready_a2", False):
                    st.caption("Prepare the PDF to enable download.")

                # Download button (safe)
                if st.session_state.get("scenario_pdf_ready_a2", False):
                    st.download_button(
                        label="Download Scenario Report (PDF)",
                        data=st.session_state.scenario_pdf_buffer_a2,
                        file_name="scenario_analysis_app2.pdf",
                        mime="application/pdf",
                        width='stretch',
                        key="scenario_pdf_download_a2"
                    )
                else:
                    st.button(
                        "Download Scenario Report (PDF)",
                        width='stretch',
                        disabled=True,
                        key="scenario_pdf_disabled_a2"
                    )
            render_scenario_results_a2()