from __future__ import annotations

from typing import Any

from .timer import get_timer_snapshot


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalized_text(value: Any, case_sensitive: bool) -> str:
    text = _clean_text(value)
    return text if case_sensitive else text.casefold()


def _display_answer(question: dict[str, Any], answer: Any) -> str:
    if answer in (None, "", []):
        return "Skipped"

    if question["type"] == "multiple_choice":
        option_map = {option["id"]: option["label"] for option in question.get("options", [])}
        selected = [option_map.get(item, str(item)) for item in answer]
        return ", ".join(selected)

    if question["type"] in {"single_choice", "dropdown", "true_false"}:
        option_map = {option["id"]: option["label"] for option in question.get("options", [])}
        return option_map.get(answer, str(answer))

    return str(answer)


def _correct_answer_display(question: dict[str, Any]) -> str:
    if question["type"] in {"numeric_input", "text_input"}:
        accepted = question.get("accepted_answers", [])
        return ", ".join(str(item) for item in accepted)
    return _display_answer(question, question.get("correct_answer"))


def _score_single_choice(question: dict[str, Any], answer: Any) -> tuple[bool, bool]:
    if answer in (None, "", "__ia_select__"):
        return False, True
    return str(answer) == str(question.get("correct_answer")), False


def _score_multiple_choice(question: dict[str, Any], answer: Any) -> tuple[bool, bool]:
    if not answer:
        return False, True
    expected = set(str(item) for item in question.get("correct_answer", []))
    observed = set(str(item) for item in answer)
    return observed == expected, False


def _score_numeric(question: dict[str, Any], answer: Any) -> tuple[bool, bool]:
    text_value = _clean_text(answer)
    if not text_value:
        return False, True

    try:
        observed = float(text_value)
    except ValueError:
        return False, False

    tolerance = float(question.get("tolerance", 0.0))
    accepted = question.get("accepted_answers", [])
    for candidate in accepted:
        try:
            target = float(candidate)
        except (TypeError, ValueError):
            continue
        if abs(observed - target) <= tolerance:
            return True, False
    return False, False


def _score_text(question: dict[str, Any], answer: Any) -> tuple[bool, bool]:
    text_value = _clean_text(answer)
    if not text_value:
        return False, True

    case_sensitive = bool(question.get("case_sensitive", False))
    observed = _normalized_text(text_value, case_sensitive=case_sensitive)
    accepted = [
        _normalized_text(candidate, case_sensitive=case_sensitive)
        for candidate in question.get("accepted_answers", [])
    ]
    return observed in accepted, False


def evaluate_answer(question: dict[str, Any], answer: Any) -> dict[str, Any]:
    question_type = question["type"]
    score_map = {
        "single_choice": _score_single_choice,
        "dropdown": _score_single_choice,
        "true_false": _score_single_choice,
        "multiple_choice": _score_multiple_choice,
        "numeric_input": _score_numeric,
        "text_input": _score_text,
    }
    scorer = score_map[question_type]
    is_correct, is_skipped = scorer(question, answer)

    marks = float(question.get("marks", 1.0))
    negative_marks = float(question.get("negative_marks", 0.0))
    obtained = 0.0
    if is_correct:
        obtained = marks
    elif not is_skipped:
        obtained = -negative_marks

    return {
        "question_id": question["id"],
        "type": question_type,
        "prompt": question["prompt"],
        "user_answer": answer,
        "user_answer_display": _display_answer(question, answer),
        "correct_answer_display": _correct_answer_display(question),
        "is_correct": is_correct,
        "is_skipped": is_skipped,
        "marks": marks,
        "obtained": obtained,
        "explanation": question.get("explanation", ""),
        "section_id": question["section_id"],
        "section_title": question["section_title"],
        "topic": question.get("topic", ""),
    }


def score_question_set(question_set: dict[str, Any], answers: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    question_results: list[dict[str, Any]] = []
    section_summary: dict[str, dict[str, Any]] = {}
    total_marks = 0.0
    total_obtained = 0.0
    correct_count = 0
    skipped_count = 0

    for section in question_set.get("sections", []):
        summary = {
            "section_id": section["id"],
            "section_title": section["title"],
            "marks": 0.0,
            "obtained": 0.0,
            "correct": 0,
            "skipped": 0,
            "questions": 0,
        }

        for question in section.get("questions", []):
            result = evaluate_answer(question, answers.get(question["id"]))
            question_results.append(result)

            total_marks += result["marks"]
            total_obtained += result["obtained"]
            summary["marks"] += result["marks"]
            summary["obtained"] += result["obtained"]
            summary["questions"] += 1

            if result["is_correct"]:
                correct_count += 1
                summary["correct"] += 1
            if result["is_skipped"]:
                skipped_count += 1
                summary["skipped"] += 1

        section_summary[section["id"]] = summary

    timer_snapshot = get_timer_snapshot(attempt)
    percentage = 0.0 if total_marks <= 0 else max(0.0, total_obtained) / total_marks * 100.0
    total_questions = len(question_results)
    incorrect_count = total_questions - correct_count - skipped_count

    return {
        "set_id": question_set["set_id"],
        "title": question_set["title"],
        "question_results": question_results,
        "section_summary": list(section_summary.values()),
        "total_marks": total_marks,
        "total_obtained": total_obtained,
        "percentage": percentage,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "skipped_count": skipped_count,
        "total_questions": total_questions,
        "pass_percent": float(question_set.get("scoring", {}).get("pass_percent", 0.0)),
        "timer_snapshot": timer_snapshot,
    }
