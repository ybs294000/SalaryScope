"""
currency_utils.py — SalaryScope Currency Conversion Utility
============================================================
Features:
  - Fetches live exchange rates from a free public API (no key needed)
  - Graceful fallback if network is unavailable
  - Optional fallback: load rates from a local JSON file
  - Core conversion functions usable in any tab
  - Streamlit UI helpers for Tab 1 & Tab 2 (toggle + expander + dropdown)
  - Does NOT modify any existing USD prediction output

Usage in app.py (Tab 1 / Tab 2 result section):
    from currency_utils import render_currency_converter

    # After your existing USD prediction display:
    render_currency_converter(
        usd_amount=prediction,          # the predicted salary in USD
        location_hint=country,          # ISO-2 or plain country name (optional, for default currency)
        widget_key="manual_a1"          # unique key prefix per call-site
    )
"""

import json
import os
import threading
from datetime import datetime, timedelta
from typing import Optional

import requests
import streamlit as st

from app.utils.country_utils import resolve_iso2
from app.tabs.admin_panel import _is_local
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Primary free API — no key required, updated daily
_EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"

# How long to keep cached rates in memory before re-fetching (minutes)
_CACHE_TTL_MINUTES = 60

# Default path for the offline fallback rates file
# Users can place a file here and it will be loaded when the network is down
_FALLBACK_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "exchange_rates_fallback.json"
)

