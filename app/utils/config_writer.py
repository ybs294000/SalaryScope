"""
app/utils/config_writer.py
==========================
SalaryScope -- Runtime config.toml Theme Writer

Rewrites .streamlit/config.toml so that all six theme sections always
reflect the active theme. Preserves [browser], [server], and all comments.

Structure written (matches original config.toml exactly):

  [theme]
    base, font, baseRadius, buttonRadius,
    showWidgetBorder, showSidebarBorder, chartCategoricalColors
    -- NO color values here; those live in the named sections below.

  [theme.dark]           15 color keys
  [theme.dark.sidebar]    4 keys
  [theme.light]          15 color keys  (LIGHT_CLEAN defaults when in dark mode)
  [theme.light.sidebar]   4 keys        (LIGHT_CLEAN defaults when in dark mode)

When active theme is dark:   [theme.dark/*] <- active, [theme.light/*] <- LIGHT_CLEAN
When active theme is light:  [theme.light/*] <- active, [theme.dark/*] <- DARK_PROFESSIONAL

This keeps both mode sections fully populated so Streamlit can switch between
them via its own settings menu without hitting missing-key errors.

On STREAMLIT CLOUD: no-op. inject_theme_css() handles per-session theming.
"""

import os
import re

import streamlit as st


_CONFIG_PATH = os.path.join(".streamlit", "config.toml")
_SECTION_RE  = re.compile(r"^\[([^\]]+)\]")

# Sections this writer owns. [browser] and [server] are never touched.
_OWNED = {"theme", "theme.dark", "theme.dark.sidebar",
          "theme.light", "theme.light.sidebar"}

# Fixed Dark Professional defaults -- written into [theme.dark/*] when the
# active theme is light so that the dark sections remain fully populated.
_DP_DARK = {
    "primaryColor":                  "#3E7DE0",
    "backgroundColor":               "#0C1118",
    "secondaryBackgroundColor":      "#141A22",
    "textColor":                     "#E6EAF0",
    "linkColor":                     "#4F8EF7",
    "borderColor":                   "#283142",
    "dataframeHeaderBackgroundColor":"#141A22",
    "greenColor":                    "#22C55E",
    "orangeColor":                   "#F59E0B",
    "redColor":                      "#EF4444",
    "blueColor":                     "#4F8EF7",
    "violetColor":                   "#A78BFA",
    "yellowColor":                   "#F59E0B",
    "grayColor":                     "#9CA6B5",
}
_DP_SIDEBAR = {
    "backgroundColor":          "#141A22",
    "secondaryBackgroundColor": "#1B2230",
    "borderColor":              "#283142",
    "primaryColor":             "#4F8EF7",
}

# Fixed Light Clean defaults -- written into [theme.light/*] when the
# active theme is dark so the light sections remain fully populated.
_LC_LIGHT = {
    "primaryColor":                  "#2563EB",
    "backgroundColor":               "#FAFAFA",
    "secondaryBackgroundColor":      "#FFFFFF",
    "textColor":                     "#1A202C",
    "linkColor":                     "#1D4ED8",
    "borderColor":                   "#CBD5E1",
    "dataframeHeaderBackgroundColor":"#F4F6F9",
    "greenColor":                    "#16A34A",
    "orangeColor":                   "#D97706",
    "redColor":                      "#DC2626",
    "blueColor":                     "#2563EB",
    "violetColor":                   "#7C3AED",
    "yellowColor":                   "#D97706",
    "grayColor":                     "#4A5568",
}
_LC_SIDEBAR = {
    "backgroundColor":          "#F4F6F9",
    "secondaryBackgroundColor": "#FFFFFF",
    "borderColor":              "#E2E8F0",
    "primaryColor":             "#2563EB",
}

_CHART_COLORS = [
    "#4F8EF7", "#38BDF8", "#34D399", "#A78BFA",
    "#F59E0B", "#FB923C", "#F472B6", "#22D3EE",
]


