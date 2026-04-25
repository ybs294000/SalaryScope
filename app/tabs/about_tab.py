"""
about_tab.py
------------
Renders the "About" tab for SalaryScope.

Sections
--------
- Hero section: app name, tagline, key stat pills (incl. prediction modes), author info, links
- CTA buttons (easy to remove -- single block marked below)
- Quick-start guide (new users)
- Example prediction card (easy to remove -- single block marked below)
- Features & Modules expander
  - Model 1, Model 2, Model Hub, Resume Analysis,
    Salary Adjustment, Financial Planning Tools,
    Prediction Feedback, Scenario Analysis,
    User Account System, User Profile,
    Shared System Features, Technologies Used
- Model Performance Summary expander
- FAQ expander
- Privacy & Data Notice expander
- Tab Guide expander
- Usage Instructions expander
- Limitations expander
- Dataset Citations expander

The content is UI-focused and self-contained, with no dependencies on model
logic or datasets.
"""
import streamlit as st


# ---------------------------------------------------------------------------
# Shared formatting helpers
# ---------------------------------------------------------------------------

def _info_card(title: str, body: str, accent: str = "#4F8EF7") -> str:
    """Return an HTML info card string for st.markdown."""
    return (
        f'<div style="border-left:3px solid {accent};background:{accent}11;'
        f'border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:8px;">'
        f'<div style="font-size:0.75rem;font-weight:600;color:{accent};margin-bottom:3px;">{title}</div>'
        f'<div style="font-size:0.875rem;color:var(--text-main,#E2E8F0);">{body}</div>'
        f'</div>'
    )


