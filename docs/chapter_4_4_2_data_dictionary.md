# Chapter 4.2 — Data Dictionary

**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Version:** 1.6.0  
**Purpose:** Submission-ready data dictionary for the college report, Chapter 4, Section 4.2.

---

## 1. Introduction

This section summarises the main data entities, datasets, persistent collections, and structured configuration files used by SalaryScope. It is intentionally shorter and more report-oriented than the full technical reference in `docs/data_dictionary.md`.

---

## 2. Training Dataset for Model 1

**Caption: Table 4.2.1 — Data dictionary for the general salary dataset used by Model 1**

| Field Name | Data Type | Example / Allowed Values | Description |
|---|---|---|---|
| `Age` | Integer | `18` to `70` | Candidate age in years |
| `Years of Experience` | Float | `0.0` to `40.0` | Total work experience in years |
| `Education Level` | Integer | `0, 1, 2, 3` | Encoded highest education level |
| `Senior` | Integer | `0` or `1` | Indicates whether the role is senior |
| `Gender` | String | `Male`, `Female` | Gender field used in the source dataset |
| `Job Title` | String | e.g. `Data Analyst` | Canonical job title |
| `Country` | String | e.g. `United States`, `India`, `Other` | Country of the role |
| `Salary` | Float | Annual salary in USD | Target variable predicted by Model 1 |

**Caption: Table 4.2.2 — Education level encoding used in Model 1**

| Code | Education Level |
|---|---|
| `0` | High School |
| `1` | Bachelor's Degree |
| `2` | Master's Degree |
| `3` | PhD |

---

## 3. Training Dataset for Model 2

**Caption: Table 4.2.3 — Data dictionary for the data science salary dataset used by Model 2**

| Field Name | Data Type | Example / Allowed Values | Description |
|---|---|---|---|
| `experience_level` | String | `EN`, `MI`, `SE`, `EX` | Experience level code |
| `employment_type` | String | `FT`, `PT`, `CT`, `FL` | Employment type code |
| `job_title` | String | e.g. `Machine Learning Engineer` | Data science job title |
| `employee_residence` | String | ISO-2 country code | Employee residence country |
| `remote_ratio` | Integer | `0`, `50`, `100` | On-site, hybrid, or remote work ratio |
| `company_location` | String | ISO-2 country code | Company country |
| `company_size` | String | `S`, `M`, `L` | Small, medium, or large company |
| `salary_in_usd` | Float | Annual salary in USD | Target variable predicted by Model 2 |

**Caption: Table 4.2.4 — Encoded fields used in Model 2**

| Field | Code | Meaning |
|---|---|---|
| `experience_level` | `EN` | Entry Level |
| `experience_level` | `MI` | Mid Level |
| `experience_level` | `SE` | Senior Level |
| `experience_level` | `EX` | Executive Level |
| `employment_type` | `FT` | Full Time |
| `employment_type` | `PT` | Part Time |
| `employment_type` | `CT` | Contract |
| `employment_type` | `FL` | Freelance |
| `company_size` | `S` | Small Company |
| `company_size` | `M` | Medium Company |
| `company_size` | `L` | Large Company |
| `remote_ratio` | `0` | On-site |
| `remote_ratio` | `50` | Hybrid |
| `remote_ratio` | `100` | Fully Remote |

---

## 4. Firestore Collections

### 4.1 Users Collection

**Caption: Table 4.2.5 — Data dictionary for `users/{email}`**

| Field Name | Data Type | Description |
|---|---|---|
| `username` | String | Email used as username |
| `email` | String | Registered email address |
| `display_name` | String | User-selected display name |
| `created_at` | String | ISO-8601 timestamp of account creation |
| `auth_provider` | String | Authentication source, currently `firebase` |

### 4.2 Predictions Collection

**Caption: Table 4.2.6 — Data dictionary for `predictions/{email}/records/{auto-id}`**

| Field Name | Data Type | Description |
|---|---|---|
| `model_used` | String | Prediction model used for the record |
| `input_data` | String | JSON-serialised prediction input data |
| `predicted_salary` | Float | Predicted annual salary in USD |
| `created_at` | String | ISO-8601 timestamp |

### 4.3 Feedback Collection

