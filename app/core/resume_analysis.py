import re
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import pdfplumber
import spacy
import streamlit as st
from spacy.matcher import PhraseMatcher


# ============================================================
# CACHE NLP MODEL
# ============================================================

@st.cache_resource
def load_spacy_model():
    return spacy.load("en_core_web_sm", disable=["parser", "textcat"])


# ============================================================
# LEXICONS
# ============================================================

SKILL_PATTERNS = [
    "python", "java", "c", "c++", "c#", "javascript", "typescript",
    "sql", "mysql", "postgresql", "mongodb", "sqlite",
    "html", "css", "bootstrap", "tailwind",
    "machine learning", "deep learning", "artificial intelligence",
    "natural language processing", "nlp", "computer vision",
    "data analysis", "data analytics", "data visualization",
    "pandas", "numpy", "matplotlib", "seaborn", "plotly",
    "scikit-learn", "sklearn", "tensorflow", "keras", "pytorch",
    "xgboost", "lightgbm", "opencv", "flask", "django", "streamlit",
    "git", "github", "docker", "linux", "aws", "azure", "gcp",
    "power bi", "tableau", "excel", "statistics", "probability",
    "regression", "classification", "clustering", "feature engineering",
    "model deployment", "api", "rest api", "firebase"
]
# ADD BELOW EXISTING SKILL_PATTERNS
SKILL_PATTERNS += [
    # Data / Engineering
    "spark", "hadoop", "airflow", "kafka", "dbt",

    # APIs / Backend
    "fastapi", "graphql",

    # MLOps / Deployment
    "mlops", "kubectl", "kubernetes",

    # Version / Tools
    "gitlab", "bitbucket",

    # BI / Analytics
    "looker", "sas",

    # General
    "problem solving", "data structures", "algorithms"
]
JOB_TITLE_ALIASES = {
    "data engineer": [
        "data engineer"
    ],
    "software engineer": [
        "software engineer", "software developer", "developer", "application developer"
    ],
    "data scientist": [
        "data scientist", "machine learning engineer", "ml engineer", "ai engineer"
    ],    
    "data analyst": [
        "data analyst", "business analyst", "analytics analyst"
    ],
    "web developer": [
        "web developer", "frontend developer", "backend developer", "full stack developer", "full-stack developer"
    ],
    "devops engineer": [
        "devops engineer", "site reliability engineer", "sre"
    ],
    "project manager": [
        "project manager", "program manager"
    ],
    "product manager": [
        "product manager"
    ],
    "system administrator": [
        "system administrator", "sysadmin"
    ],
    "network engineer": [
        "network engineer", "network administrator"
    ],
    "database administrator": [
        "database administrator", "dba"
    ],
    "ui ux designer": [
        "ui designer", "ux designer", "ui/ux designer", "product designer", "graphic designer"
    ],
    "cybersecurity analyst": [
        "cybersecurity analyst", "security analyst", "information security analyst"
    ],
    "cloud engineer": [
        "cloud engineer", "cloud architect"
    ],
    "qa engineer": [
        "qa engineer", "test engineer", "software tester", "quality assurance engineer"
    ]
}

# ============================
# APP1 DATASET EXPANSION 
# ============================

