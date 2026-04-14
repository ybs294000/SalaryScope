"""
investment_utils.py -- SalaryScope Investment Growth Estimator
==============================================================
Projects the future value of regular monthly savings under compound growth,
using country-adjusted expected return benchmarks for typical retail investment
instruments (equity index funds, balanced funds, fixed deposits).

Answers the question: "If I invest my savings consistently, what will I have?"

IMPORTANT DISCLAIMER
--------------------
Investment projections are purely illustrative. Actual returns depend on
market conditions, instrument choice, fees, taxes, inflation, and timing.
Past performance does not guarantee future results. This is not financial
advice or investment guidance. Consult a qualified financial advisor.

Design
------
- Completely standalone: works with or without savings_utils, loan_utils,
  budget_utils, tax_utils, takehome_utils, col_utils, or any other module.
- `compute_investment_growth(monthly_savings_usd, ...)` -- pure-math core
  using the standard future-value of an annuity formula. No Streamlit.
- `render_investment_estimator(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_savings_adjuster / render_loan_adjuster interface pattern.

Integration
-----------
    from investment_utils import render_investment_estimator

    render_investment_estimator(
        monthly_savings_usd=monthly_savings,
        location_hint=country,
        widget_key="manual_a1_inv",
        net_monthly_usd=net_monthly,
    )

    # Best practice: pipe from savings_utils
    from savings_utils import render_savings_adjuster
    from investment_utils import render_investment_estimator

    sav = render_savings_adjuster(net_monthly_usd=net_monthly, ...)
    render_investment_estimator(
        monthly_savings_usd=sav.get("savings", net_monthly * 0.20),
        ...
    )

Pure-math usage:
    from investment_utils import compute_investment_growth

    result = compute_investment_growth(monthly_savings_usd=500, country="IN")
    print(result["value_10yr"], result["value_30yr"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Country-level expected annual return benchmarks.
# These represent a blended retail investor return across equity index and
# balanced fund instruments, net of typical fund expense ratios.
# Sources: long-run equity return studies (Dimson/Marsh/Staunton), IMF,
# World Bank, local market historical CAGR 2000-2023.
# These are broad approximations -- individual results vary enormously.
# ---------------------------------------------------------------------------
_EXPECTED_RETURN: dict[str, float] = {
    # North America
    "US": 0.090,   # S&P 500 long-run ~10%, net of fees ~9%
    "CA": 0.082,
    "MX": 0.095,   # higher nominal due to inflation environment
    # Europe
    "GB": 0.078,
    "DE": 0.075,
    "FR": 0.075,
    "CH": 0.065,
    "NL": 0.075,
    "BE": 0.072,
    "AT": 0.070,
    "SE": 0.082,
    "NO": 0.078,
    "DK": 0.078,
    "FI": 0.078,
    "IE": 0.075,
    "ES": 0.072,
    "PT": 0.070,
    "IT": 0.068,
    "GR": 0.068,
    "PL": 0.085,
    "CZ": 0.080,
    "HU": 0.088,
    "RO": 0.090,
    "TR": 0.120,   # high nominal, high inflation
    "UA": 0.100,
    "RU": 0.100,
    # Middle East
    "AE": 0.075,
    "QA": 0.075,
    "SA": 0.078,
    "KW": 0.072,
    "BH": 0.072,
    "OM": 0.070,
    "IL": 0.080,
    "JO": 0.072,
    # South Asia
    "IN": 0.110,   # Nifty 50 long-run ~12%, conservative blended estimate
    "PK": 0.110,
    "BD": 0.100,
    "LK": 0.095,
    "NP": 0.090,
    # East / Southeast Asia
    "JP": 0.055,
    "KR": 0.082,
    "CN": 0.088,
    "HK": 0.072,
    "TW": 0.090,
    "SG": 0.070,
    "MY": 0.082,
    "TH": 0.085,
    "VN": 0.100,
    "PH": 0.090,
    "ID": 0.100,
    "MM": 0.100,
    # Oceania
    "AU": 0.082,
    "NZ": 0.078,
    # Africa
    "ZA": 0.092,
    "NG": 0.115,
    "KE": 0.110,
    "GH": 0.115,
    "EG": 0.115,
    "MA": 0.088,
    "ET": 0.095,
    "TZ": 0.100,
    # Latin America
    "BR": 0.100,
    "AR": 0.130,   # very high nominal, high inflation
    "CL": 0.085,
    "CO": 0.095,
    "PE": 0.090,
    "BO": 0.088,
    "UY": 0.090,
    "CR": 0.088,
    "DO": 0.090,
    "PA": 0.080,
    "EC": 0.085,
}
_EXPECTED_RETURN_FALLBACK = 0.080

# Inflation rate approximations (annual) for real return calculation
_INFLATION_RATE: dict[str, float] = {
    "US": 0.030, "CA": 0.028, "GB": 0.032, "DE": 0.025, "FR": 0.025,
    "CH": 0.015, "AU": 0.030, "NZ": 0.030, "JP": 0.015, "SG": 0.022,
    "IN": 0.055, "PK": 0.080, "BD": 0.060, "CN": 0.025, "BR": 0.055,
    "MX": 0.055, "TR": 0.060, "AR": 0.080, "ZA": 0.055, "NG": 0.080,
    "AE": 0.025, "SA": 0.025, "IL": 0.030,
}
_INFLATION_RATE_FALLBACK = 0.035


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


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit dependency
# ---------------------------------------------------------------------------

def _fv_annuity(pmt: float, monthly_rate: float, n_months: int) -> float:
    """Future value of a regular monthly payment under compound interest."""
    if monthly_rate == 0.0:
        return pmt * n_months
    return pmt * (((1 + monthly_rate) ** n_months - 1) / monthly_rate)


def compute_investment_growth(
    monthly_savings_usd: float,
    country: Optional[str] = None,
    annual_return_pct: Optional[float] = None,
    horizons_yr: Optional[list] = None,
) -> dict:
    """
    Project the future value of consistent monthly savings under compound growth.

    Parameters
    ----------
    monthly_savings_usd : Monthly amount invested / saved (USD).
    country             : ISO-2 code or country name for default return rate.
    annual_return_pct   : Override annual return rate (as %, e.g. 8.0 for 8%).
                          If None, uses country-level benchmark.
    horizons_yr         : List of year horizons to compute. Default: [5,10,20,30].

    Returns
    -------
    dict with keys:
        monthly_savings     -- input monthly amount
        annual_return_pct   -- actual return rate used (as %)
        inflation_pct       -- country-level inflation estimate (as %)
        real_return_pct     -- inflation-adjusted annual return (as %)
        horizons            -- list of dicts, each with:
                                 years, value_nominal, value_real,
                                 total_contributed, total_gain
        total_contributed_* -- total cash put in over each horizon
    """
    if horizons_yr is None:
        horizons_yr = [5, 10, 20, 30]

    key = _resolve_key(country, _EXPECTED_RETURN)
    inf_key = _resolve_key(country, _INFLATION_RATE)

    if annual_return_pct is not None:
        r_annual = float(annual_return_pct) / 100.0
    else:
        r_annual = _EXPECTED_RETURN.get(key or "", _EXPECTED_RETURN_FALLBACK)

    inflation = _INFLATION_RATE.get(inf_key or "", _INFLATION_RATE_FALLBACK)
    real_r_annual = ((1 + r_annual) / (1 + inflation)) - 1.0

    monthly_rate = r_annual / 12.0
    real_monthly_rate = real_r_annual / 12.0

    horizons_data = []
    for yrs in horizons_yr:
        n = yrs * 12
        value_nominal = _fv_annuity(monthly_savings_usd, monthly_rate, n)
        value_real = _fv_annuity(monthly_savings_usd, real_monthly_rate, n)
        contributed = monthly_savings_usd * n
        gain = value_nominal - contributed
        horizons_data.append({
            "years": yrs,
            "value_nominal": value_nominal,
            "value_real": value_real,
            "total_contributed": contributed,
            "total_gain": gain,
        })

    return {
        "monthly_savings": monthly_savings_usd,
        "annual_return_pct": r_annual * 100.0,
        "inflation_pct": inflation * 100.0,
        "real_return_pct": real_r_annual * 100.0,
        "horizons": horizons_data,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_investment_estimator(
    monthly_savings_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "investment",
    net_monthly_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Investment Growth Estimator panel.

    Parameters
    ----------
    monthly_savings_usd : Monthly savings amount to invest (USD).
                          Pipe in from savings_utils.render_savings_adjuster()
                          result["savings"] for best results.
    location_hint       : ISO-2 country code or country name.
    widget_key          : Unique key prefix per call-site (e.g. "manual_a1_inv").
                          Must differ for every place this is called.
    net_monthly_usd     : Optional net monthly income -- shown as context only.

    Returns
    -------
    dict -- the compute_investment_growth result.
    Returns an empty dict if widget is hidden or savings amount is invalid.
    """
    if not monthly_savings_usd or monthly_savings_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/trending_up: Investment Growth Estimator",
        key=toggle_key,
        value=False,
        help="Project how your savings could grow under compound investment returns.",
    )
    if not show:
        return {}

    with st.expander(":material/trending_up: Investment Growth Estimator", expanded=True):
        st.caption(
            ":material/info: Projects future value of regular monthly investments "
            "using the compound interest annuity formula. Return rates are "
            "country-level benchmarks for a blended retail investment portfolio. "
            "This is not financial advice -- actual returns vary significantly."
        )

        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        key = _resolve_key(location_hint, _EXPECTED_RETURN)
        d_return = _EXPECTED_RETURN.get(key or "", _EXPECTED_RETURN_FALLBACK)

        if location_hint and location_hint not in ("", "Other"):
            context_parts = (
                f"<span style='color:#9CA6B5;'>Monthly savings to invest:</span>"
                f" <b>{_loc(monthly_savings_usd)}</b>"
            )
            if net_monthly_usd:
                context_parts += (
                    f" &nbsp;&middot;&nbsp; "
                    f"<span style='color:#9CA6B5;'>Monthly net income:</span>"
                    f" <b>{_loc(net_monthly_usd)}</b>"
                )
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #22C55E;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#C8D6E8;'>"
                f"<span style='font-weight:700;color:#E6EAF0;'>Country:</span> "
                f"{_country_name(location_hint)}<br>"
                f"<span style='color:#9CA6B5;'>Default annual return benchmark:</span>"
                f" <b>{d_return * 100:.1f}% p.a.</b>"
                f" &nbsp;&middot;&nbsp; "
                f"{context_parts}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #6B7585;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#9CA6B5;'>"
                f"Monthly savings to invest: <b style='color:#C8D6E8;'>{_loc(monthly_savings_usd)}</b>. "
                "No country detected -- using 8.0% generic return benchmark. "
                "Override below for a different scenario."
                "</div>",
                unsafe_allow_html=True,
            )

        use_custom = st.toggle(
            "Override investment parameters",
            key=f"{widget_key}_custom",
            value=False,
            help="Set your own expected annual return and monthly investment amount.",
        )

        custom_return_pct = None
        custom_monthly = monthly_savings_usd

        if use_custom:
            c1, c2 = st.columns(2)
            with c1:
                custom_return_pct = st.slider(
                    "Expected Annual Return (%)",
                    min_value=1.0, max_value=30.0,
                    value=float(round(d_return * 100, 1)),
                    step=0.5,
                    key=f"{widget_key}_return",
                    help=(
                        "Expected average annual return on your investments. "
                        "Conservative estimate (FD / bonds): 4-7%. "
                        "Equity index funds (long-run average): 8-12%. "
                        "Higher risk instruments may yield more or less."
                    ),
                )
            with c2:
                custom_monthly = st.number_input(
                    "Monthly Investment Amount (USD)",
                    min_value=1.0,
                    max_value=float(max(monthly_savings_usd * 3, 10000)),
                    value=float(round(monthly_savings_usd, 2)),
                    step=10.0,
                    key=f"{widget_key}_monthly",
                    help=(
                        "The amount you plan to invest each month consistently. "
                        "Defaults to your estimated monthly savings."
                    ),
                )

        result = compute_investment_growth(
            monthly_savings_usd=custom_monthly,
            country=location_hint,
            annual_return_pct=custom_return_pct,
        )

        st.divider()

        label_suffix = f"({cur_code})" if use_local else "(USD)"

        c1, c2, c3 = st.columns(3)
        c1.metric(
            f"Monthly Investment {label_suffix}",
            _loc(result["monthly_savings"]),
        )
        c2.metric("Annual Return Used", f"{result['annual_return_pct']:.1f}% p.a.")
        c3.metric("Real Return (Inflation-adj.)", f"{result['real_return_pct']:.1f}% p.a.")

        st.divider()
        st.markdown("**Projected Portfolio Value**")

        colors = ["#F59E0B", "#3B82F6", "#A78BFA", "#22C55E"]
        for idx, h in enumerate(result["horizons"]):
            color = colors[idx % len(colors)]
            st.markdown(
                _card(
                    _loc(h["value_nominal"]),
                    f"PROJECTED VALUE AFTER {h['years']} YEARS {label_suffix}",
                    color=color,
                ),
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown("**Detailed Projection Table**")
        for h in result["horizons"]:
            st.markdown(
                _info_row(f"{h['years']}-year nominal value", _loc(h["value_nominal"])),
                unsafe_allow_html=True,
            )
            st.markdown(
                _info_row(
                    f"{h['years']}-year real value (inflation-adj.)",
                    _loc(h["value_real"]),
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                _info_row(
                    f"{h['years']}-year total contributed",
                    _loc(h["total_contributed"]),
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                _info_row(
                    f"{h['years']}-year total gain",
                    _loc(h["total_gain"]),
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div style='height:8px;'></div>",
                unsafe_allow_html=True,
            )

        st.caption(
            "Uses the future-value annuity formula: FV = PMT x [(1+r)^n - 1] / r. "
            "Return benchmarks are long-run blended estimates; actual market returns vary. "
            "Real return adjusts for country-level inflation approximation. "
            "No tax on gains is modelled. Consult a financial advisor for personalised planning."
        )

    return result
