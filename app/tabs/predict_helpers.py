"""
hr_tools/predict_helpers.py
---------------------------
Thin wrappers around App 1 (Random Forest) and App 2 (XGBoost) inference
used exclusively by the HR sub-tools. No session state is written here;
callers receive plain numeric results.

Both helpers return a dict:
    {
        "predicted_usd": float,          # raw model output in USD
        "band_label": str | None,        # salary band string if available
        "override_applied": bool,        # True when HR has overridden
        "final_usd": float,              # override value or predicted_usd
        "note": str,                     # human-readable provenance note
    }
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# App 1 inference
# ---------------------------------------------------------------------------

def predict_app1(
    model,
    salary_band_model,
    job_title: str,
    country: str,
    years_experience: float,
    education_level: int,
    age: int,
    gender: str,
    is_senior: int,
    title_features,
    SALARY_BAND_LABELS: dict,
    override_usd: float | None = None,
    override_reason: str = "",
) -> dict:
    """
    Run App 1 (Random Forest) inference for a single profile.
    Returns the prediction dict described in module docstring.
    """

    tf = title_features(job_title)
    tf_dict = {
        "title_is_junior": tf[0],
        "title_is_senior": tf[1],
        "title_is_exec":   tf[2],
        "title_is_mgmt":   tf[3],
        "title_domain":    tf[4],
    }

    row = pd.DataFrame([{
        "Age":                  age,
        "Years of Experience":  years_experience,
        "Education Level":      education_level,
        "Senior":               is_senior,
        "Gender":               gender,
        "Job Title":            job_title,
        "Country":              country,
        **tf_dict,
    }])

    predicted_usd = float(model.predict(row)[0])

    band_label = None
    if salary_band_model is not None:
        try:
            band_raw = salary_band_model.predict(row)[0]
            band_label = SALARY_BAND_LABELS.get(band_raw, band_raw)
        except Exception:
            pass

    override_applied = override_usd is not None and override_usd > 0

    if override_applied:
        final_usd = float(override_usd)
        note = f"HR override applied ({override_reason or 'no reason stated'}). Model estimate: ${predicted_usd:,.0f}."
    else:
        final_usd = predicted_usd
        note = "Based on Model 1 (Random Forest) prediction."

    return {
        "predicted_usd":   predicted_usd,
        "band_label":      band_label,
        "override_applied": override_applied,
        "final_usd":       final_usd,
        "note":            note,
    }


# ---------------------------------------------------------------------------
# App 2 inference
# ---------------------------------------------------------------------------

def predict_app2(
    model,
    job_title: str,
    experience_level: str,
    employment_type: str,
    company_location: str,
    employee_residence: str,
    remote_ratio: int,
    company_size: str,
    title_features,
    EXPERIENCE_REVERSE: dict,
    EMPLOYMENT_REVERSE: dict,
    COMPANY_SIZE_REVERSE: dict,
    override_usd: float | None = None,
    override_reason: str = "",
) -> dict:
    """
    Run App 2 (XGBoost) inference for a single profile.
    Returns the prediction dict described in module docstring.
    """

    exp_code  = EXPERIENCE_REVERSE.get(experience_level, experience_level)
    emp_code  = EMPLOYMENT_REVERSE.get(employment_type, employment_type)
    size_code = COMPANY_SIZE_REVERSE.get(company_size, company_size)

    tf = title_features(job_title)
    tf_dict = {
        "title_is_junior": tf[0],
        "title_is_senior": tf[1],
        "title_is_exec":   tf[2],
        "title_is_mgmt":   tf[3],
        "title_domain":    tf[4],
    }

    exp_x_domain = f"{exp_code}_{tf_dict['title_domain']}"

    row = pd.DataFrame([{
        "experience_level":   exp_code,
        "employment_type":    emp_code,
        "job_title":          job_title,
        "employee_residence": employee_residence,
        "remote_ratio":       remote_ratio,
        "company_location":   company_location,
        "company_size":       size_code,
        "exp_x_domain":       exp_x_domain,
        **tf_dict,
    }])

    row.columns = row.columns.astype(str)

    try:
        raw = model.predict(row)[0]
        # XGBoost model was trained on log-transformed target
        predicted_usd = float(np.expm1(raw))
    except Exception:
        predicted_usd = float(model.predict(row)[0])

    override_applied = override_usd is not None and override_usd > 0

    if override_applied:
        final_usd = float(override_usd)
        note = f"HR override applied ({override_reason or 'no reason stated'}). Model estimate: ${predicted_usd:,.0f}."
    else:
        final_usd = predicted_usd
        note = "Based on Model 2 (XGBoost) prediction."

    return {
        "predicted_usd":   predicted_usd,
        "band_label":      None,
        "override_applied": override_applied,
        "final_usd":       final_usd,
        "note":            note,
    }


# ---------------------------------------------------------------------------
# Override UI widget — reused in multiple tools
# ---------------------------------------------------------------------------

def render_override_widget(key_prefix: str, model_estimate_usd: float) -> tuple[float | None, str]:
    """
    Renders a standardised HR override section.
    Returns (override_value_or_None, reason_string).
    Key prefix must be unique per tool instance to avoid widget key collisions.
    """
    import streamlit as st

    with st.expander(":material/edit: HR Override — adjust model estimate", expanded=False):
        st.caption(
            "Use this section if the model estimate does not match your internal salary bands, "
            "local market data, or company-specific compensation policy. "
            "The override replaces the model value in all calculations below. "
            "The original model estimate is always recorded alongside the override."
        )

        col_toggle, col_spacer = st.columns([1, 3])
        with col_toggle:
            apply_override = st.checkbox(
                "Apply override",
                key=f"{key_prefix}_apply_override",
                value=False,
            )

        if apply_override:
            col_val, col_reason = st.columns([1, 2])
            with col_val:
                override_val = st.number_input(
                    "Override salary (USD / year)",
                    min_value=10_000,
                    max_value=2_000_000,
                    value=int(round(model_estimate_usd / 1000) * 1000),
                    step=1_000,
                    key=f"{key_prefix}_override_val",
                )
            with col_reason:
                override_reason = st.text_input(
                    "Reason for override",
                    placeholder="e.g. Internal band policy, local market adjustment, niche role",
                    key=f"{key_prefix}_override_reason",
                )

            delta = override_val - model_estimate_usd
            delta_pct = (delta / model_estimate_usd * 100) if model_estimate_usd else 0
            sign = "+" if delta >= 0 else ""
            st.caption(
                f"Override is {sign}{delta_pct:.1f}% ({sign}${delta:,.0f}) relative to model estimate of ${model_estimate_usd:,.0f}."
            )
            return float(override_val), override_reason

        return None, ""