# ---------------------------------------------------------------------------
# Currency metadata: code → (display name, symbol)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Currency metadata: code -> (display name, symbol)
# Symbol values use Unicode escape sequences to stay ASCII-safe in source files.
#
# Quick reference for the escapes used below:
#   \u0024  $     US Dollar / generic dollar sign
#   \u00a3  £     Pound Sterling
#   \u00a5  ¥     Yen / Yuan
#   \u20ac  €     Euro
#   \u20b9  ₹     Indian Rupee
#   \u20a9  ₩     Korean Won
#   \u20b1  ₱     Philippine Peso
#   \u20ba  ₺     Turkish Lira
#   \u20bd  ₽     Russian Ruble
#   \u20aa  ₪     Israeli New Shekel
#   \u20ab  ₫     Vietnamese Dong
#   \u20ae  ₮     Mongolian Togrog
#   \u20ad  ₭     Lao Kip
#   \u20bf  ₿     (unused — listed for completeness)
#   \u09f3  ৳     Bangladeshi Taka
#   \u0e3f  ฿     Thai Baht
#   \u20b4  ₴     Ukrainian Hryvnia
#   \u20b8  ₸     Kazakhstani Tenge
#   \u20bc  ₼     Azerbaijani Manat
#   \u20be  ₾     Georgian Lari
#   \u058f  ֏     Armenian Dram
#   \u20a8  ₨     Pakistani / Sri Lankan Rupee
#   \u20a6  ₦     Nigerian Naira
#   \u20a1  \u20a1  Costa Rican Colon  (₡)
#   \u20b2  ₲     Paraguayan Guarani
#   \u0192  ƒ     (unused here)
#   \u060b  ؋     Afghan Afghani
# ---------------------------------------------------------------------------
CURRENCY_INFO: dict[str, tuple[str, str]] = {
    "USD": ("US Dollar",                    "\u0024"),
    "EUR": ("Euro",                         "\u20ac"),
    "GBP": ("British Pound",               "\u00a3"),
    "INR": ("Indian Rupee",                "\u20b9"),
    "CAD": ("Canadian Dollar",             "CA\u0024"),
    "AUD": ("Australian Dollar",           "A\u0024"),
    "JPY": ("Japanese Yen",               "\u00a5"),
    "CNY": ("Chinese Yuan",               "\u00a5"),
    "CHF": ("Swiss Franc",                "CHF"),
    "SGD": ("Singapore Dollar",           "S\u0024"),
    "AED": ("UAE Dirham",                 "AED"),
    "SAR": ("Saudi Riyal",               "SAR"),
    "MXN": ("Mexican Peso",              "MX\u0024"),
    "BRL": ("Brazilian Real",            "R\u0024"),
    "ZAR": ("South African Rand",        "R"),
    "KRW": ("South Korean Won",          "\u20a9"),
    "HKD": ("Hong Kong Dollar",          "HK\u0024"),
    "SEK": ("Swedish Krona",             "SEK"),
    "NOK": ("Norwegian Krone",           "NOK"),
    "DKK": ("Danish Krone",              "DKK"),
    "PLN": ("Polish Zloty",              "PLN"),
    "TRY": ("Turkish Lira",              "\u20ba"),
    "RUB": ("Russian Ruble",             "\u20bd"),
    "IDR": ("Indonesian Rupiah",         "Rp"),
    "MYR": ("Malaysian Ringgit",         "RM"),
    "THB": ("Thai Baht",                 "\u0e3f"),
    "PHP": ("Philippine Peso",           "\u20b1"),
    "PKR": ("Pakistani Rupee",           "\u20a8"),
    "NGN": ("Nigerian Naira",            "\u20a6"),
    "EGP": ("Egyptian Pound",            "EGP"),
    "ILS": ("Israeli Shekel",            "\u20aa"),
    "NZD": ("New Zealand Dollar",        "NZ\u0024"),
    "CZK": ("Czech Koruna",              "Kc"),
    "HUF": ("Hungarian Forint",          "Ft"),
    "RON": ("Romanian Leu",              "RON"),
    "HRK": ("Croatian Kuna",             "kn"),
    "BGN": ("Bulgarian Lev",             "BGN"),
    "UAH": ("Ukrainian Hryvnia",         "\u20b4"),
    "CLP": ("Chilean Peso",              "CL\u0024"),
    "COP": ("Colombian Peso",            "COP"),
    "ARS": ("Argentine Peso",            "ARS"),
    "VND": ("Vietnamese Dong",           "\u20ab"),
    "BDT": ("Bangladeshi Taka",          "\u09f3"),
    "LKR": ("Sri Lankan Rupee",          "LKR"),
    "KWD": ("Kuwaiti Dinar",             "KD"),
    "QAR": ("Qatari Riyal",              "QR"),
    "OMR": ("Omani Rial",               "OMR"),
    "BHD": ("Bahraini Dinar",            "BD"),
    "MAD": ("Moroccan Dirham",           "MAD"),
    "DZD": ("Algerian Dinar",            "DZD"),
    "TND": ("Tunisian Dinar",            "TND"),
    "GHS": ("Ghanaian Cedi",             "GHS"),
    "KES": ("Kenyan Shilling",           "KES"),
    "UGX": ("Ugandan Shilling",          "UGX"),
    "TZS": ("Tanzanian Shilling",        "TZS"),
    "CRC": ("Costa Rican Colon",         "\u20a1"),
    "DOP": ("Dominican Peso",            "DOP"),
    "PEN": ("Peruvian Sol",              "S/"),
    "BOB": ("Bolivian Boliviano",        "Bs"),
    "PYG": ("Paraguayan Guarani",        "\u20b2"),
    "UYU": ("Uruguayan Peso",            "UYU"),
    "UZS": ("Uzbekistani Som",           "UZS"),
    "AMD": ("Armenian Dram",             "\u058f"),
    "GEL": ("Georgian Lari",             "\u20be"),
    "AZN": ("Azerbaijani Manat",         "\u20bc"),
    "KZT": ("Kazakhstani Tenge",         "\u20b8"),
    "MKD": ("Macedonian Denar",          "MKD"),
    "RSD": ("Serbian Dinar",             "RSD"),
    "ALL": ("Albanian Lek",              "ALL"),
    "BAM": ("Bosnia-Herzegovina Mark",   "KM"),
    "MDL": ("Moldovan Leu",              "MDL"),
    "MNT": ("Mongolian Togrog",          "\u20ae"),
    "MMK": ("Myanmar Kyat",              "K"),
    "KHR": ("Cambodian Riel",            "KHR"),
    "LAK": ("Laotian Kip",               "\u20ad"),
    "TWD": ("Taiwan Dollar",             "NT\u0024"),
    "NPR": ("Nepalese Rupee",            "NPR"),
    "AFN": ("Afghan Afghani",            "\u060b"),
    "IQD": ("Iraqi Dinar",               "IQD"),
    "IRR": ("Iranian Rial",              "IRR"),
    "JOD": ("Jordanian Dinar",           "JD"),
    "LBP": ("Lebanese Pound",            "LBP"),
    "SYP": ("Syrian Pound",              "SYP"),
    "YER": ("Yemeni Rial",               "YER"),
    "LYD": ("Libyan Dinar",              "LYD"),
}


