"""
feedback.py — Prediction Feedback System for SalaryScope
=========================================================
Provides:
  - save_feedback()  : persists a feedback record to Firestore
  - feedback_ui()    : renders a collapsible feedback form in Streamlit

Firestore path:  feedback/{auto-id}
Completely separate from the predictions/ collection.

ROLLBACK GUIDE
--------------
Three independent rollback layers. Each is marked with matching comment pairs.

  Layer 3 — ORIGINAL FORM (accuracy, direction, stars, actual salary)
    The unchanged original code. Never remove this.

  Layer 1 — EXTENDED DATA (general enrichment fields)
    Markers: # << EXTENDED DATA BLOCK START / END >>
    To remove entirely:
      - Delete the `extended` parameter from save_feedback() (marked).
      - Delete the `if extended: record[...] = extended` block (marked).
      - Delete _collect_extended_data() and all module-level _*_OPTIONS constants.
      - Delete the `extended = _collect_extended_data(...)` line in feedback_ui().
      - Delete the `extended=extended` kwarg in the save_feedback() call.

  Layer 2 — CROSS-DATASET BRIDGE FIELDS (DS1 <-> DS2)
    Markers: # << CROSS-DATASET BLOCK START / END >>
    To remove Layer 2 while keeping Layer 1:
      - Delete _collect_cross_dataset_fields() and its constants
        (_EDUCATION_LABELS, _EMPLOYMENT_TYPE_OPTIONS, _REMOTE_RATIO_OPTIONS,
         _COMPANY_SIZE_OPTIONS, _ISO2_COUNTRIES, _is_app1_model, _is_app2_model).
      - Delete the single call line inside _collect_extended_data() (marked).
    Layer 1 remains fully intact.

COMBINED DATASET SCHEMA (what ends up in Firestore)
----------------------------------------------------
Core record (always present — unchanged from original):
  username, model_used, input_data (JSON string), predicted_salary,
  accuracy_rating, direction, actual_salary, star_rating, created_at

extended_data (nested dict; absent if user skipped everything):

  Cross-dataset bridge — DS1 -> DS2  (present when model = XGBoost):
    age               int        18-80
    education_level   int        0=High School, 1=Bachelor, 2=Master, 3=PhD
    is_senior         int        0 or 1
    gender            str        Male / Female / Non-binary / Other

  Cross-dataset bridge — DS2 -> DS1  (present when model = Random Forest):
    employment_type   str        FT / PT / CT / FL  (DS2 raw codes)
    remote_ratio      int        0 / 50 / 100       (DS2 raw values)
    company_size      str        S / M / L           (DS2 raw codes)
    company_location  str        ISO-2 country code  (DS2 raw format)

  General enrichment (both models):
    compensation_type, actual_base_usd, actual_total_comp_usd,
    offer_determination, skills (list), years_primary_skill,
    certifications (list), industry, company_type, company_age_years,
    immediate_team_size, direct_reports, years_current_company,
    total_employers, hours_per_week, city_tier, work_authorisation,
    additional_context
"""

import streamlit as st
import json
from datetime import datetime


# ------------------------------------------------------------------
# FIRESTORE HELPER
# ------------------------------------------------------------------

def _db():
    from database import _get_firestore_client
    return _get_firestore_client()


# ------------------------------------------------------------------
# SAVE FEEDBACK
# ------------------------------------------------------------------

def save_feedback(
    username: str,
    model_used: str,
    input_data: dict,
    predicted_salary: float,
    accuracy_rating: str,
    direction: str,
    actual_salary: float | None,
    star_rating: int,
    # << EXTENDED DATA BLOCK START — remove this parameter to roll back Layer 1 >>
    extended: dict | None = None,
    # << EXTENDED DATA BLOCK END >>
):
    """
    Write one feedback document to Firestore.
    `extended` is optional; absent keys produce no Firestore field.
    """
    db = _db()

    record = {
        "username":         username or "anonymous",
        "model_used":       model_used,
        "input_data":       json.dumps(input_data),
        "predicted_salary": predicted_salary,
        "accuracy_rating":  accuracy_rating,
        "direction":        direction,
        "actual_salary":    actual_salary,
        "star_rating":      star_rating,
        "created_at":       datetime.utcnow().isoformat(),
    }

    # << EXTENDED DATA BLOCK START — remove to roll back Layer 1 >>
    if extended:
        record["extended_data"] = extended
    # << EXTENDED DATA BLOCK END >>

    db.collection("feedback").add(record)


