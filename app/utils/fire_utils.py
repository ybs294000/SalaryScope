"""
fire_utils.py -- SalaryScope FIRE Calculator
============================================
Financial Independence / Retire Early (FIRE) estimator.

Answers the core FIRE question:
    "How long until I can retire and live off my investments?"

FIRE Variants supported
-----------------------
- Lean FIRE   : Minimal lifestyle, typically 25x lean annual expenses
- Regular FIRE: Standard lifestyle, 25x current annual expenses (4% rule)
- Fat FIRE    : Affluent lifestyle, 33x annual expenses (3% withdrawal rate)
- Coast FIRE  : Stop contributing now and let growth carry you to a target
- Barista FIRE: Semi-retire with part-time income covering partial expenses

Core formula
------------
    FIRE Number = Annual Expenses / Withdrawal Rate
    Years to FIRE = log(FN / (FN - P)) / log(1 + r)
        where P = current portfolio, r = real return rate per year

Design notes
------------
- compute_fire() is a pure-math function with no Streamlit dependency.
- render_fire_calculator() provides the full Streamlit UI, following the
  same toggle + expander pattern used by render_savings_adjuster(),
  render_tax_adjuster(), and render_col_adjuster().
- All monetary values handled internally in USD; local currency display
  is applied only at render time via the same currency helper used across
  the app.
- No external dependencies beyond stdlib math and streamlit/plotly.

Integration
-----------
    from fire_utils import render_fire_calculator

    render_fire_calculator(
        annual_salary_usd=prediction,         # gross annual salary in USD
        location_hint=country,                # ISO-2 or plain country name
        widget_key="manual_a1_fire",          # unique key per call-site
        net_monthly_usd=net_monthly,          # optional, from takehome_utils
        savings_monthly_usd=monthly_savings,  # optional, from savings_utils
    )

IMPORTANT DISCLAIMER
--------------------
This tool is for educational and illustrative purposes only.
It is not financial advice. Real retirement planning depends on taxes,
inflation, healthcare costs, market volatility, sequence-of-returns risk,
social security / pension entitlements, and individual circumstances that
this model cannot capture. Consult a qualified financial advisor.
"""

from __future__ import annotations

import math
from typing import Optional

import plotly.graph_objects as go
import streamlit as st

from app.theme import apply_theme

# ---------------------------------------------------------------------------
# FIRE configuration constants
# ---------------------------------------------------------------------------

# Safe withdrawal rate by FIRE variant
_WITHDRAWAL_RATES: dict[str, float] = {
    "Lean FIRE":    0.04,   # 4% rule -- minimal lifestyle
    "Regular FIRE": 0.04,   # 4% rule -- current lifestyle
    "Fat FIRE":     0.03,   # 3% rule -- affluent lifestyle
    "Coast FIRE":   0.04,   # used for target computation only
    "Barista FIRE": 0.04,   # partial withdrawal; rest from part-time income
}

# Expense multiplier relative to input annual expenses for each variant
_EXPENSE_MULTIPLIER: dict[str, float] = {
    "Lean FIRE":    0.70,   # 70% of current expenses -- stripped-down life
    "Regular FIRE": 1.00,   # match current expenses
    "Fat FIRE":     1.50,   # 150% -- upgraded lifestyle
    "Coast FIRE":   1.00,
    "Barista FIRE": 1.00,
}

# Assumed long-run nominal portfolio returns by risk profile
_RETURN_RATES: dict[str, float] = {
    "Conservative (bonds-heavy, ~5% nominal)": 0.05,
    "Moderate (60/40 portfolio, ~7% nominal)":  0.07,
    "Aggressive (equity-heavy, ~9% nominal)":  0.09,
}

# Assumed long-run inflation rate for real-return calculation
_INFLATION = 0.03

# Color palette consistent with SalaryScope dark theme
_COLORS = {
    "accent":   "#3B82F6",
    "green":    "#22C55E",
    "amber":    "#F59E0B",
    "red":      "#EF4444",
    "muted":    "#9CA6B5",
    "text":     "#E6EAF0",
    "subtext":  "#C8D6E8",
    "bg_card":  "linear-gradient(135deg,#1A2535 0%,#1B2230 100%)",
    "border":   "#2D3A50",
}

# ---------------------------------------------------------------------------
# Country-level default expense ratios (reused from savings_utils pattern)
# ---------------------------------------------------------------------------
_EXPENSE_RATIO: dict[str, float] = {
    "US": 0.70, "CA": 0.68, "GB": 0.68, "DE": 0.62, "FR": 0.65,
    "CH": 0.65, "NL": 0.62, "BE": 0.63, "AT": 0.62, "SE": 0.60,
    "NO": 0.58, "DK": 0.60, "FI": 0.62, "IE": 0.68, "ES": 0.65,
    "PT": 0.63, "IT": 0.66, "GR": 0.67, "PL": 0.62, "CZ": 0.60,
    "HU": 0.62, "RO": 0.63, "HR": 0.64, "SK": 0.60, "SI": 0.62,
    "BG": 0.63, "RS": 0.64, "TR": 0.70, "UA": 0.66, "RU": 0.65,
    "AE": 0.60, "QA": 0.58, "SA": 0.60, "KW": 0.58, "IL": 0.70,
    "IN": 0.55, "PK": 0.65, "BD": 0.60, "LK": 0.60,
    "JP": 0.70, "KR": 0.62, "CN": 0.60, "HK": 0.72, "SG": 0.65,
    "MY": 0.62, "TH": 0.63, "PH": 0.65, "ID": 0.63,
    "AU": 0.67, "NZ": 0.68,
    "ZA": 0.68, "NG": 0.72, "KE": 0.68, "EG": 0.65,
    "BR": 0.72, "AR": 0.70, "CL": 0.65, "CO": 0.67, "MX": 0.68,
}
_EXPENSE_FALLBACK = 0.65


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_iso2(location_hint: Optional[str]) -> Optional[str]:
    if not location_hint:
        return None
    try:
        from app.utils.country_utils import resolve_iso2
        return resolve_iso2(location_hint)
    except ImportError:
        return str(location_hint).strip().upper() if location_hint else None


