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
    os.path.dirname(os.path.abspath(__file__)), "exchange_rates_fallback.json"
)

# ---------------------------------------------------------------------------
# Currency metadata: code → (display name, symbol)
# ---------------------------------------------------------------------------
CURRENCY_INFO: dict[str, tuple[str, str]] = {
    "USD": ("US Dollar", "$"),
    "EUR": ("Euro", "€"),
    "GBP": ("British Pound", "£"),
    "INR": ("Indian Rupee", "₹"),
    "CAD": ("Canadian Dollar", "CA$"),
    "AUD": ("Australian Dollar", "A$"),
    "JPY": ("Japanese Yen", "¥"),
    "CNY": ("Chinese Yuan", "¥"),
    "CHF": ("Swiss Franc", "CHF"),
    "SGD": ("Singapore Dollar", "S$"),
    "AED": ("UAE Dirham", "AED"),
    "SAR": ("Saudi Riyal", "SAR"),
    "MXN": ("Mexican Peso", "MX$"),
    "BRL": ("Brazilian Real", "R$"),
    "ZAR": ("South African Rand", "R"),
    "KRW": ("South Korean Won", "₩"),
    "HKD": ("Hong Kong Dollar", "HK$"),
    "SEK": ("Swedish Krona", "SEK"),
    "NOK": ("Norwegian Krone", "NOK"),
    "DKK": ("Danish Krone", "DKK"),
    "PLN": ("Polish Złoty", "PLN"),
    "TRY": ("Turkish Lira", "₺"),
    "RUB": ("Russian Ruble", "₽"),
    "IDR": ("Indonesian Rupiah", "Rp"),
    "MYR": ("Malaysian Ringgit", "RM"),
    "THB": ("Thai Baht", "฿"),
    "PHP": ("Philippine Peso", "₱"),
    "PKR": ("Pakistani Rupee", "₨"),
    "NGN": ("Nigerian Naira", "₦"),
    "EGP": ("Egyptian Pound", "EGP"),
    "ILS": ("Israeli Shekel", "₪"),
    "NZD": ("New Zealand Dollar", "NZ$"),
    "CZK": ("Czech Koruna", "Kč"),
    "HUF": ("Hungarian Forint", "Ft"),
    "RON": ("Romanian Leu", "RON"),
    "HRK": ("Croatian Kuna", "kn"),
    "BGN": ("Bulgarian Lev", "BGN"),
    "UAH": ("Ukrainian Hryvnia", "₴"),
    "CLP": ("Chilean Peso", "CL$"),
    "COP": ("Colombian Peso", "COP"),
    "ARS": ("Argentine Peso", "ARS"),
    "VND": ("Vietnamese Dong", "₫"),
    "BDT": ("Bangladeshi Taka", "৳"),
    "LKR": ("Sri Lankan Rupee", "LKR"),
    "KWD": ("Kuwaiti Dinar", "KD"),
    "QAR": ("Qatari Riyal", "QR"),
    "OMR": ("Omani Rial", "OMR"),
    "BHD": ("Bahraini Dinar", "BD"),
    "MAD": ("Moroccan Dirham", "MAD"),
    "DZD": ("Algerian Dinar", "DZD"),
    "TND": ("Tunisian Dinar", "TND"),
    "GHS": ("Ghanaian Cedi", "GHS"),
    "KES": ("Kenyan Shilling", "KES"),
    "UGX": ("Ugandan Shilling", "UGX"),
    "TZS": ("Tanzanian Shilling", "TZS"),
    "CRC": ("Costa Rican Colón", "₡"),
    "DOP": ("Dominican Peso", "DOP"),
    "PEN": ("Peruvian Sol", "S/"),
    "BOB": ("Bolivian Boliviano", "Bs"),
    "PYG": ("Paraguayan Guaraní", "₲"),
    "UYU": ("Uruguayan Peso", "UYU"),
    "UZS": ("Uzbekistani Som", "UZS"),
    "AMD": ("Armenian Dram", "֏"),
    "GEL": ("Georgian Lari", "₾"),
    "AZN": ("Azerbaijani Manat", "₼"),
    "KZT": ("Kazakhstani Tenge", "₸"),
    "MKD": ("Macedonian Denar", "MKD"),
    "RSD": ("Serbian Dinar", "RSD"),
    "ALL": ("Albanian Lek", "ALL"),
    "BAM": ("Bosnia-Herzegovina Mark", "KM"),
    "MDL": ("Moldovan Leu", "MDL"),
    "MNT": ("Mongolian Tögrög", "₮"),
    "MMK": ("Myanmar Kyat", "K"),
    "KHR": ("Cambodian Riel", "KHR"),
    "LAK": ("Laotian Kip", "₭"),
    "TWD": ("Taiwan Dollar", "NT$"),
    "NPR": ("Nepalese Rupee", "NPR"),
    "AFN": ("Afghan Afghani", "؋"),
    "IQD": ("Iraqi Dinar", "IQD"),
    "IRR": ("Iranian Rial", "IRR"),
    "JOD": ("Jordanian Dinar", "JD"),
    "LBP": ("Lebanese Pound", "LBP"),
    "SYP": ("Syrian Pound", "SYP"),
    "YER": ("Yemeni Rial", "YER"),
    "LYD": ("Libyan Dinar", "LYD"),
}

