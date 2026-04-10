# SalaryScope — User Guide

> **Version 1.0 · April 2026**  
> A complete guide to using every feature of SalaryScope.

---

## Welcome to SalaryScope

SalaryScope is a salary prediction tool powered by machine learning. It estimates annual salaries based on professional attributes, lets you upload a resume for automatic extraction, analyze multiple scenarios, and understand predictions in real-world financial context.

No installation is required. Open your browser and go to:

- **Full App**: https://salaryscope-app.streamlit.app/
- **Lite App** (no resume feature): https://salaryscope-lite-app.streamlit.app/

---

## Quick Start (30 seconds)

1. Open the app in your browser
2. From the **model dropdown at the top**, choose Model 1 (general roles) or Model 2 (data science roles)
3. Go to the **Manual Prediction** tab
4. Fill in your details and click **Predict Salary**
5. Your estimated annual salary appears instantly

---

## Choosing a Model

At the very top of the page, you will see a dropdown labeled **Select Prediction Model**.

| Model | Best For | Algorithm |
|---|---|---|
| **Model 1 — General Salary** | Any industry: finance, engineering, healthcare, management, etc. | Random Forest |
| **Model 2 — Data Science Salary** | Data science, ML, AI, data engineering, BI, analytics roles | XGBoost |

Your model selection applies across all tabs. You can switch models at any time.

---

## Tab Overview

| Tab | What You Can Do |
|---|---|
| **Manual Prediction** | Enter your details and get an instant salary estimate |
| **Resume Analysis** | Upload a PDF resume and auto-extract your details for prediction |
| **Batch Prediction** | Upload a file with many records and predict salaries in bulk |
| **Scenario Analysis** | Compare up to 5 different career profiles side-by-side |
| **Model Analytics** | Explore model performance, accuracy metrics, and feature importance |
| **Data Insights** | Explore the training dataset used by each model |
| **Profile** | View your prediction history (login required) |
| **About** | Learn about the system, its features, and its limitations |

---

## Manual Prediction

### Step-by-Step

**Model 1 inputs:**
- **Age** — your current age
- **Years of Experience** — total professional experience in years
- **Education Level** — select from High School, Bachelor's, Master's, or PhD
- **Senior Position** — toggle on if your role is a senior-level position
- **Gender** — select your gender
- **Job Title** — type or select your job title from the dropdown
- **Country** — select your country of employment

**Model 2 inputs:**
- **Experience Level** — Entry, Mid, Senior, or Executive
- **Employment Type** — Full-time, Part-time, Contract, or Freelance
- **Job Title** — your data science role title
- **Employee Residence** — your country of residence
- **Work Mode** — Onsite (0%), Hybrid (50%), or Remote (100%)
- **Company Location** — country where the company is based
- **Company Size** — Small, Medium, or Large

Once you have filled in all fields, click **Predict Salary**.

### Understanding the Results

After prediction, you will see:

- **Predicted Annual Salary** (in USD) — the model's estimate
- **Salary Breakdown** — monthly, weekly, and hourly equivalents
- **Salary Level** *(Model 1)* — Early Career Range / Professional Range / Executive Range
- **Career Stage** *(Model 1)* — Entry Stage / Growth Stage / Leadership Stage
- **Pattern Insight** *(Model 1)* — a data-derived observation about your profile
- **Confidence Interval** *(Model 1)* — the 95% lower and upper bounds of the estimate
- **Negotiation Tips** — practical tips for salary negotiation given your profile
- **Career Recommendations** — suggested next steps based on your predicted outcome

### Currency Conversion

Below the prediction result, you can toggle **Currency Conversion** to convert your salary to any of 100+ global currencies. The conversion shows annual, monthly, weekly, and hourly equivalents in the selected currency.

> The default currency is auto-selected based on your country input.

### Post-Tax Estimation

Toggle **Tax Adjustment** to estimate your approximate take-home salary after income tax. The system uses country-specific effective tax rates. You can also enter a custom effective rate if you know your actual tax situation.

> Tax estimates are approximate and do not account for specific deductions or local rules.

### Cost of Living Adjustment

Toggle **Cost of Living Adjustment** to normalize the salary for purchasing power in your country relative to a global baseline. This helps you compare salaries across countries in terms of real-world affordability.

