# SalaryScope — Design Document
**Version:** 1.4.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Author:** Yash Shah  
**Document Type:** Software Design Document (SDD)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [Module Design](#4-module-design)
5. [Data Flow](#5-data-flow)
6. [Machine Learning Pipeline](#6-machine-learning-pipeline)
7. [NLP Pipeline](#7-nlp-pipeline)
8. [Authentication and Security Design](#8-authentication-and-security-design)
9. [Model Hub Design](#9-model-hub-design)
10. [Financial Tools Design](#10-financial-tools-design)
11. [Database Design](#11-database-design)
12. [UI and Theming Design](#12-ui-and-theming-design)
13. [PDF Report Generation](#13-pdf-report-generation)
14. [Feedback and Data Collection Design](#14-feedback-and-data-collection-design)
15. [Deployment Architecture](#15-deployment-architecture)
16. [Design Decisions and Rationale](#16-design-decisions-and-rationale)
17. [Known Limitations and Constraints](#17-known-limitations-and-constraints)

---

## 1. Introduction

### 1.1 Purpose

This document describes the software architecture, module design, data flows, and design decisions for SalaryScope v1.4.0 — a machine learning-powered salary prediction web application built with Python and Streamlit.

### 1.2 Scope

The document covers all components of the system including the Streamlit frontend, ML model integration, NLP resume analysis pipeline, Firebase authentication and database layer, Model Hub extensibility framework, financial utility modules, and PDF report generation.

### 1.3 Intended Audience

This document is intended for developers maintaining or extending the codebase, academic evaluators reviewing the system design, and technical reviewers assessing the project.

### 1.4 Project Context

SalaryScope is a Final Year B.Tech project (Computer Engineering, Gandhinagar Institute of Technology, Gandhinagar University). The system combines machine learning with a full-stack interactive web application, deployed publicly on Streamlit Cloud.

---

## 2. System Overview

SalaryScope provides salary prediction through three modes of interaction — manual form input, PDF resume upload with NLP extraction, and bulk file upload — across two independently trained ML models:

- **Model 1 (App 1):** Random Forest Regressor trained on a general salary dataset. Covers a broad range of job roles and countries.
- **Model 2 (App 2):** XGBoost Regressor trained on a data science salaries dataset. Specialises in data science and ML roles globally.

In addition to prediction, the system provides dataset exploration, model performance analytics, financial planning tools, a dedicated HR & Employer Tools tab for compensation planning workflows, an AI Assistant for explanation and drafting tasks, a user account system backed by Firebase, and a Model Hub that allows admins to deploy additional independently trained models without modifying application code.

---

## 3. Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Cloud (Web Browser)               │
│                                                                  │
│  ┌─────────────┐   ┌──────────────────────────────────────────┐ │
│  │  Sidebar     │   │           Tab Area                        │ │
│  │  - Model     │   │  Manual | Resume | AI Assistant |      │ │
│  │    Selector  │   │  Batch | Scenario | Analytics |       │ │
│  │  - Auth      │   │  Insights | Hub | HR Tools | Profile | │ │
│  │              │   │  Admin | About                         │ │
│  └─────────────┘   └──────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐  ┌───▼──────┐  ┌───▼────────────┐
    │  Firebase Auth  │  │Firestore │  │ HuggingFace    │
    │  (REST API)     │  │(Database)│  │ Dataset Repo   │
    └─────────────────┘  └──────────┘  │ (Model storage)│
                                        └────────────────┘
```

### 3.2 Layered Architecture

The application follows a deliberate layered structure to prevent circular imports and separate concerns:

```
Layer 0: Entry Point
    app_resume.py          — Page config, resource loading, tab mounting

Layer 1: Tabs (app/tabs/)
    manual_prediction_tab  — Input form + results + financial tools
    resume_analysis_tab    — Resume PDF workflow + Offer Letter workflow
    llm_assistant_tab      — Grounded assistant UI for help/explanations/drafting
    batch_prediction_tab   — File upload + bulk prediction
    scenario_analysis_tab  — Multi-scenario comparison
    model_analytics_tab    — Performance metrics + SHAP + association rules
    data_insights_tab      — EDA dashboards
    model_hub_tab          — Model Hub UI
    hr_tools_tab           — HR compensation planning tools
    user_profile           — Prediction history + account management
    admin_panel            — System diagnostics + feedback analytics
    about_tab              — Static informational content

Layer 2: Core (app/core/)
    auth.py                — Firebase Authentication, session management
    database.py            — Firestore CRUD operations
    resume_analysis.py     — NLP pipeline (spaCy + regex)
    insights_engine.py     — Domain detection, market comparison, App 1/2 insights
    email_verification.py  — Firebase email verification flow
    password_policy.py     — NIST SP 800-63B password validation
    rate_limiter.py        — Two-layer (session + Firestore) brute-force protection
    account_management.py  — Password change, account deletion

Layer 3: Utilities (app/utils/)
    currency_utils.py      — Live currency conversion
    tax_utils.py           — Tax estimation
    col_utils.py           — Cost-of-living adjustment
    ctc_utils.py           — CTC breakdown
    takehome_utils.py      — Net take-home calculation
    savings_utils.py       — Savings potential
    loan_utils.py          — Loan affordability
    budget_utils.py        — Budget allocation
    investment_utils.py    — Investment growth projection
    emergency_fund_utils.py — Emergency fund planning
    lifestyle_utils.py     — Lifestyle budget split
    country_utils.py       — Centralised country/ISO resolution
    recommendations.py     — Career recommendation engine (App 1 + 2)
    negotiation_tips.py    — Salary negotiation tips (App 1 + 2)
    feedback.py            — Feedback UI + Firestore persistence
    pdf_utils.py           — PDF report generation (ReportLab)

Layer 4: Model Hub (app/model_hub/)
    registry.py            — Registry CRUD (models_registry.json)
    loader.py              — Bundle download + session caching
    predictor.py           — Feature vector build + model.predict()
    schema_parser.py       — schema.json → Streamlit widgets
    uploader.py            — Bundle validation + HuggingFace upload
    validator.py           — Schema + column consistency validation
    _hf_client.py          — HuggingFace SDK wrapper

Layer 5: HR Tools (app/hr_tools/)
    predict_helpers.py      — Shared single-row and batch inference helpers
    hiring_budget.py        — Payroll budget estimator
    benchmarking_table.py   — Salary benchmarking grid
    candidate_comparison.py — Side-by-side candidate comparison
    offer_checker.py        — Offer competitiveness checker
    team_audit.py           — Team-wide compensation audit from CSV
```

### 3.3 Dependency Rules

- Tabs may import from Core and Utilities but never from other Tabs.
- Utilities may import from `country_utils` but never from Core (with the exception of `feedback.py` which imports from `database.py`).
- Core modules never import from Tabs or Utilities (except `account_management.py` which lazily imports `auth.py` and `database.py`).
- Model Hub modules are fully self-contained and only import from `_hf_client.py` and each other; never from Core or Tabs.
- All dependencies are injected into tab render functions from `app_resume.py` to prevent double-loading of cached resources and circular imports.

---

## 4. Module Design

### 4.1 Entry Point (`app_resume.py`)

`app_resume.py` is the single Streamlit entry point. It performs the following at startup:

1. Initialises Firestore (idempotent, guarded by `st.session_state.db_initialized`).
2. Sets page configuration and applies the global dark professional CSS theme.
3. Loads all ML models, metadata, datasets, and lookup tables using `@st.cache_resource` and `@st.cache_data` decorators to prevent reloading on every Streamlit rerun.
4. Renders the sidebar with the model selector and authentication widgets.
5. Constructs the tab list dynamically (AI Assistant and HR Tools are part of the full-app base set; Profile and Admin tabs are added conditionally based on login status and admin flag).
6. Mounts each tab renderer, passing all required resources as arguments.

**Design principle:** No business logic lives in `app_resume.py`. It is purely an orchestrator — loading, assembling, and passing resources to tab modules.

### 4.2 Tab Modules

Each tab module exposes a single `render_*()` function that accepts all required resources as parameters. This pattern:

- Prevents circular imports (no tab ever imports from `app_resume.py`).
- Prevents double-loading (cached resources loaded once in `app_resume.py`, reused across tabs).
- Makes each tab independently testable.
- Uses `@st.fragment` for sub-sections that should not trigger full-page reruns (e.g., resume editor, feedback dashboard, Model Analytics sub-sections).

### 4.3 Core Authentication (`auth.py`)

Authentication is entirely Firebase-based via the REST Identity Toolkit API. No passwords are stored locally.

**Login flow:**
1. Rate limit check (session + Firestore layers).
2. Firebase `signInWithPassword` REST call.
3. On success: check email verification status.
4. If verified: store `id_token`, set session expiry to `now + 24h`, store `username` in `st.session_state`.
5. If unverified: enter pending verification UI.

**Session management:** Sessions live entirely in `st.session_state`. No server-side session store is used. The session expiry is enforced on every page load by comparing `_session_expiry` to `datetime.utcnow()`.

**Admin detection:** Compared by email — `st.session_state.username.lower() == ADMIN_EMAIL.lower()`. Admin email is stored in `st.secrets`.

### 4.4 Rate Limiter (`rate_limiter.py`)

Two-layer design to work within Streamlit Cloud's single-process-per-user constraint:

- **Layer 1 (session state):** Zero-latency per-tab check. Prevents rapid repeated submissions within one browser tab.
- **Layer 2 (Firestore):** Cross-session, cross-tab check. Document ID is `{action}__{sha256[:16](email)}` to avoid PII exposure. Fails open on any error — a Firestore outage never blocks a legitimate user.

Rate limits: login 5/5min, register 3/10min, email resend 3/10min, password change 3/10min, account deletion 3/10min, forgot password 3/10min.

### 4.5 Insights Engine (`insights_engine.py` and `recommendations.py`)

Both modules implement the same domain detection and recommendation logic independently. `insights_engine.py` is the primary engine used by `manual_prediction_tab` and `resume_analysis_tab`. `recommendations.py` mirrors the logic and is used by the same tabs for the recommendations section.

**Market comparison design:** Uses hierarchical fallback across four progressively broader subsets of the App 2 training dataset, always requiring experience level in the filter. Requires a minimum of 15 samples per subset before computing average. Returns "insufficient data" if no subset meets the threshold.

---

## 5. Data Flow

### 5.1 Manual Prediction Flow (Model 1)

```
User fills form (age, experience, education, senior, gender, job_title, country)
    │
    ▼
Input validation (age - experience ≥ 18)
    │
    ▼
pd.DataFrame construction
    │
    ├──► app1_model.predict(input_df)         → predicted_salary (float)
    ├──► app1_salary_band_model.predict()     → salary_band (0/1/2)
    ├──► app1_cluster_model.predict()         → career_stage (0/1/2)
    └──► get_assoc_insight_a1_improved()      → association pattern text
    │
    ▼
Results display (salary card, breakdown, confidence interval)
    │
    ▼
Financial tools chain:
    currency_utils → tax_utils → col_utils → ctc_utils →
    takehome_utils → savings_utils → loan_utils →
    budget_utils → investment_utils → emergency_fund_utils → lifestyle_utils
    │
    ▼
Insights + negotiation tips + recommendations
    │
    ▼
Feedback UI → Firestore (feedback collection)
    │
    ▼
PDF generation (ReportLab) → BytesIO buffer → download button
    │
    ▼
save_prediction() → Firestore (predictions collection) [if logged in]
```

### 5.2 Resume Analysis Flow (Model 1)

```
User uploads PDF
    │
    ▼
extract_text_from_pdf() [pdfplumber]
    │
    ▼
preprocess_resume_text() [regex cleaning]
    │
    ├──► extract_experience_years()  [regex]
    ├──► extract_education_level()   [keyword matching]
    ├──► extract_job_title()         [spaCy PhraseMatcher + alias map]
    ├──► extract_country()           [spaCy NER + alias map]
    └──► extract_skills()            [spaCy PhraseMatcher, ~80 skill patterns]
    │
    ▼
calculate_resume_score() → score_data (experience/education/skills breakdown)
    │
    ▼
Editable feature form (user can correct extracted values)
    │
    ▼
Predict Salary from Resume → same prediction pipeline as manual
    │
    ▼
Results with confidence interval + currency/tax/COL tools + PDF
```

### 5.3 Batch Prediction Flow

```
File upload (CSV/XLSX/JSON/SQL) OR Google Drive link
    │
    ▼
convert_drive_link() [if Drive link]
    │
    ▼
validate_bulk_dataframe() → error report if invalid columns/values
    │
    ▼
For each row: model.predict(row_df)
    │
    ▼
bulk_result_df (input columns + Predicted Annual Salary + salary band + career stage)
    │
    ▼
Batch Analytics Dashboard:
    - Summary metrics (avg, min, max, std)
    - Salary leaderboard by job title
    - Distribution histogram
    - Breakdowns by experience/company size/work mode/country
    │
    ▼
Export (CSV/XLSX/JSON) + PDF report
```

### 5.4 Model Hub Prediction Flow

```
User selects model from dropdown (active models only)
    │
    ▼
load_bundle(model_meta) → check session cache → if miss: download from HuggingFace
    │  Format detection: probe for model.onnx first
    │    ONNX found: download model.onnx + columns.json
    │    ONNX absent: download model.pkl + columns.pkl (legacy)
    │  schema.json and aliases.json always fetched with force=True
    │  If aliases.json present → merged into schema fields at load time
    │  bundle.bundle_format recorded as "onnx" or "pickle" for predictor routing
    │
    ▼
render_schema_form(schema) → {field_name: model_value} dict
    │  Selectbox options show alias display labels if defined;
    │  returned values are always the underlying model values
    │
    ▼
predict(bundle, raw_input):
    _build_feature_vector():
        - Direct match: column name == field name
        - OHE match: column name == "{field}_{value}" (sklearn get_dummies convention)
        - Fill missing with 0.0
    │
    ▼
predictor dispatches on bundle.bundle_format:
    "onnx"   -> onnxruntime sess.run([output], {input: X_f32}) -> scalar float
    "pickle" -> bundle.model.predict(X_df) -> scalar float
    │
    ▼
PredictionResult stored in st.session_state[mh_pred_result_{model_id}]
    │  Persisted so fragment reruns (e.g. currency toggle) do not lose the result
    │
    ▼
_render_prediction_result(stored) → result card + optional currency converter
    │  render_currency_converter() shown if currency_utils is importable
    │  location_hint derived from raw_input (checks 'country', 'employee_residence', etc.)
```

---

## 6. Machine Learning Pipeline

### 6.1 Model 1 — Random Forest Regressor

**Training approach:**
- GridSearchCV with 5-fold cross-validation for hyperparameter selection.
- Final model retrained on the complete dataset using best hyperparameters.
- Target: annual salary in USD.

**Supporting models:**
- `HistGradientBoostingClassifier` for salary band classification (Early Career / Professional / Executive), separately tuned with GridSearchCV.
- KMeans clustering for career stage segmentation (Entry / Growth / Leadership). PCA used for visualisation.
- Apriori algorithm (MLxtend) for association rule mining between education, experience category, job group, and salary level.

**Confidence interval:** Estimated as `prediction ± 1.96 × residual_std` where `residual_std` is the standard deviation of training residuals. This is an approximation, not a formal prediction interval.

### 6.2 Model 2 — XGBoost Regressor

**Training approach:**
- Target variable: `log1p(salary_in_usd)` to reduce skewness and improve model performance.
- Prediction is back-transformed using `expm1()` for display.
- Custom feature engineering on job titles (seniority flags, domain classification, management flags).
- Interaction feature: `exp_x_domain = "{experience_level}_{title_domain}"`.

**Explainability:**
- SHAP values computed on the test set for top-15 feature drivers.
- Grouped feature importance aggregates OHE column importances by original feature group.

### 6.3 Pre-computation Strategy

Heavy analytics (residuals, SHAP values, feature importances, clustering metrics) are pre-computed during model development as Jupyter notebooks and saved as `app1_analytics.pkl` and `app2_analytics.pkl`. This ensures the web application loads instantly without recomputing these on startup.

---

## 7. NLP Pipeline

### 7.1 Model

`spaCy en_core_web_sm` loaded with `parser` and `textcat` components disabled for performance. Cached via `@st.cache_resource`.

### 7.2 Pipeline Stages

```
PDF Binary → pdfplumber → raw text
    │
    ▼
preprocess_resume_text():
    - Lowercase normalisation
    - Regex-based cleaning (remove noise characters, normalise whitespace)
    │
    ▼
Parallel feature extraction (all operate on the same cleaned text):
    │
    ├── extract_experience_years()
    │       Regex: "X years", "X+ years", "X year experience"
    │       Returns float; 0.0 if not found
    │
    ├── extract_education_level()
    │       Keyword matching: phd/doctorate → 3, master → 2, bachelor → 1, default → 0
    │
    ├── extract_job_title()
    │       spaCy PhraseMatcher with JOB_TITLE_ALIASES (~14 canonical titles, 60+ aliases)
    │       Returns (canonical_title, source_label)
    │
    ├── extract_country()  [App 1]
    │       spaCy NER (GPE, LOC entities) → country_utils.resolve_iso2 → allowed list
    │       Fallback: alias scan (longest match first)
    │
    ├── extract_country_iso_a2()  [App 2]
    │       Same NER approach but returns ISO-2 code
    │       Fallback: alias scan; default "US"
    │
    └── extract_skills()
            spaCy PhraseMatcher with ~80 skill patterns
            Returns sorted list of matched skill strings
```

### 7.3 Design Rationale for Rule-Based Approach

A rule-based NLP approach was chosen over a supervised model because:
- No labeled resume dataset was available for training.
- Rule-based extraction is deterministic and interpretable.
- Processing speed is acceptable for individual uploads (no GPU required).
- spaCy `en_core_web_sm` is small enough to run within Streamlit Cloud memory limits.

---

## 8. Authentication and Security Design

### 8.1 Firebase Authentication

All authentication is delegated to Firebase Authentication via REST Identity Toolkit API calls. No passwords are stored in Firestore or the application.

```
Register:
  password_policy.validate() → Firebase signUp → send verification email
  → save_pending_verification() in Firestore → enter verification pending UI

Login:
  rate_limit check → Firebase signInWithPassword
  → check_email_verified() → if verified: create session
                           → if not: enter verification pending UI
                           → check Firestore for persisted pending state

Password Reset:
  rate_limit check → Firebase sendOobCode (PASSWORD_RESET)
  → show generic success (account enumeration protection)
```

### 8.2 Password Policy

Aligned with NIST SP 800-63B (2024) and OWASP Authentication Cheat Sheet (2024):
- Minimum 12 characters, maximum 128 characters.
- Must contain: uppercase, lowercase, digit, special character.
- No leading or trailing whitespace.
- No runs of 3 or more identical consecutive characters.
- Not in a blocklist of ~60 common passwords.

### 8.3 Session Security

- Sessions are browser-local (`st.session_state`) with a 24-hour expiry enforced client-side.
- The Firebase ID token is stored in session state and used only for re-authentication during sensitive operations (password change, account deletion).
- No session data is stored server-side.

### 8.4 Model Hub Security

- Upload restricted to admin users (enforced in `model_hub_tab.py` before any admin section renders).
- ONNX bundles use onnxruntime (protobuf format) — no arbitrary Python execution on deserialisation. This is the primary security improvement over pickle bundles.
- `columns.json` in ONNX bundles is plain JSON — no deserialisation risk compared to `columns.pkl`.
- `aliases.json` is JSON-only (no pickle) and is validated against the schema before upload or push.
- File size limits enforced pre-download (pre-flight via HuggingFace API `get_paths_info`) and post-download.
- joblib/pickle deserialisation is acknowledged as a security risk; mitigated by admin-only upload control and a security audit log entry on every load.
- Folder names are always generated by the system (`model_{timestamp}_{random}`); no user-controlled path injection is possible.

---

## 9. Model Hub Design

### 9.1 Architecture Overview

The Model Hub is a self-contained subsystem that allows admins to extend the prediction capabilities of the application without modifying application code.

```
HuggingFace Dataset Repo (private)
├── models_registry.json          ← Registry of all models
└── models/
    └── model_{timestamp}_{id}/
        ├── model.onnx            ← ONNX computation graph (preferred)
        ├── columns.json          ← JSON array of column names (ONNX format)
        │    OR
        ├── model.pkl             ← sklearn-compatible estimator (pickle format)
        ├── columns.pkl           ← ordered feature column list (pickle format)
        ├── schema.json           ← UI field definitions (both formats)
        └── aliases.json          ← display labels for selectbox values (optional)
```

### 9.2 Registry Design

`models_registry.json` is a JSON file with a single `"models"` array. It is fetched fresh from HuggingFace on each tab load (with a 120-second in-session cache). All mutations (add, activate/deactivate, rollback) return a new dict; the caller is responsible for calling `push_registry()` to persist.

**Versioning and rollback:** Models in the same "family" share a `family_id` or `display_name`. `rollback_to_version(registry, model_id)` deactivates all family members except the target, effectively rolling back to that version.

### 9.3 Schema-to-UI Mapping

`schema_parser.py` is the single point of schema-to-widget mapping. Each field's `ui` key maps to a Streamlit widget via a dispatch table:

| `ui` value | Streamlit widget | Required schema keys |
|---|---|---|
| `slider` | `st.slider` | `min`, `max`; optional `step`, `default`, `row`, `col_span` |
| `selectbox` | `st.selectbox` | `values` list; optional `aliases` dict, `row`, `col_span` |
| `number_input` | `st.number_input` | optional `min`, `max`, `step`, `row`, `col_span` |
| `text_input` | `st.text_input` | optional `default`, `row`, `col_span` |
| `checkbox` | `st.checkbox` | optional `default`, `row`, `col_span` |

**Column-based layout system:** The top-level `layout` key controls the form grid: `{"columns": 2}` produces a two-column form. Fields use `row` (integer group) and `col_span` (1-3) to control placement. Fields without `row` each get their own row, preserving old single-column behaviour. Sliders default to spanning the full row width. All layout keys are fully optional — schemas without them render identically to before.

**Result card label:** The top-level `result_label` key overrides the target variable name on the prediction result card. `get_result_label(schema, fallback)` in `schema_parser.py` reads this and falls back to the registry target name when absent.

**Alias system:** A `selectbox` field may carry an `aliases` dict mapping model values to display labels. `render_schema_form()` always returns the underlying model value. Aliases can be defined inline for small sets or in a separate `aliases.json` sidecar for large sets; sidecar merged at load time, sidecar wins if both present.

### 9.4 Feature Vector Construction

`predictor.py` builds the feature vector aligned to `columns.pkl` ordering:

1. **Direct match:** If the column name appears directly as a schema field name, the value is passed through.
2. **OHE match:** For selectbox fields, columns in the form `{field_name}_{value}` are matched (sklearn `get_dummies` / `pd.get_dummies` convention).
3. **Zero fill:** Columns with no schema match are filled with 0.0 and a warning is generated.

This allows models trained with internal preprocessing pipelines or feature engineering columns not exposed to the user to still receive valid (zero-padded) input vectors.

---

## 10. Financial Tools Design

### 10.1 Module Architecture

All financial utility modules follow a uniform interface pattern:

```python
# Pure-math core (no Streamlit dependency)
result = compute_*(gross_usd=..., country=..., **kwargs)

# Streamlit UI widget (toggle + expander)
render_*(gross_usd=..., location_hint=..., widget_key=..., **kwargs)
```

All modules are fully standalone and degrade gracefully if upstream modules are unavailable.

### 10.2 Financial Tools Chain

The recommended call order in `manual_prediction_tab.py`:

```
prediction (USD)
    │
    ▼
render_currency_converter()     → selected_currency, active_rates
    │
    ▼
render_tax_adjuster()           → effective_rate, post_tax_annual
    │
    ▼
render_col_adjuster()           → ppp_equivalent_usd
    │
    ▼
render_ctc_adjuster()           → base, HRA, bonus, PF, gratuity, allowances
    │
    ▼
render_takehome_adjuster()      → net_annual, net_monthly
    │
    ▼
render_savings_adjuster()       → savings (monthly), annual_savings
    │
    ▼
render_loan_adjuster()          → max_loan, affordable_emi
    │
    ▼
render_budget_planner()         → per-category monthly allocations
    │
    ▼
render_investment_estimator()   → future value at 5/10/20/30 years
    │
    ▼
render_emergency_fund_planner() → 3-month target, 6-month target, months to build
    │
    ▼
render_lifestyle_split()        → discretionary spending tiers and categories
```

### 10.3 Country Resolution

All financial modules delegate country name and ISO-2 resolution to `country_utils.resolve_iso2()` and `country_utils.get_country_name()`. This provides a single source of truth using Babel's CLDR territory data with application-level overrides.

### 10.4 Data Sources

| Module | Data | Source |
|---|---|---|
| `currency_utils` | Exchange rates (live) | open.er-api.com (no key) |
| `tax_utils` | Tax brackets | OECD, TaxFoundation, government portals (2024) |
| `col_utils` | CoL indices | Numbeo, World Bank, EIU (2023/24) |
| `ctc_utils` | CTC component ratios | Government portals, Gulf labour law, employer surveys (2023/24) |
| `takehome_utils` | PF/pension rates | OECD, ILO, official government portals (2023/24) |
| `savings_utils` | Household expense ratios | Numbeo, World Bank (2023/24) |
| `loan_utils` | Interest rates, EMI norms | Central bank policy rates, retail mortgage benchmarks (2023/24) |
| `investment_utils` | Expected returns | Dimson/Marsh/Staunton, IMF, World Bank, local CAGR 2000-2023 |
| `emergency_fund_utils` | Job market stability | World Bank, OECD labour market data |

---

## 11. Database Design

### 11.1 Firestore Structure

```
Firestore
├── users/
│   └── {email}/                    ← User profile document
├── predictions/
│   └── {email}/
│       └── records/
│           └── {auto-id}/          ← One document per prediction
├── feedback/
│   └── {auto-id}/                  ← One document per feedback submission
├── pending_verifications/
│   └── {email}/                    ← Temporary; deleted after verification
└── rate_limits/
    └── {action}__{sha256_prefix}/  ← Attempt counters per action per user
```

### 11.2 Legacy Compatibility

`database.py` retains stub functions (`init_db`, `create_prediction_table`, `delete_expired_sessions`) that are no-ops. These exist so that legacy call sites in `app_resume.py` do not break. The actual database is entirely Firestore.

### 11.3 Prediction Query Pattern

Predictions are fetched in descending `created_at` order, limited to 500 records. The results are then reversed to oldest-first for the profile chart (matching the original ascending-order expectation of the chart code).

---

## 12. UI and Theming Design

### 12.1 Theme

A single dark professional theme is applied globally via `st.markdown()` with a custom CSS block injected in `app_resume.py`. The theme is CSS-variable-based:

| Variable | Value | Usage |
|---|---|---|
| `--primary` | `#3E7DE0` | H1 headings, borders, primary accent |
| `--primary-hover` | `#2F6CD0` | Button hover state |
| `--bg-main` | `#0C1118` | App background |
| `--bg-card` | `#141A22` | Sidebar, cards, expanders |
| `--bg-input` | `#1B2230` | Input fields, plot backgrounds |
| `--border` | `#283142` | Borders, grid lines |
| `--text-main` | `#E6EAF0` | Primary text |
| `--text-muted` | `#9CA6B5` | Secondary text, labels |
| `--success` | `#22C55E` | Success indicators |
| `--warning` | `#F59E0B` | Warning indicators |
| `--error` | `#EF4444` | Error indicators |

### 12.2 Tab Structure

Tabs are constructed dynamically in `app_resume.py`. The base set of tabs is always present; Profile and Admin tabs are appended conditionally based on session state:

```
Base tabs:    Manual Prediction | Resume Analysis | Batch Prediction |
              AI Assistant | Scenario Analysis | Model Analytics |
              Data Insights | Model Hub | HR Tools | About

Conditional:  Profile  (logged in)
              Admin    (is_admin())
```

### 12.3 Fragment Usage

`@st.fragment` is applied to sub-sections that involve user interaction without needing to re-run the entire page:

- Model Analytics sub-sections (regression, diagnostics, classifier, clustering, NLP)
- Model Hub prediction panel and admin sub-sections
- Feedback dashboard in Admin panel
- Resume editor and resume score widgets in Resume Analysis tab
- Data Insights dashboards

---

## 13. PDF Report Generation

### 13.1 Architecture

PDFs are generated using ReportLab with a custom `NumberedCanvas` class that adds "Page X of Y" footers. All heavy library imports (matplotlib, ReportLab, numpy, pandas) are lazy to avoid adding startup latency.

A centralised `_fig_to_image(fig, dpi=150)` helper renders matplotlib figures to ReportLab `ImageReader` objects and immediately closes the figure to prevent memory leaks.

### 13.2 Report Types

| Report | Trigger | Model | Contents |
|---|---|---|---|
| Manual Prediction | "Prepare PDF Report" button | Both | Input summary, predicted salary, breakdowns, confidence interval, insights |
| Resume Analysis | "Prepare PDF Report" button | Both | Resume score, extracted features, predicted salary, recommendations |
| Batch Prediction | "Prepare Batch PDF Report" button | Both | Summary metrics, leaderboard, distribution charts |
| Scenario Analysis | "Prepare PDF Report" button | Both | Scenario comparison table, salary charts, sensitivity sweeps |
| Model Analytics | Immediately available (cached) | Both | Performance metrics, model comparison, feature importance, SHAP charts |

### 13.3 PDF Caching

Model Analytics PDFs are generated once and cached with `@st.cache_data`. Prediction-specific PDFs (manual, resume, batch, scenario) are generated on-demand and stored in `st.session_state` as `BytesIO` buffers. A two-step pattern (Prepare → Download) is used to prevent regenerating the PDF on every rerun.

---

## 14. Feedback and Data Collection Design

### 14.1 Feedback Schema

Feedback is stored in two layers:

**Core record** (always collected): accuracy\_rating, direction, star\_rating, optional actual\_salary.

**Extended data** (optional, expandable section): cross-dataset bridge fields (allows linking App 1 predictions to App 2 features and vice versa for future unified dataset construction), compensation structure, skills, certifications, industry, company context, role context, and free text.

### 14.2 Dataset Building Strategy

The extended feedback schema is designed to build a unified dataset that bridges the two training datasets and captures compensation complexity not present in either:

- App 2 (XGBoost) users can provide age, education, gender → links to App 1 feature space.
- App 1 (RF) users can provide employment type, remote ratio, company size → links to App 2 feature space.
- Both can provide actual compensation breakdown, skills, industry, company type, work conditions.

This creates a progressive real-world dataset for future model retraining without disrupting the current prediction workflow.

### 14.3 Anonymisation

Feedback submitted by unauthenticated users is stored with `username = "anonymous"`. No IP addresses or browser fingerprints are collected. Prediction history is deliberately NOT deleted when an account is deleted, as it is stored under an orphaned email key and contains anonymised salary data.

---

## 15. Deployment Architecture

### 15.1 Streamlit Cloud Deployment

The application is deployed on Streamlit Cloud (free tier) as two separate apps:

| App | URL | Entry Point | Description |
|---|---|---|---|
| Full App | `salaryscope-app.streamlit.app` | `app_resume.py` | Complete feature set including resume analysis, scenario analysis, Model Hub, Admin Panel, and all 11 financial tools |
| Lite App | `salaryscope-lite-app.streamlit.app` | `app-lite.py` | Lightweight version with Manual Prediction, Batch Prediction, Model Analytics, Data Insights, and Profile only |

The split is driven by Streamlit Cloud free-tier memory limits. The lite app removes not only spaCy and pdfplumber but also the HuggingFace Hub dependency, the entire Model Hub subsystem, all 11 financial utility modules, the feedback system, and the Scenario Analysis and Admin Panel tabs — resulting in a significantly smaller memory footprint and faster startup.

The lite app's About tab is also simplified and rendered inline in `app-lite.py` rather than importing `about_tab.py`, reflecting its reduced feature set.

### 15.2 Secrets Configuration

All sensitive configuration is stored in Streamlit Cloud secrets (`.streamlit/secrets.toml`):

| Secret Key | Description |
|---|---|
| `FIREBASE_API_KEY` | Firebase project web API key |
| `FIREBASE_SERVICE_ACCOUNT` | Full service account JSON (TOML table) |
| `ADMIN_EMAIL` | Email address with admin privileges |
| `HF_TOKEN` | HuggingFace access token (write scope) |
| `HF_REPO_ID` | HuggingFace dataset repository ID |
| `IS_LOCAL` | Boolean; enables local-only features (CoL index save/reset) |

### 15.3 Process Model

Streamlit Cloud runs each user session in an isolated Python process. There is no shared in-process state between users. This is the reason the rate limiter uses Firestore as a cross-session persistence layer rather than relying on a shared in-process dict.

---

## 16. Design Decisions and Rationale

| Decision | Rationale |
|---|---|
| Streamlit as the framework | Enables rapid ML app development with minimal frontend code; Python-native |
| Firebase Authentication over custom auth | Eliminates password storage risk; provides verified email flow, password reset out of the box |
| Firestore over SQLite | Persistent, scalable, cloud-native; SQLite does not persist across Streamlit Cloud restarts |
| HuggingFace for model storage | Free private dataset repos with versioned file storage; SDK-based uploads avoid deprecated HTTP endpoints |
| Pre-computed analytics | SHAP values and clustering analytics are expensive; pre-computing in notebooks eliminates startup latency |
| Dependency injection for tabs | Prevents circular imports; ensures cached resources are loaded once; makes tabs independently testable |
| Rule-based NLP over supervised model | No labeled resume dataset available; deterministic and interpretable; suitable for Streamlit Cloud memory constraints |
| Two separate deployments (full vs lite) | The lite app is a substantially reduced build (no resume analysis, scenario analysis, Model Hub, Admin Panel, financial tools, or feedback) primarily to stay within Streamlit Cloud free-tier memory limits but also to offer a simpler entry point |
| joblib over pickle directly | Better compression and cross-version compatibility for sklearn/XGBoost models |
| ONNX as preferred Model Hub format | Eliminates arbitrary code execution on model load; protobuf graph safe to deserialise; onnxruntime is cross-platform and framework-agnostic |
| Dual-format support (ONNX + pickle) | Existing pickle bundles continue working with no migration; ONNX opt-in for new uploads; format detected from bundle contents and recorded in registry |
| Log-transform target for Model 2 | Salary distributions are right-skewed; log transform improves model fit and reduces influence of extreme values |

---

## 17. Known Limitations and Constraints

- The lite app (`app-lite.py`) is a substantially reduced deployment — it excludes Resume Analysis, Scenario Analysis, Model Hub, Admin Panel, HR Tools, all 11 financial tools, and the feedback system. This is by design to fit within Streamlit Cloud free-tier memory limits, not a missing feature.
- Streamlit Cloud free tier has memory limits; large batch files (>10,000 rows) may be slower or cause timeouts.
- spaCy resume parsing is sensitive to PDF formatting; heavily formatted or image-heavy PDFs may produce poor extraction.
- Tax and CoL data is static (updated periodically in code), not real-time.
- Currency rates are cached for 60 minutes; not real-time.
- The confidence interval shown for Model 1 is based on training residual standard deviation, which is an approximation.
- Model Hub bundles use joblib (pickle) serialisation; this is a security risk if bundles from untrusted sources are uploaded.
- Sessions expire after 24 hours; users must re-authenticate.
- No Google OAuth implementation (code is present but commented out).
- Prediction history is not deleted when an account is deleted (by design, for anonymised data retention).
- The feedback-driven dataset is not yet used for model retraining (future scope).

---

*End of Design Document*
