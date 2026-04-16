# SalaryScope — Software Requirements Specification (SRS)
**Version:** 1.1.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Author:** Yash Shah  
**Document Type:** Software Requirements Specification  
**Standard Reference:** IEEE 830-1998 (adapted)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [External Interface Requirements](#5-external-interface-requirements)
6. [System Constraints](#6-system-constraints)
7. [Assumptions and Dependencies](#7-assumptions-and-dependencies)
8. [Use Cases](#8-use-cases)
9. [Requirements Traceability Matrix](#9-requirements-traceability-matrix)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the functional and non-functional requirements for SalaryScope v1.1.0 — a machine learning-powered salary prediction web application. It serves as the authoritative reference for the features implemented, the constraints applied, and the behaviour expected from each system component.

### 1.2 Scope

SalaryScope is a browser-based application that predicts annual salaries using two independently trained machine learning models. It accepts user input via three modes (manual form, PDF resume upload, bulk file upload), provides supporting financial context tools, allows dataset and model performance exploration, supports a user account system backed by Firebase, and exposes an extensible Model Hub for deploying additional trained models without modifying application code.

The system is deployed on Streamlit Cloud as two separate applications — a full version including NLP-based resume analysis and a lite version without it — due to platform resource constraints.

### 1.3 Definitions and Abbreviations

| Term | Definition |
|---|---|
| App 1 / Model 1 | Random Forest Regressor trained on the general salary dataset |
| App 2 / Model 2 | XGBoost Regressor trained on the data science salaries dataset |
| CoL | Cost of Living |
| CTC | Cost to Company — the total annual compensation package |
| EMI | Equated Monthly Instalment — fixed monthly loan repayment |
| HuggingFace (HF) | Platform used for model and registry file storage |
| ISO-2 | ISO 3166-1 alpha-2 two-letter country code |
| NLP | Natural Language Processing |
| OHE | One-Hot Encoding |
| PPP | Purchasing Power Parity |
| RF | Random Forest |
| SHAP | SHapley Additive exPlanations — model explainability framework |
| Streamlit | Python framework for building interactive web applications |

### 1.4 References

- Streamlit Documentation — https://docs.streamlit.io
- Firebase Authentication REST API — https://firebase.google.com/docs/reference/rest/auth
- Firestore Documentation — https://firebase.google.com/docs/firestore
- HuggingFace Hub Documentation — https://huggingface.co/docs/huggingface_hub
- NIST SP 800-63B (2024) — Digital Identity Guidelines
- OWASP Authentication Cheat Sheet (2024)
- Scikit-learn Documentation — https://scikit-learn.org
- XGBoost Documentation — https://xgboost.readthedocs.io
- SHAP Documentation — https://shap.readthedocs.io

---

## 2. Overall Description

### 2.1 Product Perspective

SalaryScope is a standalone web application. It does not integrate with or replace any existing enterprise system. It consumes external services (Firebase Authentication, Firebase Firestore, HuggingFace Hub, ExchangeRate API) and makes them transparent to the end user.

### 2.2 Product Functions

At the highest level, SalaryScope provides:

- Salary prediction from manual inputs, resume PDFs, and bulk files.
- Post-prediction financial context (tax, CoL, CTC, take-home, savings, loans, investments).
- Model performance transparency through analytics dashboards.
- Dataset exploration through interactive EDA dashboards.
- An extensible Model Hub for admin-deployed additional models.
- A user account system with prediction history and account management.
- An admin panel for system monitoring and feedback analytics.

### 2.3 User Classes

| User Class | Description | Access Level |
|---|---|---|
| Anonymous User | Not logged in | Manual prediction, batch prediction, scenario analysis, model analytics, data insights, about tab |
| Registered User | Logged in with a verified account | All anonymous features + Model Hub (prediction), Profile tab (history, export, account management) |
| Admin User | Registered user whose email matches ADMIN\_EMAIL | All registered user features + Model Hub (upload, registry management, schema editor) + Admin Panel |

### 2.4 Operating Environment

- Platform: Any modern web browser (Chrome, Firefox, Edge, Safari)
- Deployment: Streamlit Cloud (Linux, Ubuntu 24)
- Python version: 3.13+
- No local installation required by the end user

### 2.5 Design and Implementation Constraints

- The application must run within Streamlit Cloud free-tier memory and compute limits.
- The full app (`app_resume.py`) and the lite app (`app.py`) must be maintained as separate deployments. The lite app is a substantially reduced version — it excludes Resume Analysis, Scenario Analysis, Model Hub, Admin Panel, all 11 financial tools, and the feedback system. It does not depend on spaCy, pdfplumber, or HuggingFace Hub. Only `FIREBASE_API_KEY` and `FIREBASE_SERVICE_ACCOUNT` are required secrets for the lite app.
- All persistent data must be stored in Firebase Firestore; SQLite is not persistent across Streamlit Cloud restarts.
- All secrets (API keys, Firebase credentials, HuggingFace token) must be managed through Streamlit Cloud secrets and never hardcoded.
- Model artefacts must be stored in a private HuggingFace dataset repository.
- The application must not use a shared in-process state for cross-session data (Streamlit Cloud isolates each user in a separate process).

---

## 3. Functional Requirements

### 3.1 Prediction Core

#### FR-P01 — Model Selection
The system shall provide a model selector that allows the user to choose between Model 1 (Random Forest, general salary) and Model 2 (XGBoost, data science salary). The selected model shall apply to all prediction tabs simultaneously.

#### FR-P02 — Manual Prediction (Model 1)
The system shall accept the following inputs for Model 1 manual prediction: Age (integer, 18–70), Years of Experience (float, 0–40), Education Level (0–3), Senior Position (0/1), Gender (Male/Female/Other), Job Title (from supported list), Country (from supported list or "Other"). The system shall validate that `Age - Years of Experience >= 18` before predicting.

#### FR-P03 — Manual Prediction (Model 2)
The system shall accept the following inputs for Model 2 manual prediction: Experience Level (EN/MI/SE/EX), Employment Type (FT/PT/CT/FL), Job Title (from DS/ML title list), Employee Residence (ISO-2 code), Remote Ratio (0/50/100), Company Location (ISO-2 code), Company Size (S/M/L).

#### FR-P04 — Prediction Output (Model 1)
After a successful Model 1 prediction, the system shall display: predicted annual salary in USD, monthly/weekly/hourly breakdowns, salary band classification (Early Career / Professional / Executive), career stage (Entry / Growth / Leadership), association rule pattern insight, confidence interval estimate, salary negotiation tips, and career recommendations.

#### FR-P05 — Prediction Output (Model 2)
After a successful Model 2 prediction, the system shall display: predicted annual salary in USD, monthly/weekly/hourly breakdowns, domain classification (ML/AI, Data Engineering, Analytics, Data Science), market comparison (above/below dataset average for the role and experience level), salary negotiation tips, and career recommendations.

#### FR-P06 — Prediction Persistence
If the user is logged in, each completed prediction shall be saved to Firestore under `predictions/{email}/records/{auto-id}` including the model used, all input fields as a JSON string, the predicted salary, and a UTC timestamp.

### 3.2 Resume Analysis

#### FR-R01 — PDF Upload
The system shall accept PDF file uploads in the Resume Analysis tab. Only PDF format shall be supported.

#### FR-R02 — Text Extraction
The system shall extract text from the uploaded PDF using pdfplumber and preprocess it with regex-based cleaning before NLP processing.

#### FR-R03 — Feature Extraction
The system shall extract the following features from the resume text using a hybrid NLP pipeline (spaCy PhraseMatcher + regex + rule-based matching): job title, years of experience, education level, country (App 1) or ISO-2 country code (App 2), and technical skills.

#### FR-R04 — Editable Feature Form
After extraction, the system shall display all extracted features in an editable form. The user shall be able to correct any incorrectly extracted value before proceeding to prediction.

#### FR-R05 — Resume Score
The system shall compute and display a resume score (out of 100) with component breakdowns for Experience (max 40), Education (max 35 for App 1), and Skills (max 25 for App 1) or DS/ML-weighted Skills (max 35) and Title Relevance (max 25) for App 2.

#### FR-R06 — Resume-Based Prediction
After reviewing the extracted features, the user shall be able to run a salary prediction using the same pipeline as manual prediction.

#### FR-R07 — Lite App Scope
The lite app deployment (`app.py`) shall include only the following tabs: Manual Prediction, Batch Prediction, Model Analytics, Data Insights, Profile, and About. The Resume Analysis, Scenario Analysis, Model Hub, and Admin Panel tabs shall not be present. The 11 financial planning tools, the prediction feedback system, and the HuggingFace Hub dependency shall be excluded from the lite app. The lite app's About tab shall be rendered inline with simplified content reflecting its reduced feature set.

### 3.3 Batch Prediction

#### FR-B01 — File Formats
The system shall support batch file uploads in CSV, XLSX, JSON, and SQL format. The system shall also accept a public Google Drive sharing link and resolve it to a downloadable file URL.

#### FR-B02 — Column Validation
The system shall validate that the uploaded file contains all required columns with correct names before attempting prediction. A detailed error message shall identify any missing or invalid columns.

#### FR-B03 — Batch Prediction Execution
The system shall run model predictions for each row in the validated file and produce an output dataframe containing all original input columns plus a Predicted Annual Salary column.

#### FR-B04 — Batch Size Limit
The system shall accept files with up to 50,000 rows. A warning shall be displayed for files above 10,000 rows regarding expected processing time.

#### FR-B05 — Batch Analytics Dashboard
After batch prediction, the system shall display: total records, average/minimum/maximum/standard deviation of predicted salaries, a salary leaderboard by job title, a salary distribution histogram, and breakdowns by experience level/company size/work mode/country (where applicable to the active model).

#### FR-B06 — Batch Export
The system shall allow export of batch prediction results in CSV, XLSX, JSON, and SQL format.

### 3.4 Scenario Analysis

#### FR-S01 — Scenario Configuration
The system shall allow the user to define up to 5 named salary prediction scenarios. Each scenario shall use the same input fields as the Manual Prediction form for the active model. Scenarios shall be pre-filled with sensible default values.

#### FR-S02 — Add and Remove Scenarios
The user shall be able to add scenarios up to the maximum of 5 and remove any individual scenario (minimum 1 must remain).

#### FR-S03 — Run All Scenarios
The system shall run predictions for all configured scenarios simultaneously on a single button click and display the results in a comparison table and a salary bar chart.

#### FR-S04 — Sensitivity Sweep
The system shall provide a sensitivity sweep section that varies one parameter (experience for App 1, experience level for App 2) across all possible values while holding all other inputs fixed for a selected baseline scenario, and displays the results as a line chart.

#### FR-S05 — Scenario Export
The user shall be able to export scenario results in CSV, XLSX, and JSON format.

### 3.5 Model Analytics

#### FR-A01 — Regression Model Metrics
The system shall display Test R², Cross-Validation R², MAE, and RMSE for the active prediction model.

#### FR-A02 — Model Comparison
The system shall display a comparison table and visualisation of all candidate models evaluated during training, with the selected model highlighted.

#### FR-A03 — Feature Importance
The system shall display feature importance for the active model. For Model 2, this shall include both grouped feature importance and SHAP analysis (top 15 features by mean absolute SHAP value).

#### FR-A04 — Residual Diagnostics
The system shall display residual analysis charts: predicted vs actual scatter plot and residual distribution histogram.

#### FR-A05 — Model 1 Classifier Metrics
For Model 1, the system shall additionally display salary band classifier metrics: accuracy, confusion matrix, classification report, and classifier model comparison.

#### FR-A06 — Model 1 Clustering Analytics
For Model 1, the system shall display KMeans clustering analytics: silhouette score, Davies-Bouldin score, PCA cluster visualisation, and cluster centre characteristics.

#### FR-A07 — Model 1 Association Rules
For Model 1, the system shall display Apriori association rule mining results: support, confidence, lift, and top rules by lift.

#### FR-A08 — Resume NLP Module Description
The system shall display a Resume NLP Module section in the Model Analytics tab describing the extraction pipeline, design rationale, and limitations. This section shall appear for both models.

#### FR-A09 — Analytics PDF Download
The system shall provide a downloadable PDF report of all model analytics for the active model.

### 3.6 Data Insights

#### FR-D01 — Dataset Dashboards
The system shall provide three collapsible interactive dashboards per model for exploring the training dataset. Each dashboard shall have independent filter controls and KPI tile summaries.

#### FR-D02 — App 1 Dashboards
For Model 1, the three dashboards shall cover: (1) salary landscape and distribution, (2) human capital dimensions (age, experience, education, gender), (3) geographic and role patterns.

#### FR-D03 — App 2 Dashboards
For Model 2, the three dashboards shall cover: (1) salary distribution by experience level and employment type, (2) work mode and company size interactions, (3) job roles and geographic salary patterns.

### 3.7 Model Hub

#### FR-H01 — Authentication Gate
The Model Hub tab shall require the user to be logged in. A warning message shall be displayed and the tab content shall be hidden for unauthenticated users.

#### FR-H02 — Active Model Listing
The system shall fetch the model registry from HuggingFace and display only models with `"active": true` in the user-facing model selector dropdown.

#### FR-H03 — Registry Caching
The registry shall be cached in session state with a 120-second TTL to avoid unnecessary network requests on every Streamlit rerun.

#### FR-H04 — Bundle Loading
When the user clicks Load Model, the system shall detect the bundle format automatically by probing for `model.onnx` in the bundle folder. If `model.onnx` is present, the system shall download `model.onnx` and `columns.json` and load the model via onnxruntime (no pickle deserialisation). If `model.onnx` is absent, the system shall fall back to downloading `model.pkl` and `columns.pkl` and loading via joblib. In both cases, `schema.json` shall be downloaded and any optional `aliases.json` merged into the schema before the form is rendered. `schema.json` and `aliases.json` shall always be fetched bypassing the local disk cache to reflect any in-place updates. The loaded bundle shall be cached in session state for the duration of the session.

#### FR-H05 — Dynamic Prediction Form
The system shall generate a Streamlit input form dynamically from the schema.json of the loaded model. Supported widget types are: slider, selectbox, number\_input, text\_input, checkbox. For selectbox fields with defined aliases, the dropdown shall display the alias labels to the user. The form shall return underlying model values (not display labels) to the prediction pipeline regardless of whether aliases are active. If the schema defines a `layout.columns` value of 2 or 3, the system shall render the form in a responsive multi-column grid using the per-field `row` and `col_span` keys. Schemas without these keys shall render in a single column, preserving the existing behaviour.

#### FR-H06 — Hub Prediction
The system shall build a feature vector from the form values aligned to columns.pkl ordering, handling direct column matches, OHE column expansion (sklearn get\_dummies convention), and zero-fill for unmatched columns. The system shall call `model.predict()` and display the scalar result.

#### FR-H07 — Admin Bundle Upload
Admin users shall be able to upload a new model bundle in either of two formats: ONNX (model.onnx + columns.json + schema.json) or Pickle (model.pkl + columns.pkl + schema.json). An optional `aliases.json` file may also be uploaded with either format. The system shall present a format selector in the upload UI. The system shall validate all files before uploading — for ONNX bundles this includes verifying that `model.onnx` loads cleanly via onnxruntime and that `columns.json` is a valid JSON string array. A unique versioned folder name shall be generated for each upload. The bundle format shall be recorded in the registry entry as `bundle_format`.

#### FR-H08 — Admin Registry Management
Admin users shall be able to activate or deactivate any model in the registry, and roll back to a previous version within a model family.

#### FR-H09 — Admin Schema Editor
Admin users shall have access to a visual schema editor for building schema.json files field-by-field, and an upload/validate tool for existing schema.json files.

#### FR-H10 — Schema-Only Update
Admin users shall be able to upload a new schema.json to an existing bundle path without re-uploading model.pkl or columns.pkl.

#### FR-H11 — Aliases Sidecar Support
The system shall support an optional `aliases.json` file in a bundle folder that provides display labels for selectbox model values. Admin users shall be able to upload or replace `aliases.json` for an existing bundle without re-uploading any other file. The aliases file shall be validated against the bundle's schema before upload.

#### FR-H12 — Currency Conversion in Hub
After a Model Hub prediction result is displayed, a currency conversion widget shall be shown if the currency utility module is available. The widget shall auto-detect a default currency from the prediction inputs when a country field is present.

#### FR-H13 — ONNX Bundle Format Support
The system shall support ONNX bundles (model.onnx + columns.json) as a secure alternative to pickle bundles (model.pkl + columns.pkl). Loading an ONNX bundle shall not involve pickle deserialisation. The loader shall detect the bundle format automatically from the files present in the bundle folder. Both formats shall be fully supported with no functional difference to the end user.

#### FR-H14 — Column-Based Form Layout
The schema.json format shall support optional top-level `layout.columns` (integer 1-3) and per-field `row` (integer) and `col_span` (integer 1-3) keys. When `layout.columns` is 2 or 3, the system shall render the prediction form in a multi-column grid. Fields sharing the same `row` value shall be placed side-by-side. All layout keys shall be optional; their absence shall result in single-column rendering identical to existing behaviour.

#### FR-H15 — Result Card Label Override
The schema.json format shall support an optional top-level `result_label` string key. When present, this string shall be used as the label on the prediction result card in place of the registry `target` field. When absent, the registry `target` field shall be used, preserving existing behaviour.

### 3.8 Financial Tools

#### FR-F01 — Currency Converter
The system shall convert the predicted salary to any of 100+ supported currencies using live exchange rates from open.er-api.com. Rates shall be cached in memory for 60 minutes. A fallback to a local rates file shall be used if the network is unavailable.

#### FR-F02 — Tax Adjuster
The system shall estimate post-tax annual salary using progressive tax bracket data for 40+ countries. The user shall be able to override the estimated effective rate with a custom rate.

#### FR-F03 — Cost-of-Living Adjuster
The system shall compute a PPP-equivalent salary for a user-selected comparison country using built-in CoL indices (US = 100 baseline, ~100 countries). The user shall be able to override either country's CoL index.

#### FR-F04 — CTC Breakdown
The system shall break down gross annual salary into estimated CTC components (base, HRA, bonus, PF, gratuity, allowances) using country-specific component rate tables.

#### FR-F05 — Take-Home Estimator
The system shall compute estimated monthly and annual net take-home salary after income tax, PF/pension, and statutory deductions using country-specific rates.

#### FR-F06 — Savings Estimator
The system shall estimate monthly and annual savings potential from net take-home income using country-level household expense ratios.

#### FR-F07 — Loan Affordability
The system shall estimate the maximum affordable loan using the standard reducing-balance EMI formula, country-typical interest rates, and standard lender EMI-cap norms. Interest rate, tenure, and EMI cap shall be adjustable via sliders.

#### FR-F08 — Budget Planner
The system shall break down monthly net income into recommended spending category allocations using country-adjusted envelope budgeting benchmarks.

#### FR-F09 — Investment Growth Estimator
The system shall project the future value of monthly savings under compound growth using country-adjusted expected return benchmarks for 5, 10, 20, and 30-year horizons.

#### FR-F10 — Emergency Fund Planner
The system shall estimate 3-month and 6-month emergency fund targets adjusted for country job-market stability, and compute months required to reach each target at the current savings rate.

#### FR-F11 — Lifestyle Budget Split
The system shall split discretionary income (net minus essentials) across lifestyle tiers (Basic, Comfortable, Premium) and spending categories using country-level cost benchmarks.

#### FR-F12 — Financial Tool Toggle
Each financial tool shall be independently toggleable via an on/off toggle control. Tools shall be collapsed by default and expand when toggled on.

### 3.9 Authentication and Account Management

#### FR-AC01 — Registration
The system shall allow users to register with an email address, a display name, and a password. Passwords shall be validated against the policy defined in FR-AC04 before account creation is attempted.

#### FR-AC02 — Email Verification
The system shall send a Firebase email verification link after registration. Login shall not be permitted until the email address has been verified. A pending verification UI with resend and check options shall be displayed to unverified users.

#### FR-AC03 — Login
The system shall authenticate users via the Firebase signInWithPassword REST endpoint. A session with a 24-hour expiry shall be created in st.session\_state upon successful login.

#### FR-AC04 — Password Policy
Passwords shall meet all of the following requirements: minimum 12 characters, maximum 128 characters, at least one uppercase letter, at least one lowercase letter, at least one digit, at least one special character, no leading or trailing whitespace, no run of 3 or more identical consecutive characters, and not appear in the common-password blocklist.

#### FR-AC05 — Rate Limiting
Login attempts shall be limited to 5 per 5 minutes per email. Registration attempts shall be limited to 3 per 10 minutes per email. Password reset, email resend, password change, and account deletion actions shall each be limited to 3 per 10 minutes per email. Rate limits shall be enforced via a two-layer system (session state + Firestore) and shall fail open on any error.

#### FR-AC06 — Forgot Password
The system shall accept an email address and trigger a Firebase password reset email. The system shall return the same generic success message regardless of whether the email exists, to prevent account enumeration.

#### FR-AC07 — Logout
The system shall destroy the session (clear all auth-related session state keys) and rerun the application on logout.

#### FR-AC08 — Password Change
Logged-in users shall be able to change their password by providing their current password (re-authenticated against Firebase) and a new password meeting the password policy.

#### FR-AC09 — Account Deletion
Logged-in users shall be able to permanently delete their account by providing their current password and typing the exact phrase "delete my account". On confirmation, the Firebase Authentication account and Firestore user document shall be deleted. Prediction history shall be retained in anonymised form.

### 3.10 User Profile

#### FR-PR01 — Prediction Summary
The Profile tab shall display total prediction count, average predicted salary, and most recent predicted salary as KPI metrics.

#### FR-PR02 — Prediction History Chart
The Profile tab shall display a scatter plot of up to 500 most recent predictions over time, colour-coded by model type.

#### FR-PR03 — Prediction History Table
The Profile tab shall display a tabular view of up to 500 most recent predictions showing model, predicted salary, and timestamp.

#### FR-PR04 — Input Detail View
The Profile tab shall allow the user to select any individual prediction from a dropdown and view the exact input values that produced it.

#### FR-PR05 — History Export
The Profile tab shall allow export of the full prediction history in CSV, XLSX, and JSON formats.

### 3.11 Feedback System

#### FR-FB01 — Feedback Form
After every manual prediction, a collapsible feedback form shall be displayed. Feedback shall not require login.

#### FR-FB02 — Core Feedback Fields
The feedback form shall collect: accuracy rating (Yes/Somewhat/No), prediction direction (Too High/About Right/Too Low), star rating (1–5), and optional actual salary in USD.

#### FR-FB03 — Extended Feedback
The feedback form shall provide an optional expanded section collecting cross-dataset bridge fields and compensation enrichment data for future model training purposes.

#### FR-FB04 — Feedback Persistence
Submitted feedback shall be stored in Firestore under `feedback/{auto-id}`. Anonymous submissions shall use the username value "anonymous".

#### FR-FB05 — Feedback Deduplication
The feedback form shall be keyed by model and predicted salary value within the current session to prevent accidental duplicate submissions.

### 3.12 Admin Panel

#### FR-AD01 — Access Control
The Admin Panel tab shall be visible only to the user whose email matches the ADMIN\_EMAIL secret. A "Access denied" error shall be displayed and execution halted for any other user who navigates to the tab.

#### FR-AD02 — System Diagnostics
The admin panel shall display: Python version, OS, architecture, deployment environment, active Streamlit session info, RAM usage (via psutil), and registered user count from Firestore.

#### FR-AD03 — Feedback Analytics
The admin panel shall provide on-demand aggregated feedback statistics: total feedback count, accuracy and direction breakdowns, average star rating, median actual salary, and per-model feedback counts, displayed with charts.

#### FR-AD04 — Recent Feedback
The admin panel shall provide on-demand display of the 5 most recent individual feedback records from Firestore.

#### FR-AD05 — Cache Management
The admin panel shall provide buttons to trigger Python garbage collection and to clear all Streamlit `@st.cache_data` caches.

#### FR-AD06 — Session Inspector
The admin panel shall display session state key counts grouped by category (admin, scenario, bulk, resume) and an option to display all session keys.

### 3.13 PDF Report Generation

#### FR-PDF01 — Report Types
The system shall generate downloadable PDF reports for: manual prediction, resume-based prediction, batch prediction, scenario analysis, and model analytics.

#### FR-PDF02 — Two-Step Download
For prediction-specific reports (manual, resume, batch, scenario), the system shall use a two-step pattern: a Prepare button generates the report and a Download button saves it. This prevents regeneration on every Streamlit rerun.

#### FR-PDF03 — Model Analytics PDF
The model analytics PDF shall be generated once using `@st.cache_data` and made available immediately as a download button without a separate prepare step.

#### FR-PDF04 — Page Numbering
All PDF reports shall include "Page X of Y" footers on every page.

---

## 4. Non-Functional Requirements

### 4.1 Performance

#### NFR-PE01
The application shall load all model artefacts and display the first tab within a reasonable time for a first-time load on Streamlit Cloud (expected 15–45 seconds depending on resource availability). Subsequent loads within the same session shall be faster due to `@st.cache_resource` caching.

#### NFR-PE02
Manual predictions shall return results within 3 seconds of the Predict button being clicked, excluding network latency.

#### NFR-PE03
Batch prediction for files under 1,000 rows shall complete within 10 seconds. Files between 1,000 and 10,000 rows shall complete within 60 seconds.

#### NFR-PE04
PDF generation for prediction-specific reports shall complete within 10 seconds.

#### NFR-PE05
Exchange rate fetching shall time out after 5 seconds. On timeout, the system shall fall back to a local rates file or display a warning.

### 4.2 Reliability

#### NFR-RE01
The rate limiter shall fail open on any Firestore or session state error — authentication failures shall never be caused by the rate limiter itself.

#### NFR-RE02
The currency converter shall fail gracefully when the exchange rate API is unreachable. The tool shall remain visible with a warning message; it shall not crash the page.

#### NFR-RE03
Financial tools shall degrade gracefully for countries not in their built-in data tables by using a defined generic fallback value.

#### NFR-RE04
The Model Hub registry fetch shall fail with a user-readable error message if HuggingFace is unreachable. The rest of the application shall remain functional.

### 4.3 Security

#### NFR-SE01
No passwords shall be stored in the application database. All password management shall be delegated to Firebase Authentication.

#### NFR-SE02
Firebase credentials (API key, service account JSON) shall be stored exclusively in Streamlit secrets and never appear in source code or logs.

#### NFR-SE03
The HuggingFace token shall be stored in Streamlit secrets and never logged or printed in application output.

#### NFR-SE04
Rate limits shall be enforced for all authentication actions (login, register, password reset, password change, account deletion, email resend) at both the session and Firestore layers.

#### NFR-SE05
The admin role shall be determined by email comparison only, using the ADMIN\_EMAIL secret. The check shall be case-insensitive.

#### NFR-SE06
Model Hub bundle uploads shall be restricted to the admin user. File size limits shall be enforced before upload (model.pkl ≤ 200 MB, columns.pkl ≤ 10 MB, schema.json ≤ 512 KB).

#### NFR-SE07
Rate limit documents in Firestore shall be keyed by SHA-256 hash prefix of the user email, not the email itself, to avoid storing PII in document IDs.

#### NFR-SE08
joblib bundle deserialisation in the Model Hub shall log a security notice at WARNING level on every load as an audit trail.

### 4.4 Usability

#### NFR-US01
The application shall render correctly and be fully usable on any modern desktop or mobile web browser without requiring installation of any software.

#### NFR-US02
All error messages shall be user-readable and specific. System-level exception tracebacks shall only be displayed in development/debug contexts, not as the primary error message.

#### NFR-US03
The tab structure shall be dynamically adjusted based on login status. Tabs for features requiring login (Profile, Model Hub) shall be either hidden or guarded with a clear login prompt.

#### NFR-US04
Financial tools shall be individually toggleable and collapsed by default to avoid overwhelming the user. Each tool shall include a clear disclaimer that results are estimates.

#### NFR-US05
All Streamlit widget keys across the application shall be unique to prevent key collision errors on re-render.

### 4.5 Maintainability

#### NFR-MA01
Each tab module shall expose a single `render_*()` function and accept all dependencies as parameters. No tab shall import from `app_resume.py` directly.

#### NFR-MA02
All financial utility modules shall follow the `compute_*() / render_*()` pattern, with the compute function having no Streamlit dependency, making it independently testable.

#### NFR-MA03
Country name and ISO-2 resolution shall be centralised in `country_utils.py`. No other module shall maintain its own country alias table.

#### NFR-MA04
The Model Hub schema parser (`schema_parser.py`) shall be the single point of schema-to-widget mapping. Adding a new UI widget type shall require changes only to `schema_parser.py` and `validator.py`.

#### NFR-MA05
All rollbackable features (email verification, password policy, rate limiter, extended feedback, change password, delete account) shall be tagged with rollback comments in source code for safe removal.

### 4.6 Scalability

#### NFR-SC01
The application architecture shall support the addition of a third or further prediction model by adding new model artefacts and a new `IS_APP*` flag in the entry point, without modifying any tab module.

#### NFR-SC02
The Model Hub shall support an unlimited number of admin-uploaded models without requiring any code changes.

#### NFR-SC03
Batch prediction shall support up to 50,000 input rows.

### 4.7 Data Integrity

#### NFR-DI01
Prediction records shall be stored as immutable documents in Firestore. No in-place update of a prediction record shall be performed.

#### NFR-DI02
Feedback records shall be stored as immutable documents. They shall never be deleted, even after account deletion.

#### NFR-DI03
Model Hub bundles shall be stored in uniquely named, timestamped folders. Existing bundles shall never be overwritten by a new upload.

---

## 5. External Interface Requirements

### 5.1 User Interfaces

The user interface is implemented entirely in Streamlit and rendered in the browser. There are no native mobile applications. The UI adapts to the browser window width using Streamlit's responsive layout system.

### 5.2 Hardware Interfaces

No special hardware is required. A standard device with a web browser and internet connection is sufficient.

### 5.3 Software Interfaces

| Service | Purpose | Protocol / SDK |
|---|---|---|
| Firebase Authentication REST API | User registration, login, email verification, password reset | HTTPS REST (Identity Toolkit v1) |
| Firebase Firestore (Admin SDK) | Persistent data storage | Firebase Admin Python SDK |
| HuggingFace Hub | Model artefact and registry storage/retrieval | huggingface\_hub SDK (v0.20+) |
| ExchangeRate API (open.er-api.com) | Live currency exchange rates | HTTPS REST (no key required) |
| spaCy (en\_core\_web\_sm) | NLP processing for resume analysis | Python library |
| scikit-learn | Random Forest model, KMeans clustering, HistGradientBoostingClassifier | Python library |
| XGBoost | XGBoost Regressor model | Python library |
| SHAP | Model explainability values | Python library |
| MLxtend | Apriori association rule mining | Python library |
| ReportLab | PDF report generation | Python library |
| pdfplumber | PDF text extraction for resume analysis | Python library |
| Plotly | Interactive charts throughout the application | Python library |
| Matplotlib | Chart generation for PDF reports | Python library |
| Babel | Country name resolution (CLDR territory data) | Python library |

### 5.4 Communications Interfaces

The application communicates with external services over HTTPS. All Firebase REST API calls and HuggingFace SDK calls are outbound from the Streamlit Cloud server. The user's browser communicates only with the Streamlit Cloud WebSocket endpoint.

---

## 6. System Constraints

### 6.1 Platform Constraints

- Streamlit Cloud free tier imposes memory limits that prevent running spaCy + pdfplumber in the same process as the full ML stack without risk of OOM errors on busy instances.
- Each user session runs in an isolated Python process on Streamlit Cloud; shared in-process state between users is not possible.
- Streamlit's execution model re-runs the entire script on every user interaction; all expensive operations must be guarded with `@st.cache_resource` or `@st.cache_data`.

### 6.2 Data Constraints

- Model predictions are capped at 500 records displayed in the Profile tab (Firestore query limit per page).
- Model Hub registry file is capped at 256 KB as a sanity guard.
- Feedback extended data collects at most 500 actual salary values in the admin feedback analytics aggregation.

### 6.3 Security Constraints

- joblib (pickle) deserialisation of Model Hub bundles is an inherent security risk. This risk is accepted and documented because upload is restricted to admin-controlled sources only.
- Firebase ID tokens expire; re-authentication is required for sensitive operations (password change, account deletion).

### 6.4 Licensing Constraints

- The application is released under the MIT License.
- All datasets used (Kaggle general salary, Kaggle data science salaries) are publicly available with Kaggle standard licences.
- External libraries are used under their respective open-source licences (Apache 2.0, MIT, BSD, etc.).

---

## 7. Assumptions and Dependencies

### 7.1 Assumptions

- The ExchangeRate API (open.er-api.com) remains freely available without authentication.
- Firebase Authentication and Firestore remain available as free-tier services sufficient for the expected user load.
- HuggingFace dataset repository storage remains available for the artefact files.
- The training datasets (Kaggle) accurately represent salary distributions at the time of training, acknowledging that they may not reflect current market conditions.
- Users accessing the application have a stable internet connection.

### 7.2 Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.13+ | Runtime |
| streamlit | Latest stable | Web framework |
| scikit-learn | Latest stable | Model 1 (Random Forest, classifier, KMeans) |
| xgboost | Latest stable | Model 2 |
| shap | Latest stable | Feature explainability |
| mlxtend | Latest stable | Association rule mining |
| spacy | Latest stable | NLP for resume analysis |
| en\_core\_web\_sm | Latest compatible | spaCy English model |
| pdfplumber | Latest stable | PDF text extraction |
| firebase-admin | Latest stable | Firestore access |
| huggingface\_hub | 0.20+ | Model storage |
| reportlab | Latest stable | PDF generation |
| plotly | Latest stable | Interactive charts |
| pandas | Latest stable | Data manipulation |
| numpy | Latest stable | Numerical operations |
| joblib | Latest stable | Model serialisation |
| onnxruntime | 1.18+ | ONNX model inference for Model Hub ONNX bundles |
| skl2onnx | 1.17+ | sklearn-to-ONNX conversion (used offline when preparing ONNX bundles) |
| babel | Latest stable | Country name resolution (CLDR) |
| bcrypt | Latest stable | Password hashing utility |
| psutil | Latest stable | Memory monitoring in admin panel |
| requests | Latest stable | HTTP calls to Firebase REST API and exchange rate API |

---

## 8. Use Cases

### UC-01 — Predict Salary Manually

**Actor:** Any user (logged in or anonymous)  
**Precondition:** Application is loaded and a model is selected.  
**Main Flow:**
1. User navigates to the Manual Prediction tab.
2. User fills in all required input fields.
3. User clicks Predict Salary.
4. System validates inputs.
5. System runs the prediction pipeline and displays results.
6. User optionally enables financial tools to explore the predicted salary further.
7. User optionally clicks Prepare PDF Report and downloads the report.
8. User optionally submits feedback via the feedback expander.

**Alternate Flow — Validation Error:**
- At step 4, if age minus years of experience is less than 18, the system displays an error and stops.

**Postcondition:** Prediction result is displayed. If logged in, the prediction is saved to Firestore.

---

### UC-02 — Predict Salary from Resume

**Actor:** Any user (full app only)  
**Precondition:** Application is loaded (full app), a model is selected.  
**Main Flow:**
1. User navigates to the Resume Analysis tab.
2. User uploads a PDF resume.
3. User clicks Extract Resume Features.
4. System extracts text, runs NLP pipeline, displays extracted features and resume score.
5. User reviews and optionally edits extracted features.
6. User clicks Predict Salary from Resume.
7. System runs prediction and displays results with financial tools and recommendations.
8. User optionally downloads a PDF report.

**Alternate Flow — Extraction Failure:**
- At step 4, if no readable text is found in the PDF, the system displays an error message.

---

### UC-03 — Run Batch Predictions

**Actor:** Any user  
**Precondition:** Application is loaded, a model is selected.  
**Main Flow:**
1. User navigates to the Batch Prediction tab.
2. User downloads the sample file to understand the required format.
3. User uploads a file (CSV/XLSX/JSON/SQL) or pastes a Google Drive link.
4. System validates the file and displays any errors.
5. User clicks Run Batch Prediction.
6. System runs predictions for all rows and displays the results table.
7. System displays the batch analytics dashboard.
8. User exports results in a chosen format.

---

### UC-04 — Compare Scenarios

**Actor:** Any user  
**Precondition:** Application is loaded, a model is selected.  
**Main Flow:**
1. User navigates to the Scenario Analysis tab.
2. User configures one or more named scenarios.
3. User clicks Run All Scenarios.
4. System runs predictions for all scenarios and displays the comparison table and charts.
5. User views the sensitivity sweep for a selected baseline scenario.
6. User exports results or downloads a PDF report.

---

### UC-05 — Register and Verify Account

**Actor:** New user  
**Main Flow:**
1. User clicks Register in the sidebar.
2. User provides display name, email, and password.
3. System validates password policy.
4. System calls Firebase signUp.
5. System sends a verification email via Firebase.
6. User checks inbox and clicks the verification link.
7. User returns to the application and clicks "I have verified my email".
8. System confirms verification and prompts user to log in.

**Alternate Flow — Password Policy Failure:**
- At step 3, if the password does not meet requirements, specific failure messages are displayed and registration is not attempted.

---

### UC-06 — Upload Model to Hub

**Actor:** Admin user  
**Precondition:** Admin is logged in.  
**Main Flow:**
1. Admin navigates to the Model Hub tab.
2. Admin scrolls to the Upload Bundle section.
3. Admin selects ONNX or Pickle format and uploads the corresponding files (model.onnx + columns.json or model.pkl + columns.pkl), schema.json, and fills in display name, description, target variable name.
4. System validates all files (size, format, schema structure, schema-column consistency; for ONNX, onnxruntime load verification).
5. System generates a unique folder name and uploads all files to HuggingFace. The bundle format is recorded in the registry entry.
6. System adds the new model entry to models\_registry.json and pushes it to HuggingFace.
7. System displays a success message with the generated model ID.

**Alternate Flow — Validation Failure:**
- At step 4, if any file fails validation, a detailed error message is displayed and no upload is performed.

---

## 9. Requirements Traceability Matrix

| Requirement ID | Description | Implemented In | Test Evidence |
|---|---|---|---|
| FR-P01 | Model selection | `app_resume.py` sidebar | Model selector visible; switching model changes tab behaviour |
| FR-P02 | Manual prediction inputs (Model 1) | `manual_prediction_tab.py` | Age-experience validation; all fields render correctly |
| FR-P03 | Manual prediction inputs (Model 2) | `manual_prediction_tab.py` | All Model 2 fields render; ISO codes accepted |
| FR-P04 | Prediction output (Model 1) | `manual_prediction_tab.py` | All output sections rendered after prediction |
| FR-P05 | Prediction output (Model 2) | `manual_prediction_tab.py` | Domain classification and market comparison displayed |
| FR-P06 | Prediction persistence | `database.py`, `manual_prediction_tab.py` | Prediction appears in Profile tab after login |
| FR-R01–FR-R07 | Resume analysis | `resume_analysis_tab.py`, `resume_analysis.py` | Upload, extract, edit, predict flow functional |
| FR-B01–FR-B06 | Batch prediction | `batch_prediction_tab.py` | File upload, validation, prediction, export verified |
| FR-S01–FR-S05 | Scenario analysis | `scenario_analysis_tab.py` | Up to 5 scenarios, sweep, export functional |
| FR-A01–FR-A09 | Model analytics | `model_analytics_tab.py` | All sections render; PDF downloadable |
| FR-D01–FR-D03 | Data insights | `data_insights_tab.py` | Three dashboards per model; filters functional |
| FR-H01–FR-H15 | Model Hub | `model_hub_tab.py`, `app/model_hub/*` | Auth gate, load (ONNX + pickle), predict, admin upload (ONNX + pickle), aliases, layout, result label, registry verified |
| FR-F01–FR-F12 | Financial tools | `app/utils/*_utils.py` | Each tool toggleable; output plausible for known inputs |
| FR-AC01–FR-AC09 | Authentication | `auth.py`, `account_management.py` | Registration, login, verification, rate limiting verified |
| FR-PR01–FR-PR05 | User profile | `user_profile.py` | History chart, table, export functional |
| FR-FB01–FR-FB05 | Feedback system | `feedback.py` | Feedback submitted and visible in Admin Panel |
| FR-AD01–FR-AD06 | Admin panel | `admin_panel.py` | All sections functional for admin user |
| FR-PDF01–FR-PDF04 | PDF reports | `pdf_utils.py` | All report types generate and download correctly |
| NFR-SE01–NFR-SE08 | Security requirements | `auth.py`, `rate_limiter.py`, `password_policy.py`, `model_hub_tab.py`, `loader.py` | No passwords in Firestore; rate limits enforced; audit log on bundle load |

---

*End of Software Requirements Specification*
