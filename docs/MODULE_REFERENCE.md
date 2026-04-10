# SalaryScope — Module & API Reference

> **Version 1.0 · April 2026**  
> Internal reference for developers working with the SalaryScope codebase.

---

## Overview

SalaryScope is composed of a main Streamlit application (`app_resume.py`) and a set of supporting Python modules. This document describes the public interface (functions, parameters, return values) of each module, intended for developers who wish to extend, maintain, or integrate parts of the system.

---

## Module Index

| Module | File | Purpose |
|---|---|---|
| [Resume Analysis](#resume_analysispy) | `resume_analysis.py` | spaCy + regex + phrase-matching based resume parsing and scoring |
| [Authentication](#authpy) | `auth.py` | Firebase Authentication (login, register, session) |
| [Database](#databasepy) | `database.py` | Firestore read/write operations |
| [Feedback](#feedbackpy) | `feedback.py` | Prediction feedback UI and storage |
| [Insights Engine](#insights_enginepy) | `insights_engine.py` | Salary insights generation |
| [Recommendations](#recommendationspy) | `recommendations.py` | Career recommendation engine |
| [Negotiation Tips](#negotiation_tipspy) | `negotiation_tips.py` | Salary negotiation tips engine |
| [PDF Utils](#pdf_utilspy) | `pdf_utils.py` | ReportLab PDF generation |
| [Currency Utils](#currency_utilspy) | `currency_utils.py` | Currency conversion and UI |
| [Tax Utils](#tax_utilspy) | `tax_utils.py` | Post-tax estimation and UI |
| [COL Utils](#col_utilspy) | `col_utils.py` | Cost-of-living adjustment and UI |
| [User Profile](#user_profilepy) | `user_profile.py` | Profile tab UI and prediction history |
| [Admin Panel](#admin_panelpy) | `admin_panel.py` | Admin diagnostics dashboard |

---

## `resume_analysis.py`

Handles resume feature extraction using spaCy (NER + PhraseMatcher) combined with rule-based methods (regex and keyword matching).

---

### `extract_text_from_pdf(file) -> str`

Extracts all text content from an uploaded PDF file using `pdfplumber`.

**Parameters**:
- `file` — a file-like object (e.g., Streamlit `UploadedFile`)

**Returns**: A single string containing all extracted text, with page breaks normalized.

**Behavior**: Returns an empty string if no text can be extracted.

---

### `extract_resume_features(raw_text: str, allowed_job_titles: list[str], allowed_countries: list[str]) -> dict`

Extracts structured professional features from raw resume text for **Model 1** (General Salary).

**Parameters**:
- `text` — raw text string from `extract_text_from_pdf()`

**Returns**: A dictionary with keys:

| Key | Type | Description |
|---|---|---|
| `job_title` | str | Detected job title |
| `years_experience` | float | Years of professional experience |
| `skills` | list[str] | List of detected technical/professional skills |
| `education_level` | int | 0 = High School, 1 = Bachelor's, 2 = Master's, 3 = PhD |
| `country` | str | Detected country name |

**Notes**: Uses spaCy NER (for country), PhraseMatcher (for skills), and regex patterns (for experience and education keywords).

---

### `extract_resume_features_a2(raw_text: str, allowed_job_titles_a2: list[str], allowed_iso_codes_a2: list[str]) -> dict`

Extracts features from resume text for **Model 2** (Data Science Salary).

**Parameters**:
- `text` — raw text string

**Returns**: A dictionary with Model 2-compatible keys:

| Key | Type | Description |
|---|---|---|
| `job_title` | str | Detected job title |
| `experience_level` | str | EN / MI / SE / EX |
| `employee_residence` | str | ISO country code |
| `employment_type` | str | FT / PT / CT / FL |
| `remote_ratio` | int | 0 / 50 / 100 |
| `company_size` | str | S / M / L |
| `company_location` | str | ISO country code |

---

### `calculate_resume_score(features: dict) -> dict`

Computes a resume quality score (0–100) for Model 1 features.

**Parameters**:
- `features` — output dictionary from `extract_resume_features()`

**Returns**: A float in the range [0, 100].

**Scoring Components**:
- Experience: proportional to years (max contribution at ~15+ years)
- Education: mapped by level (0→10, 1→25, 2→35, 3→40 points)
- Skills: based on unique skill count (capped)

---

### `calculate_resume_score_a2(features: dict) -> dict`

Computes a resume quality score for Model 2 features.

**Parameters**:
- `features` — output dictionary from `extract_resume_features_a2()`

**Returns**: A float in the range [0, 100].

---

### `education_label(level: int) -> str`

Converts an integer education level to a human-readable label.

**Parameters**:
- `level` — integer (0, 1, 2, or 3)

**Returns**: One of `"High School"`, `"Bachelor's"`, `"Master's"`, `"PhD"`.

---

### `APP2_ALLOWED_ISO_CODES_A2`

A module-level set containing all valid ISO country codes accepted by Model 2's input pipeline. Used for validation in the resume extraction pipeline.

---

## `auth.py`

Handles user registration, login, session management, and admin verification via Firebase Authentication.

---

### `register_ui() -> None`

Renders the registration form in the Streamlit sidebar. Handles form submission, Firebase user creation, and Firestore profile initialization.

---

### `login_ui() -> None`

Renders the login form in the Streamlit sidebar. On successful authentication, sets `st.session_state.logged_in_user` and `st.session_state.login_time`.

---

### `logout() -> None`

Clears `st.session_state.logged_in_user` and related session data, effectively ending the user session.

---

### `get_logged_in_user() -> str | None`

Returns the email of the currently logged-in user, or `None` if no user is authenticated.

Also checks session expiry (24-hour limit) and calls `logout()` automatically if expired.

**Returns**: Email string or `None`.

---

### `is_admin(email: str) -> bool`

Checks whether the provided email belongs to an authorized administrator.

**Parameters**:
- `email` — user's email address

**Returns**: `True` if admin, `False` otherwise.

---

## `database.py`

Manages Firestore database initialization and all data persistence operations.

---

### `init_db() -> None`

Initializes the Firebase Admin SDK using credentials from `st.secrets["FIREBASE_SERVICE_ACCOUNT"]`. Safe to call multiple times — subsequent calls are no-ops if the SDK is already initialized.

---

### `create_prediction_table() -> None`

Ensures the required Firestore collection structure exists. Creates placeholder documents if collections are empty.

---

### `save_prediction(email: str, model_used: str, input_data: dict, predicted_salary: float) -> None`

Saves a prediction record to Firestore under `predictions/{email}/records/`.

**Parameters**:
- `email` — user's email
- `model_used` — `"Model 1"` or `"Model 2"`
- `input_data` — dictionary of all input features used for the prediction
- `predicted_salary` — the predicted annual salary in USD

---

### `get_predictions(email: str) -> list[dict]`

Retrieves all prediction records for a given user from Firestore.

**Parameters**:
- `email` — user's email

**Returns**: A list of prediction dictionaries, each containing `model_used`, `input_data`, `predicted_salary`, and `created_at`.

---

### `delete_expired_sessions() -> None`

Cleans up stale session entries from Firestore (if session data is persisted). Called on application startup.

---

## `feedback.py`

Provides the feedback collection UI and storage functionality.

---

### `feedback_ui(model_used: str, input_data: dict, predicted_salary: float) -> None`

Renders the complete feedback form as a Streamlit `st.expander`. Handles form submission and writes data to the `feedback/` Firestore collection.

**Parameters**:
- `model_used` — `"Model 1"` or `"Model 2"`
- `input_data` — dictionary of prediction inputs (stored alongside feedback for traceability)
- `predicted_salary` — the predicted annual salary for this prediction

**Behavior**:
- Uses a session state flag to prevent double submission in the same session.
- Optionally displays an extended feedback form for richer data collection.
- Stores `extended_data` as a nested map in Firestore if extended form is filled.

---

## `insights_engine.py`

Generates human-readable salary insights based on prediction context.

---

### `generate_insights_app1(input_data: dict, predicted_salary: float, salary_level: str, career_stage: str) -> str`

Generates a contextual insight string for a Model 1 prediction.

**Parameters**:
- `input_data` — prediction input features
- `predicted_salary` — predicted annual salary (USD)
- `salary_level` — one of `"Early Career Range"`, `"Professional Range"`, `"Executive Range"`
- `career_stage` — one of `"Entry Stage"`, `"Growth Stage"`, `"Leadership Stage"`

**Returns**: A formatted markdown string with salary context and interpretation.

---

### `generate_insights_app2(input_data: dict, predicted_salary: float) -> str`

Generates a contextual insight string for a Model 2 prediction.

**Parameters**:
- `input_data` — Model 2 input features
- `predicted_salary` — predicted annual salary (USD)

**Returns**: A formatted markdown string with domain-specific salary context.

---

## `recommendations.py`

Generates career recommendation text based on prediction context.

---

### `generate_recommendations_app1(input_data: dict, salary_level: str, career_stage: str) -> list[str]`

Generates career development recommendations for a Model 1 prediction.

**Returns**: A list of recommendation strings.

---

### `generate_recommendations_app2(input_data: dict, predicted_salary: float) -> list[str]`

Generates recommendations for a Model 2 prediction.

**Returns**: A list of recommendation strings.

---

### `render_recommendations(recommendations: list[str]) -> None`

Renders a list of recommendation strings as formatted Streamlit UI elements.

---

## `negotiation_tips.py`

Generates salary negotiation tips based on prediction context.

---

### `generate_negotiation_tips_app1(input_data: dict, salary_level: str, career_stage: str) -> list[str]`

Generates negotiation tips for a Model 1 prediction context.

**Returns**: A list of tip strings.

---

### `generate_negotiation_tips_app2(input_data: dict, predicted_salary: float) -> list[str]`

Generates negotiation tips for a Model 2 prediction context.

**Returns**: A list of tip strings.

---

### `render_negotiation_tips(tips: list[str]) -> None`

Renders negotiation tips as formatted Streamlit UI elements.

---

## `pdf_utils.py`

Generates multi-page PDF reports using ReportLab. All functions return a `BytesIO` object for direct use with `st.download_button`.

---

### `app1_generate_manual_pdf(input_data, result, insights, recommendations, tips, currency_info, tax_info, col_info) -> BytesIO`

Generates a Model 1 manual prediction PDF report.

---

### `app1_generate_resume_pdf(input_data, result, resume_score, insights, recommendations, tips) -> BytesIO`

Generates a Model 1 resume-based prediction PDF report.

---

### `app1_generate_bulk_pdf(batch_df, summary_stats) -> BytesIO`

Generates a Model 1 batch prediction analytics PDF report.

---

### `app1_generate_scenario_pdf(scenarios, scenario_results) -> BytesIO`

Generates a Model 1 scenario comparison PDF report.

---

### `cached_app1_model_analytics_pdf() -> BytesIO`

Generates and caches the Model 1 model analytics PDF. Caching avoids redundant generation on each Streamlit rerun.

---

All `app2_*` equivalents follow identical signatures and return types but are tailored to Model 2's output schema.

---

## `currency_utils.py`

Handles live and fallback currency conversion.

---

### `get_active_currency() -> str`

Returns the currently selected currency code from session state (e.g., `"EUR"`, `"INR"`).

---

### `get_active_rates() -> dict`

Returns the currently active exchange rate dictionary. Attempts live fetch, then local fallback, then built-in rates.

**Returns**: A dictionary mapping ISO currency codes to exchange rates relative to USD.

---

### `render_currency_converter(predicted_salary: float, country: str) -> None`

Renders the full currency conversion UI panel (toggle, currency selector, converted salary display) in Streamlit.

**Parameters**:
- `predicted_salary` — gross annual salary in USD
- `country` — user's country (used for default currency selection)

---

## `tax_utils.py`

Handles post-tax salary estimation.

---

### `render_tax_adjuster(predicted_salary: float, country: str) -> None`

Renders the tax adjustment UI panel in Streamlit.

**Parameters**:
- `predicted_salary` — gross annual salary in USD
- `country` — user's country (used for default tax rate lookup)

**Behavior**: Displays toggle to enable/disable, country-derived effective rate with custom override option, and net salary breakdown.

---

## `col_utils.py`

Handles cost-of-living salary normalization.

---

### `render_col_adjuster(predicted_salary: float, country: str) -> None`

Renders the COL adjustment UI panel in Streamlit.

**Parameters**:
- `predicted_salary` — gross annual salary in USD
- `country` — user's country (used for COL index lookup)

---

## `user_profile.py`

Handles the user profile tab UI and prediction history display.

---

### `show_profile(email: str) -> None`

Renders the complete Profile tab for a logged-in user.

**Parameters**:
- `email` — email of the logged-in user

**Behavior**: Fetches prediction history from Firestore, renders summary dashboard, timeline chart, per-prediction detail viewer, and export buttons.

---

## `admin_panel.py`

Provides system diagnostics and monitoring for administrator users.

---

### `show_admin_panel() -> None`

Renders the complete admin panel. Includes:
- System info (OS, Python version, deployment environment)
- Firebase project status and user count
- Feedback analytics (distribution, model-wise breakdown, ratings)
- Recent activity feed
- RAM usage and cache controls
- Extended local diagnostics (when running locally)

**Access Control**: This function should only be called after confirming `is_admin(email) == True`.

---

## Session State Key Reference

The following `st.session_state` keys are used across the application:

| Key | Type | Description |
|---|---|---|
| `db_initialized` | bool | DB initialization guard |
| `logged_in_user` | str | Email of authenticated user |
| `login_time` | datetime | Timestamp of login (for expiry check) |
| `model_choice` | int | 1 or 2 (active model) |
| `app1_result` | dict | Last Model 1 prediction output |
| `app2_result` | dict | Last Model 2 prediction output |
| `app1_inputs` | dict | Last Model 1 input snapshot |
| `app2_inputs` | dict | Last Model 2 input snapshot |
| `scenarios` | list[dict] | List of scenario input dicts |
| `scenario_results` | list[dict] | List of scenario prediction outputs |
| `batch_df` | DataFrame | Batch prediction results |
| `feedback_submitted_{hash}` | bool | Per-prediction feedback guard |
| `exchange_rates` | dict | Cached exchange rate data |
| `exchange_rates_time` | datetime | Timestamp of last rate fetch |

---

## Model Artifact Loading

Models are loaded using `joblib.load()` at application startup:

```python
import joblib

rf_pipeline    = joblib.load("model/rf_model_grid.pkl")
classifier     = joblib.load("model/salary_band_classifier.pkl")
cluster_pipe   = joblib.load("model/career_cluster_pipeline.pkl")
app1_analytics = joblib.load("model/app1_analytics.pkl")

xgb_pipeline   = joblib.load("model/salaryscope_3755_production_model.pkl")
app2_analytics = joblib.load("model/app2_analytics.pkl")
```

Each `.pkl` file contains a scikit-learn/XGBoost pipeline or a dictionary of pre-computed analytics objects (residuals, SHAP values, feature importances, PCA coordinates, association rules).

---

## Error Handling Conventions

- All external API calls (Firebase, ExchangeRate API) are wrapped in `try/except` blocks.
- User-facing errors are rendered with `st.error()`.
- Informational messages use `st.info()` or `st.warning()`.
- Fallback chains handle degraded operation gracefully (e.g., currency fallback).
- Model loading errors disable the affected feature and display a descriptive message rather than crashing the application.

---

*End of Module & API Reference*