JOB_TITLE_ALIASES.update({

    # --------------------------------
    # EXTENDED SOFTWARE / TECH
    # --------------------------------
    "software engineer": [
        "software engineer manager",
        "software architect",
        "principal engineer",
        "software manager"
    ],

    "web developer": [
        "full stack engineer",
        "front end developer",
        "back end developer",
        "frontend developer",
        "backend developer"
    ],

    "data scientist": [
        "research scientist",
        "scientist",
        "principal scientist"
    ],

    "data analyst": [
        "operations analyst",
        "business operations analyst"
    ],

    "devops engineer": [
        "it manager",
        "it consultant",
        "it support specialist",
        "technical support specialist",
        "help desk analyst"
    ],

    "network engineer": [
        "it support"
    ],

    # --------------------------------
    # MANAGEMENT EXTENSIONS
    # --------------------------------
    "project manager": [
        "project engineer",
        "project coordinator"
    ],

    "product manager": [
        "product development manager"
    ],

    # --------------------------------
    # MARKETING (NEW CATEGORY)
    # --------------------------------
    "marketing manager": [
        "marketing manager",
        "marketing coordinator",
        "marketing analyst",
        "marketing director",
        "digital marketing manager",
        "content marketing manager",
        "product marketing manager",
        "marketing specialist",
        "digital marketing specialist",
        "social media manager",
        "social media specialist",
        "public relations manager",
        "advertising coordinator"
    ],

    # --------------------------------
    # SALES (NEW CATEGORY)
    # --------------------------------
    "sales representative": [
        "sales associate",
        "sales representative",
        "sales executive"
    ],

    "sales manager": [
        "sales manager",
        "sales director",
        "sales operations manager"
    ],

    # --------------------------------
    # HR (NEW CATEGORY)
    # --------------------------------
    "hr manager": [
        "human resources manager",
        "hr manager",
        "hr generalist",
        "hr coordinator",
        "human resources coordinator",
        "human resources specialist",
        "recruiter",
        "technical recruiter"
    ],

    # --------------------------------
    # FINANCE (NEW CATEGORY)
    # --------------------------------
    "financial analyst": [
        "financial analyst",
        "financial manager",
        "financial advisor",
        "accountant"
    ],

    # --------------------------------
    # DESIGN EXTENSIONS
    # --------------------------------
    "ui ux designer": [
        "ux researcher",
        "designer"
    ],

    # --------------------------------
    # OPERATIONS / GENERAL
    # --------------------------------
    "project manager": [
        "operations manager",
        "operations coordinator",
        "operations director"
    ]

})
EDUCATION_PATTERNS = {
    3: [
        "phd", "ph.d", "doctorate", "doctoral"
    ],
    2: [
        "m.tech", "mtech", "master of technology", "master of science", "msc",
        "m.sc", "ms", "m.e", "me", "mba", "master's", "masters"
    ],
    1: [
        "b.tech", "btech", "bachelor of technology", "bachelor of engineering",
        "b.e", "be", "b.sc", "bsc", "bca", "bachelor", "undergraduate"
    ],
    0: [
        "high school", "secondary school", "12th", "12th grade", "higher secondary"
    ]
}

COUNTRY_ALIASES = {
    "usa": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "us": "USA",
    "india": "India",
    "uk": "UK",
    "united kingdom": "UK",
    "england": "UK",
    "canada": "Canada",
    "germany": "Germany",
    "france": "France",
    "australia": "Australia",
    "singapore": "Singapore",
    "netherlands": "Netherlands",
    "spain": "Spain",
    "italy": "Italy",
    "japan": "Japan",
    "brazil": "Brazil",
    "mexico": "Mexico"
}


# ============================================================
# MATCHER BUILDERS
# ============================================================

@st.cache_resource
def build_skill_matcher():
    nlp = load_spacy_model()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in SKILL_PATTERNS]
    matcher.add("SKILLS", patterns)
    return matcher


@st.cache_resource
def build_job_title_matcher():
    nlp = load_spacy_model()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    phrase_to_canonical = {}
    all_phrases = []

    for canonical, aliases in JOB_TITLE_ALIASES.items():
        for alias in aliases:
            phrase_to_canonical[alias.lower()] = canonical
            all_phrases.append(nlp.make_doc(alias))

    matcher.add("JOB_TITLE", all_phrases)
    return matcher, phrase_to_canonical


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_text_from_pdf(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    uploaded_file.seek(0)
    pdf_bytes = uploaded_file.read()

    text_parts = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)

    uploaded_file.seek(0)
    return "\n".join(text_parts).strip()


# ============================================================
# CLEANING / PREPROCESSING
# ============================================================

def normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def preprocess_resume_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\bwww\.\S+\b", " ", text)
    return normalize_whitespace(text)


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_experience_years(text: str) -> float:
    text_l = text.lower()

    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)\s+(?:of\s+)?experience",
        r"experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|year|yrs|yr)"
    ]

    values = []
    for pattern in patterns:
        matches = re.findall(pattern, text_l)
        for match in matches:
            try:
                val = float(match)
                if 0 <= val <= 40:
                    values.append(val)
            except Exception:
                pass

    if not values:
        return 0.0

    return max(values)


def extract_education_level(text: str):
    text_l = text.lower()

    phd_patterns = [r"\bphd\b", r"\bph\.d\b", r"\bdoctorate\b"]
    masters_patterns = [
        r"\bm\.tech\b", r"\bmtech\b", r"\bmaster of\b",
        r"\bmsc\b", r"\bm\.sc\b", r"\bms\b", r"\bm\.e\b", r"\bme\b", r"\bmba\b"
    ]
    bachelors_patterns = [
        r"\bb\.tech\b", r"\bbtech\b", r"\bbachelor of\b",
        r"\bb\.e\b", r"\bbe\b", r"\bbsc\b", r"\bb\.sc\b", r"\bbca\b"
    ]

    for pattern in phd_patterns:
        if re.search(pattern, text_l):
            return 3, "phd"

    for pattern in masters_patterns:
        if re.search(pattern, text_l):
            return 2, "masters"

    for pattern in bachelors_patterns:
        if re.search(pattern, text_l):
            return 1, "bachelors"

    return 1, "default_bachelor"


