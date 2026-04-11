"""
loan_utils.py -- SalaryScope Loan Affordability Estimator
==========================================================
Estimates the maximum loan a borrower can afford based on their monthly
net income, using country-specific interest rates and lender EMI-cap norms.

Answers the question: "How large a loan can I realistically service?"

IMPORTANT DISCLAIMER
--------------------
Loan eligibility in practice depends on credit score, lender underwriting
policy, collateral, existing obligations, employment type, and income
verification. This module produces indicative estimates only -- not a credit
assessment or financial advice. Consult a bank or financial advisor for
actual loan offers.

Design
------
- Completely standalone: works with or without tax_utils, takehome_utils,
  savings_utils, col_utils, currency_utils, or any other SalaryScope module.
- `compute_loan_affordability(net_monthly_usd, ...)` -- pure-math core using
  the standard reducing-balance EMI formula. No Streamlit dependency.
- `render_loan_adjuster(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_tax_adjuster / render_col_adjuster interface pattern.

Integration
-----------
    from loan_utils import render_loan_adjuster

    render_loan_adjuster(
        net_monthly_usd=net_monthly,     # post-tax monthly income
        location_hint=country,
        widget_key="manual_a1_loan",
        gross_usd=prediction,            # optional: shown as context
    )

    # Best practice: pipe net_monthly from takehome_utils:
    from takehome_utils import render_takehome_adjuster
    from loan_utils import render_loan_adjuster

    th = render_takehome_adjuster(gross_usd=prediction, ...)
    render_loan_adjuster(net_monthly_usd=th.get("net_monthly", prediction/12), ...)

Pure-math usage:
    from loan_utils import compute_loan_affordability

    result = compute_loan_affordability(net_monthly_usd=5000, country="IN")
    print(result["max_loan"], result["affordable_emi"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Built-in country-level default interest rates (annual %, home loan benchmark)
# Sources: central bank policy rates, average retail mortgage rates 2023/24.
# These are illustrative mid-market estimates, not real-time lender quotes.
# ---------------------------------------------------------------------------
_DEFAULT_LOAN_RATE: dict[str, float] = {
    # North America
    "US": 7.0,
    "CA": 6.0,
    "MX": 10.5,
    # Europe
    "GB": 5.5,
    "DE": 4.0,
    "FR": 4.2,
    "CH": 2.5,
    "NL": 4.0,
    "BE": 4.0,
    "AT": 4.2,
    "SE": 4.5,
    "NO": 5.5,
    "DK": 4.5,
    "FI": 4.5,
    "IE": 4.0,
    "ES": 4.5,
    "PT": 4.5,
    "IT": 4.3,
    "GR": 5.0,
    "PL": 7.5,
    "CZ": 5.5,
    "HU": 8.0,
    "RO": 7.5,
    "HR": 5.0,
    "TR": 25.0,  # high due to inflation environment
    "UA": 18.0,
    "RU": 16.0,
    # Middle East
    "AE": 5.0,
    "QA": 5.0,
    "SA": 5.0,
    "KW": 5.5,
    "BH": 5.5,
    "OM": 5.5,
    "IL": 5.5,
    "JO": 8.5,
    # South Asia
    "IN": 8.5,
    "PK": 18.0,
    "BD": 9.0,
    "LK": 14.0,
    "NP": 12.0,
    # East / Southeast Asia
    "JP": 1.5,    # Bank of Japan near-zero rate environment
    "KR": 4.5,
    "CN": 4.2,
    "HK": 5.0,
    "TW": 3.0,
    "SG": 3.5,
    "MY": 4.5,
    "TH": 6.5,
    "VN": 9.5,
    "PH": 7.5,
    "ID": 9.0,
    "MM": 14.0,
    # Oceania
    "AU": 6.5,
    "NZ": 7.0,
    # Africa
    "ZA": 11.5,
    "NG": 22.0,
    "KE": 14.0,
    "GH": 30.0,
    "EG": 22.0,
    "MA": 6.0,
    "ET": 12.0,
    "TZ": 17.0,
    # Latin America
    "BR": 12.0,
    "AR": 50.0,   # high inflation environment
    "CL": 7.0,
    "CO": 13.0,
    "PE": 8.0,
    "BO": 7.0,
    "UY": 9.0,
    "CR": 10.0,
    "DO": 9.0,
    "PA": 6.5,
    "EC": 9.0,
}
_DEFAULT_LOAN_RATE_FALLBACK = 7.0

# Typical EMI-to-net-income cap used by mainstream lenders (fraction).
# Sources: central bank guidelines, lender affordability rules 2023/24.
_EMI_INCOME_CAP: dict[str, float] = {
    "US": 0.36,   # CFPB / conventional guideline: 36% total debt-to-income
    "CA": 0.40,
    "MX": 0.35,
    "GB": 0.35,
    "DE": 0.35,
    "FR": 0.33,   # HCSF cap
    "CH": 0.33,
    "NL": 0.30,
    "BE": 0.33,
    "AT": 0.35,
    "SE": 0.35,
    "NO": 0.35,
    "DK": 0.35,
    "FI": 0.35,
    "IE": 0.35,
    "ES": 0.35,
    "PT": 0.35,
    "IT": 0.35,
    "GR": 0.35,
    "PL": 0.40,
    "CZ": 0.45,
    "HU": 0.50,
    "RO": 0.40,
    "TR": 0.40,
    "AE": 0.50,   # UAE Central Bank: 50% of salary
    "QA": 0.50,
    "SA": 0.33,
    "KW": 0.40,
    "BH": 0.40,
    "OM": 0.40,
    "IL": 0.40,
    "IN": 0.40,   # RBI / lender practice: ~40% FOIR
    "PK": 0.40,
    "BD": 0.40,
    "LK": 0.40,
    "NP": 0.40,
    "JP": 0.35,
    "KR": 0.40,   # DSR cap from FSC
    "CN": 0.50,
    "HK": 0.40,
    "SG": 0.30,   # MAS TDSR: 55% total debt but conservative home estimate
    "TW": 0.40,
    "MY": 0.40,
    "TH": 0.40,
    "VN": 0.40,
    "PH": 0.35,
    "ID": 0.35,
    "AU": 0.30,   # APRA stress-test based -- conservative
    "NZ": 0.35,
    "ZA": 0.40,
    "NG": 0.33,
    "KE": 0.35,
    "BR": 0.30,
    "MX": 0.35,
    "AR": 0.30,
    "CL": 0.40,
}
_EMI_INCOME_CAP_FALLBACK = 0.35

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_key(location_hint: Optional[str], table: dict) -> Optional[str]:
    if not location_hint:
        return None
    key = str(location_hint).strip().upper()
    if key in table:
        return key
    try:
        from country_utils import resolve_iso2
        resolved = resolve_iso2(location_hint)
        if resolved and resolved in table:
            return resolved
    except ImportError:
        pass
    return None


def _country_name(location_hint: Optional[str]) -> str:
    if not location_hint:
        return "Unknown"
    try:
        from country_utils import get_country_name
        return get_country_name(location_hint) or str(location_hint)
    except ImportError:
        return str(location_hint)


def _fmt(v: float) -> str:
    return f"${v:,.0f}"


def _pct(r: float) -> str:
    return f"{r * 100:.1f}%"


def _get_currency_meta(location_hint: Optional[str]) -> tuple[str, str, float]:
    """Return (currency_code, symbol, fx_rate). Falls back to USD."""
    try:
        from currency_utils import guess_currency, get_converted_amount, CURRENCY_INFO
        code = guess_currency(location_hint) or "USD"
        if code == "USD":
            return "USD", "$", 1.0
        _, rate = get_converted_amount(1.0, code)
        symbol = CURRENCY_INFO.get(code, (code, code))[1]
        return code, symbol, rate
    except Exception:
        return "USD", "$", 1.0


def _fmt_local(v: float, symbol: str, code: str) -> str:
    """Format in local currency; integer for high-unit currencies."""
    if code in ("JPY", "KRW", "IDR", "VND", "CLP", "UGX", "TZS", "PYG", "LAK", "MNT", "MMK", "KHR", "IRR"):
        return f"{symbol}{v:,.0f}"
    return f"{symbol}{v:,.2f}"


def _card(value_str: str, label: str, color: str = "#3E7DE0") -> str:
    return (
        "<div style='"
        "background:linear-gradient(135deg,#1A2535 0%,#1B2230 100%);"
        f"border:1px solid #2D3A50;border-left:5px solid {color};"
        "border-radius:10px;padding:16px 20px;text-align:center;margin:6px 0;'>"
        "<div style='color:#9CA6B5;font-size:11px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:4px;'>{label}</div>"
        f"<div style='color:{color};font-size:28px;font-weight:700;"
        f"letter-spacing:-0.5px;'>{value_str}</div>"
        "</div>"
    )


def _info_row(label: str, value: str) -> str:
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:5px 0;border-bottom:1px solid #283142;'>"
        f"<span style='color:#9CA6B5;font-size:13px;'>{label}</span>"
        f"<span style='color:#E6EAF0;font-size:13px;'>{value}</span>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit, reusable anywhere
# ---------------------------------------------------------------------------

def compute_loan_affordability(
    net_monthly_usd: float,
    loan_years: int = 20,
    annual_interest_rate_pct: Optional[float] = None,
    country: Optional[str] = None,
    emi_cap_fraction: Optional[float] = None,
    existing_emi_usd: float = 0.0,
) -> dict:
    """
    Estimate the maximum loan principal a borrower can afford.

    Uses the standard reducing-balance EMI formula:
        P = EMI * [(1+r)^n - 1] / [r * (1+r)^n]
    where r = monthly interest rate and n = total number of payments.

    Parameters
    ----------
    net_monthly_usd          : Monthly net (post-tax) income in USD.
    loan_years               : Loan tenure in years (default 20).
    annual_interest_rate_pct : Annual interest rate in %. None = country default.
    country                  : ISO-2 code or country name for rate defaults.
    emi_cap_fraction         : Max EMI as fraction of net income. None = country default.
    existing_emi_usd         : Any existing monthly EMI obligations in USD.
                               Reduces the affordable EMI by this amount.

    Returns
    -------
    dict with keys:
        max_loan              -- maximum loan principal in USD
        max_emi               -- maximum allowable EMI (USD / month)
        affordable_emi        -- max_emi minus existing obligations
        existing_emi_usd      -- passed-in existing EMI
        loan_years            -- tenure used
        n_payments            -- total number of monthly payments
        interest_rate_pct     -- annual interest rate used
        emi_cap_fraction_used -- EMI cap fraction applied
        monthly_rate          -- monthly interest rate (decimal)
        total_repayment       -- affordable_emi * n_payments
        total_interest        -- total_repayment - max_loan
        interest_cost_ratio   -- total_interest / max_loan (fraction)
    """
    key = _resolve_key(country, _DEFAULT_LOAN_RATE)

    rate_pct = float(annual_interest_rate_pct) if annual_interest_rate_pct is not None \
        else _DEFAULT_LOAN_RATE.get(key or "", _DEFAULT_LOAN_RATE_FALLBACK)

    cap = float(emi_cap_fraction) if emi_cap_fraction is not None \
        else _EMI_INCOME_CAP.get(key or "", _EMI_INCOME_CAP_FALLBACK)

    max_emi = net_monthly_usd * cap
    affordable_emi = max(0.0, max_emi - float(existing_emi_usd))

    monthly_rate = rate_pct / 100.0 / 12.0
    n = int(loan_years) * 12

    if monthly_rate > 0 and affordable_emi > 0:
        factor = ((1 + monthly_rate) ** n - 1) / (monthly_rate * (1 + monthly_rate) ** n)
        max_loan = affordable_emi * factor
    elif affordable_emi > 0:
        # Zero interest edge case
        max_loan = affordable_emi * n
    else:
        max_loan = 0.0

    total_repayment = affordable_emi * n
    total_interest = max(0.0, total_repayment - max_loan)
    interest_cost_ratio = total_interest / max_loan if max_loan > 0 else 0.0

    return {
        "max_loan": max_loan,
        "max_emi": max_emi,
        "affordable_emi": affordable_emi,
        "existing_emi_usd": float(existing_emi_usd),
        "loan_years": int(loan_years),
        "n_payments": n,
        "interest_rate_pct": rate_pct,
        "emi_cap_fraction_used": cap,
        "monthly_rate": monthly_rate,
        "total_repayment": total_repayment,
        "total_interest": total_interest,
        "interest_cost_ratio": interest_cost_ratio,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_loan_adjuster(
    net_monthly_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "loan",
    gross_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Loan Affordability Estimator panel.

    Parameters
    ----------
    net_monthly_usd : Monthly net (post-tax) income in USD.
                      Pipe from takehome_utils.render_takehome_adjuster()
                      for best results.
    location_hint   : ISO-2 country code or country name.
    widget_key      : Unique key prefix per call-site (e.g. "manual_a1_loan").
                      Must differ for every place this is called.
    gross_usd       : Optional annual gross salary -- shown as context only.

    Returns
    -------
    dict -- the compute_loan_affordability result.
    Returns an empty dict if widget is hidden or income is invalid.

    Usage
    -----
        from loan_utils import render_loan_adjuster
        render_loan_adjuster(net_monthly_usd=net_monthly, location_hint=country,
                             widget_key="manual_a1_loan", gross_usd=prediction)
    """
    if not net_monthly_usd or net_monthly_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/home: Loan Affordability Estimator",
        key=toggle_key,
        value=False,
        help="Estimate the maximum loan you can service based on your net monthly income.",
    )
    if not show:
        return {}

    with st.expander(":material/home: Loan Affordability Estimator", expanded=True):
        st.caption(
            ":material/info: Estimates the maximum loan principal you can service "
            "based on your net monthly income, using country-specific interest rate "
            "and lender EMI-cap norms. All parameters are overridable. "
            "This is not a credit assessment or financial advice."
        )

        key = _resolve_key(location_hint, _DEFAULT_LOAN_RATE)
        d_rate = _DEFAULT_LOAN_RATE.get(key or "", _DEFAULT_LOAN_RATE_FALLBACK)
        d_cap = _EMI_INCOME_CAP.get(key or "", _EMI_INCOME_CAP_FALLBACK)

        if location_hint and location_hint not in ("", "Other"):
            st.info(
                f"**Country:** {_country_name(location_hint)}\n\n"
                f"Default interest rate: **{d_rate:.1f}% p.a.**  |  "
                f"Lender EMI cap: **{_pct(d_cap)}** of net income  |  "
                f"Monthly net income: **{_fmt(net_monthly_usd)}**"
                + (f"  |  Annual gross: **{_fmt(gross_usd)}**" if gross_usd else "")
            )
        else:
            st.info(
                f"Monthly net income: **{_fmt(net_monthly_usd)}**. "
                "No country detected -- using generic defaults. "
                "Override below for more accurate results."
            )

        use_custom = st.toggle(
            "Override loan parameters",
            key=f"{widget_key}_custom",
            value=False,
            help="Set your own interest rate, tenure, EMI cap, and existing obligations.",
        )

        loan_years = 20
        rate_pct = d_rate
        cap = d_cap
        existing_emi = 0.0

        if use_custom:
            c1, c2 = st.columns(2)
            with c1:
                rate_pct = st.slider(
                    "Annual Interest Rate (%)",
                    min_value=1.0, max_value=35.0,
                    value=float(round(d_rate, 2)),
                    step=0.25,
                    key=f"{widget_key}_rate",
                    help=(
                        "Annual interest rate offered by the lender. "
                        "Default is the country-level benchmark -- "
                        "actual offers vary by credit profile."
                    ),
                )
                loan_years = st.slider(
                    "Loan Tenure (years)",
                    min_value=1, max_value=30,
                    value=20,
                    step=1,
                    key=f"{widget_key}_years",
                    help="Longer tenure reduces monthly EMI but increases total interest paid.",
                )
            with c2:
                cap = st.slider(
                    "Max EMI as % of Net Income",
                    min_value=10, max_value=70,
                    value=int(d_cap * 100),
                    step=1,
                    key=f"{widget_key}_cap",
                    help=(
                        "Most lenders cap the EMI at 30-50% of net monthly income. "
                        "Setting this higher increases loan eligibility "
                        "but may strain your budget."
                    ),
                ) / 100.0
                existing_emi = st.number_input(
                    "Existing monthly EMI obligations (USD)",
                    min_value=0.0,
                    max_value=float(net_monthly_usd * 0.8),
                    value=0.0,
                    step=10.0,
                    key=f"{widget_key}_existing",
                    help=(
                        "Sum of all current EMI payments (car loan, personal loan, etc.). "
                        "Lenders subtract these from the allowable EMI."
                    ),
                )

        result = compute_loan_affordability(
            net_monthly_usd,
            loan_years=loan_years,
            annual_interest_rate_pct=rate_pct,
            country=location_hint,
            emi_cap_fraction=cap,
            existing_emi_usd=existing_emi,
        )

        # --- Currency resolution ---
        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        st.divider()

        # Eligibility banner
        if result["max_loan"] <= 0:
            card_color = "#EF4444"
        elif result["max_loan"] < net_monthly_usd * 12:
            card_color = "#F59E0B"
        else:
            card_color = "#3E7DE0"

        loan_card_label = (
            f"ESTIMATED MAXIMUM LOAN AMOUNT ({cur_code}  ≈  {_fmt(result['max_loan'])} USD)"
            if use_local else "ESTIMATED MAXIMUM LOAN AMOUNT (USD)"
        )
        st.markdown(
            _card(_loc(result["max_loan"]), loan_card_label, color=card_color),
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            f"Max Allowable EMI ({cur_code}/mo)" if use_local else "Max Allowable EMI (USD/mo)",
            _loc(result["max_emi"]),
            delta=_fmt(result["max_emi"]) if use_local else None, delta_color="off",
        )
        c2.metric(
            "Affordable EMI (after existing)",
            _loc(result["affordable_emi"]),
            delta=_fmt(result["affordable_emi"]) if use_local else None, delta_color="off",
        )
        c3.metric("Loan Tenure", f"{result['loan_years']} years")

        c4, c5, c6 = st.columns(3)
        c4.metric("Interest Rate", f"{result['interest_rate_pct']:.2f}% p.a.")
        c5.metric(
            f"Total Repayment ({cur_code})" if use_local else "Total Repayment (est.)",
            _loc(result["total_repayment"]),
            delta=_fmt(result["total_repayment"]) if use_local else None, delta_color="off",
        )
        c6.metric(
            f"Total Interest ({cur_code})" if use_local else "Total Interest Paid (est.)",
            _loc(result["total_interest"]),
            delta=_fmt(result["total_interest"]) if use_local else None, delta_color="off",
        )

        # Loan summary table
        st.divider()
        st.markdown("**Loan Summary**")
        rows = [
            ("Monthly Net Income", _loc(net_monthly_usd) + (f"  ≈ {_fmt(net_monthly_usd)}" if use_local else "")),
            ("Lender EMI Cap", f"{_pct(result['emi_cap_fraction_used'])} of net income"),
            ("Max Allowable EMI", _loc(result["max_emi"]) + (f"  ≈ {_fmt(result['max_emi'])}" if use_local else "")),
            ("Less: Existing EMI", _loc(result["existing_emi_usd"]) + (f"  ≈ {_fmt(result['existing_emi_usd'])}" if use_local else "")),
            ("Affordable EMI", _loc(result["affordable_emi"]) + (f"  ≈ {_fmt(result['affordable_emi'])}" if use_local else "")),
            ("Interest Rate", f"{result['interest_rate_pct']:.2f}% p.a."),
            ("Tenure", f"{result['loan_years']} years ({result['n_payments']} payments)"),
            ("Maximum Loan Principal", _loc(result["max_loan"]) + (f"  ≈ {_fmt(result['max_loan'])}" if use_local else "")),
            ("Total Interest Cost", _loc(result["total_interest"]) + (f"  ≈ {_fmt(result['total_interest'])}" if use_local else "")),
            ("Interest as % of Principal", f"{result['interest_cost_ratio'] * 100:.1f}%"),
        ]
        for label, value in rows:
            st.markdown(_info_row(label, value), unsafe_allow_html=True)

        st.divider()

        # Eligibility message
        if result["max_loan"] <= 0:
            st.error(
                ":material/error: Existing EMI obligations consume the full EMI cap. "
                "No additional loan capacity under these parameters. "
                "Consider increasing tenure, reducing existing debt, or increasing income."
            )
        elif result["max_loan"] < net_monthly_usd * 12:
            st.warning(
                ":material/warning: Loan capacity is below one year of gross income. "
                "Extending the tenure or reducing existing obligations may help. "
                "This may reflect a high interest rate or low income-to-EMI ratio."
            )
        else:
            months_payoff = result["n_payments"]
            loan_str = f"{_loc(result['max_loan'])} ({_fmt(result['max_loan'])})" if use_local else _fmt(result['max_loan'])
            emi_str = f"{_loc(result['affordable_emi'])} ({_fmt(result['affordable_emi'])})" if use_local else _fmt(result['affordable_emi'])
            st.success(
                f":material/check_circle: Based on these parameters, you can afford a loan "
                f"of approximately {loan_str} with an EMI of "
                f"{emi_str}/month over "
                f"{result['loan_years']} years ({months_payoff} payments)."
            )

        st.caption(
            "Uses the standard reducing-balance EMI formula. "
            "Actual loan eligibility depends on credit score, lender policy, "
            "collateral, income verification, and existing liabilities. "
            "Interest rate shown is a country-level benchmark, not a lender quote."
        )

    return result