"""
batch_prediction_tab.py
-----------------------
Renders the Batch Prediction tab for both App 1 and App 2.

All external dependencies are injected via render_batch_prediction_tab() so that:
  - No resources are loaded or cached here (zero double-loading)
  - No imports from app_resume.py (zero circular dependencies)
  - The inner logic is identical to the original tab code

Usage in app_resume.py:
    from batch_prediction_tab import render_batch_prediction_tab

    with tab_objects[2]:
        render_batch_prediction_tab(
            is_app1=IS_APP1,
            app1_model=app1_model if IS_APP1 else None,
            app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
            app1_cluster_model=app1_cluster_model_a1 if IS_APP1 else None,
            app1_cluster_metadata=app1_cluster_metadata_a1 if IS_APP1 else None,
            app1_job_titles=app1_job_titles,
            app1_countries=app1_countries,
            app2_model=app2_model if not IS_APP1 else None,
            app2_job_titles=app2_job_titles,
            df_app1=df_app1,
            df_app2=df_app2,
            APP1_REQUIRED_COLUMNS=APP1_REQUIRED_COLUMNS,
            APP2_REQUIRED_COLUMNS=APP2_REQUIRED_COLUMNS,
            SALARY_BAND_LABELS=SALARY_BAND_LABELS,
            EXPERIENCE_MAP=EXPERIENCE_MAP,
            COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
            REMOTE_MAP=REMOTE_MAP,
            COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
            apply_theme=_apply_theme,
            get_plot_df=get_plot_df,
            generate_salary_leaderboard=generate_salary_leaderboard,
            app1_validate_bulk_dataframe=app1_validate_bulk_dataframe,
            app2_validate_bulk_dataframe=app2_validate_bulk_dataframe,
            convert_drive_link=convert_drive_link,
            title_features=title_features,
            app1_generate_bulk_pdf=app1_generate_bulk_pdf,
            app2_generate_bulk_pdf=app2_generate_bulk_pdf,
        )
"""

import ast
import re

import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from io import BytesIO


