"""
live_model_trainer.py
=====================
Trains a GradientBoostingRegressor on cleaned Adzuna salary data and
packages the result as a versioned artefact.

Feature set (expanded from previous version):
    Numeric:
        experience_level_num   0-3  (inferred from raw title keywords)
        education_level        0-3  (defaults to 1 from Adzuna; reserved for enrichment)
        remote_ratio           0 / 50 / 100  (inferred from title keywords)
        is_contract            0 / 1  (permanent=0, contract/temp=1)
        salary_band_ratio      float 0-5  (salary_max/salary_min - 1; precision proxy)

    Categorical:
        job_title              canonical normalised title (e.g. "Data Scientist")
        company_size           S / M / L  (defaults to M from Adzuna)
        company_location       ISO-2 code
        category_label         Adzuna category (e.g. "IT Jobs", "Accounting Jobs")

Model artefact schema
---------------------
{
    "model":    sklearn Pipeline,
    "metadata": {
        "version", "trained_at", "n_samples", "features",
        "cv_r2_mean", "cv_r2_std", "cv_mae_mean",
        "test_r2", "test_mae", "test_rmse",
        "target", "model_type", "source", "previous_hash"
    }
}

Rollback note
-------------
Delete this file and the import in live_training_tab.py to remove training.
The storage and prediction modules are unaffected.
"""

from __future__ import annotations

import io
import hashlib
import datetime
import numpy as np
import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.utils.live_training_cleaner import MIN_RECORDS_FOR_TRAINING

# ---------------------------------------------------------------------------
# FEATURE DEFINITIONS
# ---------------------------------------------------------------------------

NUMERIC_FEATURES: list[str] = [
    "experience_level_num",  # 0-3 inferred from raw title
    "education_level",       # 0-3 (mostly 1 from Adzuna; reserved for enrichment)
    "remote_ratio",          # 0 / 50 / 100 inferred from title keywords
    "is_contract",           # 0=permanent, 1=contract/temp
    "salary_band_ratio",     # (max-min)/min -- salary precision proxy, 0-5
]

CATEGORICAL_FEATURES: list[str] = [
    "job_title",          # canonical normalised name
    "company_size",       # S / M / L (defaults to M from Adzuna)
    "company_location",   # ISO-2 code
    "category_label",     # Adzuna category label
]

ALL_FEATURES: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET: str = "salary_in_usd"

# Tuned for real job-listing datasets (200-5000 rows typical with multi-domain fetch)
GBR_PARAMS: dict = {
    "n_estimators":     500,
    "learning_rate":    0.04,
    "max_depth":        4,
    "min_samples_leaf": 4,
    "subsample":        0.8,
    "loss":             "huber",   # robust to salary outliers
    "random_state":     42,
}

# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

def _build_pipeline() -> Pipeline:
    numeric_transformer = StandardScaler()

    categorical_transformer = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
        min_frequency=3,    # rare titles / locations collapse to 'infrequent'
        max_categories=250,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer,     NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    pipe = Pipeline([
        ("preprocessor", preprocessor),
        ("model",        GradientBoostingRegressor(**GBR_PARAMS)),
    ])
    return pipe


# ---------------------------------------------------------------------------
# TRAINING
# ---------------------------------------------------------------------------

def train_live_model(
    df_clean: pd.DataFrame,
    previous_model_bytes: bytes | None = None,
) -> tuple[dict | None, dict]:
    """
    Train on cleaned Adzuna data.

    Parameters
    ----------
    df_clean             : cleaned DataFrame from clean_adzuna_records()
    previous_model_bytes : bytes of the current HF model (for hash tracking)

    Returns (artefact, train_report). artefact is None on failure.
    """
    if len(df_clean) < MIN_RECORDS_FOR_TRAINING:
        return None, {
            "ok": False,
            "reason": (
                f"Need at least {MIN_RECORDS_FOR_TRAINING} clean records; "
                f"got {len(df_clean)}."
            ),
            "details": {},
        }

    missing = [c for c in ALL_FEATURES + [TARGET] if c not in df_clean.columns]
    if missing:
        return None, {
            "ok": False,
            "reason": f"Missing columns: {missing}",
            "details": {},
        }

    try:
        X = df_clean[ALL_FEATURES].copy()
        y = df_clean[TARGET].copy()

        folds = min(5, max(3, len(df_clean) // 50))

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42,
                stratify=df_clean["company_location"],
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42,
            )

        pipe = _build_pipeline()

        cv_r2  = cross_val_score(
            pipe, X_train, y_train, cv=folds, scoring="r2", n_jobs=-1
        )
        cv_mae = cross_val_score(
            pipe, X_train, y_train, cv=folds,
            scoring="neg_mean_absolute_error", n_jobs=-1,
        )

        pipe.fit(X_train, y_train)

        y_pred    = pipe.predict(X_test)
        test_r2   = float(r2_score(y_test, y_pred))
        test_mae  = float(mean_absolute_error(y_test, y_pred))
        test_rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

        prev_hash = (
            hashlib.sha256(previous_model_bytes).hexdigest()
            if previous_model_bytes else None
        )

        now     = datetime.datetime.utcnow()
        version = now.strftime("%Y%m%dT%H%M%SZ")

        artefact = {
            "model": pipe,
            "metadata": {
                "version":       version,
                "trained_at":    now.isoformat(),
                "n_samples":     int(len(df_clean)),
                "n_train":       int(len(X_train)),
                "n_test":        int(len(X_test)),
                "features":      ALL_FEATURES,
                "target":        TARGET,
                "cv_folds":      folds,
                "cv_r2_mean":    float(np.mean(cv_r2)),
                "cv_r2_std":     float(np.std(cv_r2)),
                "cv_mae_mean":   float(-np.mean(cv_mae)),
                "test_r2":       test_r2,
                "test_mae":      test_mae,
                "test_rmse":     test_rmse,
                "model_type":    "GradientBoostingRegressor",
                "gbr_params":    GBR_PARAMS,
                "source":        "adzuna_live_training",
                "previous_hash": prev_hash,
            },
        }

        return artefact, {
            "ok": True,
            "reason": "Training completed successfully.",
            "details": {
                "n_samples":   int(len(df_clean)),
                "cv_r2_mean":  float(np.mean(cv_r2)),
                "cv_r2_std":   float(np.std(cv_r2)),
                "cv_mae_mean": float(-np.mean(cv_mae)),
                "test_r2":     test_r2,
                "test_mae":    test_mae,
                "test_rmse":   test_rmse,
                "version":     version,
            },
        }

    except Exception as exc:
        return None, {"ok": False, "reason": f"Training error: {exc}", "details": {}}


# ---------------------------------------------------------------------------
# SERIALISATION
# ---------------------------------------------------------------------------

def serialise_artefact(artefact: dict) -> bytes:
    buf = io.BytesIO()
    joblib.dump(artefact, buf, compress=3)
    return buf.getvalue()


def deserialise_artefact(data: bytes) -> dict:
    return joblib.load(io.BytesIO(data))
