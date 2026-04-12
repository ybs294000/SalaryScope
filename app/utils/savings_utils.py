"""
savings_utils.py -- SalaryScope Savings Potential Utility
==========================================================
Estimates monthly and annual savings potential from a net take-home income,
benchmarked against country-level typical household expense ratios.

Answers the question: "How much can I realistically save each month?"

IMPORTANT DISCLAIMER
--------------------
Expense ratios are country-level benchmarks for a middle-income urban household.
Individual savings capacity depends heavily on lifestyle, dependants, rent,
debt obligations, and personal choices. This is not financial advice.

Design
------
- Completely standalone: works with or without tax_utils, takehome_utils,
  col_utils, currency_utils, or any other SalaryScope module.
- `compute_savings_potential(net_monthly_usd, country, ...)` -- pure-math core,
  no Streamlit dependency, safe to call from any tab or utility.
- `render_savings_adjuster(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_tax_adjuster / render_col_adjuster interface pattern.

Integration
-----------
    from savings_utils import render_savings_adjuster

    render_savings_adjuster(
        net_monthly_usd=net_monthly,      # post-tax monthly income
        location_hint=country,
        widget_key="manual_a1_sav",
        gross_usd=prediction,             # optional: shown as context
    )

    # If takehome_utils is also in use, pipe its output:
    from takehome_utils import render_takehome_adjuster
    from savings_utils import render_savings_adjuster

    th = render_takehome_adjuster(gross_usd=prediction, ...)
    render_savings_adjuster(net_monthly_usd=th.get("net_monthly", prediction/12), ...)

Pure-math usage:
    from savings_utils import compute_savings_potential

    result = compute_savings_potential(net_monthly_usd=5000, country="IN")
    print(result["savings"], result["annual_savings"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Built-in country-level expense ratios
# Fraction of net monthly take-home that a typical middle-income urban
# household spends on all expenses (rent, food, transport, utilities, etc.).
# Sources: Numbeo, World Bank household surveys, EIU 2023/24.
# ---------------------------------------------------------------------------
_EXPENSE_RATIO: dict[str, float] = {
    # North America
    "US": 0.70,
    "CA": 0.68,
    "MX": 0.68,
    # Europe
    "GB": 0.68,
    "DE": 0.62,
    "FR": 0.65,
    "CH": 0.65,
    "NL": 0.62,
    "BE": 0.63,
    "AT": 0.62,
    "SE": 0.60,
    "NO": 0.58,
    "DK": 0.60,
    "FI": 0.62,
    "IE": 0.68,
    "ES": 0.65,
    "PT": 0.63,
    "IT": 0.66,
    "GR": 0.67,
    "PL": 0.62,
    "CZ": 0.60,
    "HU": 0.62,
    "RO": 0.63,
    "HR": 0.64,
    "SK": 0.60,
    "SI": 0.62,
    "BG": 0.63,
    "RS": 0.64,
    "TR": 0.70,
    "UA": 0.66,
    "RU": 0.65,
    # Middle East
    "AE": 0.60,
    "QA": 0.58,
    "SA": 0.60,
    "KW": 0.58,
    "BH": 0.60,
    "OM": 0.62,
    "IL": 0.70,
    "JO": 0.68,
    # South Asia
    "IN": 0.55,
    "PK": 0.65,
    "BD": 0.60,
    "LK": 0.60,
    "NP": 0.58,
    # East / Southeast Asia
    "JP": 0.70,
    "KR": 0.62,
    "CN": 0.60,
    "HK": 0.72,
    "TW": 0.65,
    "SG": 0.65,
    "MY": 0.62,
    "TH": 0.63,
    "VN": 0.60,
    "PH": 0.65,
    "ID": 0.63,
    "MM": 0.66,
    # Oceania
    "AU": 0.67,
    "NZ": 0.68,
    # Africa
    "ZA": 0.68,
    "NG": 0.72,
    "KE": 0.68,
    "GH": 0.70,
    "EG": 0.65,
    "MA": 0.66,
    "ET": 0.68,
    "TZ": 0.67,
    # Latin America
    "BR": 0.72,
    "AR": 0.70,
    "CL": 0.65,
    "CO": 0.67,
    "PE": 0.65,
    "BO": 0.65,
    "UY": 0.65,
    "PY": 0.66,
    "VE": 0.72,
    "EC": 0.66,
    "CR": 0.65,
    "DO": 0.66,
    "PA": 0.64,
    "GT": 0.67,
}
_EXPENSE_RATIO_FALLBACK = 0.65

# Recommended savings-rate tiers for guidance labels
_SAVINGS_TIERS = [
    (0.30, "strong",   "#22C55E",
     "Strong savings rate. You are in a healthy financial position."),
    (0.20, "good",     "#34D399",
     "Good savings rate. Consider increasing investments for long-term growth."),
    (0.10, "moderate", "#F59E0B",
     "Moderate savings rate. Reviewing discretionary spend could help."),
    (0.05, "low",      "#FB923C",
     "Low savings rate. Focus on reducing variable and fixed expenses."),
    (0.00, "minimal",  "#EF4444",
     "Expenses are near or exceeding income. Immediate budget review is advised."),
]

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


def _savings_tier(rate: float) -> tuple:
    """Return (tier_label, color, message) for a savings rate."""
    for threshold, label, color, msg in _SAVINGS_TIERS:
        if rate >= threshold:
            return label, color, msg
    return "minimal", "#EF4444", _SAVINGS_TIERS[-1][3]


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit, reusable anywhere
# ---------------------------------------------------------------------------

def compute_savings_potential(
    net_monthly_usd: float,
    country: Optional[str] = None,
    expense_ratio: Optional[float] = None,
    custom_expense_usd: Optional[float] = None,
) -> dict:
    """
    Estimate monthly and annual savings from a net take-home income.

    Parameters
    ----------
    net_monthly_usd    : Monthly net (post-tax) income in USD.
    country            : ISO-2 code or country name for expense-ratio default.
    expense_ratio      : Override the country expense ratio (fraction 0--1).
                         Applied to net income to estimate total monthly expenses.
    custom_expense_usd : If provided, used directly as monthly expenses in USD,
                         bypassing the ratio-based estimate entirely.

    Returns
    -------
    dict with keys:
        net_monthly         -- input net monthly income
        expenses            -- estimated monthly expenses
        savings             -- estimated monthly savings
        savings_rate        -- savings as fraction of net income
        annual_savings      -- monthly savings * 12
        five_year_savings   -- monthly savings * 60 (no investment returns assumed)
        ten_year_savings    -- monthly savings * 120
        expense_ratio_used  -- actual expense fraction (expenses / net_monthly)
        tier                -- savings quality label (strong / good / moderate / low)
        tier_color          -- hex color for the tier
        tier_message        -- guidance message for the tier
    """
    key = _resolve_key(country, _EXPENSE_RATIO)
    ratio = expense_ratio if expense_ratio is not None \
        else _EXPENSE_RATIO.get(key or "", _EXPENSE_RATIO_FALLBACK)

    if custom_expense_usd is not None:
        expenses = max(0.0, float(custom_expense_usd))
    else:
        expenses = net_monthly_usd * ratio

    savings = max(0.0, net_monthly_usd - expenses)
    savings_rate = savings / net_monthly_usd if net_monthly_usd > 0 else 0.0
    tier, color, msg = _savings_tier(savings_rate)
    actual_ratio = expenses / net_monthly_usd if net_monthly_usd > 0 else ratio

    return {
        "net_monthly": net_monthly_usd,
        "expenses": expenses,
        "savings": savings,
        "savings_rate": savings_rate,
        "annual_savings": savings * 12,
        "five_year_savings": savings * 60,
        "ten_year_savings": savings * 120,
        "expense_ratio_used": actual_ratio,
        "tier": tier,
        "tier_color": color,
        "tier_message": msg,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_savings_adjuster(
    net_monthly_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "savings",
    gross_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Savings Potential Calculator panel.

    Parameters
    ----------
    net_monthly_usd : Monthly net (post-tax) income in USD.
                      Pipe in from takehome_utils.render_takehome_adjuster()
                      for best results, or compute from gross as a fallback.
    location_hint   : ISO-2 country code or country name.
    widget_key      : Unique key prefix per call-site (e.g. "manual_a1_sav").
                      Must differ for every place this is called.
    gross_usd       : Optional gross annual salary -- shown as context only.

    Returns
    -------
    dict -- the compute_savings_potential result.
    Returns an empty dict if widget is hidden or income is invalid.

    Usage
    -----
        from savings_utils import render_savings_adjuster
        render_savings_adjuster(net_monthly_usd=net_monthly, location_hint=country,
                                widget_key="manual_a1_sav", gross_usd=prediction)
    """
    if not net_monthly_usd or net_monthly_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/savings: Savings Potential Calculator",
        key=toggle_key,
        value=False,
        help="Estimate monthly savings based on country-typical expense patterns.",
    )
    if not show:
        return {}

    with st.expander(":material/savings: Savings Potential Calculator", expanded=True):
        st.caption(
            ":material/info: Estimates how much you can save each month based on "
            "typical household expense ratios for your country. "
            "Override to match your actual budget. This is not financial advice."
        )

        key = _resolve_key(location_hint, _EXPENSE_RATIO)
        d_ratio = _EXPENSE_RATIO.get(key or "", _EXPENSE_RATIO_FALLBACK)

        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"
        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        if location_hint and location_hint not in ("", "Other"):
            gross_part = (
                f" &nbsp;·&nbsp; <span style='color:#9CA6B5;'>Annual gross:</span>"
                f" <b>{_loc(gross_usd)}</b>"
                if gross_usd else ""
            )
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #22C55E;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#C8D6E8;'>"
                f"<span style='font-weight:700;color:#E6EAF0;'>Country:</span> "
                f"{_country_name(location_hint)}<br>"
                f"<span style='color:#9CA6B5;'>Typical expense ratio:</span> <b>{_pct(d_ratio)} of net income</b>"
                f" &nbsp;·&nbsp; "
                f"<span style='color:#9CA6B5;'>Monthly net income:</span> <b>{_loc(net_monthly_usd)}</b>"
                f"{gross_part}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #6B7585;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#9CA6B5;'>"
                f"Monthly net income: <b style='color:#C8D6E8;'>{_loc(net_monthly_usd)}</b>. "
                "No country detected — using generic 65% expense ratio. "
                "Override below for more accurate results."
                "</div>",
                unsafe_allow_html=True,
            )

        use_custom = st.toggle(
            "Override expense inputs",
            key=f"{widget_key}_custom",
            value=False,
            help="Set your own expense amount or ratio.",
        )

        custom_expense: Optional[float] = None
        custom_ratio: Optional[float] = None

        if use_custom:
            mode = st.radio(
                "Input mode",
                ["Set expense ratio (%)", "Set expense amount (USD / month)"],
                key=f"{widget_key}_mode",
                horizontal=True,
            )
            if mode == "Set expense ratio (%)":
                custom_ratio = st.slider(
                    "Monthly expense ratio (% of net income)",
                    min_value=10, max_value=100,
                    value=int(d_ratio * 100),
                    step=1,
                    key=f"{widget_key}_ratio",
                    help=(
                        "Percentage of your net monthly income spent on all "
                        "expenses including rent, food, transport, utilities, "
                        "and discretionary spending."
                    ),
                ) / 100.0
            else:
                custom_expense = st.number_input(
                    "Monthly expenses (USD)",
                    min_value=0.0,
                    max_value=float(net_monthly_usd * 2.0),
                    value=float(round(net_monthly_usd * d_ratio, 0)),
                    step=50.0,
                    key=f"{widget_key}_exp_amt",
                    help="Your actual estimated total monthly expenditure in USD.",
                )

        result = compute_savings_potential(
            net_monthly_usd,
            location_hint,
            expense_ratio=custom_ratio,
            custom_expense_usd=custom_expense,
        )

        st.divider()

        # Top-level cards: income / expenses / savings
        c1, c2, c3 = st.columns(3)
        c1.metric(
            f"Monthly Net Income ({cur_code})" if use_local else "Monthly Net Income (USD)",
            _loc(result["net_monthly"]),
        )
        c2.metric(
            f"Est. Monthly Expenses ({cur_code})" if use_local else "Est. Monthly Expenses (USD)",
            _loc(result["expenses"]),
            delta=f"-{result['expense_ratio_used'] * 100:.0f}% of income",
            delta_color="inverse",
        )
        c3.metric(
            f"Monthly Savings ({cur_code})" if use_local else "Monthly Savings (USD)",
            _loc(result["savings"]),
            delta=f"{result['savings_rate'] * 100:.1f}% savings rate",
            delta_color="normal",
        )

        annual_card_label = (
            f"ESTIMATED ANNUAL SAVINGS ({cur_code})"
            if use_local else "ESTIMATED ANNUAL SAVINGS (USD)"
        )
        st.markdown(
            _card(
                _loc(result["annual_savings"]),
                annual_card_label,
                color=result["tier_color"],
            ),
            unsafe_allow_html=True,
        )

        c4, c5, c6 = st.columns(3)
        c4.metric("Savings Rate", f"{result['savings_rate'] * 100:.1f}%")
        c5.metric(
            f"5-Year Savings ({cur_code})" if use_local else "5-Year Savings (USD)",
            _loc(result["five_year_savings"]),
        )
        c6.metric(
            f"10-Year Savings ({cur_code})" if use_local else "10-Year Savings (USD)",
            _loc(result["ten_year_savings"]),
        )

        # Tier icon mapping
        tier_icons = {
            "strong":   ":material/thumb_up:",
            "good":     ":material/trending_up:",
            "moderate": ":material/trending_flat:",
            "low":      ":material/warning:",
            "minimal":  ":material/error:",
        }
        icon = tier_icons.get(result["tier"], ":material/info:")
        st.markdown(
            f"<p style='color:{result['tier_color']};font-size:14px;margin-top:6px;'>"
            f"{result['tier_message']}</p>",
            unsafe_allow_html=True,
        )

        # Expense vs savings bar
        st.divider()
        st.markdown("**Income Allocation**")
        exp_pct = result["expense_ratio_used"] * 100
        sav_pct = result["savings_rate"] * 100
        exp_bar = max(2, int(exp_pct * 1.5))
        sav_bar = max(2, int(sav_pct * 1.5))
        st.markdown(
            f"<div style='margin:4px 0;'>"
            f"<span style='display:inline-block;width:120px;color:#9CA6B5;"
            f"font-size:13px;'>Expenses</span>"
            f"<span style='display:inline-block;background:#EF4444;"
            f"width:{exp_bar}px;height:13px;border-radius:3px;"
            f"vertical-align:middle;margin-right:8px;'></span>"
            f"<span style='color:#E6EAF0;font-size:13px;'>"
            f"{_loc(result['expenses'])} / mo ({exp_pct:.1f}%)</span>"
            f"</div>"
            f"<div style='margin:4px 0;'>"
            f"<span style='display:inline-block;width:120px;color:#9CA6B5;"
            f"font-size:13px;'>Savings</span>"
            f"<span style='display:inline-block;background:{result['tier_color']};"
            f"width:{sav_bar}px;height:13px;border-radius:3px;"
            f"vertical-align:middle;margin-right:8px;'></span>"
            f"<span style='color:#E6EAF0;font-size:13px;'>"
            f"{_loc(result['savings'])} / mo ({sav_pct:.1f}%)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.caption(
            "Expense ratios are country-level benchmarks for a middle-income urban "
            "household (Numbeo / World Bank / EIU 2023/24). "
            "Savings projections assume no investment returns or compounding. "
            "Individual results vary significantly based on lifestyle and location."
        )

    return result