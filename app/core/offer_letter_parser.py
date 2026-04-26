"""
app/core/offer_letter_parser.py
--------------------------------
Rule-based offer letter parsing utilities for SalaryScope.

Purpose
-------
- Extract structured compensation and employment fields from offer letter PDFs
- Stay academic-safe by using transparent regex/rule patterns instead of
  opaque inference
- Produce editable, evidence-backed outputs that downstream tabs/tools can use

This module is intentionally standalone. It does not depend on Streamlit and
can be removed without affecting existing resume parsing or HR tools.
"""

from __future__ import annotations

import io
import re
from typing import Any

import pdfplumber

from app.utils.country_utils import resolve_iso2


_CURRENCY_SYMBOL_TO_CODE = {
    "$": "USD",
    "₹": "INR",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "AED": "AED",
    "SGD": "SGD",
    "AUD": "AUD",
    "CAD": "CAD",
}

_WORK_MODE_PATTERNS = {
    "Remote": [r"\bremote\b", r"\bwork from home\b", r"\bwfh\b"],
    "Hybrid": [r"\bhybrid\b", r"\bpartially remote\b", r"\bflexible location\b"],
    "On-site": [r"\bon[\s-]?site\b", r"\bin[\s-]?office\b", r"\bwork from office\b"],
}

_LABEL_PATTERNS: dict[str, list[str]] = {
    "base_salary": [
        r"(?:base salary|fixed salary|annual base|annual salary|base pay|gross salary)",
    ],
    "ctc": [
        r"(?:ctc|cost to company|total compensation|total cash compensation|annual compensation package)",
    ],
    "joining_bonus": [
        r"(?:joining bonus|sign[\s-]?on bonus|sign[\s-]?up bonus|welcome bonus)",
    ],
    "annual_bonus": [
        r"(?:annual bonus|performance bonus|variable pay|target bonus|incentive bonus)",
    ],
    "equity": [
        r"(?:equity|esop|esops|stock grant|restricted stock units|rsu|rsus|stock options)",
    ],
    "job_title": [
        r"(?:job title|position|role|designation)",
    ],
    "level": [
        r"(?:level|grade|band|job level|designation level)",
    ],
    "location": [
        r"(?:location|work location|place of work|base location)",
    ],
    "probation": [
        r"(?:probation period|probation)",
    ],
    "notice": [
        r"(?:notice period|notice)",
    ],
}


def extract_text_from_offer_pdf(uploaded_file: Any) -> dict[str, Any]:
    """
    Extract plain text from an uploaded offer letter PDF.

    Parameters
    ----------
    uploaded_file:
        Streamlit UploadedFile, bytes, or a file-like object.
    """
    raw_bytes = _read_pdf_bytes(uploaded_file)

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")

    text = "\n".join(page for page in pages if page.strip())
    cleaned = preprocess_offer_text(text)

    return {
        "text": cleaned,
        "page_count": len(pages),
        "character_count": len(cleaned),
    }


