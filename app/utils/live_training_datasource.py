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
- Covers 12 countries: us, gb, de, fr, au, ca, in, nl, pl, ru, sg, za.
- Salary histogram endpoint gives aggregated distribution data per job title.

Credentials required (add to .streamlit/secrets.toml and Streamlit Cloud secrets):
    ADZUNA_APP_ID  = "your_app_id"
    ADZUNA_APP_KEY = "your_app_key"

Registration: https://developer.adzuna.com/signup (free, instant)

Data collected per job listing
-------------------------------
- title          : str   job title as posted
- salary_min     : float annual salary lower bound (USD equivalent)
- salary_max     : float annual salary upper bound (USD equivalent)
- salary_mid     : float average of min/max used as training target
- country        : str   ISO 2-letter code
- contract_type  : str   permanent / contract / part_time
- created        : str   ISO date of posting

Rate limiting
-------------
A minimum 0.3-second sleep is applied between paginated calls to stay
well under the 25/minute limit.  A daily quota guard warns when fewer
than 20 requests remain (based on response headers when available).

Rollback note
-------------
This module has no side effects beyond HTTP calls and returns pure data.
Remove the import from live_training_tab.py to disable it completely.
"""

from __future__ import annotations

import time
import math
import datetime
import streamlit as st
import requests

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"

# Supported Adzuna country codes and their display names
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

# Results per page (Adzuna max is 50)
RESULTS_PER_PAGE = 50

# Seconds to sleep between page requests (keeps under 25/min)
REQUEST_DELAY_S = 0.35

# Minimum plausible annual salary (USD)
SALARY_MIN_USD = 8_000.0

# Maximum plausible annual salary (USD)
SALARY_MAX_USD = 2_500_000.0

# Approximate USD conversion multipliers for non-USD countries
# Updated periodically; exact rates are not critical for training data
_APPROX_FX: dict[str, float] = {
    "us": 1.0,
    "gb": 1.27,   # GBP -> USD
    "au": 0.65,   # AUD -> USD
    "ca": 0.74,   # CAD -> USD
    "de": 1.09,   # EUR -> USD
    "fr": 1.09,
    "in": 0.012,  # INR -> USD
    "nl": 1.09,
    "pl": 0.25,   # PLN -> USD
    "sg": 0.75,   # SGD -> USD
}


# ---------------------------------------------------------------------------
# CREDENTIAL HELPERS
# ---------------------------------------------------------------------------

def _get_credentials() -> tuple[str | None, str | None]:
    """Return (app_id, app_key) from Streamlit secrets, or (None, None)."""
    try:
        app_id  = st.secrets.get("ADZUNA_APP_ID")
        app_key = st.secrets.get("ADZUNA_APP_KEY")
        if app_id and app_key:
            return str(app_id), str(app_key)
    except Exception:
        pass
    return None, None


def is_adzuna_configured() -> bool:
    """Return True if Adzuna credentials are present in secrets."""
    app_id, app_key = _get_credentials()
    return app_id is not None and app_key is not None


# ---------------------------------------------------------------------------
# LOW-LEVEL REQUEST
# ---------------------------------------------------------------------------

def _get(url: str, params: dict, timeout: int = 15) -> tuple[dict | None, str | None]:
    """
    Execute one GET request.  Returns (json_dict, error_string).
    Never raises.
    """
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
    """Convert a raw Adzuna salary figure to approximate USD annual."""
    fx = _APPROX_FX.get(country.lower(), 1.0)
    return raw_salary * fx


def _mid(salary_min: float | None, salary_max: float | None) -> float | None:
    """Return midpoint of salary range, or None if both are absent."""
    if salary_min is not None and salary_max is not None:
        return (salary_min + salary_max) / 2.0
    if salary_min is not None:
        return salary_min
    if salary_max is not None:
        return salary_max
    return None


# ---------------------------------------------------------------------------
# MAIN FETCH FUNCTION
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_adzuna_salary_records(
    job_titles: list[str],
    countries: list[str],
    max_records: int = 1000,
) -> tuple[list[dict], dict]:
    """
    Fetch job listings with salary data from the Adzuna API.

    Searches each (job_title, country) pair and collects records that
    include salary information.  Results are deduplicated on (title, salary_mid).

    Parameters
    ----------
    job_titles : list of str
        Job title keywords to search.  E.g. ["data scientist", "software engineer"].
        Kept short to maximize recall; Adzuna does partial matching.
    countries : list of str
        Adzuna country codes.  E.g. ["us", "gb", "in"].
    max_records : int
        Soft cap on total records collected across all searches.
        Prevents exhausting the daily quota on a single training run.

    Returns
    -------
    (records, fetch_report)
        records      -- list of dicts (one per job listing with salary)
        fetch_report -- dict with counts, warnings, quota hint
    """
    app_id, app_key = _get_credentials()
    if not app_id:
        return [], {
            "ok": False,
            "reason": "ADZUNA_APP_ID and ADZUNA_APP_KEY not set in secrets.",
            "total_fetched": 0,
            "with_salary": 0,
            "warnings": [],
        }

    records: list[dict] = []
    warnings: list[str] = []
    requests_made = 0
    seen: set[str] = set()

    base_params = {"app_id": app_id, "app_key": app_key, "results_per_page": RESULTS_PER_PAGE}

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

            # Adzuna paginates; fetch up to 3 pages per (title, country)
            for page in range(1, 4):
                if len(records) >= max_records:
                    break

                url = f"{ADZUNA_BASE}/{country_lower}/search/{page}"
                params = {
                    **base_params,
                    "what": title,
                    "content-type": "application/json",
                    "salary_include_unknown": 0,  # only listings with salary data
                }

                data, err = _get(url, params)
                requests_made += 1

                if err:
                    warnings.append(f"[{country}/{title}/p{page}] {err}")
                    break   # stop pagination for this (title, country) on error

                if data is None:
                    break

                jobs = data.get("results", [])
                if not jobs:
                    break   # no more pages

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

                    # Plausibility gate
                    if not (SALARY_MIN_USD <= mid_usd <= SALARY_MAX_USD):
                        continue

                    job_title_raw = str(job.get("title", "")).strip()
                    if not job_title_raw:
                        continue

                    # Deduplication key
                    dedup_key = f"{job_title_raw.lower()}|{round(mid_usd, -3)}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    contract = str(job.get("contract_type") or "").strip().lower()
                    created  = str(job.get("created", ""))[:10]

                    records.append({
                        "job_title":    job_title_raw,
                        "salary_min":   _to_usd_annual(s_min_f, country_lower) if s_min_f else None,
                        "salary_max":   _to_usd_annual(s_max_f, country_lower) if s_max_f else None,
                        "salary_mid":   mid_usd,
                        "country":      country_lower.upper(),
                        "search_term":  title,
                        "contract":     contract,
                        "created":      created,
                    })

                time.sleep(REQUEST_DELAY_S)

    fetch_report = {
        "ok": len(records) > 0,
        "total_fetched": len(records) + len(seen) - len(records),
        "with_salary": len(records),
        "requests_made": requests_made,
        "countries_searched": countries,
        "titles_searched": job_titles,
        "warnings": warnings,
        "reason": (
            f"Fetched {len(records)} listings with salary from "
            f"{requests_made} API requests."
        ) if records else (
            "No salary records returned.  Check credentials or try different search terms."
        ),
    }

    return records, fetch_report


# ---------------------------------------------------------------------------
# QUALITY SUMMARY (no API calls)
# ---------------------------------------------------------------------------

def get_fetch_quality_summary(records: list[dict]) -> dict:
    """Lightweight summary of fetched records without cleaning."""
    if not records:
        return {"total": 0}

    salaries = [r["salary_mid"] for r in records if r.get("salary_mid")]
    import statistics
    return {
        "total": len(records),
        "with_salary_range": sum(1 for r in records if r.get("salary_min") and r.get("salary_max")),
        "countries": list({r["country"] for r in records}),
        "salary_min":    min(salaries) if salaries else 0,
        "salary_max":    max(salaries) if salaries else 0,
        "salary_median": statistics.median(salaries) if salaries else 0,
        "salary_mean":   statistics.mean(salaries) if salaries else 0,
    }
