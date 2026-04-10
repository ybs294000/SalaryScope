# Software Requirements Specification (SRS)

## SalaryScope — Salary Prediction System using Machine Learning

---

| Field | Details |
|---|---|
| **Document Title** | Software Requirements Specification |
| **Project Name** | SalaryScope |
| **Version** | 1.0 |
| **Author** | Yash Shah |
| **Institution** | Gandhinagar Institute of Technology, Gandhinagar University |
| **Department** | Computer Engineering |
| **Submission Type** | Final Year B.Tech Project |
| **Date** | April 2026 |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [External Interface Requirements](#5-external-interface-requirements)
6. [System Constraints](#6-system-constraints)
7. [Assumptions and Dependencies](#7-assumptions-and-dependencies)
8. [Appendix](#8-appendix)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) document describes the complete functional and non-functional requirements for **SalaryScope**, a machine learning-powered salary prediction web application. This document is intended for use by the developer, academic evaluators, and any future contributors who wish to extend or maintain the system.

### 1.2 Scope

SalaryScope is a browser-based web application that allows users to predict annual salaries based on professional profile data. The system provides:

- Two distinct ML-based salary prediction models targeting different professional domains
- NLP-driven resume parsing and automatic salary estimation
- Batch prediction for large datasets
- Scenario analysis and sensitivity simulation
- Financial context tools (currency conversion, tax estimation, cost-of-living adjustment)
- User authentication, prediction history, and feedback collection
- Downloadable PDF analytics and prediction reports

The system is deployed on Streamlit Community Cloud and does not require any local installation by the end user beyond a modern web browser.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|---|---|
| SRS | Software Requirements Specification |
| ML | Machine Learning |
| NLP | Natural Language Processing |
| RF | Random Forest |
| XGBoost | Extreme Gradient Boosting |
| UI | User Interface |
| API | Application Programming Interface |
| COL | Cost of Living |
| PDF | Portable Document Format |
| MAE | Mean Absolute Error |
| RMSE | Root Mean Square Error |
| R² | Coefficient of Determination |
| SHAP | SHapley Additive exPlanations |
| Firestore | Google Firebase Firestore (cloud NoSQL database) |
| USD | United States Dollar |

### 1.4 References

- Python 3.13 Documentation: https://docs.python.org/3/
- Streamlit Documentation: https://docs.streamlit.io
- Scikit-learn Documentation: https://scikit-learn.org
- XGBoost Documentation: https://xgboost.readthedocs.io
- Firebase Documentation: https://firebase.google.com/docs
- SHAP Documentation: https://shap.readthedocs.io
- Kaggle — [Salary by Job Title and Country Dataset](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)
- Kaggle — [Data Science Salaries 2023 Dataset](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)

### 1.5 Overview

Section 2 provides an overall description of the system, its context, and its users. Section 3 details functional requirements organized by feature area. Section 4 covers non-functional requirements including performance, security, and usability. Section 5 describes external interfaces. Sections 6 and 7 cover constraints and assumptions.

---

## 2. Overall Description

### 2.1 Product Perspective

SalaryScope is a standalone web application developed as a Final Year B.Tech project. It integrates pre-trained machine learning models, a Firebase backend for authentication and storage, and a Streamlit frontend into a unified, browser-accessible system. It is not a component of a larger existing system.

The application is deployed in two variants:
- **Full App** (`app_resume.py`): Includes all features including spaCy-based NLP resume analysis.
- **Lite App** (`app-lite.py`): A lightweight version without the resume analysis module, suited for resource-constrained deployment environments.

### 2.2 Product Functions

At a high level, SalaryScope provides the following core capabilities:

- **Salary Prediction**: Predict annual salary using structured input via two ML models
- **Resume-Based Prediction**: Extract professional features from a PDF resume and use them for prediction
- **Batch Prediction**: Upload datasets of up to 50,000 records and generate predictions in bulk
- **Scenario Analysis**: Compare up to 5 hypothetical professional profiles side-by-side
- **Financial Adjustment Tools**: Convert predicted salary to other currencies, estimate post-tax income, and apply cost-of-living adjustments
- **Model Analytics**: Inspect model internals, performance metrics, and training data distributions
- **User Management**: Register/login, save prediction history, and review past predictions
- **Admin Panel**: Diagnostics, system monitoring, and feedback analytics for administrators
- **PDF Report Generation**: Export results of any major prediction or analytics view as a formatted PDF

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Level |
|---|---|---|
| **Anonymous User** | Uses prediction and feedback features without registering | Non-technical |
| **Registered User** | Logged-in user with prediction history and profile access | Non-technical |
| **Administrator** | Special-access user with access to diagnostics and feedback analytics | Technical |
| **Developer** | Extends or maintains the codebase locally | Technical |

### 2.4 Operating Environment

- **Deployment**: Streamlit Community Cloud (Linux/Debian environment)
- **Client**: Any modern web browser (Chrome, Firefox, Edge recommended)
- **Development Environment**: Python 3.13, Windows 11 (developed), Ubuntu 24.04 LTS (tested)
- **Database**: Google Firebase Firestore (cloud-hosted)
- **Authentication**: Firebase Authentication

### 2.5 Design and Implementation Constraints

- The application is limited by Streamlit Community Cloud free-tier memory and CPU constraints.
- The NLP-based resume module (spaCy) is resource-intensive and is deployed separately from the lite version.
- All ML models are pre-trained and loaded at runtime as `.pkl` files; real-time training is not supported.
- Firebase credentials must be provided via `.streamlit/secrets.toml` and must never be committed to version control.
- Session state is per-browser and non-persistent across sessions by design.

### 2.6 Assumptions and Dependencies

- The user has a stable internet connection to access the deployed application.
- Firebase services (Authentication and Firestore) are available and properly configured.
- The exchange rate API (`open.er-api.com`) is reachable for live currency conversion; a local fallback file is used if it is not.
- The spaCy language model (`en_core_web_sm` or similar) is installed in the deployment environment.

---

## 3. Functional Requirements

### 3.1 Model Selection

**FR-MS-01**: The system shall provide a model selector at the top of the application, allowing the user to switch between Model 1 (Random Forest — General Salary) and Model 2 (XGBoost — Data Science Salary).

**FR-MS-02**: The active model selection shall persist across all tabs within a single session.

**FR-MS-03**: Input forms, result displays, analytics views, and PDF reports shall dynamically adapt to reflect the active model.

---

### 3.2 Manual Prediction

**FR-MP-01**: The system shall provide an input form with fields appropriate to the active model.

- *Model 1 fields*: Age, Years of Experience, Education Level, Senior Position, Gender, Job Title, Country
- *Model 2 fields*: Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

**FR-MP-02**: Upon clicking "Predict Salary", the system shall output the predicted annual salary in USD.

**FR-MP-03**: The system shall display salary breakdowns: monthly, weekly, and hourly estimates.

**FR-MP-04** *(Model 1 only)*: The system shall display a salary level classification (Early Career / Professional / Executive Range).

**FR-MP-05** *(Model 1 only)*: The system shall display a career stage segmentation (Entry / Growth / Leadership Stage) derived from KMeans clustering.

**FR-MP-06** *(Model 1 only)*: The system shall display an association rule-based pattern insight relevant to the input profile.

**FR-MP-07**: The system shall display negotiation tips and career recommendations after prediction.

**FR-MP-08** *(Model 1 only)*: The system shall display a 95% salary confidence interval based on training residuals.

**FR-MP-09**: The system shall allow the user to download a PDF report summarizing the prediction and all displayed outputs.

**FR-MP-10**: The system shall display a feedback form (collapsible) after each prediction result, available to all users regardless of login status.

---

### 3.3 Resume-Based Prediction

**FR-RP-01**: The system shall allow the user to upload a PDF resume file.

**FR-RP-02**: Upon clicking "Extract Resume Features", the system shall use NLP (spaCy + regex) to automatically extract the following fields from the uploaded resume:
- Job Title
- Years of Experience
- Skills
- Education Level
- Country

**FR-RP-03**: Extracted fields shall be displayed in editable form controls, allowing the user to correct any extraction errors before running prediction.

**FR-RP-04**: The system shall compute and display a resume score based on experience level, education level, and identified skills count.

**FR-RP-05**: Upon clicking "Predict Salary from Resume", the system shall use the extracted (and potentially edited) features to run the selected model's prediction pipeline.

**FR-RP-06**: Results shall include all outputs applicable to the active model (salary, level, career stage, pattern insight, negotiation tips, recommendations).

**FR-RP-07**: The system shall allow the user to download a PDF report of the resume-based prediction result.

**FR-RP-08**: Resume Analysis shall be available for both Model 1 and Model 2.

---

### 3.4 Batch Prediction

**FR-BP-01**: The system shall accept batch input files in the following formats: CSV, XLSX, JSON, SQL.

**FR-BP-02**: The system shall accept a public Google Drive file sharing link as an alternative to direct file upload.

**FR-BP-03**: The system shall validate the uploaded file against required column specifications and display detailed error messages for any violations.

**FR-BP-04**: The system shall support batch files of up to 50,000 rows.

**FR-BP-05**: The system shall provide a downloadable sample file illustrating the required input format for the active model.

**FR-BP-06**: After running batch prediction, the system shall display a full analytics dashboard including:
- Salary distribution charts
- Summary statistics per category
- A salary leaderboard

**FR-BP-07**: The system shall allow export of batch prediction results in CSV, XLSX, JSON, or SQL format.

**FR-BP-08**: The system shall allow download of a PDF batch analytics report.

---

### 3.5 Scenario Analysis

**FR-SA-01**: The system shall allow users to define between 1 and 5 named prediction scenarios within a single session.

**FR-SA-02**: Each scenario shall accept the same input fields as the Manual Prediction tab for the active model.

**FR-SA-03**: Each scenario shall be pre-populated with sensible default values.

**FR-SA-04**: The user shall be able to add or remove individual scenarios up to the defined limit.

**FR-SA-05**: Upon clicking "Run All Scenarios", the system shall generate predictions for all defined scenarios simultaneously.

**FR-SA-06**: The system shall display a side-by-side comparison table showing at minimum: predicted salary, salary level, and career stage (Model 1) or experience level, company size, and work mode (Model 2) for each scenario.

**FR-SA-07**: The system shall display a bar chart comparing predicted annual salaries across all scenarios.

**FR-SA-08** *(Model 1 only)*: The system shall display a salary confidence interval chart showing 95% lower and upper bounds per scenario.

**FR-SA-09** *(Model 1 only)*: The system shall display an Experience vs. Salary bubble scatter plot across all scenarios.

**FR-SA-10**: The system shall provide a sensitivity sweep that simulates salary change across:
- Continuous experience range 0–40 years (Model 1), with all other inputs from a selected baseline scenario held fixed
- All four experience levels (Model 2), with all other inputs from a selected baseline scenario held fixed

**FR-SA-11** *(Model 1 only)*: The system shall provide an education level sweep (High School → Bachelor's → Master's → PhD) for a selected baseline scenario.

**FR-SA-12** *(Model 2 only)*: The system shall provide a company size sweep (Small → Medium → Large) for a selected baseline scenario.

**FR-SA-13**: The system shall allow export of scenario results in CSV, XLSX, or JSON format.

---

### 3.6 Financial Adjustment Tools

**FR-FA-01 — Currency Conversion**: The system shall allow the user to toggle currency conversion and select from 100+ global currencies, converting the predicted salary (base: USD) into the selected currency with annual, monthly, weekly, and hourly breakdowns.

**FR-FA-02**: Exchange rates shall be fetched from `open.er-api.com`. If the API is unavailable, the system shall fall back to a local JSON file. If the local file is also unavailable, the system shall use built-in approximate rates.

**FR-FA-03**: Exchange rates shall be cached in memory for approximately 60 minutes to reduce redundant API calls.

**FR-FA-04 — Tax Estimation**: The system shall allow the user to enable post-tax salary estimation based on country-specific approximate effective tax rates or a custom tax rate input.

**FR-FA-05**: The tax estimation display shall include: estimated tax amount, net annual salary, and monthly/weekly/hourly breakdowns post-tax.

**FR-FA-06 — Cost of Living Adjustment**: The system shall allow the user to enable COL adjustment, which normalizes the predicted salary based on the relative cost-of-living index for the selected country.

**FR-FA-07**: Currency conversion, tax estimation, and COL adjustment shall each be independently togglable and shall not modify the original USD prediction value.

---

### 3.7 Model Analytics

**FR-MA-01**: The Model Analytics tab shall display the following for the active model:
- Regression metrics: R², MAE, RMSE
- Model comparison table and bar chart
- Feature importance visualization
- Predicted vs. Actual scatter plot
- Residual analysis and distribution
- Prediction uncertainty distribution

**FR-MA-02** *(Model 1 only)*: Additional analytics shall include:
- Confusion matrix for the salary level classifier
- Classification model comparison
- Career stage clustering analytics with PCA visualization
- Association rule mining analytics (support, confidence, lift)

**FR-MA-03** *(Model 2 only)*: Additional analytics shall include:
- SHAP-based grouped feature importance visualization

**FR-MA-04**: The system shall allow download of a PDF model analytics report.

---

### 3.8 Data Insights

**FR-DI-01**: The Data Insights tab shall present exploratory analysis of the training dataset used by the active model.

**FR-DI-02**: Visualizations shall include at minimum: salary distributions, and salary breakdowns by education, experience, seniority, country, and job title.

**FR-DI-03**: Charts shall include trend lines and box plots where appropriate.

---

### 3.9 User Authentication

**FR-AU-01**: The system shall provide registration functionality using email and password via Firebase Authentication.

**FR-AU-02**: The system shall provide login functionality for registered users.

**FR-AU-03**: Sessions shall be stored via Streamlit session state and shall expire after 24 hours.

**FR-AU-04**: The system shall provide a logout function accessible from the sidebar.

**FR-AU-05**: All core prediction features shall be accessible without authentication. Authentication gates only the Profile tab and prediction history storage.

---

### 3.10 User Profile

**FR-UP-01**: The Profile tab shall be visible only to logged-in users.

**FR-UP-02**: The system shall store each prediction made by a logged-in user (model used, inputs, predicted salary, timestamp) in Firestore.

**FR-UP-03**: The profile dashboard shall display: total predictions made, average predicted salary, and the most recent prediction.

**FR-UP-04**: The system shall display a prediction history chart (scatter plot over time, colored by model).

**FR-UP-05**: The user shall be able to view the full input details of any individual past prediction.

**FR-UP-06**: The system shall allow export of full prediction history in CSV, XLSX, or JSON format.

---

### 3.11 Prediction Feedback

**FR-PF-01**: After any manual prediction result, the system shall display a collapsible feedback form accessible to all users (logged-in and anonymous).

**FR-PF-02**: The feedback form shall collect:
- Accuracy rating (Yes / Somewhat / No)
- Direction (Too High / About Right / Too Low)
- Star rating (1–5)
- Optional actual or expected salary in USD

**FR-PF-03**: Feedback shall be stored in Firestore under a dedicated `feedback/` collection, separate from prediction history.

**FR-PF-04**: The system shall allow at most one feedback submission per prediction result per session.

**FR-PF-05** *(Extended Feedback)*: An optional extended feedback form shall collect additional real-world data including compensation structure, skills, industry context, role details, and work conditions, stored under an `extended_data` field.

---

### 3.12 Admin Panel

**FR-AP-01**: The admin panel shall be accessible only to users whose accounts have admin privileges (verified via internal admin check).

**FR-AP-02**: The admin panel shall display system information: OS, architecture, Python version, and deployment environment.

**FR-AP-03**: The admin panel shall display Firebase project configuration status and user count.

**FR-AP-04**: The admin panel shall display feedback analytics: total feedback count, accuracy distribution, average rating, direction trends, model-wise breakdown, and median actual salary.

**FR-AP-05**: The admin panel shall allow viewing of the most recent feedback entries with prediction details.

**FR-AP-06**: The admin panel shall display RAM usage and allow manual garbage collection and cache clearing.

**FR-AP-07** *(Local environment only)*: The admin panel shall display extended diagnostics including CPU, disk, network metrics, Python environment, and installed package status.

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-PE-01**: Single manual predictions shall complete and display results within 3 seconds under normal network conditions.

**NFR-PE-02**: Batch prediction of up to 1,000 records shall complete within 10 seconds; up to 50,000 records within 5 minutes.

**NFR-PE-03**: Exchange rates shall be cached for approximately 60 minutes to minimize external API latency.

**NFR-PE-04**: Pre-computed analytics (residuals, SHAP values, association rules) shall be loaded from cached `.pkl` files rather than recomputed at runtime.

### 4.2 Reliability

**NFR-RE-01**: The currency conversion system shall gracefully fall back to a local rates file, then to built-in approximate rates, if the external API is unreachable.

**NFR-RE-02**: Core prediction functionality (Manual, Batch, Scenario) shall remain fully operational even when Firebase services are unavailable.

**NFR-RE-03**: The system shall display user-friendly error messages for invalid inputs, unsupported file formats, and failed API calls.

### 4.3 Usability

**NFR-US-01**: The application shall implement a unified dark professional color theme consistently across all pages and components.

**NFR-US-02**: All input forms shall provide appropriate validation and feedback before prediction execution.

**NFR-US-03**: The tab-based navigation structure shall remain consistent across both models; only model-specific tabs or fields shall differ.

**NFR-US-04**: PDF reports shall be downloadable with a single click after a one-time preparation step.

### 4.4 Security

**NFR-SE-01**: Firebase API keys and service account credentials shall be stored exclusively in `.streamlit/secrets.toml` and shall never be committed to version control.

**NFR-SE-02**: Passwords shall be managed exclusively by Firebase Authentication; no plaintext passwords shall be stored by the application.

**NFR-SE-03**: Admin panel access shall require a verified admin check; it shall not be accessible to regular or anonymous users.

**NFR-SE-04**: Anonymous feedback shall be stored without any personally identifiable information.

### 4.5 Scalability

**NFR-SC-01**: The batch prediction pipeline shall support up to 50,000 records in a single submission.

**NFR-SC-02**: The Firestore data model shall be structured to allow efficient per-user prediction history retrieval without requiring full collection scans.

### 4.6 Maintainability

**NFR-MT-01**: Each logical subsystem (resume NLP, currency utils, tax utils, COL utils, PDF generation, auth, feedback, recommendations, negotiation tips, insights engine, admin panel, user profile) shall reside in a separate Python module.

**NFR-MT-02**: Pre-trained models shall be stored as `.pkl` files and loaded at startup, allowing model updates without changes to application code.

**NFR-MT-03**: All configurable parameters (tax rates, COL indices, fallback rates) shall be stored as data structures within their respective utility modules, not hardcoded in the main application file.

### 4.7 Portability

**NFR-PT-01**: The application shall be platform-independent and accessible from any modern web browser without client-side installation.

**NFR-PT-02**: The system shall run on Windows, macOS, and Linux when installed locally.

---

## 5. External Interface Requirements

### 5.1 User Interfaces

- The UI is rendered entirely by Streamlit in a web browser.
- A wide-layout page configuration is used.
- Navigation is tab-based within the main content area.
- The sidebar contains: model selector, user login/logout controls, and navigation to the profile.
- All visual components use the defined dark professional CSS theme.

### 5.2 Hardware Interfaces

No direct hardware interfaces. The application is web-based and interacts with the user through standard browser/computer hardware.

### 5.3 Software Interfaces

| Interface | Purpose |
|---|---|
| Firebase Authentication REST API | User registration and login |
| Firebase Admin SDK | Firestore read/write operations |
| Google Firestore | Storage of users, predictions, and feedback |
| ExchangeRate API (`open.er-api.com`) | Live exchange rate data for currency conversion |
| Streamlit Community Cloud | Application hosting and deployment |
| spaCy NLP Library | Resume text feature extraction |
| pdfplumber | PDF text extraction from uploaded resumes |
| ReportLab | Programmatic PDF report generation |

### 5.4 Communications Interfaces

- The application communicates with Firebase over HTTPS.
- The exchange rate API is accessed over HTTPS.
- No direct WebSocket or real-time communication protocols are used.

---

## 6. System Constraints

- **Free-tier deployment constraints**: Streamlit Community Cloud free tier imposes memory and CPU limits. The spaCy-based resume module and the full app are therefore deployed separately from the lite app.
- **Static models**: Models are pre-trained and cannot be updated at runtime. Improving models requires offline retraining and redeployment of `.pkl` files.
- **Dataset coverage**: Model accuracy is limited by the coverage of the training datasets; unseen roles, countries, or salary ranges may yield less reliable predictions.
- **No real-time market data**: The system does not integrate with live salary market APIs; all predictions are data-driven from historical datasets.
- **Single-file Streamlit architecture**: The main app logic resides in `app_resume.py`, which is a constraint of the chosen deployment framework.

---

## 7. Assumptions and Dependencies

### Assumptions

- Users accessing the deployed app have a stable internet connection.
- Users providing resume PDFs have resumes in a standard text-based PDF format (not scanned images).
- Tax and COL estimates are used by users for approximate planning, not precise financial decisions.
- Exchange rates from the public API are sufficiently accurate for informational purposes.

### Dependencies

| Dependency | Version / Notes |
|---|---|
| Python | 3.13+ |
| Streamlit | Latest compatible |
| Scikit-learn | For Random Forest, HistGradientBoosting, KMeans, PCA, GridSearchCV |
| XGBoost | For Model 2 regression |
| spaCy | For resume NLP extraction |
| pdfplumber | For PDF text extraction |
| MLxtend | For Apriori association rule mining |
| SHAP | For Model 2 feature importance |
| Plotly | For interactive charts |
| Matplotlib | For static charts in PDF reports |
| ReportLab | For PDF generation |
| Firebase Admin SDK | For Firestore and Auth operations |
| Pandas / NumPy | For data manipulation |
| Requests | For external API calls |
| bcrypt | For password hashing utility |
| Joblib | For `.pkl` model serialization/deserialization |

---

## 8. Appendix

### 8.1 Firestore Data Schema

```
users/
  {email}/
    username, email, display_name, created_at, auth_provider

predictions/
  {email}/
    records/
      {auto-id}/
        model_used, input_data, predicted_salary, created_at

feedback/
  {auto-id}/
    username, model_used, input_data, predicted_salary,
    accuracy_rating, direction, actual_salary, star_rating, created_at,
    extended_data (optional)
```

### 8.2 Model Summary

| Property | Model 1 (RF) | Model 2 (XGBoost) |
|---|---|---|
| Dataset | `Salary.csv` | `ds_salaries.csv` |
| Algorithm | Random Forest Regressor | XGBoost Regressor |
| Target | Annual Salary (USD) | log1p(salary_in_usd) |
| Test R² | ~0.964 | ~0.595 (log scale) |
| MAE | ~$4,927 | ~$35,913 |
| Additional Models | HistGBClassifier, KMeans, Apriori | SHAP analysis |

### 8.3 Input Features per Model

**Model 1**: Age, Years of Experience, Education Level (0–3), Senior Position (0/1), Gender, Job Title, Country

**Model 2**: Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

---

*End of SRS Document*