# SalaryScope — Module Reference
**Version:** 1.4.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Author:** Yash Shah  
**Document Type:** Module Reference / API Documentation

---

## Table of Contents

1. [Entry Point](#1-entry-point)
2. [Tab Modules — app/tabs/](#2-tab-modules--apptabs)
3. [Core Modules — app/core/](#3-core-modules--appcore)
4. [Utility Modules — app/utils/](#4-utility-modules--apputils)
5. [Model Hub Modules — app/model_hub/](#5-model-hub-modules--appmodel_hub)
6. [Module Dependency Map](#6-module-dependency-map)

---

## Conventions

**Parameters listed as** `name (type)` — required. `name (type, default)` — optional with default.  
**Returns** — described as the return type and key fields.  
**Side effects** — any Streamlit UI rendered, Firestore writes, or network calls.  
**Raises** — exceptions the caller should handle.

---

## 1. Entry Point

### `app_resume.py`

**Purpose:** Single Streamlit entry point. Orchestrates resource loading, sidebar rendering, and tab mounting. Contains no business logic.

**Startup sequence:**
1. `init_db()` + `create_prediction_table()` — Firestore init stubs (idempotent, guarded by `db_initialized` session flag).
2. `st.set_page_config()` — sets page title and wide layout.
3. Dark professional CSS theme injected via `st.markdown()`.
4. All ML models, datasets, and lookup tables loaded with `@st.cache_resource` / `@st.cache_data`.
5. Sidebar rendered: model selector dropdown, auth widgets (`login_ui`, `register_ui`, `forgot_password_ui`).
6. Tab list constructed dynamically; the full app includes AI Assistant and HR Tools in the base tab set, while Profile and Admin are appended conditionally.
7. Each tab renderer called with full dependency injection.

**Key globals available to tabs (passed as arguments):**

| Symbol | Type | Description |
|---|---|---|
| `IS_APP1` | bool | True if Model 1 (RF) is selected |
| `app1_model` | sklearn estimator | Loaded Random Forest Regressor |
| `app2_model` | XGBoost estimator | Loaded XGBoost Regressor |
| `df_app1` | DataFrame | App 1 training dataset |
| `df_app2` | DataFrame | App 2 training dataset |
| `COUNTRY_NAME_MAP` | dict | ISO-2 → country name mapping |
| `title_features` | callable | `title_features(job_title)` → (is\_junior, is\_senior, is\_exec, is\_mgmt, domain) |

---

## 2. Tab Modules — app/tabs/

### `manual_prediction_tab.py`

#### `render_manual_prediction_tab(**kwargs)`

Renders the Manual Prediction tab for both App 1 and App 2 based on `IS_APP1`.

**Parameters (selected key params):**

| Parameter | Type | Description |
|---|---|---|
| `IS_APP1` | bool | Controls which model branch is rendered |
| `app1_model` | estimator | RF model (None if App 2) |
| `app2_model` | estimator | XGBoost model (None if App 1) |
| `app1_metadata` | dict | Includes `residual_std` for CI calculation |
| `app1_salary_band_model` | estimator | Salary band classifier (App 1 only) |
| `app1_cluster_model_a1` | estimator | KMeans model (App 1 only) |
| `assoc_rules_a1_v2` | DataFrame | Apriori rules (App 1 only) |
| `df_app2` | DataFrame | App 2 dataset for market comparison |
| `title_features` | callable | Job title feature extractor |
| `app1_generate_manual_pdf` | callable | PDF generator for App 1 results |
| `app2_generate_manual_pdf` | callable | PDF generator for App 2 results |

**Side effects:** Renders full prediction form and results. Calls `save_prediction()` if logged in. Calls `feedback_ui()`. Calls all financial tool renderers. Generates PDF on button click.

---

### `resume_analysis_tab.py`

#### `render_resume_tab(**kwargs)`

Renders the Resume Analysis tab for both App 1 and App 2.

The tab now contains a document-mode selector:
- `Resume PDF` — salary prediction workflow with NLP extraction
- `Offer Letter` — compensation extraction workflow rendered by `offer_letter_tab.py`

**Key parameters:**

| Parameter | Type | Description |
|---|---|---|
| `IS_APP1` | bool | Controls which NLP pipeline and model branch is used |
| `app1_model` | estimator | RF model (App 1) |
| `app2_model` | estimator | XGBoost model (App 2) |
| `app1_job_titles` | list | Allowed App 1 job titles (for PhraseMatcher) |
| `app2_job_titles` | list | Allowed App 2 job titles |
| `app1_generate_resume_pdf` | callable | PDF generator |
| `app2_generate_resume_pdf` | callable | PDF generator |

**Internal `@st.fragment` functions (App 1):**
- `render_resume_editor()` — editable extracted feature form
- `render_resume_score()` — score display
- `render_resume_prediction()` — prediction trigger
- `render_resume_results()` — results display with tools

**Session state keys managed:** `resume_features`, `resume_text`, `resume_score_data`, `resume_prediction_result`, `resume_pdf_ready`, `resume_pdf_buffer`, `last_resume_name`.

---

### `llm_assistant_tab.py`

#### `render_llm_assistant_tab()`

Renders the AI Assistant tab in the full app.

**Purpose:** Provides a grounded assistant for app help, prediction explanation, negotiation drafting, resume wording, and report-writing support without replacing the ML salary models.

**Key dependencies used internally:**

| Dependency | Description |
|---|---|
| `app.local_llm.service` | Backend routing, model availability checks, and response generation |
| `app.local_llm.storage_router` | Conversation storage abstraction (local SQLite vs Hugging Face dataset-backed storage) |
| `app.local_llm.exporters` | PDF and Markdown export helpers |
| `app.local_llm.deployment` | Local vs Streamlit Cloud runtime detection |

**Side effects:** Renders the chat UI, stores conversations/messages, and exposes export actions for individual replies and full conversations.

---

### `batch_prediction_tab.py`

#### `render_batch_prediction_tab(**kwargs)`

Renders the Batch Prediction tab for both App 1 and App 2.

**Key parameters:**

| Parameter | Type | Description |
|---|---|---|
| `is_app1` | bool | Model branch selector |
| `APP1_REQUIRED_COLUMNS` | list | Required column names for App 1 |
| `APP2_REQUIRED_COLUMNS` | list | Required column names for App 2 |
| `app1_validate_bulk_dataframe` | callable | Validation function for App 1 uploads |
| `app2_validate_bulk_dataframe` | callable | Validation function for App 2 uploads |
| `convert_drive_link` | callable | Google Drive link → direct download URL |
| `generate_salary_leaderboard` | callable | Produces ranked leaderboard DataFrame |
| `get_plot_df` | callable | Shared helper for plot data preparation |
| `apply_theme` | callable | Applies dark theme to Plotly figures |
| `app1_generate_bulk_pdf` | callable | PDF generator |
| `app2_generate_bulk_pdf` | callable | PDF generator |

**Session state keys managed:** `bulk_result_df`, `bulk_pdf_buffer`.

---

### `scenario_analysis_tab.py`

#### `render_scenario_tab(**kwargs)`

Renders the Scenario Analysis tab.

**Key parameters:**

| Parameter | Type | Description |
|---|---|---|
| `is_app1` | bool | Model branch |
| `app1_model` / `app2_model` | estimator | Active model |
| `apply_theme` | callable | Plotly dark theme applier |
| `colorway` | list | Colour sequence for charts |
| `title_features` | callable | Title feature extractor (App 2) |
| `app1_generate_scenario_pdf` | callable | PDF generator |
| `app2_generate_scenario_pdf` | callable | PDF generator |

**Session state keys managed:** `scenarios_a1`, `scenarios_a2`, `scenario_results_a1`, `scenario_results_a2`, `scenario_pdf_buffer_a1`, `scenario_pdf_buffer_a2`, `scenario_pdf_ready_a1`, `scenario_pdf_ready_a2`.

---

### `model_analytics_tab.py`

#### `render_model_analytics_tab(**kwargs)`

Renders the Model Analytics tab. Internally delegates to `@st.fragment` sub-renderers.

**Internal fragment functions (App 1):**
- `_render_app1_section1_regression(app1_metadata, APP1_MODEL_COMPARISON, apply_theme, model_colors)`
- `_render_app1_section2_diagnostics(analytics_data, apply_theme)`
- `_render_app1_section3_classifier(app1_classifier_metadata, APP1_CLASSIFIER_MODEL_COMPARISON, apply_theme, model_colors)`
- `_render_app1_section4_clustering_assoc(app1_cluster_metadata, analytics_data, df_app1, assoc_rules, apply_theme)`

**Internal fragment functions (App 2):**
- `_render_app2_section1_regression(app2_metadata, APP2_MODEL_COMPARISON, apply_theme, model_colors)`
- `_render_app2_section2_diagnostics(analytics_data, apply_theme)`
- `_render_app2_section3_features(analytics_data, apply_theme)`

**Shared:**
- `_render_resume_nlp_section()` — displayed for both models

**PDF:** `cached_app1_model_analytics_pdf` / `cached_app2_model_analytics_pdf` are `@st.cache_data` functions passed in and called directly.

---

### `data_insights_tab.py`

#### `render_data_insights_tab(is_app1, df_app1, df_app2, country_name_map, apply_theme_fn=None)`

Renders the Data Insights tab. All theming is managed internally; `apply_theme_fn` is accepted for API compatibility but unused.

**Internal `@st.fragment` dashboard functions (App 1):**
- `_app1_dash1(df)` — Salary Landscape and Distribution
- `_app1_dash2(df)` — Human Capital Dimensions
- `_app1_dash3(df)` — Geographic and Role Patterns

**Internal `@st.fragment` dashboard functions (App 2):**
- `_app2_dash1(df)` — Salary Distribution
- `_app2_dash2(df)` — Work Mode and Company Interactions
- `_app2_dash3(df, country_map)` — Job Roles and Geographic Patterns

---

### `model_hub_tab.py`

#### `render_model_hub_tab(user=None, is_admin_user=False)`

Renders the Model Hub tab.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `user` | dict or None | None | Logged-in user dict with `username` key; None = not logged in |
| `is_admin_user` | bool | False | Whether to show admin sections |

**Internal `@st.fragment` functions:**
- `_render_prediction_panel(active_models, user)` — model selector + dynamic form + predict button
- `_render_upload_section(registry, user)` — admin bundle upload
- `_render_registry_manager(registry)` — activate/deactivate/rollback
- `_render_schema_editor()` — visual schema builder + upload/validate

**Registry cache:** Session key `mh_registry_cache` with 120-second TTL. `_get_registry(force=False)` manages the cache. `_invalidate_registry_cache()` forces a fresh fetch on next access.

**Prediction result persistence:** After a successful prediction, the result is stored in `st.session_state[f"mh_pred_result_{model_id}"]` as a plain dict. This allows the result card and currency toggle to remain visible when the `@st.fragment` reruns due to widget interactions (e.g. the currency toggle being clicked) without re-submitting the form.

**Currency conversion:** `render_currency_converter()` from `app.utils.currency_utils` is shown below the result card if the module is importable. The import is guarded in a `try/except` so the tab works even if `currency_utils` is absent (e.g. lite app). Location hint for default currency is derived from the raw input dict by checking common field names: `country`, `location`, `employee_residence`, `company_location`, `country_code`.

---

### `hr_tools_tab.py`

#### `render_hr_tools_tab(**kwargs)`

Renders the HR & Employer Tools tab and forwards shared model resources into the five sub-tools under `app/hr_tools/`.

**Key parameters:**

| Parameter | Type | Description |
|---|---|---|
| `is_app1` | bool | Controls whether App 1 or App 2 input sets are rendered by the HR tools |
| `app1_model` / `app2_model` | estimator | Active salary prediction model |
| `app1_job_titles` / `app2_job_titles` | list | Supported title lists for the active model |
| `app1_countries` / `app2_country_display_options` | list | Location dropdown values |
| `SALARY_BAND_LABELS` | dict | App 1 salary-band labels used in benchmarking and audit output |
| `EXPERIENCE_MAP`, `EMPLOYMENT_MAP`, `COMPANY_SIZE_MAP`, `REMOTE_MAP` | dict | Shared code-to-label mappings for App 2 |
| `title_features` | callable | App 2 title feature extractor used by shared prediction helpers |

**Side effects:** Renders five inner sub-tabs: Hiring Budget, Salary Benchmarking, Candidate Comparison, Offer Checker, and Team Audit. Each tool may run single-row or vectorised predictions and exposes CSV export.

---

### `user_profile.py`

#### `show_profile()`

Renders the User Profile tab. No parameters — reads from `st.session_state`.

**Sections rendered:** Prediction Summary KPIs, Prediction History Chart (scatter, up to 500 points), Prediction History Table, View Prediction Inputs (selectbox + field display), Export Prediction History (CSV/XLSX/JSON), Account Management section (`render_account_management_section()`), Logout button.

**Session state keys read:** `username`, `logged_in`.

---

### `admin_panel.py`

#### `show_admin_panel(username)`

Renders the Admin Panel tab.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `username` | str | Email of the current admin user |

**Internal cached functions:**

| Function | TTL | Description |
|---|---|---|
| `_get_feedback_stats()` | 300s | Aggregates all feedback from Firestore into scalar metrics |
| `_get_recent_feedback(limit=5)` | 120s | Returns the N most recent feedback documents |

**Helper functions:**

| Function | Returns | Description |
|---|---|---|
| `_get_os_info()` | str | OS name and version |
| `_get_arch()` | str | CPU architecture (x86\_64 or ARM64) |
| `_mem_mb()` | float | Current process RSS memory in MB (requires psutil) |
| `_count_users()` | int | Number of documents in Firestore `users` collection |
| `_is_local()` | bool | True if running in local development environment |
| `_get_deployment_label()` | str | "Local" or "Streamlit Cloud" |

---

### `about_tab.py`

#### `render_about_tab()`

Renders the static About tab. No parameters. Contains only `st.markdown` and `st.expander` calls. No business logic.

---

## 3. Core Modules — app/core/

### `auth.py`

#### `login_ui()`

Renders the login form and handles the full authentication flow.

**Side effects:** On success — sets `st.session_state.logged_in = True`, `username`, `_firebase_id_token`, `_session_expiry`. On pending verification — calls `render_verification_pending_ui()`. Calls `check_rate_limit()` before attempting Firebase sign-in. Calls `record_attempt()` on failure, `clear_attempts()` on success.

---

#### `register_ui()`

Renders the registration form and handles account creation.

**Side effects:** On success — calls `_firebase_sign_up_email()`, `ensure_firestore_user()`, `send_verification_email()`, `set_pending_verification()`, `save_pending_verification()`. Calls `check_rate_limit()` and `record_attempt()`.

---

#### `forgot_password_ui()`

Renders the password reset request form.

**Side effects:** Calls Firebase `sendOobCode` (PASSWORD\_RESET). Returns the same success message regardless of whether the email exists (account enumeration protection). Rate limited.

---

#### `logout()`

Clears auth session state and triggers a Streamlit rerun.

**Side effects:** Calls `destroy_session()`. Sets `logged_in = False`, `username = None`. Calls `st.rerun()`.

---

#### `is_admin() → bool`

Checks whether the current session belongs to the admin user.

**Returns:** True if `st.session_state.username.lower() == ADMIN_EMAIL.lower()` and both are non-empty strings.

---

#### `get_logged_in_user() → str or None`

Returns the username (email) of the currently logged-in user, or None.

---

#### `destroy_session()`

Clears all authentication-related session state keys: `logged_in`, `username`, `_firebase_id_token`, `_session_expiry`, `is_admin`, `auth_loading`.

---

### `database.py`

#### `_get_firestore_client() → firestore.Client`

`@st.cache_resource`. Initialises Firebase Admin SDK from `st.secrets["FIREBASE_SERVICE_ACCOUNT"]` and returns a Firestore client. Idempotent — safe to call multiple times.

---

#### `ensure_firestore_user(username, email, display_name=None)`

Creates a Firestore user document at `users/{username}` if it does not already exist. Idempotent.

---

#### `save_prediction(username, model_used, input_data, predicted_salary)`

Writes a prediction record to `predictions/{username}/records/{auto-id}`.

| Parameter | Type | Description |
|---|---|---|
| `username` | str | Email of the logged-in user |
| `model_used` | str | e.g. "Random Forest", "XGBoost" |
| `input_data` | dict | Input fields used for the prediction |
| `predicted_salary` | float | Annual salary in USD |

---

#### `get_user_predictions(username) → list[tuple]`

Returns up to 500 prediction records for the user, ordered oldest-first.

**Returns:** List of tuples `(prediction_id, model_used, input_data_json, predicted_salary, created_at)`.

---

#### `save_pending_verification(email, id_token)`

Stores a pending verification record in `pending_verifications/{email}`. Idempotent.

---

#### `get_pending_verification_db(email) → dict or None`

Returns the pending verification record for the email, or None.

---

#### `clear_pending_verification_db(email)`

Deletes the pending verification record for the email.

---

#### Stub functions (no-ops for legacy compatibility)

`init_db()`, `create_prediction_table()`, `delete_expired_sessions()`, `get_user(username)`, `create_user(username, email, password_hash)`, `create_session(...)`, `get_session(...)`, `delete_session(...)`.

---

### `resume_analysis.py`

#### `load_spacy_model() → spacy.Language`

`@st.cache_resource`. Loads `en_core_web_sm` with `parser` and `textcat` disabled.

---

#### `extract_text_from_pdf(file) → str`

Extracts plain text from an uploaded PDF file using pdfplumber.

**Parameters:** `file` — a Streamlit `UploadedFile` object.  
**Returns:** Concatenated text from all pages.

---

#### `preprocess_resume_text(raw_text) → str`

Cleans extracted PDF text: lowercasing, regex-based noise removal, whitespace normalisation.

---

#### `extract_experience_years(text) → float`

Extracts years of experience from preprocessed resume text using regex patterns. Returns 0.0 if no match found.

---

#### `extract_education_level(text) → int`

Detects education level from keyword matching. Returns 0 (High School), 1 (Bachelor's), 2 (Master's), or 3 (PhD).

---

#### `extract_job_title(text, allowed_job_titles) → tuple[str, str]`

Matches job title using spaCy PhraseMatcher against `JOB_TITLE_ALIASES`.

**Returns:** `(canonical_title, source_label)` where source\_label describes the extraction method.

---

#### `extract_skills(text) → list[str]`

Detects technical skills using spaCy PhraseMatcher against `SKILL_PATTERNS` (~80 skills).

**Returns:** Sorted list of matched skill strings.

---

#### `calculate_resume_score(features) → dict`

Computes App 1 resume score.

**Parameters:** `features` — dict with `years_of_experience`, `education_level`, `skills`.  
**Returns:** Dict with keys `total_score`, `level` ("Basic"/"Moderate"/"Strong"), `experience_score`, `education_score`, `skills_score`, `skills_detected`.

---

#### `extract_resume_features(raw_text, allowed_job_titles, allowed_countries) → dict`

Full App 1 feature extraction pipeline.

**Returns:** Dict with `job_title`, `years_of_experience`, `education_level`, `senior`, `gender`, `country`, `skills`.

---

#### `extract_resume_features_a2(raw_text, allowed_job_titles_a2, allowed_iso_codes_a2) → dict`

Full App 2 feature extraction pipeline.

**Returns:** Dict with `experience_level_a2`, `employment_type_a2`, `job_title_a2`, `employee_residence_a2`, `company_location_a2`, `remote_ratio_a2`, `company_size_a2`, `years_of_experience_a2`, `skills_a2`, `sources_a2`.

---

#### `calculate_resume_score_a2(features_a2) → dict`

Computes App 2 resume score (DS/ML-weighted).

**Returns:** Dict with `total_score_a2`, `level_a2`, `experience_score_a2`, `skills_score_a2`, `title_score_a2`, `ds_skill_count_a2`, `skills_detected_a2`.

---

### `insights_engine.py`

#### `generate_insights_app2(input_dict, prediction, df_app2, title_features_func) → dict`

Generates smart insights for App 2 predictions.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `input_dict` | dict | Must have keys: "Job Title", "Experience Level", "Company Location" |
| `prediction` | float | Predicted salary in USD |
| `df_app2` | DataFrame | App 2 training dataset for market comparison |
| `title_features_func` | callable | `title_features(job_title)` → (jr, sr, exec\_, is\_mgmt, domain) |

**Returns:** Dict with `role` (str), `market_msg` (str), `market_type` ("success"/"warning"/"info").

---

#### `generate_insights_app1(input_dict) → dict`

Generates insights for App 1 predictions.

**Parameters:** `input_dict` — must have "Job Title", "Years of Experience", "Senior Position".  
**Returns:** Dict with `job_group` (str), `experience_category` (str).

---

#### `detect_domain_from_title(job_title) → str`

Classifies a job title into one of: "ml\_ai", "analytics", "data\_eng", "scientist", "other". Priority order is applied: ml\_ai → analytics → data\_eng → scientist → other.

---

#### `classify_job_group_app1(job_title) → str`

Classifies an App 1 job title into one of: "Tech", "Management", "Marketing\_Sales", "HR", "Finance", "Design", "Operations".

---

#### `compute_market_insight(job_title, company_location, experience_label, domain, prediction, df_app2) → tuple[str, str]`

Performs hierarchical market comparison against the App 2 dataset (minimum 15 samples required per subset).

**Returns:** `(message_string, type_string)` where type is "success", "warning", or "info".

---

### `email_verification.py`

#### `send_verification_email(id_token) → tuple[bool, str or None]`

Sends a Firebase email verification link.

**Returns:** `(success, error_message)`. `error_message` is None on success.

---

#### `check_email_verified(id_token) → tuple[bool or None, str or None]`

Checks whether the Firebase account's email is verified.

**Returns:** `(verified, error_message)`. `verified` is None if the check could not complete (network issue).

---

#### `render_verification_pending_ui(email, id_token)`

Renders the "check your inbox" screen with resend and check buttons.

---

#### `set_pending_verification(email, id_token)` / `get_pending_verification() → tuple` / `clear_pending_verification()` / `is_verification_pending() → bool`

Session state helpers for persisting pending verification across Streamlit reruns.

---

### `password_policy.py`

#### `validate_password_strength(password) → list[str]`

Validates a password against all policy rules.

**Returns:** List of human-readable failure messages. Empty list means the password passed all checks.

**Rules applied:** min 12 chars, max 128 chars, uppercase, lowercase, digit, special char, no leading/trailing whitespace, no 3+ identical consecutive chars, not in common-password blocklist (~60 entries).

---

#### `password_strength_hint() → str`

Returns a concise one-line hint string suitable for display below a password input field.

---

### `rate_limiter.py`

#### `check_rate_limit(action, identifier) → tuple[bool, str or None]`

Checks whether the action-identifier pair is rate-limited.

**Parameters:** `action` — one of "login", "register", "resend\_verify", "change\_password", "delete\_account", "forgot\_password". `identifier` — email address.  
**Returns:** `(allowed, error_message)`. Fails open on any error.

---

#### `record_attempt(action, identifier)`

Records a failed attempt. Call after a failed operation. Does not raise on any error.

---

#### `clear_attempts(action, identifier)`

Resets the attempt counter after a successful authentication event. Does not raise on any error.

---

### `account_management.py`

#### `render_account_management_section()`

Single entry point called from `user_profile.show_profile()`. Renders a divider, an "Account Management" subheader, then calls `render_change_password_ui()` and `render_delete_account_ui()`.

---

#### `render_change_password_ui()`

Renders a change-password expander. Re-authenticates via Firebase, validates new password against policy, calls Firebase `update` endpoint to change the password. Rate limited.

---

#### `render_delete_account_ui()`

Renders a delete-account expander. Re-authenticates via Firebase, requires typed confirmation phrase "delete my account", calls Firebase `delete` endpoint, cleans up Firestore documents, clears session state. Rate limited. Prediction history is intentionally retained.

---

## 4. Utility Modules — app/utils/

### `country_utils.py`

#### `get_country_name(iso2) → str`

Returns the English display name for an ISO-3166-1 alpha-2 country code using Babel CLDR data with application-level overrides (e.g. "Hong Kong" instead of CLDR's verbose form).

**Parameters:** `iso2` — ISO-2 code (case-insensitive) or None.  
**Returns:** Country name string. Returns the input unchanged if not found.

---

#### `resolve_iso2(location) → str or None`

Resolves a country name, alias, or ISO-2 code to a canonical uppercase ISO-2 code.

**Lookup order:** (1) direct ISO-2 match via CLDR, (2) exact `_ALIAS_TABLE` match, (3) case-insensitive alias match, (4) case-insensitive CLDR territory name match.  
**Returns:** Uppercase ISO-2 code, or None if resolution fails.

---

### `currency_utils.py`

#### `get_exchange_rates() → dict`

Fetches live USD-based exchange rates from `open.er-api.com`. Cached in-memory for 60 minutes. Falls back to a local JSON file if the network is unavailable.

**Returns:** Dict mapping currency code → rate (float, where 1 USD = rate units of currency).

---

#### `convert_currency(amount_usd, target_currency, rates) → float`

Converts a USD amount to the target currency using the provided rates dict.

---

#### `render_currency_converter(usd_amount, location_hint, widget_key)`

Renders the currency converter toggle + expander widget.

**Parameters:** `usd_amount` (float) — salary in USD. `location_hint` (str) — country name or ISO-2 for default currency selection. `widget_key` (str) — unique widget key prefix.

---

#### `get_active_currency(widget_key) → str`

Returns the currently selected currency code for the given widget instance. Used by downstream modules (e.g. `tax_utils`) to display post-tax figures in the same currency.

---

#### `get_active_rates() → dict`

Returns the currently loaded exchange rates dict (or empty dict if not yet loaded).

---

### `tax_utils.py`

#### `compute_post_tax(gross_usd, country, custom_rate=None) → dict`

Calculates estimated post-tax annual salary.

**Parameters:** `gross_usd` (float), `country` (str — name or ISO-2), `custom_rate` (float or None — override effective rate as a decimal, e.g. 0.25 for 25%).  
**Returns:** Dict with `net_annual`, `net_monthly`, `effective_rate`, `tax_usd`, `country_used`.

---

#### `get_effective_rate(gross_usd, country) → float`

Returns the estimated effective tax rate for the given gross salary and country.

---

#### `render_tax_adjuster(gross_usd, location_hint, widget_key, converted_currency=None, rates=None)`

Renders the tax adjuster toggle + expander. Shows post-tax in USD and optionally in the converted currency if `converted_currency` and `rates` are provided.

---

### `col_utils.py`

#### `get_col_index(location_hint, custom_overrides=None) → tuple[float, str]`

Returns the CoL index for a location.

**Returns:** `(index_value, source_label)` where source is "built-in", "custom", or "default (unknown country)".

---

#### `compute_col_adjusted(gross_usd, work_country, compare_country, custom_work_index=None, custom_compare_index=None, custom_overrides=None) → dict`

Computes the PPP-equivalent salary for the comparison country.

**Returns:** Dict with `ppp_equivalent_usd`, `adjustment_factor`, `work_col_index`, `compare_col_index`.

---

#### `render_col_adjuster(gross_usd, work_country, widget_key, net_usd=None)`

Renders the CoL adjuster toggle + expander.

---

### `ctc_utils.py`

#### `compute_ctc_breakdown(gross_usd, country, custom_rates=None) → dict`

Breaks down gross CTC into components using country-specific rate tables.

**Returns:** Dict with `basic`, `hra`, `bonus`, `pf_employee`, `gratuity`, `other_allowances`, `total` (all in USD/year).

---

#### `render_ctc_adjuster(gross_usd, location_hint, widget_key)`

Renders the CTC breakdown toggle + expander.

---

### `takehome_utils.py`

#### `compute_take_home(gross_usd, country, net_usd=None) → dict`

Estimates monthly and annual net take-home salary after tax, PF, and statutory deductions. Uses `tax_utils` bracket engine if available; falls back to internal tiered estimates.

**Parameters:** `net_usd` — if provided, uses this as the post-tax annual figure instead of recomputing tax.  
**Returns:** Dict with `net_annual`, `net_monthly`, `effective_rate`, `pf_deduction`, `total_deductions`.

---

#### `render_takehome_adjuster(gross_usd, location_hint, widget_key, net_usd=None) → dict`

Renders the take-home adjuster toggle + expander.

**Returns:** Dict with `net_monthly_{widget_key suffix}` for downstream modules.

---

### `savings_utils.py`

#### `compute_savings_potential(net_monthly_usd, country, custom_expense_ratio=None) → dict`

Estimates monthly savings from net income using country-level expense ratios.

**Returns:** Dict with `savings` (monthly), `annual_savings`, `expense_ratio`, `savings_rate`, `monthly_expenses`.

---

#### `render_savings_adjuster(net_monthly_usd, location_hint, widget_key, gross_usd=None) → dict`

Renders the savings estimator toggle + expander.

**Returns:** Dict with `savings` key for downstream use by `investment_utils`.

---

### `loan_utils.py`

#### `compute_loan_affordability(net_monthly_usd, country, custom_rate=None, custom_tenure=None, custom_emi_cap=None) → dict`

Estimates maximum affordable loan using the reducing-balance EMI formula.

**Formula:** `EMI = P × r × (1+r)^n / ((1+r)^n - 1)` where r = monthly rate, n = months.  
**Returns:** Dict with `max_loan`, `affordable_emi`, `loan_rate`, `tenure_years`, `emi_cap_fraction`.

---

#### `render_loan_adjuster(net_monthly_usd, location_hint, widget_key, gross_usd=None)`

Renders the loan affordability toggle + expander with adjustable rate, tenure, and EMI cap sliders.

---

### `budget_utils.py`

#### `compute_budget_allocation(net_monthly_usd, country) → dict`

Computes monthly budget category allocations using country-adjusted envelope budgeting.

**Returns:** Dict with `categories` — list of `{label, amount_usd, pct}` dicts. Categories: Housing, Food, Transport, Healthcare, Savings/Investments, Entertainment/Lifestyle, Miscellaneous.

---

#### `render_budget_planner(net_monthly_usd, location_hint, widget_key, gross_usd=None)`

Renders the budget planner toggle + expander.

---

### `investment_utils.py`

#### `compute_investment_growth(monthly_savings_usd, country, custom_rate=None) → dict`

Projects future value of monthly savings under compound growth.

**Formula:** `FV = PMT × ((1+r)^n - 1) / r` where r = monthly rate, n = months.  
**Returns:** Dict with `value_5yr`, `value_10yr`, `value_20yr`, `value_30yr`, `annual_return_rate`.

---

#### `render_investment_estimator(monthly_savings_usd, location_hint, widget_key, net_monthly_usd=None)`

Renders the investment growth estimator toggle + expander.

---

### `emergency_fund_utils.py`

#### `compute_emergency_fund(net_monthly_usd, country, monthly_contribution=None) → dict`

Estimates emergency fund targets and build timeline.

**Returns:** Dict with `monthly_expense`, `target_3mo`, `target_6mo`, `months_to_3mo`, `months_to_6mo`, `stability_factor`.

---

#### `render_emergency_fund_planner(net_monthly_usd, location_hint, widget_key, gross_usd=None)`

Renders the emergency fund planner toggle + expander.

---

### `lifestyle_utils.py`

#### `compute_lifestyle_split(net_monthly_usd, country) → dict`

Splits discretionary income across lifestyle tiers and spending categories.

**Returns:** Dict with `discretionary` (amount after essentials), `tiers` (list of `{label, monthly_cost, feasibility}`), `discretionary_categories` (list of `{label, amount_usd}`).

---

#### `render_lifestyle_split(net_monthly_usd, location_hint, widget_key, gross_usd=None)`

Renders the lifestyle budget split toggle + expander.

---

### `recommendations.py`

#### `generate_recommendations_app2(input_dict, prediction, df_app2, title_features_func) → list[str]`

Generates career recommendations for App 2 predictions.

**Pipeline:** domain detection → role classification → market type computation → base recs + role tip + market tip.  
**Returns:** List of recommendation strings.

---

#### `generate_recommendations_app1(input_dict) → list[str]`

Generates career recommendations for App 1 predictions.

**Pipeline:** job group classification → experience category → base recs + role tip + senior boost.  
**Returns:** List of recommendation strings.

---

#### `render_recommendations(recommendations)`

Renders a list of recommendation strings as a markdown bullet list. Displays `st.info("No recommendations available.")` for empty input.

---

### `negotiation_tips.py`

#### `generate_negotiation_tips_app1(prediction, salary_band_label, career_stage_label, experience, job_title, country, senior, market_type) → list[str]`

Generates 3 salary negotiation tips for App 1 predictions. Tips are driven by: experience years (numeric), senior flag, country.

---

#### `generate_negotiation_tips_app2(prediction, experience_label, company_size_label, remote_label, company_location, job_title, role, market_type) → list[str]`

Generates 3 salary negotiation tips for App 2 predictions. Tips are driven by: experience level label, company size label, work mode label.

---

#### `render_negotiation_tips(tips)`

Renders a list of tip strings as markdown bullet points.

---

### `feedback.py`

#### `save_feedback(username, model_used, input_data, predicted_salary, accuracy_rating, direction, actual_salary, star_rating, extended=None)`

Writes a feedback document to `feedback/{auto-id}` in Firestore.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `username` | str | Yes | Email or "anonymous" |
| `model_used` | str | Yes | e.g. "Random Forest", "XGBoost" |
| `input_data` | dict | Yes | Input fields used for the prediction |
| `predicted_salary` | float | Yes | Predicted salary in USD |
| `accuracy_rating` | str | Yes | "Yes", "Somewhat", or "No" |
| `direction` | str | Yes | "Too High", "About Right", or "Too Low" |
| `actual_salary` | float or None | No | User-reported actual salary |
| `star_rating` | int | Yes | 1–5 |
| `extended` | dict or None | No | Optional extended data block |

---

#### `feedback_ui(predicted_salary, model_used, input_data)`

Renders the collapsible feedback expander. Internally manages a session-keyed submission flag to prevent duplicate submissions within a session.

---

### `pdf_utils.py`

All PDF generation functions return a `BytesIO` buffer containing the complete PDF.

#### `app1_generate_manual_pdf(input_details, prediction, salary_band, career_stage, metadata) → BytesIO`

#### `app2_generate_manual_pdf(input_details, prediction, lower_bound, upper_bound, metadata) → BytesIO`

#### `app1_generate_resume_pdf(result_dict) → BytesIO`

#### `app2_generate_resume_pdf(input_details, prediction, lower_bound, upper_bound, metadata) → BytesIO`

#### `app1_generate_bulk_pdf(result_df) → BytesIO`

#### `app2_generate_bulk_pdf(result_df, country_name_map) → BytesIO`

#### `app1_generate_scenario_pdf(scenario_df) → BytesIO`

#### `app2_generate_scenario_pdf(scenario_df) → BytesIO`

#### `cached_app1_model_analytics_pdf(metadata, model_comparison, classifier_metadata, analytics_data, cluster_metadata, assoc_rules, model, salary_band_model) → BytesIO`

`@st.cache_data` — generated once, served from cache on subsequent calls.

#### `cached_app2_model_analytics_pdf(metadata, model_comparison, analytics_data, model) → BytesIO`

`@st.cache_data` — generated once, served from cache on subsequent calls.

**Internal helpers:**

| Function | Description |
|---|---|
| `_fig_to_image(fig, dpi=150) → ImageReader` | Renders a matplotlib figure to a ReportLab ImageReader; closes the figure immediately to prevent memory leaks |
| `_get_numbered_canvas()` | Lazily creates and caches the `NumberedCanvas` class with "Page X of Y" footer support |

---

## 5. Model Hub Modules — app/model_hub/

### `_hf_client.py`

Low-level HuggingFace SDK wrapper. All other Model Hub modules import from this file for HF operations.

**Configuration (resolved at import time):**

| Variable | Source | Description |
|---|---|---|
| `HF_TOKEN` | `st.secrets["HF_TOKEN"]` or `os.environ["HF_TOKEN"]` | HuggingFace write-scope access token |
| `HF_REPO_ID` | `st.secrets["HF_REPO_ID"]` or `os.environ["HF_REPO_ID"]` | Dataset repo in the form "owner/repo-name" |
| `REGISTRY_PATH` | hardcoded | `"models_registry.json"` |
| `MAX_MODEL_FILE_BYTES` | hardcoded | `200 * 1024 * 1024` (200 MB) |

#### `download_file_bytes(path_in_repo) → bytes`

Downloads a file from the HuggingFace dataset repo using `hf_hub_download`.

**Raises:** `FileNotFoundError` if the file does not exist. `PermissionError` on 401/403. `RuntimeError` on other failures.

---

#### `upload_file_bytes(path_in_repo, data, commit_message="Upload via Model Hub")`

Uploads raw bytes to the repo using `HfApi.create_commit` with `CommitOperationAdd`.

**Raises:** `PermissionError` if token is missing or lacks write scope. `RuntimeError` on upload failure.

---

#### `file_size_bytes(path_in_repo) → int or None`

Returns the file size in bytes using `HfApi.get_paths_info`. Returns None if unavailable (non-blocking).

---

#### `list_repo_paths(prefix="models/") → list[str]`

Lists all file paths under a prefix using `HfApi.list_repo_tree`. Returns empty list on any error.

---

### `registry.py`

#### `fetch_registry(raw=False) → dict`

Fetches and parses `models_registry.json` from HuggingFace. Returns an empty `{"models": []}` if the file does not exist. Validates each entry and skips malformed ones (logs a warning).

**Raises:** `RuntimeError` if the file cannot be fetched or parsed.

---

#### `get_active_models(registry) → list[dict]`

Returns models with `"active": true` from the registry dict.

---

#### `get_model_by_id(registry, model_id) → dict or None`

Returns the registry entry for a given model ID, or None.

---

#### `add_model_to_registry(registry, model_entry) → dict`

Returns a new registry dict with `model_entry` appended. Does not push to HuggingFace.

**Raises:** `ValueError` if the model ID already exists or the entry is invalid.

---

#### `set_model_active(registry, model_id, active) → dict`

Returns a new registry dict with the model's `active` flag updated.

**Raises:** `ValueError` if the model ID is not found.

---

#### `rollback_to_version(registry, model_id) → dict`

Activates `model_id` and deactivates all other models in the same family (`family_id` or `display_name` match).

**Raises:** `ValueError` if the model ID is not found.

---

#### `push_registry(registry)`

Serialises and uploads `models_registry.json` to HuggingFace.

**Raises:** `RuntimeError` on upload failure.

---

### `loader.py`

#### `load_bundle(model_meta, force_reload=False) → ModelBundle`

Downloads and deserialises a model bundle from HuggingFace. Checks session cache first; downloads on miss. Enforces size limits pre- and post-download. Logs a security notice on every deserialisation.

**Parameters:** `model_meta` — registry entry dict with `id` and `path` keys. `force_reload` — bypass session cache.  
**Returns:** `ModelBundle` instance with aliases merged into schema if `aliases.json` is present in the bundle folder.  
**Raises:** `RuntimeError` on size limit breach, missing files, or deserialisation failure.  
**Format detection:** `load_bundle()` probes for `model.onnx` first. If found, loads `model.onnx` + `columns.json` via onnxruntime (no pickle). If absent, falls back to `model.pkl` + `columns.pkl` (legacy path). Both paths populate an identical `ModelBundle` object.  
**Cache note:** `schema.json` and `aliases.json` are always fetched with `force_download=True` to pick up any in-place updates. `model.onnx`, `model.pkl`, `columns.json`, and `columns.pkl` use the SDK disk cache (immutable once written).

---

#### `clear_bundle_cache(model_id=None)`

Clears the session cache for one model (if `model_id` provided) or all models.

---

#### `ModelBundle`

Dataclass with `__slots__`:

| Attribute | Type | Description |
|---|---|---|
| `model_id` | str | Registry ID |
| `model` | Any | Deserialised sklearn-compatible estimator |
| `columns` | list[str] | Ordered feature column names |
| `schema` | dict | Parsed schema dict (aliases already merged in if `aliases.json` was found) |
| `model_meta` | dict | Raw registry entry |
| `has_aliases` | bool | True if `aliases.json` was found and merged at load time |
| `bundle_format` | str | `"onnx"` or `"pickle"` — set at load time; used by `predictor.py` to route inference to the correct API |

---

### `predictor.py`

#### `predict(bundle, raw_input) → PredictionResult`

Runs a prediction using a loaded `ModelBundle`.

**Parameters:** `bundle` — `ModelBundle` instance. `raw_input` — `{field_name: value}` dict from `render_schema_form()`.  
**Dispatch:** Routes to `_predict_onnx()` (onnxruntime) or `_predict_pickle()` (sklearn DataFrame) based on `bundle.bundle_format`.  
**Raises:** `RuntimeError` if the model fails to predict or returns a non-finite value. `ValueError` if the feature vector length mismatches the column count.

---

#### `PredictionResult`

Dataclass with `__slots__`:

| Attribute | Type | Description |
|---|---|---|
| `value` | float | Predicted scalar value |
| `model_id` | str | Registry ID of the model |
| `target` | str | Name of the predicted variable |
| `warnings` | list[str] | Any feature vector construction warnings |
| `raw_input` | dict | Original form input values |
| `feature_vector` | list[float] | Aligned numeric feature vector |

---

### `schema_parser.py`

#### `render_schema_form(schema, key_prefix="mh_form") → dict`

Renders Streamlit input widgets for all fields in `schema["fields"]`.

**Parameters:** `schema` — validated schema dict (aliases already merged in by `loader.py`). `key_prefix` — unique string prefix for all widget keys (use a stable, model-specific prefix).  
**Returns:** `{field_name: model_value}` dict. For aliased selectbox fields, the user sees display labels but the returned values are always the underlying model values.

**Widget dispatch table:**

| `ui` value | Handler function |
|---|---|
| `"slider"` | `_widget_slider()` |
| `"selectbox"` | `_widget_selectbox()` |
| `"number_input"` | `_widget_number_input()` |
| `"text_input"` | `_widget_text_input()` |
| `"checkbox"` | `_widget_checkbox()` |

Respects optional `layout`, `row`, and `col_span` schema keys for multi-column grid rendering. Schemas without these keys render in a single column, identical to old behaviour.

Unknown `ui` values fall back to `_widget_text_input()` with a warning.

---

#### `get_result_label(schema, fallback) -> str`

Returns the label to display on the prediction result card.

**Parameters:** `schema` — parsed schema dict. `fallback` — string to use when `schema["result_label"]` is absent or empty (typically `model_meta["target"]`).  
**Returns:** Non-empty string. Checks `schema["result_label"]` first; falls back to `fallback`.

**Alias helper functions (internal):**

| Function | Description |
|---|---|
| `_build_alias_map(field)` | Returns `{model_value: display_label}` dict, or `{}` if no aliases defined |
| `_display_options(field)` | Returns list of strings to show in selectbox — alias labels where defined, raw values otherwise |
| `_resolve_to_model_value(field, display_label)` | Inverts the alias map to return the model value for a selected display label |

---

### `uploader.py`

#### `upload_bundle_onnx(onnx_bytes, columns_json_bytes, schema_bytes, display_name, description="", target="prediction", uploaded_by="admin", family_id=None, aliases_bytes=None) → UploadResult`

Validates and uploads an ONNX bundle (model.onnx + columns.json + schema.json) to HuggingFace. Verifies the ONNX model loads cleanly via onnxruntime and that `columns.json` is a valid JSON string array. Registry entry includes `"bundle_format": "onnx"`.

**Returns:** `UploadResult` with `folder_name`, `folder_path`, `registry_entry`, `warnings`.  
**Raises:** `ValueError` on validation failures (including onnxruntime load errors). `RuntimeError` on upload failures.

---

#### `upload_bundle(model_bytes, columns_bytes, schema_bytes, display_name, description="", target="prediction", uploaded_by="admin", family_id=None, aliases_bytes=None) → UploadResult`

Validates and uploads a pickle bundle (model.pkl + columns.pkl + schema.json) to HuggingFace. Registry entry includes `"bundle_format": "pickle"`.

**Returns:** `UploadResult` with `folder_name`, `folder_path`, `registry_entry`, `warnings`. Registry entry includes `has_aliases` boolean.  
**Raises:** `ValueError` on validation failures. `RuntimeError` on upload failures.

---

#### `upload_schema_only(schema_bytes, model_id, bundle_path) → list[str]`

Uploads only `schema.json` to an existing bundle path.

**Returns:** List of warnings (empty on success).  
**Raises:** `ValueError` on schema validation failure. `RuntimeError` on upload failure.

---

#### `upload_aliases_only(aliases_bytes, model_id, bundle_path, schema) → None`

Uploads or replaces `aliases.json` in an existing bundle folder. Validates the aliases against the provided schema before uploading and clears the session bundle cache for `model_id` so the next Load Model picks up the new aliases.

**Parameters:** `aliases_bytes` — raw bytes of the new `aliases.json`. `model_id` — registry id (used for cache clearing). `bundle_path` — bundle folder path. `schema` — parsed schema dict for validation.  
**Raises:** `ValueError` on validation failure. `RuntimeError` on upload failure.

---

#### `UploadResult`

Dataclass with `__slots__`:

| Attribute | Type | Description |
|---|---|---|
| `folder_name` | str | Generated folder name: `model_{timestamp}_{6-char-random}` |
| `folder_path` | str | Full path: `models/{folder_name}/` |
| `registry_entry` | dict | Complete registry entry dict ready for `add_model_to_registry()` |
| `warnings` | list[str] | Schema-column consistency warnings |

---

### `validator.py`

Pure Python — no Streamlit dependency. Safe to use in offline tools or CI pipelines.

#### `validate_schema(schema) → list[str]`

Validates the structure of a parsed schema dict. Returns a list of issue strings; empty list = valid.

**Checks:** Top-level `fields` key present and is a list; each field has `name`, `type`, `ui`; no duplicate names; allowed `type` and `ui` values; per-widget constraints (slider min/max, selectbox values non-empty, number\_input min < max); default within [min, max] for sliders. Optional top-level keys: `layout.columns` must be 1, 2, or 3 if present; `result_label` must be a non-empty string if present. Optional per-field keys: `row` must be an integer if present; `col_span` must be 1-3 if present.

---

#### `validate_schema_vs_columns(schema, columns) → list[str]`

OHE-aware consistency check between schema fields and `columns.pkl`.

**OHE matching:** A `selectbox` field named `job_title` with values `["A", "B"]` is matched if columns contains `job_title_A` and `job_title_B`.  
**Returns:** List of issues including truly missing fields and informational notes about unaccounted extra columns.

---

#### `validate_aliases(aliases, schema) → list[str]`

Validates an `aliases.json` dict against a parsed schema.

**Checks:** Top-level must be a dict. Every field name must exist in the schema. Every model value in each alias sub-dict must exist in the field's `values` list. Labels must be non-empty strings. Duplicate display labels within a single field are flagged (they break the reverse lookup used by `schema_parser.py`).  
**Returns:** List of issue strings; empty = valid.

---

#### `validate_bundle_files(file_names) → list[str]`

Format-aware bundle completeness check. Accepts two valid combinations:
- ONNX: `model.onnx` + `columns.json` + `schema.json`
- Pickle: `model.pkl` + `columns.pkl` + `schema.json`

Returns a sorted list of missing required file names, or a format error if the model and columns files do not match format. `aliases.json` is optional and not checked here.

---

#### `detect_bundle_format(file_names) → str`

Returns `"onnx"`, `"pickle"`, or `"unknown"` based on which model file is present in `file_names`. Used by the upload panel UI to show the correct format label and route to the correct upload function.

---

#### `parse_schema_json(raw) → tuple[dict, list[str]]`

Parses raw JSON bytes/string and validates it.

**Returns:** `(schema_dict, issues_list)`. `schema_dict` is `{}` if JSON is invalid.

---

## 6. Module Dependency Map

```
app_resume.py
    ├── app/tabs/manual_prediction_tab.py
    │       ├── app/core/insights_engine.py
    │       ├── app/utils/recommendations.py
    │       ├── app/utils/negotiation_tips.py
    │       ├── app/utils/currency_utils.py
    │       ├── app/utils/tax_utils.py
    │       ├── app/utils/col_utils.py
    │       ├── app/utils/ctc_utils.py
    │       ├── app/utils/takehome_utils.py
    │       ├── app/utils/savings_utils.py
    │       ├── app/utils/loan_utils.py
    │       ├── app/utils/budget_utils.py
    │       ├── app/utils/investment_utils.py
    │       ├── app/utils/emergency_fund_utils.py
    │       ├── app/utils/lifestyle_utils.py
    │       ├── app/utils/feedback.py
    │       └── app/core/database.py (save_prediction)
    │
    ├── app/tabs/resume_analysis_tab.py
    │       ├── app/core/resume_analysis.py
    │       ├── app/core/insights_engine.py
    │       ├── app/utils/recommendations.py
    │       ├── app/utils/negotiation_tips.py
    │       ├── app/utils/currency_utils.py
    │       ├── app/utils/tax_utils.py
    │       ├── app/utils/col_utils.py
    │       └── app/core/database.py (save_prediction)
    │
    ├── app/tabs/batch_prediction_tab.py  (no core/util imports)
    ├── app/tabs/scenario_analysis_tab.py (no core/util imports)
    │
    ├── app/tabs/model_analytics_tab.py   (no core/util imports)
    ├── app/tabs/data_insights_tab.py     (no core/util imports)
    │
    ├── app/tabs/model_hub_tab.py
    │       └── app/model_hub/* (self-contained)
    │               └── app/model_hub/_hf_client.py
    │
    ├── app/tabs/user_profile.py
    │       ├── app/core/auth.py
    │       ├── app/core/database.py
    │       └── app/core/account_management.py
    │               ├── app/core/auth.py (lazy)
    │               ├── app/core/database.py (lazy)
    │               ├── app/core/rate_limiter.py (lazy)
    │               └── app/core/password_policy.py
    │
    ├── app/tabs/admin_panel.py
    │       └── app/core/database.py
    │
    ├── app/tabs/about_tab.py             (stdlib + streamlit only)
    │
    ├── app/core/auth.py
    │       ├── app/core/email_verification.py
    │       ├── app/core/password_policy.py
    │       ├── app/core/rate_limiter.py
    │       └── app/core/database.py (lazy import)
    │
    └── app/utils/pdf_utils.py            (lazy imports, no core deps)

All financial utils (currency, tax, col, ctc, takehome, savings,
loan, budget, investment, emergency_fund, lifestyle):
    └── app/utils/country_utils.py        (Babel CLDR, no app deps)
```

---

*End of Module Reference*
