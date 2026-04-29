from __future__ import annotations

from pathlib import Path
from typing import Any


SUPPORTED_QUESTION_TYPES = {
    "single_choice",
    "multiple_choice",
    "numeric_input",
    "text_input",
    "dropdown",
    "true_false",
}


def _as_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _normalize_options(question_type: str, options: Any) -> list[dict[str, str]]:
    if question_type == "true_false":
        return [
            {"id": "true", "label": "True"},
            {"id": "false", "label": "False"},
        ]

    normalized: list[dict[str, str]] = []
    if not isinstance(options, list):
        return normalized

    for index, option in enumerate(options, start=1):
        if isinstance(option, dict):
            option_id = str(option.get("id", "")).strip() or f"option_{index}"
            label = str(option.get("label", "")).strip()
        else:
            option_id = f"option_{index}"
            label = str(option).strip()
        if label:
            normalized.append({"id": option_id, "label": label})
    return normalized


def validate_registry_payload(payload: dict[str, Any], base_dir: Path) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    warnings: list[str] = []
    entries: list[dict[str, Any]] = []

    raw_entries = payload.get("sets")
    if not isinstance(raw_entries, list) or not raw_entries:
        errors.append("registry_ia.json must include a non-empty 'sets' array.")
        return errors, warnings, entries

    seen_ids: set[str] = set()
    for index, item in enumerate(raw_entries, start=1):
        if not isinstance(item, dict):
            errors.append(f"Registry entry {index} must be a JSON object.")
            continue

        set_id = str(item.get("set_id", "")).strip()
        title = str(item.get("title", "")).strip()
        file_name = str(item.get("file", "")).strip()
        if not set_id:
            errors.append(f"Registry entry {index} is missing 'set_id'.")
            continue
        if set_id in seen_ids:
            errors.append(f"Registry contains duplicate set_id '{set_id}'.")
            continue
        seen_ids.add(set_id)

        if not title:
            errors.append(f"Registry entry '{set_id}' is missing 'title'.")
        if not file_name:
            errors.append(f"Registry entry '{set_id}' is missing 'file'.")

        full_path = (base_dir / file_name).resolve()
        if base_dir not in full_path.parents and full_path != base_dir:
            errors.append(f"Registry entry '{set_id}' points outside the interview prep package.")
        elif not full_path.exists():
            errors.append(f"Registry entry '{set_id}' points to a missing file: {file_name}")

        entries.append(
            {
                "set_id": set_id,
                "title": title or set_id,
                "subtitle": str(item.get("subtitle", "")).strip(),
                "description": str(item.get("description", "")).strip(),
                "file": file_name,
                "category": str(item.get("category", "General")).strip() or "General",
                "role_family": str(item.get("role_family", "General")).strip() or "General",
                "difficulty": str(item.get("difficulty", "Mixed")).strip() or "Mixed",
                "estimated_minutes": int(item.get("estimated_minutes", 0) or 0),
                "question_count": int(item.get("question_count", 0) or 0),
                "enabled": bool(item.get("enabled", True)),
                "tags": _as_string_list(item.get("tags", [])),
                "sort_order": int(item.get("sort_order", index)),
                "ai_integration": item.get("ai_integration", {}),
            }
        )

    entries = [entry for entry in entries if entry.get("enabled", True)]
    entries.sort(key=lambda entry: (entry.get("sort_order", 0), entry.get("title", "")))
    return errors, warnings, entries


