"""
country_utils.py -- SalaryScope Country Utilities
==================================================
Centralizes all country-name and ISO-2-code resolution used across
col_utils.py, currency_utils.py, and tax_utils.py.

Responsibilities
----------------
- get_country_name(iso2)     : ISO-2 code -> human-readable English name
                               Uses babel for authoritative CLDR territory data.
- resolve_iso2(location)     : Any country name, alias, or ISO-2 -> canonical
                               ISO-2 code (upper-cased).  Returns None if the
                               input cannot be resolved.

Design notes
------------
- babel (PyPI: Babel) is the only non-stdlib dependency added here.
  It ships the Unicode CLDR territory name table, which is the same data
  used by browsers and operating systems for locale-aware country names.
- A small _DISPLAY_OVERRIDES dict is applied on top of CLDR so that
  historically verbose or changed names render in the shorter form that
  matches the rest of the application (e.g. "Hong Kong" instead of the
  CLDR string "Hong Kong SAR China").
- _ALIAS_TABLE consolidates the name->ISO mappings that were previously
  duplicated across _COL_ALIASES, _COUNTRY_TAX_ALIASES, and
  COUNTRY_TO_CURRENCY.  Callers in the three util files replace their
  local alias dicts with calls to resolve_iso2().
"""

from __future__ import annotations

from typing import Optional

from babel import Locale

# ---------------------------------------------------------------------------
# Babel locale used for all territory lookups
# ---------------------------------------------------------------------------
_LOCALE = Locale("en")

# ---------------------------------------------------------------------------
# Display overrides applied on top of CLDR territory names.
# Only entries that differ from CLDR are listed here.
# ---------------------------------------------------------------------------
_DISPLAY_OVERRIDES: dict[str, str] = {
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "BA": "Bosnia and Herzegovina",
    "MK": "North Macedonia",
    "CZ": "Czechia",
    "KR": "South Korea",
    "CF": "Central African Republic",
    "JE": "Jersey",
    "AS": "American Samoa",
    "PR": "Puerto Rico",
}

