"""
app/theme.py
============
SalaryScope -- Design Token System  (complete edition)

Architecture: 3-tier token model used by production design systems.

  TIER 1 -- Primitives
    Raw named color values. Never used directly in components.
    Example: BLUE_600 = "#3E7DE0"

  TIER 2 -- Semantic tokens (DEFAULT_* constants)
    Named by role, not appearance. The name stays fixed across themes;
    only the resolved value changes. Code always uses these names.
    Example: DEFAULT_ACCENT_PRIMARY, DEFAULT_SURFACE_RAISED

  TIER 3 -- Theme dicts (DARK_PROFESSIONAL, DARK_MIDNIGHT, LIGHT_CLEAN)
    A full mapping of every semantic name to a primitive for one theme.
    Switching themes = swapping the active dict. Zero component changes.

Runtime
-------
Active theme stored as a theme-id string in st.session_state[THEME_KEY].
get_token("semantic_name") resolves to the active theme's value on every call.
apply_theme(fig) and all HTML helpers read the active theme automatically.

Adding a new theme
------------------
1. Write a new dict following DARK_PROFESSIONAL as a template.
2. Register it in BUILTIN_THEMES and THEME_ORDER.
Done. The panel and all helpers pick it up automatically.

Adding a new semantic token
---------------------------
1. Add DEFAULT_MY_TOKEN = <primitive> in Section 2.
2. Add "my_token": <value> to EVERY theme dict in Section 3.
3. Call get_token("my_token") wherever needed.
Zero other files change.

Section map
-----------
  1. Primitive palette
  2. Semantic token defaults
  3. Theme definitions (Dark Professional, Dark Midnight, Light Clean)
  4. Runtime resolution  (get_active_theme, get_token, get_colorway, ...)
  5. Plotly layout       (apply_theme)
  6. Backward-compat constants  (existing imports keep working)
  7. HTML helpers -- tab prediction cards  (salary, level, stage, score, assoc)
  8. HTML helpers -- utility cards         (util_card, util_result_card)
  9. HTML helpers -- banners and boxes     (info banner, status box, msg box)
 10. HTML helpers -- row elements          (bar_row, info_row, deduction_row)
 11. HTML helpers -- progress bar
 12. Pandas dataframe styler
"""

import streamlit as st

# ===========================================================================
# SECTION 1 -- Primitive palette
# Reference ONLY from theme dicts below. Never use in component code.
# ===========================================================================

# Blue
BLUE_100 = "#EBF0FF"
BLUE_200 = "#BFCFFF"
BLUE_300 = "#93AFFF"
BLUE_400 = "#6EB3FF"
BLUE_500 = "#4F8EF7"
BLUE_600 = "#3E7DE0"
BLUE_700 = "#2F6CD0"
BLUE_800 = "#1E4799"
BLUE_900 = "#0F2A5C"
BLUE_950 = "#071A40"

# Cyan / sky
CYAN_300 = "#67E8F9"
CYAN_400 = "#22D3EE"
CYAN_500 = "#38BDF8"

# Teal / emerald / mint
TEAL_300 = "#6EE7B7"
TEAL_400 = "#34D399"
TEAL_500 = "#22C55E"
TEAL_600 = "#16A34A"

# Violet / purple / pink
BLUSH      = "#F9A8D4"
PINK_500   = "#EC4899"
PINK_600   = "#DB2777"
VIOLET_400 = "#A78BFA"
VIOLET_500 = "#8B5CF6"
VIOLET_600 = "#7C3AED"
INDIGO_500 = "#818CF8"
INDIGO_600 = "#6366F1"
PURPLE_600 = "#C084FC"

# Amber / orange
AMBER_300  = "#FCD34D"
AMBER_400  = "#F59E0B"
AMBER_500  = "#FB923C"
AMBER_600  = "#F97316"
AMBER_700  = "#D97706"
ORANGE_600 = "#EA580C"

# Red
RED_400 = "#F87171"
RED_500 = "#EF4444"
RED_600 = "#DC2626"

# Slate / neutral
SLATE_300 = "#CBD5E1"
SLATE_400 = "#94A3B8"
SLATE_500 = "#6B7585"
SLATE_600 = "#4A5568"
SLATE_700 = "#374151"

# Dark surface scale
DARK_950 = "#0C1118"
DARK_900 = "#0F1923"
DARK_850 = "#111929"
DARK_800 = "#141A22"
DARK_750 = "#1A2230"
DARK_700 = "#1B2230"
DARK_650 = "#1A2535"
DARK_600 = "#1B2535"
DARK_500 = "#283142"
DARK_450 = "#2D3A50"
DARK_400 = "#374151"

# Dark card gradient starts
GRAD_DARK_A = "#1B2A45"    # Dark Professional tab card
GRAD_DARK_B = "#1A1035"    # Dark Midnight tab card

# Dark hover / tooltip
DARK_HOVER = "#1E2A3A"

# Dark banner backgrounds
DBANNER_INFO    = "#1E2D40"
DBANNER_SUCCESS = "#1A2E22"
DBANNER_WARN    = "#2E2510"
DBANNER_ERROR   = "#2E1515"

# Dark status box backgrounds
DSTATUS_INFO    = "#0F1E2D"
DSTATUS_SUCCESS = "#0F2A1A"
DSTATUS_WARN    = "#251E0F"
DSTATUS_ERROR   = "#2A1515"

# Dark gauge backgrounds
DGAUGE_SAFE   = DARK_HOVER
DGAUGE_WARN   = "#2A2215"
DGAUGE_DANGER = "#2A1515"

# Midnight surface scale
MN_950  = "#080D14"
MN_900  = "#0D1520"
MN_800  = "#111C2A"
MN_750  = "#0F1925"
MN_500  = "#1E2D45"
MN_450  = "#253550"
MN_400  = "#2E4060"
MN_HOVER = "#182234"

MNBANNER_INFO    = "#12203A"
MNBANNER_SUCCESS = "#0C2A1E"
MNBANNER_WARN    = "#251808"
MNBANNER_ERROR   = "#2A0F10"

MNSTATUS_INFO    = "#0F1530"
MNSTATUS_SUCCESS = "#0A2018"
MNSTATUS_WARN    = "#1E1208"
MNSTATUS_ERROR   = "#200A0A"

# Light surface scale
LIGHT_50  = "#FAFAFA"
LIGHT_100 = "#F4F6F9"
LIGHT_150 = "#EEF1F6"
LIGHT_200 = "#E2E8F0"
LIGHT_300 = "#CBD5E1"

LIGHT_HOVER = "#F1F5F9"

LBANNER_INFO    = "#EFF6FF"
LBANNER_SUCCESS = "#F0FDF4"
LBANNER_WARN    = "#FFFBEB"
LBANNER_ERROR   = "#FEF2F2"

# Text scales
TDARK_PRIMARY  = "#E6EAF0"
TDARK_MUTED    = "#9CA6B5"
TDARK_FAINT    = "#6B7585"
TDARK_BRIGHT   = "#E5E7EB"
TDARK_BANNER   = "#C8D6E8"

TMID_PRIMARY   = "#DDE6F5"
TMID_MUTED     = "#7A90B0"
TMID_FAINT     = "#4A5E78"
TMID_BANNER    = "#B8CCE8"

TLIGHT_PRIMARY = "#1A202C"
TLIGHT_MUTED   = "#4A5568"
TLIGHT_FAINT   = "#718096"
TLIGHT_BANNER  = "#2D3748"

WHITE = "#FFFFFF"
BLACK = "#000000"
FONT_FAMILY = "Inter, Segoe UI, sans-serif"

# ---------------------------------------------------------------------------
# Violet theme primitives  (blue-violet, NOT pinkish purple)
# Anchor hue: ~250 deg on the colour wheel -- sits right at the blue-violet
# boundary. Think Figma / Linear indigo, not lavender.
# ---------------------------------------------------------------------------

# Violet-tinted dark surfaces -- the violet hue is baked into the base layer
# at low saturation so every surface reads as "violet atmosphere" rather than
# generic dark + violet accent.
VL_950  = "#0C0C1A"    # deepest bg -- almost black with a violet cast
VL_900  = "#10101F"    # slightly lighter
VL_850  = "#141428"    # raised panels
VL_800  = "#18182E"    # cards, chart paper
VL_750  = "#1C1C34"    # sunken areas
VL_700  = "#1E1E36"    # overlays, chart plot, inputs
VL_650  = "#22223C"    # util card top
VL_600  = "#26263F"    # util card end / secondary surfaces
VL_500  = "#2E2E50"    # borders (default)
VL_450  = "#38385C"    # borders (subtle)
VL_400  = "#44446A"    # borders (strong)
VL_HOVER = "#1A1A30"   # hover bg for tooltips

