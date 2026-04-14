"""
live_training_cleaner.py
========================
Cleans and validates raw Adzuna job listing records before training.

All logic is stateless.  Returns a cleaned DataFrame AND an audit dict
so the tab can surface a quality report to the admin without any
implicit side effects.

Rollback note
-------------
Pure utility module.  No persistent state.  Remove import from trainer
to deactivate without any other changes.
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

# IQR multiplier for outlier capping
IQR_MULTIPLIER: float = 3.0

# Minimum clean records required before training proceeds
MIN_RECORDS_FOR_TRAINING: int = 50

# Maximum job title character length
MAX_TITLE_LEN: int = 120

# Contract types considered reliable for salary data
# "part_time" is excluded because part-time salaries are often annualised
# differently and skew the distribution badly.
ACCEPTED_CONTRACTS: set[str] = {"permanent", "contract", "full_time", ""}

# Experience level inference from job title keywords
_SENIOR_KEYWORDS = {"senior", "sr.", "sr ", "lead", "principal", "staff", "head",
                    "director", "vp ", "chief", "manager", "architect"}
_JUNIOR_KEYWORDS = {"junior", "jr.", "jr ", "intern", "graduate", "entry",
                    "associate", "apprentice", "trainee"}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _coerce_float(val: Any) -> float | None:
    try:
        f = float(val)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _clean_title(val: Any) -> str | None:
    if val is None:
        return None
    s = re.sub(r"\s+", " ", str(val).strip())
    if not s or len(s) > MAX_TITLE_LEN:
        return None
    # Strip leading/trailing punctuation artifacts
    s = re.sub(r"^[^\w]+|[^\w]+$", "", s)
    return s if s else None


def _infer_experience_num(title: str) -> int:
    """
    Map a job title to a rough experience ordinal (0-3).
    0 = Entry, 1 = Mid, 2 = Senior, 3 = Executive.
    Used only as a model feature; not shown to the user.
    """
    t = title.lower()
    if any(k in t for k in _JUNIOR_KEYWORDS):
        return 0
    if any(k in t for k in _SENIOR_KEYWORDS):
        if any(k in t for k in {"director", "vp ", "chief", "head of"}):
            return 3
        return 2
    return 1   # mid as default


def _infer_company_size(title: str) -> str:
    """
    We have no company size from Adzuna.  Default to 'M' (medium).
    Kept as a separate function in case enrichment is added later.
    """
    return "M"


def _country_to_iso2(country: str) -> str:
    """
    Adzuna returns 2-letter codes already (stored uppercase).
    Return as-is or default to 'US'.
    """
    c = str(country).strip().upper()
    if len(c) == 2 and c.isalpha():
        return c
    return "US"


# ---------------------------------------------------------------------------
# RECORD-LEVEL CLEANING
# ---------------------------------------------------------------------------

def _clean_record(raw: dict) -> tuple[dict | None, list[str]]:
    """
    Validate and clean one raw Adzuna record.
    Returns (clean_dict, issues).  clean_dict is None if the record is dropped.
    """
    issues: list[str] = []
    out: dict = {}

    # Target salary
    salary = _coerce_float(raw.get("salary_mid"))
    if salary is None:
        return None, ["missing salary_mid"]
    if not (SALARY_MIN_USD <= salary <= SALARY_MAX_USD):
        return None, [f"salary {salary:.0f} outside plausible range"]
    out["salary_in_usd"] = salary

    # Job title (required)
    title = _clean_title(raw.get("job_title"))
    if title is None:
        return None, ["missing or invalid job_title"]
    out["job_title"] = title

    # Contract type filter
    contract = str(raw.get("contract", "")).lower().strip()
    if contract == "part_time":
        return None, ["part-time listing excluded"]
    out["contract"] = contract

    # Country -> company_location
    out["company_location"] = _country_to_iso2(raw.get("country", "US"))

    # Inferred features
    out["experience_level_num"] = _infer_experience_num(title)
    out["company_size"]         = _infer_company_size(title)
    out["remote_ratio"]         = 0   # Adzuna does not expose remote flag; default on-site

    # Education level: unknown from Adzuna, use mid-level default
    out["education_level"] = 1

    return out, issues


# ---------------------------------------------------------------------------
# BATCH CLEANING
# ---------------------------------------------------------------------------

def clean_adzuna_records(
    raw_records: list[dict],
) -> tuple[pd.DataFrame, dict]:
    """
    Clean a list of raw Adzuna fetch records.

    Returns
    -------
    (df_clean, audit)
        df_clean -- cleaned DataFrame, may be empty
        audit    -- dict with ok, counts, warnings, salary_stats, reason
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

    # Deduplication: same job_title + salary within $2000
    df["_sal_bucket"] = (df["salary_in_usd"] / 2000).round(0)
    before = len(df)
    df = df.drop_duplicates(subset=["job_title", "_sal_bucket"], keep="first")
    df = df.drop(columns=["_sal_bucket"])
    dupes = before - len(df)
    if dupes:
        all_warnings.append(f"{dupes} near-duplicate records removed")

    # IQR outlier capping on salary
    q1 = df["salary_in_usd"].quantile(0.25)
    q3 = df["salary_in_usd"].quantile(0.75)
    iqr = q3 - q1
    lower_cap = max(q1 - IQR_MULTIPLIER * iqr, SALARY_MIN_USD)
    upper_cap = min(q3 + IQR_MULTIPLIER * iqr, SALARY_MAX_USD)
    n_capped = int(((df["salary_in_usd"] < lower_cap) | (df["salary_in_usd"] > upper_cap)).sum())
    if n_capped:
        df["salary_in_usd"] = df["salary_in_usd"].clip(lower=lower_cap, upper=upper_cap)
        all_warnings.append(f"{n_capped} salary outlier(s) capped to [{lower_cap:.0f}, {upper_cap:.0f}]")

    total_clean = len(df)
    dropped = total_raw - total_clean
    drop_rate = dropped / total_raw if total_raw else 0.0

    salary_stats = {
        "min":    float(df["salary_in_usd"].min()),
        "max":    float(df["salary_in_usd"].max()),
        "mean":   float(df["salary_in_usd"].mean()),
        "median": float(df["salary_in_usd"].median()),
        "std":    float(df["salary_in_usd"].std()),
    }

    ok = total_clean >= MIN_RECORDS_FOR_TRAINING
    reason = (
        f"{total_clean} clean records from {total_raw} raw ({dropped} dropped, {drop_rate:.0%} rate)."
        if ok else
        f"Only {total_clean} clean records; need at least {MIN_RECORDS_FOR_TRAINING}. "
        "Try adding more job titles or countries."
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
