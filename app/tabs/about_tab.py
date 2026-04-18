"""
about_tab.py
------------
Renders the "About" tab for SalaryScope.

This module contains all static informational content about the application,
including:
- Overview and purpose of SalaryScope
- Model descriptions (Model 1 and Model 2)
- Features and modules
- Model Hub description (including extended prediction modes)
- Resume analysis details
- Scenario analysis and prediction workflow
- User account system and profile features
- Technologies used
- Tab guide and usage instructions
- Limitations and disclaimers

The content is UI-focused and self-contained, with no dependencies on model
logic or datasets. It is separated from the main app to improve readability,
maintainability, and modular structure.
"""
import streamlit as st

def render_about_tab():
    st.markdown("## About SalaryScope")

    st.markdown(
        "SalaryScope is a web application that predicts salary based on factors like "
        "education, experience, job title, and location. "
        "It uses machine learning models to give an estimated salary along with supporting insights. "
        "The application supports manual input, resume-based prediction, batch prediction, and scenario analysis. "
        "It is designed to help students and job seekers get a general idea of salary expectations. "
        "It includes post-tax estimation, cost-of-living adjustments, a full suite of financial planning tools, "
        "and a secure user account system. "
        "A Model Hub tab allows admins to upload additional trained models and make them available to "
        "logged-in users through a dynamically generated prediction interface, "
        "with four prediction modes available per model: Manual, Batch, Resume, and Scenario."
    )

    with st.expander(":material/widgets: Features & Modules"):

        col_ab1, col_ab2 = st.columns(2)

        with col_ab1:
            st.markdown("### Model 1 — General Salary (Random Forest)")
            st.markdown("""
**Dataset:** [General Salary Dataset (Kaggle)](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)

**Models:**
- Random Forest Regressor (optimized via GridSearchCV) for salary prediction
- HistGradientBoostingClassifier (optimized via GridSearchCV) for salary level classification
- KMeans Clustering for career stage segmentation (Entry, Growth, Leadership)
- Apriori Algorithm for association rule mining between career attributes and salary categories

**Input Features:**
- Age, Years of Experience, Education Level, Senior Position, Gender, Job Title, Country

**Salary Level Output:**
- Early Career Range (Low)
- Professional Range (Medium)
- Executive Range (High)

**Career Stage Output:**
- Entry Stage
- Growth Stage
- Leadership Stage

**Features:**
- Manual salary prediction with salary band and career stage classification
- Pattern insight generation using association rule mining (education, experience, job group, salary level)
- Salary negotiation tips tailored to experience, seniority, job title, and country
- Career recommendations based on job group and experience category
- Resume Analysis: upload a PDF resume to extract features using NLP (spaCy, PhraseMatcher) and predict salary automatically
- Resume scoring system with experience, education, and skills breakdown (scored out of 100)
- Detected skill extraction from resume text using a curated technical skill lexicon
- Batch salary estimation with salary level and career stage assignment per record
- Predicted vs Actual diagnostics
- Prediction confidence interval based on residual standard deviation from model evaluation
- Classification confusion matrix and feature importance
- Career stage clustering analytics (PCA visualization, silhouette score, Davies-Bouldin score)
- Association rule analytics (support, confidence, lift visualizations)
- Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries, salary levels, and career stages, and run sensitivity sweeps across experience and education
- Multi-format export (CSV, JSON, XLSX, SQL)
- Google Drive public link upload
- PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
- Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
- Currency conversion support (100+ currencies) with live exchange rates
- Basic post-tax salary estimation based on country-level tax systems
- Cost-of-living adjustment for cross-country salary comparison
- Real-world salary interpretation using combined financial adjustments
            """)

        with col_ab2:
            st.markdown("### Model 2 — Data Science Salary (XGBoost)")
            st.markdown("""
**Dataset:** [Data Science Salaries Dataset (Kaggle)](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)

**Model:**
- XGBoost Regressor with log-transformed target (`log1p(salary_in_usd)`)
- Custom feature engineering on job titles (seniority, domain, management signals)
- Interaction feature: experience level x job title domain

**Input Features:**
- Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

**Features:**
- Manual salary prediction with domain-aware smart insights and career recommendations
- Resume Analysis: upload a PDF resume to extract features using NLP and predict salary automatically
- Resume scoring system with experience, skills, and role relevance breakdown (scored out of 100)
- Batch salary estimation
- Feature importance
- Predicted vs Actual diagnostics
- Residual analysis
- Prediction uncertainty distribution
- Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries by experience level, company size, and work mode, and run sensitivity sweeps across experience levels and company sizes
- Multi-format export (CSV, JSON, XLSX, SQL)
- Google Drive public link upload
- PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
- Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
- Currency conversion support (100+ currencies) with live exchange rates
- Basic post-tax salary estimation based on country-level tax systems
- Cost-of-living adjustment for cross-country salary comparison
- Real-world salary interpretation using combined financial adjustments
            """)

        st.divider()

        st.markdown("### Model Hub")
        st.markdown("""
- Available to all logged-in users; upload and management controls are admin-only
- Two bundle formats supported: ONNX (model.onnx + columns.json, recommended) and Pickle (model.pkl + columns.pkl, legacy)
- ONNX bundles are loaded via onnxruntime with no arbitrary code execution on deserialisation
- Each upload creates a new versioned folder in a private HuggingFace dataset repo — existing bundles are never overwritten
- A registry file (`models_registry.json`) tracks all uploaded models, their active status, and bundle format
- Model Card metadata (intended use, limitations, metrics, training data, authors, links) can be attached at upload time and is displayed before loading
- Users see a dropdown of active models, a Model Card panel, and four prediction modes after loading a bundle

**Four prediction modes per loaded model:**
- **Manual** — fill in schema fields and predict a single result, shown using the same styled result card as the rest of the application
- **Batch** — upload a CSV or XLSX file (up to 10,000 rows), run predictions across all rows, and download results as CSV or XLSX with an auto-generated distribution chart; uploading a new file clears previous results automatically
- **Resume** — upload a PDF resume; features are extracted using NLP and pre-filled into an editable form for review before prediction; includes a resume quality score panel; uploading a new PDF clears previous results automatically
- **Scenario** — define up to 5 named scenarios, edit inputs directly without a save step, run all scenarios simultaneously, and compare results in a table and bar chart; an optional sensitivity sweep simulates how the prediction changes as one field varies across a range

**Schema system:**
- `schema.json` defines the input fields, their types, and the Streamlit widget to use (slider, selectbox, number_input, text_input, checkbox)
- Optional `layout` key enables multi-column form rendering (2 or 3 columns) using per-field `row` and `col_span` keys
- Optional `result_label` key overrides the prediction result card label
- Optional `plots` key declares charts to render automatically in the appropriate mode (gauge, bar, horizontal bar, scatter, histogram, line)
- Optional `scenario_sweep` key configures a sensitivity sweep in Scenario mode (continuous range or discrete values)
- Optional `aliases.json` sidecar provides human-readable display labels for selectbox model values
- Optional per-bundle `skills.json` and `job_titles.json` lexicons override global extraction defaults for resume analysis; falls back to the shared app-level lexicons when not provided

**Admin capabilities:**
- Upload ONNX or Pickle bundles with optional model card metadata, aliases, and custom lexicons
- Activate, deactivate, or roll back models from the Registry Manager
- Build or validate schema.json using the visual Schema Editor with layout and result label settings
- Push a replacement schema.json or aliases.json to an existing bundle without re-uploading the model
        """)

        st.divider()

        st.markdown("### Resume Analysis")
        st.markdown("""
- Available for both built-in models (Model 1 and Model 2) and all Model Hub models
- Upload a PDF resume to automatically extract structured features using NLP
- Text extraction via `pdfplumber`; feature extraction via `spaCy` with `PhraseMatcher` for skills, NER for countries, and regex for experience years
- Extraction engine is data-driven: skill phrases, job title aliases, education patterns, and country aliases are loaded from JSON lexicons that can be extended without code changes
- Model Hub models can supply their own per-bundle lexicons (`skills.json`, `job_titles.json`) which override the shared global lexicons for that specific model
- Detected skill coverage spans programming languages, data science, ML/AI, data engineering, MLOps, cloud platforms, mechanical and civil engineering, electrical and electronics, aerospace, chemical and process engineering, energy and environment, pharmaceutical and drug development, biotechnology and life sciences, neuroscience, mathematics and statistics, and cybersecurity
- Resume scoring out of 100 across three dimensions: experience (up to 40), education (up to 30), and skills (up to 30)
- Profile strength label: Basic, Moderate, or Strong
- Extraction quality panel showing auto-extracted field count, fields needing review, and per-field provenance (which extractor matched, what value was found)
- Extracted fields are fully editable before prediction
- Uploading a new PDF or switching models clears previous extraction results automatically; an explicit Clear button is also provided
        """)

        st.divider()

        st.markdown("### Salary Adjustment & Global Insights")
        st.markdown("""
        - Basic currency conversion using live exchange rates with fallback support
        - Basic tax estimation using country-level effective tax models
        - Cost-of-living adjustment using global indices (US = 100 baseline)
        - Enables realistic salary comparison across countries using purchasing power (PPP)
        - Modular design — can be applied independently or combined
        """)

        st.divider()

        st.markdown("### Financial Planning Tools")
        st.markdown("""
- 11 modular, toggle-based tools that operate on the predicted salary
- Post-tax estimator, CTC breakdown, take-home estimator, savings potential, loan affordability, budget planner, investment growth estimator, emergency fund planner, lifestyle budget split, cost-of-living adjuster, and currency converter
- Each tool uses country-specific data sourced from Numbeo, OECD, World Bank, and government portals
- Results are approximate estimates intended for planning purposes, not financial advice
        """)

        st.divider()

        st.markdown("### Prediction Feedback")
        st.markdown("""
- Available in the Manual Prediction tab for both models
- Appears as a collapsible expander after a prediction is generated
- Allows users to rate whether the prediction was accurate (Yes / Somewhat / No)
- Allows users to indicate the direction of error (Too High / About Right / Too Low)
- Star rating from 1 to 5 for overall prediction quality
- Optional field to enter actual or expected salary in USD
- Available to both logged-in and anonymous users
- Feedback is stored in Firestore under a separate `feedback/` collection alongside the prediction inputs and predicted salary
- Submission is one-time per prediction result within a session — the form is replaced by a confirmation message after submitting
        """)

        st.divider()

        st.markdown("### Scenario Analysis")
        st.markdown("""
- Available for both built-in models and all Model Hub models
- Build up to 5 fully customisable named scenarios in a single session
- Each scenario accepts the same inputs as manual prediction for the active model
- Input fields are plain widgets — no save step required before running; values are always current when Run All Scenarios is clicked
- Run all scenarios simultaneously with a single button click
- Side-by-side comparison table and horizontal bar chart showing predicted values per scenario
- For built-in Model 1: charts colored by salary level and career stage; salary confidence interval chart; experience vs salary bubble scatter; sensitivity sweep across 0-40 years experience; education level sweep across High School, Bachelor's, Master's, and PhD
- For built-in Model 2: charts colored by experience level, company size, and work mode; sensitivity sweep across four experience levels; company size sweep
- For Model Hub models: sweep field and mode (continuous range or discrete values) declared in schema.json via `scenario_sweep`
- Export scenario results in CSV format
        """)

        st.divider()

        st.markdown("### User Account System")
        st.markdown("""
        - Email and password registration and login via Firebase Authentication
        - Email verification required before full account access
        - User profile data stored in Firestore
        - Session management via Streamlit session state (per-browser, 24-hour expiry)
        - Password policy aligned with NIST SP 800-63B: minimum 12 characters, uppercase, lowercase, digit, special character, no consecutive identical characters, common-password blocklist
        - Two-layer rate limiting for all authentication actions (session-state layer + Firestore layer)
        - Secure password reset via email (Firebase OOB code system)
        - Account management: change password (with re-authentication), delete account (with confirmation)
        """)

        st.divider()

        st.markdown("### User Profile")
        st.markdown("""
- Prediction history stored per logged-in user in Firestore (model, inputs, salary, timestamp)
- Summary dashboard: total predictions, average salary, latest prediction
- Prediction history chart (scatter plot over time, colored by model)
- Per-prediction input detail viewer
- Export prediction history in CSV, XLSX, or JSON format
- Profile tab visible only when logged in
        """)

        st.divider()

        st.markdown("### Shared System Features")
        st.markdown("""
- Model switcher to toggle between both built-in prediction systems
- Unified theme across the entire application with dynamic light/dark mode support
- Dynamic tab layout: Manual Prediction, Resume Analysis, Batch Prediction, Scenario Analysis, Model Analytics, Data Insights, Model Hub, Profile (logged-in only), About
- ReportLab-based multi-page PDF reports with embedded charts
- State-managed UI to prevent re-computation on interaction
- Google Drive public link upload for batch files
- Predictions saved to Firestore for logged-in users
- Structured prediction feedback collected from all users and stored in Firestore
        """)

        st.divider()

        st.markdown("### Technologies Used")
        st.markdown("""
- Python 3.13
- Streamlit
- Pandas / NumPy
- Scikit-learn (Random Forest, HistGradientBoostingClassifier, KMeans, PCA, GridSearchCV)
- XGBoost
- MLxtend (Apriori association rule mining)
- spaCy (NLP for resume feature extraction — PhraseMatcher, NER)
- pdfplumber (PDF text extraction)
- Plotly / Matplotlib
- ReportLab (PDF generation)
- SHAP (SHapley Additive exPlanations for Model 2 feature importance)
- Firebase Authentication (user login and registration)
- Firebase Admin SDK / Firestore (user data, prediction storage, and feedback storage)
- HuggingFace Hub SDK (model bundle storage and retrieval for Model Hub)
- joblib (model serialization and deserialization for pickle bundles)
- onnxruntime (ONNX model inference for Model Hub ONNX bundles)
- Requests (cloud file retrieval)
- bcrypt (password hashing utility)
- Babel (Unicode CLDR territory data for country resolution)
        """)

    with st.expander(":material/menu_book: Tab Guide"):
        st.markdown("""
**Manual Prediction**
- Enter your profile details and click Predict Salary to get an instant salary estimate.
- Model 1 shows salary level, career stage, association pattern insight, negotiation tips, and career recommendations.
- Model 2 shows domain-aware smart insights, negotiation tips, and career recommendations.
- After results are shown, expand the Feedback section at the bottom to rate the prediction accuracy.

**Resume Analysis**
- Upload a PDF resume and click Extract to run NLP-based extraction.
- The quality panel shows how many fields were auto-extracted and which ones need review.
- Edit any pre-filled field if needed, then click Predict Salary from Resume.
- Upload a new PDF at any time — previous extraction results are cleared automatically.
- Click Clear to reset the tab manually between resumes.

**Batch Prediction**
- Upload a file (CSV, XLSX, JSON, or SQL) or paste a public Google Drive link to run predictions on multiple records at once.
- Download the sample file first to understand the required column format.
- After prediction, a batch analytics dashboard with charts and a salary leaderboard is displayed.
- Export results in your preferred format using the dropdown and download button.

**Scenario Analysis**
- Build up to 5 named scenarios using the same inputs as manual prediction.
- Edit inputs directly in each scenario panel — no save step is needed.
- Click Run All Scenarios to generate predictions for every scenario simultaneously.
- Review the comparison table, salary charts, and confidence interval ranges.
- Use the sensitivity sweep section to simulate how salary changes as experience or education varies.
- Click Clear Results to reset between runs.

**Model Analytics**
- Explore the performance and internals of the active model.
- Includes accuracy metrics, model comparison charts, feature importance, residual diagnostics, and prediction uncertainty.
- Model 1 additionally shows classifier metrics, clustering analytics, and association rule mining visualizations.

**Data Insights**
- Explore the dataset used to train the active model.
- Includes salary distributions and comparisons by education, experience, country, job role, company size, and work mode.

**Model Hub**
- Requires login to access.
- Select a model from the dropdown to view its Model Card, then click Load Model to download the bundle.
- Four modes are available after loading: Manual (single prediction), Batch (file upload), Resume (PDF extraction), and Scenario (multi-scenario comparison).
- In each mode, uploading a new file or PDF clears previous results automatically; a Clear button is also available.
- Admins additionally see an Upload Bundle panel with fields for model card metadata, optional lexicons, and aliases; a Registry Manager for activating and deactivating models; and a Schema Editor for building or validating schema.json files.

**Profile**
- Visible only when logged in.
- Shows your prediction history, summary statistics, and a timeline chart.
- Allows export of your full prediction history in CSV, XLSX, or JSON format.

**About**
- Describes the application, its models, features, and technologies.
- Contains the Tab Guide, Usage Instructions, and Limitations for reference.
        """)

    with st.expander(":material/help: Usage Instructions"):
        st.markdown("""
**Getting Started**
- Select a prediction model from the dropdown at the top: Model 1 (Random Forest) for general salary prediction, or Model 2 (XGBoost) for data science roles.
- The active model applies across all tabs except Model Hub, which has its own independent model selector.

**Manual Prediction**
- Fill in all input fields in the Manual Prediction tab.
- Click **Predict Salary** to generate results.
- Scroll down to view salary level, career stage, pattern insight, negotiation tips, and recommendations.
- Click **Prepare PDF Report** to generate a downloadable summary, then click **Download** to save it.
- To share feedback, expand the **Share Feedback on This Prediction** section, fill in the fields, and click **Submit Feedback**. Login is not required.
- Optionally enable currency conversion, tax adjustment, and cost-of-living comparison for real-world context.

**Resume Analysis**
- Go to the Resume Analysis tab and upload a PDF resume.
- Click **Extract** (or **Extract Resume Features** in the built-in tab) to run NLP extraction.
- Review the extraction quality panel and edit any pre-filled field if the extracted value looks wrong.
- Click **Predict Salary from Resume** to get results.
- Upload a new PDF at any time to restart — previous results clear automatically.
- After prediction, you can apply currency conversion, tax estimation, and cost-of-living adjustment.

**Batch Prediction**
- Download the sample file from the left column to understand the required format.
- Upload your file or paste a public Google Drive sharing link.
- Click **Run Batch Prediction** (or **Run** in the Model Hub batch mode) to process all records.
- Export results in your preferred format using the download buttons.

**Scenario Analysis**
- Go to the Scenario Analysis tab after selecting your model.
- Each scenario panel shows all input fields — edit them directly, no save step needed.
- Click **Add Scenario** to add more (up to 5) or **Remove** to delete one.
- Click **Run All Scenarios** to predict salaries for all scenarios at once.
- Scroll down to view the comparison table, salary charts, and sensitivity sweeps.
- Click **Clear Results** to reset between runs.
- Use the export button to save scenario results as CSV.

**Model Hub**
- Log in first — the tab requires authentication.
- Select a model from the dropdown and review the Model Card for information about the model.
- Click **Load Model** to download the bundle from HuggingFace. This only needs to be done once per session.
- Choose a prediction mode from the tabs: Manual, Batch, Resume, or Scenario.
- In Batch mode, upload a CSV or XLSX file whose columns match the schema field names shown in the guide, then click **Run**. Click **Clear** to reset between uploads.
- In Resume mode, upload a PDF and click **Extract**. Review and edit the extracted fields, then click **Predict from Resume**. Click **Clear** to reset between resumes.
- In Scenario mode, fill in each scenario panel directly and click **Run All Scenarios**.
- If you are an admin, the Upload Bundle, Registry Manager, and Schema Editor sections are visible below the prediction panel.

**Account (Optional)**
- Register or log in from the sidebar to save predictions.
- Logged-in users can view their full prediction history in the Profile tab.
- Sessions expire after 24 hours and require re-login.

**Google Drive Upload**
- Set the file sharing permission to "Anyone with the link can view" before pasting the link.
- Select the correct file format from the dropdown after pasting the link.
        """)

    with st.expander(":material/warning: Limitations"):
        st.markdown("""
- The models are trained on limited datasets, so predictions may not always match real-world salaries.
- Some job roles, countries, or inputs may not be fully covered in the dataset.
- Resume analysis depends on text extraction quality and may not work properly for image-based, scanned, or heavily formatted PDFs. ATS-friendly, text-selectable PDFs extract best.
- Extraction heuristics (experience years, education level, country, job title) are rule-based and may miss edge cases in unconventional resume layouts.
- Predictions are based on past data and do not consider current market trends or company-specific salaries.
- Scenario Analysis results are generated by the same underlying model as manual prediction and carry the same limitations.
- The results should be used only as an estimate, not as an exact salary value.
- Feedback submitted anonymously cannot be linked to a specific user session and is stored as-is without any personal identifier.
- Currency conversion uses publicly available exchange rates and may not reflect real-time market fluctuations or transaction rates.
- Tax estimation is based on simplified models and approximate effective rates; it does not account for deductions, filing status, or local regulations.
- Cost-of-living adjustments use country-level indices and may not accurately represent city-level variations or individual lifestyle differences.
- Combined salary adjustments (tax, currency, cost of living) are indicative and should be interpreted as general estimates rather than precise financial outcomes.
- Model Hub ONNX bundles (model.onnx) are loaded via onnxruntime and carry no arbitrary code execution risk. Pickle bundles (model.pkl) are deserialized using joblib — only upload pickle files from sources you control entirely.
- Model Hub predictions are only as reliable as the model and training data used — the system does not validate model quality or dataset coverage.
- Per-bundle lexicons (skills.json, job_titles.json) in the Model Hub override global lexicons for resume extraction; if not uploaded, the shared app-level lexicons are used as fallback.
        """)