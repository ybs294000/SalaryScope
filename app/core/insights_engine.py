import pandas as pd


# =========================================================
# DOMAIN DETECTION (DATASET-ALIGNED)
# =========================================================

DOMAIN_KEYWORDS = {
    "ml_ai": [
        "machine learning",
        "ml ",
        "mlops",
        "deep learning",
        "nlp",
        "computer vision",
        "vision",
        "ai ",
        "ai-",
        "ai_",
        "research scientist",
        "applied scientist",
        "machine learning scientist",
        "machine learning engineer",
        "ml engineer",
        "ml developer",
        "ml researcher"
    ],

    "data_eng": [
        "data engineer",
        "etl",
        "pipeline",
        "big data",
        "data infrastructure",
        "data architect",
        "cloud data",
        "database engineer",
        "data devops",
        "etl developer",
        "etl engineer"
    ],

    "analytics": [
        "analyst",
        "analytics",
        "bi",
        "business intelligence",
        "dashboard",
        "reporting",
        "insight"
    ],

    "scientist": [
        "data scientist",
        "data science"
    ],
}


def detect_domain_from_title(job_title):
    if not isinstance(job_title, str):
        return "other"

    title = f" {job_title.lower()} "

    # PRIORITY ORDER

    if any(kw in title for kw in DOMAIN_KEYWORDS["ml_ai"]):
        return "ml_ai"

    if any(kw in title for kw in DOMAIN_KEYWORDS["analytics"]):
        return "analytics"

    if any(kw in title for kw in DOMAIN_KEYWORDS["data_eng"]):
        return "data_eng"

    if any(kw in title for kw in DOMAIN_KEYWORDS["scientist"]):
        return "scientist"

    return "other"


# =========================================================
# ROLE CLASSIFICATION 
# =========================================================

DOMAIN_TO_ROLE = {
    "ml_ai":     "Machine Learning / AI",
    "data_eng":  "Data Engineering",
    "analytics": "Analytics",
    "scientist": "Data Science",
}


def classify_role_app2(domain, is_mgmt, is_exec):
    # Only override if actually management
    if is_mgmt:
        return "Management"

    return DOMAIN_TO_ROLE.get(domain, "Other")


# =========================================================
# MARKET COMPARISON 
# =========================================================

MIN_SAMPLE = 15


def compute_market_insight(job_title, company_location, experience_label, domain, prediction, df_app2):

    # Normalize location
    if "(" in company_location:
        company_location = company_location.split("(")[-1].replace(")", "").strip()

    # Map UI labels to dataset
    EXP_MAP = {
        "Entry Level": "EN",
        "Mid Level": "MI",
        "Senior Level": "SE",
        "Executive Level": "EX"
    }

    exp_code = EXP_MAP.get(experience_label)

    title_mask = df_app2["job_title"] == job_title
    loc_mask   = df_app2["company_location"] == company_location
    exp_mask   = df_app2["experience_level"] == exp_code

    domain_mask = (
        df_app2["job_title"].str.lower().str.contains(domain.replace("_", " "), na=False)
        if domain != "other" else pd.Series(False, index=df_app2.index)
    )

    # Hierarchical fallback (experience ALWAYS included)
    fallbacks = [
        df_app2[title_mask & loc_mask & exp_mask],
        df_app2[title_mask & exp_mask],
        df_app2[loc_mask & domain_mask & exp_mask],
        df_app2[domain_mask & exp_mask],
    ]

    for subset in fallbacks:
        if len(subset) >= MIN_SAMPLE:
            avg = subset["salary_in_usd"].mean()

            if prediction >= avg:
                return (
                    "You are above the market average for this role and experience level.",
                    "success"
                )
            else:
                return (
                    "You are below the market average for this role and experience level.",
                    "warning"
                )

    return (
        "Not enough data available for reliable market comparison.",
        "info"
    )


# =========================================================
# RECOMMENDATION ENGINE
# =========================================================

BASE_RECS = {
    "Entry Level": [
        "Build strong fundamentals in your domain",
        "Work on hands-on projects",
        "Create a strong portfolio (GitHub / real work)",
    ],
    "Mid Level": [
        "Improve real-world problem solving",
        "Start specialization in your domain",
        "Take ownership of projects",
    ],
    "Senior Level": [
        "Focus on system design and scalability",
        "Lead major projects",
        "Mentor juniors",
    ],
    "Executive Level": [
        "Focus on business strategy and decisions",
        "Align tech with business goals",
        "Drive organizational impact",
    ],
}


ROLE_RECS = {
    "Entry Level": {
        "Machine Learning / AI": "Focus on ML basics and statistics",
        "Data Science":          "Focus on EDA and statistical thinking",
        "Data Engineering":      "Learn SQL and data pipelines",
        "Analytics":             "Learn SQL, Excel, and visualization tools",
    },
    "Mid Level": {
        "Machine Learning / AI": "Learn model optimization and deployment",
        "Data Engineering":      "Work with Spark, Kafka, distributed systems",
        "Analytics":             "Improve dashboards and business insights",
    },
    "Senior Level": {
        "Machine Learning / AI": "Work on production ML and MLOps",
        "Data Engineering":      "Design large-scale data architecture",
        "Management":            "Improve leadership and team management",
        "Analytics":             "Drive business decisions using data insights",
    },
    "Executive Level": {
        "Management":            "Strengthen leadership and vision",
        "Machine Learning / AI": "Define AI strategy and lead innovation initiatives",
        "Data Engineering":      "Oversee large-scale data infrastructure decisions",
        "Analytics":             "Drive data-driven business strategy and decision making",
        "Data Science":          "Lead advanced analytics and modeling initiatives",
    },
}


