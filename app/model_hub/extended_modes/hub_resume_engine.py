"""
hub_resume_engine.py
====================
Data-driven resume feature extraction engine for Model Hub bundles.

Design principles
-----------------
1. ALL lexicon data lives in JSON files under lexicons/.
   No skill lists, country maps, or patterns are hardcoded here.
   To extend extraction, edit the JSON files only.

2. The engine is schema-driven.  It does not know about App 1 or App 2.
   It receives a list of schema field definitions and returns one extracted
   value per field, using the extractor selected by field name heuristics
   or by an explicit "extractor" key in the schema field descriptor.

3. spaCy and pdfplumber are lazy-loaded and guarded.  The engine degrades
   gracefully if either is absent (e.g. lite deployment).

4. Every extractor returns an ExtractionResult namedtuple so callers always
   know whether the value was found or is a fallback, and why.

5. The engine is stateless -- it builds all matchers once (cached via
   functools.lru_cache) and holds no mutable state.

Per-bundle resume_config.json (new)
------------------------------------
A model bundle can include an optional resume_config.json sidecar file.
When present, loader.py loads it into ModelBundle.resume_config and
hub_resume_tab.py passes it into extract_all_fields().

resume_config.json is a selective override -- every key is optional.
Missing keys fall back to the engine built-in defaults so existing bundles
without the file continue to work identically.

Supported top-level keys in resume_config.json:

  scoring (dict):
      experience_max   (number) -- max points for experience (default 40)
      education_max    (number) -- max points for education  (default 30)
      skills_max       (number) -- max points for skills     (default 30)
      skills_per_point (number) -- multiplier per skill      (default 3)
      thresholds (dict):
          Override experience scoring bands.  Each key is a band name
          (arbitrary string); each value is {max, score, note}.
          Bands are sorted by 'max' ascending at runtime.
          Example:
              "thresholds": {
                  "entry":  {"max": 2,   "score": 10, "note": "Entry level"},
                  "mid":    {"max": 5,   "score": 25, "note": "Mid level"},
                  "senior": {"max": 999, "score": 40, "note": "Senior level"}
              }
      edu_map (dict):
          Override education level scoring.  Keys are string level ints.
          Example: {"0": [5, "High school"], "1": [15, "Bachelor"]}

  extractors (dict):
      Per-extractor override configs.  Supported extractor ids:
        experience:
            patterns          (list of regex strings) -- replaces built-in patterns
            max_years         (number)                -- upper bound (default 50)
        senior_flag:
            keywords          (list of strings)       -- replaces built-in list
            experience_threshold (number)             -- auto-senior threshold (default 6)
        remote_ratio:
            remote_keywords   (list of strings)       -- replaces built-in list
            hybrid_keywords   (list of strings)       -- replaces built-in list
            onsite_keywords   (list of strings)       -- replaces built-in list
        employment_type:
            part_time_keywords (list of strings)      -- replaces built-in detection
            freelance_keywords (list of strings)
            contract_keywords  (list of strings)
        age:
            min_age           (int)                   -- default 16
            max_age           (int)                   -- default 80
        job_title:
            keyword_fallback  (list of [[keywords], title] pairs)

  field_name_mapping (list):
      Extra [keyword_string, extractor_id_string] pairs injected at the
      front of the field-name-to-extractor lookup table.  These take priority
      over built-in defaults.  Example:
          "field_name_mapping": [
              ["years_exp", "experience"],
              ["tech_stack", "skills_list"]
          ]

  preprocessing (dict):
      strip_urls       (bool, default true)  -- remove http/www URLs
      max_text_length  (int,  default 0)     -- truncate text if > 0

Schema field extension hook
---------------------------
A schema field can carry an optional "extractor" key that overrides the
automatic selection:

    {
        "name": "experience_years",
        "type": "float",
        "ui": "slider",
        "extractor": "experience"   <-- override
    }

Supported extractor identifiers:
    experience      numeric years of experience (float)
    education       education level integer 0-3
    country_name    country display name (e.g. "USA", "India")
    country_iso     ISO-2 code (e.g. "US", "IN")
    senior_flag     seniority integer 0 or 1
    job_title       job title string
    employment_type FT / PT / CT / FL string
    remote_ratio    0 / 50 / 100 integer
    skills_list     list of skill strings
    skills_str      comma-separated skills string

Lexicon files (all under lexicons/ next to this file)
------------------------------------------------------
    skills.json      -- skills by category
    job_titles.json  -- canonical title -> alias list
    education.json   -- level -> regex patterns
    countries.json   -- alias -> display name / iso code

Extending extractors
--------------------
To add a new extractor:
1. Implement a function _extract_yourname(text, field, context) -> ExtractionResult
2. Register it in _EXTRACTOR_REGISTRY at the bottom of this file.
3. Optionally add a keyword in _FIELD_NAME_TO_EXTRACTOR for auto-selection.
No other file needs changing.

Removal
-------
Deleting this file removes all hub resume extraction.  hub_resume_tab.py
catches the ImportError and shows a graceful warning.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_LEXICON_DIR = os.path.join(os.path.dirname(__file__), "lexicons")


def _lexicon_path(filename: str) -> str:
    return os.path.join(_LEXICON_DIR, filename)


# ---------------------------------------------------------------------------
# ExtractionResult -- returned by every extractor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractionResult:
    """
    Container returned by every individual extractor function.

    Attributes
    ----------
    value        : The extracted value.  Type depends on the extractor.
    found        : True if a real match was found, False if this is a fallback.
    source       : Short string describing how the value was obtained.
    raw          : Optional raw matched string before normalisation.
    extractor_id : The registered extractor identifier that ran (e.g. "experience",
                   "education", "country_iso"). Used by _compute_score to derive
                   score contributions without depending on field names.
    """
    value:        Any
    found:        bool
    source:       str
    raw:          str = ""
    extractor_id: str = ""


@dataclass
class ResumeExtractionOutput:
    """
    Full output of extract_all_fields().

    extracted   : {field_name: value} for all schema fields.
    results     : {field_name: ExtractionResult} with provenance.
    unmatched   : field names where no extractor produced a real match.
    skills      : flat list of all detected skill strings (always populated).
    score       : ResumeScore (if scoring was requested).
    """
    extracted:  dict[str, Any]
    results:    dict[str, ExtractionResult]
    unmatched:  list[str]
    skills:     list[str]
    score:      "ResumeScore | None" = None


@dataclass
class ResumeScore:
    total:            int
    level:            str
    experience_score: int
    experience_note:  str
    education_score:  int
    education_note:   str
    skills_score:     int
    skills_note:      str
    breakdown:        dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lexicon loading (cached -- loaded once per process)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _load_skills_flat() -> list[str]:
    """Return a flat list of all skills from the global skills.json file."""
    try:
        with open(_lexicon_path("skills.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        flat: list[str] = []
        for key, values in data.items():
            if key.startswith("_"):
                continue
            if isinstance(values, list):
                flat.extend(str(v).lower() for v in values)
        return sorted(set(flat))
    except Exception as exc:
        logger.warning("skills.json load failed: %s", exc)
        return []


@functools.lru_cache(maxsize=None)
def _load_job_titles() -> dict[str, list[str]]:
    """Return {canonical_title: [alias, ...]} from the global job_titles.json file."""
    try:
        with open(_lexicon_path("job_titles.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception as exc:
        logger.warning("job_titles.json load failed: %s", exc)
        return {}


@functools.lru_cache(maxsize=None)
def _load_education() -> dict[int, dict]:
    """Return {level_int: {label, patterns}} from education.json."""
    try:
        with open(_lexicon_path("education.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        levels = data.get("levels", {})
        return {int(k): v for k, v in levels.items()}
    except Exception as exc:
        logger.warning("education.json load failed: %s", exc)
        return {}


@functools.lru_cache(maxsize=None)
def _load_countries_display() -> dict[str, str]:
    """Return {alias_lower: display_name} from countries.json display_names."""
    try:
        with open(_lexicon_path("countries.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return {k.lower(): v for k, v in data.get("display_names", {}).items()}
    except Exception as exc:
        logger.warning("countries.json load failed: %s", exc)
        return {}


@functools.lru_cache(maxsize=None)
def _load_countries_iso() -> dict[str, str]:
    """Return {alias_lower: iso2_code} from countries.json iso_codes."""
    try:
        with open(_lexicon_path("countries.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        return {k.lower(): v for k, v in data.get("iso_codes", {}).items()}
    except Exception as exc:
        logger.warning("countries.json load failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# spaCy helpers (lazy, guarded)
# ---------------------------------------------------------------------------

_SPACY_AVAILABLE = False

try:
    import spacy  # type: ignore
    from spacy.matcher import PhraseMatcher  # type: ignore
    _SPACY_AVAILABLE = True
except ImportError:
    pass


@functools.lru_cache(maxsize=None)
def _get_nlp():
    """Load spaCy model once.  Returns None if unavailable."""
    if not _SPACY_AVAILABLE:
        return None
    try:
        return spacy.load("en_core_web_sm", disable=["parser", "textcat"])
    except Exception as exc:
        logger.warning("spaCy model load failed: %s", exc)
        return None


@functools.lru_cache(maxsize=None)
def _get_skill_matcher():
    """Build spaCy PhraseMatcher from skills lexicon.  Returns None if unavailable."""
    nlp = _get_nlp()
    if nlp is None:
        return None
    skills = _load_skills_flat()
    if not skills:
        return None
    try:
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        patterns = [nlp.make_doc(s) for s in skills]
        matcher.add("SKILLS", patterns)
        return matcher
    except Exception as exc:
        logger.warning("Skill matcher build failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# PDF text extraction (guarded)
# ---------------------------------------------------------------------------

_PDFPLUMBER_AVAILABLE = False
try:
    import pdfplumber  # type: ignore
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    pass


def extract_text_from_pdf(uploaded_file: Any) -> str:
    """
    Extract raw text from an uploaded PDF file object.

    Requires pdfplumber.  Returns empty string if unavailable or on error.
    Resets file pointer before and after reading.
    """
    if not _PDFPLUMBER_AVAILABLE:
        logger.warning("pdfplumber not available -- cannot extract PDF text")
        return ""
    if uploaded_file is None:
        return ""
    try:
        from io import BytesIO
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        parts: list[str] = []
        with pdfplumber.open(BytesIO(raw)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text)
        uploaded_file.seek(0)
        return "\n".join(parts).strip()
    except Exception as exc:
        logger.error("PDF extraction error: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

def preprocess_text(text: str, resume_config: dict | None = None) -> str:
    """
    Normalise whitespace, strip URLs and null bytes.

    When resume_config provides a 'preprocessing' block, the following
    overrides are applied:
      strip_urls       (bool, default True)  -- strip http/www URLs
      max_text_length  (int,  default 0)     -- truncate text if > 0
    """
    cfg = {}
    if resume_config:
        cfg = resume_config.get("preprocessing") or {}

    text = text.replace("\x00", " ")

    strip_urls = cfg.get("strip_urls", True)
    if strip_urls:
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"\bwww\.\S+\b", " ", text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = text.strip()

    max_len = cfg.get("max_text_length", 0)
    if isinstance(max_len, int) and max_len > 0:
        text = text[:max_len]

    return text


# ---------------------------------------------------------------------------
# Individual extractors
# All follow the signature: (text: str, field: dict, context: dict) -> ExtractionResult
# context carries things like "allowed_values", "schema_fields"
# ---------------------------------------------------------------------------

_EXP_PATTERNS = [
    re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)"
        r"\s+(?:of\s+)?(?:professional\s+)?experience",
        re.IGNORECASE,
    ),
    re.compile(
        r"experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
        re.IGNORECASE,
    ),
    # German: "5 Jahre/Jahren Berufserfahrung", "5 Jahre/Jahren Erfahrung"
    re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*jahren?\s+(?:berufs)?erfahrung",
        re.IGNORECASE,
    ),
    # French: "5 ans d'expérience" -- any char after d handles all apostrophe variants
    re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*an[sn]?\s+d.exp[e\u00e9]rience",
        re.IGNORECASE,
    ),
    # Spanish: "5 años de experiencia"
    re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*a[n\u00f1]os?\s+de\s+experiencia",
        re.IGNORECASE,
    ),
    # Portuguese: "5 anos de experiência", "5 anos de experiencia"
    re.compile(
        r"(\d+(?:\.\d+)?)\+?\s*anos?\s+de\s+experi[\u00eae]ncia",
        re.IGNORECASE,
    ),
]


def _extract_experience(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract numeric years of experience."""
    resume_config = context.get("resume_config") or {}
    ext_cfg = (resume_config.get("extractors") or {}).get("experience") or {}

    # Build the pattern list from config or fall back to module-level defaults.
    # Config patterns (if provided) replace the defaults entirely so the model
    # owner has full control.  Each entry in config must be a valid regex string.
    patterns = _EXP_PATTERNS
    cfg_patterns = ext_cfg.get("patterns")
    if cfg_patterns and isinstance(cfg_patterns, list):
        built: list[re.Pattern] = []
        for pat_str in cfg_patterns:
            try:
                built.append(re.compile(pat_str, re.IGNORECASE))
            except re.error as exc:
                logger.warning(
                    "resume_config extractors.experience.patterns: bad regex '%s': %s",
                    pat_str, exc,
                )
        if built:
            patterns = built

    max_years = float(ext_cfg.get("max_years", 50))

    candidates: list[float] = []
    for pat in patterns:
        for m in pat.finditer(text):
            try:
                val = float(m.group(1))
                if 0.0 <= val <= max_years:
                    candidates.append(val)
            except (ValueError, IndexError):
                pass

    if not candidates:
        default = float(field.get("default", 0))
        return ExtractionResult(value=default, found=False, source="no_match_default")

    value = max(candidates)
    return ExtractionResult(value=value, found=True, source="regex", raw=str(value))


