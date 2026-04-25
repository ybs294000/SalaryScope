"""
app/utils/config_writer.py
==========================
SalaryScope -- Runtime config.toml Theme Writer

On LOCAL: rewrites [theme], [theme.dark/light], [theme.dark/light.sidebar]
to match the active theme. Preserves all other sections byte-for-byte.
On STREAMLIT CLOUD: no-op (inject_theme_css handles per-session theming).
"""

import os
import re

import streamlit as st


_CONFIG_PATH = os.path.join(".streamlit", "config.toml")
_SECTION_RE  = re.compile(r"^\[([^\]]+)\]")

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
# Block builders
# ---------------------------------------------------------------------------

def _q(v: str) -> str:
    return '"' + v + '"'


def _build_flat_theme(t: dict) -> str:
    """[theme] flat block -- global options, matches original exactly."""
    mode    = t.get("mode",           "dark")
    primary = t.get("accent_primary", "#3E7DE0")
    bg      = t.get("surface_base",   "#0C1118")
    sec_bg  = t.get("surface_raised", "#141A22")
    text    = t.get("text_primary",   "#E6EAF0")

    chart = "\n".join("    " + _q(c) + "," for c in _CHART_COLORS)

    return (
        "[theme]\n"
        "base = " + _q(mode) + "\n"
        'font = "sans-serif"\n'
        "\n"
        'baseRadius   = "md"\n'
        'buttonRadius = "md"\n'
        "\n"
        "showWidgetBorder  = true\n"
        "showSidebarBorder = true\n"
        "\n"
        "chartCategoricalColors = [\n"
        + chart + "\n"
        "]\n"
        "\n"
        "primaryColor             = " + _q(primary) + "\n"
        "backgroundColor          = " + _q(bg)      + "\n"
        "secondaryBackgroundColor = " + _q(sec_bg)  + "\n"
        "textColor                = " + _q(text)    + "\n"
    )


def _build_named_theme(t: dict) -> str:
    """[theme.dark] or [theme.light] -- full section with all semantic keys."""
    mode     = t.get("mode",            "dark")
    section  = "theme.dark" if mode == "dark" else "theme.light"
    primary  = t.get("accent_primary",  "#3E7DE0")
    bg       = t.get("surface_base",    "#0C1118")
    sec_bg   = t.get("surface_raised",  "#141A22")
    text     = t.get("text_primary",    "#E6EAF0")
    link     = t.get("accent_bright",   "#4F8EF7")
    border   = t.get("border_default",  "#283142")
    success  = t.get("status_success",  "#22C55E")
    warning  = t.get("status_warning",  "#F59E0B")
    error    = t.get("status_error",    "#EF4444")
    muted    = t.get("text_secondary",  "#9CA6B5")
    colorway = t.get("colorway",        [])
    violet   = colorway[3] if len(colorway) > 3 else "#A78BFA"

    return (
        "[" + section + "]\n"
        "\n"
        "base = " + _q(mode) + "\n"
        "\n"
        "primaryColor             = " + _q(primary)  + "\n"
        "backgroundColor          = " + _q(bg)        + "\n"
        "secondaryBackgroundColor = " + _q(sec_bg)    + "\n"
        "textColor                = " + _q(text)      + "\n"
        "linkColor                = " + _q(link)      + "\n"
        "borderColor              = " + _q(border)    + "\n"
        "dataframeHeaderBackgroundColor = " + _q(sec_bg) + "\n"
        "\n"
        "greenColor  = " + _q(success) + "\n"
        "orangeColor = " + _q(warning) + "\n"
        "redColor    = " + _q(error)   + "\n"
        "blueColor   = " + _q(link)    + "\n"
        "violetColor = " + _q(violet)  + "\n"
        "yellowColor = " + _q(warning) + "\n"
        "grayColor   = " + _q(muted)   + "\n"
    )


def _build_sidebar(t: dict) -> str:
    """[theme.dark.sidebar] or [theme.light.sidebar]."""
    mode    = t.get("mode",             "dark")
    section = "theme.dark.sidebar" if mode == "dark" else "theme.light.sidebar"
    panel   = t.get("surface_raised",   "#141A22")   # sidebar panel bg
    inputs  = t.get("surface_overlay",  "#1B2230")   # widget interiors
    border  = t.get("border_default",   "#283142")
    bright  = t.get("accent_bright",    "#4F8EF7")   # brighter primary for sidebar

    return (
        "[" + section + "]\n"
        "\n"
        "backgroundColor          = " + _q(panel)  + "\n"
        "secondaryBackgroundColor = " + _q(inputs) + "\n"
        "borderColor              = " + _q(border) + "\n"
        "primaryColor             = " + _q(bright) + "\n"
    )


# ---------------------------------------------------------------------------
# Config rewriter
# ---------------------------------------------------------------------------

def _rewrite_config(original: str, t: dict) -> str:
    """
    Replace the three theme sections in *original* with fresh content built
    from *t*. All other lines are passed through unchanged.
    """
    mode = t.get("mode", "dark")
    named   = "theme.dark"         if mode == "dark" else "theme.light"
    sidebar = "theme.dark.sidebar" if mode == "dark" else "theme.light.sidebar"

    targets = {"theme", named, sidebar}
    new_content = {
        "theme":   _build_flat_theme(t),
        named:     _build_named_theme(t),
        sidebar:   _build_sidebar(t),
    }

    lines  = original.splitlines(keepends=True)
    output = []
    skip   = False

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("["):
            m = _SECTION_RE.match(stripped)
            if m:
                sec  = m.group(1).strip().lower()
                skip = sec in targets
                if skip:
                    output.append(new_content[sec])
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
