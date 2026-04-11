"""
ctc_utils.py -- SalaryScope CTC Structure Breakdown Utility
============================================================
Breaks down an annual gross CTC into its standard components:
Base Salary, HRA, Bonus, PF / Pension (employee), Gratuity, Other Allowances.

IMPORTANT DISCLAIMER
--------------------
All component splits are APPROXIMATE country-level estimates for illustrative
purposes only. Actual CTC structures depend on employer policy, designation,
local regulations, and individual offer letters. This is not financial or
legal advice.

Design
------
- Completely standalone: works with or without tax_utils, col_utils,
  currency_utils, or any other SalaryScope module.
- country_utils is used for name / ISO-2 resolution if present, but the
  file degrades gracefully without it.
- `compute_ctc_breakdown(gross_usd, country, ...)` -- pure-math core,
  no Streamlit dependency, safe to call from any tab or utility.
- `render_ctc_adjuster(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_tax_adjuster / render_col_adjuster interface pattern.

Integration
-----------
    from ctc_utils import render_ctc_adjuster

    render_ctc_adjuster(
        gross_usd=prediction,
        location_hint=country,
        widget_key="manual_a1_ctc",
    )

Pure-math usage (Tab 3 / Tab 4 or other utilities):
    from ctc_utils import compute_ctc_breakdown

    result = compute_ctc_breakdown(gross_usd=80000, country="IN")
    print(result["basic"], result["hra"], result["bonus"])
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Built-in country-level rate tables
# ---------------------------------------------------------------------------

# HRA as fraction of basic salary -- standard employer policy by country.
# Sources: income-tax rules (India), Gulf labour law, employer surveys 2023/24.
_HRA_RATE: dict[str, float] = {
    "IN": 0.50,   # metro HRA -- 50% of basic is the most common policy
    "US": 0.00,   # not a formal payroll component in the US
    "GB": 0.00,
    "DE": 0.00,
    "FR": 0.00,
    "AU": 0.00,
    "CA": 0.00,
    "JP": 0.05,   # jutaku teate (housing allowance) small component
    "CN": 0.08,   # housing fund contribution sometimes shown as allowance
    "KR": 0.05,
    "SG": 0.10,   # housing component in some multinationals
    "AE": 0.25,   # housing allowance mandated / very common in Gulf
    "QA": 0.25,
    "SA": 0.25,
    "KW": 0.25,
    "BH": 0.20,
    "OM": 0.20,
    "PK": 0.45,   # HRA common in Pakistan corporate packages
    "BD": 0.40,
    "LK": 0.25,
    "NP": 0.30,
    "EG": 0.20,
    "NG": 0.10,
    "ZA": 0.00,
    "MY": 0.10,
    "PH": 0.10,
    "ID": 0.10,
    "TH": 0.05,
    "VN": 0.05,
}
_HRA_RATE_FALLBACK = 0.00

# Typical target annual bonus as fraction of CTC.
# Sources: Mercer, Aon, Deloitte compensation surveys 2023/24.
_BONUS_RATE: dict[str, float] = {
    "US": 0.10,
    "GB": 0.10,
    "DE": 0.08,
    "FR": 0.07,
    "AU": 0.08,
    "CA": 0.08,
    "CH": 0.12,
    "NL": 0.08,
    "SE": 0.08,
    "NO": 0.07,
    "DK": 0.07,
    "IE": 0.09,
    "SG": 0.12,
    "JP": 0.15,   # bi-annual shunin and nenmatsu bonuses
    "KR": 0.15,   # quarterly performance bonus common
    "CN": 0.10,
    "HK": 0.12,
    "TW": 0.12,
    "IN": 0.10,
    "PK": 0.08,
    "BD": 0.08,
    "LK": 0.08,
    "AE": 0.08,
    "QA": 0.08,
    "SA": 0.08,
    "BR": 0.07,
    "MX": 0.07,
    "AR": 0.07,
    "ZA": 0.10,
    "NG": 0.08,
    "KE": 0.08,
    "MY": 0.09,
    "PH": 0.09,
    "ID": 0.08,
    "TH": 0.08,
    "VN": 0.07,
}
_BONUS_RATE_FALLBACK = 0.08

# PF / pension employee contribution as fraction of basic salary.
# Sources: official government portals, OECD, ILO 2023/24.
_PF_RATE: dict[str, float] = {
    "IN": 0.12,   # EPF -- 12% of basic (capped at INR 15,000 basic for statutory)
    "US": 0.062,  # Social Security OASDI employee share
    "GB": 0.08,   # National Insurance (primary threshold band)
    "DE": 0.093,  # Rentenversicherung employee half
    "FR": 0.069,  # CRDS/CSG net employee share
    "CA": 0.057,  # CPP employee contribution
    "AU": 0.11,   # Superannuation (shown as CTC cost -- employer-side)
    "SG": 0.20,   # CPF employee share (age < 55)
    "JP": 0.09,   # Kosei Nenkin employee share
    "CN": 0.08,   # Basic pension fund employee share
    "KR": 0.045,  # NPS employee share
    "BR": 0.075,  # INSS average employee contribution
    "ZA": 0.01,   # UIF employee contribution (capped)
    "AE": 0.00,   # No mandatory PF for expats; UAE nationals: GPSSA 5%
    "QA": 0.00,
    "SA": 0.10,   # GOSI -- Saudi nationals employee share
    "KW": 0.00,
    "BH": 0.05,
    "OM": 0.065,
    "NL": 0.174,  # AOW + ANW employee share
    "SE": 0.07,   # Inkomstpension employee share
    "NO": 0.082,  # National Insurance employee contribution
    "DK": 0.00,   # Funded by general taxes -- no direct employee PF line
    "CH": 0.053,  # AHV/IV/EO employee half
    "NZ": 0.03,   # KiwiSaver minimum employee rate
    "MX": 0.0175, # IMSS employee share
    "PK": 0.06,   # EOBI + voluntary PF
    "BD": 0.10,   # Provident Fund -- typically 10% of basic
    "LK": 0.08,   # EPF employee contribution
    "NP": 0.10,   # PF employee contribution
    "EG": 0.11,   # Social insurance employee share
    "NG": 0.08,   # Pension Reform Act -- employee contribution
    "KE": 0.06,   # NSSF + NHIF combined employee share
    "MY": 0.11,   # EPF employee contribution (age < 60)
    "PH": 0.045,  # SSS + PhilHealth + Pag-IBIG employee shares
    "ID": 0.02,   # BPJS Ketenagakerjaan employee share
    "TH": 0.05,   # Social Security Fund employee share
    "VN": 0.105,  # VSS + HI employee shares
}
_PF_RATE_FALLBACK = 0.07

# Gratuity provision as fraction of basic salary (annual accrual).
# Where not statutory, defaults to 0 -- user can override.
# Sources: government labour law portals, Gulf HR guides.
_GRATUITY_RATE: dict[str, float] = {
    "IN": 0.0481,   # 15 days per year: 15/26 * (1/12) ~ 4.81% of annual basic
    "AE": 0.0833,   # 21 days per year (< 5 yrs) / 30 days (> 5 yrs): ~8.33% avg
    "QA": 0.0833,
    "SA": 0.0833,
    "KW": 0.0833,
    "BH": 0.0833,
    "OM": 0.0833,
    "PK": 0.0481,
    "BD": 0.0481,
    "LK": 0.0481,
    "NP": 0.0481,
    "EG": 0.0481,
    "KE": 0.0500,
    "NG": 0.0500,
    "ZA": 0.0000,   # covered by UIF and pension -- not a separate gratuity line
    "PH": 0.0833,   # retirement pay law
    "ID": 0.0833,   # UMP-based severance provision
    "MY": 0.0481,
    "TH": 0.0481,
    "VN": 0.0481,
    "US": 0.0000,
    "GB": 0.0000,
    "DE": 0.0000,
    "FR": 0.0000,
    "AU": 0.0000,
    "CA": 0.0000,
    "SG": 0.0000,
    "JP": 0.0000,
    "CN": 0.0000,
    "KR": 0.0000,
    "BR": 0.0000,
    "CH": 0.0000,
    "NL": 0.0000,
    "SE": 0.0000,
    "NO": 0.0000,
    "DK": 0.0000,
}
_GRATUITY_RATE_FALLBACK = 0.00  # not universal -- 0 unless explicitly known

# ---------------------------------------------------------------------------
# Helpers (no external dependencies)
# ---------------------------------------------------------------------------

def _resolve_key(location_hint: Optional[str], table: dict) -> Optional[str]:
    """
    Return the table key for a location hint, or None.
    Direct ISO-2 match first; falls back to country_utils if available.
    """
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
    """
    Resolve local currency for a location hint.

    Returns (currency_code, currency_symbol, fx_rate_from_usd).
    Falls back to ("USD", "$", 1.0) if currency_utils is unavailable
    or the location cannot be resolved.
    """
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
    """Format a value in local currency. Uses integer formatting for large-unit currencies."""
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


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit, reusable anywhere
# ---------------------------------------------------------------------------

def compute_ctc_breakdown(
    gross_usd: float,
    country: Optional[str] = None,
    basic_fraction: float = 0.40,
    hra_rate: Optional[float] = None,
    bonus_rate: Optional[float] = None,
    pf_rate: Optional[float] = None,
    gratuity_rate: Optional[float] = None,
    other_allowance_fraction: float = 0.05,
) -> dict:
    """
    Break down an annual CTC gross salary (USD) into standard components.

    Parameters
    ----------
    gross_usd               : Annual gross CTC in USD.
    country                 : ISO-2 code or country name. Used to look up
                              country-specific default rates.
    basic_fraction          : Basic salary as fraction of CTC (default 0.40).
    hra_rate                : HRA as fraction of basic. None = country default.
    bonus_rate              : Target bonus as fraction of CTC. None = country default.
    pf_rate                 : PF / pension employee share as fraction of basic.
                              None = country default.
    gratuity_rate           : Gratuity provision as fraction of basic. None = country default.
    other_allowance_fraction: Catch-all other allowances as fraction of CTC (default 0.05).

    Returns
    -------
    dict with keys:
        gross_usd          -- input annual CTC
        basic              -- base salary (annual)
        hra                -- house rent allowance (annual)
        bonus              -- target variable pay (annual)
        pf_employee        -- employee PF / pension contribution (annual)
        gratuity           -- gratuity accrual provision (annual)
        other_allowances   -- other allowances (annual)
        monthly_basic      -- basic / 12
        monthly_gross      -- gross / 12
        rates_used         -- dict of all rates applied
    """
    key = _resolve_key(country, _HRA_RATE)

    r_hra = hra_rate if hra_rate is not None \
        else _HRA_RATE.get(key or "", _HRA_RATE_FALLBACK)
    r_bonus = bonus_rate if bonus_rate is not None \
        else _BONUS_RATE.get(key or "", _BONUS_RATE_FALLBACK)
    r_pf = pf_rate if pf_rate is not None \
        else _PF_RATE.get(key or "", _PF_RATE_FALLBACK)
    r_gratuity = gratuity_rate if gratuity_rate is not None \
        else _GRATUITY_RATE.get(key or "", _GRATUITY_RATE_FALLBACK)

    basic = gross_usd * basic_fraction
    hra = basic * r_hra
    bonus = gross_usd * r_bonus
    pf_employee = basic * r_pf
    gratuity = basic * r_gratuity
    other = gross_usd * other_allowance_fraction

    return {
        "gross_usd": gross_usd,
        "basic": basic,
        "hra": hra,
        "bonus": bonus,
        "pf_employee": pf_employee,
        "gratuity": gratuity,
        "other_allowances": other,
        "monthly_basic": basic / 12,
        "monthly_gross": gross_usd / 12,
        "rates_used": {
            "basic_fraction": basic_fraction,
            "hra_rate": r_hra,
            "bonus_rate": r_bonus,
            "pf_rate": r_pf,
            "gratuity_rate": r_gratuity,
            "other_fraction": other_allowance_fraction,
        },
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_ctc_adjuster(
    gross_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "ctc",
) -> None:
    """
    Render a toggle + expander for the CTC Structure Breakdown panel.

    Parameters
    ----------
    gross_usd      : Annual gross CTC in USD.
    location_hint  : ISO-2 country code or country name.
    widget_key     : Unique key prefix per call-site (e.g. "manual_a1_ctc").
                     Must be different for every place this is called.

    Usage
    -----
        from ctc_utils import render_ctc_adjuster
        render_ctc_adjuster(gross_usd=prediction, location_hint=country,
                            widget_key="manual_a1_ctc")
    """
    if not gross_usd or gross_usd <= 0:
        return

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/account_balance_wallet: CTC Structure Breakdown",
        key=toggle_key,
        value=False,
        help="Show how your annual salary breaks down into payroll components.",
    )
    if not show:
        return

    with st.expander(
        ":material/account_balance_wallet: CTC Structure Breakdown",
        expanded=True,
    ):
        st.caption(
            ":material/info: Approximate breakdown of your annual CTC into standard "
            "payroll components. All rates are country-specific defaults and can be "
            "overridden below. This is not financial or legal advice."
        )

        key = _resolve_key(location_hint, _HRA_RATE)
        d_basic = 0.40
        d_hra = _HRA_RATE.get(key or "", _HRA_RATE_FALLBACK)
        d_bonus = _BONUS_RATE.get(key or "", _BONUS_RATE_FALLBACK)
        d_pf = _PF_RATE.get(key or "", _PF_RATE_FALLBACK)
        d_gratuity = _GRATUITY_RATE.get(key or "", _GRATUITY_RATE_FALLBACK)
        d_other = 0.05

        if location_hint and location_hint not in ("", "Other"):
            st.info(
                f"**Country detected:** {_country_name(location_hint)}\n\n"
                f"Basic: {_pct(d_basic)} of CTC  |  "
                f"HRA: {_pct(d_hra)} of Basic  |  "
                f"Bonus: {_pct(d_bonus)} of CTC  |  "
                f"PF: {_pct(d_pf)} of Basic  |  "
                f"Gratuity: {_pct(d_gratuity)} of Basic"
            )
        else:
            st.info(
                "No country detected. Using generic defaults. "
                "Enable the override below for more accurate figures."
            )

        use_custom = st.toggle(
            "Override component rates",
            key=f"{widget_key}_custom",
            value=False,
            help="Manually set the fraction of CTC for each payroll component.",
        )

        if use_custom:
            c1, c2 = st.columns(2)
            with c1:
                d_basic = st.slider(
                    "Basic Salary (% of CTC)",
                    min_value=20, max_value=70,
                    value=int(d_basic * 100),
                    step=1,
                    key=f"{widget_key}_basic",
                    help="Typically 35-50% of CTC in India; 100% in Western countries.",
                ) / 100.0
                d_hra = st.slider(
                    "HRA (% of Basic)",
                    min_value=0, max_value=60,
                    value=int(d_hra * 100),
                    step=1,
                    key=f"{widget_key}_hra",
                    help="House Rent Allowance. 50% of basic is standard in India for metros.",
                ) / 100.0
                d_bonus = st.slider(
                    "Target Bonus (% of CTC)",
                    min_value=0, max_value=40,
                    value=int(d_bonus * 100),
                    step=1,
                    key=f"{widget_key}_bonus",
                    help="Variable / performance bonus as a percentage of annual CTC.",
                ) / 100.0
            with c2:
                d_pf = st.slider(
                    "PF / Pension (% of Basic)",
                    min_value=0, max_value=25,
                    value=int(d_pf * 100),
                    step=1,
                    key=f"{widget_key}_pf",
                    help="Employee PF or pension contribution as a percentage of basic.",
                ) / 100.0
                d_gratuity = st.slider(
                    "Gratuity Provision (% of Basic)",
                    min_value=0, max_value=15,
                    value=int(d_gratuity * 100),
                    step=1,
                    key=f"{widget_key}_gratuity",
                    help="Annual gratuity accrual as a percentage of basic. ~4.81% in India.",
                ) / 100.0
                d_other = st.slider(
                    "Other Allowances (% of CTC)",
                    min_value=0, max_value=20,
                    value=int(d_other * 100),
                    step=1,
                    key=f"{widget_key}_other",
                    help="Special allowance, LTA, medical, internet, or any other components.",
                ) / 100.0

        result = compute_ctc_breakdown(
            gross_usd,
            location_hint,
            basic_fraction=d_basic,
            hra_rate=d_hra,
            bonus_rate=d_bonus,
            pf_rate=d_pf,
            gratuity_rate=d_gratuity,
            other_allowance_fraction=d_other,
        )

        # --- Currency resolution ---
        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            """Format in local currency (or USD if no conversion available)."""
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        st.divider()

        card_label = f"ANNUAL CTC ({cur_code})" if use_local else "ANNUAL CTC (USD)"
        card_val = (
            f"{_loc(result['gross_usd'])}  ≈ {_fmt(result['gross_usd'])}"
            if use_local else _fmt(result["gross_usd"])
        )
        st.markdown(
            _card(card_val, card_label, color="#3E7DE0"),
            unsafe_allow_html=True,
        )

        comp_label = f"Annual Components ({cur_code} / USD)" if use_local else "Annual Components (USD)"
        st.markdown(f"**{comp_label}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Base Salary", _loc(result["basic"]),
                  delta=_fmt(result["basic"]) if use_local else None, delta_color="off")
        c2.metric("HRA", _loc(result["hra"]),
                  delta=_fmt(result["hra"]) if use_local else None, delta_color="off")
        c3.metric("Target Bonus", _loc(result["bonus"]),
                  delta=_fmt(result["bonus"]) if use_local else None, delta_color="off")

        c4, c5, c6 = st.columns(3)
        c4.metric("PF / Pension (Employee)", _loc(result["pf_employee"]),
                  delta=_fmt(result["pf_employee"]) if use_local else None, delta_color="off")
        c5.metric("Gratuity Provision", _loc(result["gratuity"]),
                  delta=_fmt(result["gratuity"]) if use_local else None, delta_color="off")
        c6.metric("Other Allowances", _loc(result["other_allowances"]),
                  delta=_fmt(result["other_allowances"]) if use_local else None, delta_color="off")

        c7, c8, _ = st.columns(3)
        c7.metric("Monthly Gross", _loc(result["monthly_gross"]),
                  delta=_fmt(result["monthly_gross"]) if use_local else None, delta_color="off")
        c8.metric("Monthly Basic", _loc(result["monthly_basic"]),
                  delta=_fmt(result["monthly_basic"]) if use_local else None, delta_color="off")

        st.divider()
        st.markdown("**Component Proportions (% of CTC)**")

        components = [
            ("Base Salary",           result["basic"],           "#3E7DE0"),
            ("HRA",                   result["hra"],             "#22C55E"),
            ("Target Bonus",          result["bonus"],           "#F59E0B"),
            ("PF / Pension",          result["pf_employee"],     "#A78BFA"),
            ("Gratuity",              result["gratuity"],        "#FB923C"),
            ("Other Allowances",      result["other_allowances"],"#38BDF8"),
        ]

        for label, val, color in components:
            pct_of_ctc = val / gross_usd * 100 if gross_usd > 0 else 0
            bar_w = max(4, int(pct_of_ctc * 5))
            val_display = (
                f"{_loc(val)} ({_fmt(val)}) ({pct_of_ctc:.1f}%)"
                if use_local else
                f"{_fmt(val)} ({pct_of_ctc:.1f}%)"
            )
            st.markdown(
                f"<div style='display:flex;align-items:center;margin:3px 0;'>"
                f"<span style='width:200px;color:#9CA6B5;font-size:13px;"
                f"flex-shrink:0;'>{label}</span>"
                f"<span style='display:inline-block;background:{color};"
                f"width:{bar_w}px;height:13px;border-radius:3px;"
                f"margin-right:10px;flex-shrink:0;'></span>"
                f"<span style='color:#E6EAF0;font-size:13px;'>"
                f"{val_display}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.caption(
            "Figures are illustrative estimates only. Actual CTC structures depend on "
            "employer policy, designation band, and individual offer terms. "
            "PF shown is the employee-side contribution. Gratuity is an annual accrual "
            "provision -- it is paid out on separation, not monthly."
        )