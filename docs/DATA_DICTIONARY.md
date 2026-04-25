# SalaryScope — Data Dictionary
**Version:** 1.3.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Author:** Yash Shah  
**Document Type:** Data Dictionary

---

## Table of Contents

1. [Overview](#1-overview)
2. [Dataset 1 — General Salary Dataset (Model 1)](#2-dataset-1--general-salary-dataset-model-1)
3. [Dataset 2 — Data Science Salaries Dataset (Model 2)](#3-dataset-2--data-science-salaries-dataset-model-2)
4. [Firestore Collections](#4-firestore-collections)
5. [Model Artefacts](#5-model-artefacts)
6. [Model Hub Bundle Schema](#6-model-hub-bundle-schema)
7. [Session State Keys](#7-session-state-keys)
8. [Financial Utility Data](#8-financial-utility-data)
9. [Encoding and Mapping Tables](#9-encoding-and-mapping-tables)
10. [NLP Feature Extraction Fields](#10-nlp-feature-extraction-fields)

---

## 1. Overview

SalaryScope uses two independently trained machine learning models, each backed by a distinct dataset. All persistent data lives in Firebase Firestore. Model artefacts are stored in a private HuggingFace dataset repository. Session state is browser-local (Streamlit `st.session_state`) and does not persist across sessions beyond the 24-hour login token stored in Firestore.

---

## 2. Dataset 1 — General Salary Dataset (Model 1)

**Source:** [Kaggle — Salary by Job Title and Country](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)  
**Model trained on this dataset:** Random Forest Regressor  
**Target variable:** `Salary` (annual, USD)

### 2.1 Raw Input Columns

| Column | Type | Range / Allowed Values | Description |
|---|---|---|---|
| `Age` | Integer | 18 – 70 | Respondent age in years |
| `Years of Experience` | Float | 0.0 – 40.0 | Total professional work experience in years |
| `Education Level` | Integer | 0, 1, 2, 3 | Highest education attained (see encoding below) |
| `Senior` | Integer | 0, 1 | Whether the role is a senior position (1 = Yes, 0 = No) |
| `Gender` | String | Male, Female | Self-reported gender |
| `Job Title` | String | ~100 canonical titles | Job title; mapped to canonical form via alias table |
| `Country` | String | 5 countries + "Other" | Country where the role is based |
| `Salary` | Float | — | Annual gross salary in USD (target variable; not an input) |

### 2.2 Education Level Encoding

| Integer Code | Label |
|---|---|
| 0 | High School |
| 1 | Bachelor's Degree |
| 2 | Master's Degree |
| 3 | PhD |

### 2.3 Derived / Engineered Features (Model 1)

| Feature | Derivation | Used By |
|---|---|---|
| `salary_band` | Classifier output: 0 = Early Career, 1 = Professional, 2 = Executive | `HistGradientBoostingClassifier` |
| `career_stage` | KMeans cluster label: Entry Stage, Growth Stage, Leadership Stage | KMeans clustering model |
| `job_group` | Rule-based: Tech, Management, Marketing\_Sales, HR, Finance, Design, Operations | Insights engine, recommendations |
| `experience_category` | Rule-based: Entry (≤2 yrs), Mid (≤5 yrs), Senior (>5 yrs) | Recommendations, association rules |
| `education_cat` | String label from education integer: High School, Bachelor, Master, PhD | Association rule mining |

### 2.4 Salary Band Labels

| Integer Code | Label |
|---|---|
| 0 | Early Career Range |
| 1 | Professional Range |
| 2 | Executive Range |

### 2.5 Association Rule Fields (Apriori — Model 1)

The association rule mining uses the following categorical attributes derived from inputs:

| Attribute | Possible Values |
|---|---|
| Education | High School, Bachelor, Master, PhD |
| Experience | Entry, Mid, Senior |
| Job Group | Tech, Management, Marketing\_Sales, HR, Finance, Design, Operations |
| Salary Level | Low, Medium, High |

---

## 3. Dataset 2 — Data Science Salaries Dataset (Model 2)

**Source:** [Kaggle — Data Science Salaries 2023](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)  
**Model trained on this dataset:** XGBoost Regressor  
**Target variable:** `salary_in_usd` (log-transformed: `log1p(salary_in_usd)`)

### 3.1 Raw Input Columns

| Column | Type | Allowed Values | Description |
|---|---|---|---|
| `experience_level` | String | EN, MI, SE, EX | Experience level code |
| `employment_type` | String | FT, PT, CT, FL | Employment type code |
| `job_title` | String | ~100 DS/ML titles | Data science or ML job title |
| `employee_residence` | String | ISO-2 country code | Country of employee residence |
| `remote_ratio` | Integer | 0, 50, 100 | Work mode (0 = on-site, 50 = hybrid, 100 = remote) |
| `company_location` | String | ISO-2 country code | Country where the hiring company is located |
| `company_size` | String | S, M, L | Company size code |
| `salary_in_usd` | Float | — | Annual gross salary in USD (target; not an input) |

### 3.2 Experience Level Codes

| Code | Label |
|---|---|
| EN | Entry Level |
| MI | Mid Level |
| SE | Senior Level |
| EX | Executive Level |

### 3.3 Employment Type Codes

| Code | Label |
|---|---|
| FT | Full Time |
| PT | Part Time |
| CT | Contract |
| FL | Freelance |

### 3.4 Company Size Codes

| Code | Label |
|---|---|
| S | Small Company |
| M | Medium Company |
| L | Large Company |

### 3.5 Remote Ratio Values

| Value | Label |
|---|---|
| 0 | On-site |
| 50 | Hybrid |
| 100 | Fully Remote |

### 3.6 Engineered Features (Model 2)

| Feature | Type | Derivation / Description |
|---|---|---|
| `title_is_junior` | Binary | 1 if title contains "junior", "jr", "associate", "entry" |
| `title_is_senior` | Binary | 1 if title contains "senior", "sr", "lead", "principal", "staff" |
| `title_is_exec` | Binary | 1 if title contains "head", "vp", "director", "chief", "cto", "cdo" |
| `title_is_mgmt` | Binary | 1 if title contains "manager", "head", "lead", "director" |
| `title_domain` | String | Detected domain: ml\_ai, data\_eng, analytics, scientist, other |
| `exp_x_domain` | String | Interaction feature: `{experience_level}_{title_domain}` (e.g. "SE\_ml\_ai") |

### 3.7 Domain Detection Priority

Domains are detected by keyword scan of the job title in this priority order:

| Priority | Domain | Key Keywords |
|---|---|---|
| 1 | ml\_ai | machine learning, deep learning, nlp, computer vision, mlops, ai |
| 2 | analytics | analyst, analytics, bi, business intelligence, dashboard |
| 3 | data\_eng | data engineer, etl, pipeline, big data, data architect |
| 4 | scientist | data scientist, data science |
| 5 | other | (fallback) |

---

## 4. Firestore Collections

### 4.1 `users`

**Path:** `users/{email}`  
One document per registered user, keyed by email address.

| Field | Type | Description |
|---|---|---|
| `username` | String | Email address (used as username) |
| `email` | String | User email address |
| `display_name` | String | Display name chosen at registration |
| `created_at` | String | ISO-8601 UTC timestamp of account creation |
| `auth_provider` | String | Always `"firebase"` |

### 4.2 `predictions`

**Path:** `predictions/{email}/records/{auto-id}`  
Prediction history stored per user, capped at 500 records returned per query.

| Field | Type | Description |
|---|---|---|
| `model_used` | String | "Random Forest", "XGBoost", "Random Forest Resume", "XGBoost Resume" |
| `input_data` | String | JSON-serialised dict of all input fields used for the prediction |
| `predicted_salary` | Float | Predicted annual salary in USD |
| `created_at` | String | ISO-8601 UTC timestamp |

### 4.3 `feedback`

**Path:** `feedback/{auto-id}`  
Anonymous or attributed prediction feedback. Login is not required.

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | String | Yes | Email or `"anonymous"` if not logged in |
| `model_used` | String | Yes | Model that produced the prediction |
| `input_data` | String | Yes | JSON-serialised input dict |
| `predicted_salary` | Float | Yes | Predicted salary in USD |
| `accuracy_rating` | String | Yes | "Yes", "Somewhat", or "No" |
| `direction` | String | Yes | "Too High", "About Right", or "Too Low" |
| `actual_salary` | Float | No | User-reported actual salary in USD; null if skipped |
| `star_rating` | Integer | Yes | 1 – 5 star rating |
| `created_at` | String | Yes | ISO-8601 UTC timestamp |
| `extended_data` | Object | No | Nested object with optional enrichment fields (see below) |

#### 4.3.1 `extended_data` Sub-fields

| Field | Type | Description |
|---|---|---|
| `age` | Integer | 18–80; cross-dataset bridge for XGBoost users |
| `education_level` | Integer | 0–3; cross-dataset bridge for XGBoost users |
| `is_senior` | Integer | 0 or 1; cross-dataset bridge for XGBoost users |
| `gender` | String | Male / Female / Non-binary / Other; bridge for XGBoost users |
| `employment_type` | String | FT/PT/CT/FL; cross-dataset bridge for RF users |
| `remote_ratio` | Integer | 0/50/100; bridge for RF users |
| `company_size` | String | S/M/L; bridge for RF users |
| `company_location` | String | ISO-2; bridge for RF users |
| `compensation_type` | String | e.g. "Base + bonus + equity" |
| `actual_base_usd` | Float | Actual base salary in USD |
| `actual_total_comp_usd` | Float | Actual total compensation in USD |
| `offer_determination` | String | e.g. "Negotiated — got more than initial offer" |
| `skills` | Array\<String\> | List of selected technical skills |
| `years_primary_skill` | Integer | Years of experience in primary skill |
| `certifications` | Array\<String\> | List of professional certifications |
| `industry` | String | Industry sector |
| `company_type` | String | e.g. "Public (listed company)" |
| `company_age_years` | Integer | Age of company in years |
| `immediate_team_size` | String | e.g. "6-15" |
| `direct_reports` | String | e.g. "4-10" |
| `years_current_company` | Integer | Tenure at current employer |
| `total_employers` | Integer | Total number of employers in career |
| `hours_per_week` | String | e.g. "35-40 hrs / week (standard)" |
| `city_tier` | String | e.g. "Major global hub (e.g. NYC, London, Tokyo)" |
| `work_authorisation` | String | e.g. "Citizen / permanent resident" |
| `additional_context` | String | Free-text, max 300 characters |

### 4.4 `pending_verifications`

**Path:** `pending_verifications/{email}`  
Temporary record for accounts awaiting email verification. Deleted after verification is confirmed.

| Field | Type | Description |
|---|---|---|
| `email` | String | User email address |
| `id_token` | String | Firebase ID token for the unverified account |
| `created_at` | String | ISO-8601 UTC timestamp |

### 4.5 `rate_limits`

**Path:** `rate_limits/{action__{sha256_prefix}}`  
Per-action, per-user rate limit tracking. Document ID is `{action}__{sha256[:16](email)}` to avoid storing PII.

| Field | Type | Description |
|---|---|---|
| `attempts` | Integer | Number of failed attempts in current window |
| `window_start` | Float | Epoch timestamp (seconds) of window start |

---

## 5. Model Artefacts

All artefacts are stored in a private HuggingFace dataset repository (`HF_REPO_ID`) and downloaded on application startup.

### 5.1 Model 1 Artefacts

| File | Format | Description |
|---|---|---|
| `app1_model.pkl` | joblib | Random Forest Regressor — salary prediction |
| `app1_metadata.json` | JSON | Test R², CV R², MAE, RMSE, best hyperparameters |
| `app1_salary_band_model.pkl` | joblib | HistGradientBoostingClassifier — salary band (0/1/2) |
| `app1_classifier_metadata.json` | JSON | Classifier accuracy, confusion matrix, feature importances |
| `app1_cluster_model.pkl` | joblib | KMeans — career stage clustering |
| `app1_cluster_metadata.json` | JSON | Cluster labels, silhouette score, Davies-Bouldin score, PCA data |
| `assoc_rules_a1_v2.pkl` | joblib | Apriori association rules (MLxtend) |
| `app1_analytics.pkl` | joblib | Pre-computed analytics: residuals, predicted vs actual, feature importance |
| `app1_model_comparison.json` | JSON | Comparison table across candidate models (R², MAE, RMSE) |
| `app1_classifier_comparison.json` | JSON | Classifier model comparison table |
| `df_app1.pkl` | joblib | Training dataset (used for data insights tab and association rules) |

### 5.2 Model 2 Artefacts

| File | Format | Description |
|---|---|---|
| `app2_model.pkl` | joblib | XGBoost Regressor — data science salary prediction (log-transformed target) |
| `app2_metadata.json` | JSON | Test R², CV R², MAE, RMSE, best hyperparameters |
| `app2_analytics.pkl` | joblib | Pre-computed: residuals, SHAP values, grouped feature importance, prediction distribution |
| `app2_model_comparison.json` | JSON | Comparison table across candidate models |
| `df_app2.pkl` | joblib | Training dataset (used for insights, data insights tab, recommendations) |

### 5.3 Metadata JSON Schema (Model 1 — `app1_metadata.json`)

| Key | Type | Description |
|---|---|---|
| `test_r2` | Float | R² score on held-out test set |
| `cv_mean_r2` | Float | Mean R² across 5-fold cross-validation |
| `mae` | Float | Mean Absolute Error on test set |
| `rmse` | Float | Root Mean Squared Error on test set |
| `best_params` | Object | Best hyperparameters selected by GridSearchCV |
| `residual_std` | Float | Standard deviation of residuals; used for confidence interval estimation |

---

## 6. Model Hub Bundle Schema

Each Model Hub bundle is a versioned package stored in the HuggingFace repo at `models/{folder_name}/`.

### 6.1 Bundle Files

Two bundle formats are supported. The loader detects the format at load time by probing for `model.onnx` first.

**ONNX format (recommended):**

| File | Format | Size Limit | Required | Description |
|---|---|---|---|---|
| `model.onnx` | ONNX protobuf | 200 MB | Yes | ONNX computation graph — loaded via onnxruntime, no arbitrary code execution. |
| `columns.json` | JSON | 10 MB | Yes | JSON array of feature column name strings. No pickle risk. |
| `schema.json` | JSON | 512 KB | Yes | UI schema defining input fields. |
| `aliases.json` | JSON | 512 KB | No | Display labels for selectbox model values. |
| `skills.json` | JSON | 512 KB | No | Optional per-bundle skills lexicon for resume extraction; overrides the global shared lexicon for this bundle only. |
| `job_titles.json` | JSON | 512 KB | No | Optional per-bundle job title alias map for resume extraction; overrides the global shared lexicon for this bundle only. |
| `resume_config.json` | JSON | 256 KB | No | Optional per-bundle resume extraction config overriding scoring weights, extractor settings, thresholds, field-name mapping, and preprocessing. |

**Pickle format (legacy):**

| File | Format | Size Limit | Required | Description |
|---|---|---|---|---|
| `model.pkl` | joblib/pickle | 200 MB | Yes | sklearn-compatible estimator with a `predict()` method. |
| `columns.pkl` | joblib/pickle | 10 MB | Yes | Ordered list of feature column names (strings). |
| `schema.json` | JSON | 512 KB | Yes | UI schema defining input fields. |
| `aliases.json` | JSON | 512 KB | No | Display labels for selectbox model values. |
| `skills.json` | JSON | 512 KB | No | Optional per-bundle skills lexicon for resume extraction; overrides the global shared lexicon for this bundle only. |
| `job_titles.json` | JSON | 512 KB | No | Optional per-bundle job title alias map for resume extraction; overrides the global shared lexicon for this bundle only. |
| `resume_config.json` | JSON | 256 KB | No | Optional per-bundle resume extraction config overriding scoring weights, extractor settings, thresholds, field-name mapping, and preprocessing. |

### 6.2 Registry Entry (`models_registry.json`)

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Unique folder name: `model_{timestamp}_{6-char-random}` |
| `display_name` | String | Yes | Human-readable name shown in the UI dropdown |
| `path` | String | Yes | HuggingFace path: `models/{id}/` |
| `description` | String | No | Optional description paragraph |
| `target` | String | Yes | Name of the predicted variable, e.g. `"salary_in_usd"` |
| `active` | Boolean | Yes | Whether the model is visible to users |
| `version` | Integer | Yes | Version number (starts at 1) |
| `uploaded_at` | String | Yes | ISO-8601 UTC timestamp of upload |
| `uploaded_by` | String | Yes | Username of the admin who uploaded |
| `size_bytes` | Integer | Yes | Total size of all uploaded bundle files in bytes |
| `schema_version` | String | Yes | Schema version, e.g. `"1.0"` |
| `num_features` | Integer | Yes | Number of columns in `columns.pkl` |
| `num_inputs` | Integer | Yes | Number of fields in `schema.json["fields"]` |
| `has_aliases` | Boolean | Yes | True if `aliases.json` was uploaded with the bundle |
| `has_skills_lexicon` | Boolean | No | True if `skills.json` was uploaded with the bundle |
| `has_titles_lexicon` | Boolean | No | True if `job_titles.json` was uploaded with the bundle |
| `has_resume_config` | Boolean | No | True if `resume_config.json` was uploaded with the bundle |
| `bundle_format` | String | Yes | `"onnx"` or `"pickle"` — recorded at upload time so the loader can detect format without probing HuggingFace |
| `family_id` | String | No | Optional group ID for rollback/versioning |

### 6.3 `schema.json` Field Definition

| Field | Type | Required | Description |
|---|---|---|---|
| `fields` | Array | Yes | List of field definition objects |

Top-level schema keys (all optional):

| Key | Type | Description |
|---|---|---|
| `layout` | Object | Grid layout: `{"columns": N}` where N is 1, 2, or 3. Omitting = single-column (backward compatible with all existing schemas). |
| `result_label` | String | Label shown on the prediction result card. Overrides the registry target variable name. Omitting = registry target name used. |
| `plots` | Array | Optional chart declarations rendered automatically in the appropriate Model Hub mode (manual, batch, resume, or scenario). |
| `scenario_sweep` | Object | Optional sensitivity-sweep configuration used by the Scenario mode. |

Each field object:

| Key | Type | Required | Description |
|---|---|---|---|
| `name` | String | Yes | Snake\_case field identifier; must match column name or OHE prefix |
| `type` | String | Yes | Data type: `int`, `float`, `category`, `bool`, `str` |
| `ui` | String | Yes | Widget type: `slider`, `selectbox`, `number_input`, `text_input`, `checkbox` |
| `label` | String | No | Display label shown in the UI (defaults to prettified name) |
| `help` | String | No | Help text shown as tooltip |
| `min` | Number | slider, number\_input | Minimum value |
| `max` | Number | slider, number\_input | Maximum value |
| `default` | Any | No | Default value; must be within [min, max] for sliders |
| `step` | Number | No | Increment step for slider/number\_input |
| `values` | Array\<String\> | selectbox | List of allowed string values (always model values, never display labels) |
| `aliases` | Object | No (selectbox only) | Maps model values to display labels: `{"model_value": "Display Label"}`. Can be defined inline for small sets; use `aliases.json` sidecar for large sets. Sidecar wins if both present. |
| `row` | Integer | No | Layout group. Fields sharing the same row integer are placed side-by-side. Fields without `row` each get their own row (backward compatible). |
| `col_span` | Integer | No | Column span: 1, 2, or 3. How many grid columns the field occupies. Sliders default to full row width. Default 1. |

---

## 7. Session State Keys

All session state is per-browser-tab and expires when the tab closes or the session expires (24 hours).

### 7.1 Authentication Keys

| Key | Type | Description |
|---|---|---|
| `logged_in` | Boolean | Whether the user is currently authenticated |
| `username` | String | Email of the logged-in user; None if not logged in |
| `_firebase_id_token` | String | Firebase ID token for the current session |
| `_session_expiry` | datetime | UTC expiry datetime for the current session |
| `is_admin` | Boolean | Whether the current user has admin privileges |
| `db_initialized` | Boolean | Flag to prevent re-running Firestore init on reruns |

### 7.2 Prediction State Keys

| Key | Type | Description |
|---|---|---|
| `manual_prediction_result` | Dict | Result of most recent manual prediction |
| `manual_pdf_buffer` | BytesIO | Generated PDF buffer for manual prediction report |
| `manual_pdf_ready` | Boolean | Whether the manual PDF has been generated |
| `resume_features` | Dict | Extracted features from uploaded resume (App 1) |
| `resume_features_a2` | Dict | Extracted features from uploaded resume (App 2) |
| `resume_text` | String | Raw extracted text from uploaded PDF resume (App 1) |
| `resume_text_a2` | String | Raw extracted text from uploaded PDF resume (App 2) |
| `resume_score_data` | Dict | Resume score breakdown (App 1) |
| `resume_prediction_result` | Dict | Prediction result from resume analysis (App 1) |
| `resume_pdf_ready` | Boolean | Whether resume PDF has been generated |
| `resume_pdf_buffer` | BytesIO | Generated PDF buffer for resume report |
| `bulk_result_df` | DataFrame | Results dataframe from batch prediction |
| `bulk_pdf_buffer` | BytesIO | Generated PDF buffer for batch report |
| `scenarios_a1` | List\<Dict\> | List of up to 5 scenario configurations (App 1) |
| `scenarios_a2` | List\<Dict\> | List of up to 5 scenario configurations (App 2) |
| `scenario_results_a1` | List\<Dict\> | Computed results for all App 1 scenarios |
| `scenario_results_a2` | List\<Dict\> | Computed results for all App 2 scenarios |

### 7.3 Model Hub State Keys

| Key | Type | Description |
|---|---|---|
| `mh_bundle_cache` | Dict\<str, ModelBundle\> | Loaded model bundles keyed by model ID. Each ModelBundle carries `bundle_format` ("onnx" or "pickle") used by predictor.py to route inference. |
| `mh_registry_cache` | Dict | Cached registry with `_fetched_at` timestamp (TTL: 120s) |
| `mh_schema_fields` | List\<Dict\> | Fields being built in the Schema Editor |
| `mh_pred_result_{model_id}` | Dict | Persisted prediction result for a loaded model. Keyed per model ID so switching models shows a fresh form. Contains `value`, `model_id`, `target`, `warnings`, `raw_input`. Written on form submit; read on every fragment rerun to keep the result card and currency toggle visible after widget interactions. |
| `mh_currency_{model_id}` | (managed by `currency_utils`) | Currency converter widget state for a given model's prediction result. Key follows the `render_currency_converter()` convention. |

### 7.4 Email Verification State Keys

| Key | Type | Description |
|---|---|---|
| `_ev_pending_email` | String | Email address awaiting verification |
| `_ev_pending_token` | String | Firebase ID token for the pending account |

---

## 8. Financial Utility Data

### 8.1 Cost-of-Living Indices (`col_utils.py`)

Baseline: US = 100. Source: Numbeo, World Bank, EIU 2023/24 (country-level approximations).

| Country | ISO-2 | CoL Index | Category |
|---|---|---|---|
| Switzerland | CH | 137.0 | Very High |
| Norway | NO | 121.0 | Very High |
| Denmark | DK | 117.0 | Very High |
| United States | US | 100.0 | High |
| Singapore | SG | 95.0 | High |
| Australia | AU | 93.0 | High |
| United Kingdom | GB | 91.0 | High |
| Japan | JP | 88.0 | Moderate–High |
| Germany | DE | 83.0 | Moderate–High |
| France | FR | 82.0 | Moderate–High |
| India | IN | 23.0 | Low |
| Vietnam | VN | 28.0 | Low |
| Nigeria | NG | 25.0 | Low |
| Ethiopia | ET | 18.0 | Very Low |
| Afghanistan | AF | 15.0 | Very Low |

Fallback for unknown countries: 50.0.

### 8.2 Tax Brackets (`tax_utils.py`)

Progressive brackets encoded as `(upper_bound_usd, marginal_rate)` tuples. Final bracket uses `float('inf')`. Rates are combined effective estimates (income tax + major social contributions). Source: OECD, TaxFoundation, government portals (2024).

Example — United States (federal + avg state ~5%):

| Income Threshold (USD) | Marginal Rate |
|---|---|
| 0 – 11,600 | 10% |
| 11,601 – 47,150 | 17% |
| 47,151 – 100,525 | 27% |
| 100,526 – 191,950 | 29% |
| 191,951 – 243,725 | 31% |
| 243,726 – 609,350 | 35% |
| 609,351+ | 42% |

Countries with built-in bracket data include: US, GB, DE, FR, IN, CA, AU, JP, SG, AE, and 30+ more.

### 8.3 CTC Component Rates (`ctc_utils.py`)

HRA as fraction of basic salary (country-specific):

| Country | ISO-2 | HRA Rate | Notes |
|---|---|---|---|
| India | IN | 50% | Metro HRA — most common employer policy |
| Gulf countries (UAE, QA, SA, KW) | AE/QA/SA/KW | 25% | Housing allowance mandated / common |
| Pakistan | PK | 45% | Common in corporate packages |
| Bangladesh | BD | 40% | — |
| Japan | JP | 5% | Jutaku teate (housing allowance) |
| USA, UK, Germany, France | US/GB/DE/FR | 0% | Not a formal payroll component |

### 8.4 PF / Pension Rates (`takehome_utils.py`)

Employee-side pension/provident fund contribution as fraction of gross salary:

| Country | ISO-2 | Rate | Scheme |
|---|---|---|---|
| India | IN | 12% | EPF (approximated as % of gross) |
| United States | US | 6.2% | Social Security OASDI |
| United Kingdom | GB | 8% | National Insurance |
| Germany | DE | 9.3% | Rentenversicherung (employee half) |
| Australia | AU | 11% | Superannuation (shown as CTC cost) |
| Canada | CA | 5.7% | CPP employee contribution |
| France | FR | 6.9% | Net employee share (CRDS/CSG) |

### 8.5 Expected Investment Returns (`investment_utils.py`)

Blended annual return benchmark (equity index + balanced funds, net of fees):

| Country | ISO-2 | Expected Return | Notes |
|---|---|---|---|
| United States | US | 9.0% | S&P 500 long-run ~10%, net of fees |
| Mexico | MX | 9.5% | Higher nominal due to inflation |
| India | IN | ~11% | Nifty/Sensex long-run historical |
| Germany | DE | ~7% | DAX historical |
| Japan | JP | ~6% | Lower due to deflationary environment |

---

## 9. Encoding and Mapping Tables

### 9.1 Country Name to ISO-2 Alias Table

The `country_utils.py` `_ALIAS_TABLE` maps common names and abbreviations to ISO-3166-1 alpha-2 codes. Key entries:

| Alias | ISO-2 |
|---|---|
| USA, United States | US |
| UK, United Kingdom | GB |
| UAE, United Arab Emirates | AE |
| South Korea | KR |
| Hong Kong | HK |
| Taiwan | TW |
| Russia | RU |
| Czechia, Czech Republic | CZ |

Full resolution order: direct ISO-2 → exact alias → case-insensitive alias → CLDR territory name.

### 9.2 Currency Metadata (`currency_utils.py`)

Over 100 currencies supported. Live rates from `open.er-api.com` (no API key, updated daily), cached for 60 minutes. Key entries:

| Code | Name | Symbol |
|---|---|---|
| USD | US Dollar | $ |
| EUR | Euro | € |
| GBP | British Pound | £ |
| INR | Indian Rupee | ₹ |
| JPY | Japanese Yen | ¥ |
| AED | UAE Dirham | AED |
| SGD | Singapore Dollar | S$ |
| KRW | South Korean Won | ₩ |

---

## 10. NLP Feature Extraction Fields

### 10.1 Resume Feature Extraction Output (App 1)

Produced by `extract_resume_features()` in `resume_analysis.py`:

| Field | Type | Description |
|---|---|---|
| `job_title` | String | Canonical job title matched via PhraseMatcher + alias map |
| `years_of_experience` | Float | Years extracted by regex pattern matching |
| `education_level` | Integer | 0–3 mapped from detected degree keywords |
| `senior` | Integer | 0 or 1; derived from experience > 5 years or title keywords |
| `gender` | String | Not extracted; defaults to "Male" (most common in dataset) |
| `country` | String | Country name extracted from text; matched to allowed list |
| `skills` | List\<String\> | Technical skills matched via spaCy PhraseMatcher |

**Skill lexicon size:** ~80 skills across programming languages, databases, ML frameworks, cloud platforms, BI tools, and DevOps tools.

### 10.2 Resume Feature Extraction Output (App 2)

Produced by `extract_resume_features_a2()`:

| Field | Type | Description |
|---|---|---|
| `experience_level_a2` | String | EN/MI/SE/EX mapped from extracted years |
| `employment_type_a2` | String | FT/PT/CT/FL detected by keyword scan |
| `job_title_a2` | String | Canonical DS/ML job title |
| `employee_residence_a2` | String | ISO-2 code; detected by NER then alias scan |
| `company_location_a2` | String | Same as employee\_residence (assumed same country) |
| `remote_ratio_a2` | Integer | 0/50/100 detected by keyword scan |
| `company_size_a2` | String | Defaults to "M" (medium); not reliably extractable from resume |
| `years_of_experience_a2` | Float | Numeric years from regex |
| `skills_a2` | List\<String\> | DS/ML-weighted skill list |
| `sources_a2` | Dict | Extraction method per field (for transparency) |

### 10.3 Resume Scoring (App 1)

| Component | Max Score | Scoring Criteria |
|---|---|---|
| Experience | 40 | 0 yrs = 0, 1 yr = 8, 2 yrs = 15, 4 yrs = 22, 7 yrs = 30, 10 yrs = 36, 15+ yrs = 40 |
| Education | 35 | High School = 8, Bachelor = 18, Master = 28, PhD = 35 |
| Skills | 25 | 2 pts per skill, max 25 |
| **Total** | **100** | Basic (<35), Moderate (35–64), Strong (65+) |

### 10.4 Resume Scoring (App 2)

| Component | Max Score | Scoring Criteria |
|---|---|---|
| Experience | 40 | 0 yrs = 0, ≤1 yr = 8, ≤3 yrs = 18, ≤6 yrs = 28, ≤10 yrs = 36, >10 yrs = 40 |
| Skills (DS/ML weighted) | 35 | DS skill = 5 pts, general skill = 2 pts; max 35 |
| Title Relevance | 25 | Core DS/ML title = 25, related data title = 15, other = 8 |
| **Total** | **100** | Basic (<35), Moderate (35–64), Strong (65+) |

---

*End of Data Dictionary*
