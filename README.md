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
    <img src="https://img.shields.io/badge/Model%20Storage-HuggingFace-FFD21E?style=for-the-badge&logo=huggingface&logoColor=white&labelColor=2D3748" alt="Model Storage: HuggingFace" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/version-1.3.0-blue?style=for-the-badge&labelColor=2D3748" alt="Version: 1.3.0" />
  </a>
</p>

<p align="center">
  <a>
    <img src="https://img.shields.io/badge/Deployment-Streamlit%20Cloud-1E9E82?style=flat-square&logo=streamlit&logoColor=white&labelColor=2D3748" alt="Deployment: Streamlit Cloud" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/Platform-Web%20App-2C3E50?style=flat-square&labelColor=2D3748" alt="Platform: Web" />
  </a>
  <a>
    <img src="https://img.shields.io/badge/License-MIT-6C5CE7?style=flat-square&labelColor=2D3748" alt="License: MIT" />
  </a>
</p>

> Machine learning-powered salary prediction system with dual models, hybrid resume analysis (spaCy + rule-based extraction), interactive analytics, an extensible Model Hub with four schema-driven prediction modes per model, and data-driven extraction lexicons covering multiple professional domains.

SalaryScope is a machine learning-based web application developed as a Final Year B.Tech Project. It provides salary prediction capabilities through two distinct models, each trained on a different dataset and targeting different use cases. The application is built with Streamlit and deployed on Streamlit Cloud.

---

## Table of Contents

