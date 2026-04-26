# SalaryScope — User Guide
**Version:** 1.4.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Selecting a Model](#3-selecting-a-model)
4. [Manual Prediction](#4-manual-prediction)
5. [Resume Analysis](#5-resume-analysis)
6. [Batch Prediction](#6-batch-prediction)
7. [Scenario Analysis](#7-scenario-analysis)
8. [Model Analytics](#8-model-analytics)
9. [Data Insights](#9-data-insights)
10. [Model Hub](#10-model-hub)
11. [Financial Planning Tools](#11-financial-planning-tools)
12. [User Account and Profile](#12-user-account-and-profile)
13. [Providing Feedback](#13-providing-feedback)
14. [Admin Panel](#14-admin-panel)
15. [Exporting and Downloading Reports](#15-exporting-and-downloading-reports)
16. [Troubleshooting](#16-troubleshooting)
17. [Frequently Asked Questions](#17-frequently-asked-questions)
18. [Important Disclaimers](#18-important-disclaimers)

---

## 1. Introduction

SalaryScope is a web-based salary prediction tool that uses machine learning to estimate annual salaries based on your professional profile. It supports three ways to get a prediction:

- **Manual Prediction** — fill in a form with your details
- **Resume Analysis** — upload your PDF resume and let the system extract your details automatically
- **Batch Prediction** — upload a file with multiple records and get predictions for all of them at once

Beyond salary prediction, SalaryScope includes financial planning tools (tax estimation, cost-of-living comparison, savings potential, loan affordability, and more), a dedicated HR & Employer Tools tab for compensation planning, dataset exploration dashboards, model performance analytics, and a Model Hub where additional trained models can be accessed.

In the full app, an AI Assistant tab is also available for app help, prediction explanation, drafting tasks, negotiation wording, and cautious role or career guidance.

**Live applications:**
- Full App (all features including resume analysis, scenario analysis, Model Hub, and financial tools): https://salaryscope-app.streamlit.app/
- Lite App (Manual Prediction, Batch Prediction, Model Analytics, Data Insights, Profile): https://salaryscope-lite-app.streamlit.app/

---

## 2. Getting Started

### 2.1 Accessing the Application

Open either link above in a web browser. No installation is required. The application runs entirely in the browser.

### 2.2 Application Layout

The application has two main areas:

**Sidebar (left panel):**
- Model selector dropdown at the top
- Login / Register / Logout controls

**Tab area (main content):**
- A row of tabs across the top for navigating between features
- Content changes based on which tab is active and which model is selected

### 2.3 Creating an Account (Optional)

An account is not required to use most features. You can make predictions, use financial tools, and view analytics without logging in. Creating an account allows you to:

- Save your prediction history
- View your prediction timeline in the Profile tab
- Export your full prediction history
- Access the Model Hub
- Access the AI Assistant on Streamlit Cloud
- Change your password or manage your account

**To register:**
1. In the sidebar, click **Register**.
2. Enter a display name, email address, and password.
3. Your password must be at least 12 characters and include an uppercase letter, lowercase letter, digit, and special character.
4. Click **Register**.
5. A verification email will be sent to your address. Check your inbox (and spam folder) and click the verification link.
6. Return to the application and click **I have verified my email**, then sign in.

### 2.4 Logging In

1. In the sidebar, click **Login**.
2. Enter your registered email and password.
3. Click **Login**.

If you forget your password, click **Forgot Password**, enter your email, and follow the instructions in the reset email. The reset link expires after 1 hour.

Sessions expire after 24 hours and require re-login.

### 2.5 AI Assistant Access

- **Local development:** the AI Assistant can be used without login for testing.
- **Streamlit Cloud:** you must be logged in to use the AI Assistant.
- The assistant is grounded in SalaryScope context and is best used for:
  - app help
  - explanation of displayed results
  - negotiation drafts and talking points
  - recruiter-friendly resume or report wording
  - cautious job-title clarification or career suggestions

The AI Assistant can make mistakes. Always review important details before relying on them.

---

## 3. Selecting a Model

At the top of the sidebar, use the model selector dropdown to choose which model powers your predictions:

| Model | Best For |
|---|---|
| **Model 1 — General Salary (Random Forest)** | Any job role, broad range of countries |
| **Model 2 — Data Science Salary (XGBoost)** | Data science, ML, analytics, and data engineering roles |

The selected model applies to all tabs — Manual Prediction, Resume Analysis, Batch Prediction, Scenario Analysis, Model Analytics, and Data Insights — simultaneously. The Model Hub has its own independent model selector.

You can switch models at any time. Previous results in the current session will be cleared when you switch.

---

## 4. Manual Prediction

Manual prediction is the fastest way to get a salary estimate for a single set of inputs.

### 4.1 Model 1 Inputs

| Field | Description | Range |
|---|---|---|
| Age | Your age in years | 18 – 70 |
| Education Level | Highest degree attained | High School / Bachelor's / Master's / PhD |
| Gender | Self-reported gender | Male / Female / Other |
| Job Title | Your job title | Select from the dropdown list |
| Years of Experience | Total years of professional work experience | 0.0 – 40.0 |
| Senior Position | Whether your role is a senior position | Yes / No |
| Country | Country where the role is based | Select from the dropdown list |

If your country is not listed, select **Other**.

### 4.2 Model 2 Inputs

| Field | Description | Allowed Values |
|---|---|---|
| Experience Level | Career stage | Entry Level / Mid Level / Senior Level / Executive Level |
| Employment Type | Type of employment | Full Time / Part Time / Contract / Freelance |
| Job Title | Your data science or ML job title | Select from the dropdown list |
| Employee Residence | Your country of residence | Select from the dropdown list |
| Work Mode | On-site, hybrid, or remote | On-site / Hybrid / Fully Remote |
| Company Location | Country where the company is based | Select from the dropdown list |
| Company Size | Size of the company | Small / Medium / Large |

### 4.3 Running the Prediction

After filling in all fields, click **Predict Salary**. Results appear below the form.

**Validation:** If the age and years of experience combination is unrealistic (e.g. 20 years old with 15 years of experience), an error will be shown and you will need to correct the inputs before proceeding.

### 4.4 Reading the Results

**Predicted Annual Salary:** Displayed as a large figure in USD.

**Salary Breakdown:** Monthly, weekly, and hourly approximations calculated from the annual figure.

**Model 1 additional outputs:**
- **Salary Level:** Early Career / Professional / Executive Range.
- **Career Stage:** Entry / Growth / Leadership Stage (from KMeans clustering).
- **Pattern Insight:** An association rule observation linking your profile attributes to a salary category.
- **Confidence Interval:** An estimated likely salary range (95% approximation based on training residuals).

**Model 2 additional outputs:**
- **Smart Insights:** Domain classification (ML/AI, Data Engineering, Analytics, Data Science) and a market comparison (above or below average for your role and experience level in the dataset).

**Salary Negotiation Tips:** Three targeted tips based on your experience level, seniority, company size, and location.

**Career Recommendations:** A short list of actionable career development suggestions based on your job group and experience level.

---

## 5. Resume Analysis

Resume Analysis automatically extracts your professional details from a PDF resume and uses them as inputs for salary prediction.

> **Note:** Resume Analysis is available in the Full App only. It is not available in the Lite App.

### 5.1 Uploading Your Resume

1. Go to the **Resume Analysis** tab.
2. Choose the document type:
   - **Resume PDF** for salary prediction from a resume
   - **Offer Letter** for extracting compensation details from an offer document
3. For resume-based salary prediction, keep **Resume PDF** selected.
4. Click **Browse files** or drag and drop your PDF resume.
5. Only PDF format is supported.
6. Click **Extract Resume Features**.

The system will extract your job title, years of experience, education level, country, and detected technical skills from the resume text.

### 5.2 Reviewing Extracted Features

After extraction, a form appears showing the detected values. You can:

- Review what was detected for each field.
- Expand **View Extracted Resume Text** to see the raw text that was parsed.
- Edit any field where the detected value is incorrect before running the prediction.

This step is important because extraction accuracy depends on how clearly information is presented in the resume. If a value was not found, a sensible default is used.

### 5.3 Resume Score

A resume score (out of 100) is displayed with breakdowns for Experience, Education, and Skills. This is an indicative rating of how well the resume maps to the model's feature expectations and is not a hiring assessment.

| Range | Level |
|---|---|
| 0 – 34 | Basic |
| 35 – 64 | Moderate |
| 65 – 100 | Strong |

### 5.4 Running the Prediction

After reviewing and adjusting the extracted fields, click **Predict Salary from Resume**. The prediction pipeline is the same as manual prediction, using the extracted (and optionally edited) values as inputs.

### 5.5 Tips for Better Extraction

- Use a plain, well-structured PDF resume (avoid heavy tables, columns, or image-based layouts).
- State your years of experience explicitly (e.g. "5 years of experience in data engineering").
- Include your degree title clearly (e.g. "Bachelor of Engineering", "Master of Science").
- List technical skills in a dedicated skills section.
- Include your country or city name somewhere in the document.

---

## 6. Batch Prediction

Batch Prediction allows you to run salary predictions for many records at once by uploading a file.

### 6.1 Supported File Formats

- CSV (.csv)
- Excel (.xlsx)
- JSON (.json)
- SQL dump (.sql)
- Public Google Drive sharing link

### 6.2 Required Column Format

Download the sample file from the left column of the Batch Prediction tab to see the exact required format. The column names must match exactly (case-sensitive).

**Model 1 required columns:**

| Column | Type | Allowed Values |
|---|---|---|
| Age | Integer | 18 – 70 |
| Years of Experience | Float | 0.0 – 40.0 |
| Education Level | Integer | 0, 1, 2, 3 |
| Senior | Integer | 0 or 1 |
| Gender | Text | Male, Female, Other |
| Job Title | Text | Supported titles only |
| Country | Text | Supported countries only |

**Model 2 required columns:**

| Column | Type | Allowed Values |
|---|---|---|
| experience\_level | Text | EN, MI, SE, EX |
| employment\_type | Text | FT, PT, CT, FL |
| job\_title | Text | Supported DS/ML titles only |
| employee\_residence | Text | ISO-2 country code |
| remote\_ratio | Integer | 0, 50, 100 |
| company\_location | Text | ISO-2 country code |
| company\_size | Text | S, M, L |

Extra columns in your file are ignored. Maximum file size is 50,000 rows.

### 6.3 Uploading via Google Drive

1. Upload your file to Google Drive.
2. Set sharing to **Anyone with the link can view**.
3. Copy the sharing link.
4. Paste it into the Google Drive link field in the Batch Prediction tab.
5. Select the correct file format from the dropdown.

### 6.4 Running Batch Predictions

After uploading your file, click **Run Batch Prediction**. A progress indicator shows while predictions are being computed.

### 6.5 Batch Analytics

After prediction, an analytics dashboard appears below the results with:

- **Summary Metrics:** Total records, average, minimum, maximum, and standard deviation of predicted salaries.
- **Salary Leaderboard:** Job roles ranked by average predicted salary. Top 3 roles are highlighted with medals.
- **Salary Distribution:** Histogram of predicted salaries.
- **Breakdowns by:** Experience level, company size, work mode, and country.

### 6.6 Exporting Results

Use the export dropdown to choose CSV, XLSX, JSON, or SQL format, then click the download button to save the results file containing all input columns plus predicted salary.

---

## 7. Scenario Analysis

Scenario Analysis lets you compare multiple salary predictions side by side by building named scenarios with different inputs.

### 7.1 Building Scenarios

1. Go to the **Scenario Analysis** tab.
2. A first scenario is pre-filled with default values. Rename it and adjust the inputs.
3. Click **Add Scenario** to add more scenarios (up to 5).
4. Each scenario can have a custom name and completely independent input values.
5. To remove a scenario, click **Remove** on its card.

### 7.2 Running All Scenarios

Click **Run All Scenarios** to compute predictions for every scenario simultaneously. Results appear in a comparison table and salary chart.

### 7.3 Reading the Results

- **Comparison table:** Shows each scenario's inputs and predicted salary side by side.
- **Salary chart:** Bar or grouped bar chart comparing predicted salaries across all scenarios.
- **Model 1 additional columns:** Salary level and career stage per scenario.

### 7.4 Sensitivity Sweep

The Sensitivity Sweep section simulates how salary changes when you vary one parameter while keeping everything else fixed for a selected baseline scenario:

- **Model 1:** Sweep across Education Levels or Years of Experience.
- **Model 2:** Sweep across Experience Levels or Company Sizes.

Select a baseline scenario from the dropdown, and the sweep chart will show the salary trajectory.

### 7.5 Exporting Scenario Results

Use the export dropdown to save scenario results in CSV, XLSX, or JSON format. A PDF report is also available via the Prepare PDF Report button.

---

## 8. Model Analytics

The Model Analytics tab provides detailed information about the performance and internals of the currently selected model.

### 8.1 Model 1 (Random Forest) Analytics Sections

**Salary Regression Model:**
- Test R², Cross-Validation R², MAE, RMSE.
- Model comparison table and radar chart across candidate models (Random Forest highlighted as the selected model).
- Tuned hyperparameters from GridSearchCV.
- Feature importance chart and cumulative importance.
- Residual diagnostics: predicted vs actual scatter, residual distribution.

**Salary Level Classifier:**
- Accuracy, confusion matrix, classification report.
- Comparison across candidate classifiers.

**Career Stage Clustering:**
- Silhouette score, Davies-Bouldin score.
- PCA visualisation of clusters.
- Cluster centre characteristics.

**Association Rule Mining:**
- Support, confidence, and lift metrics.
- Top rules linking career attributes to salary categories.

**Resume NLP Module:**
- Processing pipeline overview table.
- Pipeline flow diagram (PDF → features).
- Design rationale and limitations.

### 8.2 Model 2 (XGBoost) Analytics Sections

- Test R², Cross-Validation R², MAE, RMSE.
- Model comparison table and radar chart.
- Residual diagnostics and uncertainty distribution.
- Grouped feature importance (by feature category).
- SHAP analysis: top-15 features by mean absolute SHAP value.
- Resume NLP module (same as Model 1 section).

### 8.3 Downloading the Analytics Report

A **Download Model Analytics Report (PDF)** button is available at the bottom of the tab. This PDF contains all the metrics and charts for the current model.

---

## 9. Data Insights

The Data Insights tab lets you explore the training dataset for the currently selected model through interactive dashboards.

### 9.1 Dashboard Structure

Each model has three dashboards, accessible as collapsible sections:

**Model 1 Dashboards:**
- Dashboard 1 — Salary Landscape: overall salary distribution, seniority and education breakdowns.
- Dashboard 2 — Human Capital Dimensions: age, experience, gender, and education relationships.
- Dashboard 3 — Geographic and Role Patterns: salary by country, job title, and job group.

**Model 2 Dashboards:**
- Dashboard 1 — Salary Distribution: overall shape, experience level, and employment type.
- Dashboard 2 — Work Mode and Company: remote ratio, company size, and work mode interactions.
- Dashboard 3 — Job Roles and Geography: top data science roles and top countries by salary.

### 9.2 Using Filters

Each dashboard has independent filter controls at the top (education level, seniority, experience level, salary cap, etc.). Changing a filter updates only that dashboard's charts.

### 9.3 KPI Tiles

Each dashboard shows key statistics (record count, median salary, mean salary, etc.) for the current filtered view.

---

## 10. Model Hub

The Model Hub allows you to run predictions using additional models uploaded by the admin, beyond the two built-in models.

### 10.1 Accessing the Model Hub

The Model Hub requires you to be **logged in**. Sign in from the sidebar before navigating to this tab.

### 10.2 Running a Prediction

1. Go to the **Model Hub** tab.
2. From the dropdown, select one of the available models. Only admin-approved, active models appear here.
3. Review the model information shown (number of input fields, number of features).
4. Click **Load Model** to download the model bundle. This only needs to be done once per session.
5. Fill in the input form that appears. Fields are generated automatically from the model's schema. Dropdown fields show human-readable labels (e.g. "Junior (0-4 years)", "Oncology") even when the underlying model uses short codes — this is handled automatically.
6. Click **Predict**.

The predicted value is displayed with the target variable name as defined by the model's creator. If currency conversion is available, a currency toggle appears below the result so you can view the prediction in your local currency.

### 10.3 Admin Features

If you are the admin user, additional sections appear below the prediction panel:

**Upload Bundle:** Upload a new model by providing model.pkl, columns.pkl, schema.json, a display name, a description, and the target variable name. An optional `aliases.json` file can also be uploaded to provide human-readable display labels for dropdown fields. The system validates all files before uploading.

**Registry Manager:** Activate or deactivate models to control which ones appear in the user dropdown. Roll back to a previous version within a model family.

**Schema Editor:** Build a schema.json file interactively using a field-by-field form, or upload an existing schema.json to validate it and preview how the input form will look.

---

## 11. Financial Planning Tools

After a prediction is shown in the Manual Prediction tab, a series of optional financial tools appear below the salary display. Each tool is a toggle — enable it to expand the tool, disable it to collapse it.

All tools are approximate estimates for planning purposes only. They are not financial advice.

### 11.1 Currency Converter

Shows the predicted salary converted to a currency of your choice. Live exchange rates are fetched from open.er-api.com (updated daily, no API key required). Over 100 currencies are supported.

The default currency is auto-detected from your work country when possible.

### 11.2 Tax Adjuster

Estimates post-tax take-home salary based on country-level progressive tax brackets (combined income tax + major social contributions). You can override the rate with a custom effective rate using the slider.

The post-tax figure is also shown in your selected currency if currency conversion is enabled.

### 11.3 Cost-of-Living Adjuster

Shows how much salary you would need in a different country to maintain the same purchasing power, using country-level CoL indices (US = 100 baseline).

Select a comparison country from the dropdown to see the PPP-equivalent salary. You can override the CoL index for either country using the slider.

### 11.4 CTC Breakdown

Breaks down your gross annual salary into estimated CTC components: Base Salary, HRA (if applicable), Bonus, PF/Pension, Gratuity, and Other Allowances. Component fractions are based on typical employer practices in your country.

### 11.5 Take-Home Salary Estimator

Estimates your monthly and annual net in-hand salary after income tax, PF/pension contributions, and other statutory deductions. Uses the tax brackets from the Tax Adjuster module when available.

### 11.6 Savings Potential

Estimates how much you can save each month based on typical household expense ratios for your country. Shows monthly savings, annual savings, expense ratio, and savings rate.

### 11.7 Loan Affordability

Estimates the maximum loan you can service based on your monthly net income, country-typical interest rates, and standard lender EMI-cap norms (typically 40–50% of net income). You can adjust the interest rate, loan tenure, and EMI cap using sliders.

### 11.8 Budget Planner

Breaks down your monthly net income into recommended spending categories: Housing, Food, Transport, Healthcare, Savings/Investments, Entertainment, and Miscellaneous. Based on the 50/30/20 envelope budgeting approach adapted for your country.

### 11.9 Investment Growth Estimator

Projects the future value of your estimated monthly savings under compound growth, using country-adjusted blended investment return benchmarks. Shows projections at 5, 10, 20, and 30 years.

This is a purely illustrative projection. Actual returns depend on market conditions, instrument choice, fees, and timing.

### 11.10 Emergency Fund Planner

Estimates how large an emergency fund you should build (3–6 months of expenses, adjusted for country job-market stability) and how many months it would take to build it at your current savings rate.

### 11.11 Lifestyle Budget Split

Takes your discretionary income (net minus essentials) and splits it across lifestyle tiers (Basic, Comfortable, Premium) and spending categories (dining, entertainment, travel, fitness, subscriptions, personal care, hobbies).

---

## 11A. HR & Employer Tools

The Full App includes a dedicated **HR & Employer Tools** tab for compensation planning. These tools use the currently selected built-in model as their salary reference engine and are intended for hiring managers, recruiters, and compensation teams.

### 11A.1 Hiring Budget

Estimate total annual payroll cost for an open role by combining the model salary estimate with headcount, benefits percentage, overhead percentage, and one-time recruiting cost assumptions.

### 11A.2 Salary Benchmarking

Generate a benchmarking grid across experience levels for a selected role and location. The resulting table supports editable HR Override, Band Min, Band Max, and Internal Notes columns before export.

### 11A.3 Candidate Comparison

Compare expected salaries for 2 to 5 candidates side by side using the same model and location assumptions. Each candidate can optionally use an internal override instead of the model estimate.

### 11A.4 Offer Checker

Compare a planned offer against the model estimate and view whether the offer falls below, near, or above the predicted range.

### 11A.5 Team Audit

Upload a CSV of current team salaries to compare them with model-derived reference salaries in batch. The audit highlights potentially underpaid and overpaid records using configurable thresholds and supports a global model adjustment percentage.

All HR tools support CSV export, and the tools that show a single-row estimate also support a manual HR override workflow.

---

## 12. User Account and Profile

### 12.1 Profile Tab

The Profile tab (visible only when logged in) shows:

- **Prediction Summary:** Total number of predictions made, average predicted salary, and most recent prediction.
- **Prediction History Chart:** Scatter plot of all predictions over time, colour-coded by model type.
- **Prediction History Table:** Tabular view of the most recent 500 predictions.
- **View Prediction Inputs:** Select any prediction to see the exact input values that were used.
- **Export Prediction History:** Download your full history in CSV, XLSX, or JSON format.

### 12.2 Account Management

Below the prediction history, an Account Management section provides:

**Change Password:**
1. Enter your current password.
2. Enter and confirm your new password (must meet the password policy).
3. Click **Change Password**.

**Delete Account:**
1. Click to expand the Delete Account section.
2. Enter your current password.
3. Type exactly `delete my account` in the confirmation field.
4. Click **Permanently Delete My Account**.

Account deletion removes your login credentials immediately. Your prediction history is retained in anonymised form for dataset purposes.

### 12.3 Logging Out

Click the **Logout** button at the bottom of the Profile tab, or use the logout button in the sidebar.

---

## 13. Providing Feedback

After every salary prediction, a **Share Feedback on This Prediction** section appears at the bottom of the results (in a collapsed expander). Feedback is optional and does not require login.

### 13.1 Basic Feedback

| Field | Required | Description |
|---|---|---|
| Was the prediction accurate? | Yes | Yes / Somewhat / No |
| How did it compare to reality? | Yes | Too High / About Right / Too Low |
| Overall rating | Yes | 1–5 stars |
| Your actual / expected salary (USD) | No | Leave at 0 to skip |

### 13.2 Extended Feedback (Optional)

An expandable section allows you to provide additional detail that helps build a richer dataset for future model improvements:

- Compensation structure (base, bonus, equity)
- Skills and certifications
- Industry and company context
- Role details (team size, direct reports, tenure)
- Work conditions (hours, city tier, visa status)
- Free-text context (up to 300 characters)

### 13.3 Submitting Feedback

Click **Submit Feedback**. A success message confirms the submission. Feedback is stored anonymously if you are not logged in.

---

## 14. Admin Panel

The Admin Panel tab is visible only to the admin user (the account whose email matches the `ADMIN_EMAIL` secret).

### 14.1 System Diagnostics

Displays runtime information: Python version, OS, architecture, deployment environment (Local or Streamlit Cloud), active model context, RAM usage, and registered user count.

### 14.2 Feedback Analytics

Click **Load Feedback Analytics** to fetch aggregated feedback statistics from Firestore:
- Total feedback submissions.
- Accuracy breakdown (% Yes / Somewhat / No).
- Prediction direction breakdown (Too High / About Right / Too Low).
- Average star rating.
- Median actual salary reported by users.
- Feedback count per model (pie and bar charts).

Click **Show Recent Feedback** to view the 5 most recent individual submissions.

### 14.3 Memory and Cache

- **RAM Usage:** Current process memory consumption.
- **Run Garbage Collection:** Forces Python garbage collection and shows memory before/after.
- **Clear Cache:** Clears all `@st.cache_data` caches (forces fresh data loading on next rerun).

### 14.4 Session State Inspector

Shows counts of total session keys and key counts grouped by category (admin, scenario, bulk, resume). An option to display all session keys is available (use with caution for large sessions).

---

## 15. Exporting and Downloading Reports

### 15.1 PDF Reports

Available in the following tabs:

| Tab | Report Contents |
|---|---|
| Manual Prediction | Input summary, predicted salary, salary breakdown, insights |
| Resume Analysis | Resume score, extracted features, predicted salary, recommendations |
| Batch Prediction | Summary metrics, leaderboard, distribution charts |
| Scenario Analysis | Scenario comparison table, charts, sensitivity sweeps |
| Model Analytics | Full model performance report (available immediately) |

**How to download a PDF:**
1. Click **Prepare PDF Report** to generate the report.
2. A success message and a **Download** button will appear.
3. Click **Download** to save the file.

Note: If you navigate away and return, you may need to re-generate the PDF.

### 15.2 Data Exports

| Tab | Formats | Content |
|---|---|---|
| Batch Prediction | CSV, XLSX, JSON | All input columns + predicted salaries |
| Scenario Analysis | CSV, XLSX, JSON | Scenario inputs + predicted salaries |
| Profile | CSV, XLSX, JSON | Full prediction history |

---

## 16. Troubleshooting

**The application is slow or not loading.**
Streamlit Cloud free tier has resource limits. Large datasets or heavy computations may take longer. Wait a moment and try again. If the app is asleep due to inactivity, it may take 30–60 seconds to wake up.

**Resume extraction produced incorrect values.**
The NLP extraction depends on text clarity in the PDF. Heavily formatted, multi-column, or image-based resumes are harder to parse. Use the editable form after extraction to correct any incorrect values before running the prediction.

**My country is not in the list.**
Select **Other** for Model 1 country inputs. For Model 2, use the closest ISO-2 country code available. The financial tools will use a generic estimate for unsupported countries.

**The verification email did not arrive.**
Check your spam or junk folder. Firebase verification emails are sometimes filtered there. Click **Resend verification email** in the application if needed. The verification link expires after 24 hours.

**I cannot log in after registering.**
Ensure you have clicked the verification link in your email. Without email verification, login will prompt you to verify first.

**The currency converter shows "No data available".**
The live exchange rate API (open.er-api.com) could not be reached. Check your internet connection. A fallback to a local rates file will be used if available.

**Batch prediction is very slow.**
Files above 10,000 rows will be noticeably slower. Ensure your file format is correct and no validation errors are present. Consider splitting very large files into smaller batches.

**The Model Hub says "Could not load model registry".**
This indicates a configuration issue with the HuggingFace repository secrets. Contact the admin.

**The AI Assistant is unavailable or not responding on Streamlit Cloud.**
If you are not logged in, sign in first. Cloud AI chat is disabled for anonymous users. If you are already logged in, the Hugging Face Space backend may be asleep, cold-starting, or temporarily unavailable.

---

## 17. Frequently Asked Questions

**Is my data stored anywhere?**
Prediction inputs and results are stored in Firestore if you are logged in. Feedback is stored in Firestore regardless of login status, but anonymous feedback contains no personal identifiers. Resume text is processed in memory and not stored anywhere.

**Do I need an account to use the application?**
No. Manual prediction, batch prediction, scenario analysis, model analytics, and data insights are all available without an account. An account is required for the Model Hub, for prediction history in the Profile tab, and for the AI Assistant on Streamlit Cloud.

**How accurate are the salary predictions?**
Predictions are estimates based on patterns in publicly available historical datasets. They may not reflect current market conditions, company-specific salaries, or regional cost variations. Use predictions as a general reference, not as exact figures. See Section 18 for full disclaimers.

**What is the difference between the Full App and the Lite App?**
The Lite App is a substantially reduced version of the Full App. It includes Manual Prediction, Batch Prediction, Model Analytics, Data Insights, Profile, and About. It does not include Resume Analysis, Scenario Analysis, Model Hub, Admin Panel, HR Tools, or any of the 11 financial planning tools (currency converter, tax estimator, CoL adjuster, etc.). The split exists to keep the Lite App within Streamlit Cloud free-tier memory limits. Both apps share the same Firebase project so prediction history is shared across them.

**Can I use the Model Hub to deploy my own models?**
Yes, if you are the admin. You need to train an sklearn-compatible or ONNX-compatible model, prepare the matching columns list, define a `schema.json` file, and optionally attach `aliases.json`, `skills.json`, `job_titles.json`, or `resume_config.json`. Upload the bundle through the Model Hub admin interface.

**Why is the confidence interval only shown for Model 1?**
Model 1 uses a Random Forest Regressor, and the confidence interval is estimated from the standard deviation of training residuals. Model 2 uses XGBoost with a log-transformed target; the back-transformation makes residual-based interval estimation less straightforward, so it is not shown.

**How often is the currency data updated?**
Exchange rates are fetched from open.er-api.com once per 60 minutes (cached in memory). The provider updates rates daily.

---

## 18. Important Disclaimers

- Salary predictions are based on publicly available historical datasets and may not reflect current real-world salary trends or company-specific compensation.
- Predictions do not account for real-time market conditions, economic changes, or negotiation outcomes.
- Resume analysis uses NLP-based extraction which may not accurately handle all resume formats. Always review extracted values before accepting predictions.
- Tax estimation uses approximate effective rates and does not model detailed national tax rules, deductions, filing status, or local regulations.
- Cost-of-living adjustments are based on country-level indices and may not represent city-level variations or individual lifestyle differences.
- Currency conversion uses publicly available exchange rates and may not reflect real-time market rates or transaction fees.
- Financial tools (savings, loans, investments, emergency funds, lifestyle) are illustrative benchmarks for a typical middle-income urban household. Individual circumstances vary significantly. These tools are not financial advice.
- Investment projections are entirely illustrative. Actual returns depend on market conditions, fees, taxes, and timing. Past performance does not guarantee future results.
- Model Hub predictions are only as reliable as the model and dataset used during training. The system does not validate model quality.
- Model Hub bundles use joblib (pickle) serialisation. Only upload bundles from sources you control entirely.

---

*End of User Guide*
