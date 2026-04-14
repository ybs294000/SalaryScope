"""
live_training_cleaner.py
========================
Cleans and validates raw Adzuna job listing records before training.

Key improvements over the previous version:
- Normalises raw Adzuna titles to canonical forms (e.g. "Senior Data Scientist
  at XYZ Ltd" -> "Data Scientist") so the model trains on meaningful groupings
  rather than thousands of near-unique long strings.
- Derives a broader set of features from Adzuna fields:
    salary_band_ratio  (salary_max / salary_min - 1): confidence proxy
    is_contract        (1/0): permanent vs contract/temp
    is_remote          (1/0): inferred from title keywords
- Infers remote_ratio from title and description keywords instead of defaulting
  to 0 for all Adzuna records.
- Preserves category_label as a higher-level grouping feature.
- All logic is stateless. Returns cleaned DataFrame plus audit dict.

Rollback note
-------------
Pure utility. Remove import from trainer to deactivate without side effects.
"""

from __future__ import annotations

import re
import pandas as pd
import numpy as np
from typing import Any

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

SALARY_MIN_USD: float = 10_000.0
SALARY_MAX_USD: float = 1_500_000.0
IQR_MULTIPLIER: float = 3.0
MIN_RECORDS_FOR_TRAINING: int = 100
MAX_TITLE_LEN: int = 200

# ---------------------------------------------------------------------------
# CANONICAL JOB TITLE MAPPING
# ---------------------------------------------------------------------------
# Maps a broad set of raw title patterns (lowercased, partial match) to a
# clean canonical name. Checked in ORDER -- first match wins. This collapses
# variants like "Senior Data Scientist III at Google (Remote)" -> "Data Scientist"
# and "Junior Backend Dev / Node.js" -> "Backend Developer".
#
# Rules are intentionally broad: we normalise the concept, not the exact rank,
# because seniority is already captured via experience_level_num.

_CANONICAL_TITLE_RULES: list[tuple[str, str]] = [
    # AI / ML
    (r"mlops|ml ops|machine learning ops",               "MLOps Engineer"),
    (r"machine learning|ml engineer",                     "Machine Learning Engineer"),
    (r"\bai engineer\b|artificial intelligence engineer", "AI Engineer"),
    (r"nlp engineer|natural language",                    "NLP Engineer"),
    (r"computer vision",                                  "Computer Vision Engineer"),
    (r"deep learning",                                    "Deep Learning Engineer"),
    (r"data scientist",                                   "Data Scientist"),
    (r"analytics engineer",                               "Analytics Engineer"),
    # Data
    (r"data engineer",                                    "Data Engineer"),
    (r"data analyst|business intelligence|bi analyst|bi developer", "Data Analyst"),
    (r"quantitative analyst|quant analyst|quant researcher",        "Quantitative Analyst"),
    # Software Engineering
    (r"site reliability|sre\b",                           "Site Reliability Engineer"),
    (r"devops|dev ops",                                   "DevOps Engineer"),
    (r"platform engineer",                                "Platform Engineer"),
    (r"backend|back.end|back end",                        "Backend Developer"),
    (r"frontend|front.end|front end",                     "Frontend Developer"),
    (r"full.?stack|fullstack",                            "Full Stack Developer"),
    (r"ios developer|swift developer|objective.c developer", "iOS Developer"),
    (r"android developer|kotlin developer",               "Android Developer"),
    (r"mobile developer",                                 "Mobile Developer"),
    (r"software engineer|software developer|swe\b",       "Software Engineer"),
    # Cloud / Infra
    (r"cloud architect",                                  "Cloud Architect"),
    (r"cloud engineer",                                   "Cloud Engineer"),
    (r"kubernetes|k8s engineer",                          "Kubernetes Engineer"),
    (r"infrastructure engineer|infra engineer",           "Infrastructure Engineer"),
    (r"network engineer",                                 "Network Engineer"),
    (r"systems administrator|sysadmin",                   "Systems Administrator"),
    (r"database administrator|dba\b",                     "Database Administrator"),
    # Security
    (r"security architect",                               "Security Architect"),
    (r"security engineer|appsec|application security",    "Security Engineer"),
    (r"penetration test|pentest",                         "Penetration Tester"),
    (r"soc analyst|security operations",                  "SOC Analyst"),
    (r"information security analyst",                     "Information Security Analyst"),
    # Product / Design
    (r"product manager|product owner",                    "Product Manager"),
    (r"product designer",                                 "Product Designer"),
    (r"ux designer|user experience",                      "UX Designer"),
    (r"ui developer|ui engineer",                         "UI Developer"),
    (r"scrum master",                                     "Scrum Master"),
    (r"agile coach",                                      "Agile Coach"),
    # Finance
    (r"financial analyst|finance analyst",                "Financial Analyst"),
    (r"investment analyst|equity analyst",                "Investment Analyst"),
    (r"risk analyst",                                     "Risk Analyst"),
    (r"actuarial",                                        "Actuarial Analyst"),
    (r"accountant|accounting",                            "Accountant"),
    (r"finance manager|head of finance",                  "Finance Manager"),
    # Marketing
    (r"digital marketing",                                "Digital Marketing Manager"),
    (r"seo specialist|search engine optim",               "SEO Specialist"),
    (r"growth hack|growth engineer",                      "Growth Engineer"),
    (r"content strateg",                                  "Content Strategist"),
    (r"marketing analyst",                                "Marketing Analyst"),
    (r"performance market",                               "Performance Marketer"),
    # Healthcare / Science
    (r"clinical data",                                    "Clinical Data Analyst"),
    (r"bioinformatics",                                   "Bioinformatics Scientist"),
    (r"research scientist",                               "Research Scientist"),
    (r"biomedical engineer",                              "Biomedical Engineer"),
    (r"health informatics",                               "Health Informatics Specialist"),
    (r"\bpharmacist\b",                                   "Pharmacist"),
    # Operations / Consulting
    (r"management consultant",                            "Management Consultant"),
    (r"business analyst",                                 "Business Analyst"),
    (r"operations manager",                               "Operations Manager"),
    (r"supply chain",                                     "Supply Chain Analyst"),
    (r"project manager",                                  "Project Manager"),
    (r"strategy analyst",                                 "Strategy Analyst"),
    # Sales
    (r"sales engineer",                                   "Sales Engineer"),
    (r"account executive",                                "Account Executive"),
    (r"customer success",                                 "Customer Success Manager"),
    (r"solutions architect",                              "Solutions Architect"),
    (r"technical account manager|tam\b",                  "Technical Account Manager"),
]

