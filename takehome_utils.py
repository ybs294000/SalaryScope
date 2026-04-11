"""
takehome_utils.py -- SalaryScope Take-Home Salary Utility
==========================================================
Computes the estimated in-hand / net salary after all deductions:
  - Income tax (uses tax_utils if available, otherwise a built-in tiered estimate)
  - PF / pension (employee contribution)
  - Professional tax / other statutory deductions

IMPORTANT DISCLAIMER
--------------------
All figures are APPROXIMATE estimates for illustrative / planning purposes only.
They do not constitute financial or legal advice. Consult a qualified tax or
payroll professional for precise calculations.

Design
------
- Completely standalone: works with or without tax_utils, col_utils,
  currency_utils, ctc_utils, or any other SalaryScope module.
- If tax_utils is present, its more precise bracket-based tax engine is used
  automatically. Falls back gracefully to an internal tiered estimate.
- country_utils is used for ISO-2 resolution if available; degrades without it.
- `compute_take_home(gross_usd, country, ...)` -- pure-math core,
  no Streamlit dependency, reusable from any tab or utility.
- `render_takehome_adjuster(...)` -- Streamlit toggle + expander UI widget.
  Mirrors the render_tax_adjuster / render_col_adjuster interface pattern.

Integration
-----------
    from takehome_utils import render_takehome_adjuster

    render_takehome_adjuster(
        gross_usd=prediction,
        location_hint=country,
        widget_key="manual_a1_th",
        net_usd=None,      # optional: pass net_usd from tax_utils to avoid recomputing
    )

Pure-math usage (Tab 3 / Tab 4):
    from takehome_utils import compute_take_home

    result = compute_take_home(gross_usd=80000, country="IN")
    net_monthly = result["net_monthly"]
"""

from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Built-in PF / pension rates (employee side, as fraction of gross)
# Sources: official government portals, OECD, ILO 2023/24.
# ---------------------------------------------------------------------------
_PF_RATE: dict[str, float] = {
    "IN": 0.12,    # EPF 12% of basic; approximated as % of gross here
    "US": 0.062,   # Social Security OASDI employee share
    "GB": 0.08,    # National Insurance primary threshold band
    "DE": 0.093,   # Rentenversicherung employee half
    "FR": 0.069,   # Net employee share (CRDS/CSG)
    "CA": 0.057,   # CPP employee contribution
    "AU": 0.11,    # Superannuation shown as CTC cost
    "SG": 0.20,    # CPF employee share (age < 55)
    "JP": 0.09,    # Kosei Nenkin employee share
    "CN": 0.08,    # Basic pension fund employee share
    "KR": 0.045,   # NPS employee share
    "BR": 0.075,   # INSS average employee
    "ZA": 0.01,    # UIF employee (capped)
    "AE": 0.00,    # No mandatory PF for expats
    "QA": 0.00,
    "SA": 0.10,    # GOSI Saudi nationals employee share
    "KW": 0.00,
    "BH": 0.05,
    "OM": 0.065,
    "NL": 0.174,   # AOW + ANW employee share
    "SE": 0.07,    # Inkomstpension
    "NO": 0.082,   # National Insurance employee contribution
    "DK": 0.00,    # Funded via general taxes
    "CH": 0.053,   # AHV/IV/EO employee half
    "NZ": 0.03,    # KiwiSaver minimum
    "MX": 0.0175,  # IMSS employee share
    "PK": 0.06,    # EOBI + voluntary PF
    "BD": 0.10,    # Provident Fund 10% of basic
    "LK": 0.08,    # EPF employee contribution
    "NP": 0.10,    # PF employee contribution
    "EG": 0.11,    # Social insurance employee share
    "NG": 0.08,    # Pension Reform Act employee contribution
    "KE": 0.06,    # NSSF + NHIF combined estimate
    "MY": 0.11,    # EPF employee (age < 60)
    "PH": 0.045,   # SSS + PhilHealth + Pag-IBIG combined
    "ID": 0.02,    # BPJS Ketenagakerjaan employee share
    "TH": 0.05,    # Social Security Fund employee share
    "VN": 0.105,   # VSS + HI employee shares
    "IE": 0.04,    # PRSI employee class A
    "AT": 0.105,   # ASVG pension employee share
    "BE": 0.1307,  # Pension + health employee share
    "FI": 0.074,   # TyEL + unemployment employee share
    "PT": 0.11,    # CGA / TSU employee share
    "GR": 0.064,   # IKA pension employee share (reformed)
    "ES": 0.047,   # Social security common contingencies employee
    "IT": 0.099,   # INPS pension employee share
    "PL": 0.1371,  # ZUS employee pension + disability
    "CZ": 0.065,   # Social insurance employee share
    "HU": 0.185,   # Pension + health + labour market employee share
    "RO": 0.25,    # CAS employee contribution
    "HR": 0.15,    # First pillar pension employee share
    "SK": 0.09,    # Social insurance employee share
    "SI": 0.221,   # Pension + health employee share
    "TR": 0.14,    # SSI employee share
    "UA": 0.00,    # Unified social contribution from employer side only now
    "RU": 0.00,    # Employer pays; no mandatory employee pension deduction
    "IL": 0.07,    # Bituach Leumi employee share
    "HK": 0.05,    # MPF employee mandatory contribution
    "TW": 0.075,   # NHI + pension employee share
}
_PF_RATE_FALLBACK = 0.07