def _country_name(location_hint: Optional[str]) -> str:
    if not location_hint:
        return "Unknown"
    try:
        from app.utils.country_utils import get_country_name
        return get_country_name(location_hint) or str(location_hint)
    except ImportError:
        return str(location_hint)


def _get_currency_meta(location_hint: Optional[str]) -> tuple[str, str, float]:
    """Return (currency_code, symbol, fx_rate_from_usd). Falls back to USD."""
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


def _fmt_usd(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:,.2f}M"
    return f"${v:,.0f}"


def _fmt_local(v: float, symbol: str, code: str) -> str:
    no_decimal = {"JPY", "KRW", "IDR", "VND", "CLP", "UGX", "TZS",
                  "PYG", "LAK", "MNT", "MMK", "KHR", "IRR"}
    raw = v
    if abs(raw) >= 1_000_000:
        if code in no_decimal:
            return f"{symbol}{raw / 1_000_000:,.1f}M"
        return f"{symbol}{raw / 1_000_000:,.2f}M"
    if code in no_decimal:
        return f"{symbol}{raw:,.0f}"
    return f"{symbol}{raw:,.0f}"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert #RRGGBB to rgba(r,g,b,a), with a safe fallback."""
    h = (hex_color or "").lstrip("#")
    try:
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    except Exception:
        return f"rgba(59,130,246,{alpha})"


def _stat_card(value: str, label: str, color: str = "#3B82F6",
               sub: str = "") -> str:
    sub_html = (
        f"<div style='font-size:11px;color:{_COLORS['muted']};margin-top:4px;'>"
        f"{sub}</div>"
        if sub else ""
    )
    return (
        f"<div style='background:{_COLORS['bg_card']};"
        f"border:1px solid {_COLORS['border']};border-left:4px solid {color};"
        f"border-radius:10px;padding:16px 20px;margin:6px 0;text-align:center;'>"
        f"<div style='font-size:26px;font-weight:700;color:{color};'>{value}</div>"
        f"<div style='font-size:12px;color:{_COLORS['muted']};margin-top:4px;"
        f"letter-spacing:0.06em;text-transform:uppercase;'>{label}</div>"
        f"{sub_html}"
        f"</div>"
    )


def _info_row(label: str, value: str, color: str = "#C8D6E8") -> str:
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:6px 0;border-bottom:1px solid #1E2D40;font-size:13px;'>"
        f"<span style='color:{_COLORS['muted']};'>{label}</span>"
        f"<span style='color:{color};font-weight:600;'>{value}</span>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Pure-math core
# ---------------------------------------------------------------------------

