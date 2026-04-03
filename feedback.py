"""
feedback.py — Prediction Feedback System for SalaryScope
=========================================================
Provides:
  - save_feedback()  : persists a feedback record to Firestore
  - feedback_ui()    : renders a collapsible feedback form in Streamlit

Firestore path:  feedback/{auto-id}
Completely separate from the predictions/ collection.
"""

import streamlit as st
import json
from datetime import datetime


# ------------------------------------------------------------------
# FIRESTORE HELPER
# Reuses the same cached client from database.py — no second init.
# ------------------------------------------------------------------

def _db():
    from database import _get_firestore_client
    return _get_firestore_client()


# ------------------------------------------------------------------
# SAVE FEEDBACK
# ------------------------------------------------------------------

def save_feedback(
    username: str,
    model_used: str,
    input_data: dict,
    predicted_salary: float,
    accuracy_rating: str,        # "Yes" | "Somewhat" | "No"
    direction: str,              # "Too High" | "About Right" | "Too Low"
    actual_salary: float | None,
    star_rating: int,            # 1–5
):
    """
    Write one feedback document to Firestore.
    All fields are structured — no free-text.
    """
    db = _db()
    db.collection("feedback").add({
        "username": username or "anonymous",
        "model_used": model_used,
        "input_data": json.dumps(input_data),   # same pattern as save_prediction()
        "predicted_salary": predicted_salary,
        "accuracy_rating": accuracy_rating,
        "direction": direction,
        "actual_salary": actual_salary,          # None when not provided
        "star_rating": star_rating,
        "created_at": datetime.utcnow().isoformat(),
    })


# ------------------------------------------------------------------
# FEEDBACK UI
# ------------------------------------------------------------------

def feedback_ui(predicted_salary: float, model_used: str, input_data: dict):
    """
    Renders a collapsible feedback expander.

    Parameters
    ----------
    predicted_salary : float
        The salary value just predicted (stored for reference).
    model_used : str
        Short label e.g. "Random Forest" or "XGBoost".
    input_data : dict
        The exact input fields used to produce this prediction
        (mirroring what is passed to save_prediction).
    """

    if predicted_salary is None:
        return

    # Per-prediction session key — resets automatically when a new
    # prediction with a different salary is run.
    submitted_key = f"_feedback_submitted_{model_used}_{int(predicted_salary)}"

    with st.expander(f"{chr(0x1F4DD)} Share Feedback on This Prediction", expanded=False):
        if st.session_state.get(submitted_key):
            st.success("Thank you for your feedback!")
            return

        st.caption(
            "Help us improve by letting us know how accurate this prediction was. "
            "Star rating is required; all other fields are optional."
        )

        # --- Row 1: Accuracy + Direction -------------------------
        col_a, col_b = st.columns(2)

        with col_a:
            accuracy_rating = st.radio(
                "Was the prediction accurate?",
                options=["Yes", "Somewhat", "No"],
                index=0,
                horizontal=True,
                key=f"fb_accuracy_{model_used}_{int(predicted_salary)}"
            )

        with col_b:
            direction = st.radio(
                "How did it compare to reality?",
                options=["Too High", "About Right", "Too Low"],
                index=1,
                horizontal=True,
                key=f"fb_direction_{model_used}_{int(predicted_salary)}"
            )

        # --- Row 2: Star rating ------------------------------
        star_rating = st.select_slider(
            "Overall rating",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: "⭐" * x,
            key=f"fb_stars_{model_used}_{int(predicted_salary)}"
        )

        # ── Row 3: Optional actual salary ------------------------
        actual_salary_raw = st.number_input(
            "Your actual / expected salary (USD, optional)",
            min_value=0.0,
            max_value=10_000_000.0,
            value=0.0,
            step=1000.0,
            format="%.0f",
            help="Leave at 0 to skip.",
            key=f"fb_actual_{model_used}_{int(predicted_salary)}"
        )
        actual_salary = float(actual_salary_raw) if actual_salary_raw > 0 else None

        # --- Submit ------------------------------------------------
        if st.button(
            "Submit Feedback",
            key=f"fb_submit_{model_used}_{int(predicted_salary)}",
            use_container_width=True,
            type="primary"
        ):
            username = st.session_state.get("username") or "anonymous"

            try:
                save_feedback(
                    username=username,
                    model_used=model_used,
                    input_data=input_data,
                    predicted_salary=predicted_salary,
                    accuracy_rating=accuracy_rating,
                    direction=direction,
                    actual_salary=actual_salary,
                    star_rating=star_rating,
                )
                st.session_state[submitted_key] = True
                st.success("Thank you for your feedback!")
                st.rerun()

            except Exception as e:
                st.error("Could not save feedback. Please try again later.")
                st.exception(e)