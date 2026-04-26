from app.theme import get_colorway, get_colorway_3_stages, get_token
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
from app.tabs.batch_prediction_dashboards import (
    render_batch_dashboards_app1,
    render_batch_dashboards_app2,
)


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
                render_batch_dashboards_app1(
                    analytics_df=st.session_state.bulk_result_df,
                    apply_theme=apply_theme,
                    get_plot_df=get_plot_df,
                    generate_salary_leaderboard=generate_salary_leaderboard,
                )
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
                render_batch_dashboards_app2(
                    analytics_df=st.session_state.bulk_result_df,
                    apply_theme=apply_theme,
                    generate_salary_leaderboard=generate_salary_leaderboard,
                    EXPERIENCE_MAP=EXPERIENCE_MAP,
                    COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
                    REMOTE_MAP=REMOTE_MAP,
                    COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
                )

            render_batch_analytics_a2()
