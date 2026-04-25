"""
utils/salary_card.py
--------------------
Generates a shareable 1200x630 salary prediction card as PNG using Pillow.

Font bundling
-------------
The four Poppins weights used (Bold, Medium, Regular, Light) must be placed at:
    assets/fonts/Poppins-Bold.ttf
    assets/fonts/Poppins-Medium.ttf
    assets/fonts/Poppins-Regular.ttf
    assets/fonts/Poppins-Light.ttf

Paths are resolved relative to this file's location (../../assets/fonts/),
making the module fully portable across Windows, Mac, Linux, and Streamlit Cloud.

If the bundled fonts are missing, the module falls back automatically to
system DejaVu Sans, which is present on all Streamlit Cloud deployments.
No exception is raised either way.

Requirements
------------
Pillow is an indirect dependency via matplotlib (already in requirements.txt).
It is good practice to add it explicitly:
    Pillow>=10.0.0
No other new dependencies are introduced.

Public API
----------
generate_salary_card(
    predicted_usd, job_title, location, model_name,
    band_label=None, career_stage=None,
    experience_lvl=None, tagline=None
) -> bytes
    Returns PNG bytes for st.download_button(data=..., mime="image/png").

render_salary_card_download(
    predicted_usd, job_title, location, model_name,
    band_label=None, career_stage=None, experience_lvl=None,
    tagline=None, key="salary_card_download"
) -> None
    Renders a Streamlit download button. Drop alongside the PDF button.

Integration
-----------
App 1 (manual_prediction_tab.py and resume_analysis_tab.py):
    from app.utils.salary_card import render_salary_card_download
    render_salary_card_download(
        predicted_usd = data["prediction"],
        job_title     = data["input_details"]["Job Title"],
        location      = data["input_details"]["Country"],
        model_name    = "Model 1 — General Salary",
        band_label    = data["salary_band_label"],
        career_stage  = data["career_stage_label"],
        key           = "card_dl_manual_a1",
    )

App 2:
    render_salary_card_download(
        predicted_usd  = prediction_a2,
        job_title      = data_a2["input_details"]["Job Title"],
        location       = data_a2["input_details"]["Company Location"],
        model_name     = "Model 2 — Data Science Salary",
        experience_lvl = data_a2["input_details"]["Experience Level"],
        key            = "card_dl_manual_a2",
    )
"""

import io
import pathlib
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Font resolution — portable, no hardcoded OS paths
# ---------------------------------------------------------------------------

# This file lives at  app/utils/salary_card.py
# assets/fonts/       lives at  <project_root>/assets/fonts/
# So from this file:  ../../assets/fonts/
_HERE       = pathlib.Path(__file__).resolve().parent          # app/utils/
_ASSET_DIR  = _HERE.parent.parent / "assets" / "fonts"        # <root>/assets/fonts/

# System fallback paths that are guaranteed on Streamlit Cloud (Ubuntu/Debian)
_SYS_DEJAVU     = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_SYS_DEJAVU_B   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _resolve_font(weight: str) -> pathlib.Path | None:
    """
    Return the path to Poppins-<weight>.ttf, or None if not found.
    Search order:
      1. <project_root>/assets/fonts/   (bundled — preferred, portable)
      2. /usr/share/fonts/truetype/google-fonts/  (system, Streamlit Cloud container)
    """
    filename = f"Poppins-{weight}.ttf"
    bundled = _ASSET_DIR / filename
    if bundled.exists():
        return bundled
    system = pathlib.Path(f"/usr/share/fonts/truetype/google-fonts/{filename}")
    if system.exists():
        return system
    return None


