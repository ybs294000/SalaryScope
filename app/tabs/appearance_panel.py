"""
app/tabs/appearance_panel.py
============================
SalaryScope -- Sidebar Appearance Panel

What works
----------
  - Light/Dark mode toggle: instantly switches between the dark theme family
    and Light Clean, independently of the full theme picker below it.
  - Theme dropdown: switches the full active theme (accent, colorway, surfaces)
    on Apply. Filtered to only show themes matching the current mode so the
    mode toggle and theme picker never contradict each other.
  - Reset: reverts to Dark Professional.
  - All cards, charts, and banners respond to theme switches because they call
    get_token() / get_colorway() on every render.
  - The :root CSS variable block in app_resume.py is rebuilt on every render
    from the active theme dict, so Streamlit UI elements (sidebar, inputs,
    buttons, tabs, metrics) update immediately on theme switch.

What is commented out (fine-tune pickers)
------------------------------------------
Fine-tune individual colour pickers are not functional in the current
Streamlit version and are therefore disabled. See original docstring for
the full explanation and the correct fix path (requires Streamlit >= 1.37).

Extending the theme list
------------------------
  1. Write a new theme dict in app/theme.py following DARK_PROFESSIONAL.
  2. Register it in BUILTIN_THEMES and THEME_ORDER.
  Done. The dropdown picks it up automatically, grouped by mode.

Light/Dark mode toggle -- how it works
---------------------------------------
  A session-state key _ST_MODE_KEY stores "dark" or "light".
  Pressing the toggle button writes the preferred mode, then picks either:
    - The previously used dark theme (stored in _LAST_DARK_KEY), or
    - Light Clean if switching to light.
  This means the user keeps their chosen dark theme (e.g. Dark Violet) when
  they toggle back from light mode. The full theme picker is filtered to show
  only themes matching the current mode, so it never shows dark themes when
  in light mode or vice versa.

Usage
-----
    from app.tabs.appearance_panel import render_appearance_panel

    with st.sidebar:
        render_appearance_panel()
"""

import streamlit as st

from app.theme import (
    BUILTIN_THEMES,
    THEME_ORDER,
    THEME_KEY,
    DEFAULT_THEME_ID,
    DARK_PROFESSIONAL,
    reset_theme,
)

# ---------------------------------------------------------------------------
# Session-state keys
# ---------------------------------------------------------------------------
_OVERRIDE_KEY  = "_ap_overrides"
_ST_MODE_KEY   = "_ap_st_mode"       # "dark" or "light"
_LAST_DARK_KEY = "_ap_last_dark_id"  # remembers the last-used dark theme id

# The only built-in light theme id -- used when switching to light mode
_LIGHT_THEME_ID = "light_clean"

# The default dark theme to fall back to when _LAST_DARK_KEY is absent
_DEFAULT_DARK_ID = DEFAULT_THEME_ID


# ---------------------------------------------------------------------------
# Fine-tune token tables (kept for when fine-tune is re-enabled)
# ---------------------------------------------------------------------------

_HTML_SURFACE_TOKENS = [
    ("card_grad_start",   "Card top",          "Top colour of prediction card gradient."),
    ("card_grad_end",     "Card bottom",        "Bottom colour of prediction card gradient."),
    ("accent_primary",    "Accent (border)",    "Prediction card border and accent colour."),
    ("accent_bright",     "Accent (value)",     "Large value colour inside prediction cards."),
    ("card_band_border",  "Level border",       "Border of the salary level card."),
    ("card_stage_border", "Stage border",       "Border of the career stage card."),
    ("hub_card_bg",       "Hub bg",             "Background of the Model Hub result card."),
    ("hub_card_accent",   "Hub accent",         "Left border and value colour of the Model Hub card."),
    ("util_card_start",   "Util top",           "Top of the utility card gradient."),
    ("util_card_end",     "Util bottom",        "Bottom of the utility card gradient."),
    ("util_card_border",  "Util border",        "Border of all utility result cards."),
    ("banner_info_bg",    "Info banner",        "Background of info banners."),
    ("banner_ok_bg",      "Success banner",     "Background of success banners."),
    ("banner_warn_bg",    "Warn banner",        "Background of warning banners."),
    ("banner_err_bg",     "Error banner",       "Background of error banners."),
    ("status_info_bg",    "Status info",        "Background of in-progress status boxes."),
    ("status_success_bg", "Status success",     "Background of success status boxes."),
    ("status_warn_bg",    "Status warn",        "Background of warning status boxes."),
    ("status_error_bg",   "Status error",       "Background of error status boxes."),
]

