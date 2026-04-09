"""
col_utils.py — SalaryScope Cost-of-Living (CoL) Adjustment Utility
===================================================================
Provides purchasing-power-adjusted salary comparisons across countries.

IMPORTANT NOTE ON DATA
-----------------------
Cost-of-living indices change frequently and no reliable free real-time API
exists for this data. This file uses:
  1. Built-in index values (researched from Numbeo, World Bank, EIU — 2023/2024)
  2. Full user override via slider or custom JSON file
  3. Relative adjustment against a base country (default: US = 100)

The CoL index represents roughly how expensive a location is relative to
the US (index 100). Lower index = lower cost of living = higher real purchasing power.

Design
------
- Completely standalone: works with or without currency_utils.py or tax_utils.py
- `compute_col_adjusted(gross_usd, from_country, to_country)` — core reusable function
- `render_col_adjuster(...)` — Streamlit UI widget (toggle → expander)
- Mirrors currency_utils.py / tax_utils.py patterns

Integration (Tab 1 / Tab 2 in app.py)
--------------------------------------
    from col_utils import render_col_adjuster

    # Call AFTER render_tax_adjuster (or standalone):
    render_col_adjuster(
        gross_usd=prediction,           # annual USD salary
        work_country=country,           # where salary is earned
        widget_key="manual_a1_col",     # unique key per call-site
    )

Tab 3 / Tab 4 (pure math):
    from col_utils import compute_col_adjusted, get_col_index
"""

import json
import os
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_COL_FALLBACK_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "col_indices_custom.json"
)

# ---------------------------------------------------------------------------
# Built-in CoL indices (US = 100 baseline)
# Source: Numbeo Cost of Living Index, World Bank, EIU City Cost Surveys 2023/24.
# These are COUNTRY-level approximations (not city-level).
# Higher = more expensive. Lower = cheaper (better purchasing power for same USD).
# ---------------------------------------------------------------------------

_COL_INDEX: dict[str, float] = {
    # ── North America ──
    "US":  100.0,
    "CA":   83.0,
    "MX":   40.0,

    # ── Europe ──
    "CH":  137.0,  # Switzerland — most expensive in Europe
    "NO":  121.0,
    "DK":  117.0,
    "IS":  115.0,
    "IE":  100.0,
    "LU":   98.0,
    "SE":   95.0,
    "GB":   91.0,
    "NL":   89.0,
    "FI":   88.0,
    "AT":   86.0,
    "BE":   85.0,
    "DE":   83.0,
    "FR":   82.0,
    "IT":   72.0,
    "ES":   65.0,
    "PT":   58.0,
    "GR":   55.0,
    "SI":   58.0,
    "CZ":   52.0,
    "SK":   50.0,
    "PL":   48.0,
    "HU":   47.0,
    "RO":   44.0,
    "HR":   55.0,
    "BG":   38.0,
    "RS":   40.0,
    "AL":   35.0,
    "MK":   36.0,
    "BA":   38.0,
    "MD":   30.0,
    "LV":   52.0,
    "LT":   52.0,
    "EE":   58.0,
    "MT":   62.0,
    "CY":   65.0,
    "LY":   30.0,
    "JE":   92.0,

    # ── CIS / Eastern Europe ──
    "UA":   32.0,
    "RU":   42.0,
    "BY":   35.0,
    "AM":   38.0,
    "GE":   40.0,
    "AZ":   42.0,
    "KZ":   38.0,
    "UZ":   28.0,
    "KG":   25.0,
    "TJ":   22.0,
    "TM":   28.0,

    # ── Middle East ──
    "AE":   73.0,
    "QA":   68.0,
    "KW":   65.0,
    "BH":   60.0,
    "SA":   55.0,
    "OM":   52.0,
    "IL":   90.0,
    "JO":   42.0,
    "LB":   35.0,
    "IQ":   30.0,
    "IR":   28.0,
    "SY":   22.0,
    "YE":   20.0,

    # ── South Asia ──
    "IN":   23.0,
    "PK":   22.0,
    "BD":   20.0,
    "LK":   28.0,
    "NP":   22.0,
    "AF":   15.0,

    # ── East / Southeast Asia ──
    "JP":   88.0,
    "SG":   95.0,
    "HK":   93.0,
    "KR":   80.0,
    "TW":   72.0,
    "CN":   52.0,
    "MN":   30.0,
    "MY":   38.0,
    "TH":   40.0,
    "VN":   28.0,
    "PH":   32.0,
    "ID":   30.0,
    "MM":   22.0,
    "KH":   28.0,
    "LA":   25.0,

    # ── Oceania ──
    "AU":   93.0,
    "NZ":   90.0,

    # ── Africa ──
    "ZA":   35.0,
    "NG":   25.0,
    "KE":   30.0,
    "GH":   28.0,
    "EG":   22.0,
    "MA":   30.0,
    "DZ":   25.0,
    "TN":   28.0,
    "ET":   18.0,
    "TZ":   20.0,
    "UG":   22.0,
    "CF":   20.0,

    # ── Latin America ──
    "BR":   38.0,
    "AR":   32.0,
    "CL":   45.0,
    "CO":   32.0,
    "PE":   33.0,
    "BO":   28.0,
    "PY":   28.0,
    "UY":   42.0,
    "VE":   20.0,
    "EC":   30.0,
    "CR":   42.0,
    "DO":   35.0,
    "PA":   38.0,
    "GT":   30.0,
    "HN":   28.0,
    "SV":   32.0,
    "NI":   25.0,
    "CU":   25.0,
    "PR":   75.0,  # US territory
    "BS":   85.0,
    "AS":   95.0,

    # ── Japan / Pacific already above ──
}