# Professional tax / local levy flat monthly rates in USD equivalent
# Used as an annual figure (monthly * 12).
# Only applicable in countries that levy it -- defaults to 0 elsewhere.
_PROF_TAX_ANNUAL_USD: dict[str, float] = {
    "IN": 240.0,   # max Rs.200/month (some states) -- approx $240/yr
    "NG": 120.0,   # development levy approx
    "PH": 96.0,    # professional tax receipt
    "MY": 72.0,    # HRDF levy estimate
}
_PROF_TAX_FALLBACK = 0.0

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


def _card(value_str: str, label: str, color: str = "#F59E0B") -> str:
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


def _deduction_row(label: str, amount: float, gross: float, fmt_func, color: str = "#EF4444") -> str:
    rate = amount / gross * 100 if gross > 0 else 0
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:5px 0;border-bottom:1px solid #283142;'>"
        f"<span style='color:#9CA6B5;font-size:13px;'>{label}</span>"
        f"<span style='color:{color};font-size:13px;'>"
        f"{fmt_func(amount)} ({rate:.1f}%)</span>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Core computation -- no Streamlit, reusable anywhere
# ---------------------------------------------------------------------------

def compute_take_home(
    gross_usd: float,
    country: Optional[str] = None,
    custom_tax_rate: Optional[float] = None,
    custom_pf_rate: Optional[float] = None,
    custom_other_rate: float = 0.01,
) -> dict:
    """
    Compute estimated take-home (net in-hand) salary after all deductions.

    Uses tax_utils.get_effective_rate for the tax component if tax_utils is
    importable and no override is supplied. Falls back to an internal tiered
    estimate otherwise.

    Parameters
    ----------
    gross_usd        : Annual gross salary in USD (pre-tax).
    country          : ISO-2 code or country name for default rate lookup.
    custom_tax_rate  : Override effective income-tax rate (fraction, 0--1).
                       None = auto-compute from tax_utils or built-in estimate.
    custom_pf_rate   : Override PF / pension employee rate (fraction of gross).
                       None = country default from built-in table.
    custom_other_rate: Other deductions (professional tax, group insurance, etc.)
                       as fraction of gross. Default 0.01 (1%).

    Returns
    -------
    dict with keys:
        gross_usd              -- input gross
        tax_rate               -- effective tax rate applied
        tax_amount             -- annual tax deduction (USD)
        pf_rate                -- PF rate applied
        pf_amount              -- annual PF deduction (USD)
        other_rate             -- other deductions rate
        other_amount           -- annual other deductions (USD)
        prof_tax_annual        -- professional / local tax (USD, if applicable)
        total_deductions       -- sum of all deductions (USD)
        net_annual             -- net take-home annual (USD)
        net_monthly            -- net take-home monthly (USD)
        net_weekly             -- net take-home weekly (USD)
        net_hourly             -- net take-home hourly (USD, assumes 2080 hrs/yr)
        deduction_breakdown    -- list of (label, amount) tuples for UI rendering
        tax_source             -- string describing where the tax rate came from
    """
    # -- Income tax --
    tax_source = "custom override"
    if custom_tax_rate is not None:
        tax_rate = float(custom_tax_rate)
    else:
        try:
            from tax_utils import get_effective_rate
            tax_rate, tax_src_key, _ = get_effective_rate(gross_usd, country)
            tax_source = f"tax_utils ({tax_src_key})"
        except ImportError:
            # Built-in fallback tiers (generic world average)
            if gross_usd < 20000:
                tax_rate = 0.08
            elif gross_usd < 40000:
                tax_rate = 0.15
            elif gross_usd < 70000:
                tax_rate = 0.22
            elif gross_usd < 120000:
                tax_rate = 0.28
            elif gross_usd < 200000:
                tax_rate = 0.33
            else:
                tax_rate = 0.38
            tax_source = "built-in tiered estimate (tax_utils not available)"

    # -- PF / pension --
    key = _resolve_key(country, _PF_RATE)
    pf_rate = float(custom_pf_rate) if custom_pf_rate is not None \
        else _PF_RATE.get(key or "", _PF_RATE_FALLBACK)

    # -- Professional / local tax --
    prof_tax = _PROF_TAX_ANNUAL_USD.get(key or "", _PROF_TAX_FALLBACK)

    # -- Other deductions --
    other_amount = gross_usd * custom_other_rate

    tax_amount = gross_usd * tax_rate
    pf_amount = gross_usd * pf_rate
    total_deductions = tax_amount + pf_amount + prof_tax + other_amount
    net_annual = max(0.0, gross_usd - total_deductions)

    breakdown = [
        ("Income Tax", tax_amount),
        ("PF / Pension Contribution", pf_amount),
    ]
    if prof_tax > 0:
        breakdown.append(("Professional / Local Tax", prof_tax))
    breakdown.append(("Other Deductions (insurance, etc.)", other_amount))

    return {
        "gross_usd": gross_usd,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "pf_rate": pf_rate,
        "pf_amount": pf_amount,
        "other_rate": custom_other_rate,
        "other_amount": other_amount,
        "prof_tax_annual": prof_tax,
        "total_deductions": total_deductions,
        "net_annual": net_annual,
        "net_monthly": net_annual / 12,
        "net_weekly": net_annual / 52,
        "net_hourly": net_annual / 2080,
        "deduction_breakdown": breakdown,
        "tax_source": tax_source,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def render_takehome_adjuster(
    gross_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "takehome",
    net_usd: Optional[float] = None,
) -> dict:
    """
    Render a toggle + expander for the Take-Home Salary panel.

    Parameters
    ----------
    gross_usd      : Annual gross salary in USD (pre-tax).
    location_hint  : ISO-2 country code or country name.
    widget_key     : Unique key prefix per call-site (e.g. "manual_a1_th").
                     Must differ for every place this is called.
    net_usd        : Optional pre-computed post-tax net from tax_utils.
                     If provided (and no override is active), used directly
                     to avoid a second tax computation.

    Returns
    -------
    dict -- the compute_take_home result (net_monthly key is useful for
    passing to savings_utils and loan_utils).
    Returns an empty dict with net_monthly=gross_usd/12 if widget is hidden.

    Usage
    -----
        from takehome_utils import render_takehome_adjuster
        th = render_takehome_adjuster(gross_usd=prediction, location_hint=country,
                                      widget_key="manual_a1_th")
        net_monthly = th.get("net_monthly", prediction / 12)
    """
    fallback = {
        "net_monthly": gross_usd / 12 if gross_usd else 0,
        "net_annual": gross_usd or 0,
    }
    if not gross_usd or gross_usd <= 0:
        return fallback

    toggle_key = f"{widget_key}_toggle"
    show = st.toggle(
        ":material/payments: Take-Home Salary",
        key=toggle_key,
        value=False,
        help="Show estimated in-hand salary after tax, PF, and other deductions.",
    )
    if not show:
        return fallback

    with st.expander(":material/payments: Take-Home Salary", expanded=True):
        st.caption(
            ":material/info: Estimated in-hand salary after income tax, PF / pension, "
            "and other deductions. All rates are overridable. "
            "This is not financial or legal advice."
        )

        key = _resolve_key(location_hint, _PF_RATE)
        d_pf = _PF_RATE.get(key or "", _PF_RATE_FALLBACK)

        # Get built-in tax rate for display / prefill
        try:
            from tax_utils import get_effective_rate
            d_tax, d_tax_src, _ = get_effective_rate(gross_usd, location_hint)
            tax_label = f"{_pct(d_tax)} (tax_utils -- {d_tax_src})"
        except ImportError:
            if gross_usd < 40000:
                d_tax = 0.15
            elif gross_usd < 80000:
                d_tax = 0.22
            elif gross_usd < 150000:
                d_tax = 0.28
            else:
                d_tax = 0.35
            tax_label = f"{_pct(d_tax)} (built-in estimate)"

        if location_hint and location_hint not in ("", "Other"):
            st.info(
                f"**Country:** {_country_name(location_hint)}\n\n"
                f"Est. effective tax: **{tax_label}**  |  "
                f"PF rate: **{_pct(d_pf)}** of gross"
            )
        else:
            st.info(
                "No country detected. Using generic estimates. "
                "Use the override below for more accurate results."
            )

        use_custom = st.toggle(
            "Override deduction rates",
            key=f"{widget_key}_custom",
            value=False,
            help="Set your own effective tax, PF, and other deduction rates.",
        )

        custom_tax: Optional[float] = None
        custom_pf: Optional[float] = None
        custom_other = 0.01

        if use_custom:
            c1, c2, c3 = st.columns(3)
            with c1:
                custom_tax = st.slider(
                    "Effective Income Tax Rate (%)",
                    min_value=0.0, max_value=65.0,
                    value=float(round(d_tax * 100, 1)),
                    step=0.5,
                    key=f"{widget_key}_tax",
                    help=(
                        "Your combined effective income tax rate including "
                        "all income taxes and applicable surcharges."
                    ),
                ) / 100.0
            with c2:
                custom_pf = st.slider(
                    "PF / Pension Rate (% of Gross)",
                    min_value=0.0, max_value=25.0,
                    value=float(round(d_pf * 100, 1)),
                    step=0.5,
                    key=f"{widget_key}_pf",
                    help="Employee-side PF or pension contribution as % of gross.",
                ) / 100.0
            with c3:
                custom_other = st.slider(
                    "Other Deductions (% of Gross)",
                    min_value=0.0, max_value=15.0,
                    value=1.0,
                    step=0.5,
                    key=f"{widget_key}_other",
                    help=(
                        "Group health insurance, professional tax, VPF, "
                        "or any other monthly deductions."
                    ),
                ) / 100.0

        # Prefer externally computed net_usd (from tax_utils) when no override is set
        if net_usd is not None and not use_custom:
            pf_amount = gross_usd * d_pf
            other_amount = gross_usd * 0.01
            prof_tax = _PROF_TAX_ANNUAL_USD.get(key or "", _PROF_TAX_FALLBACK)
            total_deductions = gross_usd - net_usd
            net_annual_final = net_usd
            breakdown = [
                ("Income Tax (from tax_utils)", gross_usd - net_usd - pf_amount - other_amount - prof_tax),
                ("PF / Pension Contribution", pf_amount),
            ]
            if prof_tax > 0:
                breakdown.append(("Professional / Local Tax", prof_tax))
            breakdown.append(("Other Deductions", other_amount))
            result = {
                "gross_usd": gross_usd,
                "tax_rate": d_tax,
                "tax_amount": gross_usd - net_usd,
                "pf_rate": d_pf,
                "pf_amount": pf_amount,
                "other_rate": 0.01,
                "other_amount": other_amount,
                "prof_tax_annual": prof_tax,
                "total_deductions": total_deductions,
                "net_annual": net_annual_final,
                "net_monthly": net_annual_final / 12,
                "net_weekly": net_annual_final / 52,
                "net_hourly": net_annual_final / 2080,
                "deduction_breakdown": breakdown,
                "tax_source": "tax_utils (passed via net_usd parameter)",
            }
        else:
            result = compute_take_home(
                gross_usd,
                location_hint,
                custom_tax_rate=custom_tax,
                custom_pf_rate=custom_pf,
                custom_other_rate=custom_other,
            )

        st.divider()

        # --- Currency resolution ---
        cur_code, cur_sym, fx_rate = _get_currency_meta(location_hint)
        use_local = cur_code != "USD"

        def _loc(v: float) -> str:
            if use_local:
                return _fmt_local(v * fx_rate, cur_sym, cur_code)
            return _fmt(v)

        net_card_label = (
            f"ESTIMATED NET ANNUAL TAKE-HOME ({cur_code}  ≈  {_fmt(result['net_annual'])} USD)"
            if use_local else "ESTIMATED NET ANNUAL TAKE-HOME (USD)"
        )
        st.markdown(
            _card(_loc(result["net_annual"]), net_card_label),
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gross Annual", _loc(result["gross_usd"]),
                  delta=_fmt(result["gross_usd"]) if use_local else None, delta_color="off")
        c2.metric(
            f"Net Monthly ({cur_code})" if use_local else "Net Monthly",
            _loc(result["net_monthly"]),
            delta=_fmt(result["net_monthly"]) if use_local else None, delta_color="off",
        )
        c3.metric(
            f"Net Weekly ({cur_code})" if use_local else "Net Weekly",
            _loc(result["net_weekly"]),
            delta=_fmt(result["net_weekly"]) if use_local else None, delta_color="off",
        )
        c4.metric(
            f"Net Hourly ({cur_code})" if use_local else "Net Hourly",
            _loc(result["net_hourly"]),
            delta=_fmt(result["net_hourly"]) if use_local else None, delta_color="off",
        )

        st.divider()
        st.markdown("**Deduction Breakdown**")

        for label, amount in result["deduction_breakdown"]:
            st.markdown(
                _deduction_row(label, amount, gross_usd, _loc),
                unsafe_allow_html=True,
            )

        # Total deductions row
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;"
            f"padding:6px 0;margin-top:2px;'>"
            f"<span style='color:#9CA6B5;font-size:13px;font-weight:600;'>"
            f"Total Deductions</span>"
            f"<span style='color:#EF4444;font-size:13px;font-weight:600;'>"
            f"{_loc(result['total_deductions'])}"
            f"({result['total_deductions'] / gross_usd * 100:.1f}%)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Net take-home footer row — show local + USD if currency differs
        net_display = (
            f"{_loc(result['net_annual'])}  ≈  {_fmt(result['net_annual'])}"
            if use_local else _fmt(result["net_annual"])
        )
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;"
            f"padding:7px 0;border-top:2px solid #3E7DE0;margin-top:2px;'>"
            f"<span style='color:#E6EAF0;font-size:14px;font-weight:700;'>"
            f"Net Take-Home (Annual)</span>"
            f"<span style='color:#22C55E;font-size:14px;font-weight:700;'>"
            f"{net_display}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.caption(
            f"Tax rate source: {result['tax_source']}. "
            "PF shown is the employee-side contribution only. "
            "Other deductions include professional tax, group insurance, and similar. "
            "Actual in-hand amounts depend on employer payroll policy."
        )

    return result