def extract_skills(text: str) -> List[str]:
    nlp = load_spacy_model()
    matcher = build_skill_matcher()
    doc = nlp(text)

    matches = matcher(doc)
    found = set()

    for _, start, end in matches:
        skill = doc[start:end].text.strip()
        if skill:
            found.add(skill.title() if skill.lower() != "nlp" else "NLP")

    # Always return a plain list — never a set or tuple
    return sorted(list(found))


def extract_job_title(text: str, allowed_job_titles: List[str]) -> Tuple[str, str]:
    nlp = load_spacy_model()
    matcher, phrase_to_canonical = build_job_title_matcher()
    doc = nlp(text)

    matches = matcher(doc)
    candidates = []

    for _, start, end in matches:
        raw_phrase = doc[start:end].text.lower().strip()
        canonical = phrase_to_canonical.get(raw_phrase)
        if canonical:
            candidates.append((raw_phrase, canonical))

    if not candidates:
        return "Software Engineer" if "Software Engineer" in allowed_job_titles else allowed_job_titles[0], "default"

    canonical_rank_map = {
        "data engineer": "Data Engineer",
        "software engineer": "Software Engineer",
        "data scientist": "Data Scientist",
        "data analyst": "Data Analyst",
        "web developer": "Web Developer",
        "devops engineer": "DevOps Engineer",
        "project manager": "Project Manager",
        "product manager": "Product Manager",
        "system administrator": "System Administrator",
        "network engineer": "Network Engineer",
        "database administrator": "Database Administrator",
        "ui ux designer": "UI/UX Designer",
        "cybersecurity analyst": "Cybersecurity Analyst",
        "cloud engineer": "Cloud Engineer",
        "qa engineer": "QA Engineer"
    }

    canonical_rank_map.update({
        "marketing manager": "Marketing Manager",
        "sales manager": "Sales Manager",
        "sales representative": "Sales Representative",
        "hr manager": "Human Resources Manager",
        "financial analyst": "Financial Analyst"
    })

    for raw_phrase, canonical in candidates:
        mapped = canonical_rank_map.get(canonical, canonical.title())
        if mapped in allowed_job_titles:
            return mapped, raw_phrase

    candidate_words = [canonical_rank_map.get(c, c.title()) for _, c in candidates]
    for c in candidate_words:
        if c in allowed_job_titles:
            return c, "matcher"

    return "Software Engineer" if "Software Engineer" in allowed_job_titles else allowed_job_titles[0], "fallback"


def extract_country(text: str, allowed_countries: List[str]) -> Tuple[str, str]:
    nlp = load_spacy_model()
    doc = nlp(text)

    gpe_candidates = []
    for ent in doc.ents:
        if ent.label_ in {"GPE", "LOC"}:
            gpe_candidates.append(ent.text.strip().lower())

    for gpe in gpe_candidates:
        mapped = COUNTRY_ALIASES.get(gpe)
        if mapped and mapped in allowed_countries:
            return mapped, f"ner:{gpe}"

    text_l = text.lower()
    for alias, mapped in COUNTRY_ALIASES.items():
        if alias in text_l and mapped in allowed_countries:
            return mapped, f"alias:{alias}"

    if "Other" in allowed_countries:
        return "Other", "default_other"

    return allowed_countries[0], "default"


def derive_senior_flag(experience: float, job_title: str) -> int:
    title_l = job_title.lower()
    if experience >= 6:
        return 1
    if any(k in title_l for k in ["senior", "lead", "principal", "manager", "director"]):
        return 1
    return 0


def extract_resume_features(
    raw_text: str,
    allowed_job_titles: List[str],
    allowed_countries: List[str]
) -> Dict:
    text = preprocess_resume_text(raw_text)

    experience = extract_experience_years(text)
    education_level, education_source = extract_education_level(text)
    skills = extract_skills(text)          # plain list of strings
    job_title, job_title_source = extract_job_title(text, allowed_job_titles)
    country, country_source = extract_country(text, allowed_countries)
    senior = derive_senior_flag(experience, job_title)

    return {
        "years_of_experience": float(experience),
        "education_level": int(education_level),
        "job_title": str(job_title),
        "country": str(country),
        "senior": int(senior),
        # FIX: store as plain list of str — tuples cause pandas hashing crash
        "skills": skills,
        "skills_str": ", ".join(skills),
        # FIX: sources values are all plain strings — safe for session_state hashing
        "sources": {
            "experience": "regex",
            "education": str(education_source),
            "job_title": str(job_title_source),
            "country": str(country_source),
            "skills": "spacy_phrase_matcher"
        }
    }