# Name/alias → ISO key
_COL_ALIASES: dict[str, str] = {
    "USA": "US", "United States": "US",
    "UK": "GB", "United Kingdom": "GB",
    "Germany": "DE", "France": "FR", "India": "IN",
    "Canada": "CA", "Australia": "AU", "Singapore": "SG",
    "Netherlands": "NL", "Sweden": "SE", "Norway": "NO",
    "Denmark": "DK", "Switzerland": "CH", "Japan": "JP",
    "China": "CN", "South Korea": "KR", "Brazil": "BR",
    "Mexico": "MX", "Spain": "ES", "Italy": "IT",
    "Portugal": "PT", "Ireland": "IE", "Poland": "PL",
    "United Arab Emirates": "AE", "UAE": "AE",
    "Saudi Arabia": "SA", "Kuwait": "KW",
    "Qatar": "QA", "Bahrain": "BH",
    "Israel": "IL", "Turkey": "TR", "Russia": "RU",
    "Ukraine": "UA", "Pakistan": "PK", "Nigeria": "NG",
    "South Africa": "ZA", "Egypt": "EG", "Greece": "GR",
    "Czech Republic": "CZ", "Hungary": "HU", "Romania": "RO",
    "Belgium": "BE", "Austria": "AT", "New Zealand": "NZ",
    "Malaysia": "MY", "Indonesia": "ID", "Thailand": "TH",
    "Philippines": "PH", "Vietnam": "VN", "Argentina": "AR",
    "Colombia": "CO", "Chile": "CL", "Luxembourg": "LU",
    "Hong Kong": "HK", "Kenya": "KE", "Ghana": "GH",
    "Morocco": "MA", "Slovenia": "SI", "Finland": "FI",
    "Croatia": "HR", "Bulgaria": "BG", "Serbia": "RS",
    "Albania": "AL", "North Macedonia": "MK",
    "Moldova": "MD", "Armenia": "AM", "Georgia": "GE",
    "Azerbaijan": "AZ", "Kazakhstan": "KZ", "Uzbekistan": "UZ",
    "Latvia": "LV", "Lithuania": "LT", "Estonia": "EE",
    "Slovakia": "SK", "Cyprus": "CY", "Malta": "MT",
    "Peru": "PE", "Bolivia": "BO", "Uruguay": "UY",
    "Costa Rica": "CR", "Ecuador": "EC", "Panama": "PA",
    "Vietnam": "VN", "Mongolia": "MN", "Myanmar": "MM",
    "Cambodia": "KH", "Laos": "LA", "Nepal": "NP",
    "Sri Lanka": "LK", "Bangladesh": "BD", "Afghanistan": "AF",
    "Iraq": "IQ", "Iran": "IR", "Jordan": "JO",
    "Lebanon": "LB", "Oman": "OM",
    "Ethiopia": "ET", "Tanzania": "TZ", "Uganda": "UG",
    "Algeria": "DZ", "Tunisia": "TN",
    "Taiwan": "TW", "Hong Kong": "HK",
    "Puerto Rico": "PR", "American Samoa": "AS",
    "Bosnia and Herzegovina": "BA", "Bosnia": "BA",
}

