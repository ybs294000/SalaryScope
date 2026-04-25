"""
hr_tools/predict_helpers.py
---------------------------
Thin wrappers around App 1 (Random Forest) and App 2 (XGBoost) inference
used exclusively by the HR sub-tools. No session state is written here;
callers receive plain numeric results.

Both helpers return a dict:
    {
        "predicted_usd": float,       # raw model output in USD
        "band_label": str | None,     # salary band string if App 1
        "override_applied": bool,     # True when HR has overridden
        "final_usd": float,           # override value or predicted_usd
        "note": str,                  # human-readable provenance note
    }

Performance notes:
    - Each function runs model.predict() exactly once per call.
    - Callers read widget state first via render_override_widget(), then
      call predict once with override_usd already resolved. This removes
      the previous double-predict pattern.
    - batch_predict_app1 / batch_predict_app2 build the full feature
      DataFrame and call model.predict() once for the entire team,
      replacing the previous row-by-row loop in team_audit.
    - Plotly is not imported here.
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# App 1 — single-row inference
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
    """Run App 1 (Random Forest) inference. Calls model.predict() once."""

    tf = title_features(job_title)
    row = pd.DataFrame([{
        "Age":                 age,
        "Years of Experience": years_experience,
        "Education Level":     education_level,
        "Senior":              is_senior,
        "Gender":              gender,
        "Job Title":           job_title,
        "Country":             country,
        "title_is_junior":     tf[0],
        "title_is_senior":     tf[1],
        "title_is_exec":       tf[2],
        "title_is_mgmt":       tf[3],
        "title_domain":        tf[4],
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
        note = (
            f"HR override applied ({override_reason or 'no reason stated'}). "
            f"Model estimate: ${predicted_usd:,.0f}."
        )
    else:
        final_usd = predicted_usd
        note = "Based on Model 1 (Random Forest) prediction."

    return {
        "predicted_usd":    predicted_usd,
        "band_label":       band_label,
        "override_applied": override_applied,
        "final_usd":        final_usd,
        "note":             note,
    }


# ---------------------------------------------------------------------------
# App 2 — single-row inference
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
    """Run App 2 (XGBoost) inference. Calls model.predict() once."""

    exp_code  = EXPERIENCE_REVERSE.get(experience_level, experience_level)
    emp_code  = EMPLOYMENT_REVERSE.get(employment_type, employment_type)
    size_code = COMPANY_SIZE_REVERSE.get(company_size, company_size)
    tf = title_features(job_title)
    domain = tf[4]

    row = pd.DataFrame([{
        "experience_level":   exp_code,
        "employment_type":    emp_code,
        "job_title":          job_title,
        "employee_residence": employee_residence,
        "remote_ratio":       remote_ratio,
        "company_location":   company_location,
        "company_size":       size_code,
        "exp_x_domain":       f"{exp_code}_{domain}",
        "title_is_junior":    tf[0],
        "title_is_senior":    tf[1],
        "title_is_exec":      tf[2],
        "title_is_mgmt":      tf[3],
        "title_domain":       domain,
    }])
    row.columns = row.columns.astype(str)

    try:
        raw = model.predict(row)[0]
        predicted_usd = float(np.expm1(raw))
    except Exception:
        predicted_usd = float(model.predict(row)[0])

    override_applied = override_usd is not None and override_usd > 0
    if override_applied:
        final_usd = float(override_usd)
        note = (
            f"HR override applied ({override_reason or 'no reason stated'}). "
            f"Model estimate: ${predicted_usd:,.0f}."
        )
    else:
        final_usd = predicted_usd
        note = "Based on Model 2 (XGBoost) prediction."

    return {
        "predicted_usd":    predicted_usd,
        "band_label":       None,
        "override_applied": override_applied,
        "final_usd":        final_usd,
        "note":             note,
    }


# ---------------------------------------------------------------------------
# Override UI widget
# ---------------------------------------------------------------------------

def render_override_widget(
    key_prefix: str,
    model_estimate_usd: float,
) -> tuple[float | None, str]:
    """
    Renders the HR override expander.
    Returns (override_usd_or_None, reason_string).

    Usage pattern: call this BEFORE predict_app1/predict_app2.
    Pass the returned values as override_usd and override_reason.
    This way only one predict() call is needed, not two.

        override_val, override_reason = render_override_widget(key, estimate)
        result = predict_app1(..., override_usd=override_val, ...)
    """
    import streamlit as st

    # Show a compact read-only estimate line above the expander so the
    # HR user knows what the model says before deciding to override.
    st.caption(f"Model estimate: **${model_estimate_usd:,.0f}** USD / year")

    with st.expander(":material/edit: HR Override — adjust model estimate", expanded=False):
        st.caption(
            "Use this if the model estimate does not match your internal salary bands, "
            "local market data, or company-specific compensation policy. "
            "The original model estimate is always recorded alongside any override."
        )

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
                    placeholder="e.g. Internal band policy, local market adjustment",
                    key=f"{key_prefix}_override_reason",
                )

            delta = override_val - model_estimate_usd
            delta_pct = (delta / model_estimate_usd * 100) if model_estimate_usd else 0
            sign = "+" if delta >= 0 else ""
            st.caption(
                f"Override is {sign}{delta_pct:.1f}% ({sign}${delta:,.0f}) "
                f"vs model estimate of ${model_estimate_usd:,.0f}."
            )
            return float(override_val), override_reason

        return None, ""


# ---------------------------------------------------------------------------
# App 1 — vectorised batch predict (used by team_audit only)
# ---------------------------------------------------------------------------

def batch_predict_app1(
    model,
    df: "pd.DataFrame",
    title_features,
) -> "pd.Series":
    """
    Run App 1 inference on an entire DataFrame in one model.predict() call.
    Returns a Series of predicted USD values aligned to df.index.
    NaN is returned for any row where feature engineering fails.
    """
    try:
        tf_results = df["Job Title"].apply(title_features)
        tf_df = pd.DataFrame(
            tf_results.tolist(),
            columns=["title_is_junior", "title_is_senior", "title_is_exec",
                     "title_is_mgmt", "title_domain"],
            index=df.index,
        )

        feat = pd.concat([
            pd.DataFrame({
                "Age":                 pd.to_numeric(df["Age"], errors="coerce").fillna(30),
                "Years of Experience": pd.to_numeric(df["Years of Experience"], errors="coerce").fillna(5),
                "Education Level":     pd.to_numeric(df["Education Level"], errors="coerce").fillna(1),
                "Senior":              pd.to_numeric(df["Senior"], errors="coerce").fillna(0),
                "Gender":              df["Gender"].astype(str),
                "Job Title":           df["Job Title"].astype(str),
                "Country":             df["Country"].astype(str),
            }, index=df.index),
            tf_df,
        ], axis=1)

        preds = model.predict(feat)
        return pd.Series(preds.astype(float), index=df.index)

    except Exception:
        return pd.Series([np.nan] * len(df), index=df.index)


# ---------------------------------------------------------------------------
# App 2 — vectorised batch predict (used by team_audit only)
# ---------------------------------------------------------------------------

def batch_predict_app2(
    model,
    df: "pd.DataFrame",
    title_features,
    EXPERIENCE_REVERSE: dict,
    EMPLOYMENT_REVERSE: dict,
    COMPANY_SIZE_REVERSE: dict,
) -> "pd.Series":
    """
    Run App 2 inference on an entire DataFrame in one model.predict() call.
    Returns a Series of predicted USD values aligned to df.index.
    """
    try:
        tf_results = df["job_title"].apply(title_features)
        tf_df = pd.DataFrame(
            tf_results.tolist(),
            columns=["title_is_junior", "title_is_senior", "title_is_exec",
                     "title_is_mgmt", "title_domain"],
            index=df.index,
        )

        exp_codes  = df["experience_level"].map(lambda x: EXPERIENCE_REVERSE.get(x, x))
        emp_codes  = df["employment_type"].map(lambda x: EMPLOYMENT_REVERSE.get(x, x))
        size_codes = df["company_size"].map(lambda x: COMPANY_SIZE_REVERSE.get(x, x))

        feat = pd.concat([
            pd.DataFrame({
                "experience_level":   exp_codes,
                "employment_type":    emp_codes,
                "job_title":          df["job_title"].astype(str),
                "employee_residence": df["employee_residence"].astype(str),
                "remote_ratio":       pd.to_numeric(df["remote_ratio"], errors="coerce").fillna(0),
                "company_location":   df["company_location"].astype(str),
                "company_size":       size_codes,
                "exp_x_domain":       exp_codes + "_" + tf_df["title_domain"],
            }, index=df.index),
            tf_df,
        ], axis=1)

        feat.columns = feat.columns.astype(str)
        raw = model.predict(feat)
        return pd.Series(np.expm1(raw).astype(float), index=df.index)

    except Exception:
        return pd.Series([np.nan] * len(df), index=df.index)
