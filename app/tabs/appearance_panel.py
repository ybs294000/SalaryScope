"""
app/tabs/appearance_panel.py
============================
SalaryScope -- Sidebar Appearance Panel

What works
----------
  - Theme dropdown: switches the full active theme instantly on Apply.
  - Reset: reverts to Dark Professional.
  - All cards, charts, and banners respond to theme switches because they
    call get_token() / get_colorway() on every render.

What is commented out (fine-tune pickers)
------------------------------------------
Fine-tune individual colour pickers are not functional in the current
Streamlit version and are therefore disabled.

Why they cannot work as written:
  Streamlit renders the entire script top-to-bottom in one pass. HTML card
  strings (salary_card_html, util_card_html, etc.) are built and sent to the
  browser during that pass. st.color_picker triggers a rerun when the user
  changes a value, but by the time the rerun starts from the top, the picker
  has already written the new value to session state. The appearance panel
  reads that value and calls _apply() which writes the merged theme to
  THEME_KEY. So far correct. BUT: calling st.rerun() inside the appearance
  panel after _apply() causes an infinite loop because the picker itself
  triggered the rerun. NOT calling st.rerun() means the current pass
  continues rendering with the OLD theme values already cached in local
  variables at the tops of other tabs. The updated THEME_KEY is only visible
  on the NEXT rerun, which happens naturally if the user interacts with any
  other widget. In practice the colour appears to change one interaction late,
  and for HTML cards rendered in @st.fragment blocks it never updates at all.

Correct fix (future):
  Wrap the appearance panel in @st.fragment and call st.rerun(scope="app")
  inside it after _apply(). st.fragment reruns only the fragment on widget
  interaction, and st.rerun(scope="app") triggers a full app rerun from the
  correct point without infinite-looping. This requires Streamlit >= 1.37.
  Once that is confirmed in the deployment environment, uncomment the
  fine-tune section below and add the @st.fragment decorator.

Extending the theme list
------------------------
  1. Write a new theme dict in app/theme.py following DARK_PROFESSIONAL.
  2. Register it in BUILTIN_THEMES and THEME_ORDER.
  Done -- the dropdown picks it up automatically.

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
# Session-state key for raw overrides (kept for when fine-tune is re-enabled)
# ---------------------------------------------------------------------------
_OVERRIDE_KEY = "_ap_overrides"

# ---------------------------------------------------------------------------
# Fine-tune token tables (kept for when fine-tune is re-enabled)
#
# _HTML_SURFACE_TOKENS: controls card gradients, banner backgrounds, and
#   status box backgrounds -- all consumed by HTML helpers in app/theme.py.
#   Prediction card tokens (card_grad_start, accent_primary, etc.) are
#   included here so they update salary/level/stage/score/insight cards.
#
# _CHART_TOKENS: controls Plotly chart colours consumed by apply_theme().
# ---------------------------------------------------------------------------

_HTML_SURFACE_TOKENS = [
    # Prediction output cards
    ("card_grad_start",   "Card top",          "Top colour of prediction card gradient."),
    ("card_grad_end",     "Card bottom",        "Bottom colour of prediction card gradient."),
    ("accent_primary",    "Accent (border)",    "Prediction card border and accent colour."),
    ("accent_bright",     "Accent (value)",     "Large value colour inside prediction cards."),
    ("card_band_border",  "Level border",       "Border of the salary level card."),
    ("card_stage_border", "Stage border",       "Border of the career stage card."),
    # Model Hub card
    ("hub_card_bg",       "Hub bg",             "Background of the Model Hub result card."),
    ("hub_card_accent",   "Hub accent",         "Left border and value colour of the Model Hub card."),
    # Utility cards
    ("util_card_start",   "Util top",           "Top of the utility card gradient."),
    ("util_card_end",     "Util bottom",        "Bottom of the utility card gradient."),
    ("util_card_border",  "Util border",        "Border of all utility result cards."),
    # Banners
    ("banner_info_bg",    "Info banner",        "Background of info banners."),
    ("banner_ok_bg",      "Success banner",     "Background of success banners."),
    ("banner_warn_bg",    "Warn banner",        "Background of warning banners."),
    ("banner_err_bg",     "Error banner",       "Background of error banners."),
    # Status boxes
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
# Helpers
# ---------------------------------------------------------------------------

def _get_active_id() -> str:
    stored = st.session_state.get(THEME_KEY)
    if isinstance(stored, str):
        return stored
    if isinstance(stored, dict):
        return stored.get("id", DEFAULT_THEME_ID)
    return DEFAULT_THEME_ID


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
            f"<span style='display:inline-block;width:16px;height:16px;"
            f"border-radius:3px;background:{color};margin-right:2px;{extra}'"
            f" title='{title}'></span>"
        )

    html  = "".join(swatch(c) for c in cw)
    html += swatch(accent, "accent",  "border:2px solid rgba(255,255,255,0.35);")
    html += swatch(card,   "card bg", "border:1px solid rgba(255,255,255,0.15);")
    return f"<div style='margin:4px 0 8px 0;line-height:20px;'>{html}</div>"


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

    label = (
        ":material/palette: Appearance"
        if is_default
        else ":material/brush: Appearance"
    )

    with st.expander(label, expanded=False):

        st.caption("Switch between built-in themes.")

        # ----------------------------------------------------------------
        # Theme dropdown
        # ----------------------------------------------------------------
        theme_names = {
            tid: BUILTIN_THEMES[tid]["name"]
            for tid in THEME_ORDER
            if tid in BUILTIN_THEMES
        }

        def _fmt(tid: str) -> str:
            mode = BUILTIN_THEMES[tid].get("mode", "dark")
            tag  = "[Dark]" if mode == "dark" else "[Light]"
            return f"{tag}  {BUILTIN_THEMES[tid]['name']}"

        options = list(theme_names.keys())
        idx     = options.index(live_id) if live_id in options else 0

        selected_id = st.selectbox(
            "Theme",
            options=options,
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
                reset_theme()
                st.rerun()

        st.divider()

        # ----------------------------------------------------------------
        # Fine-tune -- DISABLED (see module docstring for explanation)
        # To re-enable: uncomment the block below and add @st.fragment
        # decorator to this function (requires Streamlit >= 1.37).
        # ----------------------------------------------------------------

        # st.markdown("**Fine-tune**")
        # st.caption(
        #     "Fine-tune individual colours. "
        #     "Requires Streamlit >= 1.37 with @st.fragment support. "
        #     "Not yet enabled."
        # )

        # --- Fine-tune is currently non-functional. See module docstring. ---
        st.caption(
            ":material/info: Per-colour fine-tune is not yet available. "
            "Use the theme switcher above."
        )

        # ----------------------------------------------------------------
        # Status line
        # ----------------------------------------------------------------
        name = theme_names.get(live_id, live_id)
        if has_overrides:
            st.caption(f":material/brush: {name} + overrides active")
        else:
            st.caption(f":material/palette: {name}")