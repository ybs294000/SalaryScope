"""
tax_utils.py — SalaryScope Tax Estimation Utility
==================================================
Provides estimated post-tax salary calculations for a broad set of countries.

IMPORTANT DISCLAIMER
--------------------
Tax data is inherently complex (brackets, deductions, filing status, local taxes,
social contributions, etc.). This file provides APPROXIMATE effective tax rates
for illustrative/planning purposes only — not legal or financial advice.

Since no reliable free real-time tax API exists, the data is:
  - Built-in estimates (research-based, updated periodically)
  - Fully overridable by the user via custom rate input
  - Saveable/loadable from a local JSON file for custom configurations

Design
------
- Completely standalone: works with or without currency_utils.py
- `compute_post_tax(gross_usd, country, custom_rate)` — core function, usable anywhere
- `render_tax_adjuster(...)` — Streamlit UI widget (toggle → expander)
- Mirrors currency_utils.py patterns for easy removal or extension

Integration (Tab 1 / Tab 2 in app.py)
--------------------------------------
    from tax_utils import render_tax_adjuster

    # Call AFTER render_currency_converter (or standalone):
    render_tax_adjuster(
        gross_usd=prediction,          # annual USD salary (pre-tax)
        location_hint=country,         # ISO-2 or country name
        widget_key="manual_a1_tax",    # unique key per call-site
        converted_amount=None,         # optional: pass converted currency amount
        converted_currency=None,       # e.g. "INR" — if provided, shows post-tax in that currency too
        rates=None,                    # optional: pass rates dict from currency_utils
    )

Tab 3 / Tab 4 (pure math):
    from tax_utils import compute_post_tax, get_effective_rate
"""

import json
import os
from typing import Optional

import streamlit as st

from app.utils.country_utils import get_country_name, resolve_iso2

from app.tabs.admin_panel import _is_local

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_TAX_FALLBACK_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tax_rates_custom.json"
)

# ---------------------------------------------------------------------------
# Built-in tax data
# Structure: country_key -> list of (upper_bound_usd, marginal_rate)
#   The list encodes progressive tax brackets in USD equivalent thresholds.
#   The final bracket uses float('inf') as upper bound.
#   Rates are COMBINED (income + major social contributions) effective estimates.
#   Source: public government tax summaries, OECD data, Numbeo, TaxFoundation.
#   Last reviewed: 2024.
#
# For countries with flat/simple systems a single bracket is used.
# Social security / national insurance caps are approximated.
# ---------------------------------------------------------------------------