# ============================================================
# RESUME SCORING
# ============================================================

def score_experience(exp: float) -> Tuple[int, str]:
    if exp <= 0:
        return 0, "No clear experience found"
    if exp <= 2:
        return 10, "Entry-level experience"
    if exp <= 5:
        return 25, "Developing professional experience"
    if exp <= 10:
        return 40, "Strong professional experience"
    return 50, "Highly experienced profile"


def score_education(level: int) -> Tuple[int, str]:
    mapping = {
        0: (5, "High school level"),
        1: (15, "Bachelor's level"),
        2: (25, "Master's level"),
        3: (35, "PhD level")
    }
    return mapping.get(level, (10, "Default education score"))


def score_skills(skills: List[str]) -> Tuple[int, str]:
    score = min(len(skills) * 5, 30)
    if len(skills) == 0:
        note = "No major skills detected"
    elif len(skills) <= 3:
        note = "Basic technical skill coverage"
    elif len(skills) <= 6:
        note = "Good technical skill coverage"
    else:
        note = "Strong technical skill coverage"
    return score, note


def calculate_resume_score(features: Dict) -> Dict:
    exp_score, exp_note = score_experience(features["years_of_experience"])
    edu_score, edu_note = score_education(features["education_level"])
    # FIX: features["skills"] is now always a plain list — no conversion needed
    skill_score, skill_note = score_skills(features["skills"])

    total = min(exp_score + edu_score + skill_score, 100)

    if total < 40:
        level = "Basic"
    elif total < 70:
        level = "Moderate"
    else:
        level = "Strong"

    return {
        "total_score": int(total),
        "level": str(level),
        "experience_score": int(exp_score),
        "experience_note": str(exp_note),
        "education_score": int(edu_score),
        "education_note": str(edu_note),
        "skills_score": int(skill_score),
        "skills_note": str(skill_note),
        # FIX: plain list of str — no tuple, no set
        "skills_detected": list(features["skills"]),
        "skills_detected_str": ", ".join(features["skills"])
    }


# ============================================================
# DISPLAY HELPERS
# ============================================================

def education_label(level: int) -> str:
    return {
        0: "High School",
        1: "Bachelor's Degree",
        2: "Master's Degree",
        3: "PhD"
    }.get(level, "Unknown")

# ============================================================
# ================= APP 2 NLP ADDITIONS ======================
# (Fully independent of App 1 code above)
# All identifiers use _a2 suffix or app2_ prefix
# ============================================================

import re
from typing import List, Tuple, Dict


# ============================================================
# APP 2 — JOB TITLE PATTERNS
# Sourced from ds_salaries dataset top titles
# ============================================================

APP2_JOB_TITLE_PATTERNS_A2 = {
    "Data Engineer": [
        "data engineer", "big data engineer", "cloud data engineer",
        "data infrastructure engineer", "data operations engineer",
        "data devops engineer", "etl developer", "etl engineer",
        "lead data engineer", "principal data engineer",
        "software data engineer", "azure data engineer",
        "marketing data engineer", "bi data engineer",
        "machine learning infrastructure engineer",
        "cloud database engineer"
    ],
    "Data Scientist": [
        "data scientist", "applied data scientist", "lead data scientist",
        "principal data scientist", "staff data scientist",
        "data scientist lead", "product data scientist",
        "data science lead", "data science manager",
        "director of data science", "head of data science",
        "data science consultant", "data science engineer",
        "data science tech lead"
    ],
    "Data Analyst": [
        "data analyst", "business data analyst", "bi data analyst",
        "bi analyst", "bi developer", "bi developer",
        "product data analyst", "data quality analyst",
        "data operations analyst", "financial data analyst",
        "marketing data analyst", "data analytics specialist",
        "data analytics consultant", "data analytics lead",
        "data analytics manager", "lead data analyst",
        "principal data analyst", "staff data analyst",
        "compliance data analyst", "finance data analyst",
        "insight analyst"
    ],
    "Machine Learning Engineer": [
        "machine learning engineer", "ml engineer",
        "machine learning developer", "machine learning researcher",
        "machine learning scientist", "applied machine learning scientist",
        "applied machine learning engineer",
        "machine learning software engineer",
        "machine learning research engineer",
        "machine learning manager",
        "lead machine learning engineer",
        "principal machine learning engineer",
        "head of machine learning",
        "nlp engineer", "deep learning engineer",
        "deep learning researcher", "computer vision engineer",
        "computer vision software engineer",
        "3d computer vision researcher",
        "mlops engineer"
    ],
    "Analytics Engineer": [
        "analytics engineer", "data analytics engineer"
    ],
    "Data Architect": [
        "data architect", "big data architect", "cloud data architect",
        "principal data architect"
    ],
    "Research Scientist": [
        "research scientist", "research engineer",
        "applied scientist", "ai scientist"
    ],
    "AI Developer": [
        "ai developer", "ai programmer"
    ],
    "Data Manager": [
        "data manager", "data lead", "head of data",
        "data modeler", "data strategist", "data specialist",
        "data management specialist", "manager data management"
    ],
    "Business Intelligence Engineer": [
        "business intelligence engineer"
    ],
}

