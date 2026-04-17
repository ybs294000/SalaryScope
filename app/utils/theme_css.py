"""
app/utils/theme_css.py
======================
SalaryScope -- Dynamic CSS Theme Injector

Purpose
-------
This module replaces the static hardcoded :root { ... } block in app_resume.py
with a dynamic one whose values are read from the active theme dict on every
Streamlit render pass.

How it fits into the overall theming architecture
-------------------------------------------------
The app has TWO independent theming layers that must stay in sync:

  Layer A -- Python / Plotly / HTML layer
    Controlled by app/theme.py.
    get_token(), apply_theme(fig), salary_card_html(), etc. all read from
    st.session_state[THEME_KEY] via get_active_theme().
    This layer already switches correctly when the user picks a theme.

  Layer B -- Streamlit UI / CSS layer
    In the original code this was controlled by BOTH:
      (a) the hardcoded :root { ... } block in app_resume.py (our custom vars)
      (b) config.toml [theme.dark] / [theme.light] (Streamlit's native vars)
    Without config.toml the Streamlit native vars (--primary-color,
    --background-color, etc.) would not be set and widgets would render in
    Streamlit's built-in default colours -- making the UI look broken.

    This module bridges the gap: on every render it emits a <style> block
    containing BOTH:
      (a) --primary, --bg-main, etc. built from the active theme dict
          (so all custom component CSS keeps working unchanged)
      (b) Explicit overrides targeting Streamlit's internal selectors
          using our theme values (so Streamlit widgets match the active theme
          even without config.toml -- config.toml remains as a backup)

Why re-emit on every render
---------------------------
Streamlit re-runs the entire script from top to bottom on every interaction.
By calling inject_theme_css() near the top of app_resume.py (after
set_page_config), the freshly resolved theme values are injected into the
browser on every run. The browser replaces the previous <style> block with
the new one. This is the correct Streamlit pattern for dynamic CSS.

Note on unicode / emoji in code
--------------------------------
No emoji characters or non-ASCII unicode is used directly in this file.
All multi-character hyphens are written as "--" (two hyphens, not an em-dash).

Usage
-----
    from app.utils.theme_css import inject_theme_css

    # Near the top of app_resume.py, after st.set_page_config():
    inject_theme_css()

    # The static hardcoded st.markdown(<style>:root{...}</style>) block that
    # previously followed set_page_config can be removed -- the :root vars
    # are now emitted here. The structural CSS block (tabs, inputs, buttons,
    # metrics, etc.) that follows it STAYS as-is because it still reads
    # var(--primary), var(--bg-main), etc. -- those vars are now just
    # populated dynamically instead of statically.
"""

import streamlit as st

from app.theme import (
    get_token,
    get_active_theme,
    DARK_PROFESSIONAL,
)


def _hex_to_rgb_components(hex_color: str) -> str:
    """
    Convert a hex color string to "R, G, B" component string (no # prefix).
    Used to build rgba() values for box-shadow and other CSS that needs
    separate RGB components.
    Falls back to "62, 125, 224" (the default primary blue) on any error.
    """
    h = hex_color.lstrip("#")
    try:
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return str(r) + ", " + str(g) + ", " + str(b)
    except Exception:
        return "62, 125, 224"