# ---------------------------------------------------------------------------
# Deployment detection  (mirrors admin_panel._is_local())
# ---------------------------------------------------------------------------

def _is_local() -> bool:
    try:
        val = st.secrets.get("IS_LOCAL", None)
        if val is not None:
            return bool(val)
    except Exception:
        pass
    try:
        import os as _os
        if _os.environ.get("STREAMLIT_SHARING_MODE"):
            return False
        home = _os.environ.get("HOME", "")
        cwd  = _os.getcwd()
        if home in ("/home/appuser", "/app") or cwd.startswith("/app"):
            return False
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# Token -> config.toml value extraction
# ---------------------------------------------------------------------------

def _active_colors(t: dict) -> dict:
    """Extract all 14 named-section color values from an active theme dict."""
    colorway = t.get("colorway", [])
    violet   = colorway[3] if len(colorway) > 3 else "#A78BFA"
    sec_bg   = t.get("surface_raised", "#141A22")
    return {
        "primaryColor":                  t.get("accent_primary",  "#3E7DE0"),
        "backgroundColor":               t.get("surface_base",    "#0C1118"),
        "secondaryBackgroundColor":      sec_bg,
        "textColor":                     t.get("text_primary",    "#E6EAF0"),
        "linkColor":                     t.get("accent_bright",   "#4F8EF7"),
        "borderColor":                   t.get("border_default",  "#283142"),
        "dataframeHeaderBackgroundColor":sec_bg,
        "greenColor":                    t.get("status_success",  "#22C55E"),
        "orangeColor":                   t.get("status_warning",  "#F59E0B"),
        "redColor":                      t.get("status_error",    "#EF4444"),
        "blueColor":                     t.get("accent_bright",   "#4F8EF7"),
        "violetColor":                   violet,
        "yellowColor":                   t.get("status_warning",  "#F59E0B"),
        "grayColor":                     t.get("text_secondary",  "#9CA6B5"),
    }

def _active_sidebar(t: dict) -> dict:
    """Extract sidebar color values from an active theme dict."""
    return {
        "backgroundColor":          t.get("surface_raised",  "#141A22"),
        "secondaryBackgroundColor": t.get("surface_overlay", "#1B2230"),
        "borderColor":              t.get("border_default",  "#283142"),
        "primaryColor":             t.get("accent_bright",   "#4F8EF7"),
    }


# ---------------------------------------------------------------------------
# Block builders  (match original config.toml format exactly)
# ---------------------------------------------------------------------------

def _q(v: str) -> str:
    return '"' + str(v) + '"'

def _build_flat(mode: str) -> str:
    chart = "\n".join("    " + _q(c) + "," for c in _CHART_COLORS)
    return (
        "[theme]\n"
        "base = " + _q(mode) + "\n"
        "# sans-serif lets Inter/Segoe UI declared in CSS act as the effective font.\n"
        'font = "sans-serif"\n'
        "\n"
        '# "md" ~= 6px -- matches border-radius:6px throughout the existing CSS.\n'
        'baseRadius   = "md"\n'
        'buttonRadius = "md"\n'
        "\n"
        "# Always show widget borders at rest.\n"
        "showWidgetBorder  = true\n"
        "\n"
        "# Visible dividing line between sidebar and main body in both themes.\n"
        "showSidebarBorder = true\n"
        "\n"
        "# Plotly/Altair colorway fallback. Values = Dark Professional COLORWAY.\n"
        "chartCategoricalColors = [\n"
        + chart + "\n"
        "]\n"
    )

