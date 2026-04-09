"""
feedback.py — Prediction Feedback System for SalaryScope
=========================================================
Provides:
  - save_feedback()  : persists a feedback record to Firestore
  - feedback_ui()    : renders a collapsible feedback form in Streamlit

Firestore path:  feedback/{auto-id}
Completely separate from the predictions/ collection.

ROLLBACK NOTE
-------------
The extended data collection block is isolated between the markers:
    # -- EXTENDED DATA BLOCK START --
    ...
    # -- EXTENDED DATA BLOCK END --

To roll back to the original form, delete everything between and including
those two markers in feedback_ui(), and remove the `extended` parameter
from the save_feedback() call at the bottom of feedback_ui().
The save_feedback() function signature change is also marked for easy revert.
"""

import streamlit as st
import json
from datetime import datetime


# ------------------------------------------------------------------
# FIRESTORE HELPER
# Reuses the same cached client from database.py — no second init.
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
    accuracy_rating: str,        # "Yes" | "Somewhat" | "No"
    direction: str,              # "Too High" | "About Right" | "Too Low"
    actual_salary: float | None,
    star_rating: int,            # 1–5
    # -- EXTENDED DATA BLOCK START - remove this parameter to roll back --
    extended: dict | None = None,
    # -- EXTENDED DATA BLOCK END --
):
    """
    Write one feedback document to Firestore.
    All fields are structured — no free-text.

    The `extended` parameter carries optional supplementary fields collected
    for dataset enrichment. It is stored as a nested dict under the key
    "extended_data" and is always optional — None if the user skipped it.
    """
    db = _db()

    record = {
        "username": username or "anonymous",
        "model_used": model_used,
        "input_data": json.dumps(input_data),   # same pattern as save_prediction()
        "predicted_salary": predicted_salary,
        "accuracy_rating": accuracy_rating,
        "direction": direction,
        "actual_salary": actual_salary,          # None when not provided
        "star_rating": star_rating,
        "created_at": datetime.utcnow().isoformat(),
    }

    # -- EXTENDED DATA BLOCK START -- remove this block to roll back --
    if extended:
        record["extended_data"] = extended
    # -- EXTENDED DATA BLOCK END --

    db.collection("feedback").add(record)


# ------------------------------------------------------------------
# EXTENDED DATA COLLECTOR  (standalone helper -- easy to remove)
# ------------------------------------------------------------------
# -- EXTENDED DATA BLOCK START --

# Skill options grouped by domain — used in both models' forms.
# Kept as a module-level constant so it is defined once and easy to edit.
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
    # Soft / domain
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
    "35–40 hrs / week (standard)",
    "41–50 hrs / week",
    "51–60 hrs / week",
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