def preprocess_offer_text(text: str) -> str:
    """Normalise spacing while preserving line boundaries for label matching."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_offer_letter_fields(text: str) -> dict[str, Any]:
    """Extract structured offer letter fields and evidence snippets."""
    cleaned = preprocess_offer_text(text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    flat_text = " ".join(lines)

    currency_code = _detect_currency_code(cleaned)

    base_salary_match = _extract_labeled_money(cleaned, _LABEL_PATTERNS["base_salary"])
    ctc_match = _extract_labeled_money(cleaned, _LABEL_PATTERNS["ctc"])
    joining_bonus_match = _extract_labeled_money(cleaned, _LABEL_PATTERNS["joining_bonus"])
    annual_bonus_match = _extract_labeled_money(cleaned, _LABEL_PATTERNS["annual_bonus"])

    annual_bonus_percent = _extract_percent_near_labels(cleaned, _LABEL_PATTERNS["annual_bonus"])

    role_title = _extract_labeled_text(cleaned, _LABEL_PATTERNS["job_title"])
    level = _extract_labeled_text(cleaned, _LABEL_PATTERNS["level"])
    location = _extract_labeled_text(cleaned, _LABEL_PATTERNS["location"])
    work_mode_label = _extract_labeled_text(cleaned, [r"(?:work mode|work arrangement)"])
    probation_period = _extract_duration_text(cleaned, _LABEL_PATTERNS["probation"])
    notice_period = _extract_duration_text(cleaned, _LABEL_PATTERNS["notice"])
    work_mode = _normalize_work_mode(work_mode_label["value"]) or _detect_work_mode(cleaned)

    equity_mentions = _find_keyword_evidence(cleaned, _LABEL_PATTERNS["equity"])
    best_equity_evidence = _pick_best_equity_evidence(equity_mentions)

    company_name = _extract_company_name(cleaned, lines)
    candidate_name = _extract_candidate_name(lines)
    country_code = _extract_country_code(location["value"], cleaned)

    fields = {
        "candidate_name": candidate_name,
        "company_name": company_name,
        "job_title": role_title["value"],
        "level_or_band": level["value"],
        "location": location["value"],
        "country_code": country_code,
        "work_mode": work_mode,
        "currency_code": currency_code,
        "base_salary": base_salary_match["amount"],
        "total_ctc": ctc_match["amount"],
        "joining_bonus": joining_bonus_match["amount"],
        "annual_bonus_fixed": annual_bonus_match["amount"],
        "annual_bonus_percent": annual_bonus_percent["value"],
        "equity_mentioned": bool(equity_mentions),
        "equity_text": best_equity_evidence,
        "probation_period": probation_period["value"],
        "notice_period": notice_period["value"],
        "pay_frequency": _infer_pay_frequency(flat_text),
    }

    evidence = {
        "candidate_name": candidate_name,
        "company_name": company_name,
        "job_title": role_title["evidence"],
        "level_or_band": level["evidence"],
        "location": location["evidence"],
        "country_code": country_code,
        "base_salary": base_salary_match["evidence"],
        "total_ctc": ctc_match["evidence"],
        "joining_bonus": joining_bonus_match["evidence"],
        "annual_bonus_fixed": annual_bonus_match["evidence"],
        "annual_bonus_percent": annual_bonus_percent["evidence"],
        "equity_text": best_equity_evidence,
        "probation_period": probation_period["evidence"],
        "notice_period": notice_period["evidence"],
    }

    completeness_score = _compute_completeness(fields)

    return {
        "fields": fields,
        "evidence": evidence,
        "completeness_score": completeness_score,
        "missing_fields": [
            key for key, value in fields.items()
            if key in {
                "job_title",
                "location",
                "currency_code",
                "base_salary",
                "total_ctc",
            } and _is_missing_value(value)
        ],
        "raw_text": cleaned,
    }


def build_offer_letter_summary(parsed: dict[str, Any]) -> dict[str, Any]:
    """Build a compact summary payload for downstream tools or UI rendering."""
    fields = parsed.get("fields", {})
    currency = fields.get("currency_code") or "Unknown"
    headline_amount = fields.get("total_ctc") or fields.get("base_salary")

    return {
        "headline_compensation": _format_money(headline_amount, currency),
        "base_salary_text": _format_money(fields.get("base_salary"), currency),
        "ctc_text": _format_money(fields.get("total_ctc"), currency),
        "joining_bonus_text": _format_money(fields.get("joining_bonus"), currency),
        "annual_bonus_text": _format_money(fields.get("annual_bonus_fixed"), currency),
        "annual_bonus_percent_text": (
            f"{fields['annual_bonus_percent']:.1f}%"
            if isinstance(fields.get("annual_bonus_percent"), (int, float))
            else ""
        ),
        "equity_flag_text": "Mentioned" if fields.get("equity_mentioned") else "Not detected",
    }


def build_downstream_payload(fields: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare a minimal neutral payload for comparison/finance tools.

    This does not invoke existing tabs directly. It only shapes the data so a
    later integration can prefill offer comparison, CTC, take-home, or savings
    utilities.
    """
    annual_comp = fields.get("total_ctc") or fields.get("base_salary")

    return {
        "job_title": fields.get("job_title"),
        "location": fields.get("location"),
        "country_code": fields.get("country_code"),
        "work_mode": fields.get("work_mode"),
        "currency_code": fields.get("currency_code"),
        "annual_compensation": annual_comp,
        "base_salary": fields.get("base_salary"),
        "joining_bonus": fields.get("joining_bonus"),
        "annual_bonus_fixed": fields.get("annual_bonus_fixed"),
        "annual_bonus_percent": fields.get("annual_bonus_percent"),
        "probation_period": fields.get("probation_period"),
        "notice_period": fields.get("notice_period"),
        "equity_mentioned": fields.get("equity_mentioned", False),
    }