# ---------------------------------------------------------------------------
# Country ISO-2 → default currency code
# (covers all countries in App 1 & App 2 and more)
# ---------------------------------------------------------------------------
COUNTRY_TO_CURRENCY: dict[str, str] = {
    # Americas
    "US": "USD", "CA": "CAD", "MX": "MXN",
    "BR": "BRL", "AR": "ARS", "CL": "CLP",
    "CO": "COP", "PE": "PEN", "BO": "BOB",
    "CR": "CRC", "DO": "DOP", "HN": "HNL",
    "PR": "USD", "BS": "BSD", "UY": "UYU",
    "PA": "PAB", "GT": "GTQ", "SV": "USD",
    "NI": "NIO", "CU": "CUP", "EC": "USD",
    "VE": "VES", "PY": "PYG",
    # Europe
    "GB": "GBP", "JE": "GBP",
    "DE": "EUR", "FR": "EUR", "ES": "EUR",
    "IT": "EUR", "PT": "EUR", "NL": "EUR",
    "BE": "EUR", "AT": "EUR", "IE": "EUR",
    "GR": "EUR", "FI": "EUR", "LU": "EUR",
    "SI": "EUR", "MT": "EUR", "CY": "EUR",
    "EE": "EUR", "LV": "EUR", "LT": "EUR",
    "SK": "EUR", "HR": "EUR",
    "CH": "CHF", "SE": "SEK", "NO": "NOK",
    "DK": "DKK", "PL": "PLN", "CZ": "CZK",
    "HU": "HUF", "RO": "RON", "BG": "BGN",
    "UA": "UAH", "RU": "RUB", "TR": "TRY",
    "RS": "RSD", "MK": "MKD", "AL": "ALL",
    "BA": "BAM", "MD": "MDL", "IS": "ISK",
    # CIS / Caucasus / Central Asia
    "AM": "AMD", "GE": "GEL", "AZ": "AZN",
    "KZ": "KZT", "UZ": "UZS", "KG": "KGS",
    "TJ": "TJS", "TM": "TMT", "BY": "BYR",
    # Middle East
    "AE": "AED", "SA": "SAR", "KW": "KWD",
    "QA": "QAR", "OM": "OMR", "BH": "BHD",
    "IL": "ILS", "IQ": "IQD", "IR": "IRR",
    "JO": "JOD", "LB": "LBP", "SY": "SYP",
    "YE": "YER", "LY": "LYD",
    # South Asia
    "IN": "INR", "PK": "PKR", "BD": "BDT",
    "LK": "LKR", "NP": "NPR", "AF": "AFN",
    # East / Southeast Asia
    "JP": "JPY", "CN": "CNY", "KR": "KRW",
    "HK": "HKD", "TW": "TWD", "SG": "SGD",
    "MY": "MYR", "TH": "THB", "PH": "PHP",
    "ID": "IDR", "VN": "VND", "MM": "MMK",
    "KH": "KHR", "MN": "MNT", "LA": "LAK",
    # Oceania
    "AU": "AUD", "NZ": "NZD", "AS": "USD",
    # Africa
    "ZA": "ZAR", "NG": "NGN", "EG": "EGP",
    "GH": "GHS", "KE": "KES", "MA": "MAD",
    "DZ": "DZD", "TN": "TND", "CF": "XAF",
    "TZ": "TZS", "UG": "UGX", "ET": "ETB",
}

