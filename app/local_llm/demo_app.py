"""
Standalone Streamlit demo for local LLM experimentation.

Run separately from the main app:
    streamlit run app/local_llm/demo_app.py
"""

from __future__ import annotations

import streamlit as st

from app.local_llm.client import LocalLLMError
from app.local_llm.config import LocalLLMConfig
from app.local_llm.service import (
    generate_negotiation_script,
    generate_resume_summary,
    is_local_llm_available,
)


st.set_page_config(
    page_title="SalaryScope Local LLM Demo",
    page_icon=":material/smart_toy:",
    layout="wide",
)

st.title(":material/smart_toy: SalaryScope Local LLM Demo")
st.caption(
    "Standalone prototype for optional local AI features. "
    "This page does not modify the main SalaryScope application."
)

config = LocalLLMConfig.from_env()
available, status = is_local_llm_available()

col_a, col_b = st.columns([1, 2])
with col_a:
    st.metric("Model", config.model)
with col_b:
    st.info(status if available else f"Unavailable: {status}")

if not available:
    st.warning(
        "Start Ollama locally before using this demo. Example:\n"
        "`ollama run llama3.2:3b`"
    )

tab_resume, tab_negotiation = st.tabs(
    [
        ":material/description: Resume Summary",
        ":material/forum: Negotiation Script",
    ]
)

with tab_resume:
    st.subheader("Resume Summary Draft")
    c1, c2 = st.columns(2)
    with c1:
        candidate_name = st.text_input("Candidate Name", value="Alex Morgan")
        target_role = st.text_input("Target Role", value="Data Analyst")
        years_experience = st.text_input("Years of Experience", value="3 years")
    with c2:
        education = st.text_input("Education", value="B.Tech in Computer Engineering")
        skills_csv = st.text_input(
            "Skills",
            value="Python, SQL, Power BI, Excel, Machine Learning",
        )

    resume_text = st.text_area(
        "Resume Text",
        value=(
            "Worked on dashboarding, exploratory data analysis, and model building. "
            "Built Python and SQL workflows for reporting. "
            "Completed internships involving data cleaning, visualization, and business insights."
        ),
        height=180,
    )

    if st.button("Generate Resume Summary", type="primary", width="stretch"):
        try:
            result = generate_resume_summary(
                candidate_name=candidate_name,
                target_role=target_role,
                years_experience=years_experience,
                education=education,
                skills_csv=skills_csv,
                resume_text=resume_text,
            )
            st.success(f"Generated with {result['model']}")
            st.text_area("Generated Summary", value=result["content"], height=280)
        except LocalLLMError as exc:
            st.error(str(exc))

with tab_negotiation:
    st.subheader("Negotiation Draft Package")
    c1, c2 = st.columns(2)
    with c1:
        job_title = st.text_input("Job Title", value="Data Scientist", key="neg_job_title")
        location = st.text_input("Location", value="Bengaluru, India", key="neg_location")
        years_experience_neg = st.text_input(
            "Years of Experience",
            value="2 years",
            key="neg_exp",
        )
        predicted_salary_text = st.text_input(
            "Predicted Salary Reference",
            value="$18,000 annual salary equivalent",
            key="neg_predicted",
        )
    with c2:
        target_salary_text = st.text_input(
            "Target Salary",
            value="$20,000 annual salary equivalent",
            key="neg_target",
        )
        negotiation_style = st.selectbox(
            "Negotiation Style",
            [
                "Professional and confident",
                "Formal and concise",
                "Warm and collaborative",
            ],
        )

    extra_context = st.text_area(
        "Additional Context",
        value="Candidate has internship experience and strong SQL plus dashboarding skills.",
        height=120,
    )

    if st.button("Generate Negotiation Script", type="primary", width="stretch"):
        try:
            result = generate_negotiation_script(
                job_title=job_title,
                location=location,
                years_experience=years_experience_neg,
                predicted_salary_text=predicted_salary_text,
                target_salary_text=target_salary_text,
                negotiation_style=negotiation_style,
                extra_context=extra_context,
            )
            st.success(f"Generated with {result['model']}")
            st.text_area("Generated Draft", value=result["content"], height=320)
        except LocalLLMError as exc:
            st.error(str(exc))

st.divider()
st.caption(
    "This prototype is intentionally optional and non-critical. "
    "Salary prediction should remain with the existing ML models."
)