_GENERIC_COL = 50.0  # fallback for unknown countries


# ---------------------------------------------------------------------------
# Core: resolve index
# ---------------------------------------------------------------------------

def _resolve_col_key(location_hint: Optional[str]) -> Optional[str]:
    if not location_hint:
        return None
    key = str(location_hint).strip()
    if key in _COL_INDEX:
        return key
    alias = _COL_ALIASES.get(key)
    if alias:
        return alias
    key_lower = key.lower()
    for k in _COL_INDEX:
        if k.lower() == key_lower:
            return k
    for k, v in _COL_ALIASES.items():
        if k.lower() == key_lower:
            return v
    return None


def get_col_index(
    location_hint: Optional[str],
    custom_index: Optional[float] = None,
    custom_overrides: Optional[dict] = None,
) -> tuple[float, str]:
    """
    Return (col_index, source_label) for a location.
    col_index: float, US=100 baseline. Lower = cheaper.
    source_label: "custom" | "built_in" | "file_override" | "generic"
    """
    if custom_index is not None:
        return float(custom_index), "custom"

    key = _resolve_col_key(location_hint)

    # Check file overrides first
    if custom_overrides and key and key in custom_overrides:
        return float(custom_overrides[key]), "file_override"
    if custom_overrides and location_hint and location_hint in custom_overrides:
        return float(custom_overrides[location_hint]), "file_override"

    if key and key in _COL_INDEX:
        return _COL_INDEX[key], "built_in"

    return _GENERIC_COL, "generic"


def compute_col_adjusted(
    gross_usd: float,
    work_country: Optional[str] = None,
    compare_country: Optional[str] = "US",
    custom_work_index: Optional[float] = None,
    custom_compare_index: Optional[float] = None,
    custom_overrides: Optional[dict] = None,
) -> dict:
    """
    Compute purchasing-power-adjusted salary equivalent.

    The "PPP-equivalent" answers: "What USD salary in `compare_country`
    would give the same purchasing power as `gross_usd` in `work_country`?"

    Returns dict:
      gross_usd           : original salary
      work_col_index      : CoL index of work country
      compare_col_index   : CoL index of comparison country
      ppp_equivalent_usd  : adjusted salary in compare_country terms
      adjustment_factor   : ratio (compare_col / work_col)
      work_country_key    : resolved key
      compare_country_key : resolved key
      work_source         : data source label
      compare_source      : data source label
    """
    work_idx, work_src = get_col_index(work_country, custom_work_index, custom_overrides)
    cmp_idx, cmp_src = get_col_index(compare_country, custom_compare_index, custom_overrides)

    if work_idx <= 0:
        work_idx = _GENERIC_COL

    adjustment_factor = cmp_idx / work_idx
    ppp_equiv = gross_usd * adjustment_factor

    return {
        "gross_usd": gross_usd,
        "work_col_index": work_idx,
        "compare_col_index": cmp_idx,
        "ppp_equivalent_usd": ppp_equiv,
        "adjustment_factor": adjustment_factor,
        "work_country_key": _resolve_col_key(work_country) or (work_country or ""),
        "compare_country_key": _resolve_col_key(compare_country) or (compare_country or ""),
        "work_source": work_src,
        "compare_source": cmp_src,
    }


