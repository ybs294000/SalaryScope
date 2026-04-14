"""
live_training_datasource.py
============================
Fetches real salary data from the Adzuna Jobs API for live model training.

Why Adzuna?
-----------
- Completely free tier: register at https://developer.adzuna.com
- No credit card required.
- Free limits: 250 requests/day, 25 requests/minute.
- Returns real live job listings including salary_min / salary_max per listing.

Credentials required (add to .streamlit/secrets.toml and Streamlit Cloud secrets):
    ADZUNA_APP_ID  = "your_app_id"
    ADZUNA_APP_KEY = "your_app_key"

Registration: https://developer.adzuna.com/signup (free, instant)

Quota safety
------------
The free tier allows 250 requests per day. This module enforces a hard stop
at 25% usage (62 requests per session) to prevent accidental exhaustion of
the daily quota across multiple training runs. Override by setting
ADZUNA_MAX_REQUESTS_OVERRIDE in secrets (integer).

Rollback note
-------------
This module has no side effects beyond HTTP calls. Remove the import from
live_training_tab.py to disable it completely.
"""

from __future__ import annotations

import time
import streamlit as st
import requests

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"

SUPPORTED_COUNTRIES: dict[str, str] = {
    "us": "United States",
    "gb": "United Kingdom",
    "au": "Australia",
    "ca": "Canada",
    "de": "Germany",
    "fr": "France",
    "in": "India",
    "nl": "Netherlands",
    "pl": "Poland",
    "sg": "Singapore",
}

RESULTS_PER_PAGE = 50
REQUEST_DELAY_S  = 0.35

SALARY_MIN_USD = 8_000.0
SALARY_MAX_USD = 2_500_000.0

# Quota guard: stop at 25% of 250/day = 62 requests per session
FREE_TIER_DAILY_LIMIT    = 250
QUOTA_SAFETY_FRACTION    = 0.25
DEFAULT_SESSION_MAX_REQS = int(FREE_TIER_DAILY_LIMIT * QUOTA_SAFETY_FRACTION)  # 62

_APPROX_FX: dict[str, float] = {
    "us": 1.0,
    "gb": 1.27,
    "au": 0.65,
    "ca": 0.74,
    "de": 1.09,
    "fr": 1.09,
    "in": 0.012,
    "nl": 1.09,
    "pl": 0.25,
    "sg": 0.75,
}

# ---------------------------------------------------------------------------
# MULTI-DOMAIN JOB TITLE CATALOGUE
# ---------------------------------------------------------------------------
# Organised by domain so the tab can offer domain-level toggles.
# Titles use short generic keywords that Adzuna partial-matches broadly,
# improving recall. Normalization to canonical names happens in the cleaner.

DOMAIN_TITLES: dict[str, list[str]] = {
    "Data and AI": [
        "data scientist",
        "data analyst",
        "machine learning engineer",
        "data engineer",
        "business intelligence analyst",
        "analytics engineer",
        "AI engineer",
        "NLP engineer",
        "computer vision engineer",
        "MLops engineer",
    ],
    "Software Engineering": [
        "software engineer",
        "backend developer",
        "frontend developer",
        "full stack developer",
        "mobile developer",
        "iOS developer",
        "Android developer",
        "platform engineer",
        "site reliability engineer",
        "DevOps engineer",
    ],
    "Cloud and Infrastructure": [
        "cloud architect",
        "cloud engineer",
        "infrastructure engineer",
        "systems administrator",
        "network engineer",
        "database administrator",
        "Kubernetes engineer",
    ],
    "Cybersecurity": [
        "security engineer",
        "penetration tester",
        "information security analyst",
        "SOC analyst",
        "security architect",
    ],
    "Product and Design": [
        "product manager",
        "product designer",
        "UX designer",
        "UI developer",
        "scrum master",
        "agile coach",
    ],
    "Finance and Accounting": [
        "financial analyst",
        "quantitative analyst",
        "investment analyst",
        "accountant",
        "finance manager",
        "risk analyst",
        "actuarial analyst",
    ],
    "Marketing and Growth": [
        "digital marketing manager",
        "SEO specialist",
        "growth hacker",
        "content strategist",
        "marketing analyst",
        "performance marketer",
    ],
    "Healthcare and Science": [
        "clinical data analyst",
        "bioinformatics scientist",
        "research scientist",
        "pharmacist",
        "biomedical engineer",
        "health informatics specialist",
    ],
    "Operations and Consulting": [
        "management consultant",
        "business analyst",
        "operations manager",
        "supply chain analyst",
        "project manager",
        "strategy analyst",
    ],
    "Sales and Customer Success": [
        "sales engineer",
        "account executive",
        "customer success manager",
        "solutions architect",
        "technical account manager",
    ],
}