def _extract_education(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract education level as integer 0-3."""
    edu_data = _load_education()
    if not edu_data:
        default = int(field.get("default", 1))
        return ExtractionResult(value=default, found=False, source="lexicon_unavailable")

    for level in sorted(edu_data.keys(), reverse=True):
        level_cfg = edu_data[level]
        for pat_str in level_cfg.get("patterns", []):
            try:
                if re.search(pat_str, text, re.IGNORECASE):
                    label = level_cfg.get("label", str(level))
                    return ExtractionResult(
                        value=int(level), found=True,
                        source="pattern", raw=label,
                    )
            except re.error as exc:
                logger.warning("Bad education regex '%s': %s", pat_str, exc)

    default = int(field.get("default", 1))
    return ExtractionResult(value=default, found=False, source="no_match_default")


def _extract_country_name(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract country as display name (e.g. USA, India)."""
    allowed: list[str] | None = context.get("allowed_values")
    country_map = _load_countries_display()
    sorted_aliases = sorted(country_map.keys(), key=len, reverse=True)

    # spaCy NER pass
    nlp = _get_nlp()
    if nlp is not None:
        try:
            doc = nlp(text[:8000])
            for ent in doc.ents:
                if ent.label_ in {"GPE", "LOC"}:
                    alias = ent.text.lower().strip()
                    mapped = country_map.get(alias)
                    if mapped:
                        if allowed is None or mapped in allowed:
                            return ExtractionResult(
                                value=mapped, found=True,
                                source=f"ner:{alias}", raw=ent.text,
                            )
        except Exception as exc:
            logger.debug("NER pass failed: %s", exc)

    # Plain text scan (longest alias first)
    text_lower = text.lower()
    for alias in sorted_aliases:
        mapped = country_map[alias]
        if allowed is not None and mapped not in allowed:
            continue
        if alias in text_lower:
            return ExtractionResult(
                value=mapped, found=True,
                source=f"alias:{alias}", raw=alias,
            )

    default_val = "Other"
    if allowed and "Other" not in allowed:
        default_val = allowed[0] if allowed else "Other"
    if field.get("default"):
        default_val = field["default"]
    return ExtractionResult(value=default_val, found=False, source="default")


def _extract_country_iso(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract country as ISO-2 code (e.g. US, IN)."""
    allowed: list[str] | None = context.get("allowed_values")
    iso_map = _load_countries_iso()
    sorted_aliases = sorted(iso_map.keys(), key=len, reverse=True)

    nlp = _get_nlp()
    if nlp is not None:
        try:
            doc = nlp(text[:8000])
            for ent in doc.ents:
                if ent.label_ in {"GPE", "LOC"}:
                    alias = ent.text.lower().strip()
                    iso = iso_map.get(alias)
                    if iso:
                        if allowed is None or iso in allowed:
                            return ExtractionResult(
                                value=iso, found=True,
                                source=f"ner:{alias}", raw=ent.text,
                            )
        except Exception as exc:
            logger.debug("NER pass failed: %s", exc)

    text_lower = text.lower()
    for alias in sorted_aliases:
        if len(alias) <= 2:
            continue
        iso = iso_map[alias]
        if allowed is not None and iso not in allowed:
            continue
        if alias in text_lower:
            return ExtractionResult(
                value=iso, found=True,
                source=f"alias:{alias}", raw=alias,
            )

    default_iso = "US"
    if field.get("default"):
        default_iso = field["default"]
    elif allowed:
        default_iso = allowed[0]
    return ExtractionResult(value=default_iso, found=False, source="default")


def _extract_senior_flag(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract seniority as 0 or 1."""
    resume_config = context.get("resume_config") or {}
    ext_cfg = (resume_config.get("extractors") or {}).get("senior_flag") or {}

    # Allow bundle to extend or replace the default keyword list
    default_kws = [
        "senior", "sr.", "lead", "principal", "staff",
        "head", "director", "vp", "chief", "manager",
    ]
    senior_kws = ext_cfg.get("keywords") if ext_cfg.get("keywords") else default_kws

    # Bundle can raise or lower the experience threshold for auto-seniority
    exp_threshold = float(ext_cfg.get("experience_threshold", 6))

    text_lower = text.lower()
    for kw in senior_kws:
        if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
            return ExtractionResult(value=1, found=True, source=f"keyword:{kw}", raw=kw)

    exp_result = _extract_experience(text, {}, context)
    if exp_result.found and float(exp_result.value) >= exp_threshold:
        return ExtractionResult(
            value=1, found=True,
            source="experience_threshold", raw=str(exp_result.value),
        )

    return ExtractionResult(value=0, found=True, source="default_junior")


def _extract_job_title(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract job title from lexicon aliases, longest match first."""
    allowed: list[str] | None = context.get("allowed_values")
    resume_config = context.get("resume_config") or {}
    ext_cfg = (resume_config.get("extractors") or {}).get("job_title") or {}

    # Use bundle job titles if provided, falling back to global lexicon.
    titles_map = _resolve_job_titles(context.get("bundle_lexicons"))

    if not titles_map:
        default = field.get("default", "Software Engineer")
        return ExtractionResult(value=default, found=False, source="lexicon_unavailable")

    # Build sorted (alias, canonical) pairs by alias length descending
    pairs: list[tuple[str, str]] = []
    for canonical, aliases in titles_map.items():
        for alias in aliases:
            pairs.append((alias.lower(), canonical))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)

    text_lower = text.lower()
    for alias, canonical in pairs:
        if allowed is not None and canonical not in allowed:
            continue
        if re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
            return ExtractionResult(
                value=canonical, found=True,
                source=f"alias:{alias}", raw=alias,
            )

    # Keyword fallback: config replaces the built-in list when provided.
    # Config format: [[["kw1", "kw2"], "Title"], ...]
    # Built-in format (same structure internally):
    builtin_kw_map = [
        (["data engineer", "etl", "pipeline"], "Data Engineer"),
        (["data scientist", "machine learning", "deep learning"], "Data Scientist"),
        (["data analyst", "business analyst", "analytics"], "Data Analyst"),
        (["software engineer", "software developer", "developer"], "Software Engineer"),
        (["web developer", "frontend", "backend", "full stack"], "Web Developer"),
        (["devops", "site reliability", "cloud engineer"], "DevOps Engineer"),
    ]

    cfg_fallback = ext_cfg.get("keyword_fallback")
    if cfg_fallback and isinstance(cfg_fallback, list):
        # Build from config: each entry is [keywords_list, title_string]
        kw_map: list[tuple[list[str], str]] = []
        for pair in cfg_fallback:
            if (
                isinstance(pair, list)
                and len(pair) == 2
                and isinstance(pair[0], list)
                and isinstance(pair[1], str)
            ):
                kw_map.append((pair[0], pair[1]))
            else:
                logger.warning(
                    "resume_config extractors.job_title.keyword_fallback: "
                    "skipping malformed entry %r", pair,
                )
    else:
        kw_map = builtin_kw_map

    for keywords, title in kw_map:
        if allowed is not None and title not in allowed:
            continue
        if any(kw in text_lower for kw in keywords):
            return ExtractionResult(
                value=title, found=True,
                source="keyword_fallback", raw=keywords[0],
            )

    default = field.get("default")
    if not default and allowed:
        default = allowed[0]
    if not default:
        default = "Software Engineer"
    return ExtractionResult(value=default, found=False, source="fallback_default")


def _extract_employment_type(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract employment type as FT / PT / CT / FL."""
    resume_config = context.get("resume_config") or {}
    ext_cfg = (resume_config.get("extractors") or {}).get("employment_type") or {}

    text_lower = text.lower()

    # Each keyword group can be overridden by config.  Config replaces defaults
    # entirely for that group when present.
    pt_kws  = ext_cfg.get("part_time_keywords")  or []
    fl_kws  = ext_cfg.get("freelance_keywords")  or []
    ct_kws  = ext_cfg.get("contract_keywords")   or []

    # Default regex-based detection (runs when config does not supply keywords)
    if pt_kws:
        if any(re.search(r"\b" + re.escape(kw) + r"\b", text_lower) for kw in pt_kws):
            return ExtractionResult(value="PT", found=True, source="keyword:part-time")
    else:
        if re.search(r"\bpart[-\s]?time\b", text_lower) or re.search(r"\bintern(ship)?\b", text_lower):
            return ExtractionResult(value="PT", found=True, source="keyword:part-time")

    if fl_kws:
        if any(re.search(r"\b" + re.escape(kw) + r"\b", text_lower) for kw in fl_kws):
            return ExtractionResult(value="FL", found=True, source="keyword:freelance")
    else:
        if re.search(r"\bfreelance(r)?\b", text_lower) or re.search(r"\bself[-\s]?employed\b", text_lower):
            return ExtractionResult(value="FL", found=True, source="keyword:freelance")

    if ct_kws:
        if any(re.search(r"\b" + re.escape(kw) + r"\b", text_lower) for kw in ct_kws):
            return ExtractionResult(value="CT", found=True, source="keyword:contract")
    else:
        if re.search(r"\bcontract(or)?\b", text_lower) or re.search(r"\bconsult(ing|ant)\b", text_lower):
            return ExtractionResult(value="CT", found=True, source="keyword:contract")

    default = field.get("default", "FT")
    return ExtractionResult(value=default, found=True, source="default_full_time")


def _extract_remote_ratio(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract remote ratio as 0, 50, or 100."""
    resume_config = context.get("resume_config") or {}
    ext_cfg = (resume_config.get("extractors") or {}).get("remote_ratio") or {}

    text_lower = text.lower()

    # Keyword groups: config fully replaces defaults for any group supplied
    remote_kws = ext_cfg.get("remote_keywords") or [
        "fully remote", "100% remote", "remote work",
        "work from home", "wfh", "remote position",
    ]
    hybrid_kws = ext_cfg.get("hybrid_keywords") or [
        "hybrid", "partial remote", "flexible working", "flex work",
    ]
    onsite_kws = ext_cfg.get("onsite_keywords") or [
        "on-site", "onsite", "on site", "in office", "in-office",
    ]

    for kw in remote_kws:
        if kw in text_lower:
            return ExtractionResult(value=100, found=True, source=f"keyword:{kw}")
    for kw in hybrid_kws:
        if kw in text_lower:
            return ExtractionResult(value=50, found=True, source=f"keyword:{kw}")
    for kw in onsite_kws:
        if kw in text_lower:
            return ExtractionResult(value=0, found=True, source=f"keyword:{kw}")

    default = int(field.get("default", 0))
    return ExtractionResult(value=default, found=False, source="no_match_default")


def _extract_skills_list(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract skills as a list of strings."""
    skills = _extract_skills_internal(text, bundle_lexicons=context.get("bundle_lexicons"))
    found = len(skills) > 0
    return ExtractionResult(
        value=skills, found=found,
        source="spacy_phrase_matcher" if found else "no_skills_found",
    )


def _extract_skills_str(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract skills as a comma-separated string."""
    skills = _extract_skills_internal(text, bundle_lexicons=context.get("bundle_lexicons"))
    found = len(skills) > 0
    return ExtractionResult(
        value=", ".join(skills), found=found,
        source="spacy_phrase_matcher" if found else "no_skills_found",
    )


def _extract_age(text: str, field: dict, context: dict) -> ExtractionResult:
    """Extract age as integer."""
    resume_config = context.get("resume_config") or {}
    ext_cfg = (resume_config.get("extractors") or {}).get("age") or {}

    min_age = int(ext_cfg.get("min_age", 16))
    max_age = int(ext_cfg.get("max_age", 80))

    m = re.search(r"\bage[:\s]+(\d{2})\b", text, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        if min_age <= val <= max_age:
            return ExtractionResult(value=val, found=True, source="regex:age_label")
    pat = re.compile(
        r"\b(" + str(min_age) + r"|[2-5]\d|6[0-5])\s*(?:years?\s+)?old\b",
        re.IGNORECASE,
    )
    m2 = pat.search(text)
    if m2:
        val = int(m2.group(1))
        if min_age <= val <= max_age:
            return ExtractionResult(value=val, found=True, source="regex:years_old")
    default = int(field.get("default", 28))
    return ExtractionResult(value=default, found=False, source="no_match_default")


# ---------------------------------------------------------------------------
# Internal skill extraction helper
# ---------------------------------------------------------------------------

def _extract_skills_internal(
    text: str,
    bundle_lexicons: dict | None = None,
) -> list[str]:
    """
    Return sorted list of matched skill strings.

    When bundle_lexicons provides "skills", a fresh matcher is built from
    the bundle skill list for this call only.  Otherwise the cached global
    matcher is used.
    """
    nlp = _get_nlp()

    if bundle_lexicons and "skills" in bundle_lexicons:
        skills_list = _resolve_skills_flat(bundle_lexicons)
        matcher     = _build_skill_matcher_from_list(skills_list)
    else:
        matcher = _get_skill_matcher()

    if nlp is None or matcher is None:
        skills_list_fb = _resolve_skills_flat(bundle_lexicons)
        return _extract_skills_regex_fallback(text, skills_list_fb)
    try:
        doc = nlp(text[:50_000])
        matches = matcher(doc)
        found: set[str] = set()
        for _, start, end in matches:
            span_text = doc[start:end].text.strip()
            if span_text:
                found.add(span_text.lower())
        return sorted(found)
    except Exception as exc:
        logger.warning("spaCy skill extraction failed: %s", exc)
        skills_list_fb = _resolve_skills_flat(bundle_lexicons)
        return _extract_skills_regex_fallback(text, skills_list_fb)


def _extract_skills_regex_fallback(
    text: str,
    skills: list[str] | None = None,
) -> list[str]:
    """Regex fallback when spaCy is unavailable. Accepts an explicit skills list."""
    if skills is None:
        skills = _load_skills_flat()
    text_lower = text.lower()
    found: set[str] = set()
    for skill in skills:
        pattern = r"\b" + re.escape(skill) + r"\b"
        try:
            if re.search(pattern, text_lower):
                found.add(skill)
        except re.error:
            if skill in text_lower:
                found.add(skill)
    return sorted(found)


# ---------------------------------------------------------------------------
# Auto-extractor selection from field name
# ---------------------------------------------------------------------------

# Maps keyword substrings (checked against lowercased field name) to extractor id.
# First matching entry wins.  More specific entries should come first.
_FIELD_NAME_TO_EXTRACTOR: list[tuple[str, str]] = [
    ("employment_type",  "employment_type"),
    ("remote_ratio",     "remote_ratio"),
    ("remote",           "remote_ratio"),
    ("experience_level", "experience"),      # maps numeric years; caller can post-process
    ("experience",       "experience"),
    ("years_exp",        "experience"),
    ("years_of_exp",     "experience"),
    ("edu_level",        "education"),
    ("education",        "education"),
    ("country_iso",      "country_iso"),
    ("iso_code",         "country_iso"),
    ("residence",        "country_iso"),
    ("country",          "country_name"),
    ("location",         "country_name"),
    ("senior",           "senior_flag"),
    ("seniority",        "senior_flag"),
    ("job_title",        "job_title"),
    ("title",            "job_title"),
    ("role",             "job_title"),
    ("skills_str",       "skills_str"),
    ("skills",           "skills_list"),
    ("age",              "age"),
]


def _select_extractor(field_def: dict, resume_config: dict | None = None) -> str | None:
    """
    Return extractor identifier for a schema field.

    Checks the explicit "extractor" key first, then bundle field_name_mapping
    entries (from resume_config), then falls back to the module-level keyword
    table.  Returns None if no match.

    Bundle field_name_mapping entries are prepended to the lookup so they take
    priority over the built-in defaults without replacing them.  Each entry is
    a [keyword_string, extractor_id_string] pair.
    """
    explicit = field_def.get("extractor")
    if explicit:
        return str(explicit)

    name_lower = field_def.get("name", "").lower()

    # Bundle-level extra mappings (highest priority after explicit override)
    if resume_config:
        extra_mappings = resume_config.get("field_name_mapping") or []
        for entry in extra_mappings:
            if (
                isinstance(entry, list)
                and len(entry) == 2
                and isinstance(entry[0], str)
                and isinstance(entry[1], str)
            ):
                if entry[0].lower() in name_lower:
                    return entry[1]

    # Built-in module-level mappings
    for keyword, extractor_id in _FIELD_NAME_TO_EXTRACTOR:
        if keyword in name_lower:
            return extractor_id
    return None


# ---------------------------------------------------------------------------
# Extractor registry
# Maps extractor id -> callable(text, field, context) -> ExtractionResult
# Add new extractors here (plus the function above).
# ---------------------------------------------------------------------------

_EXTRACTOR_REGISTRY: dict[str, Any] = {
    "experience":       _extract_experience,
    "education":        _extract_education,
    "country_name":     _extract_country_name,
    "country_iso":      _extract_country_iso,
    "senior_flag":      _extract_senior_flag,
    "job_title":        _extract_job_title,
    "employment_type":  _extract_employment_type,
    "remote_ratio":     _extract_remote_ratio,
    "skills_list":      _extract_skills_list,
    "skills_str":       _extract_skills_str,
    "age":              _extract_age,
}


# ---------------------------------------------------------------------------
# Main extraction entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bundle-level lexicon helpers
# ---------------------------------------------------------------------------

def _resolve_skills_flat(bundle_lexicons: dict | None) -> list[str]:
    """
    Return the flat skills list to use for this extraction call.

    Bundle lexicon (if provided) takes priority over the global JSON file.
    This function never touches lru_cache state -- it is safe for concurrent
    Streamlit sessions because it passes data through the call stack only.
    """
    if bundle_lexicons and "skills" in bundle_lexicons:
        skills_data = bundle_lexicons["skills"]
        flat: list[str] = []
        for key, values in skills_data.items():
            if key.startswith("_"):
                continue
            if isinstance(values, list):
                flat.extend(str(v).lower() for v in values)
        return sorted(set(flat))
    return _load_skills_flat()


def _resolve_job_titles(bundle_lexicons: dict | None) -> dict[str, list[str]]:
    """
    Return the job titles map to use for this extraction call.

    Bundle lexicon (if provided) takes priority over the global JSON file.
    """
    if bundle_lexicons and "job_titles" in bundle_lexicons:
        data = bundle_lexicons["job_titles"]
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return _load_job_titles()


def _build_skill_matcher_from_list(skills: list[str]):
    """Build a PhraseMatcher from an explicit list of skills (not cached)."""
    nlp = _get_nlp()
    if nlp is None:
        return None
    try:
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        patterns = [nlp.make_doc(s) for s in skills]
        matcher.add("SKILLS", patterns)
        return matcher
    except Exception as exc:
        logger.warning("Skill matcher build from list failed: %s", exc)
        return None


def extract_all_fields(
    raw_text: str,
    schema_fields: list[dict],
    compute_score: bool = True,
    bundle_lexicons: dict | None = None,
    resume_config: dict | None = None,
) -> ResumeExtractionOutput:
    """
    Extract values for every field in schema_fields from raw_text.

    Parameters
    ----------
    raw_text        : Raw text extracted from a PDF (before preprocessing).
    schema_fields   : List of schema field dicts from schema.json.
    compute_score   : Whether to compute a ResumeScore from extracted values.
    bundle_lexicons : Optional dict of lexicon overrides loaded from the model
                      bundle folder on HuggingFace.  Supported keys:
                        "skills"     -> dict in skills.json format (categorised)
                        "job_titles" -> dict in job_titles.json format
                      When provided, these replace the global app-level lexicons
                      for this extraction call.  Missing keys fall back to the
                      global JSON files in the lexicons/ directory.
                      This dict is passed in from ModelBundle.lexicons which
                      loader.py populates at bundle load time.
    resume_config   : Optional dict loaded from resume_config.json in the model
                      bundle.  When present, selectively overrides engine defaults
                      for scoring weights, extractor keyword lists, extractor
                      patterns, field-name-to-extractor mappings, and text
                      preprocessing flags.  All keys are optional -- missing keys
                      fall back to built-in defaults.
                      Passed in from ModelBundle.resume_config by hub_resume_tab.py.

    Returns
    -------
    ResumeExtractionOutput with all extracted values, provenance, and score.
    """
    text = preprocess_text(raw_text, resume_config=resume_config)

    extracted: dict[str, Any] = {}
    results:   dict[str, ExtractionResult] = {}
    unmatched: list[str] = []

    for fld in schema_fields:
        name         = fld.get("name", "")
        extractor_id = _select_extractor(fld, resume_config=resume_config)

        if extractor_id is None:
            unmatched.append(name)
            continue

        extractor_fn = _EXTRACTOR_REGISTRY.get(extractor_id)
        if extractor_fn is None:
            logger.warning("Unknown extractor '%s' for field '%s'", extractor_id, name)
            unmatched.append(name)
            continue

        # Build context for the extractor.
        # bundle_lexicons and resume_config are passed through so individual
        # extractors can use bundle-level data without global state.
        context: dict = {}
        if fld.get("values"):
            context["allowed_values"] = list(fld["values"])
        if bundle_lexicons:
            context["bundle_lexicons"] = bundle_lexicons
        if resume_config:
            context["resume_config"] = resume_config

        try:
            result = extractor_fn(text, fld, context)
            # Attach the extractor_id so _compute_score can identify result types
            # without depending on field names (which are schema-defined and arbitrary).
            result = ExtractionResult(
                value        = result.value,
                found        = result.found,
                source       = result.source,
                raw          = result.raw,
                extractor_id = extractor_id,
            )
        except Exception as exc:
            logger.error("Extractor '%s' failed for field '%s': %s", extractor_id, name, exc)
            result = ExtractionResult(
                value        = fld.get("default"),
                found        = False,
                source       = f"extractor_error:{exc}",
                extractor_id = extractor_id,
            )

        if not result.found:
            unmatched.append(name)

        extracted[name] = result.value
        results[name]   = result

    skills_flat = _extract_skills_internal(text, bundle_lexicons=bundle_lexicons)

    score: ResumeScore | None = None
    if compute_score:
        score = _compute_score(extracted, results, skills_flat, resume_config=resume_config)

    return ResumeExtractionOutput(
        extracted  = extracted,
        results    = results,
        unmatched  = unmatched,
        skills     = skills_flat,
        score      = score,
    )


# ---------------------------------------------------------------------------
# Resume scoring
# ---------------------------------------------------------------------------

def _compute_score(
    extracted: dict[str, Any],
    results: dict[str, ExtractionResult],
    skills: list[str],
    resume_config: dict | None = None,
) -> ResumeScore:
    """
    Compute a resume quality score from extracted fields.

    Default scoring rubric (max 100):
        Experience  : 0-40  (by years found)
        Education   : 0-30  (by level found)
        Skills      : 0-30  (by count)

    When resume_config provides a 'scoring' block, the following keys override
    the defaults:
        experience_max   (int/float) -- max points for experience dimension
        education_max    (int/float) -- max points for education dimension
        skills_max       (int/float) -- max points for skills dimension
        skills_per_point (int/float) -- skill count multiplier (default 3)
        thresholds       (dict)      -- experience band overrides:
                                       {band_name: {max, score, note}}
                                       Bands are sorted by 'max' ascending.
                                       The last band (highest max) is the catch-all.
        edu_map          (dict)      -- education level overrides:
                                       {"0": [score, note], "1": [...], ...}
    """
    scoring_cfg: dict = {}
    if resume_config:
        scoring_cfg = resume_config.get("scoring") or {}

    exp_max         = float(scoring_cfg.get("experience_max",   40))
    edu_max         = float(scoring_cfg.get("education_max",    30))
    skills_max      = float(scoring_cfg.get("skills_max",       30))
    skills_per_pt   = float(scoring_cfg.get("skills_per_point",  3))

    # --- Experience score ---
    # Find the largest numeric value from any "experience" extractor.
    # Uses extractor_id (not field name) so it works with any schema field names.
    exp_val = 0.0
    for res in results.values():
        if (
            res.extractor_id == "experience"
            and res.found
            and isinstance(res.value, (int, float))
        ):
            exp_val = max(exp_val, float(res.value))

    cfg_thresholds = scoring_cfg.get("thresholds")
    if cfg_thresholds and isinstance(cfg_thresholds, dict):
        # Sort bands by 'max' ascending so we find the first band that fits.
        bands = sorted(
            cfg_thresholds.values(),
            key=lambda b: b.get("max", 0) if isinstance(b, dict) else 0,
        )
        exp_score, exp_note = int(exp_max), "Highly experienced profile"
        for band in bands:
            if not isinstance(band, dict):
                continue
            band_max = band.get("max", 0)
            if exp_val <= band_max:
                exp_score = int(band.get("score", 0))
                exp_note  = str(band.get("note", ""))
                break
    else:
        # Built-in default bands
        if exp_val <= 0:
            exp_score, exp_note = 0, "No experience information found"
        elif exp_val <= 1:
            exp_score, exp_note = 8, "Entry-level experience"
        elif exp_val <= 3:
            exp_score, exp_note = 18, "Early professional experience"
        elif exp_val <= 6:
            exp_score, exp_note = 28, "Solid professional experience"
        elif exp_val <= 10:
            exp_score, exp_note = 36, "Strong professional experience"
        else:
            exp_score, exp_note = int(exp_max), "Highly experienced profile"

    # --- Education score ---
    # Find the first result from the "education" extractor.
    # Uses extractor_id so any schema field name works.
    edu_val = 1  # default: bachelor
    for res in results.values():
        if res.extractor_id == "education" and isinstance(res.value, int):
            edu_val = res.value
            break

    cfg_edu_map = scoring_cfg.get("edu_map")
    if cfg_edu_map and isinstance(cfg_edu_map, dict):
        # Keys are string level ints: {"0": [score, note], ...}
        entry = cfg_edu_map.get(str(edu_val))
        if (
            entry
            and isinstance(entry, (list, tuple))
            and len(entry) >= 2
        ):
            edu_score = int(entry[0])
            edu_note  = str(entry[1])
        else:
            edu_score, edu_note = int(edu_max // 2), "Education level unknown"
    else:
        default_edu_map = {
            0: (5,  "High school level"),
            1: (15, "Bachelor's level"),
            2: (22, "Master's level"),
            3: (30, "PhD level"),
        }
        edu_score, edu_note = default_edu_map.get(edu_val, (10, "Education level unknown"))

    # Clamp to configured max in case config bands exceed it
    edu_score = min(edu_score, int(edu_max))

    # --- Skills score ---
    skill_count = len(skills)
    skill_score = min(int(skill_count * skills_per_pt), int(skills_max))
    if skill_count == 0:
        skill_note = "No skills detected"
    elif skill_count <= 3:
        skill_note = "Basic skill coverage"
    elif skill_count <= 8:
        skill_note = "Good skill coverage"
    else:
        skill_note = "Strong skill coverage"

    total = min(exp_score + edu_score + skill_score, 100)

    if total < 35:
        level = "Basic"
    elif total < 65:
        level = "Moderate"
    else:
        level = "Strong"

    return ResumeScore(
        total            = total,
        level            = level,
        experience_score = exp_score,
        experience_note  = exp_note,
        education_score  = edu_score,
        education_note   = edu_note,
        skills_score     = skill_score,
        skills_note      = skill_note,
        breakdown={
            "experience_years": exp_val,
            "education_level":  edu_val,
            "skill_count":      skill_count,
        },
    )