def compute_fire(
    annual_expenses_usd: float,
    current_portfolio_usd: float,
    annual_contribution_usd: float,
    fire_variant: str = "Regular FIRE",
    return_rate_label: str = "Moderate (60/40 portfolio, ~7% nominal)",
    barista_part_time_income_usd: float = 0.0,
    coast_target_age: int = 65,
    current_age: int = 30,
) -> dict:
    """
    Compute FIRE projection metrics.

    Parameters
    ----------
    annual_expenses_usd       : Current annual expenses in USD.
    current_portfolio_usd     : Existing invested portfolio value in USD.
    annual_contribution_usd   : Amount added to portfolio per year in USD.
    fire_variant              : One of the keys in _WITHDRAWAL_RATES.
    return_rate_label         : One of the keys in _RETURN_RATES.
    barista_part_time_income_usd : Annual part-time income for Barista FIRE.
    coast_target_age          : Target full retirement age for Coast FIRE.
    current_age               : Current age of the person.

    Returns
    -------
    dict with keys:
        fire_number, target_expenses, withdrawal_rate, real_return,
        years_to_fire, fire_age, current_portfolio, annual_contribution,
        progress_pct, milestone_years, portfolio_by_year,
        coast_number (Coast FIRE only), variant, is_already_fire,
        barista_fire_number (Barista FIRE only)
    """
    nominal_rate = _RETURN_RATES.get(return_rate_label, 0.07)
    real_rate = (1 + nominal_rate) / (1 + _INFLATION) - 1  # real return

    withdrawal_rate = _WITHDRAWAL_RATES.get(fire_variant, 0.04)
    expense_mult = _EXPENSE_MULTIPLIER.get(fire_variant, 1.0)
    target_expenses = annual_expenses_usd * expense_mult

    # Barista FIRE: part-time income covers some expenses
    if fire_variant == "Barista FIRE":
        net_expenses_needed = max(0.0, target_expenses - barista_part_time_income_usd)
        fire_number = net_expenses_needed / withdrawal_rate
    else:
        fire_number = target_expenses / withdrawal_rate

    # Coast FIRE: how much do you need today so it grows to FIRE number by target age?
    years_to_coast_target = max(1, coast_target_age - current_age)
    coast_number = fire_number / ((1 + real_rate) ** years_to_coast_target)

    is_already_fire = current_portfolio_usd >= fire_number
    is_coast = fire_variant == "Coast FIRE"

    # Years to FIRE -- use FV of annuity formula
    # FV = P*(1+r)^n + C*((1+r)^n - 1)/r = fire_number
    # Solve numerically (year-by-year) for robustness
    portfolio = current_portfolio_usd
    year = 0
    max_years = 80
    milestone_years: dict[str, int] = {}
    portfolio_by_year: list[dict] = [{"year": 0, "portfolio": portfolio}]

    # Coast FIRE: target is coast_number, not fire_number
    effective_target = coast_number if is_coast else fire_number

    if not is_already_fire or is_coast:
        while portfolio < effective_target and year < max_years:
            portfolio = portfolio * (1 + real_rate) + annual_contribution_usd
            year += 1
            portfolio_by_year.append({"year": year, "portfolio": portfolio})
            # milestones at 25%, 50%, 75%, 100%
            for pct, label in [(0.25, "25%"), (0.50, "50%"), (0.75, "75%"), (1.0, "100%")]:
                if label not in milestone_years and portfolio >= effective_target * pct:
                    milestone_years[label] = year
    else:
        # Already at FIRE -- still project growth for chart
        for y in range(1, 21):
            portfolio = portfolio * (1 + real_rate)
            portfolio_by_year.append({"year": y, "portfolio": portfolio})

    years_to_fire = year if (portfolio >= effective_target or is_already_fire) else max_years
    fire_age = current_age + years_to_fire
    progress_pct = min(100.0, (current_portfolio_usd / effective_target) * 100)

    return {
        "fire_number":              fire_number,
        "coast_number":             coast_number,
        "target_expenses":          target_expenses,
        "withdrawal_rate":          withdrawal_rate,
        "real_return":              real_rate,
        "nominal_return":           nominal_rate,
        "years_to_fire":            years_to_fire,
        "fire_age":                 fire_age,
        "current_portfolio":        current_portfolio_usd,
        "annual_contribution":      annual_contribution_usd,
        "progress_pct":             progress_pct,
        "milestone_years":          milestone_years,
        "portfolio_by_year":        portfolio_by_year,
        "variant":                  fire_variant,
        "is_already_fire":          is_already_fire,
        "barista_fire_number":      fire_number,
        "barista_part_time_income": barista_part_time_income_usd,
        "reached_in_years":         years_to_fire,
        "max_years_hit":            year >= max_years and portfolio < effective_target,
    }


# ---------------------------------------------------------------------------
# Streamlit render function
# ---------------------------------------------------------------------------