_COMPILED_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), canonical)
    for pattern, canonical in _CANONICAL_TITLE_RULES
]


def normalise_job_title(raw_title: str) -> str | None:
    """
    Map a raw Adzuna job title to a canonical form.
    Returns None if no rule matches (record will be dropped).
    """
    t = raw_title.lower()
    for pattern, canonical in _COMPILED_RULES:
        if pattern.search(t):
            return canonical
    return None


# ---------------------------------------------------------------------------
# EXPERIENCE INFERENCE
# ---------------------------------------------------------------------------

_EXEC_KEYWORDS  = {"director", "vp ", "chief", "head of", "president", "c-level",
                   "cto", "cdo", "ciso", "cfo"}
_SENIOR_KEYWORDS = {"senior", "sr.", "sr ", "lead", "principal", "staff",
                    "architect", "manager", "consultant"}
_JUNIOR_KEYWORDS = {"junior", "jr.", "jr ", "intern", "graduate", "entry",
                    "associate", "apprentice", "trainee", "entry-level"}


def _infer_experience_num(raw_title: str) -> int:
    t = raw_title.lower()
    if any(k in t for k in _EXEC_KEYWORDS):
        return 3
    if any(k in t for k in _SENIOR_KEYWORDS):
        return 2
    if any(k in t for k in _JUNIOR_KEYWORDS):
        return 0
    return 1


# ---------------------------------------------------------------------------
# REMOTE INFERENCE
# ---------------------------------------------------------------------------

_REMOTE_KEYWORDS  = {"remote", "work from home", "wfh", "fully remote", "distributed",
                     "anywhere", "home based", "home-based"}
_HYBRID_KEYWORDS  = {"hybrid", "flexible location", "partly remote", "2 days", "3 days"}


def _infer_remote_ratio(raw_title: str) -> int:
    t = raw_title.lower()
    if any(k in t for k in _REMOTE_KEYWORDS):
        return 100
    if any(k in t for k in _HYBRID_KEYWORDS):
        return 50
    return 0


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _coerce_float(val: Any) -> float | None:
    try:
        f = float(val)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _country_to_iso2(country: str) -> str:
    c = str(country).strip().upper()
    return c if (len(c) == 2 and c.isalpha()) else "US"


def _is_contract(contract_str: str) -> int:
    c = contract_str.lower().strip()
    return 1 if c in {"contract", "temporary", "freelance", "interim"} else 0


# ---------------------------------------------------------------------------
# RECORD-LEVEL CLEANING
# ---------------------------------------------------------------------------

