"""
utils/salary_card.py
--------------------
Generates a shareable 1200x630 salary prediction card as PNG using Pillow.

Public API
----------
generate_salary_card(predicted_usd, job_title, location, model_name,
                     band_label=None, career_stage=None,
                     experience_lvl=None, tagline=None) -> bytes

render_salary_card_download(predicted_usd, job_title, location, model_name,
                             band_label=None, career_stage=None,
                             experience_lvl=None, tagline=None,
                             key="salary_card_download") -> None

Integration
-----------
App 1 — place after PDF section in manual_prediction_tab.py and
         resume_analysis_tab.py:

    from app.utils.salary_card import render_salary_card_download
    render_salary_card_download(
        predicted_usd = prediction,
        job_title     = data["input_details"]["Job Title"],
        location      = data["input_details"]["Country"],
        model_name    = "Model 1 — General Salary",
        band_label    = salary_band_label,
        career_stage  = career_stage_label,
        key           = "card_dl_manual_a1",
    )

App 2 — same location:
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
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Font paths
# ---------------------------------------------------------------------------
_F_BOLD    = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
_F_MEDIUM  = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
_F_REGULAR = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
_F_LIGHT   = "/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf"
_F_FALLBK  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_F_FALLBKB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _f(path: str, size: int, fallback: str = _F_FALLBK) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        try:
            return ImageFont.truetype(fallback, size)
        except (IOError, OSError):
            return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Colours — match SalaryScope dark theme exactly
# ---------------------------------------------------------------------------
C_BG_TOP    = (13,  21,  38)   # #0D1526
C_BG_BOT    = (18,  32,  58)   # #12203A
C_PRIMARY   = (79,  142, 247)  # #4F8EF7
C_WHITE     = (255, 255, 255)
C_MAIN      = (226, 232, 240)  # #E2E8F0
C_MUTED     = (148, 163, 184)  # #94A3B8
C_DIVIDER   = (51,  65,  85)   # #334155
C_CARD      = (22,  35,  58)   # #16233A  slightly lighter than bg

# Band accent colours
_BAND_COL = {
    "Early Career Range": ((52,  211, 153), (16, 60,  38)),   # green fg, dark bg
    "Professional Range": ((96,  165, 250), (18, 38,  80)),   # blue  fg, dark bg
    "Executive Range":    ((251, 191, 36),  (58, 44,  10)),   # amber fg, dark bg
}
_BAND_DEFAULT = (C_PRIMARY, (18, 36, 72))

# Career stage pill colour
C_STAGE_FG = (52,  211, 153)
C_STAGE_BG = (12,  46,  30)
C_STAGE_BD = (28,  90,  58)

# Experience level pill colour (App 2)
C_EXP_FG   = (147, 197, 253)
C_EXP_BG   = (14,  30,  64)
C_EXP_BD   = (38,  68,  140)

# Breakdown pill colour
C_PILL_FG  = C_MAIN
C_PILL_BG  = (24,  40,  72)
C_PILL_BD  = (50,  72,  120)


# ---------------------------------------------------------------------------
# Drawing utilities
# ---------------------------------------------------------------------------

def _bbox(draw: ImageDraw.Draw, text: str, font) -> tuple[int, int, int, int]:
    """Return (x0, y0, x1, y1) glyph bounding box."""
    return draw.textbbox((0, 0), text, font=font)


def _tw(draw: ImageDraw.Draw, text: str, font) -> int:
    b = _bbox(draw, text, font)
    return b[2] - b[0]


def _th(draw: ImageDraw.Draw, text: str, font) -> int:
    b = _bbox(draw, text, font)
    return b[3] - b[1]


def _glyph_bottom(draw: ImageDraw.Draw, text: str, font) -> int:
    """Actual bottom of rendered glyph (not line height)."""
    return _bbox(draw, text, font)[3]


def _draw_text_centred(draw, text, font, y, canvas_w, colour):
    x = (canvas_w - _tw(draw, text, font)) // 2
    draw.text((x, y), text, font=font, fill=colour)


def _wrap(draw: ImageDraw.Draw, text: str, font, max_px: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if _tw(draw, test, font) <= max_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def _rounded_rect(draw, x0, y0, x1, y1, r, fill, outline=None, width=1):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill,
                            outline=outline, width=width)


def _pill(draw, text, font, cx, cy, fg, bg, border, px=16, py=7):
    """Draw a pill centred at (cx, cy). Returns (pill_w, pill_h)."""
    tw = _tw(draw, text, font)
    th = _th(draw, text, font)
    pw = tw + px * 2
    ph = th + py * 2
    x0 = cx - pw // 2
    y0 = cy - ph // 2
    x1 = x0 + pw
    y1 = y0 + ph
    _rounded_rect(draw, x0, y0, x1, y1, r=ph // 2, fill=bg, outline=border, width=1)
    # Centre text inside pill
    tx = x0 + px
    ty = y0 + py
    draw.text((tx, ty), text, font=font, fill=fg)
    return pw, ph


def _gradient_bg(img: Image.Image, w: int, h: int):
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * t)
        g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * t)
        b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


# ---------------------------------------------------------------------------
# Tagline generator
# ---------------------------------------------------------------------------

def _tagline(band_label, career_stage, experience_lvl) -> str:
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
    predicted_usd: float,
    job_title: str,
    location: str,
    model_name: str,
    band_label:     str | None = None,
    career_stage:   str | None = None,
    experience_lvl: str | None = None,
    tagline:        str | None = None,
) -> bytes:
    """Return PNG bytes of a 1200×630 salary card."""

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), C_BG_TOP)
    _gradient_bg(img, W, H)
    draw = ImageDraw.Draw(img)

    # -----------------------------------------------------------------------
    # Load fonts
    # -----------------------------------------------------------------------
    fn_num    = _f(_F_BOLD,    88, _F_FALLBKB)   # salary number
    fn_dollar = _f(_F_BOLD,    60, _F_FALLBKB)   # "$" prefix
    fn_title  = _f(_F_BOLD,    36, _F_FALLBKB)   # job title
    fn_loc    = _f(_F_MEDIUM,  24, _F_FALLBK)    # location
    fn_pill   = _f(_F_MEDIUM,  20, _F_FALLBK)    # pills
    fn_tag    = _f(_F_LIGHT,   22, _F_FALLBK)    # tagline
    fn_brand  = _f(_F_BOLD,    21, _F_FALLBKB)   # SalaryScope brand
    fn_sub    = _f(_F_REGULAR, 16, _F_FALLBK)    # ML-Powered / per year
    fn_footer = _f(_F_REGULAR, 18, _F_FALLBK)    # footer text
    fn_url    = _f(_F_MEDIUM,  18, _F_FALLBK)    # footer URL

    # -----------------------------------------------------------------------
    # Left accent stripe — 5px, primary colour
    # -----------------------------------------------------------------------
    for x in range(5):
        opacity = 1.0 - x * 0.18
        col = tuple(int(c * opacity) for c in C_PRIMARY)
        draw.line([(x, 0), (x, H)], fill=col)

    # -----------------------------------------------------------------------
    # Bottom accent line — 3px
    # -----------------------------------------------------------------------
    for y_off in range(3):
        opacity = 1.0 - y_off * 0.35
        col = tuple(int(c * opacity) for c in C_PRIMARY)
        draw.line([(0, H - 3 + y_off), (W, H - 3 + y_off)], fill=col)

    # -----------------------------------------------------------------------
    # Top-left pill — band label (App 1) or experience level (App 2) or model
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Top-right — "ML-Powered · SalaryScope"
    # -----------------------------------------------------------------------
    brand = "SalaryScope"
    sub   = "ML-Powered · "
    bw    = _tw(draw, brand, fn_brand)
    sw    = _tw(draw, sub,   fn_sub)
    right_x = W - 40
    brand_x = right_x - bw
    sub_x   = brand_x - sw - 4
    # baseline-align: draw sub slightly lower since it's smaller
    brand_y = 28
    sub_y   = brand_y + (_th(draw, brand, fn_brand) - _th(draw, sub, fn_sub)) // 2 + 3
    draw.text((sub_x, sub_y), sub, font=fn_sub, fill=C_MUTED)
    draw.text((brand_x, brand_y), brand, font=fn_brand, fill=C_PRIMARY)

    # -----------------------------------------------------------------------
    # Salary hero — "$" in muted, number in white, baseline-aligned
    # -----------------------------------------------------------------------
    num_text = f"{predicted_usd:,.0f}"
    dol_text = "$"

    num_bb   = _bbox(draw, num_text, fn_num)    # (x0, y0, x1, y1)
    dol_bb   = _bbox(draw, dol_text, fn_dollar)

    # Actual glyph heights (y1 of bbox)
    num_h    = num_bb[3]    # distance from draw origin to bottom of glyph
    dol_h    = dol_bb[3]

    num_w    = num_bb[2] - num_bb[0]
    dol_w    = dol_bb[2] - dol_bb[0]
    gap      = 4

    total_w  = dol_w + gap + num_w

    # Top-of-card section height available before content starts (~80px for pill row)
    # We want the salary hero vertically centred in the upper ~55% of the card
    hero_centre_y = int(H * 0.34)     # 214px from top
    hero_top_y    = hero_centre_y - num_h // 2

    # x positions
    hero_x = (W - total_w) // 2
    num_x  = hero_x + dol_w + gap
    # Baseline-align "$" to number: push dollar down so its glyph bottom matches number glyph bottom
    dol_y  = hero_top_y + (num_h - dol_h)
    num_y  = hero_top_y

    # Shadow — one pixel, dark blue
    shadow = (20, 45, 100)
    for ox, oy in [(2, 2), (1, 2)]:
        draw.text((hero_x  + ox, dol_y + oy), dol_text, font=fn_dollar, fill=shadow)
        draw.text((num_x   + ox, num_y + oy), num_text, font=fn_num,    fill=shadow)

    draw.text((hero_x, dol_y), dol_text, font=fn_dollar, fill=C_MUTED)
    draw.text((num_x,  num_y), num_text, font=fn_num,    fill=C_WHITE)

    # "per year · USD" — sits below actual glyph bottom, not below line height
    per_year_y = num_y + num_bb[3] + 10     # num_bb[3] = actual glyph bottom
    _draw_text_centred(draw, "per year  ·  USD", fn_sub, per_year_y, W, C_MUTED)

    # -----------------------------------------------------------------------
    # Job title — bold, centred, wraps if long
    # -----------------------------------------------------------------------
    title_y = per_year_y + _th(draw, "per year · USD", fn_sub) + 22
    title_lines = _wrap(draw, job_title, fn_title, W - 120)
    for line in title_lines:
        _draw_text_centred(draw, line, fn_title, title_y, W, C_WHITE)
        title_y += _bbox(draw, line, fn_title)[3] + 6

    # -----------------------------------------------------------------------
    # Location — muted, centred
    # -----------------------------------------------------------------------
    loc_y = title_y + 4
    _draw_text_centred(draw, location, fn_loc, loc_y, W, C_MUTED)
    loc_bottom = loc_y + _th(draw, location, fn_loc)

    # -----------------------------------------------------------------------
    # Pills row — career stage / experience level | monthly | hourly
    # -----------------------------------------------------------------------
    pill_gap = 14
    pills    = []

    if career_stage:
        pills.append((career_stage, C_STAGE_FG, C_STAGE_BG, C_STAGE_BD))
    elif experience_lvl:
        pills.append((experience_lvl, C_EXP_FG, C_EXP_BG, C_EXP_BD))

    monthly = predicted_usd / 12
    hourly  = predicted_usd / 2080
    pills.append((f"${monthly:,.0f} / mo", C_PILL_FG, C_PILL_BG, C_PILL_BD))
    pills.append((f"${hourly:,.0f} / hr",  C_PILL_FG, C_PILL_BG, C_PILL_BD))

    # Measure total pill row width
    pill_h      = _th(draw, pills[0][0], fn_pill) + 16    # fixed pill height
    pill_widths = [_tw(draw, p[0], fn_pill) + 34 for p in pills]
    total_pw    = sum(pill_widths) + pill_gap * (len(pills) - 1)

    pill_row_y = loc_bottom + 22
    pill_cx    = (W - total_pw) // 2

    for i, (ptext, fg, bg, bd) in enumerate(pills):
        cx = pill_cx + pill_widths[i] // 2
        cy = pill_row_y + pill_h // 2
        _pill(draw, ptext, fn_pill, cx=cx, cy=cy, fg=fg, bg=bg, border=bd, px=15, py=7)
        pill_cx += pill_widths[i] + pill_gap

    pill_bottom = pill_row_y + pill_h

    # -----------------------------------------------------------------------
    # Divider
    # -----------------------------------------------------------------------
    div_y      = pill_bottom + 20
    div_margin = 60
    draw.line([(div_margin, div_y), (W - div_margin, div_y)], fill=C_DIVIDER, width=1)

    # -----------------------------------------------------------------------
    # Tagline
    # -----------------------------------------------------------------------
    if tagline is None:
        tagline = _tagline(band_label, career_stage, experience_lvl)

    tag_y     = div_y + 18
    tag_lines = _wrap(draw, tagline, fn_tag, W - 200)
    for line in tag_lines:
        _draw_text_centred(draw, line, fn_tag, tag_y, W, C_MUTED)
        tag_y += _th(draw, line, fn_tag) + 5

    # -----------------------------------------------------------------------
    # Footer — three parts, no overlap
    # Left:   "Generated by SalaryScope"
    # Centre: model name (short, clipped)
    # Right:  URL in primary
    # -----------------------------------------------------------------------
    footer_y = H - 42

    left_text  = "Generated by SalaryScope"
    url_text   = "salaryscope-app.streamlit.app"
    left_w     = _tw(draw, left_text, fn_footer)
    url_w      = _tw(draw, url_text,  fn_url)

    draw.text((40, footer_y), left_text, font=fn_footer, fill=C_MUTED)
    draw.text((W - 40 - url_w, footer_y), url_text, font=fn_url, fill=C_PRIMARY)

    # Model name in centre — clip so it never reaches either side
    max_model_w = W - left_w - url_w - 40 - 40 - 80
    model_short = model_name.split("(")[0].strip()   # drop "(Random Forest)" etc.
    while model_short and _tw(draw, model_short, fn_footer) > max_model_w:
        model_short = model_short[:-1].rstrip()
    if model_short != model_name.split("(")[0].strip():
        model_short += "\u2026"
    _draw_text_centred(draw, model_short, fn_footer, footer_y, W, C_DIVIDER)

    # -----------------------------------------------------------------------
    # Serialise
    # -----------------------------------------------------------------------
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
    """
    Generate the salary card and render a Streamlit download button.
    Place this alongside the existing PDF download button.
    """
    import streamlit as st

    png = generate_salary_card(
        predicted_usd  = predicted_usd,
        job_title      = job_title,
        location       = location,
        model_name     = model_name,
        band_label     = band_label,
        career_stage   = career_stage,
        experience_lvl = experience_lvl,
        tagline        = tagline,
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
