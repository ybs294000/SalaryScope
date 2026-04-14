"""
budget_utils.py -- SalaryScope Budget Planner
==============================================
Breaks down a monthly net income into recommended budget category allocations
using country-adjusted cost-of-living benchmarks. Based on widely-used
envelope budgeting principles (e.g. 50/30/20 adapted per region).

Answers the question: "Where should my money ideally go each month?"

IMPORTANT DISCLAIMER
--------------------
Budget allocations are illustrative benchmarks for a typical middle-income
urban household. Individual needs vary significantly based on family size,
rent levels, debt obligations, healthcare requirements, and personal goals.
This is not financial advice.

Design
------
- Completely standalone: works with or without savings_utils, loan_utils,
  tax_utils, takehome_utils, col_utils, currency_utils, or any other
  SalaryScope module.
- `compute_budget_allocation(net_monthly_usd, country, ...)` -- pure-math
  core, no Streamlit dependency, safe to call from any tab or utility.
- `render_budget_planner(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_savings_adjuster / render_loan_adjuster interface.

Integration
-----------
    from budget_utils import render_budget_planner

    render_budget_planner(
        net_monthly_usd=net_monthly,
        location_hint=country,
        widget_key="manual_a1_budget",
        gross_usd=prediction,
    )

Pure-math usage:
    from budget_utils import compute_budget_allocation

    result = compute_budget_allocation(net_monthly_usd=5000, country="IN")
    for cat in result["categories"]:
        print(cat["label"], cat["amount_usd"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Country-level housing cost fraction of net income.
# Higher housing costs compress other category ratios proportionally.
# Sources: Numbeo 2023/24, World Bank urban household surveys.
# ---------------------------------------------------------------------------
_HOUSING_RATIO: dict[str, float] = {
    # North America
    "US": 0.30,
    "CA": 0.28,
    "MX": 0.22,
    # Europe
    "GB": 0.30,
    "DE": 0.26,
    "FR": 0.26,
    "CH": 0.28,
    "NL": 0.26,
    "BE": 0.24,
    "AT": 0.26,
    "SE": 0.24,
    "NO": 0.24,
    "DK": 0.24,
    "FI": 0.24,
    "IE": 0.28,
    "ES": 0.24,
    "PT": 0.24,
    "IT": 0.26,
    "GR": 0.24,
    "PL": 0.22,
    "CZ": 0.22,
    "HU": 0.22,
    "RO": 0.20,
    "TR": 0.24,
    "UA": 0.20,
    "RU": 0.20,
    # Middle East
    "AE": 0.28,
    "QA": 0.26,
    "SA": 0.22,
    "KW": 0.22,
    "BH": 0.24,
    "OM": 0.24,
    "IL": 0.30,
    "JO": 0.24,
    # South Asia
    "IN": 0.18,
    "PK": 0.20,
    "BD": 0.20,
    "LK": 0.20,
    "NP": 0.18,
    # East / Southeast Asia
    "JP": 0.28,
    "KR": 0.24,
    "CN": 0.24,
    "HK": 0.36,
    "TW": 0.24,
    "SG": 0.28,
    "MY": 0.22,
    "TH": 0.22,
    "VN": 0.20,
    "PH": 0.22,
    "ID": 0.20,
    "MM": 0.22,
    # Oceania
    "AU": 0.28,
    "NZ": 0.28,
    # Africa
    "ZA": 0.24,
    "NG": 0.24,
    "KE": 0.22,
    "GH": 0.22,
    "EG": 0.20,
    "MA": 0.22,
    "ET": 0.20,
    "TZ": 0.20,
    # Latin America
    "BR": 0.26,
    "AR": 0.24,
    "CL": 0.24,
    "CO": 0.22,
    "PE": 0.22,
    "BO": 0.20,
    "UY": 0.22,
    "CR": 0.22,
    "DO": 0.22,
    "PA": 0.22,
    "EC": 0.22,
}
_HOUSING_RATIO_FALLBACK = 0.25

# Fixed relative weights for remaining budget categories (after housing).
# These are blended across all remaining spend before applying country housing.
_CATEGORY_TEMPLATE = [
    # (id, label, base_fraction_of_non_housing, icon, color)
    ("food",        "Food & Groceries",    0.25, ":material/restaurant:",      "#F59E0B"),
    ("transport",   "Transport",           0.12, ":material/directions_car:",  "#3B82F6"),
    ("utilities",   "Utilities & Bills",   0.08, ":material/bolt:",            "#6366F1"),
    ("health",      "Health & Wellness",   0.08, ":material/health_and_safety:","#EF4444"),
    ("personal",    "Personal & Family",   0.10, ":material/person:",          "#A78BFA"),
    ("leisure",     "Leisure & Dining",    0.10, ":material/local_activity:",  "#EC4899"),
    ("education",   "Education & Growth",  0.07, ":material/school:",          "#22D3EE"),
    ("savings",     "Savings & Investing", 0.15, ":material/savings:",         "#22C55E"),
    ("emergency",   "Emergency Fund",      0.05, ":material/shield:",          "#34D399"),
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


def _bar_row(label: str, amount_str: str, pct: float, color: str, icon: str) -> str:
    bar_w = max(4, int(pct * 1.8))
    return (
        f"<div style='margin:5px 0;display:flex;align-items:center;gap:8px;'>"
        f"<span style='width:160px;color:#9CA6B5;font-size:13px;white-space:nowrap;'>"
        f"{label}</span>"
        f"<span style='display:inline-block;background:{color};"
        f"width:{bar_w}px;height:12px;border-radius:3px;'></span>"
        f"<span style='color:#E6EAF0;font-size:13px;'>{amount_str} ({pct:.1f}%)</span>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit dependency
# ---------------------------------------------------------------------------

def compute_budget_allocation(
    net_monthly_usd: float,
    country: Optional[str] = None,
    custom_housing_ratio: Optional[float] = None,
    overrides: Optional[dict] = None,
) -> dict:
    """
    Compute a recommended monthly budget allocation.

    Parameters
    ----------
    net_monthly_usd      : Monthly net (post-tax) income in USD.
    country              : ISO-2 code or country name for housing cost default.
    custom_housing_ratio : Override housing fraction (0.0 -- 0.6).
    overrides            : Dict of {category_id: fraction} overrides for any
                           non-housing category. Fractions refer to net income.
                           Remaining income is distributed proportionally to
                           non-overridden categories.

    Returns
    -------
    dict with keys:
        net_monthly     -- input net monthly income
        housing_ratio   -- fraction allocated to housing
        housing_amount  -- absolute housing amount in USD
        categories      -- list of dicts, each with:
                             id, label, fraction, amount_usd, icon, color
        total_allocated -- sum of all category amounts (should equal net_monthly)
    """
    if net_monthly_usd <= 0:
        return {"net_monthly": net_monthly_usd, "housing_ratio": 0.0,
                "housing_amount": 0.0, "categories": [], "total_allocated": 0.0}

    key = _resolve_key(country, _HOUSING_RATIO)
    h_ratio = (
        custom_housing_ratio
        if custom_housing_ratio is not None
        else _HOUSING_RATIO.get(key or "", _HOUSING_RATIO_FALLBACK)
    )
    h_ratio = min(max(h_ratio, 0.0), 0.70)
    housing_amount = net_monthly_usd * h_ratio
    remainder = net_monthly_usd - housing_amount

    overrides = overrides or {}

    # Sum of base weights for non-overridden categories
    total_base = sum(
        w for cid, _, w, _, _ in _CATEGORY_TEMPLATE
        if cid not in overrides
    )

    categories = []
    allocated_non_housing = 0.0
    for cid, label, base_w, icon, color in _CATEGORY_TEMPLATE:
        if cid in overrides:
            frac_of_net = float(overrides[cid])
            amount = net_monthly_usd * frac_of_net
        else:
            scaled_w = base_w / total_base if total_base > 0 else 0.0
            amount = remainder * scaled_w
            frac_of_net = amount / net_monthly_usd if net_monthly_usd > 0 else 0.0
        allocated_non_housing += amount
        categories.append({
            "id": cid,
            "label": label,
            "fraction": frac_of_net,
            "amount_usd": amount,
            "icon": icon,
            "color": color,
        })

    # Housing entry prepended
    housing_cat = {
        "id": "housing",
        "label": "Housing & Rent",
        "fraction": h_ratio,
        "amount_usd": housing_amount,
        "icon": ":material/home:",
        "color": "#F97316",
    }

    return {
        "net_monthly": net_monthly_usd,
        "housing_ratio": h_ratio,
        "housing_amount": housing_amount,
        "categories": [housing_cat] + categories,
        "total_allocated": housing_amount + allocated_non_housing,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_budget_planner(
    net_monthly_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "budget",
    gross_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Monthly Budget Planner panel.

    Parameters
    ----------
    net_monthly_usd : Monthly net (post-tax) income in USD.
                      Pipe in from takehome_utils.render_takehome_adjuster()
                      for best results, or compute from gross as a fallback.
    location_hint   : ISO-2 country code or country name.
    widget_key      : Unique key prefix per call-site (e.g. "manual_a1_budget").
                      Must differ for every place this is called.
    gross_usd       : Optional gross annual salary -- shown as context only.

    Returns
    -------
    dict -- the compute_budget_allocation result.
    Returns an empty dict if widget is hidden or income is invalid.
    """
    if not net_monthly_usd or net_monthly_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/account_balance_wallet: Monthly Budget Planner",
        key=toggle_key,
        value=False,
        help="Break down your monthly income into recommended budget categories.",
    )
    if not show:
        return {}

    with st.expander(":material/account_balance_wallet: Monthly Budget Planner", expanded=True):
        st.caption(
            ":material/info: Distributes your net monthly income across standard budget "
            "categories using country-adjusted cost-of-living benchmarks. "
            "Override any category to match your actual spending. This is not financial advice."
        )

        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        key = _resolve_key(location_hint, _HOUSING_RATIO)
        d_housing = _HOUSING_RATIO.get(key or "", _HOUSING_RATIO_FALLBACK)

        if location_hint and location_hint not in ("", "Other"):
            gross_part = (
                f" &nbsp;&middot;&nbsp; "
                f"<span style='color:#9CA6B5;'>Annual gross:</span>"
                f" <b>{_loc(gross_usd)}</b>"
                if gross_usd else ""
            )
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #F97316;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#C8D6E8;'>"
                f"<span style='font-weight:700;color:#E6EAF0;'>Country:</span> "
                f"{_country_name(location_hint)}<br>"
                f"<span style='color:#9CA6B5;'>Default housing ratio:</span>"
                f" <b>{_pct(d_housing)} of net income</b>"
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
                "No country detected -- using generic 25% housing ratio. "
                "Override below for more accurate results."
                "</div>",
                unsafe_allow_html=True,
            )

        use_custom = st.toggle(
            "Override budget inputs",
            key=f"{widget_key}_custom",
            value=False,
            help="Adjust housing ratio and individual category allocations.",
        )

        custom_housing_ratio = None
        overrides = {}

        if use_custom:
            custom_housing_ratio = st.slider(
                "Housing & Rent (% of net income)",
                min_value=5, max_value=60,
                value=int(d_housing * 100),
                step=1,
                key=f"{widget_key}_housing",
                help=(
                    "Fraction of net income spent on rent, mortgage, or accommodation. "
                    "This is usually the single largest expense category."
                ),
            ) / 100.0

            st.markdown("**Override other categories (% of net income, 0 = use default)**")
            cols = st.columns(3)
            cat_ids = [cid for cid, _, _, _, _ in _CATEGORY_TEMPLATE]
            cat_labels = {cid: lbl for cid, lbl, _, _, _ in _CATEGORY_TEMPLATE}
            for i, cid in enumerate(cat_ids):
                with cols[i % 3]:
                    val = st.number_input(
                        cat_labels[cid],
                        min_value=0.0,
                        max_value=50.0,
                        value=0.0,
                        step=0.5,
                        key=f"{widget_key}_cat_{cid}",
                        help=f"Override allocation for {cat_labels[cid]}. Set 0 to keep auto-calculated.",
                    )
                    if val > 0:
                        overrides[cid] = val / 100.0

        result = compute_budget_allocation(
            net_monthly_usd,
            country=location_hint,
            custom_housing_ratio=custom_housing_ratio,
            overrides=overrides if overrides else None,
        )

        st.divider()

        label_suffix = f"({cur_code})" if use_local else "(USD)"
        st.markdown(
            _card(
                _loc(net_monthly_usd),
                f"MONTHLY NET INCOME {label_suffix}",
                color="#3E7DE0",
            ),
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown("**Budget Allocation Breakdown**")

        bars_html = ""
        for cat in result["categories"]:
            bars_html += _bar_row(
                cat["label"],
                _loc(cat["amount_usd"]),
                cat["fraction"] * 100,
                cat["color"],
                cat["icon"],
            )
        st.markdown(bars_html, unsafe_allow_html=True)

        st.divider()
        st.markdown("**Category Details**")
        col_a, col_b, col_c = st.columns(3)
        cols_cycle = [col_a, col_b, col_c]
        for idx, cat in enumerate(result["categories"]):
            cols_cycle[idx % 3].metric(
                cat["label"],
                _loc(cat["amount_usd"]),
                delta=f"{cat['fraction'] * 100:.1f}% of income",
                delta_color="off",
            )

        st.caption(
            "Housing ratio defaults use Numbeo / World Bank 2023/24 country benchmarks. "
            "Remaining categories are scaled from a 50/30/20 envelope model. "
            "Individual allocations depend heavily on family size, location, and lifestyle."
        )

    return result