def _read_pdf_bytes(uploaded_file: Any) -> bytes:
    if isinstance(uploaded_file, bytes):
        return uploaded_file

    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()

    if hasattr(uploaded_file, "read"):
        data = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return data

    raise TypeError("Unsupported PDF input type for offer letter extraction.")


def _extract_labeled_money(text: str, label_patterns: list[str]) -> dict[str, Any]:
    for label in label_patterns:
        pattern = re.compile(
            rf"(?is)({label})\s*(?:[:\-]|is|of)?\s*"
            rf"((?:usd|inr|eur|gbp|aed|sgd|aud|cad)?\s*[$₹€£]?\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|lpa|crore|million|mn))?)"
        )
        match = pattern.search(text)
        if match:
            parsed_amount = _parse_money_value(match.group(2))
            if parsed_amount is None:
                continue
            return {
                "amount": parsed_amount,
                "evidence": match.group(0).strip(),
            }
    return {"amount": None, "evidence": ""}


def _extract_percent_near_labels(text: str, label_patterns: list[str]) -> dict[str, Any]:
    for label in label_patterns:
        pattern = re.compile(rf"(?is)({label}).{{0,50}}?(\d+(?:\.\d+)?)\s*%")
        match = pattern.search(text)
        if match:
            return {"value": float(match.group(2)), "evidence": match.group(0).strip()}
    return {"value": None, "evidence": ""}


def _extract_labeled_text(text: str, label_patterns: list[str]) -> dict[str, str]:
    for label in label_patterns:
        pattern = re.compile(rf"(?im)({label})\s*(?:[:\-])\s*(.+)$")
        match = pattern.search(text)
        if match:
            return {"value": match.group(2).strip(), "evidence": match.group(0).strip()}
    return {"value": "", "evidence": ""}


def _extract_duration_text(text: str, label_patterns: list[str]) -> dict[str, str]:
    for label in label_patterns:
        pattern = re.compile(
            rf"(?is)({label}).{{0,40}}?((?:\d+\s*(?:day|days|month|months))|(?:one|two|three|four|six)\s*(?:month|months))"
        )
        match = pattern.search(text)
        if match:
            return {"value": match.group(2).strip(), "evidence": match.group(0).strip()}
    return {"value": "", "evidence": ""}


def _detect_currency_code(text: str) -> str:
    for token, code in _CURRENCY_SYMBOL_TO_CODE.items():
        if token in text:
            return code

    upper_text = text.upper()
    for code in ("USD", "INR", "EUR", "GBP", "AED", "SGD", "AUD", "CAD"):
        if re.search(rf"\b{code}\b", upper_text):
            return code
    return ""


def _detect_work_mode(text: str) -> str:
    for label, patterns in _WORK_MODE_PATTERNS.items():
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            return label
    return ""


def _find_keyword_evidence(text: str, label_patterns: list[str]) -> list[str]:
    evidences: list[str] = []
    for label in label_patterns:
        for match in re.finditer(rf"(?im)^.*({label}).*$", text):
            evidences.append(match.group(0).strip())
    return evidences


def _pick_best_equity_evidence(evidences: list[str]) -> str:
    if not evidences:
        return ""

    priority_patterns = [r"\besop\b", r"\brsu\b", r"\bstock option", r"\bequity & long-term incentive\b"]
    for pattern in priority_patterns:
        for evidence in evidences:
            if re.search(pattern, evidence, flags=re.IGNORECASE):
                return evidence
    return evidences[0]


def _extract_company_name(text: str, lines: list[str]) -> str:
    contextual_patterns = [
        r"offer of employment.*?to you at\s+(.+?)\s+\(the\s+company\)",
        r"we are delighted to extend this offer of employment to you at\s+(.+?)\s+\(the\s+company\)",
        r"authorised signatory\s+(.+?)\s+date:",
    ]
    for pattern in contextual_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidate = _clean_company_name(match.group(1))
            if candidate:
                return candidate

    for idx, line in enumerate(lines[:8]):
        if re.search(r"\b(?:private limited|pvt ltd|limited|inc\.?|llc|technologies|solutions|labs)\b", line, re.I):
            return _clean_company_name(line)
        if idx == 0 and 2 <= len(line.split()) <= 6 and line.isupper():
            return line.title()
    return ""


