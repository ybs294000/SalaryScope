from __future__ import annotations
from typing import Any

import streamlit as st

from app.utils.budget_utils import render_budget_planner
from app.utils.col_utils import render_col_adjuster
from app.utils.ctc_utils import render_ctc_adjuster
from app.utils.currency_utils import (
    currency_dropdown_options,
    get_active_currency,
    get_active_rates,
    get_exchange_rates,
    guess_currency,
    parse_currency_option,
    render_currency_converter,
)
from app.utils.emergency_fund_utils import render_emergency_fund_planner
from app.utils.fire_utils import render_fire_calculator
from app.utils.investment_utils import render_investment_estimator
from app.utils.lifestyle_utils import render_lifestyle_split
from app.utils.loan_utils import render_loan_adjuster
from app.utils.savings_utils import render_savings_adjuster
from app.utils.takehome_utils import render_takehome_adjuster
from app.utils.tax_utils import render_tax_adjuster


def render_financial_planning_tab() -> None:
    st.header(":material/account_balance_wallet: Financial Planning")
    st.caption(
        "Use a recent SalaryScope result or enter a salary manually to explore take-home pay, "
        "budgeting, savings, borrowing, and long-term planning in one place."
    )

    available_sources = _build_available_sources()

    source_labels = list(available_sources.keys()) + ["Enter Salary Manually"]
    default_index = 0 if available_sources else source_labels.index("Enter Salary Manually")

    selected_source = st.radio(
        "Choose a salary source",
        options=source_labels,
        index=default_index,
        horizontal=True,
        key="financial_planning_source",
    )

    if selected_source != "Enter Salary Manually" and not available_sources:
        st.info(
            "Run a prediction or extract an offer letter first if you want to plan from an existing SalaryScope result. "
            "You can still use manual entry below."
        )

    if selected_source == "Enter Salary Manually":
        source_payload = _render_manual_source_form()
        if not source_payload:
            st.info(
                "Enter an annual salary, pick the currency, and choose a location to start planning."
            )
            return
    else:
        source_payload = available_sources[selected_source]

    st.divider()
    _render_source_snapshot(source_payload)

    source_id = source_payload["source_id"]
    widget_prefix = f"planning_{source_id}"

    st.divider()
    section_tabs = st.tabs(
        [
            "Income & Payroll",
            "Monthly Planning",
            "Goals & Borrowing",
        ]
    )

    with section_tabs[0]:
        render_currency_converter(
            usd_amount=source_payload["annual_salary_usd"],
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_currency",
        )
        active_currency = get_active_currency(f"{widget_prefix}_currency")
        active_rates = get_active_rates()

        render_tax_adjuster(
            gross_usd=source_payload["annual_salary_usd"],
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_tax",
            converted_currency=active_currency,
            rates=active_rates,
        )
        render_col_adjuster(
            gross_usd=source_payload["annual_salary_usd"],
            work_country=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_col",
        )
        render_ctc_adjuster(
            gross_usd=source_payload["annual_salary_usd"],
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_ctc",
        )
        takehome_result = render_takehome_adjuster(
            gross_usd=source_payload["annual_salary_usd"],
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_takehome",
            net_usd=None,
        )

    net_monthly_usd = _extract_net_monthly(
        takehome_result,
        source_payload["annual_salary_usd"] / 12,
    )

    with section_tabs[1]:
        savings_result = render_savings_adjuster(
            net_monthly_usd=net_monthly_usd,
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_savings",
            gross_usd=source_payload["annual_salary_usd"],
        )
        render_budget_planner(
            net_monthly_usd=net_monthly_usd,
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_budget",
            gross_usd=source_payload["annual_salary_usd"],
        )
        render_emergency_fund_planner(
            net_monthly_usd=net_monthly_usd,
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_emergency",
            gross_usd=source_payload["annual_salary_usd"],
        )
        render_lifestyle_split(
            net_monthly_usd=net_monthly_usd,
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_lifestyle",
            gross_usd=source_payload["annual_salary_usd"],
        )

    monthly_savings_usd = _extract_monthly_savings(
        savings_result,
        net_monthly_usd * 0.20,
    )

    with section_tabs[2]:
        render_loan_adjuster(
            net_monthly_usd=net_monthly_usd,
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_loan",
            gross_usd=source_payload["annual_salary_usd"],
        )
        render_investment_estimator(
            monthly_savings_usd=monthly_savings_usd,
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_investment",
            net_monthly_usd=net_monthly_usd,
        )
        render_fire_calculator(
            annual_salary_usd=source_payload["annual_salary_usd"],
            location_hint=source_payload["location_hint"],
            widget_key=f"{widget_prefix}_fire",
            net_monthly_usd=net_monthly_usd,
            savings_monthly_usd=monthly_savings_usd,
        )


