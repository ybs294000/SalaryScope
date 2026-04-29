from __future__ import annotations

import re
from typing import Any


_SECTION_PATTERNS = {
    "experience": [r"\bexperience\b", r"\bwork history\b", r"\bemployment\b"],
    "education": [r"\beducation\b", r"\bacademics?\b", r"\bqualifications?\b"],
    "skills": [r"\bskills?\b", r"\btechnical skills?\b", r"\btech stack\b"],
    "projects": [r"\bprojects?\b", r"\bportfolio\b"],
    "summary": [r"\bsummary\b", r"\bprofile\b", r"\bobjective\b", r"\babout me\b"],
}

_APP1_ROLE_SKILLS = {
    "software engineer": {"python", "java", "c++", "c#", "javascript", "sql", "git", "docker", "api"},
    "data scientist": {"python", "sql", "machine learning", "deep learning", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "statistics"},
    "data analyst": {"sql", "excel", "power bi", "tableau", "pandas", "statistics", "data analysis", "data visualization"},
    "data engineer": {"python", "sql", "spark", "airflow", "kafka", "aws", "gcp", "azure", "docker"},
    "web developer": {"html", "css", "javascript", "typescript", "api", "react", "django", "flask"},
    "devops engineer": {"docker", "linux", "aws", "azure", "gcp", "kubernetes", "git"},
    "project manager": {"excel", "jira", "agile", "scrum", "stakeholder management"},
    "product manager": {"analytics", "sql", "product strategy", "experimentation", "stakeholder management"},
    "human resources manager": {"recruitment", "hr", "talent acquisition", "people operations"},
    "financial analyst": {"excel", "financial analysis", "forecasting", "power bi", "tableau"},
    "marketing manager": {"seo", "content marketing", "google analytics", "campaign management", "social media"},
    "sales manager": {"crm", "salesforce", "lead generation", "negotiation", "client management"},
    "sales representative": {"crm", "lead generation", "negotiation", "client management"},
    "ui/ux designer": {"figma", "wireframing", "prototyping", "user research", "design systems"},
    "cybersecurity analyst": {"security", "siem", "network security", "incident response", "linux"},
    "cloud engineer": {"aws", "azure", "gcp", "docker", "kubernetes", "linux"},
    "qa engineer": {"testing", "selenium", "automation", "api", "sql"},
}

_APP2_DS_SKILLS = {
    "python", "r", "sql", "machine learning", "deep learning", "tensorflow", "pytorch",
    "scikit-learn", "sklearn", "pandas", "numpy", "spark", "hadoop", "tableau", "power bi",
    "natural language processing", "nlp", "computer vision", "xgboost", "lightgbm", "statistics",
    "probability", "data analysis", "data visualization", "matplotlib", "seaborn", "plotly",
    "aws", "azure", "gcp", "docker", "git", "github", "flask", "fastapi", "feature engineering",
    "model deployment", "mlops", "airflow", "dbt", "kafka",
}

_APP2_DIRECT_ROLES = {
    "Data Scientist", "Machine Learning Engineer", "Research Scientist", "AI Developer", "Analytics Engineer"
}
_APP2_ADJACENT_ROLES = {
    "Data Analyst", "Data Engineer", "Data Architect", "Business Intelligence Engineer", "Data Manager"
}