def _extract_candidate_name(lines: list[str]) -> str:
    for idx, line in enumerate(lines[:12]):
        same_line = re.search(r"^\s*(?:dear|hello|hi)\s+(.+?)[,:]?\s*$", line, re.I)
        if same_line:
            candidate = same_line.group(1).strip()
            if 1 <= len(candidate.split()) <= 5:
                return candidate
        if re.search(r"\b(?:dear|hello|hi)\b", line, re.I) and idx + 1 < len(lines):
            next_line = lines[idx + 1].strip(" ,:")
            if 1 <= len(next_line.split()) <= 4:
                return next_line

    for line in lines[:8]:
        stripped = line.strip()
        if 1 <= len(stripped.split()) <= 4 and re.fullmatch(r"[A-Za-z][A-Za-z .'-]+", stripped):
            if not re.search(r"\b(?:offer|letter|appointment|employment)\b", stripped, re.I):
                return stripped
    return ""


def _infer_pay_frequency(text: str) -> str:
    if re.search(r"\bper month\b|\bmonthly\b", text, re.I):
        return "Monthly"
    if re.search(r"\bper annum\b|\bannual\b|\byearly\b", text, re.I):
        return "Annual"
    return "Annual"


def _normalize_work_mode(value: str) -> str:
    lowered = (value or "").lower()
    if "hybrid" in lowered:
        return "Hybrid"
    if "remote" in lowered:
        return "Remote"
    if "site" in lowered or "office" in lowered:
        return "On-site"
    return ""


def _extract_country_code(location_value: str, text: str) -> str:
    candidates = []
    if location_value:
        candidates.append(location_value)
        parts = [part.strip() for part in location_value.split(",") if part.strip()]
        if parts:
            candidates.append(parts[-1])

        currency_match = re.search(r"all figures are in\s+.+?\(([A-Z]{3})\)", text, flags=re.IGNORECASE)
    if currency_match:
        currency_code = currency_match.group(1).upper()
        currency_country_map = {
            "INR": "IN",
            "GBP": "GB",
            "AED": "AE",
            "SGD": "SG",
            "AUD": "AU",
            "CAD": "CA",
        }
        mapped = currency_country_map.get(currency_code)
        if mapped:
            candidates.append(mapped)

    for candidate in candidates:
        resolved = resolve_iso2(candidate)
        if resolved:
            return resolved
    return ""


def _clean_company_name(value: str) -> str:
    text = value.strip()
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+date:\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+candidate signature\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+pune.*$", "", text, flags=re.IGNORECASE)
    return text.strip(" ,:-")


def _parse_money_value(raw: str) -> float | None:
    if not raw:
        return None

    text = raw.strip().lower()
    multiplier = 1.0

    if "crore" in text:
        multiplier = 10_000_000.0
    elif "lakh" in text or "lpa" in text:
        multiplier = 100_000.0
    elif "million" in text or re.search(r"\bmn\b", text):
        multiplier = 1_000_000.0

    numeric = re.sub(r"[^0-9.,]", "", text)
    if not numeric:
        return None

    if numeric.count(",") > 0 and numeric.count(".") == 0:
        numeric = numeric.replace(",", "")
    elif numeric.count(",") > 0 and numeric.count(".") > 0:
        numeric = numeric.replace(",", "")

    try:
        return round(float(numeric) * multiplier, 2)
    except ValueError:
        return None


def _format_money(amount: float | None, currency_code: str) -> str:
    if amount is None:
        return ""
    prefix = currency_code or ""
    return f"{prefix} {amount:,.2f}".strip()


def _compute_completeness(fields: dict[str, Any]) -> int:
    important = [
        "job_title",
        "location",
        "country_code",
        "currency_code",
        "base_salary",
        "total_ctc",
        "joining_bonus",
        "probation_period",
        "notice_period",
    ]
    bonus_present = not _is_missing_value(fields.get("annual_bonus_fixed")) or not _is_missing_value(fields.get("annual_bonus_percent"))
    if bonus_present:
        important.append("annual_bonus_percent")
    found = sum(0 if _is_missing_value(fields.get(key)) else 1 for key in important)
    return int(round((found / len(important)) * 100))


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False
