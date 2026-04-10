# SalaryScope — Data Dictionary

> **Version 1.0 · April 2026**  
> Definitions of all data fields used across datasets, models, Firestore collections, and the application interface.
> All datasets used in this project are preprocessed and cleaned versions of publicly available datasets. Modifications include duplicate removal, feature selection, categorical normalization, and removal of non-informative attributes.
> Resume feature extraction uses a combination of spaCy-based entity recognition, phrase matching, and rule-based methods (regex and keyword matching).
---

## 1. Model 1 Training Dataset — `Salary_Streamlit_App.csv`

Source: [Kaggle — Salary by Job Title and Country](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)

| Column Name | Data Type | Range / Values | Description |
|---|---|---|---|
| `Age` | Integer | 21–62 | Age of the individual in years |
| `Years of Experience` | Float | 0.0–34.0 | Total professional work experience in years |
| `Education Level` | Integer (encoded) | 0, 1, 2, 3 | Education level: 0=High School, 1=Bachelor's, 2=Master's, 3=PhD |
| `Senior` | Integer (binary) | 0, 1 | 1 if the position is a senior-level role, 0 otherwise |
| `Gender` | String (categorical) | Male, Female | Self-reported gender |
| `Job Title` | String (categorical) | 100+ distinct roles | Professional role/designation (e.g., Software Engineer, Data Analyst) |
| `Country` | String (categorical) | 50+ countries | Country of employment |
| `Salary` | Float | ~$25,000–$250,000 | Annual gross salary in USD (**target variable**) |

### Preprocessing Applied

- Data preprocessing is implemented using a `ColumnTransformer` pipeline.
- Numerical features are passed directly (no scaling) for tree-based models such as Random Forest.
- A separate preprocessing pipeline with `StandardScaler` is defined for non-tree models, but not used in the final Random Forest model.
- Categorical features (`Gender`, `Job Title`, `Country`) are encoded using `OneHotEncoder` with `handle_unknown="ignore"` to safely process unseen categories.
- The dataset was verified to contain no missing values, so no imputation or removal was required.
- Duplicate records were removed, and certain non-essential columns (e.g., `Race`) were excluded prior to training.
- Minor inconsistencies in categorical values (e.g., job titles) were standardized to ensure consistent encoding.

---

## 2. Model 2 Training Dataset — `ds_salaries_Streamlit_App.csv`

Source: [Kaggle — Data Science Salaries 2023](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)

| Column Name | Data Type | Range / Values | Description |
|---|---|---|---|
| `experience_level` | String (categorical) | EN, MI, SE, EX | Experience level: EN=Entry, MI=Mid, SE=Senior, EX=Executive |
| `employment_type` | String (categorical) | FT, PT, CT, FL | Employment type: FT=Full-time, PT=Part-time, CT=Contract, FL=Freelance |
| `job_title` | String (categorical) | 100+ distinct titles | Data science or AI/ML role title |
| `employee_residence` | String (ISO code) | ~70 country codes | ISO 3166-1 alpha-2 country code of employee's residence |
| `remote_ratio` | Integer | 0, 50, 100 | Percentage of work done remotely: 0=Onsite, 50=Hybrid, 100=Remote |
| `company_location` | String (ISO code) | ~50 country codes | ISO country code of the company's primary location |
| `company_size` | String (categorical) | S, M, L | Company size: S=Small (<50), M=Medium (50–250), L=Large (>250) |
| `salary_in_usd` | Float | ~$5132–$450,000 | Annual gross salary in USD (**target variable**) |

### Preprocessing Applied

- Data preprocessing is performed using a `ColumnTransformer`, where categorical features are encoded using `OneHotEncoder` with `handle_unknown="ignore"` and numerical features are passed through without scaling.
- The model is trained using XGBoost, a tree-based gradient boosting algorithm that does not require feature scaling.
- The target variable (`salary_in_usd`) is clipped between the 1st and 99th percentiles to reduce the impact of extreme outliers.
- The clipped target is transformed using `log1p` during training.
- Predictions are converted back to original scale using `expm1()` during inference.
- Duplicate records are removed, and non-informative columns (e.g., `work_year`) are excluded before training.

### Engineered Features (Model 2)

Feature engineering is applied to the `job_title` field to extract structured information:

