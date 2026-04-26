"""
app/tabs/offer_letter_tab.py
-----------------------------
Standalone UI for an Offer Letter Parser workflow.

This file is intentionally not wired into the main app yet. It can be imported
later as a dedicated tab or embedded as a sub-tab inside Resume Analysis.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app.core.offer_letter_parser import (
    build_downstream_payload,
    build_offer_letter_summary,
    extract_offer_letter_fields,
    extract_text_from_offer_pdf,
)
from app.utils.country_utils import resolve_iso2
from app.utils.ctc_utils import render_ctc_adjuster
from app.utils.takehome_utils import render_takehome_adjuster
from app.utils.savings_utils import render_savings_adjuster
from app.utils.loan_utils import render_loan_adjuster
from app.utils.fire_utils import render_fire_calculator
from app.utils.currency_utils import CURRENCY_INFO, get_exchange_rates


def render_offer_letter_tab() -> None:
    st.header(":material/contract: Offer Letter Parser")
    st.caption(
        "Upload an offer letter PDF to extract compensation details and key employment terms. "
        "You can review and edit the extracted fields before using them elsewhere in SalaryScope."
    )
    st.info(
        "The parser works best with text-based offer letters where salary, bonus, and employment terms are clearly written."
    )

    uploaded_pdf = st.file_uploader(
        "Upload offer letter PDF",
        type=["pdf"],
        key="offer_letter_pdf_upload",
        help="Best results come from text-based PDFs with visible salary and employment clauses.",
    )

    if uploaded_pdf is None:
        st.caption(
            "After extraction, you can review the offer details, compare them with SalaryScope's estimate, "
            "and use the compensation in planning tools such as CTC breakdown, take-home, savings, loan, and FIRE."
        )
        return

    parse_col, meta_col = st.columns([1, 2])
    with parse_col:
        parse_clicked = st.button(
            "Extract Offer Details",
            key="offer_letter_extract_btn",
            type="primary",
            width="stretch",
        )
    with meta_col:
        st.caption(
            "Use this when you want to turn an offer letter into structured fields you can review and reuse."
        )

    file_signature = (getattr(uploaded_pdf, "name", ""), getattr(uploaded_pdf, "size", 0))

    if (
        parse_clicked
        or "offer_letter_result" not in st.session_state
        or st.session_state.get("offer_letter_file_signature") != file_signature
    ):
        with st.spinner("Parsing offer letter..."):
            extracted = extract_text_from_offer_pdf(uploaded_pdf)
            parsed = extract_offer_letter_fields(extracted["text"])
            parsed["document_meta"] = {
                "page_count": extracted["page_count"],
                "character_count": extracted["character_count"],
            }
            st.session_state.offer_letter_result = parsed
            st.session_state.offer_letter_file_signature = file_signature

    parsed = st.session_state.get("offer_letter_result")
    if not parsed:
        return

    summary = build_offer_letter_summary(parsed)
    fields = dict(parsed.get("fields", {}))
    evidence = parsed.get("evidence", {})
    meta = parsed.get("document_meta", {})

    st.divider()
    st.subheader("Extraction Snapshot")
    st.caption("Start here for a quick read of what the parser found before reviewing the details below.")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Completeness", f"{parsed.get('completeness_score', 0)}%")
    metric_cols[1].metric("Pages", meta.get("page_count", 0))
    metric_cols[2].metric("Headline Compensation", summary.get("headline_compensation") or "Not found")
    metric_cols[3].metric("Currency", fields.get("currency_code") or "Not found")

    if parsed.get("missing_fields"):
        st.warning(
            "Some important fields were not detected yet: " + ", ".join(parsed["missing_fields"])
        )

    st.divider()
    st.subheader("Review and Edit")
    st.caption("Update any field that looks incomplete or unclear before using the extracted offer elsewhere in the app.")

    profile_col1, profile_col2 = st.columns(2)
    with profile_col1:
        st.markdown("#### Candidate and Role")
        fields["candidate_name"] = st.text_input("Candidate Name", value=fields.get("candidate_name", ""), key="offer_candidate_name")
        fields["company_name"] = st.text_input("Company Name", value=fields.get("company_name", ""), key="offer_company_name")
        fields["job_title"] = st.text_input("Role Title", value=fields.get("job_title", ""), key="offer_job_title")
        fields["level_or_band"] = st.text_input("Level / Band", value=fields.get("level_or_band", ""), key="offer_level_band")
    with profile_col2:
        st.markdown("#### Work Details")
        fields["location"] = st.text_input("Location", value=fields.get("location", ""), key="offer_location")
        default_country_code = fields.get("country_code") or resolve_iso2(fields.get("location")) or ""
        fields["country_code"] = st.text_input(
            "Country Code",
            value=default_country_code,
            key="offer_country_code",
            help="Two-letter country code used by SalaryScope's planning tools, such as IN for India or US for United States.",
        ).upper().strip()
        fields["work_mode"] = st.selectbox(
            "Work Mode",
            ["", "On-site", "Hybrid", "Remote"],
            index=_safe_select_index(["", "On-site", "Hybrid", "Remote"], fields.get("work_mode", "")),
            key="offer_work_mode",
        )
        fields["probation_period"] = st.text_input("Probation Period", value=fields.get("probation_period", ""), key="offer_probation")
        fields["notice_period"] = st.text_input("Notice Period", value=fields.get("notice_period", ""), key="offer_notice")

    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        st.markdown("#### Fixed Compensation")
        fields["currency_code"] = st.text_input("Currency Code", value=fields.get("currency_code", ""), key="offer_currency_code")
        fields["base_salary"] = st.number_input(
            "Base Salary",
            min_value=0.0,
            value=float(fields.get("base_salary") or 0.0),
            step=1000.0,
            key="offer_base_salary",
            help="Use the annual base salary if the letter mentions it separately.",
        ) or None
        fields["total_ctc"] = st.number_input(
            "Total CTC / Total Compensation",
            min_value=0.0,
            value=float(fields.get("total_ctc") or 0.0),
            step=1000.0,
            key="offer_total_ctc",
            help="Use the full annual package if the offer letter shows it.",
        ) or None
        fields["joining_bonus"] = st.number_input(
            "Joining Bonus",
            min_value=0.0,
            value=float(fields.get("joining_bonus") or 0.0),
            step=1000.0,
            key="offer_joining_bonus",
        ) or None
    with comp_col2:
        st.markdown("#### Variable and Equity")
        fields["annual_bonus_fixed"] = st.number_input(
            "Annual Bonus (Fixed Amount)",
            min_value=0.0,
            value=float(fields.get("annual_bonus_fixed") or 0.0),
            step=1000.0,
            key="offer_annual_bonus_fixed",
        ) or None
        fields["annual_bonus_percent"] = st.number_input(
            "Annual Bonus (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(fields.get("annual_bonus_percent") or 0.0),
            step=1.0,
            key="offer_annual_bonus_percent",
        ) or None
        fields["equity_mentioned"] = st.checkbox(
            "Equity / ESOP Mentioned",
            value=bool(fields.get("equity_mentioned")),
            key="offer_equity_mentioned",
        )
        fields["equity_text"] = st.text_area(
            "Equity Clause / Notes",
            value=fields.get("equity_text", ""),
            height=110,
            key="offer_equity_text",
            help="Paste or edit the stock, ESOP, or vesting wording if it appears in the letter.",
        )

    st.session_state.offer_letter_result["fields"] = fields

    st.divider()
    st.subheader("Matched Text")
    st.caption("These snippets show where the parser found the current values in the document.")
    evidence_df = pd.DataFrame(
        [
            {"Field": field, "Evidence": snippet}
            for field, snippet in evidence.items()
            if snippet
        ]
    )
    if evidence_df.empty:
        st.caption("No field-level matches were captured for this document.")
    else:
        st.dataframe(evidence_df, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Structured Output")
    downstream = build_downstream_payload(fields)
    st.caption(
        "This is the cleaned offer summary that can later be passed into comparison and financial planning tools."
    )
    st.json(downstream, expanded=False)

    annual_comp_usd, annual_comp_note = _get_annual_compensation_usd(fields)
    if annual_comp_usd:
        st.divider()
        st.subheader("Financial Planning Tools")
        st.caption(
            "These tools use the extracted offer as a planning starting point. They do not recreate the exact payroll structure written in the letter."
        )
        if annual_comp_note:
            st.info(annual_comp_note)

        location_hint = fields.get("country_code") or fields.get("location") or fields.get("currency_code") or None

        render_ctc_adjuster(
            gross_usd=annual_comp_usd,
            location_hint=location_hint,
            widget_key="offer_letter_ctc",
        )
        takehome_result = render_takehome_adjuster(
            gross_usd=annual_comp_usd,
            location_hint=location_hint,
            widget_key="offer_letter_takehome",
        )
        net_monthly_usd = takehome_result.get("net_monthly", annual_comp_usd / 12)
        savings_result = render_savings_adjuster(
            net_monthly_usd=net_monthly_usd,
            location_hint=location_hint,
            widget_key="offer_letter_savings",
            gross_usd=annual_comp_usd,
        )
        render_loan_adjuster(
            net_monthly_usd=net_monthly_usd,
            location_hint=location_hint,
            widget_key="offer_letter_loan",
            gross_usd=annual_comp_usd,
        )
        render_fire_calculator(
            annual_salary_usd=annual_comp_usd,
            location_hint=location_hint,
            widget_key="offer_letter_fire",
            net_monthly_usd=net_monthly_usd,
            savings_monthly_usd=savings_result.get("savings"),
        )
    else:
        st.divider()
        st.subheader("Financial Planning Tools")
        st.caption(
            "Add a valid annual compensation figure and currency code above to unlock planning tools from this offer."
        )

    with st.expander("View Extracted Offer Text"):
        st.caption("Use this if you want to inspect the raw text that was read from the PDF.")
        st.text_area(
            "Extracted Offer Letter Text",
            parsed.get("raw_text", ""),
            height=320,
            key="offer_letter_raw_text_preview",
        )

    with st.expander("View Parsed JSON"):
        st.caption("This developer-style view is useful for debugging or future integration work.")
        st.code(json.dumps(st.session_state.offer_letter_result, indent=2, default=str), language="json")


def _safe_select_index(options: list[str], value: str) -> int:
    try:
        return options.index(value)
    except ValueError:
        return 0


def _get_annual_compensation_usd(fields: dict) -> tuple[float | None, str]:
    """
    Convert the extracted annual compensation into USD for internal planning tools.

    Priority:
    1. total_ctc
    2. base_salary + annual_bonus_fixed
    3. base_salary
    """
    total_ctc = fields.get("total_ctc")
    base_salary = fields.get("base_salary")
    annual_bonus_fixed = fields.get("annual_bonus_fixed") or 0.0
    currency_code = (fields.get("currency_code") or "").upper().strip()

    if total_ctc and total_ctc > 0:
        annual_local = float(total_ctc)
        source_label = "total compensation"
    elif base_salary and base_salary > 0:
        annual_local = float(base_salary) + float(annual_bonus_fixed)
        source_label = "base salary"
    else:
        return None, ""

    if not currency_code:
        return None, ""

    if currency_code == "USD":
        return annual_local, (
            f"Planning tools are using the extracted annual {source_label} in USD."
        )

    rates = get_exchange_rates().get("rates", {})
    rate = rates.get(currency_code)
    if not rate or rate <= 0:
        return None, ""

    annual_usd = annual_local / rate
    currency_name = CURRENCY_INFO.get(currency_code, (currency_code, ""))[0]
    source_context = "the extracted annual total compensation" if source_label == "total compensation" else "the extracted annual base-plus-bonus amount"
    return annual_usd, (
        f"Planning tools are using {source_context} converted from {currency_name} ({currency_code}) "
        f"to USD at roughly 1 USD = {rate:,.2f} {currency_code}."
    )