def render_batch_prediction_tab(
    is_app1,
    # App 1 models and metadata
    app1_model,
    app1_salary_band_model,
    app1_cluster_model,
    app1_cluster_metadata,
    app1_job_titles,
    app1_countries,
    # App 2 model
    app2_model,
    app2_job_titles,
    # Datasets (for sample previews)
    df_app1,
    df_app2,
    # Column name lists
    APP1_REQUIRED_COLUMNS,
    APP2_REQUIRED_COLUMNS,
    # Lookup maps
    SALARY_BAND_LABELS,
    EXPERIENCE_MAP,
    COMPANY_SIZE_MAP,
    REMOTE_MAP,
    COUNTRY_NAME_MAP,
    # Shared helpers
    apply_theme,
    get_plot_df,
    generate_salary_leaderboard,
    app1_validate_bulk_dataframe,
    app2_validate_bulk_dataframe,
    convert_drive_link,
    title_features,
    # PDF generators
    app1_generate_bulk_pdf,
    app2_generate_bulk_pdf,
):
    st.header(":material/batch_prediction: Batch Prediction")
    st.caption("Upload multiple records to generate salary predictions and analytics in one run.")

    with st.expander("File Format & Input Guide"):
        if is_app1:
            st.markdown("""
**Required Columns**
Your file must contain exactly these columns with these exact names:

| Column | Type | Allowed Values |
|---|---|---|
| Age | Integer | 18 to 70 |
| Years of Experience | Float | 0.0 to 40.0 |
| Education Level | Integer | 0 (High School), 1 (Bachelor's), 2 (Master's), 3 (PhD) |
| Senior | Integer | 0 (No), 1 (Yes) |
| Gender | Text | Male, Female, Other |
| Job Title | Text | See supported job titles below |
| Country | Text | See supported countries below |

**Supported File Formats**
- CSV, XLSX, JSON, SQL
- Download the sample file from the left column to use as a template.

**Supported Job Titles**
""")
            st.code(", ".join(app1_job_titles))
            st.markdown("""
**Supported Countries**
""")
            st.code(", ".join(app1_countries))
            st.markdown("""
**Notes**
- Extra columns in your file are ignored -- only the required columns are used.
- If your country is not in the supported list, use `Other`.
- Age minus Years of Experience must be at least 18 (unrealistic experience for age will be flagged).
- Maximum file size is 50,000 rows. Files above 10,000 rows may be slower to process.
            """)

        else:
            st.markdown("""
**Required Columns**
Your file must contain exactly these columns with these exact names:

| Column | Type | Allowed Values |
|---|---|---|
| experience_level | Text | EN (Entry), MI (Mid), SE (Senior), EX (Executive) |
| employment_type | Text | FT (Full Time), PT (Part Time), CT (Contract), FL (Freelance) |
| job_title | Text | See supported job titles below |
| employee_residence | Text | ISO 2-letter country code (e.g. US, IN, GB) |
| remote_ratio | Integer | 0 (On-site), 50 (Hybrid), 100 (Fully Remote) |
| company_location | Text | ISO 2-letter country code (e.g. US, IN, GB) |
| company_size | Text | S (Small), M (Medium), L (Large) |

**Supported File Formats**
- CSV, XLSX, JSON, SQL
- Download the sample file from the left column to use as a template.

**Supported Job Titles**
""")
            st.code(", ".join(app2_job_titles))
            st.markdown("""
**Supported Country Codes**
""")
            st.code(", ".join(sorted(COUNTRY_NAME_MAP.keys())))
            st.markdown("""
**Notes**
- Extra columns in your file are ignored -- only the required columns are used.
- Use raw codes for experience_level, employment_type, and company_size (e.g. `FT` not `Full Time`).
- employee_residence and company_location must be valid ISO 2-letter country codes present in the supported list.
- Maximum file size is 50,000 rows. Files above 10,000 rows may be slower to process.
            """)

    col1, col2, col3 = st.columns(3)

    # -------------------------------------------------------
    # APP 1 -- Batch Prediction
    # -------------------------------------------------------
    if is_app1:

        with col1:
            st.subheader("Sample File")
            sample_df_a1 = df_app1.head(5)
            st.markdown("**Sample Preview:**")
            st.dataframe(sample_df_a1, width='stretch')
            st.markdown("### Download Sample")
            sample_format_a1 = st.selectbox("Select sample format", ["CSV", "XLSX", "JSON", "SQL"],
                                             key="sample_format_select_a1")
            if sample_format_a1 == "CSV":
                file_data_s = sample_df_a1.to_csv(index=False).encode("utf-8")
                file_name_s = "sample.csv"
                mime_s = "text/csv"
            elif sample_format_a1 == "JSON":
                file_data_s = sample_df_a1.to_json(orient="records")
                file_name_s = "sample.json"
                mime_s = "application/json"
            elif sample_format_a1 == "XLSX":
                buffer_s = BytesIO()
                sample_df_a1.to_excel(buffer_s, index=False)
                file_data_s = buffer_s.getvalue()
                file_name_s = "sample.xlsx"
                mime_s = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                sql_lines_s = []
                for _, row in sample_df_a1.iterrows():
                    gender = str(row["Gender"]).replace("'", "''")
                    job_title = str(row["Job Title"]).replace("'", "''")
                    country = str(row["Country"]).replace("'", "''")

                    sql_lines_s.append(
                        "INSERT INTO salaries VALUES "
                        f"({row['Age']}, {row['Years of Experience']}, "
                        f"{row['Education Level']}, {row['Senior']}, "
                        f"'{gender}', '{job_title}', '{country}');"
                    )
                file_data_s = "\n".join(sql_lines_s)
                file_name_s = "sample.sql"
                mime_s = "text/sql"
            st.download_button("Download Sample File", data=file_data_s,
                               file_name=file_name_s, mime=mime_s, width='stretch')

        with col2:
            st.subheader("Upload File")
            uploaded_file_a1 = st.file_uploader("Upload CSV, JSON, XLSX or SQL",
                                                 type=["csv", "json", "xlsx", "sql"])
            st.divider()
            st.markdown("### Upload via Public Google Drive Link")
            with st.container(border=True):
                st.markdown("Paste a publicly shared Google Drive file link below.")
                st.caption("Make sure the file is set to 'Anyone with the link can view'.")
                drive_link_a1 = st.text_input(
                    "Google Drive File Link",
                    placeholder="https://drive.google.com/file/d/XXXXXXXX/view?usp=sharing"
                )
                if uploaded_file_a1 is None and not drive_link_a1:
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None

            bulk_df_a1 = None
            file_source_name_a1 = None

            if uploaded_file_a1:
                file_source_name_a1 = uploaded_file_a1.name
                if st.session_state.bulk_uploaded_name != file_source_name_a1:
                    st.session_state.bulk_uploaded_name = file_source_name_a1
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None
                try:
                    if uploaded_file_a1.name.endswith("csv"):
                        bulk_df_a1 = pd.read_csv(uploaded_file_a1)
                    elif uploaded_file_a1.name.endswith("json"):
                        bulk_df_a1 = pd.read_json(uploaded_file_a1)
                    elif uploaded_file_a1.name.endswith("xlsx"):
                        bulk_df_a1 = pd.read_excel(uploaded_file_a1)
                    elif uploaded_file_a1.name.endswith("sql"):
                        content_a1 = uploaded_file_a1.read().decode("utf-8")
                        matches_a1 = re.findall(r"VALUES\s*\((.*?)\);", content_a1)
                        rows_a1 = []
                        for match in matches_a1:
                            rows_a1.append(list(ast.literal_eval(f"({match})")))
                        bulk_df_a1 = pd.DataFrame(rows_a1, columns=APP1_REQUIRED_COLUMNS)
                except Exception:
                    st.error("The uploaded file could not be processed. Please ensure it is a valid and properly formatted file.")
                    bulk_df_a1 = None

            elif drive_link_a1:
                direct_url_a1 = convert_drive_link(drive_link_a1)
                if direct_url_a1 is None:
                    st.error("Invalid Google Drive link. Please provide a valid public sharing link.")
                else:
                    drive_format_a1 = st.selectbox("Select format of Google Drive file",
                                                    ["CSV", "XLSX", "JSON", "SQL"],
                                                    key="drive_format_select_a1")
                    try:
                        with st.spinner("Downloading file from Google Drive..."):
                            response_a1 = requests.get(direct_url_a1, timeout=20)
                        if response_a1.status_code == 200:
                            content_a1 = response_a1.content
                            file_source_name_a1 = drive_link_a1
                            if st.session_state.bulk_uploaded_name != file_source_name_a1:
                                st.session_state.bulk_uploaded_name = file_source_name_a1
                                st.session_state.bulk_result_df = None
                                st.session_state.bulk_pdf_buffer = None
                            if drive_format_a1 == "CSV":
                                bulk_df_a1 = pd.read_csv(BytesIO(content_a1))
                            elif drive_format_a1 == "JSON":
                                bulk_df_a1 = pd.read_json(BytesIO(content_a1))
                            elif drive_format_a1 == "XLSX":
                                bulk_df_a1 = pd.read_excel(BytesIO(content_a1))
                            elif drive_format_a1 == "SQL":
                                text_c = content_a1.decode("utf-8")
                                matches_a1 = re.findall(r"VALUES\s*\((.*?)\);", text_c)
                                rows_a1 = [list(ast.literal_eval(f"({m})")) for m in matches_a1]
                                bulk_df_a1 = pd.DataFrame(rows_a1, columns=APP1_REQUIRED_COLUMNS)
                        else:
                            st.error("Unable to download file from Google Drive. Please check file permissions.")
                    except Exception:
                        st.error("Error downloading or processing Google Drive file. Please verify the link and file format.")
                        bulk_df_a1 = None

            if bulk_df_a1 is not None:

                MAX_ROWS = 50000
                WARNING_ROWS = 10000

                row_count = len(bulk_df_a1)

                if row_count > MAX_ROWS:
                    st.error(f"File too large ({row_count} rows). Maximum allowed is {MAX_ROWS} rows.")
                    st.stop()
                elif row_count > WARNING_ROWS:
                    st.warning(f"Large file detected ({row_count} rows). Performance may be slower.")

                if bulk_df_a1 is not None:
                    is_valid_a1, validation_error_a1 = app1_validate_bulk_dataframe(bulk_df_a1)

                    if not is_valid_a1:
                        st.error(validation_error_a1)
                        bulk_df_a1 = None
                    else:
                        bulk_df_a1 = bulk_df_a1[APP1_REQUIRED_COLUMNS]
                        st.markdown("**Uploaded File Preview:**")
                        st.dataframe(bulk_df_a1.head(), width='stretch')

        with col3:
            st.subheader("Run Prediction")
            has_data_a1 = "bulk_df_a1" in locals() and bulk_df_a1 is not None
            if not has_data_a1:
                st.info("Upload a file or provide a public Google Drive link to generate batch salary predictions.")
            else:
                run_clicked_a1 = st.button("Run Batch Prediction", width='stretch', type="primary")
                if run_clicked_a1:
                    try:
                        with st.spinner("Running batch salary prediction..."):
                            preds_a1 = app1_model.predict(bulk_df_a1)
                            band_preds_a1 = app1_salary_band_model.predict(bulk_df_a1)
                            band_labels_a1 = [SALARY_BAND_LABELS.get(b, "Unknown") for b in band_preds_a1]
                            cluster_preds_a1 = app1_cluster_model.predict(
                                bulk_df_a1[["Years of Experience", "Education Level"]]
                            )
                            stage_map_a1 = app1_cluster_metadata["cluster_stage_mapping"]
                            career_stage_a1 = [stage_map_a1[c] for c in cluster_preds_a1]
                            result_df_a1 = bulk_df_a1.copy()
                            result_df_a1["Predicted Annual Salary"] = preds_a1
                            result_df_a1["Estimated Salary Level"] = band_labels_a1
                            result_df_a1["Career Stage"] = career_stage_a1
                            st.session_state.bulk_result_df = result_df_a1
                    except Exception:
                        st.error("Prediction failed. Please ensure the uploaded data matches the required structure and values.")
                        st.session_state.bulk_result_df = None
                        st.session_state.bulk_pdf_buffer = None

                if st.session_state.bulk_result_df is not None:
                    st.markdown("**Result Preview:**")
                    st.dataframe(st.session_state.bulk_result_df.head(), width='stretch')
                    st.divider()
                    st.markdown("### Export Results")
                    export_format_a1 = st.selectbox("Select export format", ["CSV", "XLSX", "JSON", "SQL"],
                                                     key="export_format_select_a1")
                    result_df_a1 = st.session_state.bulk_result_df
                    export_df_a1 = result_df_a1.copy()
                    export_df_a1["Predicted Annual Salary"] = export_df_a1["Predicted Annual Salary"].round(2)
                    if export_format_a1 == "CSV":
                        file_data_e = export_df_a1.to_csv(index=False).encode("utf-8")
                        file_name_e = "results.csv"
                        mime_e = "text/csv"
                    elif export_format_a1 == "JSON":
                        file_data_e = export_df_a1.to_json(orient="records")
                        file_name_e = "results.json"
                        mime_e = "application/json"
                    elif export_format_a1 == "XLSX":
                        buffer_e = BytesIO()
                        export_df_a1.to_excel(buffer_e, index=False)
                        file_data_e = buffer_e.getvalue()
                        file_name_e = "results.xlsx"
                        mime_e = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else:
                        sql_lines_e = [
                            "CREATE TABLE IF NOT EXISTS salary_predictions ("
                            "Age INTEGER, Years_of_Experience REAL, Education_Level INTEGER, "
                            "Senior INTEGER, Gender TEXT, Job_Title TEXT, Country TEXT, "
                            "Predicted_Annual_Salary REAL, Estimated_Salary_Level TEXT, Predicted_Career_Stage);"
                        ]
                        for _, row in export_df_a1.iterrows():
                            gender = str(row["Gender"]).replace("'", "''")
                            job_title = str(row["Job Title"]).replace("'", "''")
                            country = str(row["Country"]).replace("'", "''")
                            salary_level = str(row["Estimated Salary Level"]).replace("'", "''")
                            career_stage = str(row["Career Stage"]).replace("'", "''")

                            sql_lines_e.append(
                                "INSERT INTO salary_predictions VALUES "
                                f"({row['Age']}, {row['Years of Experience']}, "
                                f"{row['Education Level']}, {row['Senior']}, "
                                f"'{gender}', '{job_title}', "
                                f"'{country}', {row['Predicted Annual Salary']}, "
                                f"'{salary_level}', '{career_stage}');"
                            )
                        file_data_e = "\n".join(sql_lines_e)
                        file_name_e = "results.sql"
                        mime_e = "text/sql"
                    st.download_button("Download File", data=file_data_e,
                                       file_name=file_name_e, mime=mime_e, width='stretch')

        # Batch Analytics -- App 1
        if st.session_state.bulk_result_df is not None:

            @st.fragment
            def render_batch_analytics_a1():

                st.divider()
                st.header("Batch Prediction Analytics")

                if st.button("Prepare Batch PDF Report", width='stretch'):
                    with st.spinner("Preparing PDF report..."):
                        st.session_state.bulk_pdf_buffer = app1_generate_bulk_pdf(
                            st.session_state.bulk_result_df
                        )
                if "bulk_pdf_buffer" in st.session_state and st.session_state.bulk_pdf_buffer is not None:
                    st.download_button(
                        label="Download Batch Prediction Summary (PDF)",
                        data=st.session_state.bulk_pdf_buffer,
                        file_name="bulk_salary_summary.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )
                st.divider()
                analytics_df_a1 = st.session_state.bulk_result_df

                st.subheader("Summary Metrics")
                avg_s = analytics_df_a1["Predicted Annual Salary"].mean()
                min_s = analytics_df_a1["Predicted Annual Salary"].min()
                max_s = analytics_df_a1["Predicted Annual Salary"].max()
                std_s = analytics_df_a1["Predicted Annual Salary"].std()
                std_s = 0 if pd.isna(std_s) else std_s
                col1b, col2b, col3b, col4b, col5b = st.columns(5)
                col1b.metric("Total Records", analytics_df_a1.shape[0])
                col2b.metric("Average Salary", f"${avg_s:,.2f}")
                col3b.metric("Minimum Salary", f"${min_s:,.2f}")
                col4b.metric("Maximum Salary", f"${max_s:,.2f}")
                col5b.metric("Salary Std Deviation", f"${std_s:,.2f}")

                st.subheader("Salary Level Summary")
                level_counts = analytics_df_a1["Estimated Salary Level"].value_counts()
                low_count = level_counts.get("Early Career Range", 0)
                med_count = level_counts.get("Professional Range", 0)
                high_count = level_counts.get("Executive Range", 0)
                col_l1, col_l2, col_l3 = st.columns(3)
                col_l1.metric("Early Career Range", low_count)
                col_l2.metric("Professional Range", med_count)
                col_l3.metric("Executive Range", high_count)

                st.subheader("Career Stage Summary")
                stage_counts_a1 = analytics_df_a1["Career Stage"].value_counts()
                entry_count = stage_counts_a1.get("Entry Stage", 0)
                growth_count = stage_counts_a1.get("Growth Stage", 0)
                leader_count = stage_counts_a1.get("Leadership Stage", 0)
                col_c1, col_c2, col_c3 = st.columns(3)
                col_c1.metric("Entry Stage", entry_count)
                col_c2.metric("Growth Stage", growth_count)
                col_c3.metric("Leadership Stage", leader_count)

                st.divider()
                st.subheader("Top Salary Leaderboard")

                leaderboard_a1 = generate_salary_leaderboard(
                    df=analytics_df_a1,
                    job_col="Job Title",
                    salary_col="Predicted Annual Salary"
                )
                st.dataframe(
                    leaderboard_a1,
                    width='stretch',
                    hide_index=True
                )
                st.caption("Ranks job roles by average predicted salary in the uploaded batch. Top 3 roles are highlighted with medals.")
                st.divider()
                st.subheader("Salary Leaderboard Visualization")

                fig_lb_a1 = px.bar(
                    leaderboard_a1.head(10),
                    x="Average Salary (USD)",
                    y="Job Title",
                    orientation="h",
                    title="Top Roles by Salary",
                    color_discrete_sequence=["#60A5FA"]
                )
                fig_lb_a1.update_yaxes(categoryorder="total ascending")
                apply_theme(fig_lb_a1)
                st.plotly_chart(fig_lb_a1, width='stretch')

                # Sampling only for heavy scatter plots to improve performance
                plot_df_a1 = get_plot_df(analytics_df_a1)

                st.divider()
                st.subheader("Salary Distribution")
                fig_hist_a1 = px.histogram(
                    analytics_df_a1, x="Predicted Annual Salary",
                    nbins=min(25, len(analytics_df_a1)),
                    title="Distribution of Predicted Annual Salaries",
                    color_discrete_sequence=["#4F8EF7"]
                )
                fig_hist_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
                fig_hist_a1.update_layout(xaxis_title="Predicted Salary (USD)", yaxis_title="Count")
                apply_theme(fig_hist_a1)
                st.plotly_chart(fig_hist_a1, width='stretch')

                st.divider()
                st.subheader("Average Salary by Salary Level")
                band_salary_a1 = (analytics_df_a1.groupby("Estimated Salary Level")["Predicted Annual Salary"]
                                  .mean().reset_index())
                fig_band_a1 = px.bar(band_salary_a1, x="Estimated Salary Level",
                                      y="Predicted Annual Salary",
                                      title="Average Predicted Salary by Salary Level",
                                      color="Estimated Salary Level",
                                      color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"])
                fig_band_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Early Career Range",
                        "Professional Range",
                        "Executive Range"
                    ]
                )
                apply_theme(fig_band_a1)
                st.plotly_chart(fig_band_a1, width='stretch')

                st.divider()
                st.subheader("Salary Level Distribution by Education")
                edu_band_a1 = (analytics_df_a1.groupby(["Education Level", "Estimated Salary Level"])
                               .size().reset_index(name="Count"))
                edu_band_a1["Education Level"] = edu_band_a1["Education Level"].map(
                    {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"})
                fig_edu_band_a1 = px.bar(
                    edu_band_a1, x="Education Level", y="Count",
                    color="Estimated Salary Level",
                    title="Salary Levels Across Education Levels",
                    barmode="group",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_edu_band_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                apply_theme(fig_edu_band_a1)
                st.plotly_chart(fig_edu_band_a1, width='stretch')

                st.divider()
                st.subheader("Career Stage Distribution")

                stage_dist_a1 = (
                    analytics_df_a1["Career Stage"]
                    .value_counts()
                    .reset_index()
                )
                stage_dist_a1.columns = ["Career Stage", "Count"]

                fig_stage_dist_a1 = px.bar(
                    stage_dist_a1,
                    x="Career Stage",
                    y="Count",
                    title="Distribution of Career Stages",
                    color="Career Stage",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_stage_dist_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Entry Stage",
                        "Growth Stage",
                        "Leadership Stage"
                    ]
                )
                apply_theme(fig_stage_dist_a1)
                st.plotly_chart(fig_stage_dist_a1, width='stretch')

                st.divider()
                st.subheader("Average Salary by Career Stage")
                stage_salary_a1 = (
                    analytics_df_a1
                    .groupby("Career Stage")["Predicted Annual Salary"]
                    .mean()
                    .reset_index()
                )
                fig_stage_salary_a1 = px.bar(
                    stage_salary_a1,
                    x="Career Stage",
                    y="Predicted Annual Salary",
                    title="Average Predicted Salary by Career Stage",
                    color="Career Stage",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_stage_salary_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Entry Stage",
                        "Growth Stage",
                        "Leadership Stage"
                    ]
                )
                apply_theme(fig_stage_salary_a1)
                st.plotly_chart(fig_stage_salary_a1, width='stretch')

                st.divider()
                st.subheader("Career Stage Distribution by Education")

                edu_stage_a1 = (
                    analytics_df_a1
                    .groupby(["Education Level", "Career Stage"])
                    .size()
                    .reset_index(name="Count")
                )
                edu_stage_a1["Education Level"] = edu_stage_a1["Education Level"].map(
                    {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
                )
                fig_edu_stage_a1 = px.bar(
                    edu_stage_a1,
                    x="Education Level",
                    y="Count",
                    color="Career Stage",
                    title="Career Stage Distribution Across Education Levels",
                    barmode="group",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_edu_stage_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                apply_theme(fig_edu_stage_a1)
                st.plotly_chart(fig_edu_stage_a1, width='stretch')

                st.divider()
                st.subheader("Salary vs Experience Trend")
                fig_trend_a1 = px.scatter(
                    plot_df_a1, x="Years of Experience", y="Predicted Annual Salary",
                    trendline="ols", trendline_color_override="#F59E0B",
                    title="Predicted Salary vs Experience",
                    color_discrete_sequence=["#4F8EF7"]
                )
                fig_trend_a1.update_traces(marker=dict(size=7, opacity=0.65))
                apply_theme(fig_trend_a1)
                st.plotly_chart(fig_trend_a1, width='stretch')

                st.divider()
                st.subheader("Career Progression Landscape")
                fig_career_landscape = px.scatter(
                    plot_df_a1,
                    x="Years of Experience",
                    y="Predicted Annual Salary",
                    color="Estimated Salary Level",
                    symbol="Career Stage",
                    title="Career Progression and Salary Landscape",
                    labels={
                        "Years of Experience": "Years of Experience",
                        "Predicted Annual Salary": "Predicted Salary (USD)"
                    },
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_career_landscape.update_traces(
                    marker=dict(size=9, opacity=0.65)
                )
                apply_theme(fig_career_landscape)
                st.plotly_chart(fig_career_landscape, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Education Level")
                edu_group_a1 = (analytics_df_a1.groupby("Education Level")["Predicted Annual Salary"]
                                .mean().reset_index())
                edu_group_a1["Education Level"] = edu_group_a1["Education Level"].map(
                    {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"})
                fig_edu_bulk_a1 = px.bar(
                    edu_group_a1, x="Education Level", y="Predicted Annual Salary",
                    title="Average Predicted Salary by Education",
                    color="Education Level",
                    color_discrete_sequence=["#4F8EF7", "#38BDF8", "#34D399", "#A78BFA"]
                )
                fig_edu_bulk_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                apply_theme(fig_edu_bulk_a1)
                st.plotly_chart(fig_edu_bulk_a1, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Country")
                country_group_a1 = (analytics_df_a1.groupby("Country")["Predicted Annual Salary"]
                                    .mean().reset_index()
                                    .sort_values(by="Predicted Annual Salary", ascending=False))
                fig_country_bulk_a1 = px.bar(
                    country_group_a1, x="Country", y="Predicted Annual Salary",
                    title="Average Predicted Salary by Country",
                    color="Country",
                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B","#FB923C","#F472B6","#22D3EE","#818CF8","#6EE7B7"])
                fig_country_bulk_a1.update_xaxes(categoryorder="total descending")
                apply_theme(fig_country_bulk_a1)
                st.plotly_chart(fig_country_bulk_a1, width='stretch')

                st.divider()
                st.subheader("Senior vs Non-Senior Predicted Salary")
                senior_group_a1 = (analytics_df_a1.groupby("Senior")["Predicted Annual Salary"]
                                   .mean().reset_index())
                senior_group_a1["Senior"] = senior_group_a1["Senior"].map({0: "Non-Senior", 1: "Senior"})
                fig_senior_bulk_a1 = px.bar(
                    senior_group_a1, x="Senior", y="Predicted Annual Salary",
                    title="Average Predicted Salary by Seniority",
                    color="Senior",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7"]
                )
                fig_senior_bulk_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["Non-Senior", "Senior"]
                )
                apply_theme(fig_senior_bulk_a1)
                st.plotly_chart(fig_senior_bulk_a1, width='stretch')

                st.divider()
                st.subheader("Predicted Salary Distribution by Job Title")
                job_salary_a1 = analytics_df_a1.copy()
                top_jobs_a1 = job_salary_a1["Job Title"].value_counts().head(10).index
                job_salary_a1 = job_salary_a1[job_salary_a1["Job Title"].isin(top_jobs_a1)]
                fig_job_box_a1 = px.box(
                    job_salary_a1, x="Job Title", y="Predicted Annual Salary",
                    title="Salary Distribution by Job Title (Top 10)",
                    color="Job Title",
                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA",
                                              "#F59E0B","#FB923C","#F472B6","#22D3EE","#6366F1","#14B8A6"]
                )
                fig_job_box_a1.update_layout(xaxis_title="Job Title",
                                              yaxis_title="Predicted Salary (USD)", showlegend=False)
                apply_theme(fig_job_box_a1)
                st.plotly_chart(fig_job_box_a1, width='stretch')
            render_batch_analytics_a1()

    # -------------------------------------------------------
    # APP 2 -- Batch Prediction
    # -------------------------------------------------------
    else:

        with col1:
            st.subheader("Sample File")
            sample_df_a2 = df_app2[APP2_REQUIRED_COLUMNS].head(5)
            st.markdown("Sample Preview:")
            st.dataframe(sample_df_a2, width='stretch')
            st.markdown("### Download Sample")
            sample_format_a2 = st.selectbox("Select sample format", ["CSV", "XLSX", "JSON", "SQL"],
                                             key="sample_format_select_a2")
            if sample_format_a2 == "CSV":
                file_data_s2 = sample_df_a2.to_csv(index=False).encode("utf-8")
                file_name_s2 = "salaryscope_sample.csv"
                mime_s2 = "text/csv"
            elif sample_format_a2 == "JSON":
                file_data_s2 = sample_df_a2.to_json(orient="records")
                file_name_s2 = "salaryscope_sample.json"
                mime_s2 = "application/json"
            elif sample_format_a2 == "XLSX":
                buffer_s2 = BytesIO()
                sample_df_a2.to_excel(buffer_s2, index=False)
                file_data_s2 = buffer_s2.getvalue()
                file_name_s2 = "salaryscope_sample.xlsx"
                mime_s2 = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                sql_lines_s2 = [
                    "CREATE TABLE IF NOT EXISTS salary_predictions ("
                    "experience_level TEXT, employment_type TEXT, job_title TEXT, "
                    "employee_residence TEXT, remote_ratio INTEGER, "
                    "company_location TEXT, company_size TEXT);"
                ]
                for _, row in sample_df_a2.iterrows():
                    values_s2 = []
                    for col in APP2_REQUIRED_COLUMNS:
                        v = row[col]
                        if isinstance(v, str):
                            v = v.replace("'", "''")
                            values_s2.append(f"'{v}'")
                        else:
                            values_s2.append(str(v))
                    sql_lines_s2.append(
                        f"INSERT INTO salary_predictions ({', '.join(APP2_REQUIRED_COLUMNS)}) "
                        f"VALUES ({', '.join(values_s2)});"
                    )
                file_data_s2 = "\n".join(sql_lines_s2)
                file_name_s2 = "salaryscope_sample.sql"
                mime_s2 = "text/sql"
            st.download_button("Download Sample File", data=file_data_s2,
                               file_name=file_name_s2, mime=mime_s2, width='stretch')

        with col2:
            st.subheader("Upload File")
            uploaded_file_a2 = st.file_uploader("Upload CSV, JSON, XLSX or SQL",
                                                 type=["csv", "json", "xlsx", "sql"])
            st.divider()
            st.markdown("### Upload via Public Google Drive Link")
            with st.container(border=True):
                st.markdown("Paste a publicly shared Google Drive file link below.")
                st.caption("Make sure sharing is set to 'Anyone with the link can view'.")
                drive_link_a2 = st.text_input(
                    "Google Drive File Link",
                    placeholder="https://drive.google.com/file/d/XXXX/view?usp=sharing"
                )
                if uploaded_file_a2 is None and not drive_link_a2:
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None

            bulk_df_a2 = None
            file_source_name_a2 = None

            if uploaded_file_a2:
                file_source_name_a2 = uploaded_file_a2.name
                if st.session_state.bulk_uploaded_name != file_source_name_a2:
                    st.session_state.bulk_uploaded_name = file_source_name_a2
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None
                try:
                    if uploaded_file_a2.name.endswith("csv"):
                        bulk_df_a2 = pd.read_csv(uploaded_file_a2)
                    elif uploaded_file_a2.name.endswith("json"):
                        bulk_df_a2 = pd.read_json(uploaded_file_a2)
                    elif uploaded_file_a2.name.endswith("xlsx"):
                        bulk_df_a2 = pd.read_excel(uploaded_file_a2)
                    elif uploaded_file_a2.name.endswith("sql"):
                        content_a2 = uploaded_file_a2.read().decode("utf-8")
                        matches_a2 = re.findall(r"VALUES\s*\((.*?)\);", content_a2)
                        rows_a2 = [list(ast.literal_eval(f"({m})")) for m in matches_a2]
                        bulk_df_a2 = pd.DataFrame(rows_a2, columns=APP2_REQUIRED_COLUMNS)
                except Exception:
                    st.error("The uploaded file could not be processed. Please ensure it is a valid and properly formatted file.")
                    bulk_df_a2 = None

            elif drive_link_a2:
                direct_url_a2 = convert_drive_link(drive_link_a2)
                if direct_url_a2 is None:
                    st.error("Invalid Google Drive link. Please provide a valid public sharing link.")
                else:
                    drive_format_a2 = st.selectbox("Select format of Google Drive file",
                                                    ["CSV", "XLSX", "JSON", "SQL"],
                                                    key="drive_format_select_a2")
                    try:
                        with st.spinner("Downloading file from Google Drive..."):
                            response_a2 = requests.get(direct_url_a2, timeout=20)
                        if response_a2.status_code == 200:
                            content_a2 = response_a2.content
                            file_source_name_a2 = drive_link_a2
                            if st.session_state.bulk_uploaded_name != file_source_name_a2:
                                st.session_state.bulk_uploaded_name = file_source_name_a2
                                st.session_state.bulk_result_df = None
                                st.session_state.bulk_pdf_buffer = None
                            if drive_format_a2 == "CSV":
                                bulk_df_a2 = pd.read_csv(BytesIO(content_a2))
                            elif drive_format_a2 == "JSON":
                                bulk_df_a2 = pd.read_json(BytesIO(content_a2))
                            elif drive_format_a2 == "XLSX":
                                bulk_df_a2 = pd.read_excel(BytesIO(content_a2))
                            else:
                                text_c2 = content_a2.decode("utf-8")
                                matches_a2 = re.findall(r"VALUES\s*\((.*?)\);", text_c2)
                                rows_a2 = [list(ast.literal_eval(f"({m})")) for m in matches_a2]
                                bulk_df_a2 = pd.DataFrame(rows_a2, columns=APP2_REQUIRED_COLUMNS)
                        else:
                            st.error("Unable to download file from Google Drive. Please check file permissions.")
                    except Exception:
                        st.error("Error downloading or processing Google Drive file. Please verify the link and file format.")
                        bulk_df_a2 = None

            if bulk_df_a2 is not None:

                MAX_ROWS = 50000
                WARNING_ROWS = 10000

                row_count = len(bulk_df_a2)

                if row_count > MAX_ROWS:
                    st.error(f"File too large ({row_count} rows). Maximum allowed is {MAX_ROWS} rows.")
                    st.stop()
                elif row_count > WARNING_ROWS:
                    st.warning(f"Large file detected ({row_count} rows). Performance may be slower.")

                if bulk_df_a2 is not None:
                    is_valid_a2, validation_error_a2 = app2_validate_bulk_dataframe(bulk_df_a2)

                    if not is_valid_a2:
                        st.error(validation_error_a2)
                        bulk_df_a2 = None
                    else:
                        bulk_df_a2 = bulk_df_a2[APP2_REQUIRED_COLUMNS]
                        st.markdown("Uploaded File Preview:")
                        st.dataframe(bulk_df_a2.head(), width='stretch')

        with col3:
            st.subheader("Run Prediction")
            has_data_a2 = "bulk_df_a2" in locals() and bulk_df_a2 is not None
            if not has_data_a2:
                st.info("Upload a file or provide a public Google Drive link to generate batch salary predictions.")
            else:
                run_clicked_a2 = st.button("Run Batch Prediction", width='stretch', type="primary")
                if run_clicked_a2:
                    try:
                        with st.spinner("Running batch salary prediction..."):
                            tf_bulk_a2 = bulk_df_a2["job_title"].apply(title_features)
                            tf_bulk_a2 = pd.DataFrame(
                                tf_bulk_a2.tolist(),
                                columns=[
                                    "title_is_junior",
                                    "title_is_senior",
                                    "title_is_exec",
                                    "title_is_mgmt",
                                    "title_domain"
                                ]
                            )
                            prediction_df_a2 = bulk_df_a2.reset_index(drop=True).copy()
                            prediction_df_a2["remote_ratio"] = prediction_df_a2["remote_ratio"].astype(int)
                            prediction_df_a2 = pd.concat([prediction_df_a2, tf_bulk_a2], axis=1)
                            prediction_df_a2["exp_x_domain"] = (
                                prediction_df_a2["experience_level"].astype(str)
                                + "_"
                                + prediction_df_a2["title_domain"].astype(str)
                            )
                            preds_log_a2 = app2_model.predict(prediction_df_a2)
                            preds_usd_a2 = np.expm1(preds_log_a2)
                            result_df_a2 = bulk_df_a2.copy()
                            result_df_a2["Predicted Annual Salary (USD)"] = np.round(preds_usd_a2, 2)
                            st.session_state.bulk_result_df = result_df_a2
                    except Exception:
                        st.error("Prediction failed. Please ensure the uploaded data matches the required structure and values.")
                        st.session_state.bulk_result_df = None
                        st.session_state.bulk_pdf_buffer = None

                if st.session_state.bulk_result_df is not None:
                    st.markdown("Result Preview:")
                    st.dataframe(st.session_state.bulk_result_df.head(), width='stretch')
                    st.divider()
                    st.markdown("### Export Results")
                    export_format_a2 = st.selectbox("Select export format", ["CSV", "XLSX", "JSON", "SQL"],
                                                     key="export_format_select_a2")
                    result_df_a2 = st.session_state.bulk_result_df
                    export_df_a2 = result_df_a2.copy()
                    export_df_a2["Predicted Annual Salary (USD)"] = export_df_a2["Predicted Annual Salary (USD)"].round(2)
                    if export_format_a2 == "CSV":
                        file_data_e2 = export_df_a2.to_csv(index=False).encode("utf-8")
                        file_name_e2 = "salary_predictions.csv"
                        mime_e2 = "text/csv"
                    elif export_format_a2 == "JSON":
                        file_data_e2 = export_df_a2.to_json(orient="records")
                        file_name_e2 = "salary_predictions.json"
                        mime_e2 = "application/json"
                    elif export_format_a2 == "XLSX":
                        buffer_e2 = BytesIO()
                        export_df_a2.to_excel(buffer_e2, index=False)
                        file_data_e2 = buffer_e2.getvalue()
                        file_name_e2 = "salary_predictions.xlsx"
                        mime_e2 = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else:
                        sql_lines_e2 = [
                            "CREATE TABLE IF NOT EXISTS salary_predictions ("
                            "experience_level TEXT, employment_type TEXT, job_title TEXT, "
                            "employee_residence TEXT, remote_ratio INTEGER, "
                            "company_location TEXT, company_size TEXT, "
                            "predicted_annual_salary_usd REAL);"
                        ]
                        for _, row in export_df_a2.iterrows():
                            exp_l = str(row["experience_level"]).replace("'","''")
                            emp_t = str(row["employment_type"]).replace("'","''")
                            jt = str(row["job_title"]).replace("'","''")
                            er = str(row["employee_residence"]).replace("'","''")
                            cl = str(row["company_location"]).replace("'","''")
                            cs = str(row["company_size"]).replace("'","''")
                            rr = int(row["remote_ratio"])
                            ps = round(float(row["Predicted Annual Salary (USD)"]), 2)
                            sql_lines_e2.append(
                                "INSERT INTO salary_predictions "
                                "(experience_level, employment_type, job_title, employee_residence, "
                                "remote_ratio, company_location, company_size, predicted_annual_salary_usd) "
                                f"VALUES ('{exp_l}', '{emp_t}', '{jt}', '{er}', {rr}, '{cl}', '{cs}', {ps});"
                            )
                        file_data_e2 = "\n".join(sql_lines_e2)
                        file_name_e2 = "salary_predictions.sql"
                        mime_e2 = "text/sql"
                    st.download_button("Download File", data=file_data_e2,
                                       file_name=file_name_e2, mime=mime_e2, width='stretch')

        # Batch Analytics -- App 2
        if st.session_state.bulk_result_df is not None:
            @st.fragment
            def render_batch_analytics_a2():
                st.divider()
                st.header("Batch Prediction Analytics")

                if st.button("Prepare Batch PDF Report", width='stretch'):
                    with st.spinner("Preparing PDF report..."):
                        st.session_state.bulk_pdf_buffer = app2_generate_bulk_pdf(
                            st.session_state.bulk_result_df, COUNTRY_NAME_MAP
                        )
                if "bulk_pdf_buffer" in st.session_state and st.session_state.bulk_pdf_buffer is not None:
                    st.download_button(
                        label="Download Batch Prediction Summary (PDF)",
                        data=st.session_state.bulk_pdf_buffer,
                        file_name="bulk_salary_summary.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )
                st.divider()
                analytics_df_a2 = st.session_state.bulk_result_df

                st.subheader("Summary Metrics")
                avg_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].mean()
                min_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].min()
                max_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].max()
                std_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].std()
                std_s2 = 0 if pd.isna(std_s2) else std_s2
                col1c, col2c, col3c, col4c, col5c = st.columns(5)
                col1c.metric("Total Records", analytics_df_a2.shape[0])
                col2c.metric("Average Salary", f"${avg_s2:,.2f}")
                col3c.metric("Minimum Salary", f"${min_s2:,.2f}")
                col4c.metric("Maximum Salary", f"${max_s2:,.2f}")
                col5c.metric("Salary Std Deviation", f"${std_s2:,.2f}")

                st.divider()
                st.subheader("Top Salary Leaderboard")

                leaderboard_a2 = generate_salary_leaderboard(
                    df=analytics_df_a2,
                    job_col="job_title",
                    salary_col="Predicted Annual Salary (USD)"
                )
                st.dataframe(
                    leaderboard_a2,
                    width='stretch',
                    hide_index=True
                )

                st.caption(
                    "Ranks job roles by average predicted salary in the uploaded batch. "
                    "Top 3 roles are highlighted with medals."
                )
                st.divider()
                st.subheader("Salary Leaderboard Visualization")

                fig_lb_a2 = px.bar(
                    leaderboard_a2.head(10),
                    x="Average Salary (USD)",
                    y="Job Title",
                    orientation="h",
                    title="Top Roles by Salary",
                    color_discrete_sequence=["#60A5FA"]
                )
                fig_lb_a2.update_yaxes(categoryorder="total ascending")
                apply_theme(fig_lb_a2)
                st.plotly_chart(fig_lb_a2, width='stretch')

                st.divider()
                st.subheader("Predicted Salary Distribution")
                fig_hist_a2 = px.histogram(
                    analytics_df_a2, x="Predicted Annual Salary (USD)",
                    nbins=min(25, len(analytics_df_a2)),
                    title="Distribution of Predicted Annual Salaries",
                    labels={"Predicted Annual Salary (USD)": "Predicted Annual Salary (USD)"},
                    color_discrete_sequence=["#4F8EF7"]
                )
                fig_hist_a2.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
                fig_hist_a2.update_layout(xaxis_title="Predicted Annual Salary (USD)",
                                           yaxis_title="Number of Records")
                apply_theme(fig_hist_a2)
                st.plotly_chart(fig_hist_a2, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Experience Level")
                exp_group_a2 = (analytics_df_a2.groupby("experience_level")["Predicted Annual Salary (USD)"]
                                .mean().reset_index())
                exp_group_a2["Experience Level"] = exp_group_a2["experience_level"].map(EXPERIENCE_MAP)
                fig_exp_a2 = px.bar(
                    exp_group_a2, x="Experience Level", y="Predicted Annual Salary (USD)",
                    title="Average Predicted Annual Salary by Experience Level",
                    color="Experience Level",
                    labels={"Experience Level": "Experience Level",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                        color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA"]
                )
                fig_exp_a2.update_layout(xaxis_title="Experience Level",
                                          yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                fig_exp_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Entry Level",
                        "Mid Level",
                        "Senior Level",
                        "Executive Level"
                    ]
                )
                apply_theme(fig_exp_a2)
                st.plotly_chart(fig_exp_a2, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Company Size")
                size_group_a2 = (analytics_df_a2.groupby("company_size")["Predicted Annual Salary (USD)"]
                                 .mean().reset_index())
                size_group_a2["Company Size"] = size_group_a2["company_size"].map(COMPANY_SIZE_MAP)
                fig_size_a2 = px.bar(
                    size_group_a2, x="Company Size", y="Predicted Annual Salary (USD)",
                    title="Average Predicted Annual Salary by Company Size",
                    color="Company Size",
                    labels={"Company Size": "Company Size",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                    color_discrete_sequence=["#38BDF8","#4F8EF7","#A78BFA"]
                )
                fig_size_a2.update_layout(xaxis_title="Company Size",
                                           yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                fig_size_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Small Company",
                        "Medium Company",
                        "Large Company"
                    ]
                )
                apply_theme(fig_size_a2)
                st.plotly_chart(fig_size_a2, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Work Mode")
                remote_group_a2 = (analytics_df_a2.groupby("remote_ratio")["Predicted Annual Salary (USD)"]
                                   .mean().reset_index())
                remote_group_a2["Work Mode"] = remote_group_a2["remote_ratio"].map(REMOTE_MAP)
                fig_remote_a2 = px.bar(
                    remote_group_a2, x="Work Mode", y="Predicted Annual Salary (USD)",
                    title="Average Predicted Annual Salary by Work Mode",
                    color="Work Mode",
                    labels={"Work Mode": "Work Mode",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                    color_discrete_sequence=["#38BDF8","#4F8EF7","#34D399"]
                )
                fig_remote_a2.update_layout(xaxis_title="Work Mode",
                                             yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                apply_theme(fig_remote_a2)
                st.plotly_chart(fig_remote_a2, width='stretch')

                st.divider()
                st.subheader("Top Countries by Average Predicted Salary")
                country_group_a2 = (analytics_df_a2.groupby("company_location")["Predicted Annual Salary (USD)"]
                                    .mean().reset_index()
                                    .sort_values(by="Predicted Annual Salary (USD)", ascending=False)
                                    .head(10))
                country_group_a2["Country"] = country_group_a2["company_location"].map(
                    lambda x: COUNTRY_NAME_MAP.get(x, x))
                fig_country_a2 = px.bar(
                    country_group_a2, x="Country", y="Predicted Annual Salary (USD)",
                    title="Top Countries by Average Predicted Annual Salary",
                    color="Country",
                    labels={"Country": "Country",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B","#FB923C","#F472B6","#22D3EE","#818CF8","#6EE7B7"]
                )
                fig_country_a2.update_layout(xaxis_title="Country",
                                              yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                apply_theme(fig_country_a2)
                st.plotly_chart(fig_country_a2, width='stretch')

            render_batch_analytics_a2()