# Violet accent scale  (perceptual blue-violet -- no pink shift)
VIOL_A_300 = "#A5B4FC"   # light / chart fill
VIOL_A_400 = "#818CF8"   # mid -- indigo-violet (INDIGO_500 already exists)
VIOL_A_500 = "#6366F1"   # primary -- INDIGO_600 level
VIOL_A_600 = "#5B5BD6"   # hover -- slightly darker, still blue-leaning
VIOL_A_700 = "#4F46E5"   # deep -- very blue-indigo
VIOL_A_800 = "#3730A3"   # dark / card gradient end

# Violet text
TVIOL_PRIMARY = "#ECEEFF"   # slightly lavender-white, not pure #E6EAF0
TVIOL_MUTED   = "#9B99BE"   # muted with violet tint
TVIOL_FAINT   = "#6B698E"   # faintest text
TVIOL_BANNER  = "#C4C2E8"   # banner body text

# Violet banner backgrounds
VLBANNER_INFO    = "#1A1A38"
VLBANNER_SUCCESS = "#0F2A1A"   # keep green success neutral
VLBANNER_WARN    = "#2A2010"
VLBANNER_ERROR   = "#2A1018"

# Violet status box backgrounds
VLSTATUS_INFO    = "#14143A"
VLSTATUS_SUCCESS = "#0A2018"
VLSTATUS_WARN    = "#251808"
VLSTATUS_ERROR   = "#200A14"

# Violet card gradient start
GRAD_VIOL = "#1A1A42"    # deep indigo-violet gradient top

# ---------------------------------------------------------------------------
# Green theme primitives  (emerald-teal anchor, desaturated cool surfaces)
# Anchor hue: ~160 deg -- emerald, closer to teal than to lime or grass.
# Surfaces are desaturated dark grey-green so the accent can breathe.
# ---------------------------------------------------------------------------

# Green-tinted dark surfaces -- very low saturation, slight warm-cool balance
GN_950  = "#090F0D"    # deepest bg
GN_900  = "#0D1410"    # page base
GN_850  = "#101A14"    # raised
GN_800  = "#141F18"    # cards, chart paper
GN_750  = "#18261C"    # sunken
GN_700  = "#1A2820"    # overlays, chart plot, inputs
GN_650  = "#1E2C24"    # util card top
GN_600  = "#202E26"    # util card end
GN_500  = "#293A30"    # borders (default)
GN_450  = "#324540"    # borders (subtle)
GN_400  = "#3D5048"    # borders (strong)
GN_HOVER = "#18241E"   # tooltip bg

# Emerald accent scale
EMER_300 = "#6EE7B7"   # light / chart highlight  (= TEAL_300)
EMER_400 = "#34D399"   # chart fills               (= TEAL_400)
EMER_500 = "#10B981"   # primary accent
EMER_600 = "#059669"   # hover / deeper
EMER_700 = "#047857"   # dark accent
EMER_800 = "#065F46"   # card gradient end

# Green text
TGN_PRIMARY = "#E4EDEA"   # slightly green-white
TGN_MUTED   = "#8FAF9E"   # muted with green tint
TGN_FAINT   = "#617A6C"   # faintest
TGN_BANNER  = "#BDD8CC"   # banner body text

# Green banner / status backgrounds
GNBANNER_INFO    = "#0F1F2A"   # cool dark teal
GNBANNER_SUCCESS = "#0C2A1A"   # emerald tint
GNBANNER_WARN    = "#2A2010"
GNBANNER_ERROR   = "#2A1010"

GNSTATUS_INFO    = "#0A1E28"
GNSTATUS_SUCCESS = "#082018"
GNSTATUS_WARN    = "#201808"
GNSTATUS_ERROR   = "#200A0A"

GRAD_GN = "#0E2520"    # dark emerald gradient top for tab cards


# ===========================================================================
# SECTION 2 -- Semantic token defaults  (= Dark Professional values)
# ===========================================================================

DEFAULT_SURFACE_BASE    = DARK_950
DEFAULT_SURFACE_RAISED  = DARK_800
DEFAULT_SURFACE_OVERLAY = DARK_700
DEFAULT_SURFACE_SUNKEN  = DARK_750

DEFAULT_BORDER_DEFAULT  = DARK_500
DEFAULT_BORDER_SUBTLE   = DARK_450
DEFAULT_BORDER_STRONG   = DARK_400

DEFAULT_TEXT_PRIMARY    = TDARK_PRIMARY
DEFAULT_TEXT_SECONDARY  = TDARK_MUTED
DEFAULT_TEXT_DISABLED   = TDARK_FAINT
DEFAULT_TEXT_INVERSE    = WHITE
DEFAULT_TEXT_BANNER     = TDARK_BANNER

DEFAULT_ACCENT_PRIMARY  = BLUE_600
DEFAULT_ACCENT_HOVER    = BLUE_700
DEFAULT_ACCENT_BRIGHT   = BLUE_500

DEFAULT_CHART_PAPER     = DARK_800
DEFAULT_CHART_PLOT      = DARK_700
DEFAULT_CHART_HOVER_BG  = DARK_HOVER

DEFAULT_STATUS_SUCCESS  = TEAL_500
DEFAULT_STATUS_WARNING  = AMBER_400
DEFAULT_STATUS_ERROR    = RED_500
DEFAULT_STATUS_INFO     = BLUE_500

DEFAULT_CARD_GRAD_START = GRAD_DARK_A
DEFAULT_CARD_GRAD_END   = DARK_700
DEFAULT_UTIL_CARD_START = DARK_650
DEFAULT_UTIL_CARD_END   = DARK_700
DEFAULT_UTIL_CARD_BORDER = DARK_450

DEFAULT_BANNER_INFO_BG  = DBANNER_INFO
DEFAULT_BANNER_OK_BG    = DBANNER_SUCCESS
DEFAULT_BANNER_WARN_BG  = DBANNER_WARN
DEFAULT_BANNER_ERR_BG   = DBANNER_ERROR

DEFAULT_STATUS_INFO_BG    = DSTATUS_INFO
DEFAULT_STATUS_SUCCESS_BG = DSTATUS_SUCCESS
DEFAULT_STATUS_WARN_BG    = DSTATUS_WARN
DEFAULT_STATUS_ERROR_BG   = DSTATUS_ERROR

DEFAULT_GAUGE_SAFE_BG   = DGAUGE_SAFE
DEFAULT_GAUGE_WARN_BG   = DGAUGE_WARN
DEFAULT_GAUGE_DANGER_BG = DGAUGE_DANGER

DEFAULT_CARD_BAND_BORDER  = INDIGO_500
DEFAULT_CARD_STAGE_BORDER = VIOLET_400
DEFAULT_UTIL_BLUE         = "#3B82F6"
DEFAULT_CI_MARKER         = "#fef6e4"

# Model Hub result card -- flat surface (no gradient), distinct from tab cards.
# hub_card_bg    : background of the card (surface_overlay level)
# hub_card_accent: left border + value text colour (accent_primary level)
DEFAULT_HUB_CARD_BG     = DARK_700   # surface_overlay -- same as COLOR_BG_INPUT
DEFAULT_HUB_CARD_ACCENT = BLUE_500   # bright accent

DEFAULT_COLORWAY = [
    BLUE_500, CYAN_500, TEAL_400, VIOLET_400,
    AMBER_400, AMBER_500, PINK_500, CYAN_400,
]

DEFAULT_COLORWAY_EXTENDED = DEFAULT_COLORWAY + [
    INDIGO_500, TEAL_300, AMBER_300, RED_400
]

DEFAULT_COLORWAY_3_STAGES = [DEFAULT_COLORWAY[1], DEFAULT_COLORWAY[0], DEFAULT_COLORWAY[3]]
DEFAULT_MODEL_COLORS      = [BLUE_400, BLUE_500, "#3366CC", BLUE_800, BLUE_900]
DEFAULT_CONTINUOUS_SCALE  = [[0, BLUE_800], [0.5, BLUE_500], [1.0, CYAN_500]]


# ===========================================================================
# SECTION 3 -- Theme definitions
# Every key = semantic token name (no DEFAULT_ prefix).
# ===========================================================================