_CHART_TOKENS = [
    ("chart_paper",    "Chart outer bg",   "Plotly paper_bgcolor."),
    ("chart_plot",     "Chart plot area",  "Plotly plot_bgcolor."),
    ("status_success", "Success",          "Green for success states."),
    ("status_warning", "Warning",          "Amber for warnings and trendlines."),
    ("status_error",   "Error",            "Red for errors."),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_active_id() -> str:
    stored = st.session_state.get(THEME_KEY)
    if isinstance(stored, str):
        return stored
    if isinstance(stored, dict):
        return stored.get("id", DEFAULT_THEME_ID)
    return DEFAULT_THEME_ID


def _get_current_mode() -> str:
    """Return 'dark' or 'light' based on the active theme."""
    theme = BUILTIN_THEMES.get(_get_active_id(), DARK_PROFESSIONAL)
    return theme.get("mode", "dark")


def _apply(theme_id: str, overrides: dict = None) -> None:
    """
    Write base theme + overrides as a merged dict into THEME_KEY.
    get_token() reads this on every call so all helpers pick up the change.
    """
    overrides = overrides or {}
    base = dict(BUILTIN_THEMES.get(theme_id, DARK_PROFESSIONAL))
    base.update(overrides)
    st.session_state[THEME_KEY]     = base
    st.session_state[_OVERRIDE_KEY] = overrides


def _swatch_row(theme: dict) -> str:
    """Render a row of coloured square swatches for theme preview."""
    cw     = theme.get("colorway", [])[:6]
    accent = theme.get("accent_primary", "#3E7DE0")
    card   = theme.get("card_grad_start", "#1B2A45")

    def swatch(color: str, title: str = "", extra: str = "") -> str:
        return (
            "<span style='display:inline-block;width:16px;height:16px;"
            "border-radius:3px;background:" + color + ";margin-right:2px;" + extra + "'"
            " title='" + title + "'></span>"
        )

    html  = "".join(swatch(c) for c in cw)
    html += swatch(accent, "accent",  "border:2px solid rgba(255,255,255,0.35);")
    html += swatch(card,   "card bg", "border:1px solid rgba(255,255,255,0.15);")
    return "<div style='margin:4px 0 8px 0;line-height:20px;'>" + html + "</div>"


def _dark_themes() -> list:
    """Return theme ids from THEME_ORDER that have mode == 'dark'."""
    return [
        tid for tid in THEME_ORDER
        if tid in BUILTIN_THEMES and BUILTIN_THEMES[tid].get("mode", "dark") == "dark"
    ]


def _light_themes() -> list:
    """Return theme ids from THEME_ORDER that have mode == 'light'."""
    return [
        tid for tid in THEME_ORDER
        if tid in BUILTIN_THEMES and BUILTIN_THEMES[tid].get("mode", "dark") == "light"
    ]


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_appearance_panel() -> None:
    """
    Render the Appearance expander in the sidebar.
    Call from inside a `with st.sidebar:` block in app_resume.py.
    """
    live_id       = _get_active_id()
    overrides     = st.session_state.get(_OVERRIDE_KEY, {}) or {}
    has_overrides = bool(overrides)
    is_default    = (live_id == DEFAULT_THEME_ID and not has_overrides)
    current_mode  = _get_current_mode()

    label = (
        ":material/palette: Appearance"
        if is_default
        else ":material/brush: Appearance"
    )

    with st.expander(label, expanded=False):

        # ----------------------------------------------------------------
        # Light / Dark mode toggle
        # This is a dedicated two-button row that switches the Streamlit UI
        # between dark and light mode independently of the theme picker.
        # It remembers the last dark theme so toggling back restores it.
        # ----------------------------------------------------------------
        st.caption("Light / Dark mode")

        col_dark, col_light = st.columns(2)

        with col_dark:
            dark_type = "primary" if current_mode == "dark" else "secondary"
            if st.button(
                ":material/dark_mode: Dark",
                key="_ap_mode_dark",
                use_container_width=True,
                type=dark_type,
            ):
                if current_mode != "dark":
                    # Remember where we were in dark mode before going light
                    last_dark = st.session_state.get(_LAST_DARK_KEY, _DEFAULT_DARK_ID)
                    if last_dark not in BUILTIN_THEMES:
                        last_dark = _DEFAULT_DARK_ID
                    st.session_state.pop(_OVERRIDE_KEY, None)
                    _apply(last_dark)
                    st.rerun()

        with col_light:
            light_type = "primary" if current_mode == "light" else "secondary"
            if st.button(
                ":material/light_mode: Light",
                key="_ap_mode_light",
                use_container_width=True,
                type=light_type,
            ):
                if current_mode != "light":
                    # Persist the current dark theme id before leaving
                    if current_mode == "dark":
                        st.session_state[_LAST_DARK_KEY] = live_id
                    light_ids = _light_themes()
                    target = light_ids[0] if light_ids else _LIGHT_THEME_ID
                    st.session_state.pop(_OVERRIDE_KEY, None)
                    _apply(target)
                    st.rerun()

        st.divider()

        # ----------------------------------------------------------------
        # Theme dropdown -- filtered to current mode so it never shows
        # dark themes when in light mode or vice versa
        # ----------------------------------------------------------------
        st.caption("Theme variant")

        if current_mode == "dark":
            visible_ids = _dark_themes()
        else:
            visible_ids = _light_themes()

        # Fallback: if the active id is not in visible list, add it
        if live_id not in visible_ids and live_id in BUILTIN_THEMES:
            visible_ids = [live_id] + visible_ids

        def _fmt(tid: str) -> str:
            mode = BUILTIN_THEMES[tid].get("mode", "dark")
            tag  = "[Dark]" if mode == "dark" else "[Light]"
            return tag + "  " + BUILTIN_THEMES[tid]["name"]

        idx = visible_ids.index(live_id) if live_id in visible_ids else 0

        selected_id = st.selectbox(
            "Theme",
            options=visible_ids,
            format_func=_fmt,
            index=idx,
            key="_ap_dropdown",
            label_visibility="collapsed",
        )

        # Colour swatch preview for the selected (not yet applied) theme
        preview = BUILTIN_THEMES.get(selected_id, DARK_PROFESSIONAL)
        st.markdown(_swatch_row(preview), unsafe_allow_html=True)

        ca, cr = st.columns(2)
        with ca:
            if st.button(
                "Apply",
                key="_ap_apply",
                use_container_width=True,
                type="primary",
            ):
                # If applying a dark theme, remember it for the mode toggle
                if BUILTIN_THEMES.get(selected_id, {}).get("mode", "dark") == "dark":
                    st.session_state[_LAST_DARK_KEY] = selected_id
                st.session_state.pop(_OVERRIDE_KEY, None)
                _apply(selected_id)
                st.rerun()

        with cr:
            if st.button(
                "Reset",
                key="_ap_reset",
                use_container_width=True,
            ):
                st.session_state.pop(_OVERRIDE_KEY, None)
                st.session_state.pop(_LAST_DARK_KEY, None)
                reset_theme()
                st.rerun()

        st.divider()

        # ----------------------------------------------------------------
        # Fine-tune -- DISABLED (see module docstring for explanation)
        # ----------------------------------------------------------------
        st.caption(
            ":material/info: Per-colour fine-tune is not yet available. "
            "Use the theme switcher above."
        )

        # ----------------------------------------------------------------
        # Status line
        # ----------------------------------------------------------------
        theme_names = {
            tid: BUILTIN_THEMES[tid]["name"]
            for tid in THEME_ORDER
            if tid in BUILTIN_THEMES
        }
        name = theme_names.get(live_id, live_id)
        mode_icon = ":material/dark_mode:" if current_mode == "dark" else ":material/light_mode:"
        if has_overrides:
            st.caption(mode_icon + " " + name + " + overrides active")
        else:
            st.caption(mode_icon + " " + name)