| Feature Name | Type | Description |
|---|---|---|
| `title_is_junior` | Integer (0/1) | 1 if job title indicates entry-level (e.g., intern, junior), else 0 |
| `title_is_senior` | Integer (0/1) | 1 if job title indicates senior-level (e.g., senior, lead, principal), else 0 |
| `title_is_exec` | Integer (0/1) | 1 if job title indicates executive roles (e.g., director, VP, chief), else 0 |
| `title_is_mgmt` | Integer (0/1) | 1 if job title indicates management responsibility, else 0 |
| `title_domain` | Categorical | Derived domain category (analytics, data_eng, scientist, ml_ai, other) |
| `exp_x_domain` | String (categorical) | Interaction feature combining experience level and job domain |

### Notes

- Job titles are normalized using regex-based text preprocessing before feature extraction.
- Keyword-based matching is used to derive seniority and domain indicators.

---

## 3. Association Rules Dataset — `association_rules.csv`

Precomputed from the Model 1 dataset after feature transformation and discretization (e.g., salary categories, experience categories) using the Apriori algorithm (MLxtend).

| Column Name | Data Type | Description |
|---|---|---|
| `antecedents` | String (set-like) | Input attribute combinations forming rule LHS |
| `consequents` | String (set-like) | Output attribute combinations forming rule RHS |
| `antecedent support` | Float | Frequency of antecedent occurrence |
| `consequent support` | Float | Frequency of consequent occurrence |
| `support` | Float | Joint frequency of antecedents and consequents |
| `confidence` | Float | Conditional probability of consequent given antecedent |
| `lift` | Float | Strength of association compared to independence |
| `representativity` | Float | Measure of how representative the rule is within the dataset |
| `leverage` | Float | Difference between observed and expected support |
| `conviction` | Float | Measure of implication strength |
| `zhangs_metric` | Float | Correlation-based metric for rule interestingness |
| `jaccard` | Float | Similarity between antecedent and consequent sets |
| `certainty` | Float | Certainty factor of the rule |
| `kulczynski` | Float | Average of forward and backward confidence |

---

## 4. Model Outputs

### Model 1 Output Fields

| Field Name | Type | Description |
|---|---|---|
| `predicted_salary` | Float | Annual gross salary prediction in USD |
| `monthly_salary` | Float | `predicted_salary / 12` |
| `weekly_salary` | Float | `predicted_salary / 52` |
| `hourly_salary` | Float | `predicted_salary / 2080` |
| `salary_level` | String | One of: `Early Career Range`, `Professional Range`, `Executive Range` |
| `career_stage` | String | One of: `Entry Stage`, `Growth Stage`, `Leadership Stage` |
| `confidence_lower` | Float | Lower bound of 95% confidence interval |
| `confidence_upper` | Float | Upper bound of 95% confidence interval |
| `pattern_insight` | String | Association rule-derived insight text |
| `negotiation_tips` | list[str] | List of salary negotiation tip strings |
| `recommendations` | list[str] | List of career recommendation strings |

### Model 2 Output Fields

| Field Name | Type | Description |
|---|---|---|
| `predicted_salary` | Float | Annual gross salary prediction in USD (expm1 of log-scale prediction) |
| `monthly_salary` | Float | `predicted_salary / 12` |
| `weekly_salary` | Float | `predicted_salary / 52` |
| `hourly_salary` | Float | `predicted_salary / 2080` |
| `negotiation_tips` | list[str] | List of negotiation tip strings |
| `recommendations` | list[str] | List of career recommendation strings |

---

## 5. Firestore Data Definitions

### `users/{username (email)}/`

| Field | Type | Description |
|---|---|---|
| `username` | String | User-chosen display name |
| `email` | String | User's email address (also the document ID) |
| `display_name` | String | Full name entered at registration |
| `created_at` | String (ISO UTC) | Account creation datetime, stored as `datetime.utcnow().isoformat()` |
| `auth_provider` | String | Always `"firebase"` for this application |

### `predictions/{username (email)}/records/{auto_id}/`

| Field | Type | Description |
|---|---|---|
| `model_used` | String | `"Model 1"` or `"Model 2"` |
| `input_data` | String (JSON) | All input fields used for the prediction, serialized via `json.dumps()` |
| `predicted_salary` | Float | Annual salary prediction in USD |
| `created_at` | String (ISO UTC) | Prediction datetime, stored as `datetime.utcnow().isoformat()` |

### `feedback/{auto_id}/`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `username` | String | No | Username or `"anonymous"` |
| `model_used` | String | No | `"Model 1"` or `"Model 2"` |
| `input_data` | Map / JSON String | No | Input features from the prediction |
| `predicted_salary` | Float | No | Predicted salary from the same prediction |
| `accuracy_rating` | String | No | `"Yes"`, `"Somewhat"`, or `"No"` |
| `direction` | String | No | `"Too High"`, `"About Right"`, or `"Too Low"` |
| `actual_salary` | Float | Yes | User-provided actual or expected salary in USD |
| `star_rating` | Integer | No | 1–5 |
| `created_at` | String (ISO UTC) | No | Submission datetime |
| `extended_data` | Map | Yes | Optional structured extended feedback (see below) |