DEFAULT_DOMAINS: list[str] = [
    "Data and AI",
    "Software Engineering",
    "Cloud and Infrastructure",
]

# ---------------------------------------------------------------------------
# CREDENTIAL HELPERS
# ---------------------------------------------------------------------------

def _get_credentials() -> tuple[str | None, str | None]:
    try:
        app_id  = st.secrets.get("ADZUNA_APP_ID")
        app_key = st.secrets.get("ADZUNA_APP_KEY")
        if app_id and app_key:
            return str(app_id), str(app_key)
    except Exception:
        pass
    return None, None


def _get_session_request_cap() -> int:
    """
    Return per-session request cap. Default is 25% of 250/day = 62 requests.
    Override with ADZUNA_MAX_REQUESTS_OVERRIDE in secrets.
    """
    try:
        override = st.secrets.get("ADZUNA_MAX_REQUESTS_OVERRIDE")
        if override is not None:
            return max(1, int(override))
    except Exception:
        pass
    return DEFAULT_SESSION_MAX_REQS


def is_adzuna_configured() -> bool:
    app_id, app_key = _get_credentials()
    return app_id is not None and app_key is not None


# ---------------------------------------------------------------------------
# LOW-LEVEL REQUEST
# ---------------------------------------------------------------------------

def _get(url: str, params: dict, timeout: int = 15) -> tuple[dict | None, str | None]:
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 429:
            return None, "Adzuna rate limit hit (429). Wait a minute and retry."
        if resp.status_code == 401:
            return None, "Adzuna credentials rejected (401). Check ADZUNA_APP_ID and ADZUNA_APP_KEY."
        if not resp.ok:
            return None, f"Adzuna API returned HTTP {resp.status_code}: {resp.text[:200]}"
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, "Adzuna API request timed out."
    except requests.exceptions.ConnectionError as exc:
        return None, f"Network error: {exc}"
    except Exception as exc:
        return None, f"Unexpected error: {exc}"


# ---------------------------------------------------------------------------
# SALARY NORMALISATION
# ---------------------------------------------------------------------------

def _to_usd_annual(raw_salary: float, country: str) -> float:
    fx = _APPROX_FX.get(country.lower(), 1.0)
    return raw_salary * fx


def _mid(s_min: float | None, s_max: float | None) -> float | None:
    if s_min is not None and s_max is not None:
        return (s_min + s_max) / 2.0
    return s_min if s_min is not None else s_max