def _build_named(mode: str, colors: dict) -> str:
    sec = "theme.dark" if mode == "dark" else "theme.light"
    c = colors
    return (
        "[" + sec + "]\n"
        "\n"
        "base = " + _q(mode) + "\n"
        "\n"
        "primaryColor             = " + _q(c["primaryColor"])                   + "\n"
        "backgroundColor          = " + _q(c["backgroundColor"])                + "\n"
        "secondaryBackgroundColor = " + _q(c["secondaryBackgroundColor"])       + "\n"
        "textColor                = " + _q(c["textColor"])                      + "\n"
        "linkColor                = " + _q(c["linkColor"])                      + "\n"
        "borderColor              = " + _q(c["borderColor"])                    + "\n"
        "dataframeHeaderBackgroundColor = " + _q(c["dataframeHeaderBackgroundColor"]) + "\n"
        "\n"
        "greenColor  = " + _q(c["greenColor"])  + "\n"
        "orangeColor = " + _q(c["orangeColor"]) + "\n"
        "redColor    = " + _q(c["redColor"])    + "\n"
        "blueColor   = " + _q(c["blueColor"])   + "\n"
        "violetColor = " + _q(c["violetColor"]) + "\n"
        "yellowColor = " + _q(c["yellowColor"]) + "\n"
        "grayColor   = " + _q(c["grayColor"])   + "\n"
    )

def _build_sidebar(mode: str, sb: dict) -> str:
    sec = "theme.dark.sidebar" if mode == "dark" else "theme.light.sidebar"
    return (
        "[" + sec + "]\n"
        "\n"
        "backgroundColor          = " + _q(sb["backgroundColor"])          + "\n"
        "secondaryBackgroundColor = " + _q(sb["secondaryBackgroundColor"]) + "\n"
        "borderColor              = " + _q(sb["borderColor"])              + "\n"
        "primaryColor             = " + _q(sb["primaryColor"])             + "\n"
    )


# ---------------------------------------------------------------------------
# Config rewriter
# ---------------------------------------------------------------------------

def _build_all_sections(theme_dict: dict) -> dict:
    """
    Build content for all five owned sections.
    Active mode sections use theme_dict values.
    Inactive mode sections use fixed defaults so they stay fully populated.
    Returns dict keyed by normalised section name.
    """
    mode = theme_dict.get("mode", "dark")
    active_c  = _active_colors(theme_dict)
    active_sb = _active_sidebar(theme_dict)

    if mode == "dark":
        dark_colors  = active_c
        dark_sb      = active_sb
        light_colors = _LC_LIGHT
        light_sb     = _LC_SIDEBAR
    else:
        light_colors = active_c
        light_sb     = active_sb
        dark_colors  = _DP_DARK
        dark_sb      = _DP_SIDEBAR

    return {
        "theme":               _build_flat(mode),
        "theme.dark":          _build_named("dark",  dark_colors),
        "theme.dark.sidebar":  _build_sidebar("dark",  dark_sb),
        "theme.light":         _build_named("light", light_colors),
        "theme.light.sidebar": _build_sidebar("light", light_sb),
    }


def _rewrite_config(original: str, theme_dict: dict) -> str:
    """
    Replace all five owned sections in *original*.
    [browser], [server], and all surrounding comments are preserved.
    """
    new_sections = _build_all_sections(theme_dict)

    lines  = original.splitlines(keepends=True)
    output = []
    skip   = False

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("[") and not stripped.startswith("#"):
            m = _SECTION_RE.match(stripped)
            if m:
                sec  = m.group(1).strip().lower()
                skip = sec in _OWNED
                if skip:
                    output.append(new_sections[sec])
                    continue

        if not skip:
            output.append(line)

    return "".join(output)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_theme_to_config(theme_dict: dict) -> bool:
    """
    Write all theme sections of config.toml to match theme_dict.
    No-op on Streamlit Cloud. Atomic write on local.
    """
    if not isinstance(theme_dict, dict):
        return False

    if not _is_local():
        return True

    try:
        config_dir = os.path.dirname(_CONFIG_PATH)
        if config_dir and not os.path.isdir(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        original = ""
        if os.path.isfile(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
                original = fh.read()

        updated  = _rewrite_config(original, theme_dict)
        tmp_path = _CONFIG_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(updated)
        os.replace(tmp_path, _CONFIG_PATH)
        return True

    except Exception as exc:
        st.warning(
            "Theme could not be saved to config.toml: "
            + str(exc)
            + ". The visual theme is still applied for this session."
        )
        return False
