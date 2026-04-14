"""
emergency_fund_utils.py -- SalaryScope Emergency Fund Planner
=============================================================
Estimates how large an emergency fund a person needs and how long it will
take to build one, based on country-adjusted monthly expense benchmarks
and customisable savings contributions.

Answers the question: "How much do I need as a financial safety net,
and how quickly can I build it?"

IMPORTANT DISCLAIMER
--------------------
Emergency fund recommendations are general guidelines based on widely accepted
personal finance principles (3-6 months of expenses). Individual circumstances,
employment stability, dependants, existing insurance, and risk tolerance all
affect the right target. This is not financial advice.

Design
------
- Completely standalone: works with or without savings_utils, loan_utils,
  budget_utils, investment_utils, or any other SalaryScope module.
- `compute_emergency_fund(net_monthly_usd, ...)` -- pure-math core.
  No Streamlit dependency. Safe to call from any tab or utility.
- `render_emergency_fund_planner(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_savings_adjuster / render_loan_adjuster interface pattern.

Integration
-----------
    from emergency_fund_utils import render_emergency_fund_planner

    render_emergency_fund_planner(
        net_monthly_usd=net_monthly,
        location_hint=country,
        widget_key="manual_a1_ef",
        gross_usd=prediction,
    )

    # Best practice: pipe net_monthly from takehome_utils:
    from takehome_utils import render_takehome_adjuster
    from emergency_fund_utils import render_emergency_fund_planner

    th = render_takehome_adjuster(gross_usd=prediction, ...)
    render_emergency_fund_planner(
        net_monthly_usd=th.get("net_monthly", prediction / 12), ...
    )

Pure-math usage:
    from emergency_fund_utils import compute_emergency_fund

    result = compute_emergency_fund(net_monthly_usd=5000, country="IN")
    print(result["target_3mo"], result["months_to_3mo"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Country-level job market stability factor.
# Lower value = less stable job market = higher recommended emergency cushion.
# Scale: 1.0 = very stable, 0.5 = high unemployment/volatility.
# Sources: World Bank unemployment data, IMF labour market reports 2023/24.
# Used to scale recommended fund months (stable = 3 mo, volatile = 6+ mo).
# ---------------------------------------------------------------------------
_JOB_STABILITY: dict[str, float] = {
    # North America
    "US": 0.80,
    "CA": 0.82,
    "MX": 0.60,
    # Europe
    "GB": 0.82,
    "DE": 0.90,
    "FR": 0.75,
    "CH": 0.92,
    "NL": 0.88,
    "BE": 0.80,
    "AT": 0.88,
    "SE": 0.85,
    "NO": 0.92,
    "DK": 0.90,
    "FI": 0.85,
    "IE": 0.82,
    "ES": 0.65,
    "PT": 0.68,
    "IT": 0.68,
    "GR": 0.55,
    "PL": 0.75,
    "CZ": 0.82,
    "HU": 0.75,
    "RO": 0.65,
    "TR": 0.60,
    "UA": 0.50,
    "RU": 0.62,
    # Middle East
    "AE": 0.75,
    "QA": 0.80,
    "SA": 0.70,
    "KW": 0.78,
    "BH": 0.72,
    "OM": 0.70,
    "IL": 0.80,
    "JO": 0.58,
    # South Asia
    "IN": 0.62,
    "PK": 0.52,
    "BD": 0.52,
    "LK": 0.55,
    "NP": 0.50,
    # East / Southeast Asia
    "JP": 0.90,
    "KR": 0.85,
    "CN": 0.72,
    "HK": 0.82,
    "TW": 0.85,
    "SG": 0.88,
    "MY": 0.72,
    "TH": 0.68,
    "VN": 0.65,
    "PH": 0.58,
    "ID": 0.60,
    "MM": 0.52,
    # Oceania
    "AU": 0.85,
    "NZ": 0.85,
    # Africa
    "ZA": 0.45,
    "NG": 0.45,
    "KE": 0.50,
    "GH": 0.50,
    "EG": 0.52,
    "MA": 0.55,
    "ET": 0.48,
    "TZ": 0.48,
    # Latin America
    "BR": 0.62,
    "AR": 0.52,
    "CL": 0.70,
    "CO": 0.58,
    "PE": 0.60,
    "BO": 0.55,
    "UY": 0.68,
    "CR": 0.65,
    "DO": 0.58,
    "PA": 0.65,
    "EC": 0.58,
}
_JOB_STABILITY_FALLBACK = 0.70

# Recommended fund months derived from stability factor:
# stability >= 0.85 -> 3 months; >= 0.70 -> 4; >= 0.55 -> 5; else 6
_STABILITY_MONTH_MAP = [
    (0.85, 3),
    (0.70, 4),
    (0.55, 5),
    (0.00, 6),
]

# Country-level expense ratios (reused from savings_utils definition)
_EXPENSE_RATIO: dict[str, float] = {
    "US": 0.70, "CA": 0.68, "MX": 0.68,
    "GB": 0.68, "DE": 0.62, "FR": 0.65, "CH": 0.65,
    "NL": 0.62, "BE": 0.63, "AT": 0.62, "SE": 0.60,
    "NO": 0.58, "DK": 0.60, "FI": 0.62, "IE": 0.68,
    "ES": 0.65, "PT": 0.63, "IT": 0.66, "GR": 0.67,
    "PL": 0.62, "CZ": 0.60, "HU": 0.62, "RO": 0.63,
    "HR": 0.64, "TR": 0.70, "UA": 0.66, "RU": 0.65,
    "AE": 0.60, "QA": 0.58, "SA": 0.60, "KW": 0.58,
    "BH": 0.60, "OM": 0.62, "IL": 0.70, "JO": 0.68,
    "IN": 0.55, "PK": 0.65, "BD": 0.60, "LK": 0.60, "NP": 0.58,
    "JP": 0.70, "KR": 0.62, "CN": 0.60, "HK": 0.72,
    "TW": 0.65, "SG": 0.65, "MY": 0.62, "TH": 0.63,
    "VN": 0.60, "PH": 0.65, "ID": 0.63, "MM": 0.66,
    "AU": 0.67, "NZ": 0.68,
    "ZA": 0.68, "NG": 0.72, "KE": 0.68, "GH": 0.70,
    "EG": 0.65, "MA": 0.66, "ET": 0.68, "TZ": 0.67,
    "BR": 0.72, "AR": 0.70, "CL": 0.65, "CO": 0.67,
    "PE": 0.65, "BO": 0.65, "UY": 0.65, "PY": 0.66,
    "VE": 0.72, "EC": 0.66, "CR": 0.65, "DO": 0.66,
    "PA": 0.64, "GT": 0.67,
}
_EXPENSE_RATIO_FALLBACK = 0.65

# Default monthly contribution fraction for savings toward the emergency fund
_DEFAULT_CONTRIBUTION_RATIO = 0.10


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
        from app.utils.country_utils import resolve_iso2
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
        from app.utils.country_utils import get_country_name
        return get_country_name(location_hint) or str(location_hint)
    except ImportError:
        return str(location_hint)


def _get_currency_meta(location_hint: Optional[str]) -> tuple:
    """Return (currency_code, symbol, fx_rate). Falls back to USD."""
    try:
        from app.utils.currency_utils import guess_currency, get_converted_amount, CURRENCY_INFO
        code = guess_currency(location_hint) or "USD"
        if code == "USD":
            return "USD", "$", 1.0
        _, rate = get_converted_amount(1.0, code)
        symbol = CURRENCY_INFO.get(code, (code, code))[1]
        return code, symbol, rate
    except Exception:
        return "USD", "$", 1.0


def _fmt(v: float) -> str:
    return f"${v:,.0f}"


def _pct(r: float) -> str:
    return f"{r * 100:.1f}%"


def _fmt_local(v: float, symbol: str, code: str) -> str:
    if code in (
        "JPY", "KRW", "IDR", "VND", "CLP", "UGX", "TZS",
        "PYG", "LAK", "MNT", "MMK", "KHR", "IRR",
    ):
        return f"{symbol}{v:,.0f}"
    return f"{symbol}{v:,.2f}"


def _card(value_str: str, label: str, color: str = "#22C55E") -> str:
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
        f"padding:6px 0;border-bottom:1px solid #2D3A50;font-size:13px;'>"
        f"<span style='color:#9CA6B5;'>{label}</span>"
        f"<span style='color:#E6EAF0;font-weight:600;'>{value}</span>"
        f"</div>"
    )


def _recommended_months(stability: float) -> int:
    for threshold, months in _STABILITY_MONTH_MAP:
        if stability >= threshold:
            return months
    return 6


def _status_box(color: str, bg: str, message: str) -> str:
    return (
        f"<div style='background:{bg};border-left:4px solid {color};"
        f"border-radius:6px;padding:12px 16px;margin:8px 0;font-size:13px;color:#C8D6E8;'>"
        f"{message}</div>"
    )


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit dependency
# ---------------------------------------------------------------------------

def compute_emergency_fund(
    net_monthly_usd: float,
    country: Optional[str] = None,
    target_months: Optional[int] = None,
    monthly_contribution_usd: Optional[float] = None,
    existing_fund_usd: float = 0.0,
) -> dict:
    """
    Estimate emergency fund target and time to reach it.

    Parameters
    ----------
    net_monthly_usd         : Monthly net (post-tax) income in USD.
    country                 : ISO-2 code or country name for defaults.
    target_months           : Override recommended fund months (default auto
                              from job stability score for the country).
    monthly_contribution_usd: Override monthly amount set aside for emergency
                              fund. Defaults to 10% of net monthly income.
    existing_fund_usd       : Existing emergency savings already accumulated.

    Returns
    -------
    dict with keys:
        net_monthly             -- input net monthly income
        monthly_expenses_est    -- estimated monthly expenses in USD
        recommended_months      -- country-advised fund months
        target_months_used      -- actual months used (may be overridden)
        target_3mo              -- 3-month expense fund target (USD)
        target_6mo              -- 6-month expense fund target (USD)
        target_used             -- fund target based on target_months_used
        existing_fund           -- input existing fund amount
        shortfall               -- remaining amount needed (may be 0)
        monthly_contribution    -- monthly savings toward fund
        months_to_target        -- full months to reach target from now
        job_stability_score     -- 0-1 score used to derive recommendation
        pct_funded              -- fraction of target already funded (0-1)
    """
    key_exp = _resolve_key(country, _EXPENSE_RATIO)
    key_stab = _resolve_key(country, _JOB_STABILITY)

    expense_ratio = _EXPENSE_RATIO.get(key_exp or "", _EXPENSE_RATIO_FALLBACK)
    stability = _JOB_STABILITY.get(key_stab or "", _JOB_STABILITY_FALLBACK)

    monthly_expenses = net_monthly_usd * expense_ratio

    rec_months = _recommended_months(stability)
    target_months_used = int(target_months) if target_months is not None else rec_months

    target_3mo = monthly_expenses * 3
    target_6mo = monthly_expenses * 6
    target_used = monthly_expenses * target_months_used

    if monthly_contribution_usd is not None:
        contribution = max(0.0, float(monthly_contribution_usd))
    else:
        contribution = net_monthly_usd * _DEFAULT_CONTRIBUTION_RATIO

    existing = max(0.0, float(existing_fund_usd))
    shortfall = max(0.0, target_used - existing)

    if contribution > 0:
        months_to_target = shortfall / contribution
    else:
        months_to_target = float("inf")

    pct_funded = min(existing / target_used, 1.0) if target_used > 0 else 0.0

    return {
        "net_monthly": net_monthly_usd,
        "monthly_expenses_est": monthly_expenses,
        "recommended_months": rec_months,
        "target_months_used": target_months_used,
        "target_3mo": target_3mo,
        "target_6mo": target_6mo,
        "target_used": target_used,
        "existing_fund": existing,
        "shortfall": shortfall,
        "monthly_contribution": contribution,
        "months_to_target": months_to_target,
        "job_stability_score": stability,
        "pct_funded": pct_funded,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_emergency_fund_planner(
    net_monthly_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "emergency_fund",
    gross_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Emergency Fund Planner panel.

    Parameters
    ----------
    net_monthly_usd : Monthly net (post-tax) income in USD.
                      Pipe in from takehome_utils.render_takehome_adjuster()
                      for best results, or compute from gross as a fallback.
    location_hint   : ISO-2 country code or country name.
    widget_key      : Unique key prefix per call-site (e.g. "manual_a1_ef").
                      Must differ for every place this is called.
    gross_usd       : Optional gross annual salary -- shown as context only.

    Returns
    -------
    dict -- the compute_emergency_fund result.
    Returns an empty dict if widget is hidden or income is invalid.
    """
    if not net_monthly_usd or net_monthly_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/shield: Emergency Fund Planner",
        key=toggle_key,
        value=False,
        help="Calculate your emergency fund target and how long it will take to build it.",
    )
    if not show:
        return {}

    with st.expander(":material/shield: Emergency Fund Planner", expanded=True):
        st.caption(
            ":material/info: Recommends an emergency fund target based on your country's "
            "job market stability and typical expense levels. General guideline: "
            "3-6 months of living expenses. This is not financial advice."
        )

        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        key_stab = _resolve_key(location_hint, _JOB_STABILITY)
        d_stability = _JOB_STABILITY.get(key_stab or "", _JOB_STABILITY_FALLBACK)
        d_rec_months = _recommended_months(d_stability)

        if location_hint and location_hint not in ("", "Other"):
            gross_part = (
                f" &nbsp;&middot;&nbsp; "
                f"<span style='color:#9CA6B5;'>Annual gross:</span>"
                f" <b>{_loc(gross_usd)}</b>"
                if gross_usd else ""
            )
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #34D399;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#C8D6E8;'>"
                f"<span style='font-weight:700;color:#E6EAF0;'>Country:</span> "
                f"{_country_name(location_hint)}<br>"
                f"<span style='color:#9CA6B5;'>Job stability score:</span>"
                f" <b>{d_stability:.2f} / 1.00</b>"
                f" &nbsp;&middot;&nbsp; "
                f"<span style='color:#9CA6B5;'>Recommended fund:</span>"
                f" <b>{d_rec_months} months of expenses</b>"
                f" &nbsp;&middot;&nbsp; "
                f"<span style='color:#9CA6B5;'>Monthly net income:</span>"
                f" <b>{_loc(net_monthly_usd)}</b>"
                f"{gross_part}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #6B7585;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#9CA6B5;'>"
                f"Monthly net income: <b style='color:#C8D6E8;'>{_loc(net_monthly_usd)}</b>. "
                "No country detected -- using generic 4-month recommendation. "
                "Override below for more accurate results."
                "</div>",
                unsafe_allow_html=True,
            )

        use_custom = st.toggle(
            "Override fund parameters",
            key=f"{widget_key}_custom",
            value=False,
            help="Set your own fund target, existing savings, and monthly contribution.",
        )

        custom_target_months = None
        custom_contribution = None
        existing_fund = 0.0

        if use_custom:
            c1, c2 = st.columns(2)
            with c1:
                custom_target_months = st.slider(
                    "Fund Target (months of expenses)",
                    min_value=1, max_value=12,
                    value=d_rec_months,
                    step=1,
                    key=f"{widget_key}_months",
                    help=(
                        "How many months of essential expenses your emergency fund should cover. "
                        "Standard recommendation is 3-6 months depending on job stability."
                    ),
                )
                custom_contribution = st.number_input(
                    "Monthly contribution toward fund (USD)",
                    min_value=0.0,
                    max_value=float(net_monthly_usd),
                    value=float(round(net_monthly_usd * _DEFAULT_CONTRIBUTION_RATIO, 0)),
                    step=10.0,
                    key=f"{widget_key}_contrib",
                    help=(
                        "Amount you set aside each month specifically for your emergency fund. "
                        "Once the target is reached, redirect this to investments or savings."
                    ),
                )
            with c2:
                existing_fund = st.number_input(
                    "Existing emergency savings (USD)",
                    min_value=0.0,
                    max_value=float(net_monthly_usd * 24),
                    value=0.0,
                    step=100.0,
                    key=f"{widget_key}_existing",
                    help=(
                        "Amount you already have saved as an emergency fund. "
                        "This reduces the remaining target and shortens the time to reach it."
                    ),
                )

        result = compute_emergency_fund(
            net_monthly_usd,
            country=location_hint,
            target_months=custom_target_months,
            monthly_contribution_usd=custom_contribution,
            existing_fund_usd=existing_fund,
        )

        st.divider()

        label_suffix = f"({cur_code})" if use_local else "(USD)"

        # Target card
        if result["pct_funded"] >= 1.0:
            target_color = "#22C55E"
        elif result["pct_funded"] >= 0.50:
            target_color = "#F59E0B"
        else:
            target_color = "#3E7DE0"

        st.markdown(
            _card(
                _loc(result["target_used"]),
                f"EMERGENCY FUND TARGET ({result['target_months_used']} MONTHS) {label_suffix}",
                color=target_color,
            ),
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        c1.metric(
            f"3-Month Target {label_suffix}",
            _loc(result["target_3mo"]),
        )
        c2.metric(
            f"6-Month Target {label_suffix}",
            _loc(result["target_6mo"]),
        )
        c3.metric(
            "Funded So Far",
            f"{result['pct_funded'] * 100:.1f}%",
            delta=_loc(result["existing_fund"]) if result["existing_fund"] > 0 else None,
            delta_color="normal",
        )

        st.divider()

        # Progress bar (HTML)
        pct_filled = min(int(result["pct_funded"] * 100), 100)
        bar_color = target_color
        st.markdown(
            f"<div style='margin:8px 0;'>"
            f"<div style='font-size:13px;color:#9CA6B5;margin-bottom:4px;'>"
            f"Fund progress: {pct_filled}% of {result['target_months_used']}-month target"
            f"</div>"
            f"<div style='background:#2D3A50;border-radius:6px;height:14px;width:100%;'>"
            f"<div style='background:{bar_color};width:{pct_filled}%;height:14px;"
            f"border-radius:6px;'></div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown("**Fund Build Plan**")

        for row_label, row_value in [
            ("Monthly Net Income", _loc(result["net_monthly"])),
            ("Est. Monthly Expenses", _loc(result["monthly_expenses_est"])),
            ("Fund Target", _loc(result["target_used"])),
            ("Existing Fund", _loc(result["existing_fund"])),
            ("Remaining Shortfall", _loc(result["shortfall"])),
            ("Monthly Contribution", _loc(result["monthly_contribution"])),
            (
                "Est. Months to Target",
                (
                    f"{result['months_to_target']:.1f} months"
                    if result["months_to_target"] != float("inf")
                    else "N/A (contribution is zero)"
                ),
            ),
            (
                "Est. Years to Target",
                (
                    f"{result['months_to_target'] / 12:.1f} years"
                    if result["months_to_target"] != float("inf")
                    else "N/A"
                ),
            ),
            ("Job Stability Score", f"{result['job_stability_score']:.2f} / 1.00"),
            ("Recommended Fund Length", f"{result['recommended_months']} months"),
        ]:
            st.markdown(_info_row(row_label, row_value), unsafe_allow_html=True)

        st.divider()

        if result["pct_funded"] >= 1.0:
            st.markdown(
                _status_box(
                    color="#22C55E",
                    bg="#0F2A1A",
                    message=(
                        "Emergency fund target is fully funded. "
                        "You have a strong financial safety net in place. "
                        "Consider redirecting your monthly contribution toward investments or savings."
                    ),
                ),
                unsafe_allow_html=True,
            )
        elif result["months_to_target"] != float("inf"):
            yr = result["months_to_target"] / 12
            yr_str = (
                f"{result['months_to_target']:.0f} months"
                if yr < 1
                else f"{yr:.1f} years ({result['months_to_target']:.0f} months)"
            )
            st.markdown(
                _status_box(
                    color="#3E7DE0",
                    bg="#0F1E2D",
                    message=(
                        f"At a monthly contribution of <b>{_loc(result['monthly_contribution'])}</b>, "
                        f"you will reach your {result['target_months_used']}-month emergency fund "
                        f"target in approximately <b>{yr_str}</b>."
                    ),
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                _status_box(
                    color="#EF4444",
                    bg="#2A1A1A",
                    message=(
                        "Monthly contribution is set to zero. "
                        "Set a contribution amount above to calculate the time to reach your target."
                    ),
                ),
                unsafe_allow_html=True,
            )

        st.caption(
            "Job stability scores are country-level approximations based on World Bank / IMF "
            "unemployment and labour market data 2023/24. "
            "Fund targets use estimated monthly expenses from country-level expense ratios "
            "(Numbeo / World Bank). Actual time to reach your fund depends on consistent contributions."
        )

    return result