MARKET_RECS = {
    "warning": "Upskilling or role change may improve salary",
    "success": "You are well positioned — focus on growth",
}


def generate_recommendations(role, experience_label, market_type):

    recs = list(BASE_RECS.get(experience_label, [
        "Improve technical skills",
        "Work on real-world projects",
    ]))

    role_tip = ROLE_RECS.get(experience_label, {}).get(role)
    if role_tip:
        recs.append(role_tip)

    market_tip = MARKET_RECS.get(market_type)
    if market_tip:
        recs.append(market_tip)

    return recs


# =========================================================
# MAIN FUNCTION
# =========================================================

def generate_insights_app2(input_dict, prediction, df_app2, title_features_func):

    job_title        = input_dict["Job Title"]
    experience_label = input_dict["Experience Level"]
    company_location = input_dict["Company Location"]

    # mgmt detection only
    _, _, exec_, is_mgmt, _ = title_features_func(job_title)

    # domain detection
    domain = detect_domain_from_title(job_title)

    # role classification
    role = classify_role_app2(domain, is_mgmt, exec_)

    # FIXED market insight (with experience)
    market_msg, market_type = compute_market_insight(
        job_title,
        company_location,
        experience_label,
        domain,
        prediction,
        df_app2
    )

    # recommendations
    recs = generate_recommendations(role, experience_label, market_type)

    return {
        "role": role,
        "market_msg": market_msg,
        "market_type": market_type,
        #"recommendations": recs,
    }

# =========================================================
# APP 1 — JOB GROUP CLASSIFICATION (REUSED LOGIC)
# =========================================================

def classify_job_group_app1(job_title):
    if not isinstance(job_title, str):
        return "Operations"

    t = job_title.lower()

    if any(x in t for x in ["engineer", "developer", "data", "scientist", "analyst", "architect", "it", "network"]):
        return "Tech"
    elif any(x in t for x in ["manager", "director", "vp", "chief", "ceo"]):
        return "Management"
    elif any(x in t for x in ["marketing", "sales", "brand", "advertising"]):
        return "Marketing_Sales"
    elif any(x in t for x in ["hr", "human resources", "recruit"]):
        return "HR"
    elif any(x in t for x in ["finance", "financial", "account"]):
        return "Finance"
    elif any(x in t for x in ["designer", "ux", "graphic", "creative"]):
        return "Design"
    else:
        return "Operations"


# =========================================================
# APP 1 — EXPERIENCE CATEGORY
# =========================================================

def get_experience_category_app1(experience):
    if experience <= 2:
        return "Entry"
    elif experience <= 5:
        return "Mid"
    else:
        return "Senior"


# =========================================================
# APP 1 — RECOMMENDATIONS
# =========================================================

APP1_BASE_RECS = {
    "Entry": [
        "Focus on building strong foundational skills",
        "Work on real-world projects to gain experience",
        "Explore different roles to identify your strengths"
    ],
    "Mid": [
        "Strengthen problem-solving and domain expertise",
        "Take ownership of projects and responsibilities",
        "Start building a strong professional profile"
    ],
    "Senior": [
        "Focus on leadership and decision-making skills",
        "Mentor junior professionals",
        "Drive impact through strategic contributions"
    ],
}

APP1_ROLE_RECS = {
    "Tech": "Improve technical depth and stay updated with new technologies",
    "Management": "Strengthen leadership and team management skills",
    "Marketing_Sales": "Improve communication and market understanding",
    "HR": "Focus on people management and organizational development",
    "Finance": "Enhance financial analysis and strategic planning skills",
    "Design": "Build strong design thinking and creativity",
    "Operations": "Improve process efficiency and execution skills",
}


def generate_recommendations_app1(job_group, experience_category, senior):

    recs = list(APP1_BASE_RECS.get(experience_category, [
        "Improve your skills and experience",
        "Work on practical projects"
    ]))

    role_tip = APP1_ROLE_RECS.get(job_group)
    if role_tip:
        recs.append(role_tip)

    # Senior-specific boost
    if senior == 1:
        recs.append("Negotiate for leadership responsibilities and higher compensation")

    return recs


# =========================================================
# APP 1 — MAIN FUNCTION
# =========================================================

def generate_insights_app1(input_dict):

    job_title = input_dict["Job Title"]
    experience = input_dict["Years of Experience"]
    senior = 1 if input_dict["Senior Position"] == "Yes" else 0

    # classification
    job_group = classify_job_group_app1(job_title)
    exp_category = get_experience_category_app1(experience)

    # recommendations
    recs = generate_recommendations_app1(job_group, exp_category, senior)

    return {
        "job_group": job_group,
        "experience_category": exp_category,
        #"recommendations": recs
    }

# =========================================================
# RENDER FUNCTION (MATCHES NEGOTIATION TIPS STYLE)
# =========================================================

def render_recommendations(recommendations):
    import streamlit as st

    if not recommendations:
        st.info("No recommendations available.")
        return

    for r in recommendations:
        st.markdown(f"- {r}")