**Caption: Table 4.2.7 — Data dictionary for `feedback/{auto-id}`**

| Field Name | Data Type | Description |
|---|---|---|
| `username` | String | Logged-in user email or `anonymous` |
| `model_used` | String | Model used for prediction |
| `input_data` | String | JSON-serialised prediction input |
| `predicted_salary` | Float | Predicted annual salary in USD |
| `accuracy_rating` | String | User rating of prediction accuracy |
| `direction` | String | Indicates if prediction was too high, about right, or too low |
| `actual_salary` | Float / Null | Optional user-reported actual salary |
| `star_rating` | Integer | User rating on a 1–5 scale |
| `created_at` | String | ISO-8601 timestamp |
| `extended_data` | Object | Optional richer context for future model improvement |

**Caption: Table 4.2.8 — Important sub-fields inside `feedback.extended_data`**

| Field Name | Data Type | Description |
|---|---|---|
| `age` | Integer | Cross-dataset enrichment field |
| `education_level` | Integer | Encoded education level |
| `is_senior` | Integer | Seniority bridge field |
| `gender` | String | Additional demographic field |
| `employment_type` | String | Employment type bridge field |
| `remote_ratio` | Integer | Remote work bridge field |
| `company_size` | String | Company size bridge field |
| `company_location` | String | Company country bridge field |
| `actual_base_usd` | Float | Actual base compensation |
| `actual_total_comp_usd` | Float | Actual total compensation |
| `skills` | Array of String | User-provided skill list |
| `industry` | String | Industry context |
| `additional_context` | String | Optional free-text note |

### 4.4 Pending Verifications Collection

**Caption: Table 4.2.9 — Data dictionary for `pending_verifications/{email}`**

| Field Name | Data Type | Description |
|---|---|---|
| `email` | String | Email awaiting verification |
| `id_token` | String | Temporary Firebase token |
| `created_at` | String | ISO-8601 timestamp |

### 4.5 Rate Limits Collection

**Caption: Table 4.2.10 — Data dictionary for `rate_limits/{action__hash}`**

| Field Name | Data Type | Description |
|---|---|---|
| `attempts` | Integer | Attempt count within the current rate-limit window |
| `window_start` | Float | Epoch timestamp marking the window start |

---

## 5. Resume Analysis and Extraction Data

**Caption: Table 4.2.11 — Main extracted resume fields used in Resume Analysis**

| Field Name | Data Type | Description |
|---|---|---|
| `job_title` / `job_title_a2` | String | Extracted canonical job title |
| `years_of_experience` / `years_of_experience_a2` | Float | Extracted experience in years |
| `education_level` | Integer | Encoded education level for Model 1 |
| `senior` | Integer | Senior flag for Model 1 |
| `country` | String | Extracted country name for Model 1 |
| `employee_residence_a2` | String | ISO-2 residence code for Model 2 |
| `company_location_a2` | String | ISO-2 company location code for Model 2 |
| `employment_type_a2` | String | Employment type code for Model 2 |
| `remote_ratio_a2` | Integer | Remote ratio code for Model 2 |
| `company_size_a2` | String | Company size code for Model 2 |
| `skills` / `skills_a2` | Array of String | Matched skill list |
| `sources_a2` | Object | Per-field extraction source tracking for transparency |

**Caption: Table 4.2.12 — Resume scoring outputs used by SalaryScope**

| Field Name | Data Type | Description |
|---|---|---|
| `resume_score` | Integer / Float | Overall resume score out of 100 |
| `experience_score` | Integer / Float | Score contribution from experience |
| `education_score` | Integer / Float | Score contribution from education |
| `skills_score` | Integer / Float | Score contribution from skill coverage |
| `strength_label` | String | Basic, Moderate, or Strong profile label |
| `ats_readiness_score` | Integer | Rule-based ATS readiness signal |
| `role_match_score` | Integer | Role alignment signal |
| `parse_confidence_score` | Integer | Confidence in extracted data quality |

---

## 6. Offer Letter Extraction Data

**Caption: Table 4.2.13 — Main extracted offer-letter fields**

