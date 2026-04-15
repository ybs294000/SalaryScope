# SalaryScope — Testing Guide
**Version:** 1.1.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Author:** Yash Shah  
**Document Type:** Testing Guide and Test Plan

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Test Categories](#3-test-categories)
4. [Module 1 — Authentication and Account Management](#4-module-1--authentication-and-account-management)
5. [Module 2 — Manual Prediction](#5-module-2--manual-prediction)
6. [Module 3 — Resume Analysis](#6-module-3--resume-analysis)
7. [Module 4 — Batch Prediction](#7-module-4--batch-prediction)
8. [Module 5 — Scenario Analysis](#8-module-5--scenario-analysis)
9. [Module 9 — Financial Tools](#9-module-9--financial-tools)
10. [Module 6 — Model Analytics](#10-module-6--model-analytics)
11. [Module 7 — Data Insights](#11-module-7--data-insights)
12. [Module 8 — Model Hub](#12-module-8--model-hub)
13. [Module 10 — Feedback System](#13-module-10--feedback-system)
14. [Module 11 — User Profile](#14-module-11--user-profile)
15. [Module 12 — Admin Panel](#15-module-12--admin-panel)
16. [Module 13 — PDF Reports](#16-module-13--pdf-reports)
17. [Core Unit Tests — Password Policy](#17-core-unit-tests--password-policy)
18. [Core Unit Tests — Rate Limiter](#18-core-unit-tests--rate-limiter)
19. [Core Unit Tests — Resume NLP Pipeline](#19-core-unit-tests--resume-nlp-pipeline)
20. [Core Unit Tests — Financial Utility Functions](#20-core-unit-tests--financial-utility-functions)
21. [Core Unit Tests — Insights Engine](#21-core-unit-tests--insights-engine)
22. [Core Unit Tests — Model Hub Validator](#22-core-unit-tests--model-hub-validator)
23. [Integration Tests](#23-integration-tests)
24. [Security Tests](#24-security-tests)
25. [Performance Tests](#25-performance-tests)
26. [Test Results Log Template](#26-test-results-log-template)

---

## 1. Introduction

### 1.1 Purpose

This document defines a structured test plan for SalaryScope v1.1.0. It covers manual functional tests for every feature of the application, unit tests for all pure-Python modules (which have no Streamlit dependency and can be run programmatically), integration tests for cross-module workflows, security tests for the authentication and rate limiting systems, and performance benchmarks.

### 1.2 Test Strategy

SalaryScope uses a hybrid testing approach:

- **Manual UI tests** — executed directly in the browser against the running application. These cover all Streamlit tab functionality, form interactions, and visual output.
- **Programmatic unit tests** — executed using Python's built-in `unittest` module against pure-Python functions (those without `import streamlit`). These cover password policy, rate limiter logic, NLP extraction functions, financial utility `compute_*()` functions, insights engine functions, and Model Hub validator.
- **Integration tests** — executed manually or via script, verifying multi-module workflows such as the full prediction pipeline and the Firestore read/write cycle.
- **Security tests** — targeted manual tests of authentication hardening, rate limiting, and Model Hub access controls.
- **Performance tests** — timing benchmarks for prediction, batch processing, and PDF generation.

### 1.3 Test Notation

Each test case uses the following fields:

- **ID** — unique identifier (e.g. `AUTH-001`)
- **Description** — what is being tested
- **Precondition** — state required before the test
- **Steps** — numbered actions to perform
- **Expected Result** — what should happen
- **Pass/Fail** — to be filled in during execution
- **Notes** — observations

### 1.4 Scope Boundary

The following are out of scope for this test plan:
- Load testing with concurrent users (Streamlit Cloud process isolation makes this difficult to test locally)
- Cross-browser compatibility beyond Chrome, Firefox, and Edge
- Mobile browser layout testing
- Firebase infrastructure reliability (treated as a dependency, not tested here)

---

## 2. Test Environment Setup

### 2.1 Local Environment

```bash
# Clone and install
git clone https://github.com/your-username/salaryscope.git
cd salaryscope
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Configure secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Fill in real values for FIREBASE_API_KEY, FIREBASE_SERVICE_ACCOUNT,
# ADMIN_EMAIL, HF_TOKEN, HF_REPO_ID, IS_LOCAL=true

# Run the app
streamlit run app_resume.py
```

### 2.2 Test Data Requirements

Before beginning tests, prepare the following:

| Item | Description |
|---|---|
| Test account (regular) | A registered and email-verified Firebase account that is NOT the admin email |
| Test account (admin) | The account whose email matches `ADMIN_EMAIL` in secrets |
| Sample CSV (App 1) | A valid CSV file with App 1 required columns and 10 rows of valid data |
| Sample CSV (App 2) | A valid CSV file with App 2 required columns and 10 rows of valid data |
| Invalid CSV | A CSV file with missing or incorrectly named columns |
| Sample PDF resume | A plain-text PDF resume with clearly stated job title, experience, education, and skills |
| Large CSV | A valid CSV with 1,000+ rows for performance testing |
| Model Hub bundle | `model.pkl`, `columns.pkl`, `schema.json` prepared from a simple trained sklearn model |
| Broken PDF | A PDF that contains images only (no extractable text) |

### 2.3 Running Unit Tests

```bash
# Run all unit tests from the project root
python -m pytest tests/ -v

# Run a specific module's tests
python -m pytest tests/test_password_policy.py -v
python -m pytest tests/test_financial_utils.py -v
python -m pytest tests/test_resume_analysis.py -v
python -m pytest tests/test_validator.py -v
python -m pytest tests/test_insights_engine.py -v
```

If a `tests/` directory does not yet exist, the unit test cases in Sections 17–22 provide the complete test code to populate it.

---

## 3. Test Categories

| Category | ID Prefix | Execution Method |
|---|---|---|
| Authentication | AUTH | Manual (browser) |
| Manual Prediction | PRED | Manual (browser) |
| Resume Analysis | RESM | Manual (browser) |
| Batch Prediction | BTCH | Manual (browser) |
| Scenario Analysis | SCEN | Manual (browser) |
| Financial Tools | FINT | Manual (browser) |
| Model Analytics | MANA | Manual (browser) |
| Data Insights | DATA | Manual (browser) |
| Model Hub | MHUB | Manual (browser) |
| Feedback System | FEED | Manual (browser) |
| User Profile | PROF | Manual (browser) |
| Admin Panel | ADMN | Manual (browser) |
| PDF Reports | PDF | Manual (browser) |
| Password Policy | UNIT-PP | Programmatic (pytest) |
| Rate Limiter | UNIT-RL | Programmatic (pytest) |
| Resume NLP | UNIT-NLP | Programmatic (pytest) |
| Financial Utils | UNIT-FIN | Programmatic (pytest) |
| Insights Engine | UNIT-INS | Programmatic (pytest) |
| Model Hub Validator | UNIT-VAL | Programmatic (pytest) |
| Integration | INT | Manual or script |
| Security | SEC | Manual (browser + script) |
| Performance | PERF | Manual with timing |

---

## 4. Module 1 — Authentication and Account Management

### AUTH-001 — Registration with Valid Inputs

**Precondition:** User is not logged in. Email is not already registered in Firebase.

**Steps:**
1. Click **Register** in the sidebar.
2. Enter a display name (e.g. "Test User").
3. Enter a valid, unregistered email address.
4. Enter a password meeting all policy requirements (e.g. `TestPass#12`).
5. Confirm the password.
6. Click **Register**.

**Expected Result:** A success/info message states that a verification email has been sent. The pending verification UI appears with "I have verified my email" and "Resend verification email" buttons.

---

### AUTH-002 — Password Policy Enforcement on Registration

**Precondition:** Registration form is open.

**Steps:**
1. Enter a display name and valid email.
2. Enter each of the following passwords in turn, clicking Register after each:
   - `short` (too short)
   - `alllowercase1!` (no uppercase)
   - `ALLUPPERCASE1!` (no lowercase)
   - `NoDigitHere!!!` (no digit)
   - `NoSpecial123` (no special character)
   - `HasSpaceBefore 1!` (trailing space — prepend a space)
   - `Aaa111!!!Pass` (three identical consecutive chars "aaa")
   - `password123!A` (common password)

**Expected Result:** Each attempt displays a specific, human-readable error message matching the violated rule. No Firebase account is created. The form remains open.

---

### AUTH-003 — Registration with Existing Email

**Precondition:** The test email is already registered in Firebase.

**Steps:**
1. Attempt to register with an already-registered email and a valid password.

**Expected Result:** An error message "An account with this email already exists." is displayed. No duplicate account is created.

---

### AUTH-004 — Email Verification Flow

**Precondition:** Account created via AUTH-001. Verification email received in inbox.

**Steps:**
1. Click the verification link in the email.
2. Return to the application.
3. Click **I have verified my email**.

**Expected Result:** A success message confirms verification. The pending verification UI clears. The user is prompted to log in.

---

### AUTH-005 — Login with Verified Account

**Precondition:** Account is registered and email-verified.

**Steps:**
1. Click **Login** in the sidebar.
2. Enter the correct email and password.
3. Click **Login**.

**Expected Result:** Login succeeds. The sidebar shows the logged-in state. The Profile tab appears in the tab bar.

---

### AUTH-006 — Login with Wrong Password

**Steps:**
1. Attempt to log in with a correct email but wrong password.

**Expected Result:** Error message "Incorrect password." or "Incorrect email or password." is displayed. Session is not created.

---

### AUTH-007 — Login Rate Limiting

**Precondition:** User is not logged in.

**Steps:**
1. Attempt to log in with a correct email but wrong password 5 times in quick succession.
2. Attempt a 6th login.

**Expected Result:** After 5 failures, the 6th attempt is blocked with a message like "Too many failed attempts. Please wait 1 minute before trying again." The wait period is approximately 5 minutes.

---

### AUTH-008 — Login with Unverified Account

**Precondition:** Account registered but verification email not yet clicked.

**Steps:**
1. Attempt to log in with the unverified account's credentials.

**Expected Result:** The pending verification UI is displayed rather than granting login. The user is prompted to check their inbox.

---

### AUTH-009 — Forgot Password Flow

**Steps:**
1. Click **Forgot Password** in the sidebar.
2. Enter the registered email address.
3. Click **Send Password Reset Email**.

**Expected Result:** A success message is displayed regardless of whether the email exists (account enumeration protection). A password reset email arrives in the inbox. Clicking the link in the email allows setting a new password.

---

### AUTH-010 — Forgot Password — Non-existent Email

**Steps:**
1. Click **Forgot Password**.
2. Enter an email address not registered in Firebase.
3. Click **Send Password Reset Email**.

**Expected Result:** The same generic success message is displayed as in AUTH-009. No error reveals whether the email exists.

---

### AUTH-011 — Session Expiry

**Precondition:** User is logged in.

**Steps:**
1. Manually set `st.session_state._session_expiry` to a datetime in the past (via a temporary debug UI or directly via Python console if testing locally).
2. Trigger a Streamlit rerun (e.g. click any button).

**Expected Result:** The session is detected as expired. The user is automatically logged out. The sidebar shows the logged-out state.

---

### AUTH-012 — Logout

**Precondition:** User is logged in.

**Steps:**
1. Click the **Logout** button in the Profile tab (or sidebar if present).

**Expected Result:** The session is destroyed. The sidebar shows the logged-out state. The Profile tab disappears from the tab bar.

---

### AUTH-013 — Change Password

**Precondition:** User is logged in.

**Steps:**
1. Go to the Profile tab.
2. In Account Management, expand **Change Password**.
3. Enter the correct current password.
4. Enter a new valid password (e.g. `NewPass#456`).
5. Confirm the new password.
6. Click **Change Password**.

**Expected Result:** A success message confirms the password was changed. The new password works on next login. The session remains active.

---

### AUTH-014 — Change Password — Wrong Current Password

**Steps:**
1. Attempt to change password entering an incorrect current password.

**Expected Result:** An error "Incorrect password." is shown. The password is not changed.

---

### AUTH-015 — Delete Account

**Precondition:** User is logged in.

**Steps:**
1. Go to the Profile tab.
2. In Account Management, expand **Delete Account**.
3. Read the warning.
4. Enter the correct current password.
5. Type `delete my account` in the confirmation field.
6. Click **Permanently Delete My Account**.

**Expected Result:** Account is deleted. User is logged out. A success message is shown on the next render. Attempting to log in with the deleted credentials fails.

---

### AUTH-016 — Delete Account — Wrong Confirmation Phrase

**Steps:**
1. Open the Delete Account expander.
2. Enter the correct password.
3. Type a phrase that does not exactly match `delete my account` (e.g. "Delete My Account" with capitals, or "delete account").
4. Click the delete button.

**Expected Result:** An error message states the exact phrase must be typed. The account is not deleted.

---

## 5. Module 2 — Manual Prediction

### PRED-001 — Model 1 Manual Prediction (Happy Path)

**Precondition:** App loaded, Model 1 selected.

**Steps:**
1. Navigate to Manual Prediction tab.
2. Set Age = 30, Education = Bachelor's, Gender = Male, Job Title = Software Engineer, Years of Experience = 5, Senior = No, Country = USA.
3. Click **Predict Salary**.

**Expected Result:** A predicted annual salary in USD is displayed. Monthly, weekly, and hourly breakdowns appear. Salary band (e.g. "Professional Range"), career stage (e.g. "Growth Stage"), association pattern insight, confidence interval, negotiation tips, and career recommendations are all visible.

---

### PRED-002 — Model 2 Manual Prediction (Happy Path)

**Precondition:** App loaded, Model 2 selected.

**Steps:**
1. Set Experience Level = Senior Level, Employment Type = Full Time, Job Title = Data Scientist, Employee Residence = United States (US), Work Mode = Fully Remote, Company Location = United States (US), Company Size = Large Company.
2. Click **Predict Salary**.

**Expected Result:** A predicted annual salary is displayed. Monthly/weekly/hourly breakdown appears. Domain classification (e.g. "Data Science") and market comparison (above/below average) are shown. Negotiation tips and career recommendations are visible.

---

### PRED-003 — Age-Experience Validation

**Precondition:** Model 1 selected, Manual Prediction tab open.

**Steps:**
1. Set Age = 20, Years of Experience = 15.
2. Click **Predict Salary**.

**Expected Result:** An error message states that the experience is unrealistic for the given age. No prediction is made.

---

### PRED-004 — Boundary Values (Model 1)

**Steps:**
1. Test each boundary: Age = 18 (minimum), Age = 70 (maximum), Experience = 0.0, Experience = 40.0, Education = 0 (High School), Education = 3 (PhD).
2. Run prediction for each.

**Expected Result:** All boundary inputs are accepted and produce a prediction without errors.

---

### PRED-005 — All Job Titles Produce Valid Predictions (Model 1)

**Steps:**
1. Iterate through 10 different job titles from the dropdown.
2. Run a prediction for each with fixed other inputs.

**Expected Result:** All selected job titles produce a numeric salary prediction. No job title causes an error.

---

### PRED-006 — Country = "Other" (Model 1)

**Steps:**
1. Select Country = Other.
2. Run prediction.

**Expected Result:** Prediction succeeds. Negotiation tips reference generic benchmarks rather than a specific country.

---

### PRED-007 — Model Switch Clears Results

**Steps:**
1. Run a Model 1 prediction.
2. Switch to Model 2 using the model selector.

**Expected Result:** Previous Model 1 prediction results are cleared. The Manual Prediction tab now shows Model 2 input fields.

---

### PRED-008 — Prediction Saved When Logged In

**Precondition:** User is logged in.

**Steps:**
1. Run a manual prediction.
2. Navigate to the Profile tab.

**Expected Result:** The prediction appears in the prediction history table with the correct model name, salary, and timestamp.

---

### PRED-009 — Prediction Not Saved When Logged Out

**Precondition:** User is not logged in.

**Steps:**
1. Run a manual prediction.
2. Log in.
3. Check the Profile tab.

**Expected Result:** The prediction made while logged out does not appear in the Profile history (predictions are not retroactively saved).

---

## 6. Module 3 — Resume Analysis

### RESM-001 — Upload and Extract from Plain Resume

**Precondition:** Full App loaded, any model selected, Resume Analysis tab open.

**Steps:**
1. Upload a plain-text PDF resume with clearly stated experience, education, job title, and skills.
2. Click **Extract Resume Features**.

**Expected Result:** Extraction succeeds. A form appears with detected values for job title, years of experience, education level, country, and skills. A resume score out of 100 is displayed.

---

### RESM-002 — Edit Extracted Features

**Steps:**
1. After extraction, change the detected job title to a different title from the dropdown.
2. Change the detected country.
3. Proceed to prediction.

**Expected Result:** The edited values (not the originally extracted values) are used for the prediction.

---

### RESM-003 — Image-Only PDF (No Extractable Text)

**Steps:**
1. Upload a PDF that contains only scanned images (no embedded text layer).
2. Click **Extract Resume Features**.

**Expected Result:** An error message states "Could not extract readable text from the PDF." No crash occurs. The form does not appear.

---

### RESM-004 — Resume Score Breakdown

**Steps:**
1. Upload a resume with known attributes (e.g. 5 years experience, Master's degree, 5 skills).
2. Check the resume score breakdown.

**Expected Result:** Experience, Education, and Skills sub-scores appear and sum to the total score. The level label (Basic/Moderate/Strong) matches the total score range.

---

### RESM-005 — New Upload Resets State

**Steps:**
1. Upload a resume and extract features.
2. Upload a different resume.

**Expected Result:** Previously extracted features, resume score, and prediction result are cleared. The new resume is processed from scratch.

---

### RESM-006 — Resume Prediction (App 2)

**Precondition:** Model 2 selected.

**Steps:**
1. Upload a data science resume.
2. Extract features.
3. Click **Predict Salary from Resume**.

**Expected Result:** Prediction succeeds using App 2 pipeline. Results display annual salary, breakdown, and App 2 score components (experience, skills, title relevance).

---

## 7. Module 4 — Batch Prediction

### BTCH-001 — Valid CSV Upload (App 1)

**Steps:**
1. Navigate to Batch Prediction tab, Model 1 selected.
2. Upload a valid App 1 CSV file.
3. Click **Run Batch Prediction**.

**Expected Result:** Predictions complete for all rows. A results table appears with all input columns plus "Predicted Annual Salary (USD)", "Salary Band", and "Career Stage". The batch analytics dashboard appears below.

---

### BTCH-002 — Valid CSV Upload (App 2)

**Steps:**
1. Switch to Model 2.
2. Upload a valid App 2 CSV.
3. Run batch prediction.

**Expected Result:** Predictions complete. Results include "Predicted Annual Salary (USD)" column. Analytics show experience level, company size, work mode, and country breakdowns.

---

### BTCH-003 — Missing Columns Rejected

**Steps:**
1. Upload a CSV with one required column missing (e.g. missing "Senior" for App 1).
2. Click Run Batch Prediction.

**Expected Result:** A validation error identifies the specific missing column(s). No prediction is attempted.

---

### BTCH-004 — Wrong Column Name Rejected

**Steps:**
1. Upload a CSV with a column named "age" (lowercase) instead of "Age".

**Expected Result:** Validation fails with a specific message about the incorrect column name.

---

### BTCH-005 — Invalid Values Flagged

**Steps:**
1. Upload an App 1 CSV where some rows have Age = 5 (below minimum) or an unsupported Job Title.
2. Run batch prediction.

**Expected Result:** Validation identifies rows with invalid values. Either the rows are skipped with a warning, or the entire file is rejected depending on implementation.

---

### BTCH-006 — Google Drive Link Upload

**Steps:**
1. Upload a valid CSV to Google Drive and set sharing to "Anyone with the link can view".
2. Copy the sharing link.
3. Paste it into the Google Drive link field.
4. Select the correct file format (CSV).
5. Click Run Batch Prediction.

**Expected Result:** The file is downloaded and predictions complete successfully.

---

### BTCH-007 — Download Sample File

**Steps:**
1. Click the sample file download button.

**Expected Result:** A sample CSV is downloaded with the correct column names and 5 rows of example data.

---

### BTCH-008 — Batch Analytics Dashboard

**Steps:**
1. After successful batch prediction with App 1 data.
2. View each analytics chart.

**Expected Result:** Summary metrics (total, avg, min, max, std) are correct. Leaderboard shows job titles ranked by average salary. Distribution histogram renders. Experience/country/company size breakdowns render.

---

### BTCH-009 — Export Results

**Steps:**
1. After batch prediction, select CSV format from the export dropdown.
2. Click the download button.
3. Open the downloaded file.

**Expected Result:** The file contains all input columns plus the predicted salary column. Row count matches the input file.

---

### BTCH-010 — XLSX and JSON Export

**Steps:**
1. Export the batch results in XLSX format.
2. Export again in JSON format.

**Expected Result:** Both files download correctly and contain the correct data.

---

## 8. Module 5 — Scenario Analysis

### SCEN-001 — Default Scenario Pre-filled

**Steps:**
1. Navigate to Scenario Analysis tab.

**Expected Result:** One scenario named "Scenario 1" is pre-populated with sensible default values.

---

### SCEN-002 — Add and Remove Scenarios

**Steps:**
1. Click **Add Scenario** four more times (to reach the maximum of 5).
2. Attempt to add a 6th scenario.
3. Remove one scenario using its **Remove** button.

**Expected Result:** Adding works up to 5 scenarios. The Add button is either disabled or ignored at the limit. Removing a scenario reduces the count. At least 1 scenario always remains (Remove button hidden when only 1 remains).

---

### SCEN-003 — Run All Scenarios

**Steps:**
1. Configure 3 scenarios with different inputs (different experience levels or job titles).
2. Click **Run All Scenarios**.

**Expected Result:** Predictions run for all 3 scenarios. A comparison table shows all scenario names and predicted salaries. A bar chart visualises the comparison.

---

### SCEN-004 — Scenario Sensitivity Sweep

**Steps:**
1. After running scenarios, scroll to the Sensitivity Sweep section.
2. Select a baseline scenario.
3. View the sweep chart.

**Expected Result:** The chart shows how predicted salary changes across experience levels (App 2) or education levels (App 1) while all other inputs remain fixed. X-axis labels are ordered correctly.

---

### SCEN-005 — Scenario Export (CSV)

**Steps:**
1. After running scenarios, select CSV from the export dropdown.
2. Click Download.

**Expected Result:** CSV downloads with scenario names, inputs, and predicted salaries.

---

### SCEN-006 — Scenario PDF Report

**Steps:**
1. After running scenarios, click **Prepare PDF Report**.
2. Click Download when ready.

**Expected Result:** PDF downloads containing the scenario comparison table and charts.

---

## 9. Module 9 — Financial Tools

### FINT-001 — Currency Converter Toggle

**Precondition:** A prediction has been made in Manual Prediction.

**Steps:**
1. Enable the Currency Converter toggle.
2. Select a non-USD currency (e.g. INR).
3. Verify the converted amount.

**Expected Result:** The expander opens. The predicted salary is converted to the selected currency using a realistic exchange rate. The rate source and timestamp are shown.

---

### FINT-002 — Currency Converter Fallback

**Steps:**
1. Temporarily disable network access (or simulate by testing with a known unavailable API).
2. Enable the currency converter.

**Expected Result:** A warning about unavailable live rates is shown. The tool either uses a local fallback file or displays an appropriate message. The application does not crash.

---

### FINT-003 — Tax Adjuster

**Steps:**
1. Enable the Tax Adjuster toggle.
2. Verify the detected country.
3. Check the displayed effective tax rate and post-tax salary.
4. Enable the custom rate override and slide to a different rate.

**Expected Result:** Post-tax salary is shown in USD. If currency conversion is active, it is also shown in the selected currency. The custom rate override updates the calculation immediately.

---

### FINT-004 — CoL Adjuster

**Steps:**
1. Enable the CoL Adjuster.
2. Select a comparison country with a known lower CoL (e.g. India vs USA).
3. Verify the PPP-equivalent salary is lower than the original.
4. Select a comparison country with a higher CoL (e.g. Switzerland vs USA for an India-based salary).
5. Verify the PPP-equivalent salary is higher.

**Expected Result:** Adjustment direction matches expectation. The adjustment factor and CoL indices for both countries are displayed.

---

### FINT-005 — CTC Breakdown

**Steps:**
1. Enable the CTC Adjuster.
2. Verify components (Base, HRA, Bonus, PF, etc.) are displayed.
3. For a predicted salary with location hint = India, verify HRA is approximately 50% of Base.

**Expected Result:** All components are shown. Total approximately equals the gross salary. Country-specific rates are applied correctly.

---

### FINT-006 — Take-Home Estimator

**Steps:**
1. Enable the Take-Home Estimator.
2. Verify monthly and annual net salary figures.
3. Verify the breakdown (tax, PF, other deductions).

**Expected Result:** Net annual ≤ gross annual. Monthly = annual / 12. Deduction breakdown items sum to total deductions.

---

### FINT-007 — Savings Estimator

**Steps:**
1. Enable Savings Estimator.
2. Verify monthly savings figure.
3. Verify annual savings = monthly savings × 12.

**Expected Result:** Savings = net monthly × (1 - expense\_ratio). Annual savings = monthly × 12. Both displayed correctly.

---

### FINT-008 — Loan Affordability

**Steps:**
1. Enable Loan Affordability.
2. Verify max loan and affordable EMI.
3. Adjust interest rate slider and verify max loan changes.
4. Adjust tenure slider and verify max loan changes.

**Expected Result:** Affordable EMI ≤ net\_monthly × EMI\_cap. Max loan is calculated using the reducing-balance EMI formula. Adjusting sliders recalculates immediately.

---

### FINT-009 — Investment Growth

**Steps:**
1. Enable Investment Growth.
2. Verify projections at 5, 10, 20, 30 years.
3. Verify 30-year value > 20-year > 10-year > 5-year.

**Expected Result:** Values increase monotonically with time horizon. The formula FV = PMT × ((1+r)^n - 1) / r is correctly applied.

---

### FINT-010 — Emergency Fund Planner

**Steps:**
1. Enable Emergency Fund Planner.
2. Verify 3-month and 6-month targets.
3. Verify months-to-reach figures are reasonable.

**Expected Result:** 6-month target = 2 × 3-month target. Months to reach each target decreases as savings rate increases.

---

### FINT-011 — Financial Tools Independence

**Steps:**
1. Enable all financial tools simultaneously.
2. Disable some tools and re-enable others.
3. Verify each tool retains its state independently.

**Expected Result:** Tools do not interfere with each other. Toggling one tool does not reset another.

---

## 10. Module 6 — Model Analytics

### MANA-001 — App 1 Analytics Sections Load

**Precondition:** Model 1 selected.

**Steps:**
1. Navigate to the Model Analytics tab.
2. Expand each section in turn: Regression Model, Model Diagnostics, Salary Classifier, Clustering & Association Rules, Resume NLP Module.

**Expected Result:** All sections expand without errors. Charts render. Metrics (R², MAE, RMSE) are numeric. Feature importance chart has labelled bars.

---

### MANA-002 — App 2 Analytics Sections Load

**Precondition:** Model 2 selected.

**Steps:**
1. Navigate to Model Analytics tab.
2. Expand each section: Regression Model, Model Diagnostics, Feature Importance and SHAP Analysis, Resume NLP Module.

**Expected Result:** SHAP chart renders with at least 10 features. Grouped feature importance chart shows category-level bars. All metrics are numeric.

---

### MANA-003 — Model Comparison Highlighted

**Steps:**
1. In the Model Comparison table (App 1 or App 2), verify the selected model row is highlighted.

**Expected Result:** The Random Forest row (App 1) or XGBoost row (App 2) has a distinct background colour.

---

### MANA-004 — Analytics PDF Download

**Steps:**
1. Click **Download Model Analytics Report (PDF)** at the bottom of the tab.

**Expected Result:** A PDF downloads immediately (no Prepare step needed). The PDF contains performance metrics and charts.

---

## 11. Module 7 — Data Insights

### DATA-001 — App 1 Dashboards Render

**Precondition:** Model 1 selected.

**Steps:**
1. Navigate to the Data Insights tab.
2. Expand Dashboard 1, Dashboard 2, Dashboard 3 in turn.

**Expected Result:** Each dashboard renders with charts and KPI tiles. Filters are visible and functional.

---

### DATA-002 — Dashboard Filters Work

**Steps:**
1. In Dashboard 1 (App 1), select Education Level = PhD.
2. Verify the charts update to reflect the filtered data.
3. Reset to "All".

**Expected Result:** Charts change when filters are applied. KPI values change to reflect the filtered record count.

---

### DATA-003 — App 2 Dashboards Render

**Precondition:** Model 2 selected.

**Steps:**
1. Navigate to Data Insights tab.
2. Expand all three dashboards.

**Expected Result:** All dashboards render. Job roles chart shows data science titles. Country chart shows ISO codes resolved to country names.

---

## 12. Module 8 — Model Hub

### MHUB-001 — Access Control (Not Logged In)

**Precondition:** User is not logged in.

**Steps:**
1. Navigate to the Model Hub tab.

**Expected Result:** A warning message states that login is required. No model selector or prediction panel is visible.

---

### MHUB-002 — No Active Models

**Precondition:** User is logged in. Registry contains no active models (or registry is empty).

**Steps:**
1. Navigate to the Model Hub tab.

**Expected Result:** An info message states no active models are available. No model selector dropdown appears.

---

### MHUB-003 — Load Model and Predict

**Precondition:** User is logged in. At least one active model exists in the registry.

**Steps:**
1. Select a model from the dropdown.
2. Note the number of input fields and features shown.
3. Click **Load Model**.
4. Fill in the generated input form.
5. Click **Predict**.

**Expected Result:** The bundle downloads (a spinner appears). The input form is generated from the schema. Clicking Predict shows a prediction result with the target variable name and value.

---

### MHUB-004 — Bundle Cached in Session

**Steps:**
1. Load a model (MHUB-003).
2. Navigate to another tab and return to Model Hub.
3. Make another prediction without clicking Load Model again.

**Expected Result:** The model is still loaded (from session cache). No re-download occurs. Prediction works immediately.

---

### MHUB-005 — Admin Bundle Upload

**Precondition:** Logged in as admin. Valid bundle files prepared.

**Steps:**
1. In the Upload Bundle section, upload `model.pkl`, `columns.pkl`, `schema.json`.
2. Enter a display name, description, and target variable name.
3. Click **Upload Bundle**.

**Expected Result:** All three files pass validation. Upload succeeds. A success message shows the generated model ID. The new model appears in the Registry Manager.

---

### MHUB-006 — Upload Rejects Oversized Model

**Steps:**
1. Attempt to upload a `model.pkl` file larger than 200 MB.

**Expected Result:** An error message states the file exceeds the size limit. No upload is attempted.

---

### MHUB-007 — Upload Rejects Invalid Schema

**Steps:**
1. Attempt to upload a `schema.json` that is missing the `"fields"` key.

**Expected Result:** A schema validation error is displayed. The upload is aborted.

---

### MHUB-008 — Registry Manager — Activate/Deactivate

**Precondition:** Admin logged in. At least one model in registry.

**Steps:**
1. In the Registry Manager, deactivate an active model.
2. Verify it no longer appears in the user-facing model dropdown.
3. Re-activate it.
4. Verify it reappears in the dropdown.

**Expected Result:** Active/inactive state is reflected immediately in the model selector after registry cache refresh (within 120 seconds or on next page load).

---

### MHUB-009 — Schema Editor — Visual Build

**Precondition:** Admin logged in.

**Steps:**
1. In the Schema Editor → Visual Editor, add a slider field: name=`age`, type=`int`, ui=`slider`, min=18, max=70, default=30.
2. Add a selectbox field: name=`job_title`, type=`category`, ui=`selectbox`, values=`Data Scientist,ML Engineer`.
3. Verify the schema shows as valid.
4. Download the schema.json.

**Expected Result:** Both fields are added without errors. The schema validation passes. The downloaded JSON contains both fields in the correct format.

---

### MHUB-010 — Schema Upload and Validate

**Steps:**
1. In the Schema Editor → Upload / Validate, upload a valid schema.json.
2. Verify the field count and preview.

**Expected Result:** The schema is parsed, field count is shown, and a UI preview renders correctly.

---

## 13. Module 10 — Feedback System

### FEED-001 — Feedback Form Appears After Prediction

**Steps:**
1. Make a manual prediction.
2. Scroll to the bottom of the results.
3. Look for the feedback expander.

**Expected Result:** A "Share Feedback on This Prediction" expander is visible.

---

### FEED-002 — Submit Minimal Feedback (Anonymous)

**Precondition:** User is not logged in.

**Steps:**
1. Open the feedback expander.
2. Select accuracy = "Somewhat", direction = "Too Low", star rating = 4.
3. Leave actual salary at 0.
4. Click **Submit Feedback**.

**Expected Result:** A success message "Thank you for your feedback!" appears. The form closes or is replaced by the success message. Feedback is visible in the Admin Panel.

---

### FEED-003 — Submit Feedback with Actual Salary

**Steps:**
1. Open the feedback expander.
2. Fill all fields including an actual salary of 80000.
3. Submit.

**Expected Result:** Feedback is stored. The actual salary value appears in Admin Panel feedback analytics.

---

### FEED-004 — Feedback Deduplication

**Steps:**
1. Submit feedback for a prediction.
2. Attempt to open the feedback expander again for the same prediction.

**Expected Result:** The expander shows "Thank you for your feedback!" immediately, without re-showing the form.

---

### FEED-005 — Extended Feedback Submission

**Steps:**
1. Open the feedback expander.
2. Expand the extended data section.
3. Fill in industry, company type, skills (select at least 3), certifications.
4. Submit.

**Expected Result:** Feedback is stored with the `extended_data` nested object. Admin Panel feedback count increases by 1.

---

## 14. Module 11 — User Profile

### PROF-001 — Profile Tab Visibility

**Steps:**
1. Log out and verify Profile tab is not visible.
2. Log in and verify Profile tab appears.

**Expected Result:** Tab visibility correctly follows login state.

---

### PROF-002 — Prediction History Displayed

**Precondition:** User has made at least 3 predictions while logged in.

**Steps:**
1. Navigate to Profile tab.

**Expected Result:** KPI tiles show correct total count, average salary, and latest salary. History chart shows data points. History table shows all predictions.

---

### PROF-003 — View Prediction Inputs

**Steps:**
1. Select a prediction from the "View Prediction Inputs" dropdown.

**Expected Result:** All input fields used for that prediction are displayed correctly, matching what was entered at prediction time.

---

### PROF-004 — Export History (CSV)

**Steps:**
1. Select CSV format from the export dropdown.
2. Click **Prepare Download File**.
3. Click **Download Prediction History**.

**Expected Result:** CSV downloads. It contains all prediction records with model, salary, inputs, and timestamp columns.

---

### PROF-005 — Export History (XLSX and JSON)

**Steps:**
1. Repeat PROF-004 for XLSX and JSON formats.

**Expected Result:** Both files download correctly and contain the same data as the CSV export.

---

## 15. Module 12 — Admin Panel

### ADMN-001 — Access Denied for Non-Admin

**Precondition:** Logged in as a regular (non-admin) user.

**Steps:**
1. Navigate to the Admin Panel tab.

**Expected Result:** An "Access denied." error is displayed and execution is stopped. No diagnostics or data are visible.

---

### ADMN-002 — System Diagnostics

**Precondition:** Logged in as admin.

**Steps:**
1. Navigate to Admin Panel.
2. View the diagnostics section.

**Expected Result:** Python version, OS, architecture, deployment label, RAM usage, and registered user count are all displayed with non-null values.

---

### ADMN-003 — Feedback Analytics Load

**Steps:**
1. Click **Load Feedback Analytics**.

**Expected Result:** Feedback statistics load. Total count, accuracy/direction pie charts, star rating, and model-breakdown bar chart render correctly.

---

### ADMN-004 — Recent Feedback

**Steps:**
1. Click **Show Recent Feedback**.

**Expected Result:** Up to 5 most recent feedback entries are displayed with model, star rating, accuracy, direction, and timestamp.

---

### ADMN-005 — Clear Cache

**Steps:**
1. Click **Clear Cache**.

**Expected Result:** A success message confirms the cache was cleared. On next rerun, fresh data is loaded (e.g. exchange rates refetched).

---

### ADMN-006 — Garbage Collection

**Steps:**
1. Note the RAM usage.
2. Click **Run Garbage Collection**.

**Expected Result:** The number of collected objects is shown. RAM before and after are displayed. RAM may decrease slightly.

---

## 16. Module 13 — PDF Reports

### PDF-001 — Manual Prediction PDF (App 1)

**Steps:**
1. Make a Model 1 manual prediction.
2. Click **Prepare PDF Report**.
3. Click **Download Prediction Summary (PDF)**.

**Expected Result:** PDF downloads. It contains the input summary, predicted salary, salary breakdown, salary band, career stage, negotiation tips, and recommendations.

---

### PDF-002 — Manual Prediction PDF (App 2)

**Steps:**
1. Make a Model 2 manual prediction.
2. Prepare and download the PDF.

**Expected Result:** PDF downloads with Model 2 specific content (domain classification, market comparison, negotiation tips).

---

### PDF-003 — Resume Analysis PDF

**Steps:**
1. Complete a resume-based prediction.
2. Prepare and download the PDF.

**Expected Result:** PDF contains resume score, extracted features, predicted salary, and recommendations.

---

### PDF-004 — Batch Prediction PDF

**Steps:**
1. Complete a batch prediction.
2. Click **Prepare Batch PDF Report** and download.

**Expected Result:** PDF contains summary metrics, salary leaderboard, and distribution charts.

---

### PDF-005 — Scenario Analysis PDF

**Steps:**
1. Complete scenario analysis with 3 scenarios.
2. Prepare and download the scenario PDF.

**Expected Result:** PDF contains the comparison table and chart for all scenarios.

---

### PDF-006 — Model Analytics PDF (Immediate Download)

**Steps:**
1. Navigate to Model Analytics tab.
2. Click **Download Model Analytics Report (PDF)** (no Prepare step).

**Expected Result:** PDF downloads immediately (generated once and cached). Contains all analytics sections for the active model.

---

### PDF-007 — Page Numbering

**Steps:**
1. Download any multi-page PDF report.
2. Check the footer of each page.

**Expected Result:** Each page shows "Page X of Y" in the footer where X and Y are correct.

---

### PDF-008 — PDF Does Not Require Re-prepare After Navigation

**Steps:**
1. Prepare a manual prediction PDF.
2. Navigate to another tab.
3. Return to the Manual Prediction tab.

**Expected Result:** The Download button is still active. Clicking it downloads the same PDF without needing to re-prepare.

---

## 17. Core Unit Tests — Password Policy

Create file `tests/test_password_policy.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from app.core.password_policy import validate_password_strength, password_strength_hint


class TestPasswordPolicy(unittest.TestCase):

    def test_valid_password_passes(self):
        """A password meeting all requirements should return no errors."""
        errors = validate_password_strength("Secure#Pass12")
        self.assertEqual(errors, [], f"Expected no errors, got: {errors}")

    def test_too_short_rejected(self):
        """Password under 12 characters should be rejected."""
        errors = validate_password_strength("Short#1A")
        self.assertTrue(any("12 characters" in e for e in errors))

    def test_too_long_rejected(self):
        """Password over 128 characters should be rejected."""
        long_pass = "A" * 64 + "b" * 64 + "#1"
        errors = validate_password_strength(long_pass)
        self.assertTrue(any("128" in e for e in errors))

    def test_no_uppercase_rejected(self):
        errors = validate_password_strength("nouppercase#12")
        self.assertTrue(any("uppercase" in e for e in errors))

    def test_no_lowercase_rejected(self):
        errors = validate_password_strength("NOLOWERCASE#12")
        self.assertTrue(any("lowercase" in e for e in errors))

    def test_no_digit_rejected(self):
        errors = validate_password_strength("NoDigitHere!!!")
        self.assertTrue(any("digit" in e for e in errors))

    def test_no_special_char_rejected(self):
        errors = validate_password_strength("NoSpecial123Abc")
        self.assertTrue(any("special character" in e for e in errors))

    def test_leading_space_rejected(self):
        errors = validate_password_strength(" LeadingSpace#1")
        self.assertTrue(any("space" in e for e in errors))

    def test_trailing_space_rejected(self):
        errors = validate_password_strength("TrailingSpace#1 ")
        self.assertTrue(any("space" in e for e in errors))

    def test_consecutive_identical_chars_rejected(self):
        errors = validate_password_strength("Passsword#12345")
        self.assertTrue(any("identical" in e.lower() or "consecutive" in e.lower() for e in errors))

    def test_common_password_rejected(self):
        errors = validate_password_strength("password123!AB")
        self.assertTrue(any("common" in e.lower() for e in errors))

    def test_non_string_input_handled(self):
        errors = validate_password_strength(None)
        self.assertTrue(len(errors) > 0)
        errors = validate_password_strength(12345)
        self.assertTrue(len(errors) > 0)

    def test_empty_string_handled(self):
        errors = validate_password_strength("")
        self.assertTrue(len(errors) > 0)

    def test_hint_is_string(self):
        hint = password_strength_hint()
        self.assertIsInstance(hint, str)
        self.assertGreater(len(hint), 0)

    def test_valid_password_with_various_special_chars(self):
        for special in ["!", "@", "#", "$", "%", "^", "&", "*"]:
            pw = f"ValidPass{special}123"
            errors = validate_password_strength(pw)
            self.assertEqual(errors, [], f"Password with '{special}' should pass")

    def test_exactly_12_chars_accepted(self):
        errors = validate_password_strength("Secure#Pass1")
        self.assertEqual(errors, [])

    def test_exactly_128_chars_accepted(self):
        pw = "Aa1!" + "x" * 124
        errors = validate_password_strength(pw)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
```

---

## 18. Core Unit Tests — Rate Limiter

Create file `tests/test_rate_limiter.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import unittest
from unittest.mock import patch, MagicMock

# Mock streamlit before importing rate_limiter
import unittest.mock
sys.modules['streamlit'] = MagicMock()

from app.core.rate_limiter import (
    check_rate_limit,
    record_attempt,
    clear_attempts,
    _session_check,
    _session_record,
    _session_clear,
    _fs_doc_id,
    _blocked_message,
    _LIMITS,
)


class TestRateLimiterSessionLayer(unittest.TestCase):

    def setUp(self):
        """Reset session state mock before each test."""
        import streamlit as st
        st.session_state = {}

    def test_unknown_action_always_allowed(self):
        """An action not in _LIMITS should always return allowed=True."""
        import streamlit as st
        st.session_state = {}
        allowed, msg = check_rate_limit("nonexistent_action", "user@test.com")
        self.assertTrue(allowed)
        self.assertIsNone(msg)

    def test_blocked_message_format(self):
        """Blocked message should mention minutes and be a non-empty string."""
        msg = _blocked_message(300.0)
        self.assertIn("minute", msg)
        self.assertIsInstance(msg, str)

    def test_blocked_message_minimum_one_minute(self):
        """Even 0 seconds remaining should show at least 1 minute."""
        msg = _blocked_message(0.0)
        self.assertIn("1 minute", msg)

    def test_doc_id_hides_pii(self):
        """Firestore document ID should not contain the raw email."""
        doc_id = _fs_doc_id("login", "secret@example.com")
        self.assertNotIn("secret", doc_id)
        self.assertNotIn("example.com", doc_id)
        self.assertTrue(doc_id.startswith("login__"))

    def test_doc_id_deterministic(self):
        """Same action + identifier should always produce the same doc ID."""
        id1 = _fs_doc_id("login", "user@test.com")
        id2 = _fs_doc_id("login", "user@test.com")
        self.assertEqual(id1, id2)

    def test_doc_id_different_for_different_users(self):
        id1 = _fs_doc_id("login", "user1@test.com")
        id2 = _fs_doc_id("login", "user2@test.com")
        self.assertNotEqual(id1, id2)

    def test_session_check_no_record_allows(self):
        import streamlit as st
        st.session_state = {}
        blocked, wait = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)

    def test_session_record_and_check_blocks_after_limit(self):
        import streamlit as st
        st.session_state = {}
        for _ in range(5):
            _session_record("login", "user@test.com")
        blocked, wait = _session_check("login", "user@test.com", 5, 300)
        self.assertTrue(blocked)
        self.assertGreater(wait, 0)

    def test_session_clear_resets_counter(self):
        import streamlit as st
        st.session_state = {}
        for _ in range(5):
            _session_record("login", "user@test.com")
        _session_clear("login", "user@test.com")
        blocked, _ = _session_check("login", "user@test.com", 5, 300)
        self.assertFalse(blocked)

    def test_rate_limiter_limits_config(self):
        """Verify all expected actions are configured."""
        expected = {"login", "register", "resend_verify",
                    "change_password", "delete_account", "forgot_password"}
        self.assertEqual(set(_LIMITS.keys()), expected)


if __name__ == '__main__':
    unittest.main()
```

---

## 19. Core Unit Tests — Resume NLP Pipeline

Create file `tests/test_resume_analysis.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import patch, MagicMock
sys.modules['streamlit'] = MagicMock()

from app.core.resume_analysis import (
    preprocess_resume_text,
    extract_experience_years,
    calculate_resume_score,
    extract_employment_type_a2,
    extract_remote_ratio_a2,
    calculate_resume_score_a2,
)


class TestPreprocessResumeText(unittest.TestCase):

    def test_returns_string(self):
        result = preprocess_resume_text("Some raw text here.")
        self.assertIsInstance(result, str)

    def test_handles_empty_string(self):
        result = preprocess_resume_text("")
        self.assertIsInstance(result, str)


class TestExtractExperienceYears(unittest.TestCase):

    def test_explicit_years(self):
        result = extract_experience_years("I have 5 years of experience in Python.")
        self.assertAlmostEqual(result, 5.0, places=0)

    def test_plus_notation(self):
        result = extract_experience_years("Over 3+ years of professional work.")
        self.assertAlmostEqual(result, 3.0, places=0)

    def test_no_experience_returns_zero(self):
        result = extract_experience_years("Recent graduate with strong academic background.")
        self.assertEqual(result, 0.0)

    def test_returns_float(self):
        result = extract_experience_years("7 years experience")
        self.assertIsInstance(result, float)


class TestCalculateResumeScoreApp1(unittest.TestCase):

    def test_score_structure(self):
        features = {
            "years_of_experience": 5.0,
            "education_level": 1,
            "skills": ["python", "sql", "pandas"]
        }
        result = calculate_resume_score(features)
        self.assertIn("total_score", result)
        self.assertIn("level", result)
        self.assertIn("experience_score", result)
        self.assertIn("education_score", result)
        self.assertIn("skills_score", result)

    def test_score_range(self):
        features = {
            "years_of_experience": 10.0,
            "education_level": 3,
            "skills": ["python"] * 15
        }
        result = calculate_resume_score(features)
        self.assertGreaterEqual(result["total_score"], 0)
        self.assertLessEqual(result["total_score"], 100)

    def test_zero_experience_zero_score_component(self):
        features = {"years_of_experience": 0.0, "education_level": 0, "skills": []}
        result = calculate_resume_score(features)
        self.assertEqual(result["experience_score"], 0)
        self.assertEqual(result["skills_score"], 0)

    def test_phd_max_education_score(self):
        features = {"years_of_experience": 0.0, "education_level": 3, "skills": []}
        result = calculate_resume_score(features)
        self.assertEqual(result["education_score"], 35)

    def test_level_labels(self):
        features_basic = {"years_of_experience": 0.0, "education_level": 0, "skills": []}
        result = calculate_resume_score(features_basic)
        self.assertIn(result["level"], ["Basic", "Moderate", "Strong"])


class TestExtractEmploymentType(unittest.TestCase):

    def test_full_time_default(self):
        result = extract_employment_type_a2("software engineer at tech company")
        self.assertEqual(result, "FT")

    def test_part_time_detected(self):
        result = extract_employment_type_a2("part-time data analyst position")
        self.assertEqual(result, "PT")

    def test_freelance_detected(self):
        result = extract_employment_type_a2("freelancer with 5 years experience")
        self.assertEqual(result, "FL")

    def test_contract_detected(self):
        result = extract_employment_type_a2("contract consultant role")
        self.assertEqual(result, "CT")

    def test_internship_detected_as_part_time(self):
        result = extract_employment_type_a2("summer internship at a startup")
        self.assertEqual(result, "PT")


class TestExtractRemoteRatio(unittest.TestCase):

    def test_onsite_default(self):
        result = extract_remote_ratio_a2("office-based position in NYC")
        self.assertEqual(result, 0)

    def test_remote_detected(self):
        result = extract_remote_ratio_a2("fully remote work from home position")
        self.assertEqual(result, 100)

    def test_hybrid_detected(self):
        result = extract_remote_ratio_a2("hybrid role with flexible working")
        self.assertEqual(result, 50)

    def test_wfh_detected_as_remote(self):
        result = extract_remote_ratio_a2("WFH allowed, 100% remote")
        self.assertEqual(result, 100)


class TestCalculateResumeScoreApp2(unittest.TestCase):

    def test_score_structure(self):
        features = {
            "years_of_experience_a2": 5.0,
            "skills_a2": ["python", "machine learning", "sql"],
            "job_title_a2": "Data Scientist"
        }
        result = calculate_resume_score_a2(features)
        self.assertIn("total_score_a2", result)
        self.assertIn("level_a2", result)
        self.assertIn("experience_score_a2", result)
        self.assertIn("skills_score_a2", result)
        self.assertIn("title_score_a2", result)
        self.assertIn("ds_skill_count_a2", result)

    def test_ds_title_gets_max_title_score(self):
        features = {
            "years_of_experience_a2": 0.0,
            "skills_a2": [],
            "job_title_a2": "Data Scientist"
        }
        result = calculate_resume_score_a2(features)
        self.assertEqual(result["title_score_a2"], 25)

    def test_ds_skills_weighted_higher(self):
        features_ds = {
            "years_of_experience_a2": 0.0,
            "skills_a2": ["python", "machine learning"],
            "job_title_a2": "Other"
        }
        features_gen = {
            "years_of_experience_a2": 0.0,
            "skills_a2": ["excel", "powerpoint"],
            "job_title_a2": "Other"
        }
        result_ds = calculate_resume_score_a2(features_ds)
        result_gen = calculate_resume_score_a2(features_gen)
        self.assertGreater(result_ds["skills_score_a2"], result_gen["skills_score_a2"])


if __name__ == '__main__':
    unittest.main()
```

---

## 20. Core Unit Tests — Financial Utility Functions

Create file `tests/test_financial_utils.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from app.utils.country_utils import get_country_name, resolve_iso2
from app.utils.col_utils import get_col_index, compute_col_adjusted
from app.utils.savings_utils import compute_savings_potential
from app.utils.loan_utils import compute_loan_affordability
from app.utils.investment_utils import compute_investment_growth
from app.utils.emergency_fund_utils import compute_emergency_fund
from app.utils.budget_utils import compute_budget_allocation
from app.utils.ctc_utils import compute_ctc_breakdown


class TestCountryUtils(unittest.TestCase):

    def test_get_country_name_valid_iso(self):
        result = get_country_name("US")
        self.assertIn("United States", result)

    def test_get_country_name_unknown_returns_code(self):
        result = get_country_name("XX")
        self.assertEqual(result, "XX")

    def test_get_country_name_none_returns_unknown(self):
        result = get_country_name(None)
        self.assertEqual(result, "Unknown")

    def test_resolve_iso2_from_name(self):
        self.assertEqual(resolve_iso2("United States"), "US")
        self.assertEqual(resolve_iso2("India"), "IN")
        self.assertEqual(resolve_iso2("Germany"), "DE")

    def test_resolve_iso2_from_alias(self):
        self.assertEqual(resolve_iso2("USA"), "US")
        self.assertEqual(resolve_iso2("UK"), "GB")
        self.assertEqual(resolve_iso2("UAE"), "AE")

    def test_resolve_iso2_case_insensitive(self):
        self.assertEqual(resolve_iso2("india"), "IN")
        self.assertEqual(resolve_iso2("INDIA"), "IN")

    def test_resolve_iso2_from_direct_code(self):
        self.assertEqual(resolve_iso2("IN"), "IN")
        self.assertEqual(resolve_iso2("US"), "US")

    def test_resolve_iso2_unknown_returns_none(self):
        result = resolve_iso2("Narnia")
        self.assertIsNone(result)


class TestColUtils(unittest.TestCase):

    def test_get_col_index_known_country(self):
        index, source = get_col_index("US")
        self.assertEqual(index, 100.0)
        self.assertIn("built-in", source.lower())

    def test_get_col_index_unknown_country_returns_fallback(self):
        index, source = get_col_index("XX")
        self.assertEqual(index, 50.0)

    def test_compute_col_adjusted_same_country(self):
        result = compute_col_adjusted(100000, "US", "US")
        self.assertAlmostEqual(result["adjustment_factor"], 1.0, places=3)
        self.assertAlmostEqual(result["ppp_equivalent_usd"], 100000.0, places=0)

    def test_compute_col_adjusted_cheaper_country(self):
        # India (CoL ~23) vs USA (CoL 100): salary should appear larger in India terms
        result = compute_col_adjusted(100000, "US", "IN")
        self.assertLess(result["ppp_equivalent_usd"], 100000)
        self.assertLess(result["adjustment_factor"], 1.0)

    def test_compute_col_adjusted_expensive_country(self):
        # Switzerland (CoL 137) vs USA (CoL 100)
        result = compute_col_adjusted(100000, "US", "CH")
        self.assertGreater(result["ppp_equivalent_usd"], 100000)
        self.assertGreater(result["adjustment_factor"], 1.0)


class TestSavingsUtils(unittest.TestCase):

    def test_savings_structure(self):
        result = compute_savings_potential(5000, "US")
        self.assertIn("savings", result)
        self.assertIn("annual_savings", result)
        self.assertIn("expense_ratio", result)
        self.assertIn("savings_rate", result)

    def test_savings_non_negative(self):
        result = compute_savings_potential(3000, "IN")
        self.assertGreaterEqual(result["savings"], 0)

    def test_annual_savings_equals_monthly_times_12(self):
        result = compute_savings_potential(5000, "US")
        self.assertAlmostEqual(result["annual_savings"], result["savings"] * 12, places=2)

    def test_savings_rate_between_0_and_1(self):
        result = compute_savings_potential(5000, "GB")
        self.assertGreaterEqual(result["savings_rate"], 0)
        self.assertLessEqual(result["savings_rate"], 1)


class TestLoanUtils(unittest.TestCase):

    def test_loan_structure(self):
        result = compute_loan_affordability(5000, "US")
        self.assertIn("max_loan", result)
        self.assertIn("affordable_emi", result)
        self.assertIn("loan_rate", result)
        self.assertIn("tenure_years", result)

    def test_max_loan_positive(self):
        result = compute_loan_affordability(5000, "US")
        self.assertGreater(result["max_loan"], 0)

    def test_affordable_emi_within_cap(self):
        net_monthly = 5000
        result = compute_loan_affordability(net_monthly, "US")
        emi_cap = result.get("emi_cap_fraction", 0.4)
        self.assertLessEqual(result["affordable_emi"], net_monthly * emi_cap + 1)  # +1 for rounding


class TestInvestmentUtils(unittest.TestCase):

    def test_investment_structure(self):
        result = compute_investment_growth(500, "US")
        self.assertIn("value_5yr", result)
        self.assertIn("value_10yr", result)
        self.assertIn("value_20yr", result)
        self.assertIn("value_30yr", result)

    def test_investment_grows_over_time(self):
        result = compute_investment_growth(500, "US")
        self.assertLess(result["value_5yr"], result["value_10yr"])
        self.assertLess(result["value_10yr"], result["value_20yr"])
        self.assertLess(result["value_20yr"], result["value_30yr"])

    def test_zero_savings_gives_zero_growth(self):
        result = compute_investment_growth(0, "US")
        self.assertEqual(result["value_5yr"], 0.0)
        self.assertEqual(result["value_30yr"], 0.0)


class TestEmergencyFundUtils(unittest.TestCase):

    def test_emergency_fund_structure(self):
        result = compute_emergency_fund(5000, "US")
        self.assertIn("target_3mo", result)
        self.assertIn("target_6mo", result)
        self.assertIn("monthly_expense", result)

    def test_6_month_double_3_month(self):
        result = compute_emergency_fund(5000, "US")
        self.assertAlmostEqual(result["target_6mo"], result["target_3mo"] * 2, places=0)


class TestBudgetUtils(unittest.TestCase):

    def test_budget_structure(self):
        result = compute_budget_allocation(5000, "US")
        self.assertIn("categories", result)
        self.assertIsInstance(result["categories"], list)
        self.assertGreater(len(result["categories"]), 0)

    def test_category_structure(self):
        result = compute_budget_allocation(5000, "US")
        for cat in result["categories"]:
            self.assertIn("label", cat)
            self.assertIn("amount_usd", cat)
            self.assertIn("pct", cat)

    def test_allocations_sum_to_net(self):
        net = 5000
        result = compute_budget_allocation(net, "US")
        total = sum(c["amount_usd"] for c in result["categories"])
        self.assertAlmostEqual(total, net, delta=10)


class TestCtcUtils(unittest.TestCase):

    def test_ctc_structure(self):
        result = compute_ctc_breakdown(80000, "IN")
        self.assertIn("basic", result)
        self.assertIn("hra", result)
        self.assertIn("bonus", result)
        self.assertIn("pf_employee", result)

    def test_india_hra_is_50_of_basic(self):
        result = compute_ctc_breakdown(80000, "IN")
        self.assertAlmostEqual(result["hra"], result["basic"] * 0.50, delta=100)

    def test_us_hra_is_zero(self):
        result = compute_ctc_breakdown(80000, "US")
        self.assertEqual(result["hra"], 0.0)


if __name__ == '__main__':
    unittest.main()
```

---

## 21. Core Unit Tests — Insights Engine

Create file `tests/test_insights_engine.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from app.core.insights_engine import (
    detect_domain_from_title,
    classify_job_group_app1,
    get_experience_category_app1,
    classify_role_app2,
)


class TestDomainDetection(unittest.TestCase):

    def test_ml_ai_detected(self):
        self.assertEqual(detect_domain_from_title("Machine Learning Engineer"), "ml_ai")
        self.assertEqual(detect_domain_from_title("NLP Researcher"), "ml_ai")
        self.assertEqual(detect_domain_from_title("MLOps Engineer"), "ml_ai")

    def test_analytics_detected(self):
        self.assertEqual(detect_domain_from_title("Data Analyst"), "analytics")
        self.assertEqual(detect_domain_from_title("Business Intelligence Analyst"), "analytics")

    def test_data_eng_detected(self):
        self.assertEqual(detect_domain_from_title("Data Engineer"), "data_eng")
        self.assertEqual(detect_domain_from_title("ETL Developer"), "data_eng")

    def test_scientist_detected(self):
        self.assertEqual(detect_domain_from_title("Data Scientist"), "scientist")

    def test_ml_ai_takes_priority_over_analyst(self):
        # An ML analyst should be ml_ai (higher priority)
        result = detect_domain_from_title("ML Research Analyst")
        self.assertEqual(result, "ml_ai")

    def test_other_for_unknown(self):
        self.assertEqual(detect_domain_from_title("Marketing Manager"), "other")
        self.assertEqual(detect_domain_from_title(""), "other")

    def test_none_returns_other(self):
        self.assertEqual(detect_domain_from_title(None), "other")


class TestJobGroupApp1(unittest.TestCase):

    def test_tech_group(self):
        self.assertEqual(classify_job_group_app1("Software Engineer"), "Tech")
        self.assertEqual(classify_job_group_app1("Data Analyst"), "Tech")

    def test_management_group(self):
        self.assertEqual(classify_job_group_app1("Project Manager"), "Management")
        self.assertEqual(classify_job_group_app1("Director of Engineering"), "Management")

    def test_marketing_group(self):
        self.assertEqual(classify_job_group_app1("Marketing Manager"), "Marketing_Sales")

    def test_hr_group(self):
        self.assertEqual(classify_job_group_app1("HR Generalist"), "HR")
        self.assertEqual(classify_job_group_app1("Recruiter"), "HR")

    def test_finance_group(self):
        self.assertEqual(classify_job_group_app1("Financial Analyst"), "Finance")

    def test_design_group(self):
        self.assertEqual(classify_job_group_app1("UX Designer"), "Design")

    def test_operations_fallback(self):
        self.assertEqual(classify_job_group_app1("Office Administrator"), "Operations")

    def test_non_string_returns_operations(self):
        self.assertEqual(classify_job_group_app1(None), "Operations")


class TestExperienceCategoryApp1(unittest.TestCase):

    def test_entry_level(self):
        self.assertEqual(get_experience_category_app1(0.0), "Entry")
        self.assertEqual(get_experience_category_app1(2.0), "Entry")

    def test_mid_level(self):
        self.assertEqual(get_experience_category_app1(2.5), "Mid")
        self.assertEqual(get_experience_category_app1(5.0), "Mid")

    def test_senior_level(self):
        self.assertEqual(get_experience_category_app1(5.5), "Senior")
        self.assertEqual(get_experience_category_app1(20.0), "Senior")


class TestClassifyRoleApp2(unittest.TestCase):

    def test_management_overrides_domain(self):
        result = classify_role_app2("ml_ai", is_mgmt=True, is_exec=False)
        self.assertEqual(result, "Management")

    def test_ml_ai_domain(self):
        result = classify_role_app2("ml_ai", is_mgmt=False, is_exec=False)
        self.assertEqual(result, "Machine Learning / AI")

    def test_analytics_domain(self):
        result = classify_role_app2("analytics", is_mgmt=False, is_exec=False)
        self.assertEqual(result, "Analytics")

    def test_other_domain(self):
        result = classify_role_app2("other", is_mgmt=False, is_exec=False)
        self.assertEqual(result, "Other")


if __name__ == '__main__':
    unittest.main()
```

---

## 22. Core Unit Tests — Model Hub Validator

Create file `tests/test_validator.py`:

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from app.model_hub.validator import (
    validate_schema,
    validate_schema_vs_columns,
    validate_bundle_files,
    parse_schema_json,
)


class TestValidateSchema(unittest.TestCase):

    def _valid_schema(self):
        return {
            "fields": [
                {"name": "age", "type": "int", "ui": "slider", "min": 18, "max": 70, "default": 30},
                {"name": "title", "type": "category", "ui": "selectbox", "values": ["A", "B"]},
            ]
        }

    def test_valid_schema_no_issues(self):
        issues = validate_schema(self._valid_schema())
        self.assertEqual(issues, [])

    def test_missing_fields_key(self):
        issues = validate_schema({})
        self.assertTrue(len(issues) > 0)
        self.assertTrue(any("fields" in i for i in issues))

    def test_empty_fields_list(self):
        issues = validate_schema({"fields": []})
        self.assertTrue(len(issues) > 0)

    def test_duplicate_field_names(self):
        schema = {
            "fields": [
                {"name": "age", "type": "int", "ui": "slider", "min": 0, "max": 100},
                {"name": "age", "type": "float", "ui": "number_input"},
            ]
        }
        issues = validate_schema(schema)
        self.assertTrue(any("Duplicate" in i or "duplicate" in i for i in issues))

    def test_invalid_ui_type(self):
        schema = {"fields": [{"name": "x", "type": "int", "ui": "radio_button"}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_invalid_type_value(self):
        schema = {"fields": [{"name": "x", "type": "vector", "ui": "slider", "min": 0, "max": 10}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_slider_min_greater_than_max(self):
        schema = {"fields": [{"name": "x", "type": "int", "ui": "slider", "min": 100, "max": 10}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_slider_default_out_of_range(self):
        schema = {"fields": [{"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10, "default": 50}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_selectbox_missing_values(self):
        schema = {"fields": [{"name": "x", "type": "category", "ui": "selectbox"}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_selectbox_empty_values(self):
        schema = {"fields": [{"name": "x", "type": "category", "ui": "selectbox", "values": []}]}
        issues = validate_schema(schema)
        self.assertTrue(len(issues) > 0)

    def test_non_dict_input(self):
        issues = validate_schema("not a dict")
        self.assertTrue(len(issues) > 0)


class TestValidateSchemaVsColumns(unittest.TestCase):

    def test_direct_match_no_issues(self):
        schema = {"fields": [{"name": "age", "type": "int", "ui": "slider", "min": 0, "max": 100}]}
        columns = ["age"]
        issues = validate_schema_vs_columns(schema, columns)
        self.assertEqual(issues, [])

    def test_ohe_match_no_hard_errors(self):
        schema = {"fields": [
            {"name": "job_title", "type": "category", "ui": "selectbox",
             "values": ["Data Scientist", "ML Engineer"]}
        ]}
        columns = ["job_title_Data Scientist", "job_title_ML Engineer"]
        issues = validate_schema_vs_columns(schema, columns)
        hard_errors = [i for i in issues if "no matching column" in i.lower() or "missing" in i.lower()]
        self.assertEqual(hard_errors, [])

    def test_missing_field_is_flagged(self):
        schema = {"fields": [{"name": "salary", "type": "float", "ui": "number_input"}]}
        columns = ["age", "experience"]
        issues = validate_schema_vs_columns(schema, columns)
        self.assertTrue(len(issues) > 0)

    def test_extra_columns_noted(self):
        schema = {"fields": [{"name": "age", "type": "int", "ui": "slider", "min": 0, "max": 100}]}
        columns = ["age", "extra_engineered_feature"]
        issues = validate_schema_vs_columns(schema, columns)
        self.assertTrue(any("0.0" in i or "extra" in i.lower() or "not covered" in i.lower() for i in issues))


class TestValidateBundleFiles(unittest.TestCase):

    def test_all_files_present(self):
        missing = validate_bundle_files(["model.pkl", "columns.pkl", "schema.json"])
        self.assertEqual(missing, [])

    def test_missing_model_pkl(self):
        missing = validate_bundle_files(["columns.pkl", "schema.json"])
        self.assertIn("model.pkl", missing)

    def test_missing_multiple_files(self):
        missing = validate_bundle_files(["model.pkl"])
        self.assertIn("columns.pkl", missing)
        self.assertIn("schema.json", missing)

    def test_extra_files_are_ignored(self):
        missing = validate_bundle_files(["model.pkl", "columns.pkl", "schema.json", "readme.txt"])
        self.assertEqual(missing, [])


class TestParseSchemaJson(unittest.TestCase):

    def test_valid_json_parses_correctly(self):
        import json
        schema = {"fields": [{"name": "x", "type": "int", "ui": "slider", "min": 0, "max": 10}]}
        raw = json.dumps(schema).encode("utf-8")
        parsed, issues = parse_schema_json(raw)
        self.assertEqual(issues, [])
        self.assertEqual(parsed["fields"][0]["name"], "x")

    def test_invalid_json_returns_empty_dict(self):
        parsed, issues = parse_schema_json(b"not valid json {{{")
        self.assertEqual(parsed, {})
        self.assertTrue(len(issues) > 0)

    def test_accepts_string_input(self):
        import json
        schema = {"fields": [{"name": "y", "type": "float", "ui": "number_input"}]}
        raw = json.dumps(schema)
        parsed, issues = parse_schema_json(raw)
        self.assertIsInstance(parsed, dict)


if __name__ == '__main__':
    unittest.main()
```

---

## 23. Integration Tests

### INT-001 — Full Manual Prediction Pipeline (App 1)

**Description:** Verifies the end-to-end flow from input to Firestore storage.

**Steps:**
1. Log in with a test account.
2. Select Model 1.
3. Make a manual prediction with valid inputs.
4. Query Firestore `predictions/{test_email}/records` and verify the new document exists.
5. Navigate to Profile tab and verify the prediction appears in the history.

**Expected Result:** One new Firestore document exists with matching model\_used, predicted\_salary, and created\_at.

---

### INT-002 — Financial Tool Chain (Currency → Tax → CoL)

**Description:** Verifies the data flow between financial tools.

**Steps:**
1. Make a prediction with Model 2, USA company location.
2. Enable Currency Converter, select INR.
3. Enable Tax Adjuster — verify it shows post-tax in INR (uses active currency from currency tool).
4. Enable CoL Adjuster — verify PPP calculation uses the gross USD amount.

**Expected Result:** Tax adjuster displays post-tax in both USD and INR. CoL adjuster operates on gross USD. Each tool is independent and can be enabled/disabled without affecting others.

---

### INT-003 — Model Hub Upload → Registry → Predict

**Description:** Verifies the complete admin upload flow through to user prediction.

**Steps:**
1. Log in as admin.
2. Prepare and upload a valid bundle via the Model Hub Upload section.
3. Verify the model appears in the Registry Manager.
4. Verify it appears as active in the user-facing model dropdown.
5. Load the model and make a prediction.

**Expected Result:** Upload succeeds, registry is updated, model is accessible, prediction produces a numeric result.

---

### INT-004 — Rate Limiter Across Session Boundary

**Description:** Verifies Firestore-layer rate limiting persists across browser sessions.

**Steps:**
1. In Session A, fail login 5 times with the same email.
2. Open a new browser tab (Session B) or incognito window.
3. Attempt login with the same email in Session B.

**Expected Result:** The 6th attempt in Session B is blocked by the Firestore rate limit layer, even though Session B has no session-state records of prior attempts.

---

### INT-005 — Feedback Stored and Visible in Admin Panel

**Steps:**
1. Make a prediction (any model).
2. Submit feedback with star rating = 5, accuracy = "Yes", direction = "About Right".
3. Log in as admin.
4. Open Admin Panel → Load Feedback Analytics.

**Expected Result:** Total feedback count increases by 1. The submitted star rating and accuracy are reflected in the aggregate stats.

---

## 24. Security Tests

### SEC-001 — Admin Panel Access Control

**Steps:**
1. Log in as a regular (non-admin) user.
2. Navigate to the Admin Panel tab.

**Expected Result:** "Access denied." is displayed. No system data is exposed.

---

### SEC-002 — Model Hub Upload Restricted to Admin

**Steps:**
1. Log in as a regular user.
2. Navigate to Model Hub.

**Expected Result:** The Upload Bundle, Registry Manager, and Schema Editor sections are not visible. Only the prediction panel is shown.

---

### SEC-003 — Rate Limit PII Protection

**Description:** Verify that Firestore rate limit documents do not expose email addresses.

**Steps:**
1. Fail login 3 times with a known email.
2. Open Firebase Console → Firestore → `rate_limits` collection.
3. Inspect the document ID.

**Expected Result:** The document ID contains a hash prefix (e.g. `login__a3f2b1c4d5e6f7a8`) and not the raw email address.

---

### SEC-004 — Session Expiry Enforcement

**Steps (local only):**
1. Log in.
2. Manually set `st.session_state._session_expiry` to 1 minute ago.
3. Trigger any Streamlit interaction.

**Expected Result:** User is automatically logged out. The session is destroyed. Login is required again.

---

### SEC-005 — No Plain Text Passwords in Firestore

**Steps:**
1. Register a test account.
2. Open Firebase Console → Firestore → `users` collection.
3. Open the document for the test email.

**Expected Result:** The document contains only `username`, `email`, `display_name`, `created_at`, `auth_provider`. No password field exists.

---

### SEC-006 — Account Enumeration Protection (Forgot Password)

**Steps:**
1. Submit Forgot Password with a non-existent email.
2. Submit Forgot Password with a real email.

**Expected Result:** Both responses show the same generic success message. The response for the non-existent email does not reveal that the account does not exist.

---

## 25. Performance Tests

Record timing for each test using a stopwatch or browser developer tools.

### PERF-001 — Manual Prediction Response Time

**Steps:**
1. Fill in all Model 1 inputs.
2. Start timer.
3. Click **Predict Salary**.
4. Stop timer when results appear.

**Expected Result:** ≤ 3 seconds.

---

### PERF-002 — Batch Prediction (1,000 rows)

**Steps:**
1. Prepare a valid 1,000-row CSV.
2. Upload and start timer.
3. Click **Run Batch Prediction**.
4. Stop timer when results table appears.

**Expected Result:** ≤ 30 seconds.

---

### PERF-003 — PDF Generation Time

**Steps:**
1. Make a manual prediction.
2. Start timer.
3. Click **Prepare PDF Report**.
4. Stop timer when the download button appears.

**Expected Result:** ≤ 10 seconds.

---

### PERF-004 — Model Analytics PDF (Cached)

**Steps:**
1. Navigate to Model Analytics tab.
2. Start timer.
3. Click **Download Model Analytics Report (PDF)**.
4. Stop timer when the file downloads.

**Expected Result:** ≤ 3 seconds on second call (cached). ≤ 30 seconds on first call.

---

### PERF-005 — Currency Rate Fetch

**Steps:**
1. Clear the app cache (Admin Panel → Clear Cache).
2. Enable the Currency Converter.
3. Note the time for rates to load.

**Expected Result:** ≤ 5 seconds (API timeout is set to 5 seconds). Falls back gracefully if longer.

---

### PERF-006 — Data Insights Dashboard Render

**Steps:**
1. Navigate to Data Insights tab.
2. Start timer.
3. Expand Dashboard 1.
4. Stop timer when all charts are visible.

**Expected Result:** ≤ 5 seconds.

---

## 26. Test Results Log Template

Copy this table for each test session to record results.

**Test Session Date:** ___________  
**Tester:** ___________  
**Application Version:** 1.1.0  
**Environment:** Local / Streamlit Cloud  
**Model(s) Tested:** Model 1 / Model 2 / Both  

| Test ID | Description | Pass / Fail | Actual Result (if different from expected) | Notes |
|---|---|---|---|---|
| AUTH-001 | Registration valid inputs | | | |
| AUTH-002 | Password policy enforcement | | | |
| AUTH-003 | Duplicate email | | | |
| AUTH-004 | Email verification | | | |
| AUTH-005 | Login verified account | | | |
| AUTH-006 | Login wrong password | | | |
| AUTH-007 | Login rate limiting | | | |
| AUTH-008 | Login unverified | | | |
| AUTH-009 | Forgot password | | | |
| AUTH-010 | Forgot password non-existent email | | | |
| AUTH-011 | Session expiry | | | |
| AUTH-012 | Logout | | | |
| AUTH-013 | Change password | | | |
| AUTH-014 | Change password wrong current | | | |
| AUTH-015 | Delete account | | | |
| AUTH-016 | Delete account wrong phrase | | | |
| PRED-001 | Model 1 prediction happy path | | | |
| PRED-002 | Model 2 prediction happy path | | | |
| PRED-003 | Age-experience validation | | | |
| PRED-004 | Boundary values | | | |
| PRED-005 | All job titles | | | |
| PRED-006 | Country = Other | | | |
| PRED-007 | Model switch clears results | | | |
| PRED-008 | Prediction saved logged in | | | |
| PRED-009 | Prediction not saved logged out | | | |
| RESM-001 | Plain resume extraction | | | |
| RESM-002 | Edit extracted features | | | |
| RESM-003 | Image-only PDF | | | |
| RESM-004 | Resume score breakdown | | | |
| RESM-005 | New upload resets state | | | |
| RESM-006 | Resume prediction App 2 | | | |
| BTCH-001 | Valid CSV App 1 | | | |
| BTCH-002 | Valid CSV App 2 | | | |
| BTCH-003 | Missing columns rejected | | | |
| BTCH-004 | Wrong column name | | | |
| BTCH-005 | Invalid values flagged | | | |
| BTCH-006 | Google Drive link | | | |
| BTCH-007 | Download sample file | | | |
| BTCH-008 | Batch analytics dashboard | | | |
| BTCH-009 | Export CSV | | | |
| BTCH-010 | Export XLSX and JSON | | | |
| SCEN-001 | Default scenario | | | |
| SCEN-002 | Add and remove scenarios | | | |
| SCEN-003 | Run all scenarios | | | |
| SCEN-004 | Sensitivity sweep | | | |
| SCEN-005 | Scenario export CSV | | | |
| SCEN-006 | Scenario PDF | | | |
| FINT-001 | Currency converter toggle | | | |
| FINT-002 | Currency fallback | | | |
| FINT-003 | Tax adjuster | | | |
| FINT-004 | CoL adjuster | | | |
| FINT-005 | CTC breakdown | | | |
| FINT-006 | Take-home estimator | | | |
| FINT-007 | Savings estimator | | | |
| FINT-008 | Loan affordability | | | |
| FINT-009 | Investment growth | | | |
| FINT-010 | Emergency fund | | | |
| FINT-011 | Tools independence | | | |
| MANA-001 | App 1 analytics sections | | | |
| MANA-002 | App 2 analytics sections | | | |
| MANA-003 | Model comparison highlighted | | | |
| MANA-004 | Analytics PDF download | | | |
| DATA-001 | App 1 dashboards render | | | |
| DATA-002 | Dashboard filters work | | | |
| DATA-003 | App 2 dashboards render | | | |
| MHUB-001 | Access control not logged in | | | |
| MHUB-002 | No active models | | | |
| MHUB-003 | Load model and predict | | | |
| MHUB-004 | Bundle cached in session | | | |
| MHUB-005 | Admin bundle upload | | | |
| MHUB-006 | Oversized model rejected | | | |
| MHUB-007 | Invalid schema rejected | | | |
| MHUB-008 | Registry activate/deactivate | | | |
| MHUB-009 | Schema editor visual build | | | |
| MHUB-010 | Schema upload validate | | | |
| FEED-001 | Feedback form appears | | | |
| FEED-002 | Submit minimal feedback | | | |
| FEED-003 | Feedback with actual salary | | | |
| FEED-004 | Feedback deduplication | | | |
| FEED-005 | Extended feedback | | | |
| PROF-001 | Profile tab visibility | | | |
| PROF-002 | Prediction history displayed | | | |
| PROF-003 | View prediction inputs | | | |
| PROF-004 | Export history CSV | | | |
| PROF-005 | Export XLSX and JSON | | | |
| ADMN-001 | Admin access denied non-admin | | | |
| ADMN-002 | System diagnostics | | | |
| ADMN-003 | Feedback analytics load | | | |
| ADMN-004 | Recent feedback | | | |
| ADMN-005 | Clear cache | | | |
| ADMN-006 | Garbage collection | | | |
| PDF-001 | Manual PDF App 1 | | | |
| PDF-002 | Manual PDF App 2 | | | |
| PDF-003 | Resume analysis PDF | | | |
| PDF-004 | Batch prediction PDF | | | |
| PDF-005 | Scenario analysis PDF | | | |
| PDF-006 | Model analytics PDF | | | |
| PDF-007 | Page numbering | | | |
| PDF-008 | PDF persists after navigation | | | |
| INT-001 | Full pipeline App 1 | | | |
| INT-002 | Financial tool chain | | | |
| INT-003 | Model Hub upload to predict | | | |
| INT-004 | Rate limit cross-session | | | |
| INT-005 | Feedback in admin panel | | | |
| SEC-001 | Admin panel access control | | | |
| SEC-002 | Model Hub upload restricted | | | |
| SEC-003 | Rate limit PII protection | | | |
| SEC-004 | Session expiry | | | |
| SEC-005 | No passwords in Firestore | | | |
| SEC-006 | Account enumeration protection | | | |
| PERF-001 | Prediction response time | | | |
| PERF-002 | Batch prediction 1000 rows | | | |
| PERF-003 | PDF generation time | | | |
| PERF-004 | Analytics PDF cached | | | |
| PERF-005 | Currency rate fetch | | | |
| PERF-006 | Data insights render | | | |

---

*End of Testing Guide*