# ---------------------------------------------------------------------------
# Comprehensive alias table: alternative names / abbreviations -> ISO-2.
# This replaces _COL_ALIASES, _COUNTRY_TAX_ALIASES, and the name-keyed
# entries in COUNTRY_TO_CURRENCY across the three util files.
# ---------------------------------------------------------------------------
_ALIAS_TABLE: dict[str, str] = {
    # North America
    "USA":                    "US",
    "United States":          "US",
    "Canada":                 "CA",
    "Mexico":                 "MX",
    # Europe -- British Isles
    "UK":                     "GB",
    "United Kingdom":         "GB",
    "Jersey":                 "JE",
    # Europe -- Western
    "Germany":                "DE",
    "France":                 "FR",
    "Netherlands":            "NL",
    "Belgium":                "BE",
    "Luxembourg":             "LU",
    "Switzerland":            "CH",
    "Austria":                "AT",
    "Ireland":                "IE",
    # Europe -- Southern
    "Spain":                  "ES",
    "Italy":                  "IT",
    "Portugal":               "PT",
    "Greece":                 "GR",
    "Malta":                  "MT",
    "Cyprus":                 "CY",
    "Slovenia":               "SI",
    "Croatia":                "HR",
    # Europe -- Nordic
    "Sweden":                 "SE",
    "Norway":                 "NO",
    "Denmark":                "DK",
    "Finland":                "FI",
    "Iceland":                "IS",
    # Europe -- Central / Eastern
    "Poland":                 "PL",
    "Czech Republic":         "CZ",
    "Czechia":                "CZ",
    "Slovakia":               "SK",
    "Hungary":                "HU",
    "Romania":                "RO",
    "Bulgaria":               "BG",
    "Serbia":                 "RS",
    "Albania":                "AL",
    "North Macedonia":        "MK",
    "Bosnia and Herzegovina": "BA",
    "Bosnia":                 "BA",
    "Moldova":                "MD",
    "Latvia":                 "LV",
    "Lithuania":              "LT",
    "Estonia":                "EE",
    # CIS / Caucasus / Central Asia
    "Russia":                 "RU",
    "Ukraine":                "UA",
    "Belarus":                "BY",
    "Armenia":                "AM",
    "Georgia":                "GE",
    "Azerbaijan":             "AZ",
    "Kazakhstan":             "KZ",
    "Uzbekistan":             "UZ",
    "Kyrgyzstan":             "KG",
    "Tajikistan":             "TJ",
    "Turkmenistan":           "TM",
    # Middle East
    "United Arab Emirates":   "AE",
    "UAE":                    "AE",
    "Saudi Arabia":           "SA",
    "Kuwait":                 "KW",
    "Qatar":                  "QA",
    "Bahrain":                "BH",
    "Oman":                   "OM",
    "Israel":                 "IL",
    "Jordan":                 "JO",
    "Lebanon":                "LB",
    "Iraq":                   "IQ",
    "Iran":                   "IR",
    "Syria":                  "SY",
    "Yemen":                  "YE",
    "Libya":                  "LY",
    "Turkey":                 "TR",
    # South Asia
    "India":                  "IN",
    "Pakistan":               "PK",
    "Bangladesh":             "BD",
    "Sri Lanka":              "LK",
    "Nepal":                  "NP",
    "Afghanistan":            "AF",
    # East / Southeast Asia
    "Japan":                  "JP",
    "China":                  "CN",
    "South Korea":            "KR",
    "Hong Kong":              "HK",
    "Taiwan":                 "TW",
    "Singapore":              "SG",
    "Malaysia":               "MY",
    "Thailand":               "TH",
    "Philippines":            "PH",
    "Vietnam":                "VN",
    "Indonesia":              "ID",
    "Myanmar":                "MM",
    "Cambodia":               "KH",
    "Laos":                   "LA",
    "Mongolia":               "MN",
    # Oceania
    "Australia":              "AU",
    "New Zealand":            "NZ",
    "American Samoa":         "AS",
    # Africa
    "South Africa":           "ZA",
    "Nigeria":                "NG",
    "Kenya":                  "KE",
    "Ghana":                  "GH",
    "Egypt":                  "EG",
    "Morocco":                "MA",
    "Algeria":                "DZ",
    "Tunisia":                "TN",
    "Ethiopia":               "ET",
    "Tanzania":               "TZ",
    "Uganda":                 "UG",
    "Central African Republic": "CF",
    # Latin America
    "Brazil":                 "BR",
    "Argentina":              "AR",
    "Chile":                  "CL",
    "Colombia":               "CO",
    "Peru":                   "PE",
    "Bolivia":                "BO",
    "Paraguay":               "PY",
    "Uruguay":                "UY",
    "Venezuela":              "VE",
    "Ecuador":                "EC",
    "Costa Rica":             "CR",
    "Panama":                 "PA",
    "Guatemala":              "GT",
    "Honduras":               "HN",
    "El Salvador":            "SV",
    "Nicaragua":              "NI",
    "Cuba":                   "CU",
    "Dominican Republic":     "DO",
    "Puerto Rico":            "PR",
    "Bahamas":                "BS",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_country_name(iso2: Optional[str]) -> str:
    """
    Return the English display name for an ISO-3166-1 alpha-2 country code.

    Uses babel's CLDR territory data as the authoritative source, with a
    small set of application-specific overrides applied on top (see
    _DISPLAY_OVERRIDES above).

    Parameters
    ----------
    iso2 : ISO-2 country code (case-insensitive) or None.

    Returns
    -------
    str
        Human-readable country name, or the original input string if the
        code is not found (so callers always get a printable value).
    """
    if not iso2:
        return "Unknown"
    #originally - code = str(iso2).strip().upper()
    code = str(iso2).strip()

    # Application-level overrides take priority
    if code in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[code]

    # CLDR via babel
    name = _LOCALE.territories.get(code)
    if name:
        return name

    # Fallback: return the code itself so the UI is never blank
    return code


def resolve_iso2(location: Optional[str]) -> Optional[str]:
    """
    Resolve a country name, common alias, or ISO-2 code to a canonical
    upper-cased ISO-3166-1 alpha-2 code.

    Lookup order:
      1. Direct ISO-2 match (after upper-casing).
      2. Exact match in _ALIAS_TABLE.
      3. Case-insensitive match in _ALIAS_TABLE.
      4. Case-insensitive match against babel CLDR territory names so that
         the official English name (e.g. "Czechia") always resolves even
         if it is not listed in _ALIAS_TABLE.

    Parameters
    ----------
    location : Country name, alias, or ISO-2 code.

    Returns
    -------
    str or None
        Upper-cased ISO-2 code, or None if resolution fails.
    """
    if not location:
        return None

    raw = str(location).strip()
    upper = raw.upper()

    # 1. Two-letter code that exists in CLDR
    if len(upper) == 2 and _LOCALE.territories.get(upper):
        return upper

    # 2. Exact alias match
    if raw in _ALIAS_TABLE:
        return _ALIAS_TABLE[raw]

    # 3. Case-insensitive alias match
    lower = raw.lower()
    for alias, iso in _ALIAS_TABLE.items():
        if alias.lower() == lower:
            return iso

    # 4. Case-insensitive match against full CLDR territory names
    for code, name in _LOCALE.territories.items():
        if name.lower() == lower:
            return code.upper()

    return None