# Flat lookup: phrase → canonical title
_APP2_PHRASE_TO_TITLE_A2: Dict[str, str] = {}
for _canonical_a2, _aliases_a2 in APP2_JOB_TITLE_PATTERNS_A2.items():
    for _alias_a2 in _aliases_a2:
        _APP2_PHRASE_TO_TITLE_A2[_alias_a2.lower()] = _canonical_a2


# ============================================================
# APP 2 — COUNTRY → ISO CODE MAP
# Covers all 78 employee_residence codes in the dataset
# ============================================================

APP2_COUNTRY_TO_ISO_A2: Dict[str, str] = {
    # Full names
    "united states": "US", "united states of america": "US",
    "usa": "US", "us": "US",
    "united kingdom": "GB", "uk": "GB", "england": "GB",
    "canada": "CA",
    "spain": "ES",
    "india": "IN",
    "germany": "DE",
    "france": "FR",
    "portugal": "PT",
    "brazil": "BR",
    "greece": "GR",
    "netherlands": "NL", "holland": "NL",
    "australia": "AU",
    "mexico": "MX",
    "pakistan": "PK",
    "italy": "IT",
    "ireland": "IE",
    "japan": "JP",
    "nigeria": "NG",
    "argentina": "AR",
    "austria": "AT",
    "poland": "PL",
    "belgium": "BE",
    "turkey": "TR",
    "puerto rico": "PR",
    "singapore": "SG",
    "switzerland": "CH",
    "russia": "RU",
    "ukraine": "UA",
    "slovenia": "SI",
    "latvia": "LV",
    "colombia": "CO",
    "denmark": "DK",
    "hungary": "HU",
    "bolivia": "BO",
    "vietnam": "VN",
    "croatia": "HR",
    "romania": "RO",
    "thailand": "TH",
    "united arab emirates": "AE", "uae": "AE",
    "hong kong": "HK",
    "central african republic": "CF",
    "kenya": "KE",
    "finland": "FI",
    "sweden": "SE",
    "ghana": "GH",
    "uzbekistan": "UZ",
    "philippines": "PH",
    "chile": "CL",
    "czech republic": "CZ", "czechia": "CZ",
    "american samoa": "AS",
    "lithuania": "LT",
    "cyprus": "CY",
    "israel": "IL",
    "kuwait": "KW",
    "morocco": "MA",
    "north macedonia": "MK",
    "bosnia and herzegovina": "BA", "bosnia": "BA",
    "armenia": "AM",
    "costa rica": "CR",
    "china": "CN",
    "iran": "IR",
    "slovakia": "SK",
    "indonesia": "ID",
    "egypt": "EG",
    "dominican republic": "DO",
    "malaysia": "MY",
    "estonia": "EE",
    "honduras": "HN",
    "tunisia": "TN",
    "algeria": "DZ",
    "iraq": "IQ",
    "bulgaria": "BG",
    "jersey": "JE",
    "serbia": "RS",
    "new zealand": "NZ",
    "moldova": "MD",
    "luxembourg": "LU",
    "malta": "MT",
    "bahamas": "BS",
    "albania": "AL",
    # ISO codes already
    "us": "US", "gb": "GB", "ca": "CA", "es": "ES", "in": "IN",
    "de": "DE", "fr": "FR", "pt": "PT", "br": "BR", "gr": "GR",
    "nl": "NL", "au": "AU", "mx": "MX", "pk": "PK", "it": "IT",
    "ie": "IE", "jp": "JP", "ng": "NG", "ar": "AR", "at": "AT",
    "pl": "PL", "be": "BE", "tr": "TR", "pr": "PR", "sg": "SG",
    "ch": "CH", "ru": "RU", "ua": "UA", "si": "SI", "lv": "LV",
    "co": "CO", "dk": "DK", "hu": "HU", "bo": "BO", "vn": "VN",
    "hr": "HR", "ro": "RO", "th": "TH", "ae": "AE", "hk": "HK",
    "cf": "CF", "ke": "KE", "fi": "FI", "gh": "GH", "uz": "UZ",
    "ph": "PH", "cl": "CL", "cz": "CZ", "as": "AS", "lt": "LT",
    "cy": "CY", "kw": "KW", "ma": "MA", "mk": "MK", 
    "ba": "BA", "am": "AM", "cr": "CR", "cn": "CN", "ir": "IR",
    "sk": "SK", "id": "ID", "eg": "EG", "do": "DO", "my": "MY",
    "ee": "EE", "hn": "HN", "tn": "TN", "dz": "DZ", "iq": "IQ",
    "bg": "BG", "je": "JE", "rs": "RS", "nz": "NZ", "md": "MD",
    "lu": "LU", "mt": "MT", "bs": "BS", "al": "AL",
}

