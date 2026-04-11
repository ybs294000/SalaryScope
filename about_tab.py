"""
about_tab.py
------------
Renders the "About" tab for SalaryScope.

This module contains all static informational content about the application,
including:
- Overview and purpose of SalaryScope
- Model descriptions (Model 1 and Model 2)
- Features and modules
- Resume analysis details
- Scenario analysis and prediction workflow
- User account system and profile features
- Technologies used
- Tab guide and usage instructions
- Limitations and disclaimers

The content is UI-focused and self-contained, with no dependencies on model
logic or datasets. It is separated from the main app to improve readability,
maintainability, and modular structure.
"""
import streamlit as st

def render_about_tab():
    st.markdown("## :material/info: About SalaryScope")

    st.markdown(
        "SalaryScope is a web application that predicts salary based on factors like "
        "education, experience, job title, and location. "
        "It uses machine learning models to give an estimated salary along with some basic insights. "
        "The application supports manual input, resume-based prediction, and batch prediction. "
        "It is designed to help students and job seekers get a general idea of salary expectations. "
        "It also includes basic post-tax estimation and cost-of-living adjustments for better real-world context."
    )

    with st.expander(":material/widgets: Features & Modules"):

        col_ab1, col_ab2 = st.columns(2)

        with col_ab1:
            st.markdown("### Model 1 — General Salary (Random Forest)")
            st.markdown("""
    **Dataset:** [General Salary Dataset (Kaggle)](https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country)
    
    **Models:**
    - Random Forest Regressor (optimized via GridSearchCV) for salary prediction
    - HistGradientBoostingClassifier (optimized via GridSearchCV) for salary level classification
    - KMeans Clustering for career stage segmentation (Entry, Growth, Leadership)
    - Apriori Algorithm for association rule mining between career attributes and salary categories

    **Input Features:**
    - Age, Years of Experience, Education Level, Senior Position, Gender, Job Title, Country

    **Salary Level Output:**
    - Early Career Range (Low)
    - Professional Range (Medium)
    - Executive Range (High)

    **Career Stage Output:**
    - Entry Stage
    - Growth Stage
    - Leadership Stage

    **Features:**
    - Manual salary prediction with salary band and career stage classification
    - Pattern insight generation using association rule mining (education, experience, job group, salary level)
    - Salary negotiation tips tailored to experience, seniority, job title, and country
    - Career recommendations based on job group and experience category
    - Resume Analysis: upload a PDF resume to extract features using NLP (spaCy, PhraseMatcher) and predict salary automatically
    - Resume scoring system with experience, education, and skills breakdown (scored out of 100)
    - Detected skill extraction from resume text using a curated technical skill lexicon
    - Batch salary estimation with salary level and career stage assignment per record
    - Predicted vs Actual diagnostics
    - Prediction confidence interval based on residual standard deviation from model evaluation
    - Classification confusion matrix & feature importance
    - Career stage clustering analytics (PCA visualization, silhouette score, Davies-Bouldin score)
    - Association rule analytics (support, confidence, lift visualizations)
    - Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries, salary levels, and career stages, and run sensitivity sweeps across experience and education
    - Multi-format export (CSV, JSON, XLSX, SQL)
    - Google Drive public link upload
    - PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
    - Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
    - Currency conversion support (100+ currencies) with live exchange rates
    - Basic post-tax salary estimation based on country-level tax systems
    - Cost-of-living adjustment for cross-country salary comparison
    - Real-world salary interpretation using combined financial adjustments
            """)

        with col_ab2:
            st.markdown("### Model 2 — Data Science Salary (XGBoost)")
            st.markdown("""
    **Dataset:** [Data Science Salaries Dataset (Kaggle)](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)
    
    **Model:**
    - XGBoost Regressor with log-transformed target (`log1p(salary_in_usd)`)
    - Custom feature engineering on job titles (seniority, domain, management signals)
    - Interaction feature: experience level × job title domain

    **Input Features:**
    - Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

    **Features:**
    - Manual salary prediction with domain-aware smart insights and career recommendations
    - Resume Analysis: upload a PDF resume to extract features using NLP and predict salary automatically
    - Resume scoring system with experience, skills, and role relevance breakdown (scored out of 100)
    - Batch salary estimation
    - Feature importance
    - Predicted vs Actual diagnostics
    - Residual analysis
    - Prediction uncertainty distribution
    - Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries by experience level, company size, and work mode, and run sensitivity sweeps across experience levels and company sizes
    - Multi-format export (CSV, JSON, XLSX, SQL)
    - Google Drive public link upload
    - PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
    - Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
    - Currency conversion support (100+ currencies) with live exchange rates
    - Basic post-tax salary estimation based on country-level tax systems
    - Cost-of-living adjustment for cross-country salary comparison
    - Real-world salary interpretation using combined financial adjustments
            """)

        st.divider()

        st.markdown("### Resume Analysis")
        st.markdown("""
    - Available for both models
    - Upload a PDF resume to automatically extract structured features using NLP
    - Text extraction via `pdfplumber`; feature extraction via `spaCy` with `PhraseMatcher`
    - Detects years of experience (regex), education level (pattern matching), job title (phrase matching against allowed titles), country (named entity recognition), and seniority flag
    - Skill detection from a curated lexicon of 50+ technical skills across programming, ML, data, cloud, and tools
    - Resume scoring out of 100 across three dimensions: experience (up to 50), education (up to 35), and skills (up to 30)
    - Profile strength label: Basic, Moderate, or Strong
    - Extracted fields are fully editable before prediction
    - Salary prediction using the same models as manual prediction
    - Results include annual salary, salary level, career stage, association pattern insight, confidence interval, negotiation tips, and career recommendations
    - Supports currency conversion, basic tax estimation, and cost-of-living adjustment for extracted profiles
    - Provides basic real-world salary interpretation beyond raw model predictions
        """)

        st.divider()

        st.markdown("### Salary Adjustment & Global Insights")
        st.markdown("""
        - Basic currency conversion using live exchange rates with fallback support
        - Basic tax estimation using country-level effective tax models
        - Cost-of-living adjustment using global indices (US = 100 baseline)
        - Enables realistic salary comparison across countries using purchasing power (PPP)
        - Modular design — can be applied independently or combined
        """)

        st.divider()

        st.markdown("### Prediction Feedback")
        st.markdown("""
    - Available in the Manual Prediction tab for both models
    - Appears as a collapsible expander after a prediction is generated
    - Allows users to rate whether the prediction was accurate (Yes / Somewhat / No)
    - Allows users to indicate the direction of error (Too High / About Right / Too Low)
    - Star rating from 1 to 5 for overall prediction quality
    - Optional field to enter actual or expected salary in USD
    - Available to both logged-in and anonymous users
    - Feedback is stored in Firestore under a separate `feedback/` collection alongside the prediction inputs and predicted salary
    - Submission is one-time per prediction result within a session — the form is replaced by a confirmation message after submitting
        """)

        st.divider()

        st.markdown("### Scenario Analysis")
        st.markdown("""
    - Available for both models
    - Build up to 5 fully customisable named scenarios in a single session
    - Each scenario accepts the same inputs as manual prediction for the active model
    - Run all scenarios simultaneously with a single button click
    - Side-by-side comparison table showing predicted salary, salary level, career stage (Model 1) or experience level, company size, and work mode (Model 2) per scenario
    - Bar chart comparing predicted annual salary across all scenarios with dollar labels
    - Charts colored by salary level and career stage (Model 1), or by experience level, company size, and work mode (Model 2)
    - Salary confidence interval chart showing 95% lower and upper bounds per scenario (Model 1)
    - Experience vs Salary bubble scatter plot across scenarios (Model 1)
    - Sensitivity sweep: select a baseline scenario and simulate how salary changes across a continuous experience range 0–40 years (Model 1) or across all four experience levels (Model 2), with all other inputs held fixed
    - Education level sweep: see how predicted salary shifts across High School, Bachelor's, Master's, and PhD for a selected baseline scenario (Model 1)
    - Company size sweep: see how predicted salary changes across Small, Medium, and Large companies for a selected baseline scenario (Model 2)
    - Export scenario results in CSV, XLSX, or JSON format
        """)

        st.divider()

        st.markdown("### User Account System")
        st.markdown("""
    - Email and password registration and login via Firebase Authentication
    - User profile data stored in Firestore
    - Session management via Streamlit session state (per-browser, 24-hour expiry)
        """)

        st.divider()

        st.markdown("### User Profile")
        st.markdown("""
    - Prediction history stored per logged-in user in Firestore (model, inputs, salary, timestamp)
    - Summary dashboard: total predictions, average salary, latest prediction
    - Prediction history chart (scatter plot over time, colored by model)
    - Per-prediction input detail viewer
    - Export prediction history in CSV, XLSX, or JSON format
    - Profile tab visible only when logged in
        """)

        st.divider()

        st.markdown("### Shared System Features")
        st.markdown("""
    - Model switcher to toggle between both prediction systems
    - Unified dark professional theme across the entire application
    - Dynamic tab layout: Manual Prediction, Resume Analysis, Batch Prediction, Scenario Analysis, Model Analytics, Data Insights, Profile (logged-in only), About
    - ReportLab-based multi-page PDF reports with embedded charts
    - State-managed UI to prevent re-computation on interaction
    - Google Drive public link upload for batch files
    - Predictions saved to Firestore for logged-in users
    - Structured prediction feedback collected from all users (logged-in and anonymous) and stored in Firestore
        """)

        st.divider()

        st.markdown("### Technologies Used")
        st.markdown("""
    - Python
    - Streamlit
    - Pandas / NumPy
    - Scikit-learn (Random Forest, HistGradientBoostingClassifier, KMeans, PCA, GridSearchCV)
    - XGBoost
    - MLxtend (Apriori association rule mining)
    - spaCy (NLP for resume feature extraction)
    - pdfplumber (PDF text extraction)
    - Plotly / Matplotlib
    - ReportLab (PDF generation)
    - Firebase Authentication (user login and registration)
    - Firebase Admin SDK / Firestore (user data, prediction storage, and feedback storage)
    - Requests (Cloud file retrieval)
    - bcrypt (password hashing utility)
        """)

    with st.expander(":material/menu_book: Tab Guide"):
        st.markdown("""
**Manual Prediction**
- Enter your profile details and click Predict Salary to get an instant salary estimate.
- Model 1 shows salary level, career stage, association pattern insight, negotiation tips, and career recommendations.
- Model 2 shows domain-aware smart insights, negotiation tips, and career recommendations.
- After results are shown, expand the Feedback section at the bottom to rate the prediction accuracy.

**Resume Analysis**
- Upload a PDF resume and click Extract Resume Features to run NLP-based extraction.
- Review and edit the detected fields, then click Predict Salary from Resume.
- Results include a resume score, salary estimate, career stage, pattern insight, negotiation tips, and career recommendations.

**Batch Prediction**
- Upload a file (CSV, XLSX, JSON, or SQL) or paste a public Google Drive link to run predictions on multiple records at once.
- Download the sample file first to understand the required column format.
- After prediction, a batch analytics dashboard with charts and a salary leaderboard is displayed.
- Export results in your preferred format using the dropdown and download button.

**Scenario Analysis**
- Build up to 5 named scenarios using the same inputs as manual prediction.
- Click Run All Scenarios to generate predictions for every scenario simultaneously.
- Review the comparison table, salary charts, and confidence interval ranges.
- Use the sensitivity sweep section to simulate how salary changes as experience or education varies, with all other inputs held fixed for a chosen baseline scenario.
- Export scenario results in CSV, XLSX, or JSON format.

**Model Analytics**
- Explore the performance and internals of the active model.
- Includes accuracy metrics, model comparison charts, feature importance, residual diagnostics, and prediction uncertainty.
- Model 1 additionally shows classifier metrics, clustering analytics, and association rule mining visualizations.

**Data Insights**
- Explore the dataset used to train the active model.
- Includes salary distributions and comparisons by education, experience, country, job role, company size, and work mode.

**Profile**
- Visible only when logged in.
- Shows your prediction history, summary statistics, and a timeline chart.
- Allows export of your full prediction history in CSV, XLSX, or JSON format.

**About**
- Describes the application, its models, features, and technologies.
- Contains the Tab Guide, Usage Instructions, and Limitations for reference.
        """)

    with st.expander(":material/help: Usage Instructions"):
        st.markdown("""
**Getting Started**
- Select a prediction model from the dropdown at the top: Model 1 (Random Forest) for general salary prediction, or Model 2 (XGBoost) for data science roles.
- The active model applies across all tabs.

**Manual Prediction**
- Fill in all input fields in the Manual Prediction tab.
- Click **Predict Salary** to generate results.
- Scroll down to view salary level, career stage, pattern insight, negotiation tips, and recommendations.
- Click **Prepare PDF Report** to generate a downloadable summary, then click **Download** to save it.
- To share feedback on the prediction, expand the **Share Feedback on This Prediction** section at the bottom, fill in the fields, and click **Submit Feedback**. Login is not required.
- Optionally enable currency conversion, tax adjustment, and cost-of-living comparison to better understand real-world salary value.
- These adjustments are optional and intended for approximate comparison only.

**Resume Analysis**
- Switch to Model 1 using the model selector.
- Go to the Resume Analysis tab and upload a PDF resume.
- Click **Extract Resume Features** to run NLP extraction.
- Review and edit the detected fields if needed.
- Click **Predict Salary from Resume** to get results.
- Click **Prepare PDF Report** to generate a downloadable summary, then click **Download** to save it.
- After prediction, you can apply currency conversion, tax estimation, and cost-of-living adjustment for a more realistic interpretation of the predicted salary.

**Batch Prediction**
- Download the sample file from the left column to understand the required format.
- Upload your file or paste a public Google Drive sharing link in the middle column.
- Click **Run Batch Prediction** to process all records.
- Export results in your preferred format using the dropdown and download button.

**Scenario Analysis**
- Go to the Scenario Analysis tab after selecting your model.
- Each scenario is pre-filled with sensible defaults — rename it and adjust any inputs.
- Click **Add Scenario** to add more scenarios (up to 5) or **Remove** to delete one.
- Click **Run All Scenarios** to predict salaries for all scenarios at once.
- Scroll down to view the comparison table, salary charts, and sensitivity sweeps.
- Select a baseline scenario from the dropdown in the sweep section to simulate how salary responds to changes in experience or education while everything else stays fixed.
- Use the export dropdown and download button to save scenario results.

**Account (Optional)**
- Register or log in from the sidebar to save predictions.
- Logged-in users can view their full prediction history in the Profile tab.
- Sessions expire after 24 hours and require re-login.

**Google Drive Upload**
- Set the file sharing permission to "Anyone with the link can view" before pasting the link.
- Select the correct file format from the dropdown after pasting the link.
        """)

    with st.expander(":material/warning: Limitations"):
        st.markdown("""
    - The models are trained on limited datasets, so predictions may not always match real-world salaries.
    - Some job roles, countries, or inputs may not be fully covered in the dataset.
    - Resume analysis depends on text extraction and may not work properly for all resume formats.
    - Predictions are based on past data and do not consider current market trends or company-specific salaries.
    - Scenario Analysis results are generated by the same underlying model as manual prediction and carry the same limitations.
    - The results should be used only as an estimate, not as an exact salary value.
    - Feedback submitted anonymously cannot be linked to a specific user session and is stored as-is without any personal identifier.
    - Currency conversion uses publicly available exchange rates and may not reflect real-time market fluctuations or transaction rates.
    - Tax estimation is based on simplified models and approximate effective rates; it does not account for deductions, filing status, or local regulations.
    - Cost-of-living adjustments use country-level indices and may not accurately represent city-level variations or individual lifestyle differences.
    - Combined salary adjustments (tax, currency, cost of living) are indicative and should be interpreted as general estimates rather than precise financial outcomes.
        """)
