"""
app/core/resume_lang.py
-----------------------
Language detection for uploaded resume PDFs.

Used by both resume_analysis_tab.py (main app) and hub_resume_tab.py
(Model Hub). Neither file depends on the other; both import this module
independently.

The module is entirely self-contained. It has no dependency on
resume_analysis.py, hub_resume_engine.py, or any Streamlit state.

Supported languages
-------------------
English, German, French, Spanish, Portuguese.

These were chosen because:
  - They match the countries well-represented in both training datasets
    (USA, UK, Canada, Germany, France, Spain, Portugal, Brazil)
  - Tech professionals in these countries write resumes in these languages
  - Skill terms and job titles are largely English even in non-English resumes,
    so extraction degrades gracefully rather than failing completely

Languages NOT supported (and why)
----------------------------------
  - Hindi/regional Indian languages: Indian tech professionals write
    resumes in English universally for data/software roles
  - CJK (Chinese/Japanese/Korean): requires different tokenisation, not
    represented meaningfully in the training datasets
  - Arabic: right-to-left, not in datasets

Extraction behaviour for non-English resumes
---------------------------------------------
  - Skills: detected via English PhraseMatcher -- works well because
    skill terms (Python, SQL, TensorFlow) appear in English in all languages
  - Job titles: matched via English alias lists -- same reason
  - Experience years: multilingual regex patterns added to the existing
    extractor cover German/French/Spanish/Portuguese phrasing
  - Education level: multilingual patterns added to both EDUCATION_PATTERNS
    (resume_analysis.py) and education.json (hub lexicon)
  - Country: spaCy NER + alias maps work language-independently on place names

Removal
-------
Delete this file and remove the two import lines (one in
resume_analysis_tab.py, one in hub_resume_tab.py). Both tabs continue
to function normally; they just lose the language badge and warning.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported language metadata
# key: ISO 639-1 code
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES: dict[str, dict] = {
    "en": {
        "label":         "English",
        "warning_level": "none",   # green — no action needed
        "note":          None,
    },
    "de": {
        "label":         "German",
        "warning_level": "caution",  # amber
        "note": (
            "German resume detected. Experience years and education level "
            "extraction include German-language patterns. Skill and job title "
            "extraction is English-based — those fields are likely correct "
            "since tech terms appear in English, but please review them."
        ),
    },
    "fr": {
        "label":         "French",
        "warning_level": "caution",
        "note": (
            "French resume detected. Experience years and education level "
            "extraction include French-language patterns. Skill and job title "
            "extraction is English-based — please review those fields."
        ),
    },
    "es": {
        "label":         "Spanish",
        "warning_level": "caution",
        "note": (
            "Spanish resume detected. Experience years and education level "
            "extraction include Spanish-language patterns. Skill and job title "
            "extraction is English-based — please review those fields."
        ),
    },
    "pt": {
        "label":         "Portuguese",
        "warning_level": "caution",
        "note": (
            "Portuguese resume detected. Experience years and education level "
            "extraction include Portuguese-language patterns. Skill and job title "
            "extraction is English-based — please review those fields."
        ),
    },
}

# Languages that are unsupported but common enough to give a specific label
_KNOWN_UNSUPPORTED: dict[str, str] = {
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja":    "Japanese",
    "ko":    "Korean",
    "ar":    "Arabic",
    "hi":    "Hindi",
    "ru":    "Russian",
    "it":    "Italian",
    "nl":    "Dutch",
    "pl":    "Polish",
    "tr":    "Turkish",
}

# Minimum confidence below which we treat detection as unreliable
_MIN_CONFIDENCE = 0.70

# Number of characters to feed to langdetect (more = more accurate, but slower)
_DETECT_CHARS = 800


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_resume_language(text: str) -> dict:
    """
    Detect the primary language of a resume text.

    Parameters
    ----------
    text : str
        Raw or preprocessed resume text. First _DETECT_CHARS characters
        are used for speed. Newlines are collapsed to spaces for better
        sentence-level detection.

    Returns
    -------
    dict with keys:
        code          str   ISO 639-1 code, e.g. "en", "de". "unknown" if
                            detection failed or confidence was too low.
        label         str   Human-readable language name.
        confidence    float Probability from langdetect (0.0-1.0).
                            0.0 if detection failed.
        is_english    bool  True only when code == "en".
        supported     bool  True if code is in SUPPORTED_LANGUAGES.
        warning_level str   "none" | "caution" | "warning".
                            "none"    -> English
                            "caution" -> supported non-English
                            "warning" -> unsupported or unknown
        note          str | None  Warning message for the UI. None for English.
    """
    if not text or not text.strip():
        return _build_result("unknown", "Unknown", 0.0)

    sample = text[:_DETECT_CHARS].replace("\n", " ").strip()

    try:
        from langdetect import detect_langs  # type: ignore
        results = detect_langs(sample)
        if not results:
            return _build_result("unknown", "Unknown", 0.0)

        top = results[0]
        code       = str(top.lang).lower()
        confidence = float(top.prob)

        if confidence < _MIN_CONFIDENCE:
            # Detection is unreliable — treat as unknown to avoid false warnings
            return _build_result("unknown", "Unknown", confidence)

        # Normalise zh variants
        if code.startswith("zh"):
            code = code  # keep as-is for label lookup

        return _build_result(code, _label_for(code), confidence)

    except ImportError:
        logger.info(
            "langdetect is not installed. Language detection is disabled. "
            "Add 'langdetect' to requirements.txt to enable it."
        )
        # Return English default — extraction continues normally
        return _build_result("en", "English", 1.0, _import_missing=True)

    except Exception as exc:
        logger.warning("Language detection failed: %s", exc)
        return _build_result("unknown", "Unknown", 0.0)


def get_extraction_note(lang_result: dict) -> str | None:
    """
    Return the extraction warning note string for UI display,
    or None if the language is English or detection failed without
    producing a useful warning.
    """
    if lang_result.get("is_english"):
        return None
    code = lang_result.get("code", "unknown")
    info = SUPPORTED_LANGUAGES.get(code)
    if info:
        return info["note"]
    # Unsupported language
    label = lang_result.get("label", "Unknown")
    return (
        f"{label} resume detected. The extraction engine is English-based. "
        "Experience years and education level may not be correctly extracted. "
        "Please review all fields carefully before predicting."
    )


# ---------------------------------------------------------------------------
# Streamlit UI helper
# ---------------------------------------------------------------------------

def render_language_badge(lang_result: dict) -> None:
    """
    Render a compact language detection badge in the Streamlit UI.

    Call this inside the extraction quality section of the tab,
    after running extraction. Handles all warning levels.
    """
    import streamlit as st

    code       = lang_result.get("code", "unknown")
    label      = lang_result.get("label", "Unknown")
    confidence = lang_result.get("confidence", 0.0)
    level      = lang_result.get("warning_level", "warning")
    supported  = lang_result.get("supported", False)
    import_missing = lang_result.get("_import_missing", False)

    if import_missing:
        # langdetect not installed -- show nothing, don't alarm the user
        return

    if code == "unknown":
        st.caption(":material/language: Language: could not be determined reliably.")
        return

    conf_str = f"{confidence * 100:.0f}% confidence" if confidence > 0 else ""

    if level == "none":
        # English — show a small green success line, no expander needed
        st.caption(
            f":material/check_circle: Resume language: **English** detected. "
            f"{conf_str}."
        )
        return

    note = get_extraction_note(lang_result)

    if level == "caution":
        st.info(
            f":material/language: Resume language: **{label}** detected "
            f"({conf_str}). {note}",
        )
    else:
        # warning — unsupported language
        st.warning(
            f":material/translate: Resume language: **{label}** detected "
            f"({conf_str}). {note}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _label_for(code: str) -> str:
    info = SUPPORTED_LANGUAGES.get(code)
    if info:
        return info["label"]
    return _KNOWN_UNSUPPORTED.get(code, code.upper())


def _build_result(
    code: str,
    label: str,
    confidence: float,
    _import_missing: bool = False,
) -> dict:
    supported  = code in SUPPORTED_LANGUAGES
    is_english = code == "en"

    if is_english:
        warning_level = "none"
    elif supported:
        warning_level = "caution"
    else:
        warning_level = "warning"

    return {
        "code":           code,
        "label":          label,
        "confidence":     confidence,
        "is_english":     is_english,
        "supported":      supported,
        "warning_level":  warning_level,
        "note":           SUPPORTED_LANGUAGES.get(code, {}).get("note"),
        "_import_missing": _import_missing,
    }