def _inject_about_styles():
    """Inject styling for a more polished About tab layout."""
    st.markdown(
        """
        <style>
        .about-preview-shell {
            position: relative;
            overflow: hidden;
            border: 1px solid var(--border, #334155);
            border-radius: 12px;
            background: var(--bg-card, #1E293B);
            padding: 28px 32px 22px 32px;
            margin-bottom: 8px;
        }

        .about-preview-eyebrow {
            display: inline-block;
            margin-bottom: 14px;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border, #334155);
            background: rgba(79, 142, 247, 0.10);
            color: var(--text-muted, #94A3B8);
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .about-preview-title {
            font-size: clamp(2rem, 3vw, 3rem);
            line-height: 1.05;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.03em;
            margin: 0 0 10px 0;
        }

        .about-preview-title .accent {
            color: var(--primary, #4F8EF7);
        }

        .about-preview-subtitle {
            max-width: 760px;
            color: var(--text-main, #E2E8F0);
            font-size: 0.92rem;
            line-height: 1.72;
            margin-bottom: 18px;
        }

        .about-preview-pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 16px 0 22px 0;
        }

        .about-preview-pill {
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .about-preview-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 8px 0 20px 0;
        }

        .about-preview-stat {
            border: 1px solid var(--border, #334155);
            border-radius: 16px;
            background: var(--bg-input, #1B2230);
            padding: 14px 16px;
        }

        .about-preview-stat-kicker {
            color: var(--text-muted, #94A3B8);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }

        .about-preview-stat-value {
            color: #ffffff;
            font-size: 1.3rem;
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 4px;
        }

        .about-preview-stat-note {
            color: var(--text-muted, #94A3B8);
            font-size: 0.83rem;
            line-height: 1.45;
        }

        .about-preview-meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border, #334155);
        }

        .about-preview-meta-label {
            color: var(--text-muted, #94A3B8);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 4px;
        }

        .about-preview-meta-value {
            color: #f8fafc;
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .about-preview-links a {
            color: #7dd3fc;
            font-weight: 600;
            text-decoration: none;
            margin-right: 18px;
        }

        .about-preview-links a:hover {
            color: #bae6fd;
        }

        .about-preview-step {
            border: 1px solid var(--border, #334155);
            border-radius: 8px;
            padding: 18px 18px 16px 18px;
            background: var(--bg-card, #1E293B);
            min-height: 200px;
        }

        .about-preview-step-no {
            width: 38px;
            height: 38px;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.95rem;
            font-weight: 800;
            margin-bottom: 14px;
            color: #fff;
        }

        .about-preview-step-title {
            color: #f8fafc;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .about-preview-step-copy {
            color: #cbd5e1;
            font-size: 0.88rem;
            line-height: 1.65;
        }

        @media (max-width: 980px) {
            .about-preview-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 640px) {
            .about-preview-shell {
                padding: 22px 18px 18px 18px;
                border-radius: 12px;
            }

            .about-preview-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_about_tab():
    _inject_about_styles()

    # -----------------------------------------------------------------------
    # Hero section
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div class="about-preview-shell">
            <div class="about-preview-eyebrow">SalaryScope · Machine Learning + Decision Support</div>
            <div class="about-preview-title">
                Salary intelligence for <span class="accent">job seekers, analysts, and hiring teams</span>
            </div>
            <div class="about-preview-subtitle">
                SalaryScope turns profile inputs, resumes, uploaded datasets, and scenario changes
                into salary predictions with surrounding context. Instead of showing only a number,
                it layers in analytics, resume extraction, financial interpretation, Model Hub
                extensibility, and HR planning workflows so the app feels like a decision-support
                tool rather than a single-use estimator.
            </div>
            <div class="about-preview-pill-row">
                <span class="about-preview-pill" style="background:#1D4ED833;border:1px solid #3B82F6;color:#93C5FD;">v1.3.0</span>
                <span class="about-preview-pill" style="background:#065F4633;border:1px solid #10B981;color:#6EE7B7;">Python 3.13</span>
                <span class="about-preview-pill" style="background:#7F1D1D33;border:1px solid #EF4444;color:#FCA5A5;">Streamlit Cloud</span>
                <span class="about-preview-pill" style="background:#92400E33;border:1px solid #F59E0B;color:#FCD34D;">2 built-in models</span>
                <span class="about-preview-pill" style="background:#164E6333;border:1px solid #06B6D4;color:#67E8F9;">4 prediction modes</span>
                <span class="about-preview-pill" style="background:#4C1D9533;border:1px solid #8B5CF6;color:#C4B5FD;">Model Hub + HR Tools</span>
            </div>
            <div class="about-preview-grid">
                <div class="about-preview-stat">
                    <div class="about-preview-stat-kicker">Prediction Surface</div>
                    <div class="about-preview-stat-value">Manual, Resume, Batch, Scenario</div>
                    <div class="about-preview-stat-note">Multiple entry points for individual, bulk, and what-if exploration.</div>
                </div>
                <div class="about-preview-stat">
                    <div class="about-preview-stat-kicker">Built-In Engines</div>
                    <div class="about-preview-stat-value">General + Data Science</div>
                    <div class="about-preview-stat-note">Separate models support broad roles and DS/ML-specific compensation patterns.</div>
                </div>
                <div class="about-preview-stat">
                    <div class="about-preview-stat-kicker">Decision Support</div>
                    <div class="about-preview-stat-value">Analytics + Financial Context</div>
                    <div class="about-preview-stat-note">Currency, tax, CoL, planning utilities, diagnostics, and explainability in one flow.</div>
                </div>
                <div class="about-preview-stat">
                    <div class="about-preview-stat-kicker">Extensibility</div>
                    <div class="about-preview-stat-value">Model Hub + HR Tools</div>
                    <div class="about-preview-stat-note">Admins can add new bundles; hiring teams can benchmark, audit, and plan offers.</div>
                </div>
            </div>
            <div class="about-preview-meta">
                <div>
                    <div class="about-preview-meta-label">Author</div>
                    <div class="about-preview-meta-value">
                        Yash Shah &nbsp;&middot;&nbsp;
                        B.Tech Final Year, Computer Engineering &nbsp;&middot;&nbsp;
                        Gandhinagar Institute of Technology
                    </div>
                </div>
                <div class="about-preview-links">
                    <a href="https://github.com/ybs294000/salaryscope" target="_blank">GitHub</a>
                    <a href="mailto:yashbshah2004@gmail.com">Contact</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # Quick-start guide
    # -----------------------------------------------------------------------
    st.markdown("### Start Here")
    qs1, qs2, qs3 = st.columns(3)

    with qs1:
        st.markdown(
            '<div class="about-preview-step">'
            '<div class="about-preview-step-no" style="background:linear-gradient(135deg,#2563EB,#38BDF8);">1</div>'
            '<div class="about-preview-step-title">Choose the right engine first</div>'
            '<div class="about-preview-step-copy">'
            'Start with Model 1 for broader role coverage across general professions. '
            'Use Model 2 when the profile is clearly in data science, analytics, ML, or adjacent DS/AI roles.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    with qs2:
        st.markdown(
            '<div class="about-preview-step">'
            '<div class="about-preview-step-no" style="background:linear-gradient(135deg,#059669,#2DD4BF);">2</div>'
            '<div class="about-preview-step-title">Use the input mode that matches your task</div>'
            '<div class="about-preview-step-copy">'
            'Manual is fastest for one profile, Resume is best when a CV already exists, '
            'Batch is for dataset-scale runs, and Scenario is ideal when you want to compare changes side by side.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    with qs3:
        st.markdown(
            '<div class="about-preview-step">'
            '<div class="about-preview-step-no" style="background:linear-gradient(135deg,#D97706,#F59E0B);">3</div>'
            '<div class="about-preview-step-title">Read the number in context, not alone</div>'
            '<div class="about-preview-step-copy">'
            'The strongest experience comes from pairing the salary estimate with analytics, '
            'currency and tax interpretation, cost-of-living comparison, feedback, and where relevant, HR tools.'
            '</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    st.caption(
        "Login is optional for predictions. Accounts mainly unlock saved history and Model Hub access."
    )

    st.divider()

    # -----------------------------------------------------------------------
    # Features & Modules
    # -----------------------------------------------------------------------
    with st.expander(":material/widgets: Features & Modules"):

        col_ab1, col_ab2 = st.columns(2)

        with col_ab1:
            st.markdown("### Model 1 - General Salary (Random Forest)")
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
- Classification confusion matrix and feature importance
- Career stage clustering analytics (PCA visualization, silhouette score, Davies-Bouldin score)
- Association rule analytics (support, confidence, lift visualizations)
- Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries, salary levels, and career stages, and run sensitivity sweeps across experience and education
- Multi-format export (CSV, JSON, XLSX, SQL)
- Google Drive public link upload
- PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
- Shareable salary card: download a branded 1200x630 PNG image of the prediction after each result
- Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
- Currency conversion support (100+ currencies) with live exchange rates
- Basic post-tax salary estimation based on country-level tax systems
- Cost-of-living adjustment for cross-country salary comparison
- Real-world salary interpretation using combined financial adjustments
            """)

        with col_ab2:
            st.markdown("### Model 2 - Data Science Salary (XGBoost)")
            st.markdown("""
**Dataset:** [Data Science Salaries Dataset (Kaggle)](https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023)

**Model:**
- XGBoost Regressor with log-transformed target (`log1p(salary_in_usd)`)
- Custom feature engineering on job titles (seniority, domain, management signals)
- Interaction feature: experience level x job title domain

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
- Shareable salary card: download a branded 1200x630 PNG image of the prediction after each result
- Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
- Currency conversion support (100+ currencies) with live exchange rates
- Basic post-tax salary estimation based on country-level tax systems
- Cost-of-living adjustment for cross-country salary comparison
- Real-world salary interpretation using combined financial adjustments
            """)

        st.divider()

        st.markdown("### Model Hub")
        st.markdown("""
- Available to all logged-in users; upload and management controls are admin-only
- Two bundle formats supported: ONNX (model.onnx + columns.json, recommended) and Pickle (model.pkl + columns.pkl, legacy)
- ONNX bundles are loaded via onnxruntime with no arbitrary code execution on deserialisation
- Each upload creates a new versioned folder in a private HuggingFace dataset repo -- existing bundles are never overwritten
- A registry file (`models_registry.json`) tracks all uploaded models, their active status, and bundle format
- Model Card metadata (intended use, limitations, metrics, training data, authors, links) can be attached at upload time and is displayed before loading
- Users see a dropdown of active models, a Model Card panel, and four prediction modes after loading a bundle

**Four prediction modes per loaded model:**
- **Manual** - fill in schema fields and predict a single result, shown using the same styled result card as the rest of the application
- **Batch** - upload a CSV or XLSX file (up to 10,000 rows), run predictions across all rows, and download results as CSV or XLSX with an auto-generated distribution chart; uploading a new file clears previous results automatically
- **Resume** - upload a PDF resume; features are extracted using NLP and pre-filled into an editable form for review before prediction; includes a resume quality score panel; uploading a new PDF clears previous results automatically
- **Scenario** - define up to 5 named scenarios, edit inputs directly without a save step, run all scenarios simultaneously, and compare results in a table and bar chart; an optional sensitivity sweep simulates how the prediction changes as one field varies across a range

**Schema system:**
- `schema.json` defines the input fields, their types, and the Streamlit widget to use (slider, selectbox, number_input, text_input, checkbox)
- Optional `layout` key enables multi-column form rendering (2 or 3 columns) using per-field `row` and `col_span` keys
- Optional `result_label` key overrides the prediction result card label
- Optional `plots` key declares charts to render automatically in the appropriate mode (gauge, bar, horizontal bar, scatter, histogram, line)
- Optional `scenario_sweep` key configures a sensitivity sweep in Scenario mode (continuous range or discrete values)
- Optional `aliases.json` sidecar provides human-readable display labels for selectbox model values
- Optional per-bundle `skills.json` and `job_titles.json` lexicons override global extraction defaults for resume analysis; falls back to the shared app-level lexicons when not provided

**Admin capabilities:**
- Upload ONNX or Pickle bundles with optional model card metadata, aliases, and custom lexicons
- Activate, deactivate, or roll back models from the Registry Manager
- Build or validate schema.json using the visual Schema Editor with layout and result label settings
- Push a replacement schema.json or aliases.json to an existing bundle without re-uploading the model
        """)

        st.divider()

        st.markdown("### Resume Analysis")
        st.markdown("""
- Available for both built-in models (Model 1 and Model 2) and all Model Hub models
- Upload a PDF resume to automatically extract structured features using NLP
- Text extraction via `pdfplumber`; feature extraction via `spaCy` with `PhraseMatcher` for skills, NER for countries, and regex for experience years
- Extraction engine is data-driven: skill phrases, job title aliases, education patterns, and country aliases are loaded from JSON lexicons that can be extended without code changes
- Model Hub models can supply their own per-bundle lexicons (`skills.json`, `job_titles.json`) which override the shared global lexicons for that specific model
- Detected skill coverage spans programming languages, data science, ML/AI, data engineering, MLOps, cloud platforms, mechanical and civil engineering, electrical and electronics, aerospace, chemical and process engineering, energy and environment, pharmaceutical and drug development, biotechnology and life sciences, neuroscience, mathematics and statistics, and cybersecurity
- Resume scoring out of 100 across three dimensions: experience (up to 40), education (up to 30), and skills (up to 30)
- Profile strength label: Basic, Moderate, or Strong
- Extraction quality panel showing auto-extracted field count, fields needing review, and per-field provenance (which extractor matched, what value was found)
- Extracted fields are fully editable before prediction
- Uploading a new PDF or switching models clears previous extraction results automatically; an explicit Clear button is also provided
        """)

        st.divider()

        st.markdown("### Salary Adjustment & Global Insights")
        st.markdown("""
- Basic currency conversion using live exchange rates with fallback support
- Basic tax estimation using country-level effective tax models
- Cost-of-living adjustment using global indices (US = 100 baseline)
- Enables realistic salary comparison across countries using purchasing power (PPP)
- Modular design -- can be applied independently or combined
        """)

        st.divider()

        st.markdown("### Financial Planning Tools")
        st.markdown("""
- 11 modular, toggle-based tools that operate on the predicted salary
- Post-tax estimator, CTC breakdown, take-home estimator, savings potential, loan affordability, budget planner, investment growth estimator, emergency fund planner, lifestyle budget split, cost-of-living adjuster, and currency converter
- Each tool uses country-specific data sourced from Numbeo, OECD, World Bank, and government portals
- Results are approximate estimates intended for planning purposes, not financial advice
        """)

        st.divider()

        st.markdown("### HR & Employer Tools")
        st.markdown("""
- Dedicated tab for HR teams and hiring managers; available to all users
- Five compensation planning tools accessible via inner sub-tabs
- All tools use the currently active ML model for salary estimates
- Every tool exposes a collapsible HR override section: model estimate can be replaced with an internal reference value; override reason captured as free text and included in all CSV exports alongside the original model estimate
- Tab and each sub-tool are independently removable without affecting any other part of the application

**Hiring Budget Estimator**
- Input a role profile and headcount; model predicts salary for that profile
- Adjustable employer cost assumptions: benefits & PF (%), overhead (%), one-time recruiting cost per hire
- Summary metrics: model estimate, base salary used, total cost per hire, total budget for all openings
- Bar chart showing cost breakdown per hire; CSV export

**Salary Benchmarking Table**
- Select a job title and location; model generates predictions across all experience levels
- Results displayed in an editable `st.data_editor` table with HR Override, Band Min, Band Max, and Internal Notes columns
- Predictions cached by input parameters — grid recomputes only when inputs change
- Grouped bar chart comparing model estimate vs HR override vs band markers; CSV export

**Candidate Comparison**
- Compare expected salary for 2 to 5 candidates side by side
- Each candidate has independent profile inputs and an optional individual override (e.g. known candidate expectation or counter-offer)
- Salary spread across candidates flagged with a contextual note
- Side-by-side metrics and grouped bar chart; CSV export

**Offer Competitiveness Checker**
- Input a role profile and planned offer salary
- Plotly gauge chart comparing planned offer against model reference; tiered interpretive guidance (>20% below, 10–20% below, within 10%, above reference)
- Framed as comparison against model estimate, not a market claim, to reflect dataset limitations
- CSV export

**Team Compensation Audit**
- Upload a CSV of current team salaries using the provided sample template
- Vectorised batch predictions run once on upload; result cached in session state so threshold changes do not re-run inference
- Global percentage adjustment for systematic model offset (e.g. "our salaries typically run 15% above the model")
- Configurable underpaid and overpaid thresholds
- Scatter plot of current salary vs adjusted reference, delta histogram, flagged records table, full audit table in expander; CSV export
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
- Submission is one-time per prediction result within a session -- the form is replaced by a confirmation message after submitting
        """)

        st.divider()

        st.markdown("### Scenario Analysis")
        st.markdown("""
- Available for both built-in models and all Model Hub models
- Build up to 5 fully customisable named scenarios in a single session
- Each scenario accepts the same inputs as manual prediction for the active model
- Input fields are plain widgets -- no save step required before running; values are always current when Run All Scenarios is clicked
- Run all scenarios simultaneously with a single button click
- Side-by-side comparison table and horizontal bar chart showing predicted values per scenario
- For built-in Model 1: charts colored by salary level and career stage; salary confidence interval chart; experience vs salary bubble scatter; sensitivity sweep across 0-40 years experience; education level sweep across High School, Bachelor's, Master's, and PhD
- For built-in Model 2: charts colored by experience level, company size, and work mode; sensitivity sweep across four experience levels; company size sweep
- For Model Hub models: sweep field and mode (continuous range or discrete values) declared in schema.json via `scenario_sweep`
- Export scenario results in CSV format
        """)

        st.divider()

        st.markdown("### User Account System")
        st.markdown("""
- Email and password registration and login via Firebase Authentication
- Email verification required before full account access
- User profile data stored in Firestore
- Session management via Streamlit session state (per-browser, 24-hour expiry)
- Password policy aligned with NIST SP 800-63B: minimum 12 characters, uppercase, lowercase, digit, special character, no consecutive identical characters, common-password blocklist
- Two-layer rate limiting for all authentication actions (session-state layer + Firestore layer)
- Secure password reset via email (Firebase OOB code system)
- Account management: change password (with re-authentication), delete account (with confirmation)
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
- Model switcher to toggle between both built-in prediction systems
- Unified theme across the entire application with dynamic light/dark mode support
- Dynamic tab layout: Manual Prediction, Resume Analysis, Batch Prediction, Scenario Analysis, Model Analytics, Data Insights, Model Hub, HR Tools, Profile (logged-in only), About
- ReportLab-based multi-page PDF reports with embedded charts
- State-managed UI to prevent re-computation on interaction
- Google Drive public link upload for batch files
- Predictions saved to Firestore for logged-in users
- Structured prediction feedback collected from all users and stored in Firestore
- Shareable salary prediction card (Pillow-generated 1200x630 PNG) available after every Manual and Resume prediction
        """)

        st.divider()

        st.markdown("### Technologies Used")
        st.markdown("""
- Python 3.13
- Streamlit
- Pandas / NumPy
- Scikit-learn (Random Forest, HistGradientBoostingClassifier, KMeans, PCA, GridSearchCV)
- XGBoost
- MLxtend (Apriori association rule mining)
- spaCy (NLP for resume feature extraction -- PhraseMatcher, NER)
- pdfplumber (PDF text extraction)
- Plotly / Matplotlib
- ReportLab (PDF generation)
- SHAP (SHapley Additive exPlanations for Model 2 feature importance)
- Firebase Authentication (user login and registration)
- Firebase Admin SDK / Firestore (user data, prediction storage, and feedback storage)
- HuggingFace Hub SDK (model bundle storage and retrieval for Model Hub)
- joblib (model serialization and deserialization for pickle bundles)
- onnxruntime (ONNX model inference for Model Hub ONNX bundles)
- Requests (cloud file retrieval)
- bcrypt (password hashing utility)
- Babel (Unicode CLDR territory data for country resolution)
- Pillow (PIL) (salary prediction card image generation — PNG, 1200x630)
        """)

    # -----------------------------------------------------------------------
    # Model performance summary
    # -----------------------------------------------------------------------
    with st.expander(":material/analytics: Model Performance Summary"):
        st.caption(
            "Metrics are from held-out test sets evaluated during training. "
            "Real-world accuracy depends on how closely your profile matches the training data."
        )

        st.markdown("#### Model 1 - General Salary (Random Forest Regressor)")
        m1c1, m1c2, m1c3 = st.columns(3)
        m1c1.metric("Test R2", "0.964", help="Proportion of salary variance explained by the model.")
        m1c2.metric("MAE", "$4,927", help="Mean Absolute Error -- average prediction error in USD.")
        m1c3.metric("RMSE", "$9,761", help="Root Mean Squared Error in USD.")

        st.markdown("*Salary level classifier (HistGradientBoosting):*")
        cl1, cl2, cl3, cl4 = st.columns(4)
        cl1.metric("Accuracy", "96.6%")
        cl2.metric("Precision", "96.6%")
        cl3.metric("Recall", "96.6%")
        cl4.metric("F1 Score", "96.6%")

        st.divider()

        st.markdown("#### Model 2 - Data Science Salary (XGBoost)")
        st.caption("Trained on log-transformed target (log1p); metrics reported on the original USD scale.")
        m2c1, m2c2, m2c3 = st.columns(3)
        m2c1.metric("Test R2 (log scale)", "0.595", help="Proportion of log-salary variance explained.")
        m2c2.metric("MAE", "$35,913", help="Mean Absolute Error on the USD scale after inverse transform.")
        m2c3.metric("RMSE", "$48,774", help="Root Mean Squared Error on the USD scale.")

        st.markdown("""
**Model comparison context (Model 1):**

| Model | Test R2 | MAE |
|---|---|---|
| Linear Regression | 0.800 | $16,884 |
| Decision Tree | 0.862 | $13,974 |
| Gradient Boosting | 0.892 | $12,405 |
| XGBoost (GridSearchCV) | 0.960 | $5,862 |
| Random Forest (GridSearchCV) -- final | 0.964 | $4,927 |

**Model comparison context (Model 2):**

| Model | Test R2 | MAE |
|---|---|---|
| Linear Regression (raw) | 0.349 | $40,169 |
| Gradient Boosting (raw) | 0.399 | $38,921 |
| Random Forest (log) | 0.576 | $37,878 |
| XGBoost (log) | 0.594 | $37,668 |
| XGBoost (raw + engineered) -- final | 0.595 | $35,913 |
        """)

    # -----------------------------------------------------------------------
    # FAQ
    # -----------------------------------------------------------------------
    with st.expander(":material/help_center: Frequently Asked Questions"):

        st.markdown("**Which model should I use?**")
        st.markdown(
            "Use Model 1 (Random Forest) if you are a student, early-career professional, or work "
            "outside the data science field -- it covers a broad range of job titles and countries. "
            "Use Model 2 (XGBoost) if you are in a data science, ML, or AI role -- it was trained "
            "specifically on data science salaries and captures domain-specific signals like "
            "employment type, remote ratio, and company size."
        )

        st.divider()

        st.markdown("**Do I need to log in to use the app?**")
        st.markdown(
            "No. Manual Prediction, Resume Analysis, Batch Prediction, Scenario Analysis, "
            "Model Analytics, and Data Insights are all available without an account. "
            "Logging in lets you save your prediction history in the Profile tab and access "
            "the Model Hub. Prediction feedback can be submitted without logging in."
        )

        st.divider()

        st.markdown("**How accurate are the predictions?**")
        st.markdown(
            "Model 1 achieves a test R2 of 0.964 with a mean absolute error of about $4,900 on "
            "the training dataset. Model 2 achieves a test R2 of 0.595 with a mean absolute error "
            "of about $35,900. Both figures are measured on held-out test data and represent "
            "in-distribution accuracy -- predictions for unusual job roles, countries, or "
            "experience combinations outside the training data will be less reliable. "
            "See the Model Performance Summary above for full comparison tables."
        )

        st.divider()

        st.markdown("**Is my data stored? Is it private?**")
        st.markdown(
            "Prediction inputs are stored in Firestore only for logged-in users who have an "
            "active session. Anonymous users' inputs are not stored anywhere. "
            "Feedback submissions (accuracy rating, direction, star rating, optional actual salary) "
            "are stored in a separate Firestore collection and are not linked to any personal "
            "identifier for anonymous users. Uploaded PDF resumes are processed in memory and "
            "are never written to disk or stored on any server. "
            "See the Privacy and Data Notice below for full details."
        )

        st.divider()

        st.markdown("**What file formats does Batch Prediction accept?**")
        st.markdown(
            "CSV, XLSX, JSON, and SQL for the built-in models. "
            "CSV and XLSX for Model Hub batch prediction. "
            "Public Google Drive links (file shared as 'Anyone with the link can view') "
            "are also accepted for the built-in models. "
            "Download the sample file from the Batch Prediction tab to see the exact "
            "required column names for the active model."
        )

        st.divider()

        st.markdown("**My resume PDF did not extract correctly. What should I do?**")
        st.markdown(
            "The extraction engine works best on ATS-friendly, text-selectable PDFs -- "
            "the kind produced by word processors like Microsoft Word or Google Docs when exported to PDF. "
            "Scanned resumes, image-based PDFs, and heavily formatted documents with tables "
            "or multi-column layouts often extract poorly. "
            "If extraction fails or produces wrong values, all fields are editable before "
            "you click Predict -- you can correct any field manually."
        )

        st.divider()

        st.markdown("**Can I use the app for multiple countries or currencies?**")
        st.markdown(
            "Yes. Predictions are always produced in USD. The currency converter below the result "
            "supports 100+ currencies with live exchange rates and a local fallback. "
            "The cost-of-living adjuster lets you see what the USD salary is worth in a different "
            "country relative to the US baseline. Both tools are optional and independent."
        )

        st.divider()

        st.markdown("**What is the Model Hub and who can use it?**")
        st.markdown(
            "The Model Hub lets admins upload independently trained sklearn-compatible or ONNX models "
            "and serve them to all logged-in users without changing application code. "
            "Once a bundle is loaded, users get four prediction modes: Manual, Batch, Resume, and Scenario. "
            "Only admin accounts can upload bundles, manage the registry, or edit schemas. "
            "All logged-in users can run predictions."
        )

        st.divider()

        st.markdown("**How do I save my prediction results?**")
        st.markdown(
            "For built-in models, click Prepare PDF Report after a prediction to download a "
            "formatted PDF summary. You can also click Download Salary Card (PNG) to get a shareable "
            "image card of the result. Batch results and scenario results can be downloaded as "
            "CSV or XLSX. If you are logged in, all predictions are automatically saved to "
            "your prediction history in the Profile tab and can be exported from there."
        )

    # -----------------------------------------------------------------------
    # Privacy and data notice
    # -----------------------------------------------------------------------
    with st.expander(":material/shield: Privacy and Data Notice"):
        st.markdown("""
**What is stored and where**

| Data | Logged-in users | Anonymous users |
|---|---|---|
| Prediction inputs and results | Stored in Firestore (linked to your account) | Not stored |
| Prediction feedback | Stored in Firestore (no personal identifier) | Stored in Firestore (no personal identifier) |
| Uploaded PDF resumes | Processed in memory only -- never stored | Processed in memory only -- never stored |
| Uploaded batch files | Processed in memory only -- never stored | Processed in memory only -- never stored |
| Session data | Held in browser session state (24-hour expiry) | Held in browser session state (24-hour expiry) |
| Account credentials | Managed by Firebase Authentication -- passwords are never stored in plaintext | N/A |

**What is not done**

- Resume files are never uploaded to any server or third-party storage. Text is extracted in-memory and discarded after the session ends.
- Batch files are never persisted. They are read into memory, predictions are run, and the file is discarded.
- No advertising, tracking, or analytics cookies are used.
- Prediction inputs from anonymous users are not stored and cannot be retrieved.
- Feedback data is stored without any personal identifier for anonymous users -- it cannot be linked back to a specific person or session.

**Third-party services used**

- **Firebase Authentication and Firestore** -- account management and data storage (Google Cloud)
- **HuggingFace Dataset Repo** -- Model Hub bundle storage (private repo, token-gated)
- **ExchangeRate API** (open.er-api.com) -- live currency exchange rates; no personal data is sent

**Data retention**

- Prediction history is retained until the user deletes their account.
- Account deletion removes all Firestore records linked to the account.
- Feedback records do not contain personal identifiers and are retained for model improvement purposes.

> This notice is provided for transparency. SalaryScope is an academic project and is not a commercial product. For production deployments, additional data protection measures and formal privacy policies would be appropriate.
        """)

    # -----------------------------------------------------------------------
    # Tab Guide
    # -----------------------------------------------------------------------
    with st.expander(":material/menu_book: Tab Guide"):
        st.markdown("""
**Manual Prediction**
- Enter your profile details and click Predict Salary to get an instant salary estimate.
- Model 1 shows salary level, career stage, association pattern insight, negotiation tips, and career recommendations.
- Model 2 shows domain-aware smart insights, negotiation tips, and career recommendations.
- After results are shown, expand the Feedback section at the bottom to rate the prediction accuracy.

**Resume Analysis**
- Upload a PDF resume and click Extract to run NLP-based extraction.
- Edit any pre-filled field if needed, then click Predict Salary from Resume.
- Upload a new PDF at any time -- previous extraction results are cleared automatically.

**Batch Prediction**
- Upload a file (CSV, XLSX, JSON, or SQL) or paste a public Google Drive link to run predictions on multiple records at once.
- Download the sample file first to understand the required column format.
- After prediction, a batch analytics dashboard with charts and a salary leaderboard is displayed.
- Export results in your preferred format using the dropdown and download button.

**Scenario Analysis**
- Build up to 5 named scenarios using the same inputs as manual prediction.
- Edit inputs directly in each scenario panel -- no save step is needed.
- Click Run All Scenarios to generate predictions for every scenario simultaneously.
- Review the comparison table, salary charts, and confidence interval ranges.
- Use the sensitivity sweep section to simulate how salary changes as experience or education varies.

**Model Analytics**
- Explore the performance and internals of the active model.
- Includes accuracy metrics, model comparison charts, feature importance, residual diagnostics, and prediction uncertainty.
- Model 1 additionally shows classifier metrics, clustering analytics, and association rule mining visualizations.

**Data Insights**
- Explore the dataset used to train the active model.
- Includes salary distributions and comparisons by education, experience, country, job role, company size, and work mode.

**Model Hub**
- Requires login to access.
- Select a model from the dropdown to view its Model Card, then click Load Model to download the bundle.
- Four modes are available after loading: Manual (single prediction), Batch (file upload), Resume (PDF extraction), and Scenario (multi-scenario comparison).
- In each mode, uploading a new file or PDF clears previous results automatically; a Clear button is also available.
- Admins additionally see an Upload Bundle panel with fields for model card metadata, optional lexicons, and aliases; a Registry Manager for activating and deactivating models; and a Schema Editor for building or validating schema.json files.

**HR Tools**
- Five compensation planning tools for HR teams and hiring managers.
- Hiring Budget: enter a role profile and headcount to estimate total annual payroll cost; adjust benefits, overhead, and recruiting assumptions.
- Salary Benchmarking: select a role and location to generate a prediction grid across experience levels; edit the HR Override, Band Min, and Band Max columns directly in the table.
- Candidate Comparison: enter profiles for 2 to 5 candidates to compare expected salaries side by side; use the per-candidate override checkbox to substitute a known expectation.
- Offer Checker: enter a role profile and planned offer to see how it compares to the model estimate on a gauge chart.
- Team Audit: download the sample template, fill in your team's current salaries, and upload the CSV; predictions run once and are cached so adjusting thresholds is instant.
- All tools include a HR Override expander and a CSV export button.

**Profile**
- Visible only when logged in.
- Shows your prediction history, summary statistics, and a timeline chart.
- Allows export of your full prediction history in CSV, XLSX, or JSON format.

**About**
- Describes the application, its models, features, and technologies.
- Contains the Tab Guide, Usage Instructions, and Limitations for reference.
        """)

    # -----------------------------------------------------------------------
    # Usage Instructions
    # -----------------------------------------------------------------------
    with st.expander(":material/help: Usage Instructions"):
        st.markdown("""
**Getting Started**
- Select a prediction model from the dropdown at the top: Model 1 (Random Forest) for general salary prediction, or Model 2 (XGBoost) for data science roles.
- The active model applies across all tabs except Model Hub, which has its own independent model selector.

**Manual Prediction**
- Fill in all input fields in the Manual Prediction tab.
- Click **Predict Salary** to generate results.
- Scroll down to view salary level, career stage, pattern insight, negotiation tips, and recommendations.
- Click **Prepare PDF Report** to generate a downloadable summary, then click **Download** to save it.
- Click **Download Salary Card (PNG)** to download a shareable image of your prediction result.
- To share feedback, expand the **Share Feedback on This Prediction** section, fill in the fields, and click **Submit Feedback**. Login is not required.
- Optionally enable currency conversion, tax adjustment, and cost-of-living comparison for real-world context.

**Resume Analysis**
- Go to the Resume Analysis tab and upload a PDF resume.
- Click **Extract** (or **Extract Resume Features** in the built-in tab) to run NLP extraction.
- Review the extraction quality panel and edit any pre-filled field if the extracted value looks wrong.
- Click **Predict Salary from Resume** to get results.
- Upload a new PDF at any time to restart -- previous results clear automatically.
- After prediction, you can apply currency conversion, tax estimation, and cost-of-living adjustment.
- A salary card download button is available below the prediction result.

**Batch Prediction**
- Download the sample file from the left column to understand the required format.
- Upload your file or paste a public Google Drive sharing link.
- Click **Run Batch Prediction** (or **Run** in the Model Hub batch mode) to process all records.
- Export results in your preferred format using the download buttons.

**Scenario Analysis**
- Go to the Scenario Analysis tab after selecting your model.
- Each scenario panel shows all input fields -- edit them directly, no save step needed.
- Click **Add Scenario** to add more (up to 5) or **Remove** to delete one.
- Click **Run All Scenarios** to predict salaries for all scenarios at once.
- Scroll down to view the comparison table, salary charts, and sensitivity sweeps.
- Use the export button to save scenario results as CSV.

**Model Hub**
- Log in first -- the tab requires authentication.
- Select a model from the dropdown and review the Model Card for information about the model.
- Click **Load Model** to download the bundle from HuggingFace. This only needs to be done once per session.
- Choose a prediction mode from the tabs: Manual, Batch, Resume, or Scenario.
- In Batch mode, upload a CSV or XLSX file whose columns match the schema field names shown in the guide, then click **Run**. Click **Clear** to reset between uploads.
- In Resume mode, upload a PDF and click **Extract**. Review and edit the extracted fields, then click **Predict from Resume**. Click **Clear** to reset between resumes.
- In Scenario mode, fill in each scenario panel directly and click **Run All Scenarios**.
- If you are an admin, the Upload Bundle, Registry Manager, and Schema Editor sections are visible below the prediction panel.

**HR Tools**
- Open the HR Tools tab and select a tool from the inner sub-tabs.
- **Hiring Budget**: fill in the role profile and headcount, then adjust the employer cost assumptions (benefits %, overhead %, recruiting cost). The budget summary and chart update automatically.
- **Salary Benchmarking**: select a job title and location; the prediction grid loads automatically. Edit the HR Override, Band Min, Band Max, and Internal Notes columns directly in the table. Download the result as CSV.
- **Candidate Comparison**: set the number of candidates, fill in each profile column, and optionally check Apply Override per candidate to enter a known expectation. The comparison chart updates as you edit.
- **Offer Checker**: fill in the role profile. The model estimate appears below the form. Enter your planned offer in the Planned Offer field; the gauge chart and guidance update immediately.
- **Team Audit**: download the sample CSV template first. Fill it in with your team's current salaries and upload the file. Predictions run once. Use the Global Model Adjustment and threshold sliders to calibrate the analysis — these do not re-run the model. Download the full audit CSV.
- Use the HR Override expander in any tool to substitute the model estimate with your own internal reference value and record the reason.

**Account (Optional)**
- Register or log in from the sidebar to save predictions.
- Logged-in users can view their full prediction history in the Profile tab.
- Sessions expire after 24 hours and require re-login.

**Google Drive Upload**
- Set the file sharing permission to "Anyone with the link can view" before pasting the link.
- Select the correct file format from the dropdown after pasting the link.
        """)

    # -----------------------------------------------------------------------
    # Limitations
    # -----------------------------------------------------------------------
    with st.expander(":material/warning: Limitations"):
        st.markdown("""
- The models are trained on limited datasets, so predictions may not always match real-world salaries.
- Some job roles, countries, or inputs may not be fully covered in the dataset.
- Resume analysis depends on text extraction quality and may not work properly for image-based, scanned, or heavily formatted PDFs. ATS-friendly, text-selectable PDFs extract best.
- Extraction heuristics (experience years, education level, country, job title) are rule-based and may miss edge cases in unconventional resume layouts.
- Predictions are based on past data and do not consider current market trends or company-specific salaries.
- Scenario Analysis results are generated by the same underlying model as manual prediction and carry the same limitations.
- The results should be used only as an estimate, not as an exact salary value.
- Feedback submitted anonymously cannot be linked to a specific user session and is stored as-is without any personal identifier.
- Currency conversion uses publicly available exchange rates and may not reflect real-time market fluctuations or transaction rates.
- Tax estimation is based on simplified models and approximate effective rates; it does not account for deductions, filing status, or local regulations.
- Cost-of-living adjustments use country-level indices and may not accurately represent city-level variations or individual lifestyle differences.
- Combined salary adjustments (tax, currency, cost of living) are indicative and should be interpreted as general estimates rather than precise financial outcomes.
- Model Hub ONNX bundles (model.onnx) are loaded via onnxruntime and carry no arbitrary code execution risk. Pickle bundles (model.pkl) are deserialized using joblib -- only upload pickle files from sources you control entirely.
- Model Hub predictions are only as reliable as the model and training data used -- the system does not validate model quality or dataset coverage.
- Per-bundle lexicons (skills.json, job_titles.json) in the Model Hub override global lexicons for resume extraction; if not uploaded, the shared app-level lexicons are used as fallback.
        """)

    # -----------------------------------------------------------------------
    # Dataset citations
    # -----------------------------------------------------------------------
    with st.expander(":material/dataset: Dataset Citations"):
        st.markdown("""
**Model 1 - General Salary Dataset**

> Abbootalebi, A. M. (2023). *Salary by Job Title and Country*. Kaggle.
> https://www.kaggle.com/datasets/amirmahdiabbootalebi/salary-by-job-title-and-country

- Covers a broad range of job titles, countries, education levels, and experience bands
- Used to train the Random Forest Regressor, HistGradientBoosting salary level classifier, KMeans career stage model, and Apriori association rule miner

---

**Model 2 - Data Science Salaries Dataset**

> Chaki, A. (2023). *Data Science Salaries 2023*. Kaggle.
> https://www.kaggle.com/datasets/arnabchaki/data-science-salaries-2023

- Covers data science and AI/ML roles across experience levels, employment types, company sizes, and locations
- Used to train the XGBoost Regressor with log-transformed target and engineered job title features

---

**Exchange Rates**

> Open Exchange Rates. *ExchangeRate-API*. https://open.er-api.com
> No API key required. Rates are cached in memory and refreshed periodically during a session.

---

**Cost-of-Living Indices**

> Numbeo. *Cost of Living Index by Country*. https://www.numbeo.com/cost-of-living/
> OECD. *Purchasing Power Parities*. https://data.oecd.org/price/purchasing-power-parities-ppp.htm

Values are used as approximate relative indices for cross-country salary comparison. They are periodically updated in the application and may not reflect current real-time conditions.

---

**Tax Rate Data**

> OECD. *Taxing Wages*. https://www.oecd.org/tax/taxing-wages-20725124.htm
> Various national government tax authority publications (2023/24 fiscal year).

Effective rates are approximate and used for indicative post-tax estimation only.
        """)