# ==================================================================
# OPTION LISTS  (module-level so they are defined once)
# << EXTENDED DATA BLOCK START — remove all constants to roll back Layer 1 >>
# ==================================================================

_SKILL_OPTIONS = [
    # Programming languages
    "Python", "R", "SQL", "Java", "JavaScript", "TypeScript",
    "C", "C++", "C#", "Go", "Rust", "Scala", "MATLAB", "Julia",
    "Bash / Shell", "Swift", "Kotlin", "PHP", "Ruby",
    # Data / ML / AI
    "Machine Learning", "Deep Learning", "NLP",
    "Computer Vision", "Reinforcement Learning", "Time Series Analysis",
    "Statistical Modelling", "Data Engineering", "Data Visualisation",
    "Feature Engineering", "Model Deployment / MLOps",
    # Frameworks / platforms
    "TensorFlow", "PyTorch", "Scikit-learn", "XGBoost / LightGBM",
    "Hugging Face", "LangChain", "Spark / PySpark", "Hadoop",
    "Kafka", "Airflow", "dbt", "Databricks",
    "AWS", "Google Cloud (GCP)", "Microsoft Azure",
    "Docker", "Kubernetes", "Terraform", "CI/CD",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Snowflake", "BigQuery", "Redshift", "Elasticsearch",
    # Visualisation / BI
    "Tableau", "Power BI", "Looker", "Excel / VBA",
    "Matplotlib / Seaborn / Plotly",
    # Domain / soft
    "Project Management", "Agile / Scrum", "Product Management",
    "Business Analysis", "Finance / Accounting",
    "Healthcare / Clinical", "Legal / Compliance",
    "Marketing Analytics", "Supply Chain", "CRM / Salesforce",
]

_INDUSTRY_OPTIONS = [
    "Technology / Software",
    "Financial Services / Banking",
    "Healthcare / Pharmaceuticals / Biotech",
    "E-Commerce / Retail",
    "Consulting / Professional Services",
    "Telecommunications",
    "Media / Entertainment / Gaming",
    "Manufacturing / Engineering",
    "Energy / Oil & Gas / Utilities",
    "Government / Public Sector",
    "Education / Research / Academia",
    "Non-Profit / NGO",
    "Real Estate / Construction",
    "Transport / Logistics / Aerospace",
    "Agriculture / Food",
    "Other",
]

_COMPANY_TYPE_OPTIONS = [
    "Public (listed company)",
    "Private (VC / PE backed)",
    "Private (bootstrapped / SME)",
    "Startup (< 2 years old)",
    "Government / Public sector",
    "Non-profit / NGO",
    "Academic / Research institution",
    "Self-employed / Freelance",
    "Other",
]

_CITY_TIER_OPTIONS = [
    "Major global hub (e.g. NYC, London, Tokyo, Singapore)",
    "Large national city (e.g. Chicago, Manchester, Mumbai)",
    "Mid-size city",
    "Small city / town",
    "Rural / remote area",
    "Fully remote — no fixed location",
]

_COMP_TYPE_OPTIONS = [
    "Base salary only",
    "Base + annual bonus",
    "Base + equity (RSU / ESOP / options)",
    "Base + bonus + equity",
    "Contract / daily rate",
    "Hourly / part-time",
    "Other",
]

_CERT_OPTIONS = [
    "AWS Certified (any tier)",
    "Google Cloud Certified (any tier)",
    "Microsoft Azure Certified (any tier)",
    "PMP / CAPM (Project Management)",
    "CFA (Chartered Financial Analyst)",
    "CPA / ACCA (Accounting)",
    "CISSP / CEH (Cybersecurity)",
    "Scrum Master / SAFe",
    "Tableau / Power BI certified",
    "TensorFlow Developer Certificate",
    "PhD (treated as certification here)",
    "Other professional certification",
]