# Each entry: list of (threshold_usd, rate_fraction)
# Thresholds are ANNUAL GROSS in USD. Rate is marginal above that threshold.
_TAX_BRACKETS: dict[str, list[tuple[float, float]]] = {

    # ── United States (federal + avg state ~5%) ──
    "US": [
        (11600,   0.10),
        (47150,   0.17),   # 12% fed + 5% avg state
        (100525,  0.27),
        (191950,  0.29),
        (243725,  0.31),
        (609350,  0.35),
        (float("inf"), 0.42),
    ],

    # ── United Kingdom ──
    "GB": [
        (14800,   0.20),   # personal allowance ~£12,570 + NI
        (62700,   0.40),
        (float("inf"), 0.45),
    ],

    # ── Germany ──
    "DE": [
        (12096,   0.00),
        (17005,   0.25),
        (66760,   0.42),
        (float("inf"), 0.45),
    ],

    # ── France ──
    "FR": [
        (10777,   0.00),
        (27478,   0.23),
        (78570,   0.41),
        (168994,  0.45),
        (float("inf"), 0.49),
    ],

    # ── India ──
    "IN": [
        (3900,    0.00),   # ~₹325,000
        (7800,    0.05),
        (15600,   0.10),
        (23400,   0.15),
        (39000,   0.20),
        (78000,   0.25),
        (float("inf"), 0.30),
    ],

    # ── Canada (federal + avg provincial ~9%) ──
    "CA": [
        (55867,   0.24),
        (111733,  0.33),
        (154906,  0.36),
        (220000,  0.41),
        (float("inf"), 0.44),
    ],

    # ── Australia ──
    "AU": [
        (14700,   0.00),
        (36300,   0.19),
        (86900,   0.32),
        (130300,  0.37),
        (float("inf"), 0.45),
    ],

    # ── Singapore ──
    "SG": [
        (13600,   0.00),
        (27200,   0.02),
        (40800,   0.035),
        (54400,   0.07),
        (68000,   0.115),
        (136000,  0.15),
        (204000,  0.18),
        (272000,  0.19),
        (340000,  0.195),
        (float("inf"), 0.22),
    ],

    # ── Netherlands ──
    "NL": [
        (40000,   0.368),
        (float("inf"), 0.495),
    ],

    # ── Sweden ──
    "SE": [
        (20000,   0.30),
        (float("inf"), 0.52),
    ],

    # ── Norway ──
    "NO": [
        (14000,   0.22),
        (100000,  0.34),
        (float("inf"), 0.47),
    ],

    # ── Denmark ──
    "DK": [
        (8000,    0.00),
        (60000,   0.37),
        (float("inf"), 0.55),
    ],

    # ── Switzerland ──
    "CH": [
        (14500,   0.00),
        (31600,   0.12),
        (82000,   0.22),
        (150000,  0.28),
        (float("inf"), 0.33),
    ],

    # ── Japan ──
    "JP": [
        (18000,   0.15),
        (36000,   0.25),
        (90000,   0.33),
        (150000,  0.40),
        (220000,  0.45),
        (float("inf"), 0.55),
    ],

    # ── China ──
    "CN": [
        (8800,    0.03),
        (16100,   0.10),
        (24000,   0.20),
        (41200,   0.25),
        (58000,   0.30),
        (82000,   0.35),
        (float("inf"), 0.45),
    ],

    # ── South Korea ──
    "KR": [
        (12000,   0.08),
        (46000,   0.165),
        (92000,   0.265),
        (140000,  0.385),
        (float("inf"), 0.45),
    ],

    # ── Brazil ──
    "BR": [
        (8800,    0.00),
        (14300,   0.075),
        (21000,   0.15),
        (26200,   0.225),
        (float("inf"), 0.275),
    ],

    # ── Mexico ──
    "MX": [
        (4000,    0.019),
        (8000,    0.064),
        (14000,   0.108),
        (24000,   0.16),
        (38000,   0.199),
        (60000,   0.237),
        (80000,   0.30),
        (float("inf"), 0.35),
    ],

    # ── Spain ──
    "ES": [
        (12450,   0.19),
        (20200,   0.24),
        (35200,   0.30),
        (60000,   0.37),
        (300000,  0.45),
        (float("inf"), 0.47),
    ],

    # ── Italy ──
    "IT": [
        (15000,   0.23),
        (28000,   0.25),
        (50000,   0.35),
        (float("inf"), 0.43),
    ],

    # ── Portugal ──
    "PT": [
        (7703,    0.00),
        (11623,   0.145),
        (16472,   0.21),
        (21321,   0.265),
        (27146,   0.285),
        (39791,   0.35),
        (51997,   0.37),
        (81199,   0.43),
        (float("inf"), 0.48),
    ],

    # ── Ireland ──
    "IE": [
        (40000,   0.29),
        (float("inf"), 0.52),
    ],

    # ── Poland ──
    "PL": [
        (11000,   0.00),
        (34000,   0.17),
        (float("inf"), 0.32),
    ],

    # ── UAE (no income tax) ──
    "AE": [
        (float("inf"), 0.00),
    ],

    # ── Saudi Arabia (no income tax for employees) ──
    "SA": [
        (float("inf"), 0.00),
    ],

    # ── Kuwait ──
    "KW": [
        (float("inf"), 0.00),
    ],

    # ── Qatar ──
    "QA": [
        (float("inf"), 0.00),
    ],

    # ── Bahrain ──
    "BH": [
        (float("inf"), 0.03),  # social insurance only
    ],

    # ── Israel ──
    "IL": [
        (16000,   0.10),
        (22000,   0.14),
        (30000,   0.20),
        (50000,   0.31),
        (90000,   0.35),
        (float("inf"), 0.50),
    ],

    # ── Turkey ──
    "TR": [
        (9500,    0.15),
        (30000,   0.20),
        (70000,   0.27),
        (240000,  0.35),
        (float("inf"), 0.40),
    ],

    # ── Russia ──
    "RU": [
        (float("inf"), 0.13),  # flat (15% above 5M RUB; simplified)
    ],

    # ── Ukraine ──
    "UA": [
        (float("inf"), 0.195),  # 18% income + 1.5% military
    ],

    # ── Pakistan ──
    "PK": [
        (7000,    0.00),
        (11000,   0.025),
        (20000,   0.125),
        (40000,   0.20),
        (80000,   0.25),
        (float("inf"), 0.35),
    ],

    # ── Nigeria ──
    "NG": [
        (7000,    0.07),
        (15000,   0.11),
        (27000,   0.15),
        (47000,   0.19),
        (73000,   0.21),
        (float("inf"), 0.24),
    ],

    # ── South Africa ──
    "ZA": [
        (15000,   0.18),
        (23000,   0.26),
        (38000,   0.31),
        (52000,   0.36),
        (77000,   0.39),
        (115000,  0.41),
        (float("inf"), 0.45),
    ],

    # ── Egypt ──
    "EG": [
        (7200,    0.00),
        (13000,   0.10),
        (23000,   0.15),
        (40000,   0.20),
        (float("inf"), 0.25),
    ],

    # ── Greece ──
    "GR": [
        (10000,   0.09),
        (20000,   0.22),
        (30000,   0.28),
        (40000,   0.36),
        (float("inf"), 0.44),
    ],

    # ── Czech Republic ──
    "CZ": [
        (40000,   0.19),  # 15% + social ~4%
        (float("inf"), 0.23),
    ],

    # ── Hungary ──
    "HU": [
        (float("inf"), 0.185),  # 15% flat + social 18.5%... effective ~18.5
    ],

    # ── Romania ──
    "RO": [
        (float("inf"), 0.25),  # 10% income + ~social contributions
    ],

    # ── Belgium ──
    "BE": [
        (14000,   0.25),
        (26000,   0.40),
        (45000,   0.45),
        (float("inf"), 0.50),
    ],

    # ── Austria ──
    "AT": [
        (11000,   0.00),
        (18000,   0.20),
        (31000,   0.35),
        (60000,   0.42),
        (90000,   0.48),
        (1000000, 0.50),
        (float("inf"), 0.55),
    ],

    # ── New Zealand ──
    "NZ": [
        (14000,   0.105),
        (48000,   0.175),
        (70000,   0.30),
        (float("inf"), 0.33),
    ],

    # ── Malaysia ──
    "MY": [
        (6500,    0.00),
        (13000,   0.01),
        (21500,   0.03),
        (35000,   0.08),
        (58000,   0.135),
        (83000,   0.21),
        (250000,  0.24),
        (float("inf"), 0.30),
    ],

    # ── Indonesia ──
    "ID": [
        (6000,    0.05),
        (17000,   0.15),
        (37000,   0.25),
        (100000,  0.30),
        (float("inf"), 0.35),
    ],

    # ── Thailand ──
    "TH": [
        (8000,    0.00),
        (16000,   0.05),
        (24000,   0.10),
        (40000,   0.15),
        (60000,   0.20),
        (120000,  0.25),
        (float("inf"), 0.35),
    ],

    # ── Philippines ──
    "PH": [
        (8500,    0.00),
        (16000,   0.20),
        (28000,   0.25),
        (44000,   0.30),
        (80000,   0.32),
        (float("inf"), 0.35),
    ],

    # ── Vietnam ──
    "VN": [
        (5800,    0.05),
        (11600,   0.10),
        (17300,   0.15),
        (28800,   0.20),
        (46200,   0.25),
        (90000,   0.30),
        (float("inf"), 0.35),
    ],

    # ── Argentina ──
    "AR": [
        (9000,    0.05),
        (18000,   0.09),
        (27000,   0.12),
        (45000,   0.15),
        (90000,   0.19),
        (float("inf"), 0.27),
    ],

    # ── Colombia ──
    "CO": [
        (10000,   0.00),
        (20000,   0.19),
        (35000,   0.28),
        (float("inf"), 0.33),
    ],

    # ── Chile ──
    "CL": [
        (8300,    0.00),
        (18500,   0.04),
        (30800,   0.08),
        (43000,   0.135),
        (55500,   0.23),
        (83000,   0.304),
        (110000,  0.35),
        (float("inf"), 0.40),
    ],

    # ── Luxembourg ──
    "LU": [
        (15000,   0.08),
        (38000,   0.26),
        (60000,   0.38),
        (float("inf"), 0.42),
    ],

    # ── Hong Kong ──
    "HK": [
        (20000,   0.02),
        (40000,   0.06),
        (60000,   0.10),
        (80000,   0.14),
        (float("inf"), 0.17),
    ],

    # ── Kenya ──
    "KE": [
        (3000,    0.10),
        (7000,    0.25),
        (13000,   0.30),
        (float("inf"), 0.35),
    ],

    # ── Ghana ──
    "GH": [
        (3600,    0.00),
        (5000,    0.05),
        (7000,    0.10),
        (13500,   0.175),
        (21000,   0.25),
        (float("inf"), 0.30),
    ],

    # ── Morocco ──
    "MA": [
        (3500,    0.00),
        (5000,    0.10),
        (7000,    0.20),
        (13000,   0.30),
        (20000,   0.34),
        (float("inf"), 0.38),
    ],
}