def _build_available_sources() -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}

    manual_result = st.session_state.get("manual_prediction_result")
    if manual_result and isinstance(manual_result, dict) and manual_result.get("prediction"):
        details = manual_result.get("input_details", {})
        location = details.get("Country") or details.get("Company Location") or "Unknown"
        role = details.get("Job Title") or "Latest manual prediction"
        model_label = "Model 1" if "salary_band_label" in manual_result else "Model 2"
        sources["Latest Manual Prediction"] = {
            "source_id": "manual_prediction",
            "title": "Latest Manual Prediction",
            "subtitle": f"{model_label} result",
            "annual_salary_usd": float(manual_result["prediction"]),
            "role_title": role,
            "location_hint": location,
            "location_display": location,
            "source_note": "Uses the most recent manual prediction currently stored in this session.",
        }

    resume_result = st.session_state.get("resume_prediction_result")
    if resume_result and isinstance(resume_result, dict) and resume_result.get("prediction"):
        details = resume_result.get("input_details", {})
        location = details.get("Country") or "Unknown"
        role = details.get("Job Title") or "Latest resume prediction"
        sources["Latest Resume Prediction"] = {
            "source_id": "resume_prediction",
            "title": "Latest Resume Prediction",
            "subtitle": "Model 1 result",
            "annual_salary_usd": float(resume_result["prediction"]),
            "role_title": role,
            "location_hint": location,
            "location_display": location,
            "source_note": "Uses the most recent resume-based prediction currently stored in this session.",
        }

    resume_result_a2 = st.session_state.get("resume_prediction_result_a2")
    if resume_result_a2 and isinstance(resume_result_a2, dict) and resume_result_a2.get("prediction_a2"):
        details = resume_result_a2.get("input_details_a2", {})
        location = resume_result_a2.get("company_location_code_a2") or details.get("Company Location") or "Unknown"
        role = details.get("Job Title") or "Latest resume prediction"
        sources["Latest Resume Prediction (Model 2)"] = {
            "source_id": "resume_prediction_model2",
            "title": "Latest Resume Prediction",
            "subtitle": "Model 2 result",
            "annual_salary_usd": float(resume_result_a2["prediction_a2"]),
            "role_title": role,
            "location_hint": location,
            "location_display": details.get("Company Location") or location,
            "source_note": "Uses the most recent Model 2 resume prediction currently stored in this session.",
        }

    offer_result = st.session_state.get("offer_letter_result")
    if offer_result and isinstance(offer_result, dict):
        offer_payload = _build_offer_source(offer_result)
        if offer_payload:
            sources["Latest Offer Letter"] = offer_payload

    manual_payload = st.session_state.get("financial_planning_manual_payload")
    if manual_payload and isinstance(manual_payload, dict):
        sources["Saved Manual Entry"] = manual_payload

    return sources


def _build_offer_source(offer_result: dict[str, Any]) -> dict[str, Any] | None:
    fields = offer_result.get("fields", {}) or {}
    total_ctc = fields.get("total_ctc")
    base_salary = fields.get("base_salary")
    annual_bonus_fixed = fields.get("annual_bonus_fixed") or 0.0
    currency_code = str(fields.get("currency_code") or "").upper().strip()

    if total_ctc and float(total_ctc) > 0:
        annual_local = float(total_ctc)
        source_basis = "Offer letter total compensation"
    elif base_salary and float(base_salary) > 0:
        annual_local = float(base_salary) + float(annual_bonus_fixed)
        source_basis = "Offer letter base salary"
    else:
        return None

    annual_usd = _convert_local_to_usd(annual_local, currency_code)
    if annual_usd is None:
        return None

    location_hint = fields.get("country_code") or fields.get("location") or currency_code or "Unknown"
    return {
        "source_id": "offer_letter",
        "title": "Latest Offer Letter",
        "subtitle": source_basis,
        "annual_salary_usd": annual_usd,
        "role_title": fields.get("job_title") or "Offer letter result",
        "location_hint": location_hint,
        "location_display": fields.get("location") or fields.get("country_code") or "Unknown",
        "source_note": "Uses the compensation currently reviewed in the Offer Letter workflow.",
    }


