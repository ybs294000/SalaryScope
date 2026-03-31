# SalaryScope — Salary Prediction System using Machine Learning

SalaryScope is a machine learning-based web application developed as a Final Year B.Tech Project. It provides salary prediction capabilities through two distinct models, each trained on a different dataset and targeting different use cases. The application is built with Streamlit and deployed on Streamlit Cloud.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Models](#models)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Dataset Information](#dataset-information)
- [Technologies Used](#technologies-used)
- [Authentication & Database](#authentication--database)

---

## Overview

SalaryScope allows users to predict salaries either manually, via resume upload (NLP-based extraction), or in bulk (via file upload). It supports two prediction models targeting different domains — a general salary dataset and a data science-specific salary dataset. The app includes model analytics, dataset exploration, user authentication, and PDF report generation.

---

## Features

### Manual Prediction
- Predict salary from a single set of inputs
- Salary breakdown: monthly, weekly, and hourly estimates
- Salary level classification (Early Career / Professional / Executive Range) — Model 1
- Career stage segmentation (Entry / Growth / Leadership Stage) — Model 1
- Pattern insight via association rule mining — Model 1
- Negotiation tips and career recommendations
- Confidence interval estimation based on residual standard deviation — Model 1
- Downloadable PDF prediction report

### Resume-Based Prediction (NLP)

- Upload a resume (PDF format)
- Automatic extraction of:
  - Job Title
  - Years of Experience
  - Skills
  - Education Level
  - Country
- Resume scoring based on experience, education, and skills
- Uses spaCy NLP + rule-based extraction (regex + phrase matching)
- Handles unstructured resume text and converts it into structured model-ready input
- Extracted features are passed to the selected model for prediction
- Supports both Model 1 and Model 2 pipelines

### Batch Prediction
- Upload files in CSV, XLSX, JSON, or SQL format
- Upload via public Google Drive link
- File validation with detailed error messages
- Supports up to 50,000 rows
- Full analytics dashboard after prediction (charts, summaries, leaderboard)
- Export results in CSV, XLSX, JSON, or SQL format
- Downloadable PDF batch analytics report

### Model Analytics
- Performance metrics: R², MAE, RMSE
- Model comparison table and bar chart
- Feature importance visualizations
- Predicted vs Actual scatter plots
- Residual analysis and distribution
- Prediction uncertainty distribution
- Confusion matrix for salary level classifier — Model 1
- Classification model comparison — Model 1
- Career stage clustering analytics with PCA visualization — Model 1
- SHAP-based grouped feature importance — Model 2
- Association rule mining analytics (support, confidence, lift) — Model 1
- Downloadable PDF model analytics report

### Data Insights
- Exploratory analysis of the training dataset
- Salary distributions, breakdowns by education, experience, seniority, country, job title
- Trend lines and box plots

### User Profile (Logged-in users only)
- Prediction history stored per user
- Summary dashboard: total predictions, average salary, latest prediction
- Prediction history chart over time
- Per-prediction input detail viewer
- Export prediction history in CSV, XLSX, or JSON

---

## Models

### Model 1 — Random Forest (General Salary)

| Component | Details |
|---|---|
| Dataset | `Salary.csv` — general salary dataset |
| Regression Model | Random Forest Regressor (GridSearchCV optimized) |
| Classifier | HistGradientBoostingClassifier (GridSearchCV optimized) |
| Clustering Model | KMeans (3 clusters: Entry, Growth, Leadership) |
| Association Mining | Apriori Algorithm |
| Target | Annual Salary (USD) |
| Test R² | ~0.964 |
| MAE | ~$4,927 |

**Input Features:**
- Age, Years of Experience, Education Level (0–3), Senior Position (0/1), Gender, Job Title, Country

**Outputs:**
- Predicted Annual Salary
- Salary Level (Early Career / Professional / Executive Range)
- Career Stage (Entry / Growth / Leadership Stage)
- Pattern Insight (association rule)
- Negotiation tips
- Career recommendations
- 95% Confidence Interval

---

### Model 2 — XGBoost (Data Science Salary)

| Component | Details |
|---|---|
| Dataset | `ds_salaries.csv` — data science salary dataset |
| Model | XGBoost Regressor with `log1p` target transformation |
| Feature Engineering | Job title seniority, domain, management signals; interaction feature |
| Target | `log1p(salary_in_usd)` → expm1 to USD |
| Test R² (log scale) | ~0.595 |
| MAE | ~$35,913 |

**Input Features:**
- Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

**Outputs:**
- Predicted Annual Salary
- Negotiation tips
- Career recommendations

---

## Project Structure

```
salaryscope/
│
├── app.py                          # Lightweight Streamlit application
├── app_resume.py                   # Main Streamlit application with resume analysis
├── resume_nlp.py                  # Resume parsing (NLP, regex, feature extraction)
├── auth.py                         # Firebase Authentication (login, register, session)
├── database.py                     # Firestore client, user and prediction functions
├── insights_engine.py              # Smart insights and recommendations engine
├── pdf_utils_new.py                # ReportLab PDF generation for all report types
├── user_profile.py                 # User profile tab UI and prediction history
│
├── model/
│   ├── rf_model_grid.pkl           # Model 1: Random Forest pipeline + metadata
│   ├── salary_band_classifier.pkl  # Model 1: Salary level classifier + metadata
│   ├── career_cluster_pipeline.pkl # Model 1: KMeans clustering pipeline + metadata
│   ├── app1_analytics.pkl          # Model 1: Precomputed analytics (residuals, PCA, etc.)
│   ├── salaryscope_3755_production_model.pkl  # Model 2: XGBoost pipeline + metadata
│   └── app2_analytics.pkl          # Model 2: Precomputed analytics (SHAP, residuals, etc.)
│
├── data/
│   ├── Salary_Streamlit_App.csv            # Model 1 training dataset
│   ├── ds_salaries_Streamlit_App.csv       # Model 2 training dataset
│   └── association_rules_v5.csv            # Precomputed Apriori association rules
│
├── static/
│   └── android-chrome-192x192.png          # App logo
│
├── .streamlit/
│   └── secrets.toml                        # Firebase credentials (not committed)
│
└── requirements.txt
```

---

## Installation

### Prerequisites
- Python 3.9 or higher
- A Firebase project with Firestore enabled

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/salaryscope.git
cd salaryscope

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets (see Configuration section below)

# 5. Run the application
streamlit run app.py
```

---

## Configuration

Create a `.streamlit/secrets.toml` file in the project root with the following structure:

```toml
FIREBASE_API_KEY = "your_firebase_api_key"

[FIREBASE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "your_project_id"
private_key_id = "your_private_key_id"
private_key = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email = "your_service_account_email"
client_id = "your_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your_cert_url"
```

> **Note:** Never commit `secrets.toml` to version control. Add it to `.gitignore`.

---

## Usage

### Manual Prediction
1. Select a model from the dropdown at the top
2. Navigate to the **Manual Prediction** tab
3. Fill in the required fields and click **Predict Salary**
4. View results, insights, and optionally download a PDF report

### Resume Prediction

1. Navigate to the Resume tab
2. Upload a PDF resume
3. Click Extract to parse resume details
4. Review extracted features (skills, experience, job role, etc.)
5. Run prediction using selected model
6. View results and download PDF report

### Batch Prediction
1. Download the sample file from the **Batch Prediction** tab to see the required format
2. Upload your file (CSV, XLSX, JSON, or SQL) or paste a public Google Drive link
3. Click **Run Batch Prediction**
4. Explore the analytics dashboard and export results

### Model Analytics
- Navigate to the **Model Analytics** tab to view full model diagnostics, comparison charts, and download the analytics PDF report

### User Account
- Register or log in from the sidebar
- Logged-in users can access the **Profile** tab for prediction history and exports

---

## Dataset Information

### Model 1 Dataset (`Salary.csv`)
- General salary dataset covering multiple industries and countries
- Features: Age, Years of Experience, Education Level, Senior, Gender, Job Title, Country, Salary
- Source: [Kaggle — Salary by Job Title and Country](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)
### Model 2 Dataset (`ds_salaries.csv`)
- Data science and AI/ML specific salary dataset
- Features: experience_level, employment_type, job_title, employee_residence, remote_ratio, company_location, company_size, salary_in_usd
- Source: [Kaggle — Data Science Salaries 2023 :money_with_wings:](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)

---

## Technologies Used

| Category | Technology |
|---|---|
| Frontend / UI | Streamlit |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn, XGBoost |
| Explainability | SHAP |
| Association Mining | MLxtend (Apriori) |
| Visualisation | Plotly, Matplotlib |
| PDF Generation | ReportLab |
| Authentication | Firebase Authentication |
| Database | Firebase Firestore, Firebase Admin SDK |
| Cloud File Retrieval | Requests |
| Security | bcrypt |
| Deployment | Streamlit Cloud |
| Language | Python 3.9+ |
| NLP | spaCy, Regex, PhraseMatcher |
---

## Authentication & Database

- User registration and login is handled via **Firebase Authentication** (email and password)
- User profile data and prediction history are stored in **Firestore**
- Sessions are managed via Streamlit session state with a 24-hour expiry
- Passwords are handled entirely by Firebase — no plaintext credentials are stored

### Firestore Collections

```
users/
  {email}/
    username, email, display_name, created_at, auth_provider

predictions/
  {email}/
    records/
      {auto-id}/
        model_used, input_data, predicted_salary, created_at
```

---

## License

This project was developed as a Final Year B.Tech academic submission.

---

*Built with Streamlit · Powered by Firebase · Deployed on Streamlit Cloud*