def calculate_resume_screening_app1(raw_text: str, features: dict[str, Any], score_data: dict[str, Any]) -> dict[str, Any]:
    text = raw_text or ""
    text_l = text.lower()
    skills = [str(skill).lower() for skill in features.get("skills", [])]
    sources = features.get("sources", {}) or {}
    role_title = str(features.get("job_title", ""))
    role_key = role_title.lower()

    ats_score = _score_ats_readiness(
        text=text,
        text_l=text_l,
        skills=skills,
        has_experience=features.get("years_of_experience", 0) > 0,
        has_education=features.get("education_level", 1) is not None,
        source_signals=sources,
    )
    role_score = _score_role_match_app1(
        role_key=role_key,
        skills=skills,
        years_experience=float(features.get("years_of_experience", 0)),
        senior_flag=int(features.get("senior", 0)),
        score_data=score_data,
        source_signals=sources,
    )
    confidence_score = _score_parse_confidence_app1(
        text=text,
        skills=skills,
        source_signals=sources,
        years_experience=float(features.get("years_of_experience", 0)),
    )

    strengths: list[str] = []
    gaps: list[str] = []
    improvements: list[str] = []

    if features.get("years_of_experience", 0) > 0:
        strengths.append("The resume provides readable experience information that can be screened automatically.")
    else:
        gaps.append("Years of experience are not clearly stated in the extracted resume text.")
        improvements.append("Add an explicit experience timeline with role dates or a summary such as '5+ years of experience'.")

    if len(skills) >= 6:
        strengths.append("Technical skill coverage is broad enough to support stronger automated role matching.")
    elif len(skills) == 0:
        gaps.append("The resume does not expose a clear skills section for the parser.")
        improvements.append("Add a dedicated skills section with tools, languages, and platforms written as plain text.")
    else:
        improvements.append("Expand the skills section with role-relevant tools and technologies written in exact terms.")

    if sources.get("job_title") not in {"default", "fallback"}:
        strengths.append("A role title was matched directly from the resume, which improves screening consistency.")
    else:
        gaps.append("The job title is not clearly expressed enough for a confident role match.")
        improvements.append("Use a clear, standard title near the top of the resume, such as 'Data Analyst' or 'Software Engineer'.")

    if _has_layout_risk(text):
        gaps.append("The extracted text shows formatting signals that may reduce parsing reliability in screening systems.")
        improvements.append("Use a simpler one-column layout and avoid text boxes, complex tables, and image-heavy formatting.")

    return _finalize_screening_result(
        ats_score=ats_score,
        role_score=role_score,
        confidence_score=confidence_score,
        strengths=strengths,
        gaps=gaps,
        improvements=improvements,
    )


def calculate_resume_screening_app2(raw_text: str, features: dict[str, Any], score_data: dict[str, Any]) -> dict[str, Any]:
    text = raw_text or ""
    text_l = text.lower()
    skills = [str(skill).lower() for skill in features.get("skills_a2", [])]
    sources = features.get("sources_a2", {}) or {}
    role_title = str(features.get("job_title_a2", ""))

    ats_score = _score_ats_readiness(
        text=text,
        text_l=text_l,
        skills=skills,
        has_experience=features.get("years_of_experience_a2", 0) > 0,
        has_education=True,
        source_signals=sources,
    )
    role_score = _score_role_match_app2(
        role_title=role_title,
        skills=skills,
        years_experience=float(features.get("years_of_experience_a2", 0)),
        score_data=score_data,
        source_signals=sources,
    )
    confidence_score = _score_parse_confidence_app2(
        text=text,
        skills=skills,
        source_signals=sources,
        years_experience=float(features.get("years_of_experience_a2", 0)),
    )

    strengths: list[str] = []
    gaps: list[str] = []
    improvements: list[str] = []

    ds_skill_count = int(score_data.get("ds_skill_count_a2", 0))
    if ds_skill_count >= 5:
        strengths.append("The resume shows strong data and machine-learning keyword coverage for automated matching.")
    elif ds_skill_count == 0:
        gaps.append("Few or no DS/ML-specific keywords were detected for the current role family.")
        improvements.append("Add role-relevant tools such as Python, SQL, scikit-learn, Spark, or cloud platforms in plain text.")
    else:
        improvements.append("Strengthen DS/ML keyword coverage with the exact tools, frameworks, and methods used in your projects.")

    if role_title in _APP2_DIRECT_ROLES:
        strengths.append("The extracted role title aligns directly with the data and machine-learning domain.")
    elif role_title in _APP2_ADJACENT_ROLES:
        strengths.append("The extracted role is adjacent to the target domain and still supports meaningful screening.")
    else:
        gaps.append("The extracted title is broad or indirect for a dedicated data role screening flow.")
        improvements.append("Use a clearer role title near the top of the resume if you are targeting data or ML positions.")

    if sources.get("country") == "default":
        gaps.append("Location details were not confidently extracted, which can weaken automated screening context.")
        improvements.append("Include a city and country line near your contact details.")

    if _has_layout_risk(text):
        gaps.append("The extracted text shows formatting signals that may reduce parsing reliability in screening systems.")
        improvements.append("Use a simpler one-column layout and avoid text boxes, complex tables, and image-heavy formatting.")

    return _finalize_screening_result(
        ats_score=ats_score,
        role_score=role_score,
        confidence_score=confidence_score,
        strengths=strengths,
        gaps=gaps,
        improvements=improvements,
    )