# Allowed ISO codes for App 2 (from dataset)
APP2_ALLOWED_ISO_CODES_A2 = {
    "US", "GB", "CA", "ES", "IN", "DE", "FR", "PT", "BR", "GR",
    "NL", "AU", "MX", "PK", "IT", "IE", "JP", "NG", "AR", "AT",
    "PL", "BE", "TR", "PR", "SG", "CH", "RU", "UA", "SI", "LV",
    "CO", "DK", "HU", "BO", "VN", "HR", "RO", "TH", "AE", "HK",
    "CF", "KE", "FI", "SE", "GH", "UZ", "PH", "CL", "CZ", "AS",
    "LT", "CY", "IL", "KW", "MA", "MK", "BA", "AM", "CR", "CN",
    "IR", "SK", "ID", "EG", "DO", "MY", "EE", "HN", "TN", "DZ",
    "IQ", "BG", "JE", "RS", "NZ", "MD", "LU", "MT", "BS", "AL",
}


# ============================================================
# APP 2 — EXPERIENCE LEVEL → CODE MAPPING
# ============================================================

def map_experience_to_level_code_a2(years: float) -> str:
    """Map numeric years of experience to EN/MI/SE/EX."""
    if years <= 1:
        return "EN"
    elif years <= 4:
        return "MI"
    elif years <= 10:
        return "SE"
    return "EX"


# ============================================================
# APP 2 — JOB TITLE EXTRACTION
# ============================================================

def extract_job_title_a2(text: str, allowed_job_titles_a2: List[str]) -> Tuple[str, str]:
    """
    Extract job title from resume text using App 2 patterns.
    Returns (matched_title, source_note).
    Falls back to 'Data Scientist' or first allowed title.
    """
    text_l = text.lower()

    # Score each canonical title by checking all its aliases
    best_title = None
    best_alias = None
    best_len = 0  # prefer longer (more specific) alias matches

    for phrase, canonical in _APP2_PHRASE_TO_TITLE_A2.items():
        if canonical not in allowed_job_titles_a2:
            continue
        #if phrase in text_l:
        pattern = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pattern, text_l):
            if len(phrase) > best_len:
                best_len = len(phrase)
                best_title = canonical
                best_alias = phrase

    if best_title:
        return best_title, f"phrase_match:{best_alias}"

    # Keyword fallback
    kw_map = [
        (["data engineer", "etl", "pipeline", "data infrastructure"], "Data Engineer"),
        (["data scientist", "machine learning", "ml ", "deep learning", "neural"], "Data Scientist"),
        (["data analyst", "business analyst", "analytics", "bi analyst"], "Data Analyst"),
        (["research scientist", "research engineer", "applied scientist"], "Research Scientist"),
        (["data architect", "data architecture"], "Data Architect"),
        (["ai developer", "ai programmer", "artificial intelligence developer"], "AI Developer"),
        (["data manager", "head of data", "data lead"], "Data Manager"),
    ]
    for keywords, title in kw_map:
        if title in allowed_job_titles_a2:
            if any(kw in text_l for kw in keywords):
                return title, f"keyword_fallback"

    default = "Data Scientist" if "Data Scientist" in allowed_job_titles_a2 else allowed_job_titles_a2[0]
    return default, "default"


# ============================================================
# APP 2 — COUNTRY EXTRACTION → ISO CODE
# ============================================================