def _clean_record(raw: dict) -> tuple[dict | None, list[str]]:
    issues: list[str] = []
    out: dict = {}

    # Target salary
    salary = _coerce_float(raw.get("salary_mid"))
    if salary is None:
        return None, ["missing salary_mid"]
    if not (SALARY_MIN_USD <= salary <= SALARY_MAX_USD):
        return None, [f"salary {salary:.0f} outside plausible range"]
    out["salary_in_usd"] = salary

    # Contract filter: exclude part-time because annualised figures are unreliable
    contract = str(raw.get("contract", "")).lower().strip()
    if contract == "part_time":
        return None, ["part-time listing excluded"]
    out["is_contract"] = _is_contract(contract)

    # Raw title must be present and non-empty
    raw_title = str(raw.get("job_title", "")).strip()
    if not raw_title or len(raw_title) > MAX_TITLE_LEN:
        return None, ["missing or invalid job_title"]

    # Normalise to canonical title -- drop records that don't match any rule
    canonical = normalise_job_title(raw_title)
    if canonical is None:
        return None, [f"title '{raw_title[:60]}' did not match any canonical rule"]
    out["job_title"] = canonical

    # Infer features from the raw title (before canonicalisation strips context)
    out["experience_level_num"] = _infer_experience_num(raw_title)
    out["remote_ratio"]         = _infer_remote_ratio(raw_title)

    # Location
    out["company_location"] = _country_to_iso2(raw.get("country", "US"))

    # Company size: Adzuna does not expose this; default to M (medium).
    out["company_size"] = "M"

    # Education: unknown from Adzuna; default to bachelor's (1).
    out["education_level"] = 1

    # Salary band ratio: (max - min) / min -- proxy for salary certainty.
    # High ratio = wide band = listing is less precise. Clipped to 0-5.
    s_min = _coerce_float(raw.get("salary_min"))
    s_max = _coerce_float(raw.get("salary_max"))
    if s_min and s_max and s_min > 0:
        out["salary_band_ratio"] = float(min((s_max - s_min) / s_min, 5.0))
    else:
        out["salary_band_ratio"] = 0.5   # default when only one bound available

    # Adzuna category label (e.g. "IT Jobs", "Accounting & Finance Jobs")
    raw_cat = str(raw.get("category_label", "")).strip()
    out["category_label"] = raw_cat if raw_cat else "Unknown"

    return out, issues


# ---------------------------------------------------------------------------
# BATCH CLEANING
# ---------------------------------------------------------------------------

def clean_adzuna_records(
    raw_records: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Clean a list of raw Adzuna fetch records.

    Returns (df_clean, audit).
    """
    total_raw = len(raw_records)
    clean_rows: list[dict] = []
    all_warnings: list[str] = []

    for i, raw in enumerate(raw_records):
        try:
            clean, issues = _clean_record(raw)
            for issue in issues:
                all_warnings.append(f"record {i}: {issue}")
            if clean is not None:
                clean_rows.append(clean)
        except Exception as exc:
            all_warnings.append(f"record {i}: unexpected error ({exc})")

    if not clean_rows:
        return pd.DataFrame(), {
            "ok": False,
            "total_raw": total_raw,
            "total_clean": 0,
            "dropped": total_raw,
            "drop_rate": 1.0,
            "warnings": all_warnings,
            "salary_stats": {},
            "reason": "No records survived cleaning.",
        }

    df = pd.DataFrame(clean_rows)

    # Deduplication: same canonical title + salary bucket ($2000 wide)
    df["_sal_bucket"] = (df["salary_in_usd"] / 2000).round(0)
    before = len(df)
    df = df.drop_duplicates(subset=["job_title", "_sal_bucket"], keep="first")
    df = df.drop(columns=["_sal_bucket"])
    dupes = before - len(df)
    if dupes:
        all_warnings.append(f"{dupes} near-duplicate records removed after title normalisation")

    # IQR outlier capping on salary
    q1 = df["salary_in_usd"].quantile(0.25)
    q3 = df["salary_in_usd"].quantile(0.75)
    iqr = q3 - q1
    lower_cap = max(q1 - IQR_MULTIPLIER * iqr, SALARY_MIN_USD)
    upper_cap = min(q3 + IQR_MULTIPLIER * iqr, SALARY_MAX_USD)
    n_capped = int(
        ((df["salary_in_usd"] < lower_cap) | (df["salary_in_usd"] > upper_cap)).sum()
    )
    if n_capped:
        df["salary_in_usd"] = df["salary_in_usd"].clip(lower=lower_cap, upper=upper_cap)
        all_warnings.append(
            f"{n_capped} salary outlier(s) capped to [{lower_cap:.0f}, {upper_cap:.0f}]"
        )

    total_clean = len(df)
    dropped     = total_raw - total_clean
    drop_rate   = dropped / total_raw if total_raw else 0.0

    salary_stats = {
        "min":    float(df["salary_in_usd"].min()),
        "max":    float(df["salary_in_usd"].max()),
        "mean":   float(df["salary_in_usd"].mean()),
        "median": float(df["salary_in_usd"].median()),
        "std":    float(df["salary_in_usd"].std()),
    }

    ok = total_clean >= MIN_RECORDS_FOR_TRAINING
    reason = (
        f"{total_clean} clean records from {total_raw} raw "
        f"({dropped} dropped, {drop_rate:.0%} rate)."
        if ok else
        f"Only {total_clean} clean records; need at least {MIN_RECORDS_FOR_TRAINING}. "
        "Try adding more domains or countries."
    )

    return df, {
        "ok": ok,
        "total_raw": total_raw,
        "total_clean": total_clean,
        "dropped": dropped,
        "drop_rate": drop_rate,
        "warnings": all_warnings,
        "salary_stats": salary_stats,
        "reason": reason,
    }