# ---------------------------------------------------------------------------
# Custom index file (save / load)
# ---------------------------------------------------------------------------

def load_custom_col_file(filepath: Optional[str] = None) -> dict:
    """
    Load a custom CoL indices JSON file.
    Expected format: { "IN": 25.0, "US": 100.0, ... }
    """
    filepath = filepath or _COL_FALLBACK_FILE_PATH
    if not os.path.isfile(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}
    except Exception:
        return {}


def save_custom_col_file(overrides: dict, filepath: Optional[str] = None) -> bool:
    """Save custom CoL index overrides to a JSON file. Returns True on success."""
    filepath = filepath or _COL_FALLBACK_FILE_PATH
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# All available country options for dropdown (key → display label)
# ---------------------------------------------------------------------------

def col_country_options() -> list[str]:
    """
    Returns sorted list of country display strings for Streamlit dropdowns.
    Format: 'US — United States (index: 100.0)'
    """
    # Build reverse alias map for display names
    rev = {}
    for name, iso in _COL_ALIASES.items():
        if iso not in rev:
            rev[iso] = name

    result = []
    for iso, idx in sorted(_COL_INDEX.items(), key=lambda x: x[0]):
        label = rev.get(iso, iso)
        result.append(f"{iso} \u2014 {label} (CoL: {idx:.0f})")

    return result


def parse_col_option(option: str) -> str:
    """Extract ISO code from col_country_options() string."""
    return option.split(" \u2014 ")[0].strip()


# ---------------------------------------------------------------------------
# Streamlit UI widget
# ---------------------------------------------------------------------------

def render_col_adjuster(
    gross_usd: float,
    work_country: Optional[str] = None,
    widget_key: str = "col",
    net_usd: Optional[float] = None,
) -> None:
    """
    Streamlit widget: toggle → expander with purchasing-power-adjusted salary.

    Parameters
    ----------
    gross_usd    : Annual gross salary in USD (pre-tax).
    work_country : Country where salary is earned (ISO-2 or name).
    widget_key   : Unique prefix per call-site.
    net_usd      : Optional post-tax USD amount (from tax_utils). If provided,
                   also shows PPP-adjusted net salary.

    NOTE: Existing USD prediction cards are NOT modified.
    """

    toggle_key = f"{widget_key}_col_toggle"
    custom_work_key = f"{widget_key}_custom_work_toggle"
    custom_work_slider = f"{widget_key}_work_idx_slider"
    compare_select_key = f"{widget_key}_compare_country"
    custom_cmp_key = f"{widget_key}_custom_cmp_toggle"
    custom_cmp_slider = f"{widget_key}_cmp_idx_slider"

    show_col = st.toggle(
        ":material/home: Show Cost-of-Living Adjustment",
        key=toggle_key,
        value=False,
    )

    if not show_col:
        return

    # Load saved overrides
    saved_overrides = load_custom_col_file()

    with st.expander("Cost-of-Living (Purchasing Power) Adjustment", expanded=True):

        st.caption(
            ":material/info: **What is this?** This tool adjusts your salary for purchasing power. "
            "A salary of $100,000 USD goes much further in a low-CoL country than a high-CoL one. "
            "The index is US = 100 (baseline). Lower index = cheaper living = higher real value."
        )
        st.caption(
            ":material/warning:  CoL data is built-in (2023/24 estimates). "
            "Use custom overrides for city-level or more current data."
        )

        col_a, col_b = st.columns(2)

        # --- Work country ---
        with col_a:
            work_key = _resolve_col_key(work_country)
            work_built_in, work_src = get_col_index(work_country, custom_overrides=saved_overrides)

            if work_country and work_country not in ("Other", ""):
                st.info(
                    f"**Salary earned in:** {work_country}\n\n"
                    f"**CoL index:** {work_built_in:.0f} / 100\n\n"
                    f"_Source: {work_src}_"
                )
            else:
                st.info("No work country detected. Assuming US CoL (100).")

            use_custom_work = st.toggle(
                "Override work country CoL index",
                key=custom_work_key,
                value=False,
            )
            custom_work_idx: Optional[float] = None
            if use_custom_work:
                prefill_w = float(saved_overrides.get(work_key or "", work_built_in))
                custom_work_idx = st.slider(
                    "Work country CoL index (US=100)",
                    min_value=5.0, max_value=200.0,
                    value=float(min(max(prefill_w, 5.0), 200.0)),
                    step=1.0,
                    key=custom_work_slider,
                )
