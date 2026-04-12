# SalaryScope — Salary Prediction System using Machine Learning

<p align="center">
  <a>
    <img src="https://img.shields.io/badge/Python-3.13-3178C6?style=for-the-badge&logo=python&logoColor=white&labelColor=2D3748" alt="Python 3.13" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/Framework-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white&labelColor=2D3748" alt="Framework: Streamlit" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/Machine%20Learning-Scikit--Learn%20%7C%20XGBoost-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white&labelColor=2D3748" alt="Machine Learning: Scikit-learn and XGBoost" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/NLP-spaCy-09A3D5?style=for-the-badge&logo=spacy&logoColor=white&labelColor=2D3748" alt="NLP: spaCy" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/Database-Firebase-000000?style=for-the-badge&logo=firebase&logoColor=white&labelColor=2D3748" alt="Database: Firebase" />
  </a>
  <a>
    <a>
      <img src="https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge&labelColor=2D3748" alt="Version: 1.0.0" />
    </a>
  </a>
</p>
<p align="center">
  <a>
    <img src="https://img.shields.io/badge/Deployment-Streamlit%20Cloud-1E9E82?style=flat-square&logo=streamlit&logoColor=white&labelColor=2D3748" alt="Deployment: Streamlit Cloud" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/Platform-Web%20(Browser)-2C3E50?style=flat-square&labelColor=2D3748" alt="Platform: Web" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/License-MIT-6C5CE7?style=flat-square&labelColor=2D3748" alt="License: MIT" />
  </a>
</p>

> Machine learning-powered salary prediction system with dual models, hybrid resume analysis (spaCy + rule-based extraction), and interactive analytics.

SalaryScope is a machine learning-based web application developed as a Final Year B.Tech Project. It provides salary prediction capabilities through two distinct models, each trained on a different dataset and targeting different use cases. The application is built with Streamlit and deployed on Streamlit Cloud.

---

## Table of Contents

