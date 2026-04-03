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
# RENDER FUNCTION (MATCHES NEGOTIATION TIPS STYLE)
# =========================================================

def render_recommendations(recommendations):
    import streamlit as st

    if not recommendations:
        st.info("No recommendations available.")
        return

    for r in recommendations:
        st.markdown(f"- {r}")