# ---------------------------------------------------------------------------
# In-memory rate cache (shared across all Streamlit sessions via module state)
# Thread-safe via a lock so concurrent users don't double-fetch
# ---------------------------------------------------------------------------
_rate_cache: dict = {
    "rates": None,       # dict[str, float]  — rates relative to USD
    "fetched_at": None,  # datetime
    "source": None,      # "live" | "fallback_file" | "hardcoded"
    "error": None,       # str | None
}
_cache_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Hardcoded emergency rates (approximate mid-2024 values)
# Used only when both network AND fallback file are unavailable
# ---------------------------------------------------------------------------
_HARDCODED_RATES: dict[str, float] = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.5, "CAD": 1.36,
    "AUD": 1.53, "JPY": 149.5, "CNY": 7.24, "CHF": 0.90, "SGD": 1.34,
    "AED": 3.67, "SAR": 3.75, "MXN": 17.1, "BRL": 4.97, "ZAR": 18.5,
    "KRW": 1320.0, "HKD": 7.82, "SEK": 10.4, "NOK": 10.5, "DKK": 6.88,
    "PLN": 3.95, "TRY": 32.0, "RUB": 90.0, "IDR": 15600.0, "MYR": 4.65,
    "THB": 35.5, "PHP": 56.0, "PKR": 278.0, "NGN": 1480.0, "EGP": 31.0,
    "ILS": 3.7, "NZD": 1.63, "CZK": 22.8, "HUF": 355.0, "RON": 4.57,
    "HRK": 6.96, "BGN": 1.80, "UAH": 37.0, "CLP": 900.0, "COP": 3950.0,
    "ARS": 875.0, "VND": 24500.0, "BDT": 110.0, "LKR": 305.0,
    "KWD": 0.307, "QAR": 3.64, "OMR": 0.385, "BHD": 0.377,
    "MAD": 10.1, "DZD": 135.0, "TND": 3.1, "GHS": 13.5, "KES": 128.0,
    "CRC": 520.0, "DOP": 58.5, "PEN": 3.75, "BOB": 6.91, "UYU": 39.0,
    "UZS": 12700.0, "AMD": 390.0, "IRR": 42000.0, "IQD": 1310.0,
    "RSD": 107.0, "MKD": 56.5, "ALL": 96.0, "BAM": 1.80, "MDL": 17.8,
    "UAH": 37.0, "KZT": 449.0, "TWD": 31.7, "NPR": 133.0,
}


# ---------------------------------------------------------------------------
# Core: fetch or retrieve cached rates
# ---------------------------------------------------------------------------