# ---------------------------------------------------------------------------
# Country ISO-2 → default currency code
# (covers all countries in App 1 & App 2 and more)
# ---------------------------------------------------------------------------
COUNTRY_TO_CURRENCY: dict[str, str] = {
    # Americas
    "US": "USD", "USA": "USD", "United States": "USD",
    "CA": "CAD", "Canada": "CAD",
    "MX": "MXN", "Mexico": "MXN",
    "BR": "BRL", "Brazil": "BRL",
    "AR": "ARS", "Argentina": "ARS",
    "CL": "CLP", "Chile": "CLP",
    "CO": "COP", "Colombia": "COP",
    "PE": "PEN", "Peru": "PEN",
    "BO": "BOB", "Bolivia": "BOB",
    "CR": "CRC", "Costa Rica": "CRC",
    "DO": "DOP",
    "HN": "HNL",
    "PR": "USD",
    "BS": "BSD",
    "UY": "UYU",
    # Europe
    "GB": "GBP", "United Kingdom": "GBP",
    "DE": "EUR", "Germany": "EUR",
    "FR": "EUR", "France": "EUR",
    "ES": "EUR", "Spain": "EUR",
    "IT": "EUR", "Italy": "EUR",
    "PT": "EUR", "Portugal": "EUR",
    "NL": "EUR", "Netherlands": "EUR",
    "BE": "EUR", "Belgium": "EUR",
    "AT": "EUR", "Austria": "EUR",
    "IE": "EUR", "Ireland": "EUR",
    "GR": "EUR", "Greece": "EUR",
    "FI": "EUR", "Finland": "EUR",
    "LU": "EUR", "Luxembourg": "EUR",
    "SI": "EUR", "Slovenia": "EUR",
    "MT": "EUR", "Malta": "EUR",
    "CY": "EUR", "Cyprus": "EUR",
    "EE": "EUR", "Estonia": "EUR",
    "LV": "EUR", "Latvia": "EUR",
    "LT": "EUR", "Lithuania": "EUR",
    "SK": "EUR", "Slovakia": "EUR",
    "CH": "CHF", "Switzerland": "CHF",
    "SE": "SEK", "Sweden": "SEK",
    "NO": "NOK", "Norway": "NOK",
    "DK": "DKK", "Denmark": "DKK",
    "PL": "PLN", "Poland": "PLN",
    "CZ": "CZK", "Czech Republic": "CZK",
    "HU": "HUF", "Hungary": "HUF",
    "RO": "RON", "Romania": "RON",
    "HR": "EUR", "Croatia": "EUR",
    "BG": "BGN", "Bulgaria": "BGN",
    "UA": "UAH", "Ukraine": "UAH",
    "RU": "RUB", "Russia": "RUB",
    "TR": "TRY", "Turkey": "TRY",
    "RS": "RSD", "Serbia": "RSD",
    "MK": "MKD", "North Macedonia": "MKD",
    "AL": "ALL", "Albania": "ALL",
    "BA": "BAM",
    "MD": "MDL", "Moldova": "MDL",
    "AM": "AMD", "Armenia": "AMD",
    "JE": "GBP",
    # Middle East & Central Asia
    "AE": "AED", "United Arab Emirates": "AED",
    "SA": "SAR",
    "KW": "KWD", "Kuwait": "KWD",
    "QA": "QAR",
    "OM": "OMR",
    "BH": "BHD",
    "IL": "ILS", "Israel": "ILS",
    "IQ": "IQD", "Iraq": "IQD",
    "IR": "IRR", "Iran": "IRR",
    "UZ": "UZS", "Uzbekistan": "UZS",
    "KZ": "KZT",
    # Asia
    "IN": "INR", "India": "INR",
    "JP": "JPY", "Japan": "JPY",
    "CN": "CNY", "China": "CNY",
    "SG": "SGD", "Singapore": "SGD",
    "HK": "HKD", "Hong Kong": "HKD",
    "KR": "KRW",
    "TW": "TWD",
    "MY": "MYR", "Malaysia": "MYR",
    "TH": "THB", "Thailand": "THB",
    "PH": "PHP", "Philippines": "PHP",
    "ID": "IDR", "Indonesia": "IDR",
    "VN": "VND", "Vietnam": "VND",
    "PK": "PKR", "Pakistan": "PKR",
    "BD": "BDT",
    "LK": "LKR",
    "NP": "NPR",
    "KH": "KHR",
    "MM": "MMK",
    # Oceania
    "AU": "AUD", "Australia": "AUD",
    "NZ": "NZD", "New Zealand": "NZD",
    # Africa
    "ZA": "ZAR",
    "NG": "NGN", "Nigeria": "NGN",
    "EG": "EGP", "Egypt": "EGP",
    "GH": "GHS", "Ghana": "GHS",
    "KE": "KES", "Kenya": "KES",
    "MA": "MAD", "Morocco": "MAD",
    "DZ": "DZD", "Algeria": "DZD",
    "TN": "TND", "Tunisia": "TND",
    "CF": "XAF",
    "AS": "USD",
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
    Falls back to USD if unknown.
    """
    if not location_hint:
        return "USD"
    key = str(location_hint).strip()
    # Direct lookup
    if key in COUNTRY_TO_CURRENCY:
        return COUNTRY_TO_CURRENCY[key]
    # Case-insensitive match
    key_lower = key.lower()
    for k, v in COUNTRY_TO_CURRENCY.items():
        if k.lower() == key_lower:
            return v
    return "USD"


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
        "🌍 Show Currency Conversion",
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

    with st.expander("💱 Currency Conversion", expanded=True):
        # Source status
        if rate_data["source"] == "live":
            fetched_str = rate_data["fetched_at"].strftime("%Y-%m-%d %H:%M UTC") if rate_data["fetched_at"] else "—"
            st.caption(f"✅ Live exchange rates — last updated {fetched_str}")
        elif rate_data["source"] == "fallback_file":
            st.warning(f"⚠️ {rate_data['error']}")
        else:
            st.error(
                "🔴 **No internet connection and no fallback file found.** "
                "Showing approximate built-in rates that may be outdated. "
                f"Details: {rate_data['error']}"
            )
            # Offer to load from file
            st.markdown(
                "**Tip:** Place a `exchange_rates_fallback.json` file in the same "
                "folder as `currency_utils.py` to use your own saved rates when offline."
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
            if st.button(
                "💾 Save rates for offline use",
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