_VISA_OPTIONS = [
    "Citizen / permanent resident",
    "Work visa (employer-sponsored)",
    "Work visa (self-sponsored / independent)",
    "Student visa with work permit",
    "Other",
    "Prefer not to say",
]

_HOURS_OPTIONS = [
    "Under 35 hrs / week",
    "35-40 hrs / week (standard)",
    "41-50 hrs / week",
    "51-60 hrs / week",
    "Over 60 hrs / week",
]

_OFFER_TYPE_OPTIONS = [
    "Accepted as offered (no negotiation)",
    "Negotiated — got more than initial offer",
    "Negotiated — offer did not improve",
    "Counter-offered from another company",
    "Internal transfer / promotion",
    "Consulting / freelance rate — self-set",
]

# << EXTENDED DATA BLOCK END >>


# ==================================================================
# CROSS-DATASET BRIDGE CONSTANTS & HELPERS
# << CROSS-DATASET BLOCK START — remove to roll back Layer 2 only >>
# ==================================================================

# DS1 education integer encoding  (mirrors app.py exactly)
_EDUCATION_LABELS = {
    0: "High School",
    1: "Bachelor's Degree",
    2: "Master's Degree",
    3: "PhD",
}

# DS2 employment type  (code, display label)
_EMPLOYMENT_TYPE_OPTIONS = [
    ("FT", "Full Time"),
    ("PT", "Part Time"),
    ("CT", "Contract"),
    ("FL", "Freelance"),
]

# DS2 remote_ratio  (value, display label)
_REMOTE_RATIO_OPTIONS = [
    (0,   "On-site (0%)"),
    (50,  "Hybrid (50%)"),
    (100, "Fully Remote (100%)"),
]

# DS2 company_size  (code, display label)
_COMPANY_SIZE_OPTIONS = [
    ("S", "Small  (< 50 employees)"),
    ("M", "Medium (50-250 employees)"),
    ("L", "Large  (> 250 employees)"),
]

# Representative ISO-2 list matching COUNTRY_NAME_MAP keys in app.py.
# Kept here as a literal so feedback.py has zero import dependency on app.py.
_ISO2_COUNTRIES = sorted(set([
    "AF", "AL", "AM", "AR", "AS", "AT", "AU", "AZ",
    "BA", "BD", "BE", "BG", "BH", "BO", "BR", "BS",
    "CA", "CF", "CH", "CL", "CN", "CO", "CR", "CY", "CZ",
    "DE", "DK", "DO", "DZ",
    "EC", "EE", "EG", "ES", "ET",
    "FI", "FR",
    "GB", "GE", "GH", "GR", "GT",
    "HK", "HN", "HR", "HU",
    "ID", "IE", "IL", "IN", "IQ", "IR", "IT",
    "JE", "JO", "JP",
    "KE", "KH", "KR", "KW", "KZ",
    "LA", "LB", "LK", "LT", "LU", "LV",
    "MA", "MD", "MK", "MM", "MN", "MT", "MX", "MY",
    "NG", "NI", "NL", "NO", "NP", "NZ",
    "OM",
    "PA", "PE", "PH", "PK", "PL", "PR", "PT", "PY",
    "QA",
    "RO", "RS", "RU",
    "SA", "SE", "SG", "SI", "SK", "SV",
    "TH", "TN", "TR", "TW", "TZ",
    "UA", "UG", "US", "UY", "UZ",
    "VE", "VN",
    "YE", "ZA",
]))


def _is_app1_model(model_used: str) -> bool:
    """True for Random Forest / general salary model and its resume variant."""
    m = model_used.lower()
    return "random forest" in m or ("resume" in m and "xgboost" not in m)


def _is_app2_model(model_used: str) -> bool:
    """True for XGBoost / data science salary model and its resume variant."""
    return "xgboost" in model_used.lower()