def get_exchange_rates(
    fallback_file: Optional[str] = None,
) -> dict:
    """
    Returns a dict with keys:
      rates    : dict[str, float]  — multipliers from USD
      source   : "live" | "fallback_file" | "hardcoded"
      fetched_at: datetime | None
      error    : str | None        — human-readable note if degraded

    Priority:
      1. In-memory cache (if fresh)
      2. Live API fetch
      3. Fallback JSON file (if provided or default path exists)
      4. Hardcoded approximate rates
    """
    fallback_file = fallback_file or _FALLBACK_FILE_PATH

    with _cache_lock:
        # Return cache if still fresh
        if (
            _rate_cache["rates"] is not None
            and _rate_cache["fetched_at"] is not None
            and datetime.utcnow() - _rate_cache["fetched_at"] < timedelta(minutes=_CACHE_TTL_MINUTES)
        ):
            return dict(_rate_cache)

        # Try live fetch
        try:
            resp = requests.get(_EXCHANGE_API_URL, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") == "success" and "rates" in data:
                _rate_cache["rates"] = data["rates"]
                _rate_cache["fetched_at"] = datetime.utcnow()
                _rate_cache["source"] = "live"
                _rate_cache["error"] = None
                return dict(_rate_cache)
        except Exception as exc:
            live_error = str(exc)
        else:
            live_error = "Unexpected API response format."

        # Try fallback file
        if os.path.isfile(fallback_file):
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                rates = file_data if isinstance(file_data, dict) else file_data.get("rates", {})
                if rates and "USD" in rates:
                    _rate_cache["rates"] = rates
                    _rate_cache["fetched_at"] = datetime.utcnow()
                    _rate_cache["source"] = "fallback_file"
                    _rate_cache["error"] = (
                        f"Live rates unavailable ({live_error}). "
                        f"Using rates from file: {os.path.basename(fallback_file)}."
                    )
                    return dict(_rate_cache)
            except Exception as file_exc:
                file_error = str(file_exc)
        else:
            file_error = "No fallback file found."

        # Final fallback: hardcoded
        _rate_cache["rates"] = _HARDCODED_RATES.copy()
        _rate_cache["fetched_at"] = datetime.utcnow()
        _rate_cache["source"] = "hardcoded"
        _rate_cache["error"] = (
            f"Live rates unavailable ({live_error}). "
            f"Fallback file unavailable ({file_error}). "
            "Using approximate built-in rates (may be outdated)."
        )
        return dict(_rate_cache)


# ---------------------------------------------------------------------------
# Core: convert USD amount to another currency
# ---------------------------------------------------------------------------

def convert_usd(
    usd_amount: float,
    target_currency: str,
    rates: Optional[dict[str, float]] = None,
) -> tuple[float, str]:
    """
    Convert a USD amount to target_currency.

    Returns:
        (converted_amount, formatted_string)

    If rates is None, fetches/caches automatically.
    """
    if rates is None:
        rate_data = get_exchange_rates()
        rates = rate_data["rates"]

    target = target_currency.upper()
    rate = rates.get(target)
    if rate is None:
        return usd_amount, f"${usd_amount:,.2f} USD (rate for {target} not available)"

    converted = usd_amount * rate
    symbol, decimals = _format_params(target)

    if decimals == 0:
        formatted = f"{symbol}{converted:,.0f} {target}"
    else:
        formatted = f"{symbol}{converted:,.2f} {target}"

    return converted, formatted


def _format_params(currency_code: str) -> tuple[str, int]:
    """Return (symbol, decimal_places) for a currency."""
    info = CURRENCY_INFO.get(currency_code.upper())
    symbol = info[1] if info else currency_code.upper() + " "
    # Zero-decimal currencies
    zero_decimal = {"JPY", "KRW", "VND", "IDR", "UGX", "TZS", "PYG",
                    "BIF", "CLP", "GNF", "MGA", "RWF", "XOF", "XAF",
                    "XPF", "IRR", "SYP", "YER", "NGN", "HUF"}
    decimals = 0 if currency_code.upper() in zero_decimal else 2
    return symbol, decimals


# ---------------------------------------------------------------------------
# Helper: guess default currency from a location string
# ---------------------------------------------------------------------------

def guess_currency(location_hint: Optional[str]) -> str:
    """
    Given a country name or ISO-2 code, return the most likely currency.
    Name/alias resolution is delegated to country_utils.resolve_iso2().
    Falls back to USD if the country or its currency cannot be determined.
    """
    if not location_hint:
        return "USD"
    # Resolve any name or alias to a canonical ISO-2 code
    iso = resolve_iso2(location_hint)
    if iso and iso in COUNTRY_TO_CURRENCY:
        return COUNTRY_TO_CURRENCY[iso]
    # Direct ISO-2 lookup as a final fallback (handles codes not in resolve_iso2)
    direct = str(location_hint).strip().upper()
    return COUNTRY_TO_CURRENCY.get(direct, "USD")


# ---------------------------------------------------------------------------
# Helper: build sorted dropdown list for Streamlit
# ---------------------------------------------------------------------------

def currency_dropdown_options() -> list[str]:
    """
    Returns list of strings like 'USD — US Dollar ($)' sorted with major
    currencies first, then alphabetically.
    """
    major = ["USD", "EUR", "GBP", "INR", "CAD", "AUD", "JPY", "CNY",
             "CHF", "SGD", "AED", "SAR", "MXN", "BRL", "ZAR", "KRW", "HKD"]
    result = []
    seen = set()
    rate_data = get_exchange_rates()
    available = set(rate_data["rates"].keys())

    for code in major:
        if code in available:
            info = CURRENCY_INFO.get(code, (code, code))
            result.append(f"{code} — {info[0]} ({info[1]})")
            seen.add(code)

    others = sorted(
        [c for c in available if c not in seen],
        key=lambda c: CURRENCY_INFO.get(c, (c, c))[0]
    )
    for code in others:
        info = CURRENCY_INFO.get(code, (code, code))
        result.append(f"{code} — {info[0]} ({info[1]})")

    return result


def parse_currency_option(option: str) -> str:
    """Extract the 3-letter code from a dropdown option string."""
    return option.split(" — ")[0].strip()


# ---------------------------------------------------------------------------
# Streamlit UI: save/load offline rates file
# ---------------------------------------------------------------------------

def save_rates_to_file(filepath: Optional[str] = None) -> bool:
    """
    Saves the current live rates to a JSON file for offline use.
    Returns True on success.
    """
    filepath = filepath or _FALLBACK_FILE_PATH
    rate_data = get_exchange_rates()
    if rate_data["source"] == "hardcoded":
        return False  # nothing useful to save
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(rate_data["rates"], f, indent=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Streamlit UI component — used in Tab 1 & Tab 2
# ---------------------------------------------------------------------------

def render_currency_converter(
    usd_amount: float,
    location_hint: Optional[str] = None,
    widget_key: str = "currency",
    show_breakdown: bool = True,
) -> None:
    """
    Renders a self-contained currency conversion widget for Streamlit.

    Parameters
    ----------
    usd_amount   : The predicted salary in USD (already shown by the app).
    location_hint: Country name or ISO-2 code to pre-select a currency.
    widget_key   : Unique string prefix to avoid widget key collisions.
    show_breakdown: If True, also shows monthly/weekly/hourly in target currency.

    Adds:
      • A toggle: "Show Currency Conversion"
      • If toggled on → an expander with dropdown + converted values
    """

    toggle_key = f"{widget_key}_currency_toggle"
    dropdown_key = f"{widget_key}_currency_dropdown"

    # --- Toggle ---
    show_conversion = st.toggle(
        ":material/currency_exchange: Show Currency Conversion",
        help="Convert your salary into a selected currency using current exchange rates.",
        key=toggle_key,
        value=False,
    )

    if not show_conversion:
        return

    # --- Fetch rates ---
    rate_data = get_exchange_rates()
    rates = rate_data["rates"]

    # --- Build dropdown options ---
    options = currency_dropdown_options()
    default_currency = guess_currency(location_hint)
    default_option = next(
        (o for o in options if o.startswith(default_currency + " — ")),
        options[0]
    )
    default_idx = options.index(default_option) if default_option in options else 0

    with st.expander(":material/currency_exchange: Currency Conversion", expanded=True):
        # Source status
        if rate_data["source"] == "live":
            fetched_str = rate_data["fetched_at"].strftime("%Y-%m-%d %H:%M UTC") if rate_data["fetched_at"] else "—"
            st.caption(f":material/check: Live exchange rates — last updated {fetched_str}")
        elif rate_data["source"] == "fallback_file":
            st.warning(f"material/warning: {rate_data['error']}")
        else:
            st.error(
                ":material/stop_circle: **No internet connection and no fallback file found.** "
                "Showing approximate built-in rates that may be outdated. "
                f"Details: {rate_data['error']}"
            )
            # Offer to load from file
            st.markdown(
                "**Tip:** Place a `exchange_rates_fallback.json` file in the `data` "
                "folder to use your own saved rates when offline."
            )

        # Currency selector
        selected_option = st.selectbox(
            "Select target currency",
            options,
            index=default_idx,
            key=dropdown_key,
        )
        target_code = parse_currency_option(selected_option)

        # Skip if USD selected (no point converting)
        if target_code == "USD":
            st.info("Target currency is already USD — no conversion needed.")
            return

        # Conversion
        converted_annual, annual_fmt = convert_usd(usd_amount, target_code, rates)

        # Annual
        st.markdown(
            f"""
            <div style='
                background: linear-gradient(135deg, #1A2535 0%, #1B2230 100%);
                border: 1px solid #2D3A50;
                border-left: 5px solid #34D399;
                border-radius: 10px;
                padding: 18px 24px;
                text-align: center;
                margin: 8px auto;
            '>
                <div style='color:#9CA6B5; font-size:12px; font-weight:600;
                            letter-spacing:0.5px; margin-bottom:6px;'>
                    ANNUAL SALARY ({target_code})
                </div>
                <div style='color:#34D399; font-size:34px; font-weight:700;
                            letter-spacing:-1px;'>
                    {annual_fmt}
                </div>
                <div style='color:#6B7585; font-size:12px; margin-top:6px;'>
                    Converted from ${usd_amount:,.2f} USD
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if show_breakdown:
            monthly_usd = usd_amount / 12
            weekly_usd = usd_amount / 52
            hourly_usd = usd_amount / (52 * 40)

            _, monthly_fmt = convert_usd(monthly_usd, target_code, rates)
            _, weekly_fmt = convert_usd(weekly_usd, target_code, rates)
            _, hourly_fmt = convert_usd(hourly_usd, target_code, rates)

            col1, col2, col3 = st.columns(3)
            col1.metric(f"Monthly ({target_code})", monthly_fmt.split(" ")[0])
            col2.metric(f"Weekly ({target_code})", weekly_fmt.split(" ")[0])
            col3.metric(f"Hourly ({target_code})", hourly_fmt.split(" ")[0])

        # Save-rates button (for offline use later)
        if rate_data["source"] == "live":
            if _is_local():
                if st.button(
                    ":material/save: Save rates for offline use",
                    key=f"{widget_key}_save_rates",
                    help=f"Saves current live rates to {_FALLBACK_FILE_PATH}",
                ):
                    ok = save_rates_to_file()
                    if ok:
                        st.success(f"Rates saved to `{_FALLBACK_FILE_PATH}`")
                    else:
                        st.error("Could not save rates file.")

        st.caption(
            "Exchange rates are for informational purposes only. "
            "Actual salary amounts depend on employer agreements and local tax laws."
        )


# ---------------------------------------------------------------------------
# Convenience wrappers for Tab 3 / Tab 4 (no UI, just math)
# ---------------------------------------------------------------------------

def convert_salary_series(
    usd_series,
    target_currency: str,
) -> tuple:
    """
    Convert a pandas Series or list of USD salaries.

    Returns:
        (converted_series, rate_used, source_label)
    """
    rate_data = get_exchange_rates()
    rates = rate_data["rates"]
    rate = rates.get(target_currency.upper(), 1.0)
    converted = [v * rate for v in usd_series]
    return converted, rate, rate_data["source"]


def get_rate_info() -> dict:
    """
    Returns the full rate cache dict (rates, source, fetched_at, error).
    Useful for Tab 3/4 to show rate source in analytics notes.
    """
    return get_exchange_rates()


def get_converted_amount(
    usd_amount: float,
    target_currency: str,
) -> tuple[float, float]:
    """
    Lightweight helper: convert usd_amount to target_currency.

    Returns:
        (converted_amount, fx_rate_used)

    This is the primary reusable bridge for tax_utils and col_utils
    when they need to display values in a non-USD currency.
    Always safe to call — falls back gracefully if rates unavailable.
    """
    rate_data = get_exchange_rates()
    rates = rate_data["rates"]
    code = target_currency.upper()
    rate = rates.get(code, 1.0)
    return usd_amount * rate, rate


def get_active_currency(widget_key: str) -> Optional[str]:
    """
    Returns the currently selected target currency code for a given widget_key,
    as set by render_currency_converter().

    Returns None if the currency toggle is off or widget not rendered yet.
    Useful for tax_utils / col_utils to know which currency is active
    without needing to re-render the selector.

    Example:
        currency = get_active_currency("manual_a1")
        if currency:
            render_tax_adjuster(..., converted_currency=currency)
    """
    toggle_key = f"{widget_key}_currency_toggle"
    dropdown_key = f"{widget_key}_currency_dropdown"

    toggle_on = st.session_state.get(toggle_key, False)
    if not toggle_on:
        return None

    raw = st.session_state.get(dropdown_key)
    if not raw:
        return None

    code = parse_currency_option(str(raw))
    return code if code != "USD" else None


def get_active_rates() -> Optional[dict[str, float]]:
    """
    Returns the current rates dict if rates are loaded (live, file, or hardcoded).
    Returns None only if the cache is completely empty (edge case on first call).

    Useful for passing to tax_utils.render_tax_adjuster(rates=...) to avoid
    a redundant second fetch.
    """
    rate_data = get_exchange_rates()
    return rate_data.get("rates")


def get_post_adjustment_salary(
    gross_usd: float,
    location_hint: Optional[str] = None,
    target_currency: Optional[str] = None,
    apply_tax: bool = False,
    apply_col: bool = False,
    compare_country: Optional[str] = "US",
) -> dict:
    """
    All-in-one reusable calculation bridge for Tab 3 / Tab 4 analytics.

    Optionally applies currency conversion, tax estimation, and/or
    cost-of-living adjustment to a gross USD salary — in a single call,
    with no Streamlit UI dependencies (pure math, no imports of st).

    Parameters
    ----------
    gross_usd       : Annual gross salary in USD.
    location_hint   : Country name or ISO-2 (used for tax + CoL + currency guess).
    target_currency : ISO-3 currency code. If None, guesses from location_hint.
    apply_tax       : If True, computes post-tax net using tax_utils.
    apply_col       : If True, computes PPP-adjusted value using col_utils.
    compare_country : Reference country for CoL comparison (default "US").

    Returns
    -------
    dict with keys (only present if the corresponding flag is True):
      gross_usd            : original gross
      fx_rate              : exchange rate used (1.0 if no conversion)
      target_currency      : currency code used
      gross_converted      : gross in target_currency
      tax_rate             : effective tax rate (if apply_tax)
      net_usd              : post-tax USD (if apply_tax)
      net_converted        : post-tax in target_currency (if apply_tax + conversion)
      work_col_index       : CoL index of work country (if apply_col)
      compare_col_index    : CoL index of compare_country (if apply_col)
      ppp_equivalent_usd   : PPP-adjusted in compare_country (if apply_col)
      ppp_net_usd          : PPP-adjusted post-tax (if apply_tax + apply_col)
    """
    result: dict = {"gross_usd": gross_usd}

    # --- Currency conversion ---
    if target_currency is None:
        target_currency = guess_currency(location_hint)
    result["target_currency"] = target_currency

    rates = get_active_rates() or {}
    fx = rates.get(target_currency.upper(), 1.0)
    result["fx_rate"] = fx
    result["gross_converted"] = gross_usd * fx

    # --- Tax ---
    net_usd = gross_usd
    if apply_tax:
        try:
            from tax_utils import compute_post_tax
            tax_result = compute_post_tax(gross_usd, location_hint)
            result["tax_rate"] = tax_result["tax_rate"]
            result["tax_amount_usd"] = tax_result["tax_amount_usd"]
            result["net_usd"] = tax_result["net_usd"]
            result["net_monthly_usd"] = tax_result["net_monthly_usd"]
            result["net_converted"] = tax_result["net_usd"] * fx
            net_usd = tax_result["net_usd"]
        except ImportError:
            result["tax_rate"] = None
            result["net_usd"] = gross_usd
            result["net_converted"] = gross_usd * fx

    # --- CoL ---
    if apply_col:
        try:
            from col_utils import compute_col_adjusted
            col_result = compute_col_adjusted(
                gross_usd=gross_usd,
                work_country=location_hint,
                compare_country=compare_country,
            )
            result["work_col_index"] = col_result["work_col_index"]
            result["compare_col_index"] = col_result["compare_col_index"]
            result["ppp_equivalent_usd"] = col_result["ppp_equivalent_usd"]
            result["adjustment_factor"] = col_result["adjustment_factor"]
            if apply_tax:
                result["ppp_net_usd"] = net_usd * col_result["adjustment_factor"]
        except ImportError:
            result["work_col_index"] = None
            result["ppp_equivalent_usd"] = None

    return result