- [Overview](#overview)
- [Live Demo](#live-demo)
- [Screenshots](#screenshots)
- [Features](#features)
- [Model Hub](#model-hub)
- [Models](#models)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Platform Compatibility](#platform-compatibility)
- [Configuration](#configuration)
- [Usage](#usage)
- [Dataset Information](#dataset-information)
- [Technologies Used](#technologies-used)
- [Security Features](#security-features)
- [Authentication & Database](#authentication--database)
- [Limitations](#limitations)
- [Future Scope](#future-scope)
- [Documentation](#documentation)
- [References](#references)
- [License](#license)
- [Author](#author)

---

## Overview

SalaryScope allows users to predict salaries either manually, via resume upload (hybrid extraction using spaCy and rule-based techniques), or in bulk (via file upload). It supports two prediction models targeting different domains — a general salary dataset and a data science-specific salary dataset. The app includes scenario analysis, model analytics, dataset exploration, basic tax estimation, cost-of-living adjusted salary insights, and extended financial analysis tools such as CTC breakdown, take-home salary estimation, savings potential, loan affordability insights, user authentication, prediction feedback collection, and PDF report generation.

A Model Hub module allows admins to upload additional independently trained sklearn-compatible models and make them available to logged-in users through a dynamically generated prediction interface, without modifying application code.

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
- Resume-based salary prediction using NLP (spaCy + data-driven JSON lexicons)
- Scenario analysis and sensitivity simulation
- Batch prediction (up to 50,000 records for built-in models; up to 10,000 for Model Hub)
- Real-time currency conversion with fallback system
- Model analytics and performance visualization
- Firebase-based authentication and feedback system
- Basic post-tax salary estimation with country-specific effective rates
- Basic cost-of-living (COL) adjustment for contextual salary comparison
- Financial planning tools: CTC breakdown, take-home salary, savings potential, loan affordability, budget allocation, investment growth projection, emergency fund planning, lifestyle budget split
- Model Hub: upload and serve additional trained models with four schema-driven prediction modes (Manual, Batch, Resume, Scenario) and a Model Card per model
- Per-bundle lexicons: Model Hub models can supply custom skill and job title lexicons that override global defaults for resume extraction
- Per-bundle resume config: Model Hub models can supply a `resume_config.json` that overrides extraction scoring weights, extractor keyword lists, experience thresholds, and field-name mappings for that specific model, without changing any code
- HR & Employer Tools: five compensation planning tools for hiring managers and HR teams (Hiring Budget Estimator, Salary Benchmarking Table, Candidate Comparison, Offer Competitiveness Checker, Team Compensation Audit) with per-tool HR overrides and CSV exports

---

## Live Demo

:link: SalaryScope is deployed on Streamlit Cloud with two versions:

- **Full App (Complete Feature Set):**  
  https://salaryscope-app.streamlit.app/

- **Lite App (Core Prediction Features):**  
  https://salaryscope-lite-app.streamlit.app/

### Full App vs Lite App

| Feature | Full App | Lite App |
|---|---|---|
| Manual Prediction | ✅ | ✅ |
| Batch Prediction | ✅ | ✅ |
| Model Analytics | ✅ | ✅ |
| Data Insights | ✅ | ✅ |
| User Profile | ✅ | ✅ |
| Resume Analysis (NLP) | ✅ | ❌ |
| Scenario Analysis | ✅ | ❌ |
| Model Hub | ✅ | ❌ |
| Admin Panel | ✅ | ❌ |
| Financial Planning Tools (11 modules) | ✅ | ❌ |
| Prediction Feedback System | ✅ | ❌ |
| HR & Employer Tools | ✅ | ❌ |

The lite app was built to stay within Streamlit Cloud free-tier memory limits by removing the most resource-intensive features and their dependencies (spaCy, pdfplumber, HuggingFace Hub, and the full financial tools chain). Both apps share the same Firebase project, so prediction history is unified across them.

The repository contains the complete implementation in `app_resume.py`. The lite app entry point is `app-lite.py`.

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
- Automatic extraction of: Job Title, Years of Experience, Skills, Education Level, Country
- Resume scoring out of 100 across three dimensions: experience (up to 40), education (up to 30), and skills (up to 30); profile strength label: Basic, Moderate, or Strong
- Extraction quality panel showing which fields were auto-matched and which need manual review, with per-field provenance (extractor used, value found, source)
- Uses a hybrid approach: spaCy PhraseMatcher for skills and job titles, NER for countries, regex for experience years and education level
- Extraction is data-driven: all skill phrases, job title aliases, education patterns, and country aliases are loaded from JSON lexicons under `app/model_hub/extended_modes/lexicons/` — extendable without code changes
- Skill coverage spans 20+ professional domains: programming languages, data science, ML/AI, cloud, data engineering, MLOps, mechanical and civil engineering, electrical and electronics, aerospace, chemical and process engineering, energy and environment, pharmaceutical and drug development, biotechnology and life sciences, neuroscience, mathematics and statistics, and cybersecurity
- Model Hub models can supply per-bundle `skills.json` and `job_titles.json` lexicons that override global defaults for that specific model; falls back to global lexicons when absent
- Model Hub models can supply a per-bundle `resume_config.json` that overrides extraction engine defaults (scoring weights, extractor keyword lists, experience thresholds, field-name-to-extractor mappings, and text preprocessing) for that specific model without touching any code; falls back to engine defaults when absent
- Uploading a new PDF clears previous extraction results automatically; a Clear button is also available
- Extracted features are fully editable before prediction
- Supports both Model 1 and Model 2 pipelines, and all Model Hub models
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
- Input fields are plain widgets — no save step is required before running; values are always current when Run All Scenarios is clicked
- Run all scenarios simultaneously with a single button click; Clear Results button resets between runs
- Side-by-side comparison table with predicted salary, salary level, and career stage per scenario
- Bar chart comparing predicted annual salary across all scenarios with dollar labels
- Charts colored by salary level and career stage (Model 1), or by experience level, company size, and work mode (Model 2)
- Salary confidence interval chart showing 95% lower and upper bounds per scenario — Model 1
- Experience vs Salary bubble scatter plot across all scenarios — Model 1
- Sensitivity sweep: select a baseline scenario and simulate salary change across a continuous 0–40 year experience range (Model 1) or across all four experience levels (Model 2), with all other inputs held fixed
- Education level sweep across High School, Bachelor's, Master's, and PhD for a selected baseline scenario — Model 1
- Company size sweep across Small, Medium, and Large companies for a selected baseline scenario — Model 2
- For Model Hub models: sweep field and mode (continuous range or discrete values) declared in schema.json via the `scenario_sweep` key
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

### Financial Planning Tools

A suite of 11 modular, toggle-based financial planning tools that appear below prediction results. Each tool is independently toggleable and operates on the predicted salary:

| Tool | What it answers |
|---|---|
| **Currency Converter** | What is my salary in another currency? |
| **Post-Tax Estimator** | What do I take home after income tax? |
| **Cost-of-Living Adjuster** | What salary would give equivalent purchasing power elsewhere? |
| **CTC Breakdown** | What are the components of my gross compensation package? |
| **Take-Home Estimator** | What is my net monthly in-hand after all deductions? |
| **Savings Potential** | How much can I realistically save each month? |
| **Loan Affordability** | How large a loan can I service on my income? |
| **Budget Planner** | How should I allocate my monthly net income? |
| **Investment Growth Estimator** | What will my savings be worth in 5, 10, 20, 30 years? |
| **Emergency Fund Planner** | How large a safety net do I need and how long to build it? |
| **Lifestyle Budget Split** | How should I split my discretionary income? |

All tools use country-specific data (tax brackets, CoL indices, expense ratios, loan rates, expected investment returns) sourced from Numbeo, OECD, World Bank, and government portals (2023/24). Results are approximate estimates intended for planning purposes, not financial advice.

### HR & Employer Tools

A dedicated tab providing compensation planning and benchmarking tools for HR teams and hiring managers. All tools use the currently active ML model for salary estimates and expose per-tool HR overrides so internal policy values can substitute the model output without losing the original estimate. The tab and each sub-tool are independently removable without affecting any other part of the application.

| Tool | Purpose |
|---|---|
| **Hiring Budget Estimator** | Predict salary for a role profile and compute total annual payroll cost given headcount and adjustable employer cost assumptions (benefits %, overhead %, one-time recruiting cost); bar chart cost breakdown and CSV export |
| **Salary Benchmarking Table** | Generate a reference grid of model predictions across all experience levels for a selected role and location; editable in-place with HR Override, Band Min, Band Max, and Internal Notes columns; exported as CSV |
| **Candidate Comparison** | Compare expected salary for 2 to 5 candidates side by side; each candidate has independent profile inputs and an optional individual override; salary spread flagged; CSV export |
| **Offer Competitiveness Checker** | Compare a planned offer against the model's salary estimate using a gauge chart; tiered interpretive guidance; CSV export |
| **Team Compensation Audit** | Upload a CSV of current team salaries; vectorised batch predictions run once on upload and cached in session state; configurable underpaid/overpaid thresholds and a global percentage adjustment for systematic model offset; scatter plot, delta histogram, flagged records table; CSV export |

**HR override system:** every tool exposes a collapsible override section allowing the model estimate to be replaced with an internal reference value. Override reasons are captured as free text and included in all CSV exports alongside the original model estimate.

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

## Model Hub

The Model Hub is a separate tab that allows admins to upload additional independently trained models and make them available to logged-in users, without changing application code.

### How it works

Admins train models offline and upload a bundle in one of two formats:

**ONNX format (recommended):**

| File | Required | Purpose |
|---|---|---|
| `model.onnx` | Yes | ONNX-serialised computation graph — no arbitrary code execution on load |
| `columns.json` | Yes | JSON array of feature column names the model expects |
| `schema.json` | Yes | Defines the user-facing input fields and their UI widget types |
| `aliases.json` | No | Display labels for selectbox model values |
| `skills.json` | No | Per-bundle skill lexicon for resume extraction (overrides global) |
| `job_titles.json` | No | Per-bundle job title alias map for resume extraction (overrides global) |
| `resume_config.json` | No | Per-bundle resume extraction config (overrides engine defaults for scoring, keywords, thresholds, and field mappings) |

**Pickle format (legacy, backward-compatible):**

| File | Required | Purpose |
|---|---|---|
| `model.pkl` | Yes | Trained sklearn-compatible estimator, serialized with joblib |
| `columns.pkl` | Yes | Ordered list of feature column names the model expects |
| `schema.json` | Yes | Defines the user-facing input fields and their UI widget types |
| `aliases.json` | No | Display labels for selectbox model values |
| `skills.json` | No | Per-bundle skill lexicon for resume extraction (overrides global) |
| `job_titles.json` | No | Per-bundle job title alias map for resume extraction (overrides global) |
| `resume_config.json` | No | Per-bundle resume extraction config (overrides engine defaults for scoring, keywords, thresholds, and field mappings) |

Each upload creates a versioned folder in a private HuggingFace dataset repo (`models/model_<timestamp>_<id>/`). Bundles are never overwritten. A registry file (`models_registry.json`) tracks all uploaded models, their active status, and their bundle format.

### What users see

- A dropdown listing only active, registered models
- A Model Card expander showing structured metadata (intended use, metrics, training data, authors, links) when populated by the admin
- Four prediction modes after loading a bundle: Manual (single prediction with styled result card), Batch (CSV/XLSX upload with distribution chart and downloads), Resume (PDF extraction with editable review form and quality score), and Scenario (up to 5 named scenarios with comparison chart and optional sensitivity sweep)
- In Batch and Resume modes, uploading a new file clears previous results automatically; a Clear button is also available
- In Scenario mode, input fields are plain widgets — no save step is required before running
- No access to upload, registry management, or schema editing

### What admins can do

- Upload a complete bundle (ONNX: model.onnx + columns.json + schema.json, or Pickle: model.pkl + columns.pkl + schema.json)
- Attach Model Card metadata (intended use, out-of-scope, limitations, ethical notes, metrics, training data, authors, license, tags, links) at upload time via structured form fields and a raw JSON override
- Upload an optional aliases.json alongside the bundle, or push one separately after upload
- Upload optional per-bundle lexicons (skills.json, job_titles.json) to override global resume extraction defaults for this specific model
- Upload an optional resume_config.json alongside the bundle, or push one separately after upload, to override extraction engine defaults (scoring weights, keyword lists, experience thresholds, field-name mappings, preprocessing) for this specific model
- Activate or deactivate models from the Registry Manager
- Roll back to an earlier version within a model family
- Edit or create schema.json using a visual field builder with multi-column layout settings and result card label, then download it
- Upload a replacement schema.json, aliases.json, or resume_config.json to an existing bundle without re-uploading the model

### Schema system

`schema.json` defines the prediction form entirely. Supported field types:

```json
{
  "layout": { "columns": 2 },
  "result_label": "Predicted Annual Salary (USD)",
  "fields": [
    { "name": "experience_years", "type": "int",      "ui": "slider",    "min": 0, "max": 20,
      "row": 1, "col_span": 2 },
    { "name": "job_title",        "type": "category", "ui": "selectbox", "values": ["Data Scientist", "ML Engineer"],
      "row": 2, "col_span": 1 },
    { "name": "remote_ratio",     "type": "int",      "ui": "slider",    "min": 0, "max": 100,
      "row": 2, "col_span": 1 }
  ]
}
```

Supported `ui` values: `slider`, `selectbox`, `number_input`, `text_input`, `checkbox`.

**Optional top-level keys:**
- `layout.columns` (1, 2, or 3) — arrange fields in a responsive grid. Omitting gives a single-column form identical to existing schemas.
- `result_label` — label on the prediction result card. Overrides the registry target name.
- `plots` — list of chart descriptors rendered automatically in the appropriate mode. Supported types: `gauge`, `bar`, `horizontal_bar`, `scatter`, `histogram`, `line`. Charts with `x_field`/`y_field` use batch or scenario result data; `gauge` and single-value bar charts use the scalar prediction result.
- `scenario_sweep` — configures a sensitivity sweep in Scenario mode. Fields: `field` (schema field to vary), `mode` (`range` or `values`), `min`/`max`/`steps` for range mode, `values` and `value_labels` for discrete mode.

**Optional per-field layout keys:**
- `row` — integer; fields sharing the same row number are placed side-by-side.
- `col_span` — 1, 2, or 3; how many grid columns the field occupies. All layout keys are fully optional.

**Optional per-field extractor hint (Resume mode):**
- `extractor` — explicitly selects which resume extractor to use for this field, overriding the default name-based selection. Supported values: `experience`, `education`, `country_name`, `country_iso`, `senior_flag`, `job_title`, `employment_type`, `remote_ratio`, `skills_list`, `skills_str`, `age`.

### resume_config.json — per-bundle extraction override

An optional `resume_config.json` sidecar can be included in any bundle to override the resume extraction engine defaults for that specific model. Every key is optional — include only the settings you want to change. Bundles without this file continue to use the engine built-in defaults exactly as before.

`resume_config.json` is validated before upload (same as `aliases.json`) and can be pushed to an existing bundle without re-uploading the model via the Schema Editor tab.

#### Supported top-level keys

| Key | Type | Purpose |
|---|---|---|
| `scoring` | object | Override scoring dimension weights and rubric |
| `extractors` | object | Override per-extractor keyword lists, patterns, and thresholds |
| `field_name_mapping` | array | Prepend extra keyword-to-extractor-id mappings |
| `preprocessing` | object | Override text preprocessing flags |

#### scoring block

```json
"scoring": {
  "experience_max":   40,
  "education_max":    30,
  "skills_max":       30,
  "skills_per_point": 3,

  "thresholds": {
    "entry":  { "max": 2,   "score": 8,  "note": "Entry level" },
    "mid":    { "max": 8,   "score": 20, "note": "Mid-level" },
    "senior": { "max": 9999,"score": 40, "note": "Senior level" }
  },

  "edu_map": {
    "0": [5,  "High school level"],
    "1": [15, "Bachelor level"],
    "2": [22, "Master level"],
    "3": [30, "PhD level"]
  }
}
```

- `experience_max`, `education_max`, `skills_max` — maximum points for each scoring dimension. The three values do not need to sum to 100; the total is capped at 100 after summing.
- `skills_per_point` — points awarded per detected skill. `skill_score = min(skill_count * skills_per_point, skills_max)`.
- `thresholds` — named experience scoring bands. Each key is an arbitrary band name; each value requires `max` (upper bound in years), `score` (points to award), and `note` (display string). Bands are sorted by `max` ascending at runtime; the first band whose `max` >= detected years is applied.
- `edu_map` — education level scoring. Keys are string level integers (`"0"`, `"1"`, ...). Each value is a `[score, note]` pair. The engine's `education` extractor returns an integer level (0 = lowest education, 3 = highest by default). If your model's education field maps to a different number of levels you can extend the map to cover them (e.g. add `"4"` for a fifth level).

#### extractors block

Each key is a supported extractor identifier. Only include extractors you want to override.

```json
"extractors": {
  "experience": {
    "max_years": 35,
    "patterns": [
      "(\\d+(?:\\.\\d+)?)\\+?\\s*(?:years?|yrs?)\\s+(?:of\\s+)?(?:engineering)?\\s*experience",
      "(\\d+(?:\\.\\d+)?)\\+?\\s*(?:years?|yrs?)"
    ]
  },

  "senior_flag": {
    "keywords": ["senior", "lead", "principal", "professor", "fellow"],
    "experience_threshold": 13
  },

  "remote_ratio": {
    "remote_keywords":  ["fully remote", "wfh", "distributed team"],
    "hybrid_keywords":  ["hybrid", "flexible working", "split week"],
    "onsite_keywords":  ["on-site", "lab-based", "campus-based"]
  },

  "employment_type": {
    "part_time_keywords":  ["part-time", "intern", "trainee"],
    "freelance_keywords":  ["freelance", "independent consultant"],
    "contract_keywords":   ["contract", "fixed-term", "research fellowship"]
  },

  "age": {
    "min_age": 18,
    "max_age": 80
  },

  "job_title": {
    "keyword_fallback": [
      [["aerospace engineer", "aeronautical engineer"], "Aerospace Engineer"],
      [["data scientist", "applied scientist"],         "Data Scientist"]
    ]
  }
}
```

**Supported extractor ids and their override params:**

| Extractor id | Params | Effect |
|---|---|---|
| `experience` | `max_years` (number), `patterns` (list of regex strings) | Replaces the built-in pattern list when `patterns` is provided. `max_years` caps the upper bound of valid values found. |
| `senior_flag` | `keywords` (list of strings), `experience_threshold` (number) | Replaces the built-in keyword list when `keywords` is provided. `experience_threshold` overrides the years-of-experience auto-senior threshold (default 6). |
| `remote_ratio` | `remote_keywords`, `hybrid_keywords`, `onsite_keywords` (each a list of strings) | Replaces the built-in keyword list for whichever groups are provided. Missing groups fall back to built-in. |
| `employment_type` | `part_time_keywords`, `freelance_keywords`, `contract_keywords` (each a list of strings) | Same per-group replacement pattern as remote_ratio. |
| `age` | `min_age` (int), `max_age` (int) | Overrides the valid age range for the age extractor. |
| `job_title` | `keyword_fallback` (list of `[[keywords], title]` pairs) | Replaces the entire built-in keyword fallback list. Each entry is `[[kw1, kw2, ...], "Canonical Title"]`. Canonical titles must match a value in the schema field's `values` list exactly. |

All keyword overrides for a given group replace the built-in list entirely for that group — they do not append. To keep a built-in keyword, include it explicitly in the override list.

#### field_name_mapping

```json
"field_name_mapping": [
  ["years_experience", "experience"],
  ["work_mode",        "remote_ratio"],
  ["is_management",    "senior_flag"]
]
```

Each entry is a `[keyword_string, extractor_id_string]` pair. These are prepended to the built-in field-name lookup table and take priority over it. The keyword is matched as a substring of the lowercased schema field name. This allows models with non-standard field names (such as `years_experience` instead of `experience_years`) to route correctly without adding an explicit `"extractor"` key to every field in `schema.json`.

#### preprocessing block

```json
"preprocessing": {
  "strip_urls":      true,
  "max_text_length": 0
}
```

- `strip_urls` (bool, default `true`) — remove http and www URLs from the resume text before extraction. Useful to disable if URLs contain domain names the country extractor should read.
- `max_text_length` (int, default `0`) — truncate extracted text to this many characters before any extraction. `0` means no truncation. Useful for very long academic CVs where truncating early improves extraction speed at the cost of missing content in the tail.

#### Validation rules

`resume_config.json` is validated by `validator.validate_resume_config()` before upload. Rules:

- Unrecognised top-level keys produce a warning but do not block upload (forward-compatible).
- Unrecognised extractor ids produce a warning and the section is ignored.
- `thresholds` entries must each have `max` (number), `score` (number), and `note` (string).
- `edu_map` keys must be string integers; values must be `[score, note]` pairs.
- `field_name_mapping` entries must each be a two-element `[string, string]` list.
- `keyword_fallback` entries must each be `[[string, ...], string]`.
- Structural errors (wrong types, malformed JSON) block upload.

#### Relationship to other per-bundle sidecars

`resume_config.json` controls **how** extraction runs (scoring, keywords, thresholds). The lexicon sidecars control **what** it recognises:

| Sidecar | Controls |
|---|---|
| `skills.json` | Which skill phrases are detected (replaces global skills lexicon) |
| `job_titles.json` | Which job title aliases are recognised (replaces global job titles lexicon) |
| `resume_config.json` | Scoring weights, extractor keyword lists, experience thresholds, field-name routing |

All three are independent and optional. Any combination is valid.

### Column mapping

The predictor maps schema fields to model columns automatically:

- **Direct match** — field name equals column name
- **One-hot expansion** — a `selectbox` field named `job_title` with values `["Data Scientist", "ML Engineer"]` maps to columns `job_title_Data Scientist` and `job_title_ML Engineer` (sklearn get_dummies convention)
- **Unmatched columns** — filled with `0.0`; a warning is shown if this occurs

### Access control

- The tab requires login to access
- Upload, Registry Manager, and Schema Editor are visible only to admin users
- Non-admin users see only the model selector and prediction form

### Storage

Models are stored in a private HuggingFace dataset repo configured via `st.secrets`. Required secrets:

```toml
HF_TOKEN   = "hf_xxxxxxxxxxxxxxxxxxxx"   # write-scope token
HF_REPO_ID = "your-username/your-repo"  # dataset repo
```

### Security notes

- ONNX bundles (model.onnx) are loaded via onnxruntime — no arbitrary code execution on deserialisation. This is the recommended format for new uploads.
- Pickle bundles (model.pkl) are deserialized using joblib (which uses pickle internally). Only upload pickle bundles you have trained yourself.
- File size limits are enforced: 200 MB for model files, 10 MB for columns files, 512 KB for schema.json and aliases.json.
- The tab is auth-gated — unauthenticated users cannot access it.

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
├── app_resume.py                        # Full app entry point (all features)
├── app-lite.py                               # Lite app entry point (core features only)
│
├── app/
│   ├── core/
│   │   ├── auth.py                      # Firebase Authentication (login, register, session)
│   │   ├── database.py                  # Firestore client, user and prediction functions
│   │   ├── email_verification.py        # Email verification flow and UI handling
│   │   ├── password_policy.py           # NIST SP 800-63B password validation
│   │   ├── rate_limiter.py              # Two-layer brute-force protection (session + Firestore)
│   │   ├── account_management.py        # Account actions (change password, delete account)
│   │   ├── insights_engine.py           # Domain detection, market comparison, recommendations
│   │   └── resume_analysis.py           # Resume parsing (spaCy, regex, feature extraction)
│   │
│   ├── model_hub/                       # Model Hub package
│   │   ├── __init__.py
│   │   ├── _hf_client.py                # HuggingFace SDK wrapper (download, upload, listing)
│   │   ├── registry.py                  # Registry read/write (models_registry.json)
│   │   ├── loader.py                    # Bundle download, deserialization, session cache
│   │   ├── predictor.py                 # Feature vector construction and model.predict()
│   │   ├── schema_parser.py             # schema.json -> Streamlit widgets
│   │   ├── uploader.py                  # Bundle validation and upload to HuggingFace
│   │   ├── validator.py                 # Schema, aliases, and resume_config validation
│   │   └── extended_modes/              # Schema-driven prediction modes for Model Hub
│   │       ├── __init__.py
│   │       ├── hub_manual_tab.py        # Manual prediction mode
│   │       ├── hub_batch_tab.py         # Batch prediction mode (CSV/XLSX, file-change auto-clear)
│   │       ├── hub_resume_tab.py        # Resume analysis mode (PDF extraction, auto-clear)
│   │       ├── hub_resume_engine.py     # Data-driven extraction engine (spaCy + JSON lexicons + resume_config)
│   │       ├── hub_scenario_tab.py      # Scenario analysis mode (plain widgets, no save step)
│   │       ├── model_card.py            # Model Card UI component
│   │       ├── schema_plots.py          # Chart renderer for schema plots key
│   │       └── lexicons/                # Shared global extraction lexicons (JSON, extensible)
│   │           ├── skills.json          # 450+ skills across 20+ categories
│   │           ├── job_titles.json      # 50+ canonical titles with alias lists
│   │           ├── education.json       # Education level regex patterns
│   │           └── countries.json       # Country aliases -> display names and ISO-2 codes
│   │
│   ├── tabs/
│   │   ├── manual_prediction_tab.py     # Manual Prediction
│   │   ├── resume_analysis_tab.py       # Resume Prediction (full app only)
│   │   ├── batch_prediction_tab.py      # Batch Prediction
│   │   ├── scenario_analysis_tab.py     # Scenario Analysis (full app only)
│   │   ├── model_analytics_tab.py       # Model Analytics
│   │   ├── data_insights_tab.py         # Data Insights
│   │   ├── model_hub_tab.py             # Model Hub UI (full app only)
│   │   ├── hr_tools_tab.py              # HR Tools entry point (full app only)
│   │   ├── user_profile.py              # User profile and prediction history
│   │   ├── admin_panel.py               # Admin diagnostics and monitoring (full app only)
│   │   └── about_tab.py                 # About tab (full app; lite app uses inline version)
│   │
│   ├── hr_tools/                        # HR & Employer Tools package
│   │   ├── __init__.py
│   │   ├── predict_helpers.py           # Single-row and vectorised batch inference wrappers; HR override widget
│   │   ├── hiring_budget.py             # Hiring Budget Estimator
│   │   ├── benchmarking_table.py        # Salary Benchmarking Table (cached grid)
│   │   ├── candidate_comparison.py      # Candidate Comparison (2-5 candidates)
│   │   ├── offer_checker.py             # Offer Competitiveness Checker
│   │   └── team_audit.py               # Team Compensation Audit (vectorised batch)
│   │
│   ├── utils/
│   │   ├── country_utils.py             # Centralised country/ISO-2 resolution (Babel CLDR)
│   │   ├── currency_utils.py            # Currency conversion (live rates, fallback)
│   │   ├── tax_utils.py                 # Post-tax salary estimation (progressive brackets)
│   │   ├── col_utils.py                 # Cost-of-living adjustment (PPP comparison)
│   │   ├── ctc_utils.py                 # CTC structure breakdown
│   │   ├── takehome_utils.py            # Net take-home salary estimation
│   │   ├── savings_utils.py             # Savings potential calculator
│   │   ├── loan_utils.py                # Loan affordability estimator (EMI formula)
│   │   ├── budget_utils.py              # Monthly budget allocation planner
│   │   ├── investment_utils.py          # Investment growth projection (compound FV)
│   │   ├── emergency_fund_utils.py      # Emergency fund target and build timeline
│   │   ├── lifestyle_utils.py           # Lifestyle budget split (discretionary spending)
│   │   ├── pdf_utils.py                 # PDF report generation (ReportLab)
│   │   ├── feedback.py                  # Prediction feedback UI and Firestore save
│   │   ├── recommendations.py           # Career recommendations engine
│   │   └── negotiation_tips.py          # Salary negotiation tips engine
│
├── model/                               # Model artefacts (loaded from HuggingFace at runtime)
│   ├── rf_model_grid.pkl                # Model 1: Random Forest
│   ├── salary_band_classifier.pkl       # Model 1: Salary level classifier
│   ├── career_cluster_pipeline.pkl      # Model 1: KMeans clustering
│   ├── app1_analytics.pkl               # Model 1: Precomputed analytics
│   ├── ds_xgb_model_grid.pkl            # Model 2: XGBoost
│   └── app2_analytics.pkl               # Model 2: Precomputed analytics
│
├── notebooks/                           # Jupyter notebooks for EDA and model development
├── powerbi/                             # Power BI dashboards
│
├── docs/                                # Project documentation
│   ├── data_dictionary.md               # All data schemas, field definitions, encodings
│   ├── design_document.md               # Architecture, module design, data flows
│   ├── user_guide.md                    # Step-by-step user instructions
│   ├── srs.md                           # Software Requirements Specification
│   ├── module_reference.md              # All public functions documented
│   ├── deployment.md                    # Deployment and operations guide
│   ├── testing.md                       # Test plan, unit tests, manual test cases
│   └── model_hub_extended_schema.md     # Extended schema reference (plots, scenario_sweep, lexicons, extractors, resume_config)
│   
├── samples/                             # Sample input files for batch prediction
├── assets/                              # Branding and visual assets
├── pdf_outputs/                         # Sample generated PDF reports
│
├── data/
│   ├── Salary_Streamlit_App.csv         # Model 1 training dataset
│   ├── ds_salaries_Streamlit_App.csv    # Model 2 training dataset
│   ├── association_rules.csv            # Precomputed Apriori association rules
│   └── exchange_rates_fallback.json     # Offline currency rate fallback
│
├── screenshots/
│   ├── manual_prediction.png
│   ├── scenario_analysis.png
│   ├── resume_analysis.png
│   ├── batch_prediction.png
│   └── model_analytics.png
│
├── .streamlit/
│   └── config.toml
│
├── requirements.txt
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## Installation

### Prerequisites

* Python 3.13 (recommended)
* The project may work on lower Python versions, but it has been developed and tested using Python 3.13.
* A Firebase project with Firestore enabled
* A HuggingFace dataset repo (required only if using the Model Hub)


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

Create a `.streamlit/secrets.toml` file in the project root. The full configuration is:

```toml
FIREBASE_API_KEY = "your_firebase_api_key"
ADMIN_EMAIL      = "admin@yourdomain.com"   # Email that receives admin privileges

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

To enable the Model Hub (full app only), add:

```toml
HF_TOKEN   = "hf_xxxxxxxxxxxxxxxxxxxx"   # HuggingFace token with write scope
HF_REPO_ID = "your-username/your-repo"  # Private HuggingFace dataset repo
```

For local development, optionally add:

```toml
IS_LOCAL = true   # Enables local-only features (e.g. CoL index save/reset to disk)
```

The Model Hub will not load if `HF_TOKEN` and `HF_REPO_ID` are absent, but all other tabs remain unaffected. `ADMIN_EMAIL` is required for the Admin Panel tab; without it, no user has admin access.

> **Note:** Never commit `secrets.toml` to version control. Add it to `.gitignore`.

## Important Notes

* Firebase authentication requires valid credentials and may not function without proper configuration.
* The application is fully usable without authentication for core features such as manual prediction, scenario analysis, and model analytics.
* Feedback submission is available to all users including those not logged in.
* Resume parsing requires spaCy language model installation.
* The Model Hub tab requires login to access and requires `HF_TOKEN` and `HF_REPO_ID` to be configured in secrets.

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
  - Explore additional financial insights such as take-home salary, savings potential, CTC breakdown, and loan affordability
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

### Model Hub
1. Log in to access the **Model Hub** tab
2. Select a model from the dropdown — only active, registered models are listed
3. Review the **Model Card** expander for information about the model (if populated by the admin)
4. Click **Load Model** to download the bundle from HuggingFace
5. Choose a prediction mode from the sub-tabs: **Manual**, **Batch**, **Resume**, or **Scenario**
6. In Manual mode: fill in the schema-generated form and click Predict
7. In Batch mode: upload a CSV or XLSX file and click Run — uploading a new file clears previous results automatically
8. In Resume mode: upload a PDF, click Extract, review and edit extracted fields, then click Predict from Resume — uploading a new PDF clears previous results automatically
9. In Scenario mode: fill in each scenario panel directly (no save step needed) and click Run All Scenarios

**Admin only:**
- Go to the **Upload Bundle** tab, fill in model card metadata, select ONNX or Pickle format, optionally attach aliases.json, custom lexicons (skills.json, job_titles.json), and a resume_config.json, and upload
- Use the **Registry Manager** to activate, deactivate, or roll back models
- Use the **Schema Editor** to build or validate a schema.json visually, including plots and scenario_sweep configuration; use the **Upload / Validate** sub-tab to push a replacement schema.json, aliases.json, or resume_config.json to an existing bundle

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
- Source: [Kaggle — Data Science Salaries 2023](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)

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
| Model Storage | HuggingFace Dataset Repo (via huggingface_hub SDK) |
| Security | bcrypt |
| Deployment | Streamlit Cloud |
| Language | Python 3.13+ |
| NLP | spaCy, Regex, PhraseMatcher |
| Country Resolution | Babel (Unicode CLDR territory data) |
| ONNX Runtime | onnxruntime (model inference for Model Hub), skl2onnx (sklearn-to-ONNX conversion) |
| API Integration | ExchangeRate API (open.er-api.com) |

---

## Security Features

* Email verification before account activation (Firebase email link)
* Password policy aligned with NIST SP 800-63B (2024) and OWASP Authentication Cheat Sheet: minimum 12 characters, uppercase, lowercase, digit, special character, no consecutive identical characters, common-password blocklist
* Two-layer rate limiting for all authentication actions (login, registration, password reset, password change, account deletion, email resend): session-state layer (per-tab) + Firestore layer (cross-session) — fails open on any error
* Secure password reset using Firebase email-based OOB code system
* Session management with 24-hour expiry enforced via `st.session_state`
* Firebase-managed authentication — no passwords stored in Firestore or application code
* Rate limit records in Firestore keyed by SHA-256 hash prefix of user email — PII is never stored in document IDs
* Model Hub upload restricted to admin users; file size limits enforced pre- and post-download (model files 200 MB max, schema/aliases/lexicons 512 KB max, resume_config.json 256 KB max); ONNX bundles loaded via onnxruntime (no arbitrary code execution); pickle bundles audited via joblib security log on every load; per-bundle lexicon and config JSON files are plain data with no execution risk
* Admin role determined by server-side email comparison only (case-insensitive, from `st.secrets`)

> Note: These features are implemented for application-level security and demonstration purposes. For production systems, additional hardening would be appropriate.

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

pending_verifications/
  {email}/
    email, id_token, created_at
    (temporary — deleted after email verification is confirmed)

rate_limits/
  {action}__{sha256_prefix}/
    attempts, window_start
    (keyed by hash of email — PII never stored in document IDs)
```

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
- CTC breakdown uses approximate country-level salary structures and may not reflect actual employer-specific compensation components.
- Take-home salary estimation uses effective tax rates and simplified deduction models; real payroll calculations may differ.
- Savings estimates are based on generalized expense ratios and do not account for individual lifestyle or financial obligations.
- Loan affordability calculations use standard EMI formulas and typical lender norms, but actual loan eligibility depends on credit profile and bank policies.
- Model Hub pickle bundles (model.pkl) are deserialized using joblib. Only upload pickle files from sources you control entirely. ONNX bundles (model.onnx) do not carry this risk.
- Model Hub predictions are only as reliable as the model and data used during training — the system does not validate model quality.

---

## Future Scope

- Improve model performance by training on larger and more recent datasets.
- Enhance resume parsing using more advanced NLP techniques (e.g. transformer-based models) for better accuracy across diverse resume formats.
- Expand the system to support additional job roles and domains beyond current datasets.
- Use collected feedback data to retrain or calibrate models over time.
- Enhance financial estimation modules (CTC, take-home, savings, loan) with more accurate country-specific rules and real-world datasets.
- Integrate detailed tax systems with deductions, exemptions, and region-specific regulations for improved take-home accuracy.
- Extend ONNX support in the Model Hub to additional model architectures beyond sklearn-compatible estimators (e.g. PyTorch, TensorFlow via tf2onnx).
- Add education and country pattern lexicons as optional per-bundle sidecars (currently skills, job titles, and extraction config are per-bundle overridable; education patterns and country aliases still use only global lexicons).
- Expose the spaCy model version as a configurable parameter in the extraction engine to support multilingual resume parsing.
- Allow `resume_config.json` to declare custom extractor functions by reference (plugin pattern) so model owners can add entirely new field extractors without forking the engine.
- Add city-level cost-of-living data to improve the granularity of COL adjustments beyond country averages.
- Implement real-time salary market data integration for more current predictions.
- Add Google OAuth as an alternative authentication method (infrastructure is partially scaffolded).
- Expand HR Tools with job-market demand data integration (live posting counts via a public API) to complement model-based salary estimates with demand signals.
- Add city-level cost-of-living support to the HR Team Audit so compensation gaps can be assessed at city granularity, not just country level.
- Expose HR Tools benchmarking grid as a downloadable formatted PDF report consistent with the existing ReportLab report system.

---

## Documentation

Detailed project documentation is available in the `docs/` directory:

| Document | Description |
|---|---|
| [`data_dictionary.md`](docs/data_dictionary.md) | All data schemas, Firestore collections, model artefacts, field definitions, and encodings |
| [`design_document.md`](docs/design_document.md) | Software architecture, module design, data flows, design decisions |
| [`user_guide.md`](docs/user_guide.md) | Step-by-step instructions for every feature |
| [`srs.md`](docs/srs.md) | Software Requirements Specification (functional and non-functional requirements) |
| [`module_reference.md`](docs/module_reference.md) | Every public function documented with parameters, returns, and side effects |
| [`deployment.md`](docs/deployment.md) | Firebase setup, HuggingFace setup, Streamlit Cloud deployment, secrets reference |
| [`testing.md`](docs/testing.md) | Test plan, unit test code, manual test cases, and test results log template |
| [`model_hub_extended_schema.md`](docs/model_hub_extended_schema.md) | Extended schema reference: plots, scenario_sweep, per-bundle lexicons (skills.json, job_titles.json), extractor hints, and resume_config.json full format |


---

## References

- Python Documentation — https://docs.python.org/3/
- Streamlit Documentation — https://docs.streamlit.io  
- Scikit-learn Documentation — https://scikit-learn.org  
- XGBoost Documentation — https://xgboost.readthedocs.io  
- SHAP Documentation — https://shap.readthedocs.io
- HuggingFace Hub Documentation — https://huggingface.co/docs/huggingface_hub
- Firebase Documentation — https://firebase.google.com/docs
- spaCy Documentation — https://spacy.io/usage
- Pandas Documentation — https://pandas.pydata.org/docs/
- NumPy Documentation — https://numpy.org/doc/
- Plotly Documentation — https://plotly.com/python/
- ExchangeRate API — https://www.exchangerate-api.com/docs/overview
- Kaggle — Salary by Job Title and Country — https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country
- Kaggle — Data Science Salaries 2023 — https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023

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