#                col_sw, col_rw = st.columns(2)
#                with col_sw:
#                    if st.button(
#                        "\U0001f4be Save",
#                        key=f"{widget_key}_save_work",
#                        disabled=not bool(work_key)
#                    ):
#                        upd = dict(saved_overrides)
#                        upd[work_key] = custom_work_idx
#                        if save_custom_col_file(upd):
#                            st.success(f"Saved {custom_work_idx:.0f} for {work_key}.")
#                        else:
#                            st.error("Could not save file.")
#                with col_rw:
#                    if st.button(
#                        "\U0001f5d1\ufe0f Reset",
#                        key=f"{widget_key}_reset_work",
#                        disabled=work_key not in saved_overrides
#                    ):
#                        upd = {k: v for k, v in saved_overrides.items() if k != work_key}
#                        save_custom_col_file(upd)
#                        st.rerun()

        # --- Comparison country ---
        with col_b:
            options = col_country_options()
            default_cmp_opt = next(
                (o for o in options if o.startswith("US \u2014")), options[0]
            )
            default_cmp_idx = options.index(default_cmp_opt)

            selected_cmp = st.selectbox(
                "Compare purchasing power to",
                options,
                index=default_cmp_idx,
                key=compare_select_key,
                help="Select a reference country to see what salary there gives equivalent purchasing power."
            )
            cmp_code = parse_col_option(selected_cmp)
            cmp_built_in, cmp_src = get_col_index(cmp_code, custom_overrides=saved_overrides)

            st.info(
                f"**Comparison country:** {cmp_code}\n\n"
                f"**CoL index:** {cmp_built_in:.0f} / 100\n\n"
                f"_Source: {cmp_src}_"
            )

            use_custom_cmp = st.toggle(
                "Override comparison country CoL index",
                key=custom_cmp_key,
                value=False,
            )
            custom_cmp_idx_val: Optional[float] = None
            if use_custom_cmp:
                prefill_c = float(saved_overrides.get(cmp_code, cmp_built_in))
                custom_cmp_idx_val = st.slider(
                    "Comparison country CoL index (US=100)",
                    min_value=5.0, max_value=200.0,
                    value=float(min(max(prefill_c, 5.0), 200.0)),
                    step=1.0,
                    key=custom_cmp_slider,
                )