def extract_country_iso_a2(text: str, allowed_iso_codes_a2: List[str]) -> Tuple[str, str]:
    """
    Extract country from resume text and return ISO code.
    Returns (iso_code, source_note).
    Falls back to 'US' or first allowed code.
    """
    text_l = text.lower()

    # Sort by phrase length descending to match more specific names first
    sorted_map = sorted(APP2_COUNTRY_TO_ISO_A2.items(), key=lambda x: len(x[0]), reverse=True)

    # Try spaCy NER first for GPE/LOC entities
    try:
        from resume_analysis import load_spacy_model
        nlp = load_spacy_model()
        doc = nlp(text[:5000])  # limit for speed
        for ent in doc.ents:
            if ent.label_ in {"GPE", "LOC"}:
                ent_lower = ent.text.lower().strip()
                iso = APP2_COUNTRY_TO_ISO_A2.get(ent_lower)
                if iso and iso in allowed_iso_codes_a2:
                    return iso, f"ner:{ent_lower}"
    except Exception:
        pass

    # Plain text scan (longest match first)
    for phrase, iso in sorted_map:
        if iso not in allowed_iso_codes_a2:
            continue
        # Use word-boundary aware search for short codes
        if len(phrase) <= 2:
            #pattern = r'\b' + re.escape(phrase.upper()) + r'\b'
            #if re.search(pattern, text):
            #    return iso, f"code_match:{phrase}"
            continue
        else:
            if phrase in text_l:
                return iso, f"alias_match:{phrase}"

    default = "US" if "US" in allowed_iso_codes_a2 else allowed_iso_codes_a2[0]
    return default, "default"


# ============================================================
# APP 2 — SKILLS EXTRACTION (reuses App 1 skill matcher)
# ============================================================

def extract_skills_a2(text: str) -> List[str]:
    """
    Extract technical skills from resume text.
    Reuses the App 1 spaCy skill matcher — read-only, no modification.
    Returns sorted list of skill strings.
    """
    try:
        from resume_analysis import extract_skills
        return extract_skills(text)
    except Exception:
        return []


# ============================================================
# APP 2 — EXPERIENCE YEARS EXTRACTION
# Reuses App 1 regex extractor — read-only
# ============================================================

def extract_experience_years_a2(text: str) -> float:
    """Extract numeric years of experience from resume text."""
    try:
        from resume_analysis import extract_experience_years
        return extract_experience_years(text)
    except Exception:
        return 0.0


# ============================================================
# APP 2 — EMPLOYMENT TYPE DETECTION
# ============================================================

def extract_employment_type_a2(text: str) -> str:
    text_l = text.lower()

    if re.search(r'\bpart[-\s]?time\b', text_l) or re.search(r'\bintern(ship)?\b', text_l):
        return "PT"
    if re.search(r'\bfreelance(r)?\b', text_l) or re.search(r'\bself[-\s]?employed\b', text_l):
        return "FL"
    if re.search(r'\bcontract(or)?\b', text_l) or re.search(r'\bconsult(ing|ant)\b', text_l):
        return "CT"
    return "FT"

# ============================================================
# APP 2 — REMOTE RATIO DETECTION
# ============================================================

def extract_remote_ratio_a2(text: str) -> int:
    """
    Detect work mode from resume keywords.
    Returns 0 (on-site), 50 (hybrid), or 100 (remote).
    """
    text_l = text.lower()
    if any(k in text_l for k in ["fully remote", "100% remote", "remote work", "work from home", "wfh", "remote"]):
        return 100
    if any(k in text_l for k in ["hybrid", "partial remote", "flexible"]):
        return 50
    return 0


# ============================================================
# APP 2 — RESUME SCORE (App 2 variant)
# Scores on experience level, skills, job title match
# ============================================================