def _f(weight: str, size: int, bold_fallback: bool = False) -> ImageFont.FreeTypeFont:
    """
    Load Poppins at the given weight and size.
    Falls back to DejaVu Sans (always present on Streamlit Cloud) if Poppins
    is unavailable, then to Pillow's built-in bitmap font as a last resort.
    """
    path = _resolve_font(weight)
    if path is not None:
        try:
            return ImageFont.truetype(str(path), size)
        except (IOError, OSError):
            pass

    # DejaVu fallback
    fallback = _SYS_DEJAVU_B if bold_fallback else _SYS_DEJAVU
    try:
        return ImageFont.truetype(fallback, size)
    except (IOError, OSError):
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Colours — match SalaryScope dark theme
# ---------------------------------------------------------------------------
C_BG_TOP  = (13,  21,  38)
C_BG_BOT  = (18,  32,  58)
C_PRIMARY = (79,  142, 247)
C_WHITE   = (255, 255, 255)
C_MAIN    = (226, 232, 240)
C_MUTED   = (148, 163, 184)
C_DIVIDER = (51,  65,  85)

_BAND_COL = {
    "Early Career Range": ((52,  211, 153), (16, 60,  38)),
    "Professional Range": ((96,  165, 250), (18, 38,  80)),
    "Executive Range":    ((251, 191, 36),  (58, 44,  10)),
}

C_STAGE_FG = (52,  211, 153)
C_STAGE_BG = (12,  46,  30)
C_STAGE_BD = (28,  90,  58)
C_EXP_FG   = (147, 197, 253)
C_EXP_BG   = (14,  30,  64)
C_EXP_BD   = (38,  68,  140)
C_PILL_FG  = C_MAIN
C_PILL_BG  = (24,  40,  72)
C_PILL_BD  = (50,  72,  120)


# ---------------------------------------------------------------------------
# Drawing utilities
# ---------------------------------------------------------------------------

def _bbox(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)

def _tw(draw, text, font):
    b = _bbox(draw, text, font)
    return b[2] - b[0]

def _th(draw, text, font):
    b = _bbox(draw, text, font)
    return b[3] - b[1]

def _draw_centred(draw, text, font, y, w, colour):
    x = (w - _tw(draw, text, font)) // 2
    draw.text((x, y), text, font=font, fill=colour)

def _wrap(draw, text, font, max_px):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if _tw(draw, test, font) <= max_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [text]

def _rrect(draw, x0, y0, x1, y1, r, fill, outline=None, width=1):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r,
                            fill=fill, outline=outline, width=width)

def _pill(draw, text, font, cx, cy, fg, bg, border, px=16, py=7):
    tw = _tw(draw, text, font)
    th = _th(draw, text, font)
    pw, ph = tw + px * 2, th + py * 2
    x0, y0 = cx - pw // 2, cy - ph // 2
    _rrect(draw, x0, y0, x0 + pw, y0 + ph, ph // 2, bg, border, 1)
    draw.text((x0 + px, y0 + py), text, font=font, fill=fg)
    return pw, ph

def _gradient_bg(img, w, h):
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * t)
        g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * t)
        b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


# ---------------------------------------------------------------------------
# Auto tagline
# ---------------------------------------------------------------------------

def _auto_tagline(band_label, career_stage, experience_lvl):
    if band_label == "Executive Range":
        return "Top-tier compensation — executive level."
    if band_label == "Early Career Range":
        return "A strong start — room ahead to grow."
    if band_label == "Professional Range":
        return "Solid mid-career market value."
    if experience_lvl and "Executive" in experience_lvl:
        return "Executive-level data science salary."
    if experience_lvl and "Senior" in experience_lvl:
        return "Senior-level market estimate."
    if career_stage and "Leadership" in career_stage:
        return "Leadership stage — competitive range."
    if career_stage and "Entry" in career_stage:
        return "Entry stage — building momentum."
    return "Your salary estimate from SalaryScope."


# ---------------------------------------------------------------------------
# Main card generator
# ---------------------------------------------------------------------------