def _collect_cross_dataset_fields(
    model_used: str,
    k: str,
    collected: dict,
) -> None:
    """
    Renders fields that exist in one dataset but not the other, and writes
    results directly into `collected` (mutates in place, returns nothing).

    App2 (XGBoost) users are shown DS1-only fields:
      age, education_level, is_senior, gender

    App1 (Random Forest) users are shown DS2-only fields:
      employment_type, remote_ratio, company_size, company_location

    Fields use the exact codes / types that the source dataset uses so that
    combined-dataset exports require no transformation.
    """

    # ── DS1 FIELDS for App2 users ──────────────────────────────────
    if _is_app2_model(model_used):

        st.divider()
        st.markdown("**Dataset bridge — general profile**")
        st.caption(
            "The data science salary model does not use age, education level, "
            "seniority, or gender. Sharing these here lets us build a unified "
            "dataset that combines both sources for future model training."
        )

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            age_val = st.number_input(
                "Age (optional)",
                min_value=0, max_value=80, value=0, step=1,
                key=f"{k}_bridge_age",
                help="0 = skip.",
            )
            if age_val > 0:
                collected["age"] = int(age_val)

            edu_display = ["(skip)"] + list(_EDUCATION_LABELS.values())
            edu_sel = st.selectbox(
                "Highest education level",
                options=edu_display,
                index=0,
                key=f"{k}_bridge_edu",
            )
            if edu_sel != "(skip)":
                # Store integer code to match DS1 schema exactly
                reverse_edu = {v: k_int for k_int, v in _EDUCATION_LABELS.items()}
                collected["education_level"] = reverse_edu[edu_sel]

        with col_b2:
            senior_sel = st.selectbox(
                "Is / was this a senior-level position?",
                options=["(skip)", "Yes — Senior", "No — Non-Senior"],
                index=0,
                key=f"{k}_bridge_senior",
                help=(
                    "Senior = staff, principal, lead, or explicitly titled Senior. "
                    "Stored as 1 (Yes) or 0 (No) to match DS1."
                ),
            )
            if senior_sel != "(skip)":
                collected["is_senior"] = 1 if "Yes" in senior_sel else 0

            gender_sel = st.selectbox(
                "Gender (optional)",
                options=[
                    "(skip)", "Male", "Female",
                    "Non-binary", "Other", "Prefer not to say",
                ],
                index=0,
                key=f"{k}_bridge_gender",
            )
            if gender_sel not in ("(skip)", "Prefer not to say"):
                collected["gender"] = gender_sel

    # ── DS2 FIELDS for App1 users ──────────────────────────────────
    elif _is_app1_model(model_used):

        st.divider()
        st.markdown("**Dataset bridge — employment structure**")
        st.caption(
            "The general salary model does not capture employment type, "
            "remote arrangement, company size, or company location separately "
            "from your own country. Sharing these builds a unified dataset "
            "for future model training."
        )

        col_b3, col_b4 = st.columns(2)

        with col_b3:
            emp_display = ["(skip)"] + [lbl for _, lbl in _EMPLOYMENT_TYPE_OPTIONS]
            emp_sel = st.selectbox(
                "Employment type",
                options=emp_display,
                index=0,
                key=f"{k}_bridge_emp_type",
                help="Stored as FT/PT/CT/FL to match DS2 schema.",
            )
            if emp_sel != "(skip)":
                code_map = {lbl: code for code, lbl in _EMPLOYMENT_TYPE_OPTIONS}
                collected["employment_type"] = code_map[emp_sel]

            remote_display = ["(skip)"] + [lbl for _, lbl in _REMOTE_RATIO_OPTIONS]
            remote_sel = st.selectbox(
                "Work arrangement",
                options=remote_display,
                index=0,
                key=f"{k}_bridge_remote",
                help="Stored as 0 / 50 / 100 to match DS2 remote_ratio.",
            )
            if remote_sel != "(skip)":
                ratio_map = {lbl: val for val, lbl in _REMOTE_RATIO_OPTIONS}
                collected["remote_ratio"] = ratio_map[remote_sel]

        with col_b4:
            size_display = ["(skip)"] + [lbl for _, lbl in _COMPANY_SIZE_OPTIONS]
            size_sel = st.selectbox(
                "Company size",
                options=size_display,
                index=0,
                key=f"{k}_bridge_company_size",
                help="Stored as S/M/L to match DS2 company_size.",
            )
            if size_sel != "(skip)":
                size_map = {lbl: code for code, lbl in _COMPANY_SIZE_OPTIONS}
                collected["company_size"] = size_map[size_sel]

            loc_sel = st.selectbox(
                "Company location (ISO-2 country)",
                options=["(skip)"] + _ISO2_COUNTRIES,
                index=0,
                key=f"{k}_bridge_company_loc",
                help=(
                    "Where the employer is based — may differ from your own country. "
                    "Stored as ISO-2 to match DS2 company_location."
                ),
            )
            if loc_sel != "(skip)":
                collected["company_location"] = loc_sel