def _score_ats_readiness(
    *,
    text: str,
    text_l: str,
    skills: list[str],
    has_experience: bool,
    has_education: bool,
    source_signals: dict[str, Any],
) -> int:
    score = 0
    char_count = len(text.strip())

    if char_count >= 1800:
        score += 20
    elif char_count >= 1000:
        score += 16
    elif char_count >= 600:
        score += 10
    else:
        score += 4

    section_hits = sum(
        1 for patterns in _SECTION_PATTERNS.values()
        if any(re.search(pattern, text_l) for pattern in patterns)
    )
    score += min(section_hits * 4, 20)

    if re.search(r"[\w.\-+%]+@[\w.\-]+\.\w+", text):
        score += 6
    if _looks_like_phone(text):
        score += 6
    if "linkedin.com" in text_l or "github.com" in text_l:
        score += 4

    if has_experience:
        score += 10
    if has_education:
        score += 8
    if skills:
        score += min(len(skills), 6) * 2

    if source_signals.get("job_title") not in {"default", "fallback"}:
        score += 8
    if str(source_signals.get("country", "")).startswith(("ner:", "alias:")):
        score += 6

    if _has_layout_risk(text):
        score -= 12

    return _clamp_score(score)


def _score_role_match_app1(
    *,
    role_key: str,
    skills: list[str],
    years_experience: float,
    senior_flag: int,
    score_data: dict[str, Any],
    source_signals: dict[str, Any],
) -> int:
    score = 0
    skill_set = set(skills)

    if source_signals.get("job_title") not in {"default", "fallback"}:
        score += 30
    elif role_key:
        score += 18

    expected_skills = _APP1_ROLE_SKILLS.get(role_key, set())
    matched_role_skills = len(skill_set & expected_skills)
    if expected_skills:
        score += min(matched_role_skills * 7, 35)
    else:
        score += min(len(skill_set), 5) * 4

    if years_experience >= 6 and senior_flag:
        score += 15
    elif years_experience >= 2:
        score += 10
    elif years_experience > 0:
        score += 6

    if score_data.get("total_score", 0) >= 70:
        score += 12
    elif score_data.get("total_score", 0) >= 40:
        score += 8
    else:
        score += 4

    return _clamp_score(score)


def _score_role_match_app2(
    *,
    role_title: str,
    skills: list[str],
    years_experience: float,
    score_data: dict[str, Any],
    source_signals: dict[str, Any],
) -> int:
    score = 0
    skill_set = set(skills)
    ds_skill_count = len(skill_set & _APP2_DS_SKILLS)

    if role_title in _APP2_DIRECT_ROLES:
        score += 32
    elif role_title in _APP2_ADJACENT_ROLES:
        score += 22
    elif source_signals.get("job_title") != "default":
        score += 14

    score += min(ds_skill_count * 6, 42)

    if years_experience >= 6:
        score += 16
    elif years_experience >= 3:
        score += 12
    elif years_experience > 0:
        score += 8

    if score_data.get("total_score_a2", 0) >= 65:
        score += 10
    elif score_data.get("total_score_a2", 0) >= 35:
        score += 6
    else:
        score += 3

    return _clamp_score(score)


