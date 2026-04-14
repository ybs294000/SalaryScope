"""
live_model_predictor.py
=======================
Loads the live GBR model and runs salary inference.

Input features match live_model_trainer.ALL_FEATURES:
    experience_level_num  int   0-3
    education_level       int   0-3
    remote_ratio          int   0 / 50 / 100
    job_title             str
    company_size          str   S / M / L
    company_location      str   ISO-2 code

Rollback note
-------------
Remove the import in live_training_tab.py to deactivate.
"""

from __future__ import annotations

import io
import pandas as pd
import numpy as np

from app.utils.live_model_trainer import ALL_FEATURES, deserialise_artefact
from app.utils.live_model_storage import download_current_model

# Experience level ordinals (matches cleaner inference)
EXPERIENCE_NUM_MAP: dict[str, int] = {
    "EN": 0, "MI": 1, "SE": 2, "EX": 3,
}

EXPERIENCE_DISPLAY: dict[str, str] = {
    "EN": "Entry Level",
    "MI": "Mid Level",
    "SE": "Senior Level",
    "EX": "Executive Level",
}


def build_input_row(
    experience_level: str,
    education_level: int,
    remote_ratio: int,
    job_title: str,
    company_size: str,
    company_location: str,
) -> pd.DataFrame:
    """Build a single-row DataFrame for model.predict()."""
    exp_num = EXPERIENCE_NUM_MAP.get(experience_level.upper())
    if exp_num is None:
        raise ValueError(f"Unknown experience_level '{experience_level}'.")
    row = {
        "experience_level_num": exp_num,
        "education_level":      int(education_level),
        "remote_ratio":         int(remote_ratio),
        "job_title":            str(job_title).strip(),
        "company_size":         str(company_size).strip().upper(),
        "company_location":     str(company_location).strip().upper(),
    }
    return pd.DataFrame([row])[ALL_FEATURES]


def load_live_model_from_bytes(model_bytes: bytes) -> tuple[dict | None, str | None]:
    """Deserialise artefact from bytes. Returns (artefact, error)."""
    try:
        return deserialise_artefact(model_bytes), None
    except Exception as exc:
        return None, f"Deserialisation failed: {exc}"


def load_live_model_from_storage() -> tuple[dict | None, str | None]:
    """Download and deserialise the current live model."""
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
) -> tuple[float | None, float | None, float | None, str | None]:
    """
    Run one prediction.
    Returns (pred, lower_80pct, upper_80pct, error).
    """
    try:
        pipe = artefact["model"]
        meta = artefact["metadata"]

        X    = build_input_row(experience_level, education_level, remote_ratio,
                               job_title, company_size, company_location)
        pred = float(pipe.predict(X)[0])
        pred = max(pred, 0.0)

        mae    = float(meta.get("test_mae", pred * 0.15))
        margin = 1.28 * mae
        lower  = max(pred - margin, 0.0)
        upper  = pred + margin

        return pred, lower, upper, None
    except Exception as exc:
        return None, None, None, str(exc)