#                if st.button(
#                    "\U0001f4be Save comparison index",
#                    key=f"{widget_key}_save_cmp",
#                ):
#                    upd = dict(saved_overrides)
#                    upd[cmp_code] = custom_cmp_idx_val
#                    if save_custom_col_file(upd):
#                        st.success(f"Saved {custom_cmp_idx_val:.0f} for {cmp_code}.")
#                    else:
#                        st.error("Could not save file.")

        # --- Compute ---
        result = compute_col_adjusted(
            gross_usd=gross_usd,
            work_country=work_country,
            compare_country=cmp_code,
            custom_work_index=custom_work_idx,
            custom_compare_index=custom_cmp_idx_val,
            custom_overrides=saved_overrides,
        )

        adj_factor = result["adjustment_factor"]
        ppp = result["ppp_equivalent_usd"]
        work_idx_used = result["work_col_index"]
        cmp_idx_used = result["compare_col_index"]

        st.divider()

        # --- Interpretation ---
        if abs(adj_factor - 1.0) < 0.01:
            interpretation = "Same cost of living — no adjustment needed."
            color = "#9CA6B5"
        elif adj_factor < 1.0:
            pct_diff = (1.0 - adj_factor) * 100
            interpretation = (
                f"{cmp_code} has ~{pct_diff:.0f}% lower cost of living than your work country "
                f"(CoL {work_idx_used:.0f}). "
                f"You would need only ~${ppp:,.0f} there to maintain the same lifestyle."
            )
            color = "#22C55E"
        else:
            pct_diff = (adj_factor - 1.0) * 100
            interpretation = (
                f"{cmp_code} has ~{pct_diff:.0f}% higher cost of living than your work country "
                f"(CoL {work_idx_used:.0f}). "
                f"You would need ~${ppp:,.0f} there to maintain the same lifestyle."
            )
            color = "#EF4444"

        st.markdown(
            f"""
            <div style='
                background: linear-gradient(135deg, #1A2535 0%, #1B2230 100%);
                border: 1px solid #2D3A50;
                border-left: 5px solid {color};
                border-radius: 10px;
                padding: 18px 24px;
                text-align: center;
                margin: 8px auto;
            '>
                <div style='color:#9CA6B5; font-size:12px; font-weight:600;
                            letter-spacing:0.5px; margin-bottom:6px;'>
                    PPP-EQUIVALENT SALARY IN {cmp_code} (USD)
                </div>
                <div style='color:{color}; font-size:34px; font-weight:700;
                            letter-spacing:-1px;'>
                    ${ppp:,.2f}
                </div>
                <div style='color:#6B7585; font-size:12px; margin-top:6px;'>
                    Adjustment factor: {adj_factor:.3f}x
                    (Work CoL: {work_idx_used:.0f} \u2192 {cmp_code} CoL: {cmp_idx_used:.0f})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(f":material/info: {interpretation}")

        # Summary metrics
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Your Gross (USD)", f"${gross_usd:,.0f}")
        col_m2.metric(f"PPP Equiv. in {cmp_code}", f"${ppp:,.0f}")
        col_m3.metric("Adjustment Factor", f"{adj_factor:.3f}x")

        # Also show post-tax PPP if net_usd provided
        if net_usd is not None and net_usd > 0:
            net_ppp = net_usd * adj_factor
            st.divider()
            st.markdown("#### Post-Tax PPP Equivalent")
            col_n1, col_n2, col_n3 = st.columns(3)
            col_n1.metric("Net Post-Tax (USD)", f"${net_usd:,.0f}")
            col_n2.metric(f"Net PPP Equiv. in {cmp_code}", f"${net_ppp:,.0f}")
            col_n3.metric("Adjustment Factor", f"{adj_factor:.3f}x")

        # --- CoL Scale reference ---
        st.divider()
        with st.expander("CoL Index Reference Guide"):
            st.markdown("""
| Index Range | Category | Examples |
|---|---|---|
| 130+ | Very High | Switzerland (137), Norway (121), Denmark (117) |
| 90–130 | High | Singapore (95), Australia (93), USA (100), UK (91) |
| 60–90 | Moderate–High | Japan (88), Germany (83), France (82) |
| 40–60 | Moderate | Spain (65), Brazil (38–45), China (52) |
| 20–40 | Low | India (23), Vietnam (28), Nigeria (25) |
| < 20 | Very Low | Afghanistan (15), Ethiopia (18) |

*US = 100 baseline. Higher index = more expensive. Values are country averages — city costs vary widely.*
            """)

        st.caption(
            "CoL indices are country-level approximations. City costs vary significantly. "
            "Data sourced from Numbeo, World Bank, and EIU (2023/24). "
            "Use custom overrides for city-specific or current data."
        )