DARK_PROFESSIONAL: dict = {
    "id":   "dark_professional",
    "name": "Dark Professional",
    "mode": "dark",

    "surface_base":    DARK_950,
    "surface_raised":  DARK_800,
    "surface_overlay": DARK_700,
    "surface_sunken":  DARK_750,

    "border_default":  DARK_500,
    "border_subtle":   DARK_450,
    "border_strong":   DARK_400,

    "text_primary":    TDARK_PRIMARY,
    "text_secondary":  TDARK_MUTED,
    "text_disabled":   TDARK_FAINT,
    "text_inverse":    WHITE,
    "text_banner":     TDARK_BANNER,

    "accent_primary":  BLUE_600,
    "accent_hover":    BLUE_700,
    "accent_bright":   BLUE_500,

    "chart_paper":     DARK_800,
    "chart_plot":      DARK_700,
    "chart_hover_bg":  DARK_HOVER,

    "status_success":  TEAL_500,
    "status_warning":  AMBER_400,
    "status_error":    RED_500,
    "status_info":     BLUE_500,

    "card_grad_start": GRAD_DARK_A,
    "card_grad_end":   DARK_700,
    "util_card_start": DARK_650,
    "util_card_end":   DARK_700,
    "util_card_border":DARK_450,

    "banner_info_bg":  DBANNER_INFO,
    "banner_ok_bg":    DBANNER_SUCCESS,
    "banner_warn_bg":  DBANNER_WARN,
    "banner_err_bg":   DBANNER_ERROR,

    "status_info_bg":    DSTATUS_INFO,
    "status_success_bg": DSTATUS_SUCCESS,
    "status_warn_bg":    DSTATUS_WARN,
    "status_error_bg":   DSTATUS_ERROR,

    "gauge_safe_bg":   DGAUGE_SAFE,
    "gauge_warn_bg":   DGAUGE_WARN,
    "gauge_danger_bg": DGAUGE_DANGER,

    "card_band_border":  BLUE_400,
    "card_stage_border": INDIGO_500,
    "util_blue":         "#3B82F6",
    "ci_marker":         "#fef6e4",
    "hub_card_bg":       DARK_700,    # flat surface for Model Hub result card
    "hub_card_accent":   BLUE_500,    # left border + value text in hub card

    "colorway": [
        BLUE_500, CYAN_500, TEAL_400, VIOLET_400,
        AMBER_400, AMBER_500, "#F472B6", CYAN_400,
    ],
}


DARK_MIDNIGHT: dict = {
    "id":   "dark_midnight",
    "name": "Dark Midnight",
    "mode": "dark",

    # Surfaces -- deep navy scale, darker and bluer than Dark Professional.
    # MN_* primitives give Midnight its distinct identity: the page feels
    # like deep ocean rather than the neutral charcoal of Dark Professional.
    "surface_base":    MN_950,
    "surface_raised":  MN_900,
    "surface_overlay": MN_800,
    "surface_sunken":  MN_750,

    # Borders -- navy-tinted, matching the surface scale
    "border_default":  MN_500,
    "border_subtle":   MN_450,
    "border_strong":   MN_400,

    # Text -- TMID_* has a slight blue cast that complements the navy surfaces.
    # Still highly legible; contrast ratio equivalent to TDARK_* on DARK_*.
    "text_primary":    TMID_PRIMARY,
    "text_secondary":  TMID_MUTED,
    "text_disabled":   TMID_FAINT,
    "text_inverse":    WHITE,
    "text_banner":     TMID_BANNER,

    # Accent -- violet, weight-for-weight relative to Dark Professional blue:
    #   BLUE_600 -> VIOLET_600   accent_primary
    #   BLUE_700 -> VIOLET_500   accent_hover
    #   BLUE_500 -> VIOLET_400   accent_bright
    "accent_primary":  VIOLET_600,
    "accent_hover":    VIOLET_500,
    "accent_bright":   VIOLET_400,

    # Chart -- Midnight-specific surfaces so charts sit in the same deep navy
    "chart_paper":     MN_900,
    "chart_plot":      MN_800,
    "chart_hover_bg":  MN_HOVER,

    # Status -- identical to Dark Professional (semantic colors are universal)
    "status_success":  TEAL_500,
    "status_warning":  AMBER_400,
    "status_error":    RED_500,
    "status_info":     VIOLET_400,

    # Cards -- GRAD_DARK_B is the dedicated Midnight card gradient top
    # (#1A1035: very deep purple-navy), distinct from DP's #1B2A45.
    "card_grad_start": GRAD_DARK_B,
    "card_grad_end":   MN_800,
    "util_card_start": MN_750,
    "util_card_end":   MN_800,
    "util_card_border":MN_450,

    # Banners -- MNBANNER_* are navy-tinted equivalents of DBANNER_*
    "banner_info_bg":  MNBANNER_INFO,
    "banner_ok_bg":    MNBANNER_SUCCESS,
    "banner_warn_bg":  MNBANNER_WARN,
    "banner_err_bg":   MNBANNER_ERROR,

    # Status boxes -- MNSTATUS_* equivalents of DSTATUS_*
    "status_info_bg":    MNSTATUS_INFO,
    "status_success_bg": MNSTATUS_SUCCESS,
    "status_warn_bg":    MNSTATUS_WARN,
    "status_error_bg":   MNSTATUS_ERROR,

    # Gauge zones -- navy equivalents of DGAUGE_*
    "gauge_safe_bg":   MN_HOVER,
    "gauge_warn_bg":   "#201808",
    "gauge_danger_bg": "#200A0A",

    # Card accent slots -- violet replaces blue at matching weight
    "card_band_border":  VIOLET_400,
    "card_stage_border": VIOLET_500,
    "util_blue":         VIOLET_600,
    "ci_marker":         "#EDE9FE",
    "hub_card_bg":       MN_800,
    "hub_card_accent":   VIOLET_400,

    # Colorway -- 8 perceptually distinct hues, no family repeats.
    # Slot 0: violet (accent), slot 3: INDIGO_500 (blue-indigo, distinct from
    # violet) replaces the plain VIOLET_400 repeat that was there before.
    "colorway": [
        VIOLET_400,    # 0 -- violet       (primary accent)
        CYAN_500,      # 1 -- sky blue
        TEAL_400,      # 2 -- emerald green
        INDIGO_500,    # 3 -- blue-indigo   (distinct from violet at slot 0)
        AMBER_400,     # 4 -- amber
        AMBER_500,     # 5 -- orange
        "#F472B6",     # 6 -- pink
        CYAN_400,      # 7 -- cyan-blue
    ],
}


LIGHT_CLEAN: dict = {
    "id":   "light_clean",
    "name": "Light Clean",
    "mode": "light",

    "surface_base":    LIGHT_50,
    "surface_raised":  WHITE,
    "surface_overlay": LIGHT_100,
    "surface_sunken":  LIGHT_150,

    "border_default":  LIGHT_300,
    "border_subtle":   LIGHT_200,
    "border_strong":   SLATE_600,

    "text_primary":    TLIGHT_PRIMARY,
    "text_secondary":  TLIGHT_MUTED,
    "text_disabled":   TLIGHT_FAINT,
    "text_inverse":    WHITE,
    "text_banner":     TLIGHT_BANNER,

    "accent_primary":  "#2563EB",
    "accent_hover":    "#1D4ED8",
    "accent_bright":   "#3B82F6",

    "chart_paper":     WHITE,
    "chart_plot":      LIGHT_100,
    "chart_hover_bg":  LIGHT_HOVER,

    "status_success":  TEAL_600,
    "status_warning":  AMBER_700,
    "status_error":    RED_600,
    "status_info":     "#2563EB",

    "card_grad_start": LIGHT_150,
    "card_grad_end":   WHITE,
    "util_card_start": LIGHT_100,
    "util_card_end":   WHITE,
    "util_card_border":LIGHT_300,

    "banner_info_bg":  LBANNER_INFO,
    "banner_ok_bg":    LBANNER_SUCCESS,
    "banner_warn_bg":  LBANNER_WARN,
    "banner_err_bg":   LBANNER_ERROR,

    "status_info_bg":    LBANNER_INFO,
    "status_success_bg": LBANNER_SUCCESS,
    "status_warn_bg":    LBANNER_WARN,
    "status_error_bg":   LBANNER_ERROR,

    "gauge_safe_bg":   LBANNER_SUCCESS,
    "gauge_warn_bg":   LBANNER_WARN,
    "gauge_danger_bg": LBANNER_ERROR,

    "card_band_border":  "#4F46E5",
    "card_stage_border": VIOLET_600,
    "util_blue":         "#2563EB",
    "ci_marker":         "#1E3A5F",
    "hub_card_bg":       LIGHT_100,
    "hub_card_accent":   "#2563EB",

    "colorway": [
        "#2563EB", "#0891B2", "#059669", VIOLET_600,
        AMBER_700, ORANGE_600, PINK_600, "#0E7490",
    ],
}


