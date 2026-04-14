"""
live_model_predictor.py
=======================
Loads the live GBR model and runs salary inference.

Input features match live_model_trainer.ALL_FEATURES:
    experience_level_num  int   0-3
    education_level       int   0-3
    remote_ratio          int   0 / 50 / 100
    is_contract           int   0 / 1
    salary_band_ratio     float 0-5  (leave as 0.5 for user predictions)
    job_title             str   canonical name (normalised by cleaner)
    company_size          str   S / M / L
    company_location      str   ISO-2 code
    category_label        str   Adzuna category label (optional; defaults)

Title normalisation at prediction time
---------------------------------------
The predictor applies the same normalise_job_title() function used by the
cleaner, so a user typing "Senior Data Scientist" is mapped to "Data Scientist"
(the canonical training label) before inference. If the raw input does not
match any rule, the original input is passed through and the model will fall
back to the OHE infrequent bucket -- which degrades gracefully.

Rollback note
-------------
Remove the import in live_training_tab.py to deactivate.
"""

from __future__ import annotations

import pandas as pd

from app.utils.live_model_trainer import ALL_FEATURES, deserialise_artefact
from app.utils.live_model_storage import download_current_model
from app.utils.live_training_cleaner import normalise_job_title

EXPERIENCE_NUM_MAP: dict[str, int] = {
    "EN": 0, "MI": 1, "SE": 2, "EX": 3,
}

EXPERIENCE_DISPLAY: dict[str, str] = {
    "EN": "Entry Level",
    "MI": "Mid Level",
    "SE": "Senior Level",
    "EX": "Executive Level",
}

# Default category label used when the user does not supply one.
_DEFAULT_CATEGORY = "IT Jobs"


def build_input_row(
    experience_level: str,
    education_level: int,
    remote_ratio: int,
    job_title: str,
    company_size: str,
    company_location: str,
    is_contract: int = 0,
    salary_band_ratio: float = 0.5,
    category_label: str = _DEFAULT_CATEGORY,
) -> pd.DataFrame:
    """Build a single-row DataFrame for model.predict()."""
    exp_num = EXPERIENCE_NUM_MAP.get(experience_level.upper())
    if exp_num is None:
        raise ValueError(f"Unknown experience_level '{experience_level}'.")

    # Normalise job title to canonical form used during training.
    # If the input matches no rule, pass through as-is (graceful degradation).
    raw_title = str(job_title).strip()
    canonical = normalise_job_title(raw_title)
    final_title = canonical if canonical is not None else raw_title

    row = {
        "experience_level_num": exp_num,
        "education_level":      int(education_level),
        "remote_ratio":         int(remote_ratio),
        "is_contract":          int(is_contract),
        "salary_band_ratio":    float(salary_band_ratio),
        "job_title":            final_title,
        "company_size":         str(company_size).strip().upper(),
        "company_location":     str(company_location).strip().upper(),
        "category_label":       str(category_label).strip() if category_label else _DEFAULT_CATEGORY,
    }
    return pd.DataFrame([row])[ALL_FEATURES]


def load_live_model_from_bytes(model_bytes: bytes) -> tuple[dict | None, str | None]:
    try:
        return deserialise_artefact(model_bytes), None
    except Exception as exc:
        return None, f"Deserialisation failed: {exc}"


def load_live_model_from_storage() -> tuple[dict | None, str | None]:
    model_bytes, err = download_current_model()
    if err:
        return None, err
    return load_live_model_from_bytes(model_bytes)


def predict_salary(
    artefact: dict,
    experience_level: str,
    education_level: int,
    remote_ratio: int,
    job_title: str,
    company_size: str,
    company_location: str,
    is_contract: int = 0,
    salary_band_ratio: float = 0.5,
    category_label: str = _DEFAULT_CATEGORY,
) -> tuple[float | None, float | None, float | None, str | None]:
    """
    Run one prediction.
    Returns (pred, lower_80pct, upper_80pct, error).
    """
    try:
        pipe = artefact["model"]
        meta = artefact["metadata"]

        X    = build_input_row(
            experience_level, education_level, remote_ratio,
            job_title, company_size, company_location,
            is_contract=is_contract,
            salary_band_ratio=salary_band_ratio,
            category_label=category_label,
        )
        pred = float(pipe.predict(X)[0])
        pred = max(pred, 0.0)

        mae    = float(meta.get("test_mae", pred * 0.15))
        margin = 1.28 * mae
        lower  = max(pred - margin, 0.0)
        upper  = pred + margin

        return pred, lower, upper, None
    except Exception as exc:
        return None, None, None, str(exc)