def generate_salary_card(
    predicted_usd:  float,
    job_title:      str,
    location:       str,
    model_name:     str,
    band_label:     str | None = None,
    career_stage:   str | None = None,
    experience_lvl: str | None = None,
    tagline:        str | None = None,
) -> bytes:
    """Return PNG bytes of a 1200x630 shareable salary card."""

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), C_BG_TOP)
    _gradient_bg(img, W, H)
    draw = ImageDraw.Draw(img)

    # Fonts
    fn_num    = _f("Bold",    88, bold_fallback=True)
    fn_dollar = _f("Bold",    60, bold_fallback=True)
    fn_title  = _f("Bold",    36, bold_fallback=True)
    fn_loc    = _f("Medium",  24)
    fn_pill   = _f("Medium",  20)
    fn_tag    = _f("Light",   22)
    fn_brand  = _f("Bold",    21, bold_fallback=True)
    fn_sub    = _f("Regular", 16)
    fn_footer = _f("Regular", 18)
    fn_url    = _f("Medium",  18)

    # Left accent stripe
    for x in range(5):
        opacity = 1.0 - x * 0.18
        draw.line([(x, 0), (x, H)],
                  fill=tuple(int(c * opacity) for c in C_PRIMARY))

    # Bottom accent line
    for y_off in range(3):
        opacity = 1.0 - y_off * 0.35
        draw.line([(0, H - 3 + y_off), (W, H - 3 + y_off)],
                  fill=tuple(int(c * opacity) for c in C_PRIMARY))

    # ---- Top-left pill (band / experience level / model) ----
    top_pill_text = band_label or experience_lvl or model_name.split("—")[0].strip()
    if band_label and band_label in _BAND_COL:
        tp_fg, tp_bg = _BAND_COL[band_label]
        tp_bd = tuple(min(255, c + 30) for c in tp_bg)
    else:
        tp_fg, tp_bg = C_PRIMARY, (16, 34, 72)
        tp_bd = (40, 70, 140)

    _pill(draw, top_pill_text, fn_pill,
          cx=30 + _tw(draw, top_pill_text, fn_pill) // 2 + 16,
          cy=40, fg=tp_fg, bg=tp_bg, border=tp_bd, px=16, py=8)

    # ---- Top-right: "ML-Powered · SalaryScope" ----
    brand, sub = "SalaryScope", "ML-Powered · "
    bw, sw = _tw(draw, brand, fn_brand), _tw(draw, sub, fn_sub)
    brand_x = W - 40 - bw
    sub_x   = brand_x - sw - 4
    brand_y = 28
    sub_y   = brand_y + (_th(draw, brand, fn_brand) - _th(draw, sub, fn_sub)) // 2 + 3
    draw.text((sub_x, sub_y), sub, font=fn_sub, fill=C_MUTED)
    draw.text((brand_x, brand_y), brand, font=fn_brand, fill=C_PRIMARY)

    # ---- Salary hero ----
    num_text = f"{predicted_usd:,.0f}"
    dol_text = "$"
    num_bb   = _bbox(draw, num_text, fn_num)
    dol_bb   = _bbox(draw, dol_text, fn_dollar)
    num_w    = num_bb[2] - num_bb[0]
    dol_w    = dol_bb[2] - dol_bb[0]
    num_h    = num_bb[3]       # actual glyph bottom from draw origin
    dol_h    = dol_bb[3]

    total_w  = dol_w + 4 + num_w
    hero_cx  = W // 2
    hero_top = int(H * 0.34) - num_h // 2   # vertically centred in upper 34%

    num_x  = hero_cx - total_w // 2 + dol_w + 4
    dol_x  = hero_cx - total_w // 2
    num_y  = hero_top
    dol_y  = hero_top + (num_h - dol_h)     # baseline-aligned to number

    shadow = (20, 45, 100)
    for ox, oy in [(2, 2), (1, 2)]:
        draw.text((dol_x + ox, dol_y + oy), dol_text, font=fn_dollar, fill=shadow)
        draw.text((num_x + ox, num_y + oy), num_text, font=fn_num,    fill=shadow)
    draw.text((dol_x, dol_y), dol_text, font=fn_dollar, fill=C_MUTED)
    draw.text((num_x, num_y), num_text, font=fn_num,    fill=C_WHITE)

    # "per year · USD" — below actual glyph bottom
    per_y = num_y + num_bb[3] + 10
    _draw_centred(draw, "per year  \u00b7  USD", fn_sub, per_y, W, C_MUTED)

    # ---- Job title ----
    title_y = per_y + _th(draw, "per year", fn_sub) + 22
    for line in _wrap(draw, job_title, fn_title, W - 120):
        _draw_centred(draw, line, fn_title, title_y, W, C_WHITE)
        title_y += _bbox(draw, line, fn_title)[3] + 6

    # ---- Location ----
    loc_y = title_y + 4
    _draw_centred(draw, location, fn_loc, loc_y, W, C_MUTED)
    loc_bottom = loc_y + _th(draw, location, fn_loc)

    # ---- Pills row ----
    pills = []
    if career_stage:
        pills.append((career_stage,    C_STAGE_FG, C_STAGE_BG, C_STAGE_BD))
    elif experience_lvl:
        pills.append((experience_lvl,  C_EXP_FG,   C_EXP_BG,   C_EXP_BD))

    monthly = predicted_usd / 12
    hourly  = predicted_usd / 2080
    pills.append((f"${monthly:,.0f} / mo", C_PILL_FG, C_PILL_BG, C_PILL_BD))
    pills.append((f"${hourly:,.0f} / hr",  C_PILL_FG, C_PILL_BG, C_PILL_BD))

    pill_gap  = 14
    pill_h    = _th(draw, pills[0][0], fn_pill) + 16
    pwidths   = [_tw(draw, p[0], fn_pill) + 34 for p in pills]
    total_pw  = sum(pwidths) + pill_gap * (len(pills) - 1)
    pill_row_y = loc_bottom + 22
    pill_cx   = (W - total_pw) // 2

    for i, (ptext, fg, bg, bd) in enumerate(pills):
        cx = pill_cx + pwidths[i] // 2
        cy = pill_row_y + pill_h // 2
        _pill(draw, ptext, fn_pill, cx, cy, fg, bg, bd, px=15, py=7)
        pill_cx += pwidths[i] + pill_gap

    pill_bottom = pill_row_y + pill_h

    # ---- Divider ----
    div_y = pill_bottom + 20
    draw.line([(60, div_y), (W - 60, div_y)], fill=C_DIVIDER, width=1)

    # ---- Tagline ----
    if tagline is None:
        tagline = _auto_tagline(band_label, career_stage, experience_lvl)
    tag_y = div_y + 18
    for line in _wrap(draw, tagline, fn_tag, W - 200):
        _draw_centred(draw, line, fn_tag, tag_y, W, C_MUTED)
        tag_y += _th(draw, line, fn_tag) + 5

    # ---- Footer — left / centre / right, no overlap ----
    footer_y  = H - 42
    left_text = "Generated by SalaryScope"
    url_text  = "salaryscope-app.streamlit.app"
    left_w    = _tw(draw, left_text, fn_footer)
    url_w     = _tw(draw, url_text,  fn_url)

    draw.text((40, footer_y), left_text, font=fn_footer, fill=C_MUTED)
    draw.text((W - 40 - url_w, footer_y), url_text, font=fn_url, fill=C_PRIMARY)

    max_model_w  = W - left_w - url_w - 160
    model_short  = model_name.split("(")[0].strip()
    while model_short and _tw(draw, model_short, fn_footer) > max_model_w:
        model_short = model_short[:-1].rstrip()
    if model_short != model_name.split("(")[0].strip():
        model_short += "\u2026"
    _draw_centred(draw, model_short, fn_footer, footer_y, W, C_DIVIDER)

    # ---- Serialise ----
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Streamlit convenience wrapper
# ---------------------------------------------------------------------------

def render_salary_card_download(
    predicted_usd:  float,
    job_title:      str,
    location:       str,
    model_name:     str,
    band_label:     str | None = None,
    career_stage:   str | None = None,
    experience_lvl: str | None = None,
    tagline:        str | None = None,
    key:            str = "salary_card_download",
) -> None:
    """Generate the salary card and render a Streamlit download button."""
    import streamlit as st
    png  = generate_salary_card(
        predicted_usd, job_title, location, model_name,
        band_label, career_stage, experience_lvl, tagline,
    )
    safe = job_title.replace(" ", "_").replace("/", "-")[:40]
    st.download_button(
        label     = ":material/share: Download Salary Card (PNG)",
        data      = png,
        file_name = f"salary_card_{safe}.png",
        mime      = "image/png",
        key       = key,
        help      = "Download a shareable salary prediction card as a PNG image.",
    )