# Name/alias resolution is handled by country_utils.resolve_iso2().
# The local alias dict has been removed; all lookups go through that function.

# Extra flat-rate defaults for countries not individually listed
_FLAT_RATE_DEFAULTS: dict[str, float] = {
    "LV": 0.23, "LT": 0.23, "EE": 0.22, "SK": 0.25,
    "HR": 0.25, "BG": 0.20, "RS": 0.20, "AL": 0.23,
    "BA": 0.20, "MK": 0.18, "MD": 0.18, "AM": 0.22,
    "GE": 0.20, "AZ": 0.22, "KZ": 0.20, "UZ": 0.22,
    "TN": 0.30, "DZ": 0.27, "ET": 0.30, "UG": 0.30,
    "TZ": 0.30, "CF": 0.30, "LY": 0.20,
    "IQ": 0.15, "IR": 0.25, "JO": 0.20, "OM": 0.00,
    "YE": 0.15, "SY": 0.20, "LB": 0.20,
    "BD": 0.25, "LK": 0.24, "NP": 0.25,
    "MM": 0.25, "KH": 0.20, "LA": 0.24,
    "MN": 0.20, "TW": 0.20, "AF": 0.20,
    "CY": 0.25, "MT": 0.25, "JE": 0.20,
    "PR": 0.30,  # US territory — complex
    "AS": 0.30,
    "SI": 0.22,
    "MX": 0.25,  # already in brackets but alias
    "CL": 0.18,
    "BO": 0.25, "UY": 0.30, "PY": 0.15,
    "DO": 0.25, "CR": 0.25, "HN": 0.25,
    "BS": 0.00,  # no income tax
    "PE": 0.30,
    "VE": 0.34,
    "CU": 0.20,
    "EC": 0.28,
    "GT": 0.25,
    "PA": 0.25,
    "SV": 0.30,
    "NI": 0.30,
}