def calculate_resume_score_a2(features_a2: Dict) -> Dict:
    """
    Calculate a resume score suitable for App 2 (DS/ML roles).
    Independent of App 1 scoring.
    """
    exp_years = features_a2.get("years_of_experience_a2", 0.0)
    skills = features_a2.get("skills_a2", [])
    job_title = features_a2.get("job_title_a2", "")

    # Experience score (max 40)
    if exp_years <= 0:
        exp_score, exp_note = 0, "No clear experience found"
    elif exp_years <= 1:
        exp_score, exp_note = 8, "Entry-level experience"
    elif exp_years <= 3:
        exp_score, exp_note = 18, "Early professional experience"
    elif exp_years <= 6:
        exp_score, exp_note = 28, "Solid professional experience"
    elif exp_years <= 10:
        exp_score, exp_note = 36, "Strong professional experience"
    else:
        exp_score, exp_note = 40, "Highly experienced profile"

    # Skills score (max 35) — DS/ML skills are weighted
    ds_keywords = {
        "python", "r", "sql", "machine learning", "deep learning",
        "tensorflow", "pytorch", "scikit-learn", "sklearn", "pandas",
        "numpy", "spark", "hadoop", "tableau", "power bi",
        "natural language processing", "nlp", "computer vision",
        "xgboost", "lightgbm", "statistics", "probability",
        "data analysis", "data visualization", "matplotlib",
        "seaborn", "plotly", "aws", "azure", "gcp", "docker",
        "git", "github", "flask", "fastapi", "feature engineering",
        "model deployment", "mlops", "airflow", "dbt", "kafka"
    }
    skill_lower = {s.lower() for s in skills}
    ds_skill_count = len(skill_lower & ds_keywords)
    general_count = len(skills) - ds_skill_count

    skill_score = min(ds_skill_count * 5 + general_count * 2, 35)

    if len(skills) == 0:
        skill_note = "No major skills detected"
    elif ds_skill_count == 0:
        skill_note = "General skills only — no DS/ML skills detected"
    elif ds_skill_count <= 3:
        skill_note = "Basic DS/ML skill coverage"
    elif ds_skill_count <= 6:
        skill_note = "Good DS/ML skill coverage"
    else:
        skill_note = "Strong DS/ML skill coverage"

    # Title relevance score (max 25)
    ds_titles = {
        "Data Scientist", "Machine Learning Engineer",
        "Research Scientist", "AI Developer",
        "Analytics Engineer"
    }
    mid_titles = {"Data Analyst", "Data Engineer", "Data Architect", "Business Intelligence Engineer"}

    if job_title in ds_titles:
        title_score, title_note = 25, "Directly relevant DS/ML role"
    elif job_title in mid_titles:
        title_score, title_note = 15, "Related data role"
    else:
        title_score, title_note = 8, "Indirect role match"

    total = min(exp_score + skill_score + title_score, 100)

    if total < 35:
        level = "Basic"
    elif total < 65:
        level = "Moderate"
    else:
        level = "Strong"

    return {
        "total_score_a2": int(total),
        "level_a2": str(level),
        "experience_score_a2": int(exp_score),
        "experience_note_a2": str(exp_note),
        "skills_score_a2": int(skill_score),
        "skills_note_a2": str(skill_note),
        "title_score_a2": int(title_score),
        "title_note_a2": str(title_note),
        "skills_detected_a2": list(skills),
        "skills_detected_str_a2": ", ".join(skills),
        "ds_skill_count_a2": int(ds_skill_count),
    }


# ============================================================
# APP 2 — MAIN FEATURE EXTRACTOR
# ============================================================

def extract_resume_features_a2(
    raw_text: str,
    allowed_job_titles_a2: List[str],
    allowed_iso_codes_a2: List[str],
) -> Dict:
    """
    Extract all features needed for App 2 (XGBoost DS salary model)
    from raw resume text.

    Returns a dict with keys matching App 2 model inputs plus metadata.
    """
    from resume_analysis import preprocess_resume_text

    text = preprocess_resume_text(raw_text)

    years_exp = extract_experience_years_a2(text)
    experience_level_a2 = map_experience_to_level_code_a2(years_exp)
    employment_type_a2 = extract_employment_type_a2(text)
    job_title_a2, job_title_source_a2 = extract_job_title_a2(text, allowed_job_titles_a2)
    iso_code_a2, country_source_a2 = extract_country_iso_a2(text, allowed_iso_codes_a2)
    remote_ratio_a2 = extract_remote_ratio_a2(text)
    skills_a2 = extract_skills_a2(text)

    return {
        # Model-ready fields
        "experience_level_a2": experience_level_a2,
        "employment_type_a2": employment_type_a2,
        "job_title_a2": job_title_a2,
        "employee_residence_a2": iso_code_a2,
        "company_location_a2": iso_code_a2,   # same country assumed
        "remote_ratio_a2": remote_ratio_a2,
        "company_size_a2": "M",               # conservative default
        # Extra metadata
        "years_of_experience_a2": float(years_exp),
        "skills_a2": skills_a2,
        "skills_str_a2": ", ".join(skills_a2),
        "sources_a2": {
            "experience": "regex",
            "experience_level": f"mapped_from_{years_exp:.1f}yrs",
            "job_title": str(job_title_source_a2),
            "country": str(country_source_a2),
            "skills": "spacy_phrase_matcher",
            "remote_ratio": "keyword_scan",
            "employment_type": "keyword_scan",
        }
    }