def render_fire_calculator(
    annual_salary_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "fire_main",
    net_monthly_usd: Optional[float] = None,
    savings_monthly_usd: Optional[float] = None,
) -> dict:
    """
    Render the FIRE Calculator toggle + expander widget.

    Parameters
    ----------
    annual_salary_usd     : Gross annual salary in USD (used to pre-fill inputs).
    location_hint         : ISO-2 code or country name for currency display.
    widget_key            : Unique key prefix per call-site.
    net_monthly_usd       : Optional post-tax monthly income (from takehome_utils).
    savings_monthly_usd   : Optional monthly savings (from savings_utils).

    Returns
    -------
    dict -- the compute_fire() result, or {} if widget is hidden or input invalid.
    """
    if not annual_salary_usd or annual_salary_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/local_fire_department: FIRE Calculator",
        key=toggle_key,
        value=False,
        help=(
            "Estimate how long until you reach Financial Independence / "
            "Retire Early based on your salary, savings, and investment growth."
        ),
    )
    if not show:
        return {}

    with st.expander(":material/local_fire_department: FIRE Calculator -- Financial Independence / Retire Early", expanded=True):
        st.caption(
            ":material/info: Estimates how long until you can retire based on the 4% safe withdrawal rule "
            "and compound investment growth. Results are illustrative only and not financial advice. "
            "Real outcomes depend on taxes, inflation, market returns, and individual circumstances."
        )

        # ------------------------------------------------------------------
        # Currency setup
        # ------------------------------------------------------------------
        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt_usd(v)

        def _to_input_currency(v_usd: float) -> float:
            return v_usd * fx_rate if use_local else v_usd

        def _from_input_currency(v_input: float) -> float:
            if use_local and fx_rate > 0:
                return v_input / fx_rate
            return v_input

        # ------------------------------------------------------------------
        # Derived defaults from upstream modules
        # ------------------------------------------------------------------
        iso2 = _resolve_iso2(location_hint)
        exp_ratio = _EXPENSE_RATIO.get(iso2 or "", _EXPENSE_FALLBACK)

        # Annual net income -- prefer piped value, else estimate from gross
        if net_monthly_usd and net_monthly_usd > 0:
            annual_net = net_monthly_usd * 12
        else:
            annual_net = annual_salary_usd * 0.75   # rough 25% tax estimate

        # Default annual expenses from expense ratio
        default_annual_expenses = annual_net * exp_ratio

        # Default monthly contribution -- prefer piped savings, else estimate
        if savings_monthly_usd and savings_monthly_usd > 0:
            default_monthly_contribution = savings_monthly_usd
        else:
            default_monthly_contribution = annual_net * (1 - exp_ratio) / 12

        # ------------------------------------------------------------------
        # Inputs -- Section 1: Personal & Financial Profile
        # ------------------------------------------------------------------
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:12px 0 4px;letter-spacing:0.04em;'>"
            "Personal & Financial Profile"
            "</div>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            current_age = st.number_input(
                "Current age",
                min_value=18,
                max_value=80,
                value=30,
                step=1,
                key=f"{widget_key}_age",
                help="Your current age in years.",
            )
        with c2:
            target_retirement_age = st.number_input(
                "Target retirement age (for Coast FIRE reference)",
                min_value=current_age + 1,
                max_value=90,
                value=min(65, max(current_age + 2, 65)),
                step=1,
                key=f"{widget_key}_ret_age",
                help="Age at which you plan to fully retire. Used for Coast FIRE calculation.",
            )

        c3, c4 = st.columns(2)
        portfolio_label = f"Current invested portfolio ({cur_code})" if use_local else "Current invested portfolio (USD)"
        contribution_label = f"Annual contribution to investments ({cur_code})" if use_local else "Annual contribution to investments (USD)"
        with c3:
            current_portfolio_input = st.number_input(
                portfolio_label,
                min_value=0.0,
                max_value=float(_to_input_currency(100_000_000.0)),
                value=float(round(_to_input_currency(annual_salary_usd * 0.5), -3)),
                step=float(max(1000.0, round(_to_input_currency(1000.0), -2))),
                key=f"{widget_key}_portfolio",
                help=(
                    "Total value of your current investment accounts "
                    "(stocks, ETFs, retirement accounts, etc.). "
                    "Exclude cash savings, real estate equity, and non-invested assets."
                ),
            )
        with c4:
            annual_contribution_input = st.number_input(
                contribution_label,
                min_value=0.0,
                max_value=float(_to_input_currency(annual_salary_usd * 2)),
                value=float(round(_to_input_currency(default_monthly_contribution * 12), -2)),
                step=float(max(500.0, round(_to_input_currency(500.0), -2))),
                key=f"{widget_key}_contrib",
                help=(
                    "How much you invest per year across all accounts. "
                    "Pre-filled from your estimated savings if available."
                ),
            )

        # ------------------------------------------------------------------
        # Inputs -- Section 2: Expense & FIRE Target
        # ------------------------------------------------------------------
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:12px 0 4px;letter-spacing:0.04em;'>"
            "Annual Expenses and FIRE Target"
            "</div>",
            unsafe_allow_html=True,
        )

        c5, c6 = st.columns(2)
        expenses_label = f"Current annual living expenses ({cur_code})" if use_local else "Current annual living expenses (USD)"
        with c5:
            annual_expenses_input = st.number_input(
                expenses_label,
                min_value=float(max(1000.0, round(_to_input_currency(1000.0), -2))),
                max_value=float(_to_input_currency(10_000_000.0)),
                value=float(round(_to_input_currency(default_annual_expenses), -2)),
                step=float(max(500.0, round(_to_input_currency(500.0), -2))),
                key=f"{widget_key}_expenses",
                help=(
                    "Your total annual spending on housing, food, transport, "
                    "healthcare, leisure, and all other costs. "
                    "Pre-filled from your country's typical expense ratio."
                ),
            )
        with c6:
            fire_variant = st.selectbox(
                "FIRE variant",
                list(_WITHDRAWAL_RATES.keys()),
                index=1,    # default: Regular FIRE
                key=f"{widget_key}_variant",
                help=(
                    "Lean FIRE: minimal lifestyle (70% of expenses). "
                    "Regular FIRE: same lifestyle (4% rule). "
                    "Fat FIRE: upgraded lifestyle (3% rule). "
                    "Coast FIRE: grow to target without new contributions. "
                    "Barista FIRE: part-time work covers some expenses."
                ),
            )

        # Conditional input: Barista FIRE part-time income
        barista_income = 0.0
        if fire_variant == "Barista FIRE":
            barista_label = (
                f"Expected annual part-time income in semi-retirement ({cur_code})"
                if use_local else
                "Expected annual part-time income in semi-retirement (USD)"
            )
            barista_income = st.number_input(
                barista_label,
                min_value=0.0,
                max_value=float(annual_expenses_input),
                value=float(round(annual_expenses_input * 0.30, -2)),
                step=float(max(500.0, round(_to_input_currency(500.0), -2))),
                key=f"{widget_key}_barista",
                help=(
                    "Annual income from part-time work, freelancing, or side income "
                    "during semi-retirement. This reduces the portfolio size you need."
                ),
            )

        # ------------------------------------------------------------------
        # Inputs -- Section 3: Investment Return Assumption
        # ------------------------------------------------------------------
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:12px 0 4px;letter-spacing:0.04em;'>"
            "Investment Return Assumption"
            "</div>",
            unsafe_allow_html=True,
        )

        return_rate_label = st.radio(
            "Expected portfolio return profile",
            list(_RETURN_RATES.keys()),
            index=1,    # default: Moderate
            key=f"{widget_key}_return",
            horizontal=True,
            help=(
                "Nominal (pre-inflation) annual return. "
                "Real return = nominal minus 3% inflation assumption. "
                "Historical US equity average is ~10% nominal; 7% real."
            ),
        )

        # ------------------------------------------------------------------
        # Compute
        # ------------------------------------------------------------------
        current_portfolio = _from_input_currency(float(current_portfolio_input))
        annual_contribution_input_usd = _from_input_currency(float(annual_contribution_input))
        annual_expenses_input_usd = _from_input_currency(float(annual_expenses_input))
        barista_income_usd = _from_input_currency(float(barista_income))

        result = compute_fire(
            annual_expenses_usd=annual_expenses_input_usd,
            current_portfolio_usd=current_portfolio,
            annual_contribution_usd=annual_contribution_input_usd,
            fire_variant=fire_variant,
            return_rate_label=return_rate_label,
            barista_part_time_income_usd=barista_income_usd,
            coast_target_age=int(target_retirement_age),
            current_age=int(current_age),
        )

        st.divider()

        # ------------------------------------------------------------------
        # FIRE variant description card
        # ------------------------------------------------------------------
        variant_desc = {
            "Lean FIRE":    "Minimal lifestyle with 70% of current expenses. Requires a smaller portfolio but demands strict spending discipline.",
            "Regular FIRE": "Retire at your current lifestyle. Uses the classic 4% safe withdrawal rule (25x annual expenses).",
            "Fat FIRE":     "Retire with an upgraded lifestyle at 150% of current expenses. Uses 3% withdrawal rate (33x expenses).",
            "Coast FIRE":   "Invest enough now so your portfolio grows to your FIRE number by retirement age without additional contributions.",
            "Barista FIRE": "Semi-retire with part-time income covering some expenses. Reduces the portfolio size required.",
        }
        variant_colors = {
            "Lean FIRE":    "#F59E0B",
            "Regular FIRE": "#3B82F6",
            "Fat FIRE":     "#8B5CF6",
            "Coast FIRE":   "#22C55E",
            "Barista FIRE": "#EC4899",
        }
        v_color = variant_colors.get(fire_variant, "#3B82F6")
        st.markdown(
            f"<div style='background:{_COLORS['bg_card']};"
            f"border:1px solid {_COLORS['border']};border-left:5px solid {v_color};"
            f"border-radius:10px;padding:12px 16px;margin:6px 0;font-size:13px;"
            f"color:{_COLORS['subtext']};'>"
            f"<span style='font-weight:700;color:{v_color};font-size:14px;'>"
            f"{fire_variant}</span><br>"
            f"{variant_desc.get(fire_variant, '')}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # FIRE Number and headline metrics
        # ------------------------------------------------------------------
        already = result["is_already_fire"]
        max_hit = result["max_years_hit"]

        if fire_variant == "Coast FIRE":
            effective_target = result["coast_number"]
            target_label = "Coast FIRE Number"
            progress_label = "Coast Progress"
        else:
            effective_target = result["fire_number"]
            target_label = f"{fire_variant} Number"
            progress_label = "FIRE Progress"

        progress_pct = min(100.0, (current_portfolio / effective_target) * 100) if effective_target > 0 else 0

        col_a, col_b, col_c = st.columns(3)

        if fire_variant == "Coast FIRE":
            col_a.metric(
                "Full FIRE Number",
                _loc(result["fire_number"]),
                help="25x annual expenses -- your eventual full-retirement target.",
            )
            col_b.metric(
                "Coast FIRE Number",
                _loc(result["coast_number"]),
                help=(
                    "Amount you need invested today so it grows to the FIRE Number "
                    f"by age {target_retirement_age} without further contributions."
                ),
            )
        else:
            col_a.metric(
                target_label,
                _loc(effective_target),
                help=f"Portfolio size needed to retire at {result['withdrawal_rate']*100:.0f}% withdrawal.",
            )
            col_b.metric(
                "Current Portfolio",
                _loc(current_portfolio),
                delta=f"{progress_pct:.1f}% of target",
                delta_color="normal",
            )

        if already:
            col_c.metric("Status", "You are FIRE!", help="Your portfolio already exceeds your FIRE number.")
        elif max_hit:
            col_c.metric("Years to FIRE", "80+ yrs", help="Projection exceeded 80 years. Increase contributions or reduce expenses.")
        else:
            col_c.metric(
                "Years to FIRE",
                f"{result['years_to_fire']} yrs",
                delta=f"Retire at age {result['fire_age']}",
                delta_color="normal",
            )

        # FIRE number headline card
        if already:
            headline_color = _COLORS["green"]
            headline_val = "Financial Independence Reached"
            headline_sub = f"Portfolio {_loc(current_portfolio)} exceeds {fire_variant} number {_loc(effective_target)}"
        elif max_hit:
            headline_color = _COLORS["red"]
            headline_val = "Goal not reachable within 80 years"
            headline_sub = "Increase annual contributions or reduce target expenses."
        else:
            headline_color = v_color
            headline_val = f"Retire in {result['years_to_fire']} years at age {result['fire_age']}"
            headline_sub = (
                f"{fire_variant} Number: {_loc(effective_target)} "
                f"| Real return: {result['real_return']*100:.1f}% per year"
            )
        st.markdown(
            _stat_card(headline_val, f"{fire_variant} Target", headline_color, headline_sub),
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # Progress bar
        # ------------------------------------------------------------------
        st.markdown(
            f"<div style='margin:12px 0 4px;font-size:13px;color:{_COLORS['muted']};'>"
            f"{progress_label}: "
            f"<span style='color:{_COLORS['text']};font-weight:700;'>{progress_pct:.1f}%</span> of target reached"
            f"</div>",
            unsafe_allow_html=True,
        )
        filled = max(2, int(progress_pct * 3.5))
        empty = max(0, 350 - filled)
        bar_color = headline_color if not max_hit else _COLORS["red"]
        st.markdown(
            f"<div style='display:flex;align-items:center;margin-bottom:10px;'>"
            f"<div style='width:{filled}px;height:14px;background:{bar_color};"
            f"border-radius:7px 0 0 7px;'></div>"
            f"<div style='width:{empty}px;height:14px;background:#1E2D40;"
            f"border-radius:0 7px 7px 0;'></div>"
            f"<span style='margin-left:10px;font-size:12px;color:{_COLORS['muted']};'>"
            f"{_loc(current_portfolio)} / {_loc(effective_target)}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # Key figures table
        # ------------------------------------------------------------------
        st.divider()
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:8px 0;'>Key Figures</div>",
            unsafe_allow_html=True,
        )
        rows_html = (
            _info_row("Annual expenses (current)", _loc(annual_expenses_input_usd))
            + _info_row("Target annual expenses in retirement", _loc(result["target_expenses"]))
            + _info_row("Safe withdrawal rate", f"{result['withdrawal_rate']*100:.0f}%")
            + _info_row("Assumed nominal return", f"{result['nominal_return']*100:.0f}%")
            + _info_row("Assumed inflation", "3.0%")
            + _info_row("Real (inflation-adjusted) return", f"{result['real_return']*100:.1f}%")
            + _info_row("Annual investment contribution", _loc(annual_contribution_input_usd))
        )
        if fire_variant == "Barista FIRE" and barista_income_usd > 0:
            rows_html += _info_row(
                "Part-time income in semi-retirement",
                _loc(barista_income_usd),
                color=variant_colors["Barista FIRE"],
            )
        if fire_variant == "Coast FIRE":
            rows_html += (
                _info_row("Full FIRE Number", _loc(result["fire_number"]))
                + _info_row(
                    f"Coast FIRE Number (reach by age {target_retirement_age})",
                    _loc(result["coast_number"]),
                    color=_COLORS["green"],
                )
            )
        st.markdown(
            f"<div style='background:{_COLORS['bg_card']};"
            f"border:1px solid {_COLORS['border']};border-radius:10px;"
            f"padding:12px 16px;'>{rows_html}</div>",
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # Milestones
        # ------------------------------------------------------------------
        milestones = result.get("milestone_years", {})
        if milestones and not already:
            st.divider()
            st.markdown(
                "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
                "margin:8px 0;'>Portfolio Milestones</div>",
                unsafe_allow_html=True,
            )
            m_cols = st.columns(len(milestones))
            pct_colors = {"25%": "#F59E0B", "50%": "#3B82F6", "75%": "#8B5CF6", "100%": _COLORS["green"]}
            for i, (pct_label, yrs) in enumerate(milestones.items()):
                age_at = current_age + yrs
                m_cols[i].metric(
                    f"{pct_label} of {fire_variant} Number",
                    f"Year {yrs}",
                    delta=f"Age {age_at}",
                    delta_color="normal",
                    help=f"You reach {pct_label} of your {fire_variant} number in year {yrs} (age {age_at}).",
                )

        # ------------------------------------------------------------------
        # Portfolio growth chart
        # ------------------------------------------------------------------
        st.divider()
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:8px 0;'>Portfolio Growth Projection</div>",
            unsafe_allow_html=True,
        )

        by_year = result["portfolio_by_year"]
        years_list = [d["year"] for d in by_year]
        portfolios_usd = [d["portfolio"] for d in by_year]

        # Apply fx conversion for display
        portfolios_display = [v * fx_rate for v in portfolios_usd]
        fire_line = [effective_target * fx_rate] * len(years_list)
        fire_full_line = [result["fire_number"] * fx_rate] * len(years_list)

        currency_label = cur_code if use_local else "USD"

        fig = go.Figure()

        # Portfolio area
        fig.add_trace(go.Scatter(
            x=years_list,
            y=portfolios_display,
            name="Portfolio Value",
            mode="lines",
            line=dict(color=v_color, width=2.5),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(v_color, 0.08),
            hovertemplate=f"Year %{{x}}<br>Portfolio: {cur_sym}%{{y:,.0f}}<extra></extra>",
        ))

        # FIRE target line
        fig.add_trace(go.Scatter(
            x=years_list,
            y=fire_line,
            name=f"{fire_variant} Number",
            mode="lines",
            line=dict(color=headline_color, width=1.5, dash="dash"),
            hovertemplate=f"{fire_variant} Number: {cur_sym}%{{y:,.0f}}<extra></extra>",
        ))

        # For Coast FIRE, also show the full FIRE number
        if fire_variant == "Coast FIRE":
            fig.add_trace(go.Scatter(
                x=years_list,
                y=fire_full_line,
                name="Full FIRE Number",
                mode="lines",
                line=dict(color=_COLORS["muted"], width=1, dash="dot"),
                hovertemplate=f"Full FIRE: {cur_sym}%{{y:,.0f}}<extra></extra>",
            ))

        # Mark FIRE year
        if not already and not max_hit and result["years_to_fire"] <= len(years_list) - 1:
            fire_yr = result["years_to_fire"]
            fire_val = portfolios_display[fire_yr] if fire_yr < len(portfolios_display) else fire_line[0]
            fig.add_trace(go.Scatter(
                x=[fire_yr],
                y=[fire_val],
                name="FIRE Achieved",
                mode="markers",
                marker=dict(color=_COLORS["green"], size=12, symbol="star"),
                hovertemplate=f"FIRE Achieved: Year {fire_yr}, Age {current_age + fire_yr}<extra></extra>",
            ))

        fig.update_layout(
            title_text="",
            xaxis_title="Years from now",
            yaxis_title=f"Portfolio Value ({currency_label})",
            margin=dict(l=0, r=0, t=10, b=0),
            height=380,
            hovermode="x unified",
        )
        fig.update_yaxes(tickformat=",")
        apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

        # ------------------------------------------------------------------
        # FIRE variant comparison table
        # ------------------------------------------------------------------
        st.divider()
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:8px 0;'>FIRE Variant Comparison</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "All variants computed with your inputs. Coast and Barista use the same portfolio / contributions."
        )

        compare_rows = []
        for v_name in _WITHDRAWAL_RATES.keys():
            v_res = compute_fire(
                annual_expenses_usd=annual_expenses_input_usd,
                current_portfolio_usd=current_portfolio,
                annual_contribution_usd=annual_contribution_input_usd,
                fire_variant=v_name,
                return_rate_label=return_rate_label,
                barista_part_time_income_usd=barista_income_usd,
                coast_target_age=int(target_retirement_age),
                current_age=int(current_age),
            )
            v_target = v_res["coast_number"] if v_name == "Coast FIRE" else v_res["fire_number"]
            v_pct = min(100.0, (current_portfolio / v_target) * 100) if v_target > 0 else 0
            status = "Already FIRE" if v_res["is_already_fire"] else (
                "80+ years" if v_res["max_years_hit"] else f"{v_res['years_to_fire']} yrs (age {v_res['fire_age']})"
            )
            compare_rows.append({
                "Variant":        v_name,
                "Target Number":  _loc(v_target),
                "Progress":       f"{v_pct:.1f}%",
                "Years to FIRE":  status,
            })

        import pandas as pd
        compare_df = pd.DataFrame(compare_rows)
        st.dataframe(
            compare_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Variant":       st.column_config.TextColumn("Variant", width="medium"),
                "Target Number": st.column_config.TextColumn("Target Number", width="medium"),
                "Progress":      st.column_config.TextColumn("Progress", width="small"),
                "Years to FIRE": st.column_config.TextColumn("Years / Age", width="medium"),
            },
        )

        # ------------------------------------------------------------------
        # Sensitivity: years to FIRE vs contribution amount
        # ------------------------------------------------------------------
        st.divider()
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:8px 0;'>Sensitivity: Contribution vs. Years to FIRE</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "How changing your annual investment contribution affects your timeline. "
            "Other inputs held constant."
        )

        base_contrib = annual_contribution_input_usd or 1.0
        contrib_range = [base_contrib * m for m in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]]
        contrib_labels = [_loc(c) for c in contrib_range]
        contrib_years = []
        for c in contrib_range:
            cr = compute_fire(
                annual_expenses_usd=annual_expenses_input_usd,
                current_portfolio_usd=current_portfolio,
                annual_contribution_usd=c,
                fire_variant=fire_variant,
                return_rate_label=return_rate_label,
                barista_part_time_income_usd=barista_income_usd,
                coast_target_age=int(target_retirement_age),
                current_age=int(current_age),
            )
            contrib_years.append(cr["years_to_fire"] if not cr["max_years_hit"] else 80)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=contrib_labels,
            y=contrib_years,
            marker_color=[
                _COLORS["green"] if y == min(contrib_years) else v_color
                for y in contrib_years
            ],
            text=[f"{y} yrs" for y in contrib_years],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="Contribution: %{x}<br>Years to FIRE: %{y}<extra></extra>",
        ))
        # Mark current selection
        current_idx = 2   # index of 1.0x multiplier
        fig2.add_vline(
            x=current_idx,
            line_dash="dot",
            line_color=_COLORS["amber"],
            annotation_text="Current",
            annotation_font_color=_COLORS["amber"],
            annotation_position="top",
        )
        fig2.update_layout(
            title_text="",
            xaxis_title="Annual Contribution",
            yaxis_title="Years to FIRE",
            margin=dict(l=0, r=0, t=24, b=0),
            height=330,
        )
        fig2.update_yaxes(range=[0, max(contrib_years) * 1.15 if contrib_years else 1])
        apply_theme(fig2)
        st.plotly_chart(fig2, use_container_width=True)

        # ------------------------------------------------------------------
        # Expense sensitivity
        # ------------------------------------------------------------------
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:8px 0;'>Sensitivity: Annual Expenses vs. Years to FIRE</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "How changing your annual expenses affects your timeline. "
            "A lower expense level reduces your FIRE number and accelerates retirement."
        )

        base_exp = annual_expenses_input_usd or 1.0
        exp_mults = [0.60, 0.75, 0.90, 1.0, 1.15, 1.30]
        exp_range = [base_exp * m for m in exp_mults]
        exp_labels = [f"{int(m*100)}% ({_loc(e)})" for m, e in zip(exp_mults, exp_range)]
        exp_years = []
        for e in exp_range:
            er = compute_fire(
                annual_expenses_usd=e,
                current_portfolio_usd=current_portfolio,
                annual_contribution_usd=annual_contribution_input_usd,
                fire_variant=fire_variant,
                return_rate_label=return_rate_label,
                barista_part_time_income_usd=barista_income_usd,
                coast_target_age=int(target_retirement_age),
                current_age=int(current_age),
            )
            exp_years.append(er["years_to_fire"] if not er["max_years_hit"] else 80)

        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=exp_labels,
            y=exp_years,
            marker_color=[
                _COLORS["green"] if y == min(exp_years) else v_color
                for y in exp_years
            ],
            text=[f"{y} yrs" for y in exp_years],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="Expenses: %{x}<br>Years to FIRE: %{y}<extra></extra>",
        ))
        current_exp_idx = 3   # 1.0x
        fig3.add_vline(
            x=current_exp_idx,
            line_dash="dot",
            line_color=_COLORS["amber"],
            annotation_text="Current",
            annotation_font_color=_COLORS["amber"],
            annotation_position="top",
        )
        fig3.update_layout(
            title_text="",
            xaxis_title="Annual Expenses (% of current)",
            yaxis_title="Years to FIRE",
            margin=dict(l=0, r=0, t=24, b=0),
            height=330,
        )
        fig3.update_yaxes(range=[0, max(exp_years) * 1.15 if exp_years else 1])
        apply_theme(fig3)
        st.plotly_chart(fig3, use_container_width=True)

        # ------------------------------------------------------------------
        # Actionable insights
        # ------------------------------------------------------------------
        st.divider()
        st.markdown(
            "<div style='font-size:14px;font-weight:700;color:#C8D6E8;"
            "margin:8px 0;'>Actionable Insights</div>",
            unsafe_allow_html=True,
        )

        insights = []
        years = result["years_to_fire"]
        contrib_rate = (annual_contribution_input_usd / annual_salary_usd * 100) if annual_salary_usd else 0

        if already:
            insights.append(("green",
                "Your portfolio already exceeds your FIRE number. "
                "Consider validating your withdrawal strategy with a fee-only financial planner."))
        elif max_hit:
            insights.append(("red",
                "At the current contribution level your target cannot be reached within 80 years. "
                "Increasing contributions or reducing expenses will have the largest impact."))
        else:
            if years <= 10:
                insights.append(("green",
                    f"You are on an accelerated FIRE path ({years} years). "
                    "Focus on sequence-of-returns risk as you approach retirement."))
            elif years <= 20:
                insights.append(("blue",
                    f"A {years}-year timeline is well within reach. "
                    "Consistency and avoiding lifestyle inflation are your main levers."))
            else:
                insights.append(("amber",
                    f"A {years}-year timeline gives you room to optimize. "
                    "Every additional 10% in savings rate can shorten the path by several years."))

        if contrib_rate < 10 and not already:
            insights.append(("amber",
                f"Your contribution rate is {contrib_rate:.1f}% of gross salary. "
                "The FIRE community typically targets 25-50% savings rates for faster timelines."))
        elif contrib_rate >= 30:
            insights.append(("green",
                f"A {contrib_rate:.1f}% contribution rate is strong. "
                "Ensure contributions are in tax-advantaged accounts where available."))

        if fire_variant == "Fat FIRE":
            insights.append(("blue",
                "Fat FIRE requires a significantly larger portfolio. "
                "Geographic arbitrage or income diversification can help close the gap."))

        if fire_variant == "Coast FIRE" and current_portfolio >= result["coast_number"]:
            insights.append(("green",
                "You have already reached your Coast FIRE number. "
                "Your current portfolio will grow to the full FIRE number by your target age "
                "without further contributions."))

        insight_colors = {
            "green": _COLORS["green"],
            "blue":  _COLORS["accent"],
            "amber": _COLORS["amber"],
            "red":   _COLORS["red"],
        }
        insights_html = "".join(
            f"<div style='border-left:4px solid {insight_colors.get(c,'#3B82F6')};"
            f"padding:8px 12px;margin:6px 0;background:#1A2535;"
            f"border-radius:0 6px 6px 0;font-size:13px;color:{_COLORS['subtext']};'>"
            f"{txt}</div>"
            for c, txt in insights
        )
        st.markdown(insights_html, unsafe_allow_html=True)

        # ------------------------------------------------------------------
        # Disclaimer
        # ------------------------------------------------------------------
        st.caption(
            "FIRE projections assume constant real returns and do not account for "
            "sequence-of-returns risk, taxes on withdrawals, healthcare costs, "
            "or changes in lifestyle. The 4% rule is a US-historical guideline and "
            "may not apply in all countries or market conditions. "
            "This is not financial advice. Consult a qualified financial planner."
        )

    return result