DARK_VIOLET: dict = {
    "id":   "dark_violet",
    "name": "Dark Violet",
    "mode": "dark",

    # Surfaces -- identical to Dark Professional
    "surface_base":    DARK_950,
    "surface_raised":  DARK_800,
    "surface_overlay": DARK_700,
    "surface_sunken":  DARK_750,

    # Borders -- identical to Dark Professional
    "border_default":  DARK_500,
    "border_subtle":   DARK_450,
    "border_strong":   DARK_400,

    # Text -- identical to Dark Professional
    "text_primary":    TDARK_PRIMARY,
    "text_secondary":  TDARK_MUTED,
    "text_disabled":   TDARK_FAINT,
    "text_inverse":    WHITE,
    "text_banner":     TDARK_BANNER,

    # Accent -- violet replaces blue, weight-for-weight:
    #   BLUE_600 -> VIOLET_600   accent_primary
    #   BLUE_700 -> VIOLET_500   accent_hover
    #   BLUE_500 -> VIOLET_400   accent_bright
    "accent_primary":  VIOLET_600,
    "accent_hover":    VIOLET_500,
    "accent_bright":   VIOLET_400,

    # Chart -- identical to Dark Professional
    "chart_paper":     DARK_800,
    "chart_plot":      DARK_700,
    "chart_hover_bg":  DARK_HOVER,

    # Status -- identical to Dark Professional
    "status_success":  TEAL_500,
    "status_warning":  AMBER_400,
    "status_error":    RED_500,
    "status_info":     VIOLET_400,

    # Cards -- identical to Dark Professional
    "card_grad_start": GRAD_DARK_A,
    "card_grad_end":   DARK_700,
    "util_card_start": DARK_650,
    "util_card_end":   DARK_700,
    "util_card_border":DARK_450,

    # Banners -- identical to Dark Professional
    "banner_info_bg":  DBANNER_INFO,
    "banner_ok_bg":    DBANNER_SUCCESS,
    "banner_warn_bg":  DBANNER_WARN,
    "banner_err_bg":   DBANNER_ERROR,

    # Status boxes -- identical to Dark Professional
    "status_info_bg":    DSTATUS_INFO,
    "status_success_bg": DSTATUS_SUCCESS,
    "status_warn_bg":    DSTATUS_WARN,
    "status_error_bg":   DSTATUS_ERROR,

    # Gauge zones -- identical to Dark Professional
    "gauge_safe_bg":   DGAUGE_SAFE,
    "gauge_warn_bg":   DGAUGE_WARN,
    "gauge_danger_bg": DGAUGE_DANGER,

    # Card accent slots -- violet replaces blue at matching weight
    "card_band_border":  VIOLET_400,
    "card_stage_border": VIOLET_500,
    "util_blue":         VIOLET_600,
    "ci_marker":         "#fef6e4",
    "hub_card_bg":       DARK_700,
    "hub_card_accent":   VIOLET_400,

    # Colorway -- only index 0 (BLUE_500) replaced with VIOLET_400
    "colorway": [
        VIOLET_400,    # 0 -- violet  (replaces BLUE_500)
        CYAN_500,      # 1 -- unchanged
        TEAL_400,      # 2 -- unchanged
        VIOLET_400,    # 3 -- unchanged
        AMBER_400,     # 4 -- unchanged
        AMBER_500,     # 5 -- unchanged
        "#F472B6",     # 6 -- unchanged
        CYAN_400,      # 7 -- unchanged
    ],
}


DARK_EMERALD: dict = {
    "id":   "dark_emerald",
    "name": "Dark Emerald",
    "mode": "dark",

    # Surfaces -- identical to Dark Professional
    "surface_base":    DARK_950,
    "surface_raised":  DARK_800,
    "surface_overlay": DARK_700,
    "surface_sunken":  DARK_750,

    # Borders -- identical to Dark Professional
    "border_default":  DARK_500,
    "border_subtle":   DARK_450,
    "border_strong":   DARK_400,

    # Text -- identical to Dark Professional
    "text_primary":    TDARK_PRIMARY,
    "text_secondary":  TDARK_MUTED,
    "text_disabled":   TDARK_FAINT,
    "text_inverse":    WHITE,
    "text_banner":     TDARK_BANNER,

    # Accent -- emerald replaces blue, weight-for-weight:
    #   BLUE_600 -> EMER_500   accent_primary
    #   BLUE_700 -> EMER_600   accent_hover
    #   BLUE_500 -> EMER_400   accent_bright
    "accent_primary":  EMER_500,
    "accent_hover":    EMER_600,
    "accent_bright":   EMER_400,

    # Chart -- identical to Dark Professional
    "chart_paper":     DARK_800,
    "chart_plot":      DARK_700,
    "chart_hover_bg":  DARK_HOVER,

    # Status -- identical to Dark Professional
    "status_success":  TEAL_500,
    "status_warning":  AMBER_400,
    "status_error":    RED_500,
    "status_info":     EMER_400,

    # Cards -- identical to Dark Professional
    "card_grad_start": GRAD_DARK_A,
    "card_grad_end":   DARK_700,
    "util_card_start": DARK_650,
    "util_card_end":   DARK_700,
    "util_card_border":DARK_450,

    # Banners -- identical to Dark Professional
    "banner_info_bg":  DBANNER_INFO,
    "banner_ok_bg":    DBANNER_SUCCESS,
    "banner_warn_bg":  DBANNER_WARN,
    "banner_err_bg":   DBANNER_ERROR,

    # Status boxes -- identical to Dark Professional
    "status_info_bg":    DSTATUS_INFO,
    "status_success_bg": DSTATUS_SUCCESS,
    "status_warn_bg":    DSTATUS_WARN,
    "status_error_bg":   DSTATUS_ERROR,

    # Gauge zones -- identical to Dark Professional
    "gauge_safe_bg":   DGAUGE_SAFE,
    "gauge_warn_bg":   DGAUGE_WARN,
    "gauge_danger_bg": DGAUGE_DANGER,

    # Card accent slots -- emerald replaces blue at matching weight
    "card_band_border":  EMER_400,
    "card_stage_border": EMER_500,
    "util_blue":         EMER_500,
    "ci_marker":         "#fef6e4",
    "hub_card_bg":       DARK_700,
    "hub_card_accent":   EMER_400,

    # Colorway -- only index 0 (BLUE_500) replaced with EMER_400
    "colorway": [
        EMER_400,      # 0 -- emerald  (replaces BLUE_500)
        CYAN_500,      # 1 -- unchanged
        TEAL_400,      # 2 -- unchanged
        VIOLET_400,    # 3 -- unchanged
        AMBER_400,     # 4 -- unchanged
        AMBER_500,     # 5 -- unchanged
        "#F472B6",     # 6 -- unchanged
        CYAN_400,      # 7 -- unchanged
    ],
}


# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------

BUILTIN_THEMES: dict[str, dict] = {
    DARK_PROFESSIONAL["id"]: DARK_PROFESSIONAL,
    DARK_MIDNIGHT["id"]:     DARK_MIDNIGHT,
    DARK_VIOLET["id"]:       DARK_VIOLET,
    DARK_EMERALD["id"]:      DARK_EMERALD,
    LIGHT_CLEAN["id"]:       LIGHT_CLEAN,
}

THEME_ORDER = [
    DARK_PROFESSIONAL["id"],
    DARK_MIDNIGHT["id"],
    DARK_VIOLET["id"],
    DARK_EMERALD["id"],
    LIGHT_CLEAN["id"],
]

DEFAULT_THEME_ID = DARK_PROFESSIONAL["id"]


# ===========================================================================
# SECTION 4 -- Runtime resolution
# ===========================================================================

THEME_KEY = "salaryscope_theme"


def get_active_theme() -> dict:
    """Return the active theme dict, falling back to Dark Professional."""
    stored = st.session_state.get(THEME_KEY)
    if not stored:
        return DARK_PROFESSIONAL
    if isinstance(stored, str):
        return BUILTIN_THEMES.get(stored, DARK_PROFESSIONAL)
    if isinstance(stored, dict):
        return BUILTIN_THEMES.get(stored.get("id", DEFAULT_THEME_ID), DARK_PROFESSIONAL)
    return DARK_PROFESSIONAL


def set_theme(theme_id: str) -> None:
    """Write a theme id into session state. Call st.rerun() after."""
    if theme_id in BUILTIN_THEMES:
        st.session_state[THEME_KEY] = theme_id


def reset_theme() -> None:
    """Remove theme override, reverting to Dark Professional."""
    st.session_state.pop(THEME_KEY, None)


def get_token(name: str, fallback: str = "") -> str:
    """
    Resolve a semantic token from the active theme.

    Usage
    -----
        color  = get_token("accent_primary")
        bg     = get_token("surface_raised")
        border = get_token("border_default", "#283142")
    """
    return get_active_theme().get(name, fallback)


def get_colorway() -> list:
    """Return the active 8-color chart colorway."""
    return get_active_theme().get("colorway", DEFAULT_COLORWAY)


def get_active_colorway() -> list:
    """Alias for get_colorway() -- used by app_resume scenario tab injection."""
    return get_colorway()


def get_colorway_extended() -> list:
    """12-color palette for data insights dashboards."""
    cw = get_colorway()
    extras = [INDIGO_500, TEAL_300, AMBER_300, RED_400]
    return (cw + extras)[:12]