### Downloading a PDF Report

1. Click **Prepare PDF Report** (a brief computation runs)
2. Once ready, a **Download** button appears — click it to save your report

The report includes your inputs, prediction results, insights, and charts.

### Submitting Feedback

After seeing your prediction result, an expandable section **Share Feedback on This Prediction** appears at the bottom of the page. You can:

- Rate whether the prediction was accurate (Yes / Somewhat / No)
- Indicate if the salary seemed too high, about right, or too low
- Give a star rating (1–5)
- Optionally enter your actual or expected salary

Feedback helps improve the models over time. Login is not required.

---

## Resume Analysis

> Available in the Full App only (https://salaryscope-app.streamlit.app/)

### Step-by-Step

1. Go to the **Resume Analysis** tab
2. Click **Browse files** and upload your resume in **PDF format**
3. Click **Extract Resume Features**
4. The system will automatically extract:
   - Job Title
   - Years of Experience
   - Skills (from a vocabulary of 200+ technical skills)
   - Education Level
   - Country
5. **Review the extracted fields** — they appear in editable form controls. Correct any errors you notice.
6. Your **Resume Score** (0–100) is displayed, based on your experience, education, and skills breadth.
7. Click **Predict Salary from Resume** to run the prediction.
8. Results are identical in format to the Manual Prediction tab.
9. Click **Prepare PDF Report** then **Download** to export the result.

### Tips for Better Extraction

- Use a standard, text-based PDF resume (not a scanned image)
- Make sure years of experience are mentioned explicitly (e.g., "5 years of experience")
- Degree names should be spelled out (e.g., "Bachelor of Science", "Master of Technology")
- Country name should appear at least once in the resume (address, location, or header)

---

## Batch Prediction

Batch prediction lets you run predictions on many profiles at once — useful for HR teams, researchers, or anyone with a dataset.

### Preparing Your File

1. In the **Batch Prediction** tab, click **Download Sample File** to get the correct column format for the active model
2. Populate your file following the same column names and value formats as the sample
3. Supported formats: **CSV, XLSX, JSON, SQL**
4. Maximum rows: **50,000**

### Uploading and Running

**Option A — Direct upload**: Click **Browse files** and select your prepared file.

**Option B — Google Drive link**:
1. Upload your file to Google Drive
2. Set sharing to **"Anyone with the link can view"**
3. Copy the sharing link
4. Paste the link into the Google Drive URL field
5. Select the correct file format from the dropdown

Once uploaded, click **Run Batch Prediction**.

### After Prediction

An analytics dashboard appears with:
- Salary distribution chart
- Summary statistics by category
- A salary leaderboard (top predicted salaries in the dataset)

Use the **Export** dropdown to select your preferred format (CSV, XLSX, JSON, SQL) and click **Download Results**.

You can also click **Download Batch PDF Report** for a formatted multi-page analytics report.

---

## Scenario Analysis

Scenario Analysis lets you compare up to 5 different professional profiles to see how salary changes across different attributes.

### Setting Up Scenarios

1. Go to the **Scenario Analysis** tab
2. Each scenario card has a **Name** field and the same input fields as Manual Prediction
3. All scenarios start with sensible default values — rename them and adjust as needed
4. Click **Add Scenario** to add up to 5 scenarios
5. Click **Remove** on a scenario card to delete it

### Running Scenarios

Click **Run All Scenarios** to generate predictions for every scenario simultaneously.

### Viewing Results

- **Comparison Table**: Predicted salary and key attributes for each scenario side-by-side
- **Salary Bar Chart**: Visual comparison of predicted annual salaries across all scenarios
- **Confidence Interval Chart** *(Model 1)*: 95% lower and upper bounds per scenario
- **Experience vs. Salary Bubble Chart** *(Model 1)*: Position of each scenario on an experience-salary plot

### Sensitivity Sweep

The sensitivity sweep shows how salary changes as a single variable shifts while everything else stays fixed.

1. Select a **Baseline Scenario** from the dropdown
2. The sweep automatically simulates:
   - **Model 1**: Salary across 0–40 years of experience (continuous), and salary across all four education levels
   - **Model 2**: Salary across all four experience levels, and salary across Small/Medium/Large company sizes
3. The chart shows how sensitive the model's salary prediction is to each variable

### Exporting Scenarios

Use the **Export** dropdown (CSV / XLSX / JSON) and click **Download** to save scenario results.

---

## Model Analytics

The **Model Analytics** tab lets you inspect the inner workings and performance of the active model.

### What's Available

**Both Models**:
- Regression performance metrics: R², MAE, RMSE
- Model comparison table and bar chart
- Feature importance chart
- Predicted vs. Actual salary scatter plot
- Residual distribution chart
- Prediction uncertainty distribution

**Model 1 Only**:
- Confusion matrix for the salary level classifier
- Classification model comparison
- Career stage cluster chart with PCA visualization
- Association rule analytics (support, confidence, lift values)

**Model 2 Only**:
- SHAP-based grouped feature importance (shows which features most influence predictions)

You can download a full **PDF Model Analytics Report** from this tab.

---

## Data Insights

The **Data Insights** tab lets you explore the training data that each model was built on.

Available views include salary distributions by education level, years of experience, seniority, country, and job title. Charts include trend lines and box plots for exploratory comparison.

This tab is useful for understanding the coverage and biases of the training data before interpreting a prediction.

---

## Your Account (Optional)

### Why Create an Account?

- Your predictions are saved to your personal history
- You can view and export your full prediction history from the **Profile** tab
- Sessions are remembered for 24 hours

### Registering

In the **sidebar** (left panel), click **Register**. Enter your name, email, and password. Your account is created instantly via Firebase Authentication.

### Logging In

In the sidebar, click **Login** and enter your email and password.

### Profile Tab

Once logged in, go to the **Profile** tab to see:
- Total predictions made
- Your average predicted salary
- Your most recent prediction
- A timeline chart of all your predictions
- A detailed view of each prediction's inputs
- Export buttons for CSV, XLSX, or JSON

### Session Expiry

Sessions expire after 24 hours. You will be logged out automatically and asked to log in again.

---

## Frequently Asked Questions

**Q: Is login required to use the app?**  
No. All core features (Manual Prediction, Resume Analysis, Batch, Scenario, Analytics, Data Insights) are fully available without an account. Login is only needed to save and revisit your prediction history.

**Q: Why does the salary seem too high or too low?**  
The models are trained on historical datasets and may not fully reflect current market conditions, specific company policies, or geographic nuances within a country. Use the result as a reference, not an exact figure. You can submit feedback using the feedback form after prediction.

**Q: Can I upload a Word document or image as my resume?**  
No. The resume parser only supports standard text-based PDF files. Scanned image PDFs, Word documents, and other formats are not supported. If your resume is a scanned image, you will need to enter the details manually.

**Q: Why is Model 2's salary estimate less accurate than Model 1?**  
Data science salaries vary enormously based on factors like company funding stage, specific technical skills, stock equity, and city-level cost of living — many of which are not captured in the training dataset. This makes the prediction range wider and less precise compared to the general model.

**Q: Is my uploaded resume stored?**  
No. Uploaded resume files are processed in memory and are not stored anywhere. Only prediction inputs and results (for logged-in users) are saved to Firestore.

**Q: Are currency conversions real-time?**  
Exchange rates are fetched from a public API (`open.er-api.com`) and cached for approximately 60 minutes. They are close to real-time but may not reflect live trading rates. If the API is unavailable, a fallback rate file is used.

**Q: Can I use this for salary negotiation?**  
The results can serve as a data-backed reference point for negotiation conversations, but they should be supplemented with market research, industry benchmarks, and knowledge of your specific employer.

---

## Limitations Summary

- Predictions are based on historical datasets and may not reflect current market trends.
- Some niche job titles, countries, or role combinations may have limited training data coverage.
- Resume extraction depends on text quality and may not work on all resume layouts.
- Tax, COL, and currency adjustments are approximate and intended for comparison only.
- Confidence intervals (Model 1) are estimates based on training residuals, not guaranteed bounds.

---

*SalaryScope — Built with Streamlit · Powered by Firebase · Deployed on Streamlit Community Cloud*  
*Author: Yash Shah · Gandhinagar Institute of Technology*