def validate_question_set_payload(payload: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    set_id = str(payload.get("set_id", "")).strip()
    title = str(payload.get("title", "")).strip()
    if not set_id:
        errors.append("Question set is missing 'set_id'.")
    if not title:
        errors.append("Question set is missing 'title'.")

    sections = payload.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("Question set must include at least one section.")
        return errors, warnings, payload

    normalized_sections: list[dict[str, Any]] = []
    seen_question_ids: set[str] = set()

    for section_index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            errors.append(f"Section {section_index} must be a JSON object.")
            continue

        section_id = str(section.get("id", "")).strip() or f"section_{section_index}"
        section_title = str(section.get("title", "")).strip() or f"Section {section_index}"
        raw_questions = section.get("questions")
        if not isinstance(raw_questions, list) or not raw_questions:
            errors.append(f"Section '{section_title}' must include at least one question.")
            continue

        normalized_questions: list[dict[str, Any]] = []
        for question_index, question in enumerate(raw_questions, start=1):
            if not isinstance(question, dict):
                errors.append(f"Question {question_index} in '{section_title}' must be a JSON object.")
                continue

            question_id = str(question.get("id", "")).strip()
            prompt = str(question.get("prompt", "")).strip()
            question_type = str(question.get("type", "")).strip()

            if not question_id:
                errors.append(f"A question in '{section_title}' is missing 'id'.")
                continue
            if question_id in seen_question_ids:
                errors.append(f"Duplicate question id '{question_id}' detected.")
                continue
            seen_question_ids.add(question_id)

            if not prompt:
                errors.append(f"Question '{question_id}' is missing 'prompt'.")
            if question_type not in SUPPORTED_QUESTION_TYPES:
                errors.append(f"Question '{question_id}' uses unsupported type '{question_type}'.")
                continue

            options = _normalize_options(question_type, question.get("options", []))
            if question_type in {"single_choice", "multiple_choice", "dropdown"} and len(options) < 2:
                errors.append(f"Question '{question_id}' needs at least two options.")

            correct_answer = question.get("correct_answer")
            accepted_answers = question.get("accepted_answers", [])

            if question_type in {"single_choice", "dropdown", "true_false"}:
                if correct_answer in (None, ""):
                    errors.append(f"Question '{question_id}' is missing 'correct_answer'.")
            elif question_type == "multiple_choice":
                if not isinstance(correct_answer, list) or not correct_answer:
                    errors.append(f"Question '{question_id}' must define 'correct_answer' as a non-empty list.")
            elif question_type == "numeric_input":
                if not isinstance(accepted_answers, list) or not accepted_answers:
                    errors.append(f"Question '{question_id}' must define 'accepted_answers' for numeric scoring.")
            elif question_type == "text_input":
                if not isinstance(accepted_answers, list) or not accepted_answers:
                    errors.append(f"Question '{question_id}' must define 'accepted_answers' for text scoring.")

            normalized_questions.append(
                {
                    "id": question_id,
                    "prompt": prompt,
                    "type": question_type,
                    "options": options,
                    "correct_answer": correct_answer,
                    "accepted_answers": accepted_answers,
                    "explanation": str(question.get("explanation", "")).strip(),
                    "marks": float(question.get("marks", payload.get("scoring", {}).get("default_marks", 1.0))),
                    "negative_marks": float(question.get("negative_marks", payload.get("scoring", {}).get("negative_marks", 0.0))),
                    "topic": str(question.get("topic", "")).strip(),
                    "difficulty": str(question.get("difficulty", payload.get("difficulty", "Mixed"))).strip(),
                    "case_sensitive": bool(question.get("case_sensitive", False)),
                    "tolerance": float(question.get("tolerance", 0.0)),
                    "placeholder": str(question.get("placeholder", "")).strip(),
                    "section_id": section_id,
                    "section_title": section_title,
                }
            )

        normalized_sections.append(
            {
                "id": section_id,
                "title": section_title,
                "description": str(section.get("description", "")).strip(),
                "questions": normalized_questions,
            }
        )

    question_count = sum(len(section["questions"]) for section in normalized_sections)
    if question_count == 0:
        errors.append("Question set does not contain any valid questions.")

    normalized = {
        "set_id": set_id,
        "title": title,
        "description": str(payload.get("description", "")).strip(),
        "instructions": _as_string_list(payload.get("instructions", [])),
        "category": str(payload.get("category", "General")).strip() or "General",
        "role_family": str(payload.get("role_family", "General")).strip() or "General",
        "difficulty": str(payload.get("difficulty", "Mixed")).strip() or "Mixed",
        "estimated_minutes": int(payload.get("estimated_minutes", 0) or 0),
        "timer": {
            "enabled": bool(payload.get("timer", {}).get("enabled", False)),
            "time_limit_seconds": int(payload.get("timer", {}).get("time_limit_seconds", 0) or 0),
            "enforce_on_submit": bool(payload.get("timer", {}).get("enforce_on_submit", True)),
        },
        "scoring": {
            "default_marks": float(payload.get("scoring", {}).get("default_marks", 1.0)),
            "negative_marks": float(payload.get("scoring", {}).get("negative_marks", 0.0)),
            "pass_percent": float(payload.get("scoring", {}).get("pass_percent", 0.0)),
        },
        "review": {
            "show_correct_answers": bool(payload.get("review", {}).get("show_correct_answers", True)),
            "show_explanations": bool(payload.get("review", {}).get("show_explanations", True)),
        },
        "ai_integration": payload.get("ai_integration", {}),
        "sections": normalized_sections,
        "question_count": question_count,
    }

    return errors, warnings, normalized