# << CROSS-DATASET BLOCK END >>


# ==================================================================
# EXTENDED DATA COLLECTOR
# << EXTENDED DATA BLOCK START — delete this function to roll back Layer 1 >>
# ==================================================================

def _collect_extended_data(model_used: str, salary_key: str) -> dict | None:
    """
    Renders the full optional enrichment form inside a nested expander.

    Sections:
      0. Cross-dataset bridge fields (Layer 2) — model-specific
      1. Compensation structure
      2. Skills & tools
      3. Industry & company
      4. Role context
      5. Additional context (free text, capped)

    Returns a populated dict or None if the user filled in nothing at all.
    Widget keys are namespaced by model_used + salary_key so this function
    can safely be called from multiple locations without key collisions.
    """

    k = f"ext_{model_used}_{salary_key}"

    with st.expander(
        "Optional: Help improve future models by sharing more details",
        expanded=False,
    ):
        st.caption(
            "All fields are completely optional. "
            "You can submit the main feedback above without filling any of these in. "
            "The more context you share, the more useful your data point is for "
            "training more accurate, realistic salary models."
        )

        collected: dict = {}

        # --------------------------------------------------------------
        # SECTION 0 — Cross-dataset bridge
        # << CROSS-DATASET BLOCK START — remove this one call line to roll back Layer 2 >>
        _collect_cross_dataset_fields(model_used, k, collected)
        # << CROSS-DATASET BLOCK END >>
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # SECTION 1 — Compensation structure
        # --------------------------------------------------------------
        st.divider()
        st.markdown("**Compensation structure**")

        comp_type = st.selectbox(
            "How is your compensation structured?",
            options=["(skip)"] + _COMP_TYPE_OPTIONS,
            index=0,
            key=f"{k}_comp_type",
        )
        if comp_type != "(skip)":
            collected["compensation_type"] = comp_type

        col_tc1, col_tc2 = st.columns(2)
        with col_tc1:
            base_sal = st.number_input(
                "Actual base salary (USD, optional)",
                min_value=0.0, max_value=10_000_000.0,
                value=0.0, step=1000.0, format="%.0f",
                key=f"{k}_base_salary",
                help="Annual base pay only, before bonus or equity.",
            )
            if base_sal > 0:
                collected["actual_base_usd"] = float(base_sal)

        with col_tc2:
            total_comp = st.number_input(
                "Total annual compensation (USD, optional)",
                min_value=0.0, max_value=10_000_000.0,
                value=0.0, step=1000.0, format="%.0f",
                key=f"{k}_total_comp",
                help="Base + average annual bonus + annualised equity. 0 = skip.",
            )
            if total_comp > 0:
                collected["actual_total_comp_usd"] = float(total_comp)

        offer_type = st.selectbox(
            "How was this salary determined?",
            options=["(skip)"] + _OFFER_TYPE_OPTIONS,
            index=0,
            key=f"{k}_offer_type",
        )
        if offer_type != "(skip)":
            collected["offer_determination"] = offer_type

        # --------------------------------------------------------------
        # SECTION 2 — Skills & tools
        # --------------------------------------------------------------
        st.divider()
        st.markdown("**Skills & tools**")
        st.caption(
            "Select what you actively use in this role — "
            "focus on what you spend real time on, not just CV keywords."
        )

        skills = st.multiselect(
            "Primary skills / tools",
            options=_SKILL_OPTIONS,
            default=[],
            key=f"{k}_skills",
            placeholder="Search or scroll...",
        )
        if skills:
            collected["skills"] = skills

        yoe_skill = st.slider(
            "Years using your primary skill",
            min_value=0, max_value=30, value=0, step=1,
            key=f"{k}_yoe_primary_skill",
            help="0 = skip.",
        )
        if yoe_skill > 0:
            collected["years_primary_skill"] = yoe_skill

        certs = st.multiselect(
            "Relevant certifications held (optional)",
            options=_CERT_OPTIONS,
            default=[],
            key=f"{k}_certs",
        )
        if certs:
            collected["certifications"] = certs

        # --------------------------------------------------------------
        # SECTION 3 — Industry & company
        # --------------------------------------------------------------
        st.divider()
        st.markdown("**Industry & company**")

        industry = st.selectbox(
            "Industry / sector",
            options=["(skip)"] + _INDUSTRY_OPTIONS,
            index=0,
            key=f"{k}_industry",
        )
        if industry != "(skip)":
            collected["industry"] = industry

        company_type = st.selectbox(
            "Company type / ownership structure",
            options=["(skip)"] + _COMPANY_TYPE_OPTIONS,
            index=0,
            key=f"{k}_company_type",
        )
        if company_type != "(skip)":
            collected["company_type"] = company_type

        col_co1, col_co2 = st.columns(2)
        with col_co1:
            co_age = st.number_input(
                "Company age (years, optional)",
                min_value=0, max_value=200, value=0, step=1,
                key=f"{k}_company_age",
                help="0 = skip.",
            )
            if co_age > 0:
                collected["company_age_years"] = int(co_age)

        with col_co2:
            team_size = st.selectbox(
                "Size of your immediate team",
                options=["(skip)", "Solo", "2-5", "6-15", "16-50", "51-200", "200+"],
                index=0,
                key=f"{k}_team_size",
            )
            if team_size != "(skip)":
                collected["immediate_team_size"] = team_size

        reports = st.selectbox(
            "Number of direct reports (people you manage)",
            options=[
                "(skip)", "0 — individual contributor",
                "1-3", "4-10", "11-25", "26-50", "50+",
            ],
            index=0,
            key=f"{k}_reports",
            help="Management scope is a strong salary predictor.",
        )
        if reports != "(skip)":
            collected["direct_reports"] = reports

        # --------------------------------------------------------------
        # SECTION 4 — Role context
        # --------------------------------------------------------------
        st.divider()
        st.markdown("**Role context**")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            yrs_co = st.slider(
                "Years at current / most recent company",
                min_value=0, max_value=40, value=0, step=1,
                key=f"{k}_yrs_company",
                help="0 = skip or < 1 year.",
            )
            if yrs_co > 0:
                collected["years_current_company"] = yrs_co

        with col_r2:
            total_jobs = st.number_input(
                "Total employers in your career",
                min_value=0, max_value=50, value=0, step=1,
                key=f"{k}_total_jobs",
                help="0 = skip.",
            )
            if total_jobs > 0:
                collected["total_employers"] = int(total_jobs)

        hours = st.selectbox(
            "Typical working hours per week",
            options=["(skip)"] + _HOURS_OPTIONS,
            index=0,
            key=f"{k}_hours",
        )
        if hours != "(skip)":
            collected["hours_per_week"] = hours

        city_tier = st.selectbox(
            "Location tier (city size / type)",
            options=["(skip)"] + _CITY_TIER_OPTIONS,
            index=0,
            key=f"{k}_city_tier",
            help="Captures cost-of-living and labour market density.",
        )
        if city_tier != "(skip)":
            collected["city_tier"] = city_tier

        visa = st.selectbox(
            "Work authorisation status",
            options=["(skip)"] + _VISA_OPTIONS,
            index=0,
            key=f"{k}_visa",
            help="Select 'Prefer not to say' to skip without choosing (skip).",
        )
        if visa not in ("(skip)", "Prefer not to say"):
            collected["work_authorisation"] = visa

        # --------------------------------------------------------------
        # SECTION 5 — Additional context
        # --------------------------------------------------------------
        st.divider()
        st.markdown("**Additional context (optional)**")

        free_text = st.text_area(
            "Anything else that significantly affects your salary? (max 300 characters)",
            max_chars=300,
            height=80,
            placeholder=(
                "e.g. niche domain expertise, unusual benefits, "
                "cost-of-living adjustment clause, signing bonus..."
            ),
            key=f"{k}_free_text",
            help="Keep it factual and relevant to salary determination.",
        )
        if free_text and free_text.strip():
            collected["additional_context"] = free_text.strip()

        if not collected:
            return None

        return collected