def get_colorway_3_stages() -> list:
    """3-color sequence for career stage / salary level charts."""
    cw = get_colorway()
    return [cw[1], cw[0], cw[3]] if len(cw) >= 4 else DEFAULT_COLORWAY_3_STAGES


def get_continuous_scale() -> list:
    """3-stop continuous color scale for feature importance / SHAP charts."""
    t = get_active_theme()
    return [
        [0,   t.get("accent_hover",  BLUE_800)],
        [0.5, t.get("accent_bright", BLUE_500)],
        [1.0, get_colorway()[1]],
    ]


def get_model_colors() -> list:
    """Sequential model comparison bar colors, accent-aware."""
    return [
        BLUE_400,
        get_token("accent_bright",  BLUE_500),
        get_token("accent_primary", BLUE_600),
        BLUE_800,
        BLUE_900,
    ]


def get_investment_colors() -> list:
    """4-color cycle for investment horizon cards."""
    cw = get_colorway()
    return [
        get_token("status_warning", AMBER_400),
        get_token("util_blue",      "#3B82F6"),
        cw[3] if len(cw) > 3 else VIOLET_400,
        get_token("status_success", TEAL_500),
    ]


def get_gauge_colors() -> dict:
    """
    Return the theme-aware colors used by admin_panel gauge charts.

    Returns a dict with keys:
        safe    -- bar color when metric is healthy (status_success)
        warn    -- bar color when metric is elevated (status_warning)
        danger  -- bar color when metric is critical (status_error)
        primary -- general accent (accent_primary)
        blue    -- first colorway series
        green   -- colorway[2] (teal/emerald)
        amber   -- colorway[4] (amber)
        red     -- status_error
        purple  -- colorway[3] (violet)
        muted   -- text_secondary
        border  -- border_default
        bg      -- chart_paper
        bg_inner-- chart_plot
        step_safe   -- gauge background step: safe zone
        step_warn   -- gauge background step: warning zone
        step_danger -- gauge background step: danger zone

    Usage (admin_panel.py):
        from app.theme import get_gauge_colors
        _G = get_gauge_colors()
        bar_color = _G["safe"] if pct < 50 else _G["warn"] if pct < 80 else _G["danger"]
    """
    t  = get_active_theme()
    cw = t.get("colorway", DEFAULT_COLORWAY)
    return {
        "safe":       t.get("status_success",    TEAL_500),
        "warn":       t.get("status_warning",    AMBER_400),
        "danger":     t.get("status_error",      RED_500),
        "primary":    t.get("accent_primary",    BLUE_600),
        "blue":       cw[0] if cw else BLUE_500,
        "green":      cw[2] if len(cw) > 2 else TEAL_400,
        "amber":      cw[4] if len(cw) > 4 else AMBER_400,
        "red":        t.get("status_error",      RED_500),
        "purple":     cw[3] if len(cw) > 3 else VIOLET_400,
        "muted":      t.get("text_secondary",    TDARK_MUTED),
        "text":       t.get("text_primary",      TDARK_PRIMARY),
        "border":     t.get("border_default",    DARK_500),
        "bg":         t.get("chart_paper",       DARK_800),
        "bg_inner":   t.get("chart_plot",        DARK_700),
        "step_safe":  t.get("gauge_safe_bg",     DGAUGE_SAFE),
        "step_warn":  t.get("gauge_warn_bg",     DGAUGE_WARN),
        "step_danger":t.get("gauge_danger_bg",   DGAUGE_DANGER),
    }


def get_base_layout_dict() -> dict:
    """
    Return the minimal Plotly layout dict (paper/plot bg, font, margin)
    used by admin_panel charts that need manual layout control.
    Equivalent to the old local _BASE dict inside _build_system_plots().

    Usage:
        from app.theme import get_base_layout_dict
        _BASE = get_base_layout_dict()
        fig.update_layout(height=220, **_BASE)
    """
    t = get_active_theme()
    return dict(
        paper_bgcolor=t.get("chart_paper",  DEFAULT_CHART_PAPER),
        plot_bgcolor= t.get("chart_plot",   DEFAULT_CHART_PLOT),
        font=dict(
            color=t.get("text_primary", DEFAULT_TEXT_PRIMARY),
            size=12,
        ),
        margin=dict(l=50, r=20, t=40, b=50),
    )


# ===========================================================================
# SECTION 5 -- Plotly layout builder
# ===========================================================================

def apply_theme(fig, extra: dict = None):
    """
    Apply the active theme to a Plotly figure.

    Always pair with theme=None in st.plotly_chart():
        apply_theme(fig)
        st.plotly_chart(fig, theme=None)

    Parameters
    ----------
    fig   : plotly.graph_objects.Figure
    extra : optional dict merged after the base layout
    """
    t        = get_active_theme()
    cw       = t.get("colorway",       DEFAULT_COLORWAY)
    paper    = t.get("chart_paper",    DEFAULT_CHART_PAPER)
    plot     = t.get("chart_plot",     DEFAULT_CHART_PLOT)
    hover_bg = t.get("chart_hover_bg", DEFAULT_CHART_HOVER_BG)
    border   = t.get("border_default", DEFAULT_BORDER_DEFAULT)
    text     = t.get("text_primary",   DEFAULT_TEXT_PRIMARY)
    muted    = t.get("text_secondary", DEFAULT_TEXT_SECONDARY)

    layout = dict(
        paper_bgcolor=paper,
        plot_bgcolor=plot,
        font=dict(color=text, family=FONT_FAMILY, size=13),
        title=dict(font=dict(color=text, size=16)),
        colorway=cw,
        xaxis=dict(
            gridcolor=border, linecolor=border,
            tickfont=dict(color=muted, size=12),
            title_font=dict(color=muted, size=13),
            zerolinecolor=border, showgrid=True,
        ),
        yaxis=dict(
            gridcolor=border, linecolor=border,
            tickfont=dict(color=muted, size=12),
            title_font=dict(color=muted, size=13),
            zerolinecolor=border, showgrid=True,
        ),
        legend=dict(
            bgcolor=paper, bordercolor=border, borderwidth=1,
            font=dict(color=text, size=12),
        ),
        hoverlabel=dict(
            bgcolor=hover_bg, bordercolor=border,
            font=dict(color=text, size=12),
        ),
        margin=dict(l=60, r=30, t=50, b=60),
    )
    if extra:
        layout.update(extra)
    fig.update_layout(**layout)
    return fig


# ===========================================================================
# SECTION 6 -- Backward-compatible module-level constants
# These hold Dark Professional values for files that import them directly.
# Migrate callers to get_token() over time; these never break old imports.
# ===========================================================================

COLOR_PRIMARY           = BLUE_600
COLOR_PRIMARY_HOVER     = BLUE_700
COLOR_PRIMARY_BRIGHT    = BLUE_500
COLOR_BG_MAIN           = DARK_950
COLOR_BG_CARD           = DARK_800
COLOR_BG_INPUT          = DARK_700
COLOR_BG_GRADIENT_START = GRAD_DARK_A
COLOR_BORDER            = DARK_500
COLOR_TEXT_MAIN         = TDARK_PRIMARY
COLOR_TEXT_MUTED        = TDARK_MUTED
COLOR_TEXT_FAINT        = TDARK_FAINT
COLOR_TEXT_BRIGHT       = TDARK_BRIGHT
COLOR_SUCCESS           = TEAL_500
COLOR_WARNING           = AMBER_400
COLOR_ERROR             = RED_500
COLOR_WHITE             = WHITE
COLOR_HOVER_BG          = DARK_HOVER
COLOR_BAND_BORDER       = INDIGO_500
COLOR_STAGE_BORDER      = VIOLET_400
COLOR_STAGE_VALUE       = VIOLET_400
COLOR_UTIL_CARD_BG_START = DARK_650
COLOR_UTIL_CARD_BORDER  = DARK_450
COLOR_UTIL_BLUE         = "#3B82F6"
COLOR_UTIL_INFO_TEXT    = TDARK_BANNER
COLOR_MSG_INFO_BG       = DBANNER_INFO
COLOR_MSG_SUCCESS_BG    = DBANNER_SUCCESS
COLOR_TINT_WARN         = DBANNER_WARN
COLOR_TINT_DANGER       = DBANNER_ERROR
COLOR_STATUS_SUCCESS_BG = DSTATUS_SUCCESS
COLOR_STATUS_WARN_BG    = DSTATUS_WARN
COLOR_STATUS_DANGER_BG  = DSTATUS_ERROR
COLOR_STATUS_INFO_BG    = DSTATUS_INFO
COLOR_CI_MARKER         = "#fef6e4"
COLOR_ORANGE            = AMBER_600
COLOR_INDIGO            = INDIGO_600
COLOR_PINK              = PINK_500
COLOR_BLUSH             = BLUSH
COLOR_SLATE             = SLATE_400
COLOR_CHART_YELLOW      = AMBER_300
COLOR_CHART_ROSE        = RED_400