# Generic world fallback
_GENERIC_RATE = 0.25


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _resolve_country_key(location_hint: Optional[str]) -> Optional[str]:
    """
    Map any country name, alias, or ISO-2 code to the canonical bracket key.
    Delegates name/alias resolution to country_utils.resolve_iso2(); falls back
    to a direct dict lookup for any key already present in _TAX_BRACKETS or
    _FLAT_RATE_DEFAULTS.
    """
    if not location_hint:
        return None
    # Full alias + CLDR coverage via country_utils
    iso = resolve_iso2(location_hint)
    if iso:
        if iso in _TAX_BRACKETS or iso in _FLAT_RATE_DEFAULTS:
            return iso
    # Direct key match as a last resort
    direct = str(location_hint).strip().upper()
    if direct in _TAX_BRACKETS or direct in _FLAT_RATE_DEFAULTS:
        return direct
    # Return the resolved ISO even if not in our tables (caller handles generic)
    return iso or None


def get_effective_rate(
    gross_usd: float,
    location_hint: Optional[str] = None,
    custom_rate: Optional[float] = None,
) -> tuple[float, str, str]:
    """
    Return the effective tax rate for a given gross salary and country.

    Parameters
    ----------
    gross_usd     : Annual gross salary in USD.
    location_hint : Country name or ISO-2 code. Ignored if custom_rate set.
    custom_rate   : Override rate (0.0–1.0). If provided, skips built-in data.

    Returns
    -------
    (rate, source_label, country_key)
      rate          : float 0.0–1.0
      source_label  : "custom" | "brackets" | "flat_default" | "generic"
      country_key   : resolved key used, or "" if unknown
    """
    if custom_rate is not None:
        rate = max(0.0, min(1.0, custom_rate))
        return rate, "custom", ""

    country_key = _resolve_country_key(location_hint)

    # Progressive brackets
    if country_key and country_key in _TAX_BRACKETS:
        brackets = _TAX_BRACKETS[country_key]
        total_tax = 0.0
        prev = 0.0
        for (threshold, rate) in brackets:
            if gross_usd <= prev:
                break
            taxable = min(gross_usd, threshold) - prev
            total_tax += taxable * rate
            prev = threshold
            if threshold == float("inf") or gross_usd <= threshold:
                break
        effective = total_tax / gross_usd if gross_usd > 0 else 0.0
        return effective, "brackets", country_key or ""

    # Flat default
    if country_key and country_key in _FLAT_RATE_DEFAULTS:
        return _FLAT_RATE_DEFAULTS[country_key], "flat_default", country_key
    # resolve_iso2 is already called inside _resolve_country_key, so if
    # country_key is set it is the canonical ISO-2.  No further alias lookup
    # is needed here.

    return _GENERIC_RATE, "generic", country_key or ""