# << EXTENDED DATA BLOCK END >>


# ------------------------------------------------------------------
# FEEDBACK UI  (original structure preserved entirely)
# ------------------------------------------------------------------

def feedback_ui(predicted_salary: float, model_used: str, input_data: dict):
    """
    Renders a collapsible feedback expander.

    Parameters
    ----------
    predicted_salary : float
        The salary value just predicted.
    model_used : str
        Short label e.g. "Random Forest", "XGBoost",
        "Random Forest Resume", "XGBoost Resume".
    input_data : dict
        The exact input fields used for this prediction.
    """

    if predicted_salary is None:
        return

    submitted_key = f"_feedback_submitted_{model_used}_{int(predicted_salary)}"
    salary_key    = str(int(predicted_salary))

    with st.expander(":material/feedback: Share Feedback on This Prediction", expanded=False):
        if st.session_state.get(submitted_key):
            st.success("Thank you for your feedback!")
            return

        st.caption(
            "Help us improve by letting us know how accurate this prediction was. "
            "Star rating is required; all other fields are optional."
        )

        # --- Row 1: Accuracy + Direction -------------------------
        col_a, col_b = st.columns(2)

        with col_a:
            accuracy_rating = st.radio(
                "Was the prediction accurate?",
                options=["Yes", "Somewhat", "No"],
                index=0,
                horizontal=True,
                key=f"fb_accuracy_{model_used}_{salary_key}"
            )

        with col_b:
            direction = st.radio(
                "How did it compare to reality?",
                options=["Too High", "About Right", "Too Low"],
                index=1,
                horizontal=True,
                key=f"fb_direction_{model_used}_{salary_key}"
            )

        # --- Row 2: Star rating ----------------------------------
        star_rating = st.select_slider(
            "Overall rating",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "\u2b50" * x,
            key=f"fb_stars_{model_used}_{salary_key}"
        )

        # --- Row 3: Optional actual salary -----------------------
        actual_salary_raw = st.number_input(
            "Your actual / expected salary (USD, optional)",
            min_value=0.0,
            max_value=10_000_000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
            help="Leave at 0 to skip.",
            key=f"fb_actual_{model_used}_{salary_key}"
        )
        actual_salary = float(actual_salary_raw) if actual_salary_raw > 0 else None

        # << EXTENDED DATA BLOCK START — remove this line to roll back Layer 1 >>
        extended = _collect_extended_data(model_used, salary_key)
        # << EXTENDED DATA BLOCK END >>

        # --- Submit ----------------------------------------------
        if st.button(
            "Submit Feedback",
            key=f"fb_submit_{model_used}_{salary_key}",
            use_container_width=True,
            type="primary"
        ):
            username = st.session_state.get("username") or "anonymous"

            try:
                save_feedback(
                    username=username,
                    model_used=model_used,
                    input_data=input_data,
                    predicted_salary=predicted_salary,
                    accuracy_rating=accuracy_rating,
                    direction=direction,
                    actual_salary=actual_salary,
                    star_rating=star_rating,
                    # << EXTENDED DATA BLOCK START — remove kwarg to roll back Layer 1 >>
                    extended=extended,
                    # << EXTENDED DATA BLOCK END >>
                )
                st.session_state[submitted_key] = True
                st.success("Thank you for your feedback!")
                st.rerun()

            except Exception as e:
                st.error("Could not save feedback. Please try again later.")
                st.exception(e)