COLORWAY                = DEFAULT_COLORWAY
COLORWAY_EXTENDED       = DEFAULT_COLORWAY_EXTENDED
COLORWAY_3_STAGES       = DEFAULT_COLORWAY_3_STAGES
MODEL_COLORS            = DEFAULT_MODEL_COLORS
CONTINUOUS_SCALE_BLUE   = DEFAULT_CONTINUOUS_SCALE
INVESTMENT_HORIZON_COLORS = [AMBER_400, "#3B82F6", VIOLET_400, TEAL_500]

# Expose for Plotly builder (used internally)
DEFAULT_CHART_PAPER    = DARK_800
DEFAULT_CHART_PLOT     = DARK_700
DEFAULT_CHART_HOVER_BG = DARK_HOVER
DEFAULT_BORDER_DEFAULT = DARK_500
DEFAULT_TEXT_PRIMARY   = TDARK_PRIMARY
DEFAULT_TEXT_SECONDARY = TDARK_MUTED


# ===========================================================================
# SECTION 7 -- HTML helpers: tab prediction cards
#
# Used by: manual_prediction_tab.py, resume_analysis_tab.py
#
# Each named card variant corresponds to one visual role. The border color
# and value color differ; the gradient background is shared.
# All values read from the active theme via get_token().
# ===========================================================================

def _tab_card(
    value_str: str,
    label: str,
    border_color: str,
    value_color: str,
) -> str:
    """
    Internal base card builder for all tab prediction cards.
    Gradient: card_grad_start -> card_grad_end
    """
    bg_s = get_token("card_grad_start", COLOR_BG_GRADIENT_START)
    bg_e = get_token("card_grad_end",   COLOR_BG_INPUT)
    lbl  = get_token("text_secondary",  COLOR_TEXT_MUTED)
    return (
        f"<div style='background:linear-gradient(135deg,{bg_s} 0%,{bg_e} 100%);"
        f"border:1px solid {border_color};border-left:5px solid {border_color};"
        f"border-radius:10px;padding:24px 32px;text-align:center;margin:8px auto;'>"
        f"<div style='color:{lbl};font-size:13px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:8px;'>{label}</div>"
        f"<div style='color:{value_color};font-size:42px;"
        f"font-weight:700;letter-spacing:-1px;'>{value_str}</div>"
        f"</div>"
    )


def salary_card_html(value_str: str, label: str = "ANNUAL SALARY (USD)") -> str:
    """
    Primary salary prediction result card.
    Border = accent_primary. Value = accent_bright.

    Usage (replaces the hardcoded inline style in manual/resume tabs):
        st.markdown(salary_card_html(f"${prediction:,.2f}"), unsafe_allow_html=True)
    """
    border = get_token("accent_primary", COLOR_PRIMARY)
    value  = get_token("accent_bright",  COLOR_PRIMARY_BRIGHT)
    return _tab_card(value_str, label, border, value)


def salary_level_card_html(value_str: str, label: str = "CAREER SALARY LEVEL") -> str:
    """
    Salary level / band card (Early Career / Professional / Executive Range).
    Border = card_band_border (indigo). Value = accent_bright.

    Usage:
        st.markdown(salary_level_card_html(salary_band_label), unsafe_allow_html=True)
    """
    border = get_token("card_band_border", COLOR_BAND_BORDER)
    value  = get_token("accent_bright",    COLOR_PRIMARY_BRIGHT)
    return _tab_card(value_str, label, border, value)


def career_stage_card_html(
    value_str: str, label: str = "CAREER STAGE (PROGRESSION SEGMENT)"
) -> str:
    """
    Career stage card (Entry / Growth / Leadership Stage).
    Border = card_stage_border (violet). Value = card_stage_border.

    Usage:
        st.markdown(career_stage_card_html(career_stage_label), unsafe_allow_html=True)
    """
    border = get_token("card_stage_border", COLOR_STAGE_BORDER)
    return _tab_card(value_str, label, border, border)


def resume_score_card_html(
    value_str: str,
    level_str: str = "",
    label: str = "RESUME SCORE",
) -> str:
    """
    Resume profile score card.
    Border = colorway[2] (green / teal). Value = same green.
    Shows an optional level label below the score.

    Usage:
        st.markdown(
            resume_score_card_html(
                f"{score['total_score']}/100",
                level_str=score['level'] + ' Profile',
            ),
            unsafe_allow_html=True,
        )
    """
    cw     = get_colorway()
    color  = cw[2] if len(cw) > 2 else TEAL_400
    bg_s   = get_token("card_grad_start", COLOR_BG_GRADIENT_START)
    bg_e   = get_token("card_grad_end",   COLOR_BG_INPUT)
    lbl    = get_token("text_secondary",  COLOR_TEXT_MUTED)
    txt    = get_token("text_primary",    COLOR_TEXT_MAIN)
    level_html = (
        f"<div style='color:{txt};font-size:16px;margin-top:8px;'>{level_str}</div>"
        if level_str else ""
    )
    return (
        f"<div style='background:linear-gradient(135deg,{bg_s} 0%,{bg_e} 100%);"
        f"border:1px solid {color};border-left:5px solid {color};"
        f"border-radius:10px;padding:24px 32px;text-align:center;margin:8px auto;'>"
        f"<div style='color:{lbl};font-size:13px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:8px;'>{label}</div>"
        f"<div style='color:{color};font-size:42px;font-weight:700;"
        f"letter-spacing:-1px;'>{value_str}</div>"
        f"{level_html}"
        f"</div>"
    )


def association_insight_card_html(text: str) -> str:
    """
    Association rule insight card.
    Border = status_warning (amber). Text = text_primary (bright).
    This card uses left-aligned paragraph text, not a centered value.

    Usage:
        st.markdown(association_insight_card_html(assoc_text), unsafe_allow_html=True)
    """
    border = get_token("status_warning", COLOR_WARNING)
    bg_s   = get_token("card_grad_start", COLOR_BG_GRADIENT_START)
    bg_e   = get_token("card_grad_end",   COLOR_BG_INPUT)
    txt    = get_token("text_primary",    COLOR_TEXT_MAIN)
    return (
        f"<div style='background:linear-gradient(135deg,{bg_s} 0%,{bg_e} 100%);"
        f"border:1px solid {border};border-left:5px solid {border};"
        f"border-radius:10px;padding:24px 32px;margin:8px auto;'>"
        f"<div style='color:{txt};font-size:18px;font-weight:500;"
        f"line-height:1.4;'>{text}</div>"
        f"</div>"
    )


# Generic tab card for any other custom use
def tab_result_card_html(
    value_str: str,
    label: str,
    color: str = None,
    value_color: str = None,
) -> str:
    """
    Generic prediction result card with custom colors.
    Use the named variants above when possible.
    """
    if color is None:
        color = get_token("accent_primary", COLOR_PRIMARY)
    if value_color is None:
        value_color = get_token("accent_bright", COLOR_PRIMARY_BRIGHT)
    return _tab_card(value_str, label, color, value_color)


def hub_result_card_html(value_str: str, label: str) -> str:
    """
    Model Hub prediction result card.

    Intentionally different from the salary/resume tab cards:
      - Flat surface background (hub_card_bg token) -- no gradient
      - Smaller 32px value (vs 42px on tab cards)
      - Uppercase label via CSS text-transform
      - Left border + value colour from hub_card_accent token

    These two dedicated tokens (hub_card_bg, hub_card_accent) let the user
    fine-tune the Model Hub card independently of the prediction tab cards
    via the Appearance panel.

    Usage (model_hub_tab.py _display_result):
        from app.theme import hub_result_card_html
        st.markdown(hub_result_card_html(formatted, target), unsafe_allow_html=True)
    """
    bg     = get_token("hub_card_bg",     COLOR_BG_INPUT)
    accent = get_token("hub_card_accent",  COLOR_PRIMARY_BRIGHT)
    border = get_token("border_default",   COLOR_BORDER)
    muted  = get_token("text_secondary",   COLOR_TEXT_MUTED)
    return (
        f"<div style='background:{bg};border:1px solid {border};"
        f"border-left:5px solid {accent};border-radius:10px;"
        f"padding:20px 24px;margin:8px 0;'>"
        f"<div style='color:{muted};font-size:11px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:6px;text-transform:uppercase;'>{label}</div>"
        f"<div style='color:{accent};font-size:32px;font-weight:700;"
        f"letter-spacing:-0.5px;'>{value_str}</div>"
        f"</div>"
    )