def inject_theme_css() -> None:
    """
    Emit a <style> block that:

    1. Sets all custom CSS variables (--primary, --bg-main, etc.) from the
       active theme.  All structural component CSS in app_resume.py reads
       these variables -- no changes needed there.

    2. Overrides Streamlit's internal CSS variables and element selectors so
       that Streamlit's own widgets (selectbox, slider, checkbox, radio,
       progress bar, st.metric delta, etc.) also reflect the active theme.
       This makes config.toml optional -- it remains as a backup/fallback.

    Call this once per render, right after st.set_page_config() and before
    any other st.markdown / widget calls.
    """
    t = get_active_theme()

    # ------------------------------------------------------------------
    # Resolve all tokens we need into local variables so the f-string
    # below is readable and each token is fetched exactly once.
    # ------------------------------------------------------------------
    primary        = t.get("accent_primary",  DARK_PROFESSIONAL["accent_primary"])
    primary_hover  = t.get("accent_hover",    DARK_PROFESSIONAL["accent_hover"])
    accent_bright  = t.get("accent_bright",   DARK_PROFESSIONAL["accent_bright"])

    bg_main        = t.get("surface_base",    DARK_PROFESSIONAL["surface_base"])
    bg_card        = t.get("surface_raised",  DARK_PROFESSIONAL["surface_raised"])
    bg_input       = t.get("surface_overlay", DARK_PROFESSIONAL["surface_overlay"])
    bg_sunken      = t.get("surface_sunken",  DARK_PROFESSIONAL["surface_sunken"])

    border         = t.get("border_default",  DARK_PROFESSIONAL["border_default"])
    border_subtle  = t.get("border_subtle",   DARK_PROFESSIONAL["border_subtle"])

    text_main      = t.get("text_primary",    DARK_PROFESSIONAL["text_primary"])
    text_muted     = t.get("text_secondary",  DARK_PROFESSIONAL["text_secondary"])
    text_disabled  = t.get("text_disabled",   DARK_PROFESSIONAL["text_disabled"])

    success        = t.get("status_success",  DARK_PROFESSIONAL["status_success"])
    warning        = t.get("status_warning",  DARK_PROFESSIONAL["status_warning"])
    error          = t.get("status_error",    DARK_PROFESSIONAL["status_error"])
    info_color     = t.get("status_info",     DARK_PROFESSIONAL["status_info"])

    # rgba components for box-shadow -- derived from primary
    primary_rgb    = _hex_to_rgb_components(primary)

    # Mode flag -- used for a small number of mode-specific overrides
    is_light       = (t.get("mode", "dark") == "light")

    # Tooltip / popover background -- use bg_input for dark, white for light
    tooltip_bg     = bg_card if not is_light else "#FFFFFF"
    tooltip_border = border

    # Tab selected state -- on dark themes we want white text; on light
    # themes we want primary-colored text (avoids invisible white-on-white)
    tab_selected_color = "#FFFFFF" if not is_light else primary

    # Scrollbar colors
    scrollbar_track = bg_main
    scrollbar_thumb = border

    css = (
        "<style>\n"

        # ----------------------------------------------------------------
        # 1. Custom CSS variables -- these are the vars all structural CSS
        #    in app_resume.py already reads via var(--primary) etc.
        #    Changing these is enough to update every HTML helper and the
        #    structural CSS selectors that follow this block.
        # ----------------------------------------------------------------
        ":root {\n"
        "    --primary:       " + primary       + ";\n"
        "    --primary-hover: " + primary_hover + ";\n"
        "    --accent-bright: " + accent_bright + ";\n"
        "    --bg-main:       " + bg_main       + ";\n"
        "    --bg-card:       " + bg_card       + ";\n"
        "    --bg-input:      " + bg_input      + ";\n"
        "    --bg-sunken:     " + bg_sunken     + ";\n"
        "    --border:        " + border        + ";\n"
        "    --border-subtle: " + border_subtle + ";\n"
        "    --text-main:     " + text_main     + ";\n"
        "    --text-muted:    " + text_muted    + ";\n"
        "    --text-disabled: " + text_disabled + ";\n"
        "    --success:       " + success       + ";\n"
        "    --warning:       " + warning       + ";\n"
        "    --error:         " + error         + ";\n"
        "    --info:          " + info_color    + ";\n"
        "}\n"

        # ----------------------------------------------------------------
        # 2. Streamlit internal CSS variable overrides.
        #    Streamlit injects its own --primary-color, --background-color,
        #    etc. from config.toml. We override them here so the active
        #    theme is applied even if config.toml is absent or stale.
        #    Specificity: these live on :root so they naturally win over
        #    Streamlit's injected values which are also on :root -- the
        #    last declaration wins in CSS cascade order, and our block is
        #    injected after Streamlit's default stylesheet.
        # ----------------------------------------------------------------
        ":root {\n"
        "    --primary-color:              " + primary  + ";\n"
        "    --background-color:           " + bg_main  + ";\n"
        "    --secondary-background-color: " + bg_card  + ";\n"
        "    --text-color:                 " + text_main  + ";\n"
        "    --text-color-secondary:       " + text_muted + ";\n"
        "    --border-color:               " + border   + ";\n"
        "    --link-color:                 " + accent_bright + ";\n"
        "}\n"

        # ----------------------------------------------------------------
        # 3. App container background and base text color.
        #    Covers the full viewport and the inner view container.
        # ----------------------------------------------------------------
        ".stApp, [data-testid='stAppViewContainer'] {\n"
        "    background-color: " + bg_main  + " !important;\n"
        "    color:            " + text_main + " !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 4. Sidebar background, border, and widget input interiors.
        #    Streamlit swaps bg/secondaryBg for the sidebar panel, so the
        #    sidebar background becomes bg_card (secondary). Widget input
        #    interiors inside the sidebar use bg_input.
        # ----------------------------------------------------------------
        "[data-testid='stSidebar'] {\n"
        "    background-color: " + bg_card + " !important;\n"
        "    border-right: 1px solid " + border + " !important;\n"
        "}\n"

        "[data-testid='stSidebar'] .stNumberInput > div > div,\n"
        "[data-testid='stSidebar'] .stSelectbox > div > div,\n"
        "[data-testid='stSidebar'] .stMultiSelect > div > div {\n"
        "    background-color: " + bg_input + " !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 5. Streamlit native widget overrides -- primary color ring, slider,
        #    checkbox, radio, toggle, progress bar.
        #    These elements read --primary-color from Streamlit's injected
        #    vars. Because we overrode that above, they should update
        #    automatically. The explicit rules here are a belt-and-suspenders
        #    fallback for versions that use hard-coded selectors.
        # ----------------------------------------------------------------

        # Slider thumb and track fill
        "[data-testid='stSlider'] [role='slider'] {\n"
        "    background-color: " + primary + " !important;\n"
        "    border-color:     " + primary + " !important;\n"
        "}\n"

        "[data-testid='stSlider'] [data-testid='stSliderTrack'] > span:first-child {\n"
        "    background-color: " + primary + " !important;\n"
        "}\n"

        # Checkbox tick and border
        "[data-testid='stCheckbox'] [data-baseweb='checkbox'] [role='checkbox'] {\n"
        "    background-color: " + primary + " !important;\n"
        "    border-color:     " + primary + " !important;\n"
        "}\n"

        # Radio selected dot
        #"[data-testid='stRadio'] [data-baseweb='radio'] input:checked + div {\n"
        #"    background-color: " + primary + " !important;\n"
        #"    border-color:     " + primary + " !important;\n"
        #"}\n"

        # Toggle (st.toggle) active state
        "[data-testid='stToggle'] [data-checked='true'] {\n"
        "    background-color: " + primary + " !important;\n"
        "}\n"

        # Progress bar fill
        "[data-testid='stProgress'] > div > div > div > div {\n"
        "    background-color: " + primary + " !important;\n"
        "}\n"

        # st.metric delta positive/negative colors remain semantic
        "[data-testid='stMetricDelta'] svg {\n"
        "    fill: " + success + ";\n"
        "}\n"

        # ----------------------------------------------------------------
        # 6. Popover / tooltip / dropdown overlay background.
        #    Selectbox and multiselect open a BasewEB popover. Without this
        #    it uses Streamlit's default white background in dark mode.
        # ----------------------------------------------------------------
        "[data-baseweb='popover'] [data-baseweb='menu'],\n"
        "[data-baseweb='popover'] ul,\n"
        "[data-baseweb='tooltip'] {\n"
        "    background-color: " + tooltip_bg     + " !important;\n"
        "    border:           1px solid " + tooltip_border + " !important;\n"
        "    color:            " + text_main      + " !important;\n"
        "}\n"

        "[data-baseweb='popover'] [role='option'],\n"
        "[data-baseweb='popover'] [role='menuitem'] {\n"
        "    color: " + text_main + " !important;\n"
        "}\n"

        "[data-baseweb='popover'] [role='option']:hover,\n"
        "[data-baseweb='popover'] [role='menuitem']:hover,\n"
        "[data-baseweb='popover'] [aria-selected='true'] {\n"
        "    background-color: " + bg_input + " !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 7. Tab selected state -- mode-aware text colour so it is readable
        #    on both dark and light tab container backgrounds.
        # ----------------------------------------------------------------
        "button[data-baseweb='tab'][aria-selected='true'] {\n"
        "    color: " + tab_selected_color + " !important;\n"
        "    font-weight: 600 !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 8. Expander header background and border
        # ----------------------------------------------------------------
        "[data-testid='stExpander'] details {\n"
        "    background-color: " + bg_card + " !important;\n"
        "    border:           1px solid " + border + " !important;\n"
        "    border-radius:    8px !important;\n"
        "}\n"

        "[data-testid='stExpander'] summary {\n"
        "    color: " + text_main + " !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 9. Code block / st.code background
        # ----------------------------------------------------------------
        "[data-testid='stCode'],\n"
        "code, pre {\n"
        "    background-color: " + bg_sunken + " !important;\n"
        "    color:            " + text_main  + " !important;\n"
        "    border:           1px solid " + border + " !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 10. Dataframe / table header
        # ----------------------------------------------------------------
        "[data-testid='stDataFrame'] th,\n"
        ".stDataFrame th {\n"
        "    background-color: " + bg_card + " !important;\n"
        "    color:            " + text_muted + " !important;\n"
        "    border-color:     " + border + " !important;\n"
        "}\n"

        # ----------------------------------------------------------------
        # 11. Scrollbar styling (Webkit -- Chrome, Safari, Edge)
        # ----------------------------------------------------------------
        "::-webkit-scrollbar {\n"
        "    width:  6px;\n"
        "    height: 6px;\n"
        "}\n"

        "::-webkit-scrollbar-track {\n"
        "    background: " + scrollbar_track + ";\n"
        "}\n"

        "::-webkit-scrollbar-thumb {\n"
        "    background:    " + scrollbar_thumb + ";\n"
        "    border-radius: 3px;\n"
        "}\n"

        "::-webkit-scrollbar-thumb:hover {\n"
        "    background: " + primary + ";\n"
        "}\n"

        # ----------------------------------------------------------------
        # 12. Focus ring for inputs -- uses primary RGB for rgba() shadow
        # ----------------------------------------------------------------
        ".stNumberInput > div > div:focus-within,\n"
        ".stSelectbox > div > div:focus-within {\n"
        "    border-color: " + primary + " !important;\n"
        "    box-shadow: 0 0 0 2px rgba(" + primary_rgb + ", 0.25) !important;\n"
        "}\n"

        "</style>\n"
    )

    st.markdown(css, unsafe_allow_html=True)
