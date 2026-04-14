"""
lifestyle_utils.py -- SalaryScope Lifestyle Budget Split
=========================================================
Takes the discretionary remainder after essential expenses and splits it
across lifestyle spending tiers and categories. Focuses on how a person
chooses to spend their free cash rather than mapping all income to obligations.

Answers the question: "How should I split my discretionary income across
lifestyle choices, and what does each lifestyle tier look like for my income
in my country?"

IMPORTANT DISCLAIMER
--------------------
Lifestyle cost benchmarks are country-level approximations for a single urban
professional. Actual spending depends on personal preferences, family size,
and local market conditions. This is not financial advice.

Design
------
- Completely standalone: works with or without savings_utils, loan_utils,
  budget_utils, investment_utils, emergency_fund_utils, or any other module.
- `compute_lifestyle_split(net_monthly_usd, country, ...)` -- pure-math core,
  no Streamlit dependency, safe to call from any tab or utility.
- `render_lifestyle_split(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_savings_adjuster / render_loan_adjuster interface pattern.

Integration
-----------
    from lifestyle_utils import render_lifestyle_split

    render_lifestyle_split(
        net_monthly_usd=net_monthly,
        location_hint=country,
        widget_key="manual_a1_lifestyle",
        gross_usd=prediction,
    )

    # Best practice: pipe net_monthly from takehome_utils:
    from takehome_utils import render_takehome_adjuster
    from lifestyle_utils import render_lifestyle_split

    th = render_takehome_adjuster(gross_usd=prediction, ...)
    render_lifestyle_split(
        net_monthly_usd=th.get("net_monthly", prediction / 12), ...
    )

Pure-math usage:
    from lifestyle_utils import compute_lifestyle_split

    result = compute_lifestyle_split(net_monthly_usd=5000, country="IN")
    for tier in result["tiers"]:
        print(tier["label"], tier["monthly_cost"])
    for cat in result["discretionary_categories"]:
        print(cat["label"], cat["amount_usd"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Country-level essential expense fraction of net income.
# This is what gets subtracted before the discretionary split begins.
# Sources: Numbeo 2023/24, World Bank urban household surveys.
# Intentionally slightly lower than savings_utils expense ratio because
# here we want to isolate controllable discretionary spend.
# ---------------------------------------------------------------------------
_ESSENTIAL_RATIO: dict[str, float] = {
    # North America
    "US": 0.55,
    "CA": 0.52,
    "MX": 0.50,
    # Europe
    "GB": 0.52,
    "DE": 0.46,
    "FR": 0.48,
    "CH": 0.48,
    "NL": 0.46,
    "BE": 0.46,
    "AT": 0.46,
    "SE": 0.44,
    "NO": 0.42,
    "DK": 0.44,
    "FI": 0.46,
    "IE": 0.52,
    "ES": 0.48,
    "PT": 0.46,
    "IT": 0.50,
    "GR": 0.50,
    "PL": 0.46,
    "CZ": 0.44,
    "HU": 0.46,
    "RO": 0.46,
    "TR": 0.54,
    "UA": 0.50,
    "RU": 0.50,
    # Middle East
    "AE": 0.44,
    "QA": 0.42,
    "SA": 0.44,
    "KW": 0.42,
    "BH": 0.44,
    "OM": 0.46,
    "IL": 0.54,
    "JO": 0.52,
    # South Asia
    "IN": 0.40,
    "PK": 0.48,
    "BD": 0.44,
    "LK": 0.44,
    "NP": 0.42,
    # East / Southeast Asia
    "JP": 0.54,
    "KR": 0.46,
    "CN": 0.44,
    "HK": 0.56,
    "TW": 0.48,
    "SG": 0.48,
    "MY": 0.46,
    "TH": 0.46,
    "VN": 0.44,
    "PH": 0.48,
    "ID": 0.46,
    "MM": 0.50,
    # Oceania
    "AU": 0.52,
    "NZ": 0.52,
    # Africa
    "ZA": 0.52,
    "NG": 0.56,
    "KE": 0.52,
    "GH": 0.54,
    "EG": 0.50,
    "MA": 0.50,
    "ET": 0.52,
    "TZ": 0.50,
    # Latin America
    "BR": 0.56,
    "AR": 0.54,
    "CL": 0.48,
    "CO": 0.50,
    "PE": 0.48,
    "BO": 0.48,
    "UY": 0.48,
    "CR": 0.48,
    "DO": 0.48,
    "PA": 0.46,
    "EC": 0.48,
}
_ESSENTIAL_RATIO_FALLBACK = 0.48

# ---------------------------------------------------------------------------
# Lifestyle tiers: frugal / balanced / comfortable / aspirational.
# Each tier defines how the discretionary remainder is distributed.
# Fractions below are relative weights within the discretionary pool.
# ---------------------------------------------------------------------------

# Discretionary category definitions shared across all tiers.
# (id, label, icon, color)
_DISC_CATEGORIES = [
    ("dining",        "Dining Out & Cafes",        ":material/restaurant:",         "#F59E0B"),
    ("leisure",       "Entertainment & Leisure",   ":material/local_activity:",     "#EC4899"),
    ("travel",        "Travel & Holidays",          ":material/flight:",             "#3B82F6"),
    ("shopping",      "Shopping & Clothing",        ":material/shopping_bag:",       "#A78BFA"),
    ("subscriptions", "Subscriptions & Streaming",  ":material/subscriptions:",      "#22D3EE"),
    ("fitness",       "Fitness & Sports",           ":material/fitness_center:",     "#34D399"),
    ("personal_care", "Personal Care & Grooming",   ":material/spa:",                "#F9A8D4"),
    ("hobbies",       "Hobbies & Interests",        ":material/palette:",            "#FCD34D"),
    ("gifts",         "Gifts & Social",             ":material/card_giftcard:",      "#6EE7B7"),
    ("buffer",        "Unplanned / Buffer",         ":material/shield:",             "#94A3B8"),
]

# Relative weights per tier for each category above.
# Must correspond positionally to _DISC_CATEGORIES.
_TIER_WEIGHTS = {
    "frugal":       [0.10, 0.10, 0.05, 0.08, 0.05, 0.12, 0.08, 0.12, 0.05, 0.25],
    "balanced":     [0.14, 0.13, 0.10, 0.10, 0.07, 0.10, 0.08, 0.10, 0.08, 0.10],
    "comfortable":  [0.16, 0.14, 0.16, 0.12, 0.08, 0.09, 0.08, 0.08, 0.07, 0.02],
    "aspirational": [0.16, 0.12, 0.24, 0.16, 0.08, 0.08, 0.07, 0.06, 0.03, 0.00],
}

# Tier metadata
_TIER_META = {
    "frugal": {
        "label": "Frugal",
        "color": "#22C55E",
        "description": (
            "Minimal discretionary spend. Prioritises savings and financial security. "
            "Suitable for debt payoff, building an emergency fund, or aggressive saving goals."
        ),
    },
    "balanced": {
        "label": "Balanced",
        "color": "#3B82F6",
        "description": (
            "Moderate lifestyle spending with a healthy mix of enjoyment and saving. "
            "A sustainable long-term approach for most income levels."
        ),
    },
    "comfortable": {
        "label": "Comfortable",
        "color": "#A78BFA",
        "description": (
            "Enjoys quality experiences, travel, and personal comfort regularly. "
            "Leaves limited room for rapid savings growth unless income is high."
        ),
    },
    "aspirational": {
        "label": "Aspirational",
        "color": "#F59E0B",
        "description": (
            "Premium lifestyle with frequent travel and high-end experiences. "
            "Requires a high income or acceptance of reduced savings rate."
        ),
    },
}

# Fraction of discretionary pool directed to savings for each tier
_TIER_SAVINGS_FRACTION = {
    "frugal":       0.40,
    "balanced":     0.25,
    "comfortable":  0.15,
    "aspirational": 0.05,
}


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


def _card(value_str: str, label: str, color: str = "#3B82F6") -> str:
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


def _tier_card(tier_id: str, meta: dict, monthly_disc: float,
               savings_amt: float, loc_fn, label_suffix: str) -> str:
    color = meta["color"]
    sav_frac = _TIER_SAVINGS_FRACTION[tier_id]
    spend_amt = monthly_disc * (1.0 - sav_frac)
    return (
        f"<div style='background:#1A2535;border:1px solid #2D3A50;"
        f"border-left:5px solid {color};border-radius:10px;"
        f"padding:14px 18px;margin:6px 0;'>"
        f"<div style='color:{color};font-size:15px;font-weight:700;"
        f"margin-bottom:4px;'>{meta['label']}</div>"
        f"<div style='color:#C8D6E8;font-size:13px;margin-bottom:6px;'>"
        f"{meta['description']}</div>"
        f"<div style='display:flex;gap:24px;font-size:13px;'>"
        f"<span style='color:#9CA6B5;'>Lifestyle spend: "
        f"<b style='color:#E6EAF0;'>{loc_fn(spend_amt)}/mo</b></span>"
        f"<span style='color:#9CA6B5;'>Savings from discretionary: "
        f"<b style='color:{color};'>{loc_fn(savings_amt * sav_frac / (sav_frac if sav_frac > 0 else 1))}/mo</b></span>"
        f"</div>"
        f"</div>"
    )


def _bar_row(label: str, amount_str: str, pct: float, color: str) -> str:
    bar_w = max(4, int(pct * 2.0))
    return (
        f"<div style='margin:5px 0;display:flex;align-items:center;gap:8px;'>"
        f"<span style='width:170px;color:#9CA6B5;font-size:13px;"
        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
        f"{label}</span>"
        f"<span style='display:inline-block;background:{color};"
        f"width:{bar_w}px;height:12px;border-radius:3px;'></span>"
        f"<span style='color:#E6EAF0;font-size:13px;'>"
        f"{amount_str} ({pct:.1f}%)</span>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit dependency
# ---------------------------------------------------------------------------

def compute_lifestyle_split(
    net_monthly_usd: float,
    country: Optional[str] = None,
    active_tier: str = "balanced",
    custom_essential_ratio: Optional[float] = None,
) -> dict:
    """
    Compute a lifestyle discretionary spending split.

    Parameters
    ----------
    net_monthly_usd        : Monthly net (post-tax) income in USD.
    country                : ISO-2 code or country name for essential ratio default.
    active_tier            : One of "frugal", "balanced", "comfortable", "aspirational".
    custom_essential_ratio : Override fraction of net income spent on essentials (0.0-0.90).

    Returns
    -------
    dict with keys:
        net_monthly             -- input net monthly income
        essential_ratio         -- fraction allocated to essentials
        essential_amount        -- essentials in USD
        discretionary_amount    -- remainder available for lifestyle + savings
        active_tier             -- tier id used
        tier_savings_amount     -- portion of discretionary directed to savings
        tier_spend_amount       -- portion directed to lifestyle spending
        discretionary_categories-- list of dicts, each with:
                                     id, label, fraction_of_disc,
                                     amount_usd, icon, color
        tiers                   -- summary of all four tiers for comparison,
                                   each with: id, label, color, description,
                                   monthly_disc_spend, monthly_disc_savings
    """
    if net_monthly_usd <= 0:
        return {
            "net_monthly": net_monthly_usd,
            "essential_ratio": 0.0,
            "essential_amount": 0.0,
            "discretionary_amount": 0.0,
            "active_tier": active_tier,
            "tier_savings_amount": 0.0,
            "tier_spend_amount": 0.0,
            "discretionary_categories": [],
            "tiers": [],
        }

    key = _resolve_key(country, _ESSENTIAL_RATIO)
    e_ratio = (
        float(custom_essential_ratio)
        if custom_essential_ratio is not None
        else _ESSENTIAL_RATIO.get(key or "", _ESSENTIAL_RATIO_FALLBACK)
    )
    e_ratio = min(max(e_ratio, 0.0), 0.90)
    essential_amt = net_monthly_usd * e_ratio
    disc_amt = max(0.0, net_monthly_usd - essential_amt)

    tier = active_tier if active_tier in _TIER_WEIGHTS else "balanced"
    weights = _TIER_WEIGHTS[tier]
    sav_frac = _TIER_SAVINGS_FRACTION[tier]
    spend_pool = disc_amt * (1.0 - sav_frac)
    sav_from_disc = disc_amt * sav_frac

    categories = []
    total_w = sum(weights)
    for (cid, label, icon, color), w in zip(_DISC_CATEGORIES, weights):
        frac_of_disc = (w / total_w) if total_w > 0 else 0.0
        amount = spend_pool * frac_of_disc
        categories.append({
            "id": cid,
            "label": label,
            "fraction_of_disc": frac_of_disc,
            "amount_usd": amount,
            "icon": icon,
            "color": color,
        })

    tiers = []
    for tid, tmeta in _TIER_META.items():
        tsav_frac = _TIER_SAVINGS_FRACTION[tid]
        tiers.append({
            "id": tid,
            "label": tmeta["label"],
            "color": tmeta["color"],
            "description": tmeta["description"],
            "monthly_disc_spend": disc_amt * (1.0 - tsav_frac),
            "monthly_disc_savings": disc_amt * tsav_frac,
        })

    return {
        "net_monthly": net_monthly_usd,
        "essential_ratio": e_ratio,
        "essential_amount": essential_amt,
        "discretionary_amount": disc_amt,
        "active_tier": tier,
        "tier_savings_amount": sav_from_disc,
        "tier_spend_amount": spend_pool,
        "discretionary_categories": categories,
        "tiers": tiers,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_lifestyle_split(
    net_monthly_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "lifestyle",
    gross_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Lifestyle Budget Split panel.

    Parameters
    ----------
    net_monthly_usd : Monthly net (post-tax) income in USD.
                      Pipe in from takehome_utils.render_takehome_adjuster()
                      for best results, or compute from gross as a fallback.
    location_hint   : ISO-2 country code or country name.
    widget_key      : Unique key prefix per call-site (e.g. "manual_a1_lifestyle").
                      Must differ for every place this is called.
    gross_usd       : Optional gross annual salary -- shown as context only.

    Returns
    -------
    dict -- the compute_lifestyle_split result.
    Returns an empty dict if widget is hidden or income is invalid.
    """
    if not net_monthly_usd or net_monthly_usd <= 0:
        return {}

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/interests: Lifestyle Budget Split",
        key=toggle_key,
        value=False,
        help="See how your discretionary income splits across lifestyle categories at different spending tiers.",
    )
    if not show:
        return {}

    with st.expander(":material/interests: Lifestyle Budget Split", expanded=True):
        st.caption(
            ":material/info: Focuses on how you spend your discretionary income -- "
            "the money left after essentials like housing, food, and utilities. "
            "Choose a lifestyle tier to see how your free cash distributes across "
            "spending categories. This is not financial advice."
        )

        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"
        label_suffix = f"({cur_code})" if use_local else "(USD)"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        key = _resolve_key(location_hint, _ESSENTIAL_RATIO)
        d_essential = _ESSENTIAL_RATIO.get(key or "", _ESSENTIAL_RATIO_FALLBACK)

        if location_hint and location_hint not in ("", "Other"):
            gross_part = (
                f" &nbsp;&middot;&nbsp; "
                f"<span style='color:#9CA6B5;'>Annual gross:</span>"
                f" <b>{_loc(gross_usd)}</b>"
                if gross_usd else ""
            )
            st.markdown(
                f"<div style='background:#1E2D40;border-left:4px solid #EC4899;"
                f"border-radius:6px;padding:12px 16px;margin:6px 0;font-size:13px;color:#C8D6E8;'>"
                f"<span style='font-weight:700;color:#E6EAF0;'>Country:</span> "
                f"{_country_name(location_hint)}<br>"
                f"<span style='color:#9CA6B5;'>Estimated essentials ratio:</span>"
                f" <b>{_pct(d_essential)} of net income</b>"
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
                "No country detected -- using generic 48% essentials ratio. "
                "Override below for more accurate results."
                "</div>",
                unsafe_allow_html=True,
            )

        # Tier selector
        tier_options = {
            "Frugal -- Prioritise saving": "frugal",
            "Balanced -- Mix of saving and living": "balanced",
            "Comfortable -- Quality experiences": "comfortable",
            "Aspirational -- Premium lifestyle": "aspirational",
        }
        tier_display = st.radio(
            "Select lifestyle tier",
            list(tier_options.keys()),
            index=1,
            key=f"{widget_key}_tier",
            horizontal=True,
            help="Each tier represents a different philosophy for spending your discretionary income.",
        )
        active_tier = tier_options[tier_display]

        use_custom = st.toggle(
            "Override essentials ratio",
            key=f"{widget_key}_custom",
            value=False,
            help="Set your own essentials fraction if the country default does not match your situation.",
        )

        custom_essential_ratio = None
        if use_custom:
            custom_essential_ratio = st.slider(
                "Essentials (% of net income)",
                min_value=20, max_value=90,
                value=int(d_essential * 100),
                step=1,
                key=f"{widget_key}_essential",
                help=(
                    "Fraction of net income spent on non-negotiable essentials: "
                    "housing, food, transport, utilities, insurance. "
                    "The remainder is your discretionary pool."
                ),
            ) / 100.0

        result = compute_lifestyle_split(
            net_monthly_usd,
            country=location_hint,
            active_tier=active_tier,
            custom_essential_ratio=custom_essential_ratio,
        )

        st.divider()

        # Income split overview
        c1, c2, c3 = st.columns(3)
        c1.metric(
            f"Monthly Net Income {label_suffix}",
            _loc(result["net_monthly"]),
        )
        c2.metric(
            f"Essentials {label_suffix}",
            _loc(result["essential_amount"]),
            delta=f"-{result['essential_ratio'] * 100:.0f}% of income",
            delta_color="inverse",
        )
        c3.metric(
            f"Discretionary Pool {label_suffix}",
            _loc(result["discretionary_amount"]),
            delta=f"{(1 - result['essential_ratio']) * 100:.0f}% of income",
            delta_color="normal",
        )

        st.divider()

        # Active tier highlight card
        active_meta = _TIER_META[active_tier]
        sav_frac = _TIER_SAVINGS_FRACTION[active_tier]
        st.markdown(
            f"<div style='background:#1A2535;border:1px solid #2D3A50;"
            f"border-left:5px solid {active_meta['color']};border-radius:10px;"
            f"padding:14px 18px;margin:6px 0;'>"
            f"<div style='color:{active_meta['color']};font-size:15px;"
            f"font-weight:700;margin-bottom:4px;'>"
            f"{active_meta['label']} Lifestyle</div>"
            f"<div style='color:#C8D6E8;font-size:13px;margin-bottom:8px;'>"
            f"{active_meta['description']}</div>"
            f"<div style='display:flex;gap:24px;flex-wrap:wrap;font-size:13px;'>"
            f"<span style='color:#9CA6B5;'>Lifestyle spend: "
            f"<b style='color:#E6EAF0;'>"
            f"{_loc(result['tier_spend_amount'])}/mo</b></span>"
            f"<span style='color:#9CA6B5;'>Saved from discretionary: "
            f"<b style='color:{active_meta['color']};'>"
            f"{_loc(result['tier_savings_amount'])}/mo "
            f"({sav_frac * 100:.0f}%)</b></span>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(f"**Discretionary Category Breakdown -- {active_meta['label']} Tier**")

        bars_html = ""
        for cat in result["discretionary_categories"]:
            pct_of_disc = cat["fraction_of_disc"] * 100
            bars_html += _bar_row(
                cat["label"],
                _loc(cat["amount_usd"]),
                pct_of_disc,
                cat["color"],
            )
        st.markdown(bars_html, unsafe_allow_html=True)

        st.divider()
        st.markdown("**Category Details**")
        col_a, col_b, col_c = st.columns(3)
        cols_cycle = [col_a, col_b, col_c]
        for idx, cat in enumerate(result["discretionary_categories"]):
            cols_cycle[idx % 3].metric(
                cat["label"],
                _loc(cat["amount_usd"]),
                delta=f"{cat['fraction_of_disc'] * 100:.1f}% of disc.",
                delta_color="off",
            )

        # Tier comparison table
        st.divider()
        st.markdown("**Lifestyle Tier Comparison**")
        for t in result["tiers"]:
            active_marker = " (selected)" if t["id"] == active_tier else ""
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;padding:8px 0;"
                f"border-bottom:1px solid #2D3A50;font-size:13px;'>"
                f"<span style='color:{t['color']};font-weight:600;width:130px;'>"
                f"{t['label']}{active_marker}</span>"
                f"<span style='color:#9CA6B5;'>Lifestyle: "
                f"<b style='color:#E6EAF0;'>{_loc(t['monthly_disc_spend'])}/mo</b></span>"
                f"<span style='color:#9CA6B5;'>Saved: "
                f"<b style='color:{t['color']};'>{_loc(t['monthly_disc_savings'])}/mo</b></span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.caption(
            "Essentials ratio uses country-level benchmarks from Numbeo / World Bank 2023/24. "
            "Category weights within each tier are based on typical urban professional "
            "spending patterns. Actual discretionary choices vary widely by individual preference."
        )

    return result