# ===========================================================================
# SECTION 8 -- HTML helpers: utility cards
#
# Used by: currency_utils, tax_utils, takehome_utils, col_utils,
#          ctc_utils, budget_utils, savings_utils, loan_utils,
#          investment_utils, emergency_fund_utils, lifestyle_utils,
#          model_hub_tab
#
# Gradient: util_card_start -> util_card_end  (distinct from tab card gradient)
# ===========================================================================

def util_card_html(value_str: str, label: str, color: str = None) -> str:
    """
    Standard utility result card (28px value).
    Default color = accent_primary.

    Usage:
        st.markdown(util_card_html(_loc(savings), "MONTHLY SAVINGS (USD)"),
                    unsafe_allow_html=True)
        st.markdown(util_card_html(_loc(savings), "MONTHLY SAVINGS (USD)",
                    color=get_token("status_success")),
                    unsafe_allow_html=True)
    """
    if color is None:
        color = get_token("accent_primary", COLOR_PRIMARY)
    bg_s = get_token("util_card_start",  COLOR_UTIL_CARD_BG_START)
    bg_e = get_token("util_card_end",    COLOR_BG_INPUT)
    bdr  = get_token("util_card_border", COLOR_UTIL_CARD_BORDER)
    lbl  = get_token("text_secondary",   COLOR_TEXT_MUTED)
    return (
        f"<div style='background:linear-gradient(135deg,{bg_s} 0%,{bg_e} 100%);"
        f"border:1px solid {bdr};border-left:5px solid {color};"
        f"border-radius:10px;padding:16px 20px;text-align:center;margin:6px 0;'>"
        f"<div style='color:{lbl};font-size:11px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:4px;'>{label}</div>"
        f"<div style='color:{color};font-size:28px;font-weight:700;"
        f"letter-spacing:-0.5px;'>{value_str}</div>"
        f"</div>"
    )


def util_result_card_html(
    value_str: str,
    label: str,
    footer: str = "",
    color: str = None,
) -> str:
    """
    Larger result card (34px value) for primary utility outputs.
    Used by tax_utils (net salary), currency_utils (converted amount), etc.
    Includes optional footer line (e.g. exchange rate note).

    Usage:
        st.markdown(
            util_result_card_html(
                f"${net_annual:,.2f}",
                "ESTIMATED NET ANNUAL SALARY (USD, POST-TAX)",
                footer=f"After est. {pct:.1f}% effective tax",
                color=get_token("status_warning"),
            ),
            unsafe_allow_html=True,
        )
    """
    if color is None:
        color = get_token("accent_primary", COLOR_PRIMARY)
    bg_s = get_token("util_card_start",  COLOR_UTIL_CARD_BG_START)
    bg_e = get_token("util_card_end",    COLOR_BG_INPUT)
    bdr  = get_token("util_card_border", COLOR_UTIL_CARD_BORDER)
    lbl  = get_token("text_secondary",   COLOR_TEXT_MUTED)
    ftr  = get_token("text_disabled",    COLOR_TEXT_FAINT)
    ftr_html = (
        f"<div style='color:{ftr};font-size:12px;margin-top:6px;'>{footer}</div>"
        if footer else ""
    )
    return (
        f"<div style='background:linear-gradient(135deg,{bg_s} 0%,{bg_e} 100%);"
        f"border:1px solid {bdr};border-left:5px solid {color};"
        f"border-radius:10px;padding:18px 24px;text-align:center;margin:8px auto;'>"
        f"<div style='color:{lbl};font-size:12px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:6px;'>{label}</div>"
        f"<div style='color:{color};font-size:34px;font-weight:700;"
        f"letter-spacing:-1px;'>{value_str}</div>"
        f"{ftr_html}"
        f"</div>"
    )


# ===========================================================================
# SECTION 9 -- HTML helpers: banners and status boxes
# ===========================================================================

def util_info_banner_html(body: str, border_color: str = None) -> str:
    """
    Standard info banner used by all financial utility files.
    Background = banner_info_bg. Default border = util_blue.

    Usage:
        st.markdown(
            util_info_banner_html(
                f"<b>Country:</b> {name}<br>"
                f"<span style='color:{muted}'>Default rate:</span> <b>8.5%</b>",
                border_color=get_token("accent_primary"),
            ),
            unsafe_allow_html=True,
        )
    """
    if border_color is None:
        border_color = get_token("util_blue", COLOR_UTIL_BLUE)
    bg   = get_token("banner_info_bg", COLOR_MSG_INFO_BG)
    text = get_token("text_banner",    COLOR_UTIL_INFO_TEXT)
    return (
        f"<div style='background:{bg};border-left:4px solid {border_color};"
        f"border-radius:6px;padding:12px 16px;margin:6px 0;"
        f"font-size:13px;color:{text};'>{body}</div>"
    )


def util_status_box_html(
    message: str,
    color: str = None,
    bg: str = None,
) -> str:
    """
    Styled eligibility / status message box.
    Used by loan_utils, emergency_fund_utils -- replaces their private _status_box().

    Usage:
        # Success state
        st.markdown(
            util_status_box_html(
                "Fund target reached.",
                color=get_token("status_success"),
                bg=get_token("status_success_bg"),
            ),
            unsafe_allow_html=True,
        )
        # Warning state
        st.markdown(
            util_status_box_html(
                "Limited loan capacity.",
                color=get_token("status_warning"),
                bg=get_token("status_warn_bg"),
            ),
            unsafe_allow_html=True,
        )
    """
    if color is None:
        color = get_token("accent_primary", COLOR_PRIMARY)
    if bg is None:
        bg = get_token("status_info_bg", COLOR_STATUS_INFO_BG)
    text = get_token("text_banner", COLOR_UTIL_INFO_TEXT)
    return (
        f"<div style='background:{bg};border-left:4px solid {color};"
        f"border-radius:6px;padding:12px 16px;margin:6px 0;"
        f"font-size:13px;color:{text};'>{message}</div>"
    )


def col_ppp_card_html(
    value_str: str,
    label: str,
    footer: str = "",
    color: str = None,
) -> str:
    """
    PPP-equivalent salary card used by col_utils.
    Color is passed dynamically (green/red/muted based on adjustment direction).
    Falls back to accent_primary.

    Usage:
        color = (get_token("status_success") if adj < 1
                 else get_token("status_error") if adj > 1
                 else get_token("text_secondary"))
        st.markdown(col_ppp_card_html(f"${ppp:,.2f}", label, footer, color),
                    unsafe_allow_html=True)
    """
    return util_result_card_html(value_str, label, footer=footer, color=color)


# ===========================================================================
# SECTION 10 -- HTML helpers: row elements
#
# Bar rows, info rows, and deduction rows used in utility files and CTC.
# All read theme tokens so they adapt automatically.
# ===========================================================================

def bar_row_html(
    label: str,
    amount_str: str,
    pct: float,
    color: str,
    width_scale: float = 1.8,
) -> str:
    """
    Horizontal mini-bar row. Used by budget_utils, lifestyle_utils, ctc_utils.

    Parameters
    ----------
    label        : category label (e.g. "Food & Groceries")
    amount_str   : formatted value string (e.g. "$450")
    pct          : percentage value (0-100)
    color        : bar fill color (category-specific, passed by caller)
    width_scale  : bar pixel width = max(4, int(pct * width_scale))

    Usage:
        html = ""
        for cat in result["categories"]:
            html += bar_row_html(
                cat["label"],
                _loc(cat["amount_usd"]),
                cat["fraction"] * 100,
                cat["color"],
            )
        st.markdown(html, unsafe_allow_html=True)
    """
    lbl_c = get_token("text_secondary", COLOR_TEXT_MUTED)
    val_c = get_token("text_primary",   COLOR_TEXT_MAIN)
    bar_w = max(4, int(pct * width_scale))
    return (
        f"<div style='margin:5px 0;display:flex;align-items:center;gap:8px;'>"
        f"<span style='width:160px;color:{lbl_c};font-size:13px;"
        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
        f"{label}</span>"
        f"<span style='display:inline-block;background:{color};"
        f"width:{bar_w}px;height:12px;border-radius:3px;'></span>"
        f"<span style='color:{val_c};font-size:13px;'>"
        f"{amount_str} ({pct:.1f}%)</span>"
        f"</div>"
    )


def info_row_html(label: str, value: str, separator: str = "subtle") -> str:
    """
    Key-value row with bottom border separator. Used by loan_utils,
    emergency_fund_utils, investment_utils, lifestyle_utils.

    Parameters
    ----------
    label     : row label (left, muted)
    value     : row value (right, primary)
    separator : "subtle" uses border_subtle, "default" uses border_default

    Usage:
        for row_label, row_value in rows:
            st.markdown(info_row_html(row_label, row_value), unsafe_allow_html=True)
    """
    lbl_c = get_token("text_secondary", COLOR_TEXT_MUTED)
    val_c = get_token("text_primary",   COLOR_TEXT_MAIN)
    bdr   = (get_token("border_subtle",  COLOR_UTIL_CARD_BORDER)
             if separator == "subtle"
             else get_token("border_default", COLOR_BORDER))
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:6px 0;border-bottom:1px solid {bdr};font-size:13px;'>"
        f"<span style='color:{lbl_c};'>{label}</span>"
        f"<span style='color:{val_c};font-weight:600;'>{value}</span>"
        f"</div>"
    )