def _collect_extended_data(model_used: str, salary_key: str) -> dict | None:
    """
    Renders the optional extended data collection form inside an expander.
    Returns a dict of collected values, or None if the user did not expand it.

    `model_used` and `salary_key` are used to namespace widget keys so this
    function can be called from multiple call-sites without key collisions.

    ROLLBACK: delete this entire function and its call in feedback_ui().
    """

    k = f"ext_{model_used}_{salary_key}"   # short namespace prefix

    with st.expander(
        "Optional: Help improve future models by sharing more details",
        expanded=False,
    ):
        st.caption(
            "All fields below are completely optional. "
            "Submitting the main feedback form above does not require filling these in. "
            "The more context you share, the more useful your data point is for "
            "training more accurate salary models."
        )

        collected: dict = {}

        # ------------------------------------------------------------------
        # SECTION 1 — Compensation structure
        # ------------------------------------------------------------------
        st.markdown("**Compensation structure**")

        comp_type = st.selectbox(
            "How is your compensation structured?",
            options=["(skip)"] + _COMP_TYPE_OPTIONS,
            index=0,
            key=f"{k}_comp_type",
            help="Select the structure that best describes your total package.",
        )
        if comp_type != "(skip)":
            collected["compensation_type"] = comp_type

        col_tc1, col_tc2 = st.columns(2)
        with col_tc1:
            base_salary = st.number_input(
                "Actual base salary (USD, optional)",
                min_value=0.0, max_value=10_000_000.0,
                value=0.0, step=1000.0, format="%.0f",
                key=f"{k}_base_salary",
                help="Your annual base pay only, before bonus or equity.",
            )
            if base_salary > 0:
                collected["actual_base_usd"] = float(base_salary)

        with col_tc2:
            total_comp = st.number_input(
                "Total annual compensation (USD, optional)",
                min_value=0.0, max_value=10_000_000.0,
                value=0.0, step=1000.0, format="%.0f",
                key=f"{k}_total_comp",
                help=(
                    "Include base + average annual bonus + "
                    "annualised equity value. Leave at 0 to skip."
                ),
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

        # ------------------------------------------------------------------
        # SECTION 2 — Skills
        # ------------------------------------------------------------------
        st.divider()
        st.markdown("**Skills & tools**")
        st.caption(
            "Select all that you actively use in your current or most recent role. "
            "Focus on what you spend real time on, not just what you have listed on a CV."
        )

        skills = st.multiselect(
            "Primary skills / tools used in this role",
            options=_SKILL_OPTIONS,
            default=[],
            key=f"{k}_skills",
            placeholder="Search or scroll to select skills...",
        )
        if skills:
            collected["skills"] = skills

        yoe_skill = st.slider(
            "Years using your primary skill (the one you are most expert in)",
            min_value=0, max_value=30, value=0, step=1,
            key=f"{k}_yoe_primary_skill",
            help="0 = skip / not applicable.",
        )
        if yoe_skill > 0:
            collected["years_primary_skill"] = yoe_skill

        certifications = st.multiselect(
            "Relevant certifications held (optional)",
            options=_CERT_OPTIONS,
            default=[],
            key=f"{k}_certs",
        )
        if certifications:
            collected["certifications"] = certifications

        # ------------------------------------------------------------------
        # SECTION 3 — Industry & company
        # ------------------------------------------------------------------
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
            company_age_yrs = st.number_input(
                "Company age (years, optional)",
                min_value=0, max_value=200, value=0, step=1,
                key=f"{k}_company_age",
                help="Approximate age of the company / organisation. 0 = skip.",
            )
            if company_age_yrs > 0:
                collected["company_age_years"] = int(company_age_yrs)

        with col_co2:
            team_size = st.selectbox(
                "Size of your immediate team",
                options=[
                    "(skip)", "Solo", "2–5", "6–15",
                    "16–50", "51–200", "200+",
                ],
                index=0,
                key=f"{k}_team_size",
            )
            if team_size != "(skip)":
                collected["immediate_team_size"] = team_size

        reports_count = st.selectbox(
            "Number of direct reports (people you manage)",
            options=[
                "(skip)", "0 — individual contributor",
                "1–3", "4–10", "11–25", "26–50", "50+",
            ],
            index=0,
            key=f"{k}_reports",
            help="This captures management responsibility, which strongly influences salary.",
        )
        if reports_count != "(skip)":
            collected["direct_reports"] = reports_count

        # ------------------------------------------------------------------
        # SECTION 4 — Role context
        # ------------------------------------------------------------------
        st.divider()
        st.markdown("**Role context**")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            yrs_current_company = st.slider(
                "Years at current / most recent company",
                min_value=0, max_value=40, value=0, step=1,
                key=f"{k}_yrs_company",
                help="0 = skip or less than 1 year.",
            )
            if yrs_current_company > 0:
                collected["years_current_company"] = yrs_current_company

        with col_r2:
            total_jobs = st.number_input(
                "Total number of employers in your career",
                min_value=0, max_value=50, value=0, step=1,
                key=f"{k}_total_jobs",
                help="0 = skip. Indicates career switching frequency.",
            )
            if total_jobs > 0:
                collected["total_employers"] = int(total_jobs)

        hours_per_week = st.selectbox(
            "Typical working hours per week",
            options=["(skip)"] + _HOURS_OPTIONS,
            index=0,
            key=f"{k}_hours",
        )
        if hours_per_week != "(skip)":
            collected["hours_per_week"] = hours_per_week

        city_tier = st.selectbox(
            "Location tier (city size / type)",
            options=["(skip)"] + _CITY_TIER_OPTIONS,
            index=0,
            key=f"{k}_city_tier",
            help=(
                "City tier captures cost-of-living and labour market density "
                "better than country alone."
            ),
        )
        if city_tier != "(skip)":
            collected["city_tier"] = city_tier

        visa_status = st.selectbox(
            "Work authorisation status",
            options=["(skip)"] + _VISA_OPTIONS,
            index=0,
            key=f"{k}_visa",
            help=(
                "Visa / work permit status affects salary in many markets. "
                "Select 'Prefer not to say' to skip without selecting (skip)."
            ),
        )
        if visa_status not in ("(skip)", "Prefer not to say"):
            collected["work_authorisation"] = visa_status

        # ------------------------------------------------------------------
        # SECTION 5 — Additional context (free-text, length-capped)
        # ------------------------------------------------------------------
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

        # Return None if absolutely nothing was filled in — avoids empty
        # dicts cluttering Firestore.
        if not collected:
            return None

        return collected

# -- EXTENDED DATA BLOCK END --


# ------------------------------------------------------------------
# FEEDBACK UI
# ------------------------------------------------------------------

def feedback_ui(predicted_salary: float, model_used: str, input_data: dict):
    """
    Renders a collapsible feedback expander.

    Parameters
    ----------
    predicted_salary : float
        The salary value just predicted (stored for reference).
    model_used : str
        Short label e.g. "Random Forest" or "XGBoost".
    input_data : dict
        The exact input fields used to produce this prediction
        (mirroring what is passed to save_prediction).
    """

    if predicted_salary is None:
        return

    # Per-prediction session key — resets automatically when a new
    # prediction with a different salary is run.
    submitted_key = f"_feedback_submitted_{model_used}_{int(predicted_salary)}"

    # Stable salary key used to namespace all widget keys in this call.
    salary_key = str(int(predicted_salary))

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

        # -- EXTENDED DATA BLOCK START --
        # Collect optional enrichment data in a nested expander.
        # To roll back: delete the next two lines and the `extended=extended`
        # argument in the save_feedback() call below.
        extended = _collect_extended_data(model_used, salary_key)
        # ── EXTENDED DATA BLOCK END ──

        # --- Submit -----------------------------------------------
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
                    # -- EXTENDED DATA BLOCK START -- remove to roll back --
                    extended=extended,
                    # -- EXTENDED DATA BLOCK END --
                )
                st.session_state[submitted_key] = True
                st.success("Thank you for your feedback!")
                st.rerun()

            except Exception as e:
                st.error("Could not save feedback. Please try again later.")
                st.exception(e)