# ---------------------------------------------------------------------------
# MAIN FETCH FUNCTION
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_adzuna_salary_records(
    job_titles: list[str],
    countries: list[str],
    max_records: int = 3000,
) -> tuple[list[dict], dict]:
    """
    Fetch job listings with salary data from the Adzuna API.

    Enforces a per-session request cap at 25% of the 250/day free tier
    (62 requests by default). Override with ADZUNA_MAX_REQUESTS_OVERRIDE.

    Returns (records, fetch_report).
    """
    app_id, app_key = _get_credentials()
    if not app_id:
        return [], {
            "ok": False,
            "reason": "ADZUNA_APP_ID and ADZUNA_APP_KEY not set in secrets.",
            "with_salary": 0,
            "warnings": [],
            "requests_made": 0,
            "quota_used_pct": 0.0,
            "quota_stopped": False,
        }

    session_request_cap = _get_session_request_cap()
    records: list[dict] = []
    warnings: list[str] = []
    requests_made = 0
    seen: set[str] = set()
    quota_stopped = False

    base_params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": RESULTS_PER_PAGE,
    }

    outer_break = False

    for country in countries:
        if outer_break:
            break
        country_lower = country.lower()
        if country_lower not in SUPPORTED_COUNTRIES:
            warnings.append(f"Country '{country}' not supported by Adzuna; skipped.")
            continue

        for title in job_titles:
            if outer_break:
                break
            if len(records) >= max_records:
                outer_break = True
                break

            for page in range(1, 4):
                if len(records) >= max_records:
                    break

                if requests_made >= session_request_cap:
                    quota_stopped = True
                    outer_break = True
                    warnings.append(
                        f"Session request cap of {session_request_cap} reached "
                        f"({QUOTA_SAFETY_FRACTION:.0%} of {FREE_TIER_DAILY_LIMIT}/day free tier). "
                        "Fetch stopped to protect your daily quota. "
                        "Override with ADZUNA_MAX_REQUESTS_OVERRIDE in secrets."
                    )
                    break

                url = f"{ADZUNA_BASE}/{country_lower}/search/{page}"
                params = {
                    **base_params,
                    "what": title,
                    "content-type": "application/json",
                    "salary_include_unknown": 0,
                }

                data, err = _get(url, params)
                requests_made += 1

                if err:
                    warnings.append(f"[{country}/{title}/p{page}] {err}")
                    break

                if data is None:
                    break

                jobs = data.get("results", [])
                if not jobs:
                    break

                for job in jobs:
                    s_min = job.get("salary_min")
                    s_max = job.get("salary_max")

                    if s_min is None and s_max is None:
                        continue

                    try:
                        s_min_f = float(s_min) if s_min is not None else None
                        s_max_f = float(s_max) if s_max is not None else None
                    except (TypeError, ValueError):
                        continue

                    mid_raw = _mid(s_min_f, s_max_f)
                    if mid_raw is None:
                        continue

                    mid_usd = _to_usd_annual(mid_raw, country_lower)

                    if not (SALARY_MIN_USD <= mid_usd <= SALARY_MAX_USD):
                        continue

                    job_title_raw = str(job.get("title", "")).strip()
                    if not job_title_raw:
                        continue

                    # Adzuna category label: "IT Jobs", "Accounting Jobs", etc.
                    category_label = ""
                    cat = job.get("category")
                    if isinstance(cat, dict):
                        category_label = str(cat.get("label", "")).strip()

                    # Salary band width as a signal: wide band = more uncertainty
                    salary_band_usd = None
                    if s_min_f is not None and s_max_f is not None:
                        salary_band_usd = _to_usd_annual(s_max_f - s_min_f, country_lower)

                    contract = str(job.get("contract_type") or "").strip().lower()
                    created  = str(job.get("created", ""))[:10]

                    dedup_key = f"{job_title_raw.lower()}|{round(mid_usd, -3)}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    records.append({
                        "job_title":        job_title_raw,
                        "salary_min":       _to_usd_annual(s_min_f, country_lower) if s_min_f else None,
                        "salary_max":       _to_usd_annual(s_max_f, country_lower) if s_max_f else None,
                        "salary_mid":       mid_usd,
                        "salary_band_usd":  salary_band_usd,
                        "country":          country_lower.upper(),
                        "search_term":      title,
                        "contract":         contract,
                        "category_label":   category_label,
                        "created":          created,
                    })

                time.sleep(REQUEST_DELAY_S)

    quota_used_pct = (requests_made / FREE_TIER_DAILY_LIMIT) * 100.0

    fetch_report = {
        "ok": len(records) > 0,
        "with_salary": len(records),
        "requests_made": requests_made,
        "session_request_cap": session_request_cap,
        "quota_used_pct": quota_used_pct,
        "quota_stopped": quota_stopped,
        "countries_searched": countries,
        "titles_searched": job_titles,
        "warnings": warnings,
        "reason": (
            f"Fetched {len(records)} listings with salary data from "
            f"{requests_made} API requests ({quota_used_pct:.1f}% of daily free quota)."
            + (
                " Session request cap reached; increase ADZUNA_MAX_REQUESTS_OVERRIDE to fetch more."
                if quota_stopped else ""
            )
        ) if records else (
            "No salary records returned. Check credentials or try different search terms."
        ),
    }

    return records, fetch_report


# ---------------------------------------------------------------------------
# QUALITY SUMMARY (no API calls)
# ---------------------------------------------------------------------------

def get_fetch_quality_summary(records: list[dict]) -> dict:
    if not records:
        return {"total": 0}

    salaries   = [r["salary_mid"] for r in records if r.get("salary_mid")]
    categories = list({r.get("category_label", "") for r in records if r.get("category_label")})
    import statistics
    return {
        "total": len(records),
        "with_salary_range": sum(
            1 for r in records if r.get("salary_min") and r.get("salary_max")
        ),
        "countries":     list({r["country"] for r in records}),
        "categories":    categories,
        "salary_min":    min(salaries) if salaries else 0,
        "salary_max":    max(salaries) if salaries else 0,
        "salary_median": statistics.median(salaries) if salaries else 0,
        "salary_mean":   statistics.mean(salaries) if salaries else 0,
    }