def deduction_row_html(
    label: str,
    amount_str: str,
    rate_str: str = "",
    color: str = None,
) -> str:
    """
    Deduction breakdown row. Used by takehome_utils.
    Default color = status_error (red -- deductions are costs).

    Usage:
        for label, amount in result["deduction_breakdown"]:
            pct = amount / gross * 100
            st.markdown(
                deduction_row_html(label, _loc(amount), f"({pct:.1f}%)"),
                unsafe_allow_html=True,
            )
    """
    if color is None:
        color = get_token("status_error", COLOR_ERROR)
    lbl_c = get_token("text_secondary", COLOR_TEXT_MUTED)
    bdr   = get_token("border_default", COLOR_BORDER)
    rate_span = (
        f"<span style='color:{lbl_c};font-size:12px;margin-left:4px;'>{rate_str}</span>"
        if rate_str else ""
    )
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:5px 0;border-bottom:1px solid {bdr};'>"
        f"<span style='color:{lbl_c};font-size:13px;'>{label}</span>"
        f"<span style='color:{color};font-size:13px;'>{amount_str}{rate_span}</span>"
        f"</div>"
    )


def deduction_total_row_html(label: str, value_str: str) -> str:
    """
    Total deductions footer row. Solid top border, red value.
    Used at the bottom of the takehome deduction breakdown.
    """
    accent = get_token("accent_primary", COLOR_PRIMARY)
    err    = get_token("status_error",   COLOR_ERROR)
    lbl_c  = get_token("text_primary",  COLOR_TEXT_MAIN)
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:6px 0;margin-top:2px;'>"
        f"<span style='color:{lbl_c};font-size:13px;font-weight:600;'>{label}</span>"
        f"<span style='color:{err};font-size:13px;font-weight:600;'>{value_str}</span>"
        f"</div>"
    )


def net_takehome_row_html(label: str, value_str: str) -> str:
    """
    Net take-home footer row with accent top border. Green value.
    Used at the very bottom of the takehome breakdown section.
    """
    accent  = get_token("accent_primary",  COLOR_PRIMARY)
    success = get_token("status_success",  COLOR_SUCCESS)
    txt     = get_token("text_primary",    COLOR_TEXT_MAIN)
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"padding:7px 0;border-top:2px solid {accent};margin-top:2px;'>"
        f"<span style='color:{txt};font-size:14px;font-weight:700;'>{label}</span>"
        f"<span style='color:{success};font-size:14px;font-weight:700;'>{value_str}</span>"
        f"</div>"
    )


def ctc_component_row_html(label: str, amount_str: str, pct_str: str, color: str) -> str:
    """
    CTC component bar row. Used by ctc_utils component breakdown.

    Usage:
        for label, val, color in components:
            pct = val / gross * 100
            st.markdown(
                ctc_component_row_html(label, _loc(val), f"{pct:.1f}%", color),
                unsafe_allow_html=True,
            )
    """
    lbl_c = get_token("text_secondary", COLOR_TEXT_MUTED)
    val_c = get_token("text_primary",   COLOR_TEXT_MAIN)
    bar_w = max(4, int(float(pct_str.replace("%", "")) * 5))
    return (
        f"<div style='display:flex;align-items:center;margin:3px 0;'>"
        f"<span style='width:200px;color:{lbl_c};font-size:13px;"
        f"flex-shrink:0;'>{label}</span>"
        f"<span style='display:inline-block;background:{color};"
        f"width:{bar_w}px;height:13px;border-radius:3px;"
        f"margin-right:10px;flex-shrink:0;'></span>"
        f"<span style='color:{val_c};font-size:13px;'>"
        f"{amount_str} ({pct_str})</span>"
        f"</div>"
    )


def lifestyle_tier_row_html(
    label: str,
    color: str,
    spend_str: str,
    savings_str: str,
    is_active: bool = False,
) -> str:
    """
    Lifestyle tier comparison row. Used by lifestyle_utils tier comparison table.
    """
    lbl_c  = get_token("text_secondary", COLOR_TEXT_MUTED)
    val_c  = get_token("text_primary",   COLOR_TEXT_MAIN)
    bdr    = get_token("border_subtle",  COLOR_UTIL_CARD_BORDER)
    marker = " (selected)" if is_active else ""
    return (
        f"<div style='display:flex;justify-content:space-between;"
        f"align-items:center;padding:8px 0;"
        f"border-bottom:1px solid {bdr};font-size:13px;'>"
        f"<span style='color:{color};font-weight:600;width:130px;'>"
        f"{label}{marker}</span>"
        f"<span style='color:{lbl_c};'>Lifestyle: "
        f"<b style='color:{val_c};'>{spend_str}/mo</b></span>"
        f"<span style='color:{lbl_c};'>Saved: "
        f"<b style='color:{color};'>{savings_str}/mo</b></span>"
        f"</div>"
    )


# ===========================================================================
# SECTION 11 -- HTML helpers: progress bar
#
# Used by emergency_fund_utils, and anywhere a progress bar
# is shown in an HTML context (not st.progress).
# ===========================================================================

def progress_bar_html(
    pct_filled: int,
    label: str = "",
    color: str = None,
) -> str:
    """
    Themed HTML progress bar.

    Parameters
    ----------
    pct_filled : integer 0-100
    label      : optional text shown above the bar (e.g. "Fund progress: 45% of 4-month target")
    color      : fill color -- if None, derives from pct_filled:
                   >= 100 -> status_success
                   >= 50  -> status_warning
                   < 50   -> accent_primary

    Usage:
        pct = min(int(result["pct_funded"] * 100), 100)
        st.markdown(
            progress_bar_html(pct, f"Fund progress: {pct}% of {months}-month target"),
            unsafe_allow_html=True,
        )
    """
    pct_filled = max(0, min(100, int(pct_filled)))

    if color is None:
        if pct_filled >= 100:
            color = get_token("status_success", COLOR_SUCCESS)
        elif pct_filled >= 50:
            color = get_token("status_warning", COLOR_WARNING)
        else:
            color = get_token("accent_primary", COLOR_PRIMARY)

    track = get_token("border_subtle", COLOR_UTIL_CARD_BORDER)
    lbl_c = get_token("text_secondary", COLOR_TEXT_MUTED)
    label_html = (
        f"<div style='font-size:13px;color:{lbl_c};margin-bottom:4px;'>{label}</div>"
        if label else ""
    )
    return (
        f"<div style='margin:8px 0;'>"
        f"{label_html}"
        f"<div style='background:{track};border-radius:6px;height:14px;width:100%;'>"
        f"<div style='background:{color};width:{pct_filled}%;height:14px;"
        f"border-radius:6px;transition:width 0.3s ease;'></div>"
        f"</div>"
        f"</div>"
    )


# ===========================================================================
# SECTION 12 -- Pandas dataframe styler
#
# Used by: data_insights_tab (stats tables), model_analytics_tab (comparison
# table row highlight), admin_panel (feedback tables).
# ===========================================================================

def dataframe_style_props() -> dict:
    """
    Return a dict of CSS properties for st.dataframe .set_properties().
    Reads surface_raised, text_primary, border_default from active theme.

    Usage:
        st.dataframe(
            df.style
                .format("{:,.2f}")
                .set_properties(**dataframe_style_props()),
            width='stretch',
        )
    """
    return {
        "background-color": get_token("surface_raised",  COLOR_BG_CARD),
        "color":            get_token("text_primary",    COLOR_TEXT_MAIN),
        "border-color":     get_token("border_default",  COLOR_BORDER),
    }


def dataframe_highlight_row_style(selected_text: str = "") -> str:
    """
    Return a CSS background-color string for the selected/best-model row
    highlight in model comparison tables. Uses chart_hover_bg token.

    Usage (in a pandas Styler apply function):
        def highlight(row):
            if selected_text in row["Model"]:
                return [f"background-color: {dataframe_highlight_row_style()}"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(highlight, axis=1)
        st.dataframe(styled)
    """
    return get_token("chart_hover_bg", COLOR_HOVER_BG)


def rule_divider_html() -> str:
    """
    Thin themed divider line. Used by data_insights_tab between dashboard sections.

    Usage:
        st.markdown(rule_divider_html(), unsafe_allow_html=True)
    """
    bdr = get_token("border_default", COLOR_BORDER)
    return (
        f"<hr style='border:none;border-top:1px solid {bdr};"
        f"margin:4px 0 10px 0;opacity:0.7;'>"
    )