def _render_manual_source_form() -> dict[str, Any] | None:
    st.subheader("Manual Planning Input")
    st.write("Enter an annual salary and location if you want to use the planning tools without a saved prediction.")

    stored = st.session_state.get("financial_planning_manual_payload", {})
    stored_location = stored.get("location_display", "United States")
    stored_currency = stored.get("manual_currency_code", guess_currency(stored_location))

    with st.form("financial_planning_manual_form"):
        role_title = st.text_input(
            "Role or label",
            value=stored.get("role_title", "Custom salary input"),
        )
        location = st.text_input(
            "Country or work location",
            value=stored_location,
            help="Examples: India, United States, Germany, Singapore",
        )

        currency_options = currency_dropdown_options()
        default_currency = guess_currency(location) or stored_currency or "USD"
        default_option = _default_currency_option(currency_options, default_currency)
        currency_option = st.selectbox(
            "Salary currency",
            currency_options,
            index=currency_options.index(default_option),
        )
        currency_code = parse_currency_option(currency_option)

        annual_salary = st.number_input(
            "Annual salary",
            min_value=0.0,
            value=float(stored.get("manual_amount_local", 0.0) or 0.0),
            step=1000.0,
        )

        submitted = st.form_submit_button("Use This Salary", type="primary", width="stretch")

    if submitted:
        if annual_salary <= 0:
            st.error("Enter a salary greater than zero to continue.")
            return None

        annual_usd = _convert_local_to_usd(annual_salary, currency_code)
        if annual_usd is None:
            st.error("This currency could not be converted right now. Try another currency or try again later.")
            return None

        st.session_state.financial_planning_manual_payload = {
            "source_id": "manual_entry",
            "title": "Manual Salary Entry",
            "subtitle": f"Entered in {currency_code}",
            "annual_salary_usd": annual_usd,
            "role_title": role_title or "Custom salary input",
            "location_hint": location or "United States",
            "location_display": location or "United States",
            "source_note": "Uses the annual salary you entered in this tab.",
            "manual_currency_code": currency_code,
            "manual_amount_local": float(annual_salary),
        }

    return st.session_state.get("financial_planning_manual_payload")


def _render_source_snapshot(source_payload: dict[str, Any]) -> None:
    st.subheader("Planning Snapshot")
    st.write("Review the selected salary context before using the planning tools below.")

    annual_salary = float(source_payload["annual_salary_usd"])
    monthly_salary = annual_salary / 12
    weekly_salary = annual_salary / 52

    left, right = st.columns([1.5, 1])
    with left:
        st.markdown(f"**Source:** {source_payload['title']}")
        st.markdown(f"**Role:** {source_payload.get('role_title') or 'Not specified'}")
        st.markdown(f"**Location:** {source_payload.get('location_display') or 'Not specified'}")
        if source_payload.get("subtitle"):
            st.markdown(f"**Context:** {source_payload['subtitle']}")
        if source_payload.get("source_note"):
            st.caption(source_payload["source_note"])
    with right:
        metric_cols_top = st.columns(2)
        metric_cols_bottom = st.columns(2)
        metric_cols_top[0].metric("Annual Gross (USD)", f"${annual_salary:,.2f}")
        metric_cols_top[1].metric("Monthly Gross (USD)", f"${monthly_salary:,.2f}")
        metric_cols_bottom[0].metric("Weekly Gross (USD)", f"${weekly_salary:,.2f}")
        metric_cols_bottom[1].metric("Source Type", _short_source_type(source_payload["source_id"]))


def _short_source_type(source_id: str) -> str:
    mapping = {
        "manual_prediction": "Prediction",
        "resume_prediction": "Resume",
        "resume_prediction_model2": "Resume",
        "offer_letter": "Offer",
        "manual_entry": "Manual",
    }
    return mapping.get(source_id, "Planning")


def _extract_net_monthly(result: Any, fallback: float) -> float:
    if isinstance(result, dict):
        value = result.get("net_monthly")
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
        value_alt = result.get("net_monthly_a2")
        if isinstance(value_alt, (int, float)) and value_alt > 0:
            return float(value_alt)
    return fallback


def _extract_monthly_savings(result: Any, fallback: float) -> float:
    if isinstance(result, dict):
        value = result.get("savings")
        if isinstance(value, (int, float)):
            return float(value)
    return fallback


def _convert_local_to_usd(amount_local: float, currency_code: str) -> float | None:
    code = (currency_code or "USD").upper()
    if code == "USD":
        return float(amount_local)

    rate_data = get_exchange_rates()
    rates = rate_data.get("rates", {})
    rate = rates.get(code)
    if not rate or rate <= 0:
        return None
    return float(amount_local) / float(rate)


def _default_currency_option(options: list[str], preferred_code: str) -> str:
    preferred = (preferred_code or "USD").upper()
    return next(
        (option for option in options if option.startswith(f"{preferred} — ")),
        options[0],
    )