def compute_post_tax(
    gross_usd: float,
    location_hint: Optional[str] = None,
    custom_rate: Optional[float] = None,
) -> dict:
    """
    Compute post-tax salary in USD.

    Returns dict with:
      gross_usd       : original value
      tax_rate        : effective rate used (0.0–1.0)
      tax_amount_usd  : estimated tax in USD
      net_usd         : post-tax annual USD
      net_monthly_usd : post-tax monthly USD
      net_weekly_usd  : post-tax weekly USD
      net_hourly_usd  : post-tax hourly (40hr/week)
      rate_source     : "custom" | "brackets" | "flat_default" | "generic"
      country_key     : canonical country key used
    """
    rate, source, ckey = get_effective_rate(gross_usd, location_hint, custom_rate)
    tax_amt = gross_usd * rate
    net = gross_usd - tax_amt
    return {
        "gross_usd": gross_usd,
        "tax_rate": rate,
        "tax_amount_usd": tax_amt,
        "net_usd": net,
        "net_monthly_usd": net / 12,
        "net_weekly_usd": net / 52,
        "net_hourly_usd": net / (52 * 40),
        "rate_source": source,
        "country_key": ckey,
    }


def compute_post_tax_converted(
    gross_usd: float,
    location_hint: Optional[str] = None,
    custom_rate: Optional[float] = None,
    target_currency: Optional[str] = None,
    rates: Optional[dict] = None,
) -> dict:
    """
    Compute post-tax values and optionally convert to a target currency.
    Useful for Tab 3/4 or for combined tax+currency calculations.

    `rates` should be the dict from currency_utils.get_exchange_rates()["rates"].
    If rates is None and target_currency is set, attempts to import currency_utils.
    """
    result = compute_post_tax(gross_usd, location_hint, custom_rate)

    if target_currency and target_currency.upper() != "USD":
        if rates is None:
            try:
                from currency_utils import get_exchange_rates
                rates = get_exchange_rates()["rates"]
            except ImportError:
                rates = {}

        rate_fx = rates.get(target_currency.upper(), 1.0)
        result["net_converted"] = result["net_usd"] * rate_fx
        result["net_monthly_converted"] = result["net_monthly_usd"] * rate_fx
        result["net_weekly_converted"] = result["net_weekly_usd"] * rate_fx
        result["net_hourly_converted"] = result["net_hourly_usd"] * rate_fx
        result["target_currency"] = target_currency.upper()
        result["fx_rate"] = rate_fx
    else:
        result["target_currency"] = "USD"
        result["fx_rate"] = 1.0

    return result


