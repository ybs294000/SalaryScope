# negotiation_tips.py

# --------------------------------------------------
# APP 1 (Random Forest Model)
# --------------------------------------------------

def generate_negotiation_tips_app1(
    prediction,
    salary_band_label,
    career_stage_label,
    experience,
    job_title,
    country,
    senior,
    market_type
):
    tips = []

    # 1. Experience (numeric float from app.py)
    if experience < 2:
        tips.append("Focus on gaining skills and experience before negotiating aggressively.")
    elif experience < 7:
        tips.append("Use your past projects and performance to justify a higher salary.")
    else:
        tips.append("Leverage your experience and achievements to negotiate a strong compensation package.")

    # 2. Senior flag (0/1)
    if senior == 1:
        tips.append("For senior roles, negotiate additional benefits like bonuses and leadership perks.")
    else:
        tips.append("Highlight measurable contributions to strengthen your negotiation position.")

    # 3. Country (must support 'Other')
    if country == "Other":
        tips.append("Research salary benchmarks for your region before negotiating.")
    else:
        tips.append("Compare salaries for similar roles in your country to support negotiation.")

    return tips[:3]


# --------------------------------------------------
# APP 2 (XGBoost Model)
# --------------------------------------------------

def generate_negotiation_tips_app2(
    prediction,
    experience_label,
    company_size_label,
    remote_label,
    company_location,
    job_title,
    role,
    market_type
):
    tips = []

    # 1. Experience Level (human-readable labels from app.py)
    if experience_label == "Entry Level":
        tips.append("Focus on learning opportunities and skill growth early in your career.")
    elif experience_label == "Mid Level":
        tips.append("Use your past experience and project impact to negotiate better compensation.")
    elif experience_label == "Senior Level":
        tips.append("Senior professionals should negotiate based on expertise and impact.")
    else:  # Executive Level
        tips.append("Executive roles should negotiate total compensation including bonuses and benefits.")

    # 2. Company Size (human-readable labels)
    if company_size_label == "Small Company":
        tips.append("Smaller companies may offer flexibility but limited salary growth.")
    elif company_size_label == "Medium Company":
        tips.append("Medium companies provide balanced growth and negotiation opportunities.")
    else:  # Large Company
        tips.append("Larger companies often provide structured salary bands and benefits.")

    # 3. Work Mode (IMPORTANT: exact strings)
    if remote_label == "Fully Remote":
        tips.append("Remote roles allow negotiation based on broader market standards.")
    elif remote_label == "Hybrid":
        tips.append("Hybrid roles allow negotiation on flexibility and work-life balance.")
    else:  # On-site
        tips.append("On-site roles may provide stability and additional benefits.")

    return tips[:3]


# --------------------------------------------------
# RENDER FUNCTION
# --------------------------------------------------

def render_negotiation_tips(tips):
    import streamlit as st

    for tip in tips:
        st.markdown(f"- {tip}")