### `feedback/{auto_id}/extended_data/` (Optional Nested Map)

| Field | Type | Description |
|---|---|---|
| `base_salary` | Float | Base salary component |
| `total_compensation` | Float | Total compensation including bonuses/equity |
| `bonus` | Float | Annual bonus amount |
| `equity` | String | Equity / RSU details (free text) |
| `skills` | list[str] | List of relevant skills |
| `certifications` | list[str] | Professional certifications |
| `industry` | String | Industry sector |
| `company_type` | String | Startup, MNC, Government, etc. |
| `team_size` | Integer | Size of immediate team |
| `direct_reports` | Integer | Number of direct reports |
| `tenure_months` | Integer | Months in current role |
| `weekly_hours` | Integer | Average working hours per week |
| `city_tier` | String | City tier classification (Tier 1/2/3) |
| `work_authorization` | String | Citizen, PR, Visa, etc. |
| `notes` | String | Free-text contextual notes (capped length) |
| `model2_missing_fields` | Map | For Model 2 feedback: captures Model 1 features (age, education, seniority, gender) |
| `model1_missing_fields` | Map | For Model 1 feedback: captures Model 2 features (employment type, remote ratio, company size, company location) |

---

## 6. Batch Input File Schema

### Model 1 Batch Input Columns

| Column Name | Type | Required | Accepted Values |
|---|---|---|---|
| `Age` | Integer | Yes | 18–65 |
| `Years of Experience` | Float | Yes | 0.0–40.0 |
| `Education Level` | Integer | Yes | 0, 1, 2, 3 |
| `Senior` | Integer | Yes | 0 or 1 |
| `Gender` | String | Yes | Male, Female, Other |
| `Job Title` | String | Yes | Any job title string |
| `Country` | String | Yes | Any country name string |

### Model 2 Batch Input Columns

| Column Name | Type | Required | Accepted Values |
|---|---|---|---|
| `experience_level` | String | Yes | EN, MI, SE, EX |
| `employment_type` | String | Yes | FT, PT, CT, FL |
| `job_title` | String | Yes | Any data science job title |
| `employee_residence` | String | Yes | ISO 3166-1 alpha-2 code |
| `remote_ratio` | Integer | Yes | 0, 50, 100 |
| `company_location` | String | Yes | ISO 3166-1 alpha-2 code |
| `company_size` | String | Yes | S, M, L |

---

## 7. Exchange Rate Cache Structure

Stored in `st.session_state.exchange_rates`:

```python
{
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.5,
    "JPY": 149.2,
    # ... 100+ currencies
}
```

Cached with a timestamp in `st.session_state.exchange_rates_time`. Refreshed if older than ~60 minutes.

---

## 8. Education Level Encoding

| Integer | Label | Description |
|---|---|---|
| 0 | High School | Secondary education, no degree |
| 1 | Bachelor's | Undergraduate degree (B.Tech, B.Sc, B.A, BCA, etc.) |
| 2 | Master's | Postgraduate degree (M.Tech, M.Sc, MBA, MS, etc.) |
| 3 | PhD | Doctoral degree |

---

## 9. Experience Level Encoding (Model 2)

| Code | Label | Typical Years of Experience |
|---|---|---|
| EN | Entry Level | 0–2 years |
| MI | Mid Level | 2–5 years |
| SE | Senior Level | 5–10 years |
| EX | Executive Level | 10+ years |

---

## 10. Salary Level Definitions (Model 1)

Produced by the `HistGradientBoostingClassifier` applied after regression.

| Label | Approximate Range | Description |
|---|---|---|
| Early Career Range | < $70,000/year | Entry to junior professional roles |
| Professional Range | $70,000–$130,000/year | Mid-level professional roles |
| Executive Range | > $130,000/year | Senior and executive leadership roles |

> Exact thresholds are derived from the training data distribution and may vary.

---

## 11. Career Stage Definitions (Model 1)

Produced by `KMeans (k=3)` clustering on salary and experience features, visualized using PCA.

| Label | Characteristics |
|---|---|
| Entry Stage | Lower experience, lower salary bracket, early career profile |
| Growth Stage | Mid-range experience, actively growing salary, mid-career |
| Leadership Stage | High experience, high salary, senior/leadership career profile |

---

*End of Data Dictionary*