- [Overview](#overview)
- [Live Demo](#live-demo)
- [Screenshots](#screenshots)
- [Features](#features)
- [Models](#models)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Platform Compatibility](#platform-compatibility)
- [Configuration](#configuration)
- [Usage](#usage)
- [Dataset Information](#dataset-information)
- [Technologies Used](#technologies-used)
- [Authentication & Database](#authentication--database)
- [Limitations](#limitations)
- [Future Scope](#future-scope)
- [References](#references)
- [License](#license)
- [Author](#author)

---

## Overview

SalaryScope allows users to predict salaries either manually, via resume upload (hybrid extraction using spaCy and rule-based techniques), or in bulk (via file upload). It supports two prediction models targeting different domains — a general salary dataset and a data science-specific salary dataset. The app includes scenario analysis, model analytics, dataset exploration, basic tax estimation, and cost-of-living adjusted salary insights, user authentication, prediction feedback collection, and PDF report generation.

The project follows a structured workflow:
- Data analysis and model development using Jupyter notebooks
- Additional visualization through Power BI dashboards
- Model training and evaluation
- Integration of trained models into a Streamlit-based web application
- Storage and feedback collection using Firebase

The focus of the project is to combine machine learning with an interactive application interface, providing both prediction capabilities and supporting insights for better understanding of salary patterns. The system also includes basic financial context tools such as post-tax estimation and cost-of-living adjustment to improve real-world interpretability of predictions. The system also incorporates a feedback-driven learning layer to progressively improve model performance using real-world user data.

The application runs in a web browser, making it platform-independent and easily accessible.

## Key Features (Quick Overview)

- Dual machine learning models (Random Forest + XGBoost)
- Resume-based salary prediction using NLP (spaCy)
- Scenario analysis and sensitivity simulation
- Batch prediction (up to 50,000 records)
- Real-time currency conversion with fallback system
- Model analytics and performance visualization
- Firebase-based authentication and feedback system
- Basic post-tax salary estimation with country-specific effective rates
- Basic cost-of-living (COL) adjustment for contextual salary comparison
---

## Live Demo

:link: SalaryScope is deployed on Streamlit Cloud with two versions:

- **Full App (Includes Resume Analysis):**  
  https://salaryscope-app.streamlit.app/

- **Lite App (Lightweight Version):**  
  https://salaryscope-lite-app.streamlit.app/


### Notes
- The full version includes **spaCy-based NLP resume parsing**, which is more resource-intensive.
- Due to Streamlit Cloud free-tier limitations (memory and performance), the applications are deployed separately for stability.
- The repository contains the complete implementation, including the resume-based pipeline (`app_resume.py`).

---

## Screenshots

> Screenshots below show key sections of the application.
### Manual Prediction
![Manual Prediction](screenshots/manual_prediction.png)

### Scenario Analysis
![Scenario Analysis](screenshots/scenario_analysis.png)

### Resume Analysis
![Resume Analysis](screenshots/resume_analysis.png)

### Batch Prediction
![Batch Prediction](screenshots/batch_prediction.png)

### Model Analytics
![Model Analytics](screenshots/model_analytics.png)


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
- Prediction feedback collection after each result (accuracy rating, direction, star rating, optional actual salary) 
- Optional currency conversion with global currency support (toggle-based)
- Available to all users

### Resume-Based Prediction (NLP)
- Upload a resume (PDF format)
- Automatic extraction of:
  - Job Title
  - Years of Experience
  - Skills
  - Education Level
  - Country
- Basic resume scoring based on experience, education, and skills
- Uses a hybrid approach combining spaCy (lightweight NLP for entity recognition and phrase matching) with rule-based extraction (regex and keyword matching)
- Handles unstructured resume text and converts it into structured model-ready input
- Extracted features are passed to the selected model for prediction
- Supports both Model 1 and Model 2 pipelines
- Optional currency conversion for predicted salary output

### Batch Prediction
- Upload files in CSV, XLSX, JSON, or SQL format
- Upload via public Google Drive link
- File validation with detailed error messages
- Supports up to 50,000 rows
- Full analytics dashboard after prediction (charts, summaries, leaderboard)
- Export results in CSV, XLSX, JSON, or SQL format
- Downloadable PDF batch analytics report

### Scenario Analysis
- Build and compare up to 5 fully customisable named scenarios in a single session
- Each scenario accepts the same inputs as manual prediction for the active model
- Run all scenarios simultaneously with a single button click
- Side-by-side comparison table with predicted salary, salary level, and career stage per scenario
- Bar chart comparing predicted annual salary across all scenarios with dollar labels
- Charts colored by salary level and career stage (Model 1), or by experience level, company size, and work mode (Model 2)
- Salary confidence interval chart showing 95% lower and upper bounds per scenario — Model 1
- Experience vs Salary bubble scatter plot across all scenarios — Model 1
- Sensitivity sweep: select a baseline scenario and simulate salary change across a continuous 0–40 year experience range (Model 1) or across all four experience levels (Model 2), with all other inputs held fixed
- Education level sweep across High School, Bachelor's, Master's, and PhD for a selected baseline scenario — Model 1
- Company size sweep across Small, Medium, and Large companies for a selected baseline scenario — Model 2
- Export scenario results in CSV, XLSX, or JSON format

### Prediction Feedback

- Available in the Manual Prediction tab for both models
- Appears as a collapsible expander after a prediction result is generated
- Structured feedback fields:
  - Accuracy rating: Yes / Somewhat / No
  - Direction: Too High / About Right / Too Low
  - Star rating: 1–5
  - Optional actual or expected salary (USD)
- Available to both logged-in and anonymous users
- Prediction inputs and predicted salary are stored alongside feedback for traceability
- Stored in Firestore under a dedicated `feedback/` collection, separate from prediction history
- One submission per prediction result per session

#### Enhanced Feedback Collection (Model Improvement Layer)

- Optional extended feedback form to capture richer real-world data
- Cross-dataset feature bridging:
  - For Data Science model (XGBoost):
    - Collects missing general features (age, education, seniority, gender)
  - For General model (Random Forest):
    - Collects missing DS-specific features (employment type, remote ratio, company size, company location)
- Enables creation of a unified combined dataset for future model training
- Additional optional inputs:
  - Compensation structure (base salary, total compensation, bonuses, equity)
  - Skills and certifications
  - Industry and company characteristics
  - Role context (team size, direct reports, tenure)
  - Work conditions (hours, city tier, work authorisation)
- Optional contextual notes (free-text, capped length)
- All extended data is stored under an `extended_data` field in Firestore

**Purpose:**
- Improve model accuracy over time using real user data
- Bridge gaps between heterogeneous datasets
- Capture real-world salary complexity beyond training datasets

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

### Currency Conversion

- Convert predicted salary (USD) into multiple global currencies
- Toggle-based UI to enable/disable conversion per prediction
- Supports 100+ currencies with symbols and proper formatting
- Automatic default currency selection based on user country input
- Real-time exchange rates fetched from a public API (https://open.er-api.com/) — no API key required
- Smart caching system:
  - Exchange rates cached in memory (~60 minutes) to improve performance and reduce API calls
- Robust fallback mechanism:
  - Loads local JSON fallback file (`exchange_rates_fallback.json`) if network is unavailable
  - Uses built-in approximate rates as a last resort
- Displays:
  - Annual salary (converted)
  - Monthly, weekly, and hourly breakdowns (converted)
- Streamlit-integrated UI:
  - Dropdown for currency selection
  - Expandable interface for a clean user experience
- Option to save exchange rates locally for offline usage
- Fully non-intrusive — does not modify original USD predictions

**Notes:**
- Currency conversion is for informational purposes only
- Exchange rates may vary slightly depending on source and timing
- All predictions are generated in USD as the base currency

### Post-Tax Salary Estimation

- Estimate post-tax salary based on country-specific effective tax rates
- Supports progressive tax brackets for major countries
- Automatic country detection from input (with manual override option)
- Custom tax rate input for personalized estimation
- Displays:
  - Estimated tax amount
  - Net annual salary
  - Monthly, weekly, and hourly breakdowns (post-tax)
- Optional integration with currency conversion:
  - View post-tax salary in selected currency
- Toggle-based UI to enable or disable tax adjustment
- Fully non-intrusive — does not modify original gross prediction

**Notes:**
- Tax calculations are approximate and intended for planning purposes only
- Does not include detailed deductions, exemptions, or local taxes

### Cost of Living Adjustment (COL)

- Adjust predicted salary based on relative cost of living across countries
- Provides context-aware salary comparison rather than raw numerical values
- Helps users understand real purchasing power in different regions
- Uses approximate COL indices derived from public datasets
- Displays:
  - Adjusted salary value
  - Relative affordability comparison
- Toggle-based UI for optional activation
- Works independently or alongside currency and tax adjustments

**Notes:**
- COL values are approximate and may vary by city, lifestyle, and time
- Intended for comparison and insight, not exact financial planning

### Admin Panel (Diagnostics & Monitoring)

- Accessible only to authorized users via internal admin check

**System Information**
- OS, architecture, Python and library versions
- Deployment environment (Local vs Streamlit Cloud)

**Firebase Monitoring**
- Project configuration status
- User count retrieval

**Feedback Analytics**
- Total feedback, accuracy distribution, and average rating
- Prediction direction trends
- Model-wise feedback comparison
- Median actual salary (if available)

**Recent Activity**
- View latest feedback entries with prediction details

**Performance & Debugging**
- RAM usage monitoring
- Manual garbage collection and cache clearing
- Session state inspection

**Local-Only Diagnostics**
- Process and system metrics (CPU, memory, disk, network)
- Python environment details
- Installed package checks
- Snapshot-based system visualisation

The admin panel is lightweight, on-demand, and designed for monitoring without affecting application performance.

---

## Models

### Model 1 — General Salary (Random Forest)

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

### Model 2 — Data Science Salary (XGBoost)

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
├── app_resume.py                        # Main Streamlit application with resume analysis and scenario/what-if analysis
├── app-lite.py                          # Lightweight Streamlit application
│
├── app/
│   ├── core/
│   │   ├── auth.py                      # Firebase Authentication (login, register, session)
│   │   ├── database.py                  # Firestore client, user and prediction functions
│   │   ├── insights_engine.py           # Insights engine
│   │   └── resume_analysis.py           # Resume parsing (SpaCy, regex, feature extraction)
│   │
│   ├── tabs/
│   │   ├── manual_prediction_tab.py    # Manual Prediction: Salary prediction, breakdown, insights, reports, adjustments
│   │   ├── resume_analysis_tab.py      # Resume Prediction: E    xtract features from resume and predict salary
│   │   ├── batch_prediction_tab.py     # Batch Prediction: Process files, run predictions, analytics, export results
│   │   ├── scenario_analysis_tab.py    # Scenario Analysis: Compare scenarios, charts, sensitivity analysis
│   │   ├── model_analytics_tab.py      # Model Analytics: Metrics, feature importance, residuals, evaluation
│   │   ├── data_insights_tab.py        # Data Insights: Dataset analysis, distributions, trends
│   │   ├── user_profile.py             # User profile tab UI and prediction history
│   │   ├── admin_panel.py              # Admin dashboard for basic system diagnostics, usage insights, and monitoring
│   │   └── about_tab.py                # About: Project overview and information
│   │
│   ├── utils/
│   │   ├── country_utils.py             # Centralized country resolution (ISO-2, aliases, CLDR via Babel)
│   │   ├── currency_utils.py            # Currency conversion utility (live rates, fallback system, Streamlit UI)
│   │   ├── tax_utils.py                 # Basic tax estimation utility (country-based effective rates, Streamlit UI)
│   │   ├── col_utils.py                 # Basic cost-of-living adjustment utility (relative salary normalization)
│   │   ├── pdf_utils.py                 # ReportLab PDF generation for all report types
│   │   ├── feedback.py                  # Prediction feedback collection (UI + Firestore save)
│   │   ├── recommendations.py           # Recommendations engine
│   │   ├── negotiation_tips.py          # Salary negotiation tips engine
│   │   ├── ctc_utils.py                 # CTC Breakdown: Splits salary into base, HRA, bonus, PF, gratuity, and allowances
│   │   ├── takehome_utils.python        # Take-Home Salary: Calculates net salary after tax, PF, and deductions
│   │   ├── savings_utils.py             # Savings Calculator: Estimates monthly and long-term savings from net income
│   │   └── loan_utils.python            # Loan Estimator: Calculates maximum loan based on income, EMI limits, and interest
│
├── model/
│   ├── rf_model_grid.pkl                # Model 1: Random Forest pipeline + metadata
│   ├── salary_band_classifier.pkl       # Model 1: Salary level classifier + metadata
│   ├── career_cluster_pipeline.pkl      # Model 1: KMeans clustering pipeline + metadata
│   ├── app1_analytics.pkl               # Model 1: Precomputed analytics (residuals, PCA, etc.)
│   ├── ds_xgb_model_grid.pkl            # Model 2: XGBoost pipeline + metadata
│   └── app2_analytics.pkl               # Model 2: Precomputed analytics (SHAP, residuals, etc.)
│
├── notebooks/                           # Jupyter notebooks for EDA, feature engineering, and model development
├── powerbi/                             # Power BI dashboards and exported reports
├── docs/                                # Project documentation (SRS, design, report)
├── samples/                             # Sample input files (CSV, resumes)
├── assets/                              # Branding and visual assets
├── pdf_outputs/                         # Generated PDF reports (sample outputs)
│
├── data/
│   ├── Salary_Streamlit_App.csv         # Model 1 training dataset
│   ├── ds_salaries_Streamlit_App.csv    # Model 2 training dataset
│   └── association_rules.csv            # Precomputed Apriori association rules
│
├── static/                              # Icons, favicons, and web assets
│
├── screenshots/
│   ├── manual_prediction.png
│   ├── scenario_analysis.png
│   ├── resume_analysis.png
│   ├── batch_prediction.png
│   └── model_analytics.png
│
├── .streamlit/
│   └── config.toml                      # Streamlit configuration
│
├── exchange_rates_fallback.json
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

* Python 3.13 (recommended)
* The project may work on lower Python versions, but it has been developed and tested using Python 3.13.
* A Firebase project with Firestore enabled


### Steps
```bash
# 1. Clone the repository
git clone https://github.com/ybs294000/salaryscope.git
cd salaryscope

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets (see Configuration section below)

# 5. Run the application
streamlit run app_resume.py
```
---

## Platform Compatibility

SalaryScope is a cross-platform application and has been tested in multiple environments:

### Local Development & Testing
- Windows 11 (development environment)
- Windows 10 (tested)
- Ubuntu 24.04 LTS (tested in virtual machine)
- Python 3.13

### Cloud Deployment
- Deployed on Streamlit Community Cloud
- Runs on a Linux-based environment (Debian GNU/Linux)

### Key Notes
- The application runs in a web browser and is independent of the underlying operating system
- No OS-specific dependencies are required
- Compatible with modern browsers such as:
  - Google Chrome (recommended)
  - Microsoft Edge
  - Mozilla Firefox

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

## Important Notes

* Firebase authentication requires valid credentials and may not function without proper configuration.
* The application is fully usable without authentication for core features such as manual prediction, scenario analysis, and model analytics.
* Feedback submission is available to all users including those not logged in.
* Resume parsing requires spaCy language model installation.

---

## Usage

### Manual Prediction
1. Select a model from the dropdown at the top
2. Navigate to the **Manual Prediction** tab
3. Fill in the required fields and click **Predict Salary**
4. View results, insights, and optionally:
  - Convert salary into other currencies
  - Enable post-tax salary estimation
  - Apply cost-of-living adjustment for better comparison across regions
  - Download a PDF report
5. Expand the **Share Feedback on This Prediction** section to rate the prediction accuracy — login is not required

### Resume Prediction
1. Navigate to the **Resume Analysis** tab
2. Upload a PDF resume
3. Click **Extract Resume Features** to parse resume details
4. Review and edit extracted features (skills, experience, job role, etc.)
5. Click **Predict Salary from Resume** to run prediction
6. View results and download PDF report

### Batch Prediction
1. Download the sample file from the **Batch Prediction** tab to see the required format
2. Upload your file (CSV, XLSX, JSON, or SQL) or paste a public Google Drive link
3. Click **Run Batch Prediction**
4. Explore the analytics dashboard and export results

### Scenario Analysis
1. Navigate to the **Scenario Analysis** tab after selecting your model
2. Each scenario is pre-filled with sensible defaults — rename it and adjust any inputs
3. Click **Add Scenario** to add more scenarios (up to 5) or **Remove** to delete one
4. Click **Run All Scenarios** to predict salaries for all scenarios simultaneously
5. Review the comparison table, salary charts, and confidence interval ranges
6. Select a baseline scenario from the sensitivity sweep dropdown to simulate how salary responds to changes in experience or education while everything else stays fixed
7. Use the export dropdown and download button to save scenario results

### Model Analytics
- Navigate to the **Model Analytics** tab to view full model diagnostics, comparison charts, and download the analytics PDF report

### User Account
- Register or log in from the sidebar
- Logged-in users can access the **Profile** tab for prediction history and exports
- Sessions expire after 24 hours and require re-login

### Google Drive Upload (Batch)
- Set the file sharing permission to "Anyone with the link can view" before pasting the link
- Select the correct file format from the dropdown after pasting the link

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
| Language | Python 3.13+ |
| NLP | spaCy, Regex, PhraseMatcher |
| API Integration | ExchangeRate API (open.er-api.com) |
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

feedback/
  {auto-id}/
    username, model_used, input_data, predicted_salary,
    accuracy_rating, direction, actual_salary, star_rating, created_at,
    extended_data (optional nested object)
```

---

---

## Data Collection Strategy (Feedback-Driven Learning)

SalaryScope includes a feedback-driven data collection layer designed to improve future model performance over time.

### Key Concepts

- Combines model predictions with real-world user feedback
- Collects optional structured and contextual salary data
- Bridges differences between multiple datasets used in the system
- Builds a continuously improving dataset without relying solely on external sources

### What Gets Collected

- Prediction accuracy and user rating
- Actual or expected salary (optional)
- Extended structured data (if provided):
  - Compensation structure (base, bonus, equity)
  - Skills and certifications
  - Industry and company context
  - Role-level details (team size, reports, tenure)
  - Work conditions (hours, location type, visa status)

### Benefits

- Enables future model retraining with real-world data
- Improves generalisation beyond static datasets
- Captures real compensation complexity
- Reduces dataset bias and improves reliability

### Design Approach

- Fully optional data collection (non-intrusive)
- No impact on prediction workflow if skipped
- Stored separately in Firestore for clean data pipelines

---

## Limitations

- The models are trained on publicly available datasets and may not fully reflect current real-world salary trends.
- Model predictions depend on patterns present in the training data and may not generalize well to unseen roles or regions.
- Resume analysis uses a hybrid approach combining lightweight NLP (spaCy) and rule-based extraction, which may not accurately handle complex or heavily formatted resumes.
- Predictions do not account for real-time factors such as market demand, company-specific policies, or economic changes.
- The confidence interval shown for Model 1 is an approximation based on training residuals and should be interpreted as an estimate rather than an exact range.
- Feedback submitted anonymously cannot be linked to a specific user session and is stored without any personal identifier.
- Currency conversion uses external exchange rate data and may not reflect real-time market fluctuations or transaction-specific rates.
- Tax estimation uses approximate effective rates and does not model detailed national tax rules.
- Cost-of-living adjustments are based on generalized indices and may not reflect individual lifestyle differences.
- Combined currency, tax, and COL adjustments are intended for comparative insight, not exact financial planning.
---

## Future Scope

- Improve model performance by training on larger and more recent datasets.
- Enhance resume parsing using more advanced NLP techniques for better accuracy.
- Expand the system to support additional job roles and domains beyond current datasets.
- Add more interactive analysis features to help users better understand prediction behavior.
- Use collected feedback data to retrain or calibrate models over time.

---

## References

- Python Documentation — https://docs.python.org/3/
- Streamlit Documentation — https://docs.streamlit.io  
- Scikit-learn Documentation — https://scikit-learn.org  
- XGBoost Documentation — https://xgboost.readthedocs.io  
- SHAP Documentation — https://shap.readthedocs.io

---

## License

This project is licensed under the MIT License — a permissive open-source license allowing reuse with attribution.

You are free to use, modify, and distribute this software with proper attribution.

See the [LICENSE](LICENSE) file for more details.

---
## Author

**Yash Shah**,  
B.Tech Final Year Student,  
Computer Engineering Department, Gandhinagar Institute of Technology, Gandhinagar University 
- GitHub: [@ybs294000](https://github.com/ybs294000)
- Email: yashbshah2004@gmail.com

> This project was developed as a Final Year B.Tech academic submission.

---

*Built with Streamlit · Powered by Firebase · Deployed on Streamlit Community Cloud*