# ---------------------------------------------------------------------------
# Custom rates file (save / load for offline / personalisation)
# ---------------------------------------------------------------------------

def load_custom_tax_file(filepath: Optional[str] = None) -> dict:
    """
    Load a custom tax rates JSON file.
    Expected format: { "US": 0.28, "IN": 0.20, ... }
    Returns dict of overrides (empty dict if file not found/invalid).
    """
    filepath = filepath or _TAX_FALLBACK_FILE_PATH
    if not os.path.isfile(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}
    except Exception:
        return {}


def save_custom_tax_file(overrides: dict, filepath: Optional[str] = None) -> bool:
    """Save custom tax rate overrides to a JSON file. Returns True on success."""
    filepath = filepath or _TAX_FALLBACK_FILE_PATH
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Source explanation strings
# ---------------------------------------------------------------------------

_SOURCE_NOTES = {
    "custom":       "Using your custom override rate.",
    "brackets":     "Using progressive tax brackets (income tax + est. social contributions).",
    "flat_default": "Using an estimated flat effective rate for this country.",
    "generic":      "Country not recognised — using a generic 25% placeholder.",
}


# ---------------------------------------------------------------------------
# Streamlit UI widget
# ---------------------------------------------------------------------------

def render_tax_adjuster(
    gross_usd: float,
    location_hint: Optional[str] = None,
    widget_key: str = "tax",
    converted_amount: Optional[float] = None,
    converted_currency: Optional[str] = None,
    rates: Optional[dict] = None,
) -> None:
    """
    Streamlit widget: toggle → expander with post-tax salary display.

    Parameters
    ----------
    gross_usd          : Annual gross salary in USD.
    location_hint      : Country name or ISO-2 to auto-select tax rate.
    widget_key         : Unique prefix per call-site.
    converted_amount   : If currency conversion was done, pass the converted annual amount.
    converted_currency : The currency code of converted_amount (e.g. "INR").
    rates              : Exchange rate dict from currency_utils (for cross-currency display).

    NOTE: The existing USD prediction cards are NOT modified.
    This widget is purely additive.
    """

    toggle_key = f"{widget_key}_tax_toggle"
    custom_key = f"{widget_key}_custom_rate_toggle"
    slider_key = f"{widget_key}_rate_slider"
    file_load_key = f"{widget_key}_load_file"

    show_tax = st.toggle(
        ":material/receipt_long: Show Tax Adjustment",
        help="Show estimated post-tax salary based on country-specific tax rates.",
        key=toggle_key,
        value=False,
    )

    if not show_tax:
        return

    # Load any saved custom overrides from file
    saved_overrides = load_custom_tax_file()

    # Resolve country key for looking up saved override
    country_key = _resolve_country_key(location_hint) or ""
    saved_rate_for_country = saved_overrides.get(country_key)

    with st.expander(":material/percent: Tax Estimation", expanded=True):

        st.caption(
            ":material/warning: **Disclaimer:** Tax estimates are approximate and for planning only. "
            "Actual tax depends on deductions, filing status, local taxes, and other factors. "
            "This is not financial or legal advice."
        )

        # --- Built-in estimate ---
        built_in_rate, built_in_source, _ = get_effective_rate(gross_usd, location_hint)
        built_in_pct = round(built_in_rate * 100, 1)

        col_info1, col_info2 = st.columns(2)
        with col_info1:
            if location_hint and location_hint not in ("Other", ""):
                display_country = get_country_name(country_key) if country_key else (location_hint or "Unknown")

                st.info(
                    f"**Country detected:** {display_country}\n\n"
                    f"**Estimated effective rate:** {built_in_pct}%\n\n"
                    f"_{_SOURCE_NOTES.get(built_in_source, '')}_"
                )
            else:
                st.info(
                    "No country detected. Using generic 25% rate.\n\n"
                    "Use the custom rate below for accuracy."
                )
        if _is_local():
            with col_info2:
                if saved_rate_for_country is not None:
                    st.success(
                        f"A saved custom rate for **{country_key}** was found: "
                        f"**{saved_rate_for_country * 100:.1f}%**\n\n"
                        "Enable 'Use custom rate' below to apply it."
                    )
                else:
                    st.markdown(
                        "**No saved custom rate for this country.**\n\n"
                        "You can enter one below and save it for future sessions."
                    )

        # --- Custom rate toggle ---
        use_custom = st.toggle(
            "Use custom / override tax rate",
            key=custom_key,
            value=False,
            help="Override the built-in estimate with your own effective rate."
        )

        custom_rate_value: Optional[float] = None

        if use_custom:
            # Pre-fill with saved rate if available
            prefill = saved_rate_for_country * 100 if saved_rate_for_country else built_in_pct
            prefill = float(min(max(prefill, 0.0), 80.0))

            custom_pct = st.slider(
                "Effective tax rate (%)",
                min_value=0.0,
                max_value=80.0,
                value=prefill,
                step=0.5,
                key=slider_key,
                help=(
                    "Enter your actual or expected effective tax rate. "
                    "This includes all income taxes and social contributions "
                    "as a percentage of gross salary."
                )
            )
            custom_rate_value = custom_pct / 100.0

            if _is_local():
                col_save, col_reset = st.columns(2)
                with col_save:
                    if st.button(
                        ":material/save: Save rate for this country",
                        key=f"{widget_key}_save_custom",
                        help=f"Saves {custom_pct}% for {country_key or 'unknown'} to tax_rates_custom.json",
                        disabled=not bool(country_key)
                    ):
                        updated = dict(saved_overrides)
                        updated[country_key] = custom_rate_value
                        ok = save_custom_tax_file(updated)
                        if ok:
                            st.success(f"Saved {custom_pct:.1f}% for {country_key}.")
                        else:
                            st.error("Could not write tax_rates_custom.json.")
                with col_reset:
                    if st.button(
                        ":material/delete: Remove saved rate",
                        key=f"{widget_key}_remove_custom",
                        disabled=not bool(saved_rate_for_country)
                    ):
                        updated = {k: v for k, v in saved_overrides.items() if k != country_key}
                        save_custom_tax_file(updated)
                        st.success(f"Removed saved rate for {country_key}.")
                        st.rerun()

        # --- Compute ---
        final_result = compute_post_tax(
            gross_usd,
            location_hint,
            custom_rate=custom_rate_value,
        )

        effective_pct = final_result["tax_rate"] * 100
        net_annual = final_result["net_usd"]
        tax_amt = final_result["tax_amount_usd"]

        st.divider()

        # --- Display: gross → tax → net ---
        col_g, col_t, col_n = st.columns(3)
        col_g.metric("Gross Annual (USD)", f"${gross_usd:,.0f}")
        col_t.metric(
            f"Est. Tax ({effective_pct:.1f}%)",
            f"${tax_amt:,.0f}",
            delta=f"-{effective_pct:.1f}%",
            delta_color="inverse"
        )
        col_n.metric("Est. Net Annual (USD)", f"${net_annual:,.0f}")

        # --- Net breakdown ---
        st.markdown(
            f"""
            <div style='
                background: linear-gradient(135deg, #1A2535 0%, #1B2230 100%);
                border: 1px solid #2D3A50;
                border-left: 5px solid #F59E0B;
                border-radius: 10px;
                padding: 18px 24px;
                text-align: center;
                margin: 8px auto;
            '>
                <div style='color:#9CA6B5; font-size:12px; font-weight:600;
                            letter-spacing:0.5px; margin-bottom:6px;'>
                    ESTIMATED NET ANNUAL SALARY (USD, POST-TAX)
                </div>
                <div style='color:#F59E0B; font-size:34px; font-weight:700;
                            letter-spacing:-1px;'>
                    ${net_annual:,.2f}
                </div>
                <div style='color:#6B7585; font-size:12px; margin-top:6px;'>
                    After est. {effective_pct:.1f}% effective tax on ${gross_usd:,.2f} gross
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_m, col_w, col_h = st.columns(3)
        col_m.metric("Net Monthly (USD)", f"${final_result['net_monthly_usd']:,.2f}")
        col_w.metric("Net Weekly (USD)", f"${final_result['net_weekly_usd']:,.2f}")
        col_h.metric("Net Hourly (USD)", f"${final_result['net_hourly_usd']:,.2f}")

        # --- If currency conversion was also done, show net in target currency ---
        if converted_currency and converted_currency.upper() != "USD":
            st.divider()
            st.markdown(
                f"#### Post-Tax in {converted_currency.upper()}"
            )

            # Get fx rate
            fx_rate = 1.0
            if rates:
                fx_rate = rates.get(converted_currency.upper(), 1.0)
            else:
                try:
                    from currency_utils import get_exchange_rates
                    fx_rate = get_exchange_rates()["rates"].get(converted_currency.upper(), 1.0)
                except ImportError:
                    pass

            net_converted = net_annual * fx_rate
            net_monthly_conv = final_result["net_monthly_usd"] * fx_rate
            net_weekly_conv = final_result["net_weekly_usd"] * fx_rate
            net_hourly_conv = final_result["net_hourly_usd"] * fx_rate

            # Try to get symbol
            try:
                from currency_utils import CURRENCY_INFO, _format_params
                sym, dec = _format_params(converted_currency.upper())
            except ImportError:
                sym, dec = converted_currency.upper() + " ", 2

            fmt = (lambda v: f"{sym}{v:,.0f} {converted_currency.upper()}") if dec == 0 else \
                  (lambda v: f"{sym}{v:,.2f} {converted_currency.upper()}")

            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1A2535 0%, #1B2230 100%);
                    border: 1px solid #2D3A50;
                    border-left: 5px solid #A78BFA;
                    border-radius: 10px;
                    padding: 18px 24px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color:#9CA6B5; font-size:12px; font-weight:600;
                                letter-spacing:0.5px; margin-bottom:6px;'>
                        ESTIMATED NET ANNUAL ({converted_currency.upper()}, POST-TAX)
                    </div>
                    <div style='color:#A78BFA; font-size:34px; font-weight:700;
                                letter-spacing:-1px;'>
                        {fmt(net_converted)}
                    </div>
                    <div style='color:#6B7585; font-size:12px; margin-top:6px;'>
                        At 1 USD = {fx_rate:.4f} {converted_currency.upper()}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_mc, col_wc, col_hc = st.columns(3)
            col_mc.metric(f"Net Monthly ({converted_currency.upper()})", fmt(net_monthly_conv))
            col_wc.metric(f"Net Weekly ({converted_currency.upper()})", fmt(net_weekly_conv))
            col_hc.metric(f"Net Hourly ({converted_currency.upper()})", fmt(net_hourly_conv))

        st.caption(
            "Estimates include income tax and approximate social security contributions. "
            "Local/municipal taxes, deductions, and allowances are not modelled. "
            "Consult a local tax professional for precise figures."
        )