| Field Name | Data Type | Description |
|---|---|---|
| `candidate_name` | String | Candidate named in the offer letter |
| `company_name` | String | Hiring company |
| `job_title` | String | Offered role title |
| `level_or_band` | String | Job level or band |
| `location` | String | Work location |
| `work_mode` | String | On-site, hybrid, or remote |
| `country_code` | String | Resolved ISO-2 country code |
| `currency_code` | String | Currency of the offer |
| `base_salary` | Float | Base annual salary |
| `total_ctc` | Float | Total annual compensation / CTC |
| `joining_bonus` | Float | One-time joining bonus |
| `annual_bonus_fixed` | Float / Null | Fixed annual bonus if stated |
| `annual_bonus_percent` | Float / Null | Annual bonus percentage if stated |
| `equity_mentioned` | Boolean | Whether equity or ESOP is mentioned |
| `equity_text` | String | Extracted equity clause text |
| `probation_period` | String | Probation period text |
| `notice_period` | String | Notice period text |
| `pay_frequency` | String | Salary payment frequency |

---

## 7. Model Hub Configuration Data

**Caption: Table 4.2.14 — Key files inside a Model Hub bundle**

| File Name | Data Type / Format | Description |
|---|---|---|
| `model.onnx` / `model.pkl` | ONNX / Pickle | Trained model artifact |
| `columns.json` / `columns.pkl` | JSON / Pickle | Ordered feature list |
| `schema.json` | JSON | User input schema for dynamic prediction forms |
| `aliases.json` | JSON | Display aliases for selectbox values |
| `skills.json` | JSON | Optional per-bundle skill lexicon |
| `job_titles.json` | JSON | Optional per-bundle title lexicon |
| `resume_config.json` | JSON | Optional per-bundle extraction override configuration |

**Caption: Table 4.2.15 — Core fields in `models_registry.json`**

| Field Name | Data Type | Description |
|---|---|---|
| `id` | String | Unique model bundle identifier |
| `display_name` | String | Name shown in the UI |
| `path` | String | Repository path of the bundle |
| `target` | String | Predicted target label |
| `active` | Boolean | Whether the bundle is available to users |
| `version` | Integer | Bundle version number |
| `uploaded_at` | String | Upload timestamp |
| `uploaded_by` | String | Admin username |
| `size_bytes` | Integer | Total uploaded size |
| `schema_version` | String | Bundle schema version |
| `num_features` | Integer | Number of model features |
| `num_inputs` | Integer | Number of input fields in `schema.json` |
| `bundle_format` | String | `onnx` or `pickle` |

---

## 8. Interview Prep Configuration Data

**Caption: Table 4.2.16 — Core fields in `registry_ia.json`**

| Field Name | Data Type | Description |
|---|---|---|
| `id` | String | Unique practice set ID |
| `title` | String | Practice set title shown in the UI |
| `category` | String | Practice category |
| `role_focus` | String | Role or domain focus |
| `difficulty` | String | Difficulty label |
| `file` | String | JSON file path for the set |
| `enabled` | Boolean | Whether the set is visible in the UI |
| `estimated_minutes` | Integer | Approximate duration |

**Caption: Table 4.2.17 — Core fields in an Interview Prep question-set JSON file**

| Field Name | Data Type | Description |
|---|---|---|
| `metadata` | Object | Set-level details such as title and difficulty |
| `settings` | Object | Timing, scoring, and review behaviour |
| `sections` | Array | Logical section grouping |
| `questions` | Array | List of questions in the set |
| `question.id` | String | Unique question identifier |
| `question.type` | String | Question type such as single choice or numeric |
| `question.prompt` | String | User-facing question text |
| `question.options` | Array | Answer options where relevant |
| `question.answer` | Any | Expected correct answer |
| `question.explanation` | String | Explanation shown in review |
| `question.marks` | Number | Marks assigned to the question |

---

## 9. Conclusion

The project uses a combination of structured tabular datasets, Firestore collections, JSON configuration files, and Streamlit session-state objects. The most important persistent data structures for the deployed system are the training datasets, Firebase collections, Model Hub bundle files, Interview Prep registries, and extracted resume or offer-letter fields used during prediction workflows.

For the full technical reference, including extended mappings, session-state keys, and financial utility constants, see `docs/data_dictionary.md`.