def _score_parse_confidence_app1(
    *,
    text: str,
    skills: list[str],
    source_signals: dict[str, Any],
    years_experience: float,
) -> int:
    score = 18
    if len(text.strip()) >= 900:
        score += 12
    if years_experience > 0:
        score += 12
    if skills:
        score += min(len(skills), 5) * 4
    if source_signals.get("education") != "default_bachelor":
        score += 14
    if source_signals.get("job_title") not in {"default", "fallback"}:
        score += 18
    if str(source_signals.get("country", "")).startswith(("ner:", "alias:")):
        score += 14
    if _has_layout_risk(text):
        score -= 14
    return _clamp_score(score)


def _score_parse_confidence_app2(
    *,
    text: str,
    skills: list[str],
    source_signals: dict[str, Any],
    years_experience: float,
) -> int:
    score = 20
    if len(text.strip()) >= 900:
        score += 12
    if years_experience > 0:
        score += 14
    if skills:
        score += min(len(skills), 5) * 4
    if source_signals.get("job_title") not in {"default", "keyword_fallback"}:
        score += 18
    elif source_signals.get("job_title") == "keyword_fallback":
        score += 10
    if source_signals.get("country") != "default":
        score += 16
    if _has_layout_risk(text):
        score -= 14
    return _clamp_score(score)


def _finalize_screening_result(
    *,
    ats_score: int,
    role_score: int,
    confidence_score: int,
    strengths: list[str],
    gaps: list[str],
    improvements: list[str],
) -> dict[str, Any]:
    overall = round(ats_score * 0.40 + role_score * 0.45 + confidence_score * 0.15)

    if overall >= 80:
        band = "Strong"
        headline = "This resume looks strong for automated screening."
    elif overall >= 60:
        band = "Good"
        headline = "This resume is reasonably screening-friendly but still has room to improve."
    elif overall >= 40:
        band = "Mixed"
        headline = "This resume may pass some screening checks, but several signals look weak or incomplete."
    else:
        band = "Needs Work"
        headline = "This resume may struggle in automated screening without clearer structure and stronger keyword coverage."

    unique_strengths = _dedupe_preserve_order(strengths)[:4]
    unique_gaps = _dedupe_preserve_order(gaps)[:4]
    unique_improvements = _dedupe_preserve_order(improvements)[:4]

    if not unique_strengths:
        unique_strengths = ["The resume still provides enough extracted content to support a structured review."]
    if not unique_gaps:
        unique_gaps = ["No major screening gaps were detected from the extracted text."]
    if not unique_improvements:
        unique_improvements = ["Keep titles, skills, and experience phrasing specific and easy to parse."]

    return {
        "overall_score": int(_clamp_score(overall)),
        "overall_band": band,
        "headline": headline,
        "ats_readiness_score": int(ats_score),
        "role_match_score": int(role_score),
        "parse_confidence_score": int(confidence_score),
        "strengths": unique_strengths,
        "gaps": unique_gaps,
        "improvements": unique_improvements,
        "score_notes": {
            "ats_readiness": "ATS Readiness reflects how clearly the resume is structured for automated parsing.",
            "role_match": "Role Match reflects how well the extracted title, skills, and experience align with the detected role path.",
            "parse_confidence": "Parse Confidence reflects how confidently SalaryScope could extract important resume details from the PDF.",
        },
    }


def _has_layout_risk(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return True

    short_lines = sum(1 for line in lines if len(line) <= 3)
    fragmented_ratio = short_lines / max(len(lines), 1)
    pipe_count = text.count("|")
    tab_like = text.count("\t")
    repeated_spacing = len(re.findall(r" {4,}", text))

    return fragmented_ratio > 0.20 or pipe_count >= 6 or tab_like >= 10 or repeated_spacing >= 12


def _looks_like_phone(text: str) -> bool:
    return bool(re.search(r"(\+\d{1,3}[\s\-]?)?(\(?\d{2,4}\)?[\s\-]?)?\d{3}[\s\-]?\d{3,4}", text))


def _clamp_score(value: int | float) -> int:
    return int(max(0, min(100, round(float(value)))))


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
