from __future__ import annotations

from typing import Any

import streamlit as st
from app.theme import get_gauge_colors, get_token

from .exporters import (
    build_interview_prep_csv,
    build_interview_prep_docx,
    build_interview_prep_pdf,
)
from .loader import IALoadError, load_question_set, load_registry_bundle
from .scoring import score_question_set
from .timer import build_attempt, finalize_attempt, render_timer_panel


ACTIVE_ATTEMPT_KEY = "ia_active_attempt"
LAST_RESULT_KEY = "ia_last_result"
LAST_SET_KEY = "ia_last_loaded_set_id"
QUESTION_KEYS_KEY = "ia_question_widget_keys"


def _result_band_color(score: int) -> str:
    gauge = get_gauge_colors()
    if score >= 80:
        return gauge["safe"]
    if score >= 60:
        return gauge["warn"]
    return gauge["danger"]


def _result_ring_html(score: float, label: str, note: str, center_caption: str) -> str:
    ring_color = _result_band_color(int(score))
    track = get_token("border_subtle")
    text_main = get_token("text_primary")
    text_muted = get_token("text_secondary")
    clamped = max(0, min(100, int(round(score))))
    return (
        f"<div style='display:flex;justify-content:flex-start;width:100%;'>"
        f"<div style='display:flex;flex-direction:column;align-items:center;"
        f"background:linear-gradient(135deg,{get_token('util_card_start')} 0%,{get_token('util_card_end')} 100%);"
        f"border:1px solid {get_token('util_card_border')};border-radius:14px;padding:18px 18px 14px 18px;"
        f"width:min(100%, 280px);min-width:240px;'>"
        f"<div style='font-size:12px;color:{text_muted};font-weight:600;letter-spacing:0.4px;margin-bottom:10px;'>{label}</div>"
        f"<div style='width:138px;height:138px;border-radius:50%;"
        f"background:conic-gradient({ring_color} 0 {clamped}%, {track} {clamped}% 100%);"
        f"display:flex;align-items:center;justify-content:center;'>"
        f"<div style='width:102px;height:102px;border-radius:50%;background:{get_token('surface_raised')};"
        f"display:flex;flex-direction:column;align-items:center;justify-content:center;"
        f"border:1px solid {get_token('border_subtle')}'>"
        f"<div style='color:{ring_color};font-size:28px;font-weight:700;line-height:1;'>{clamped}%</div>"
        f"<div style='color:{text_muted};font-size:11px;margin-top:6px;'>{center_caption}</div>"
        f"</div></div>"
        f"<div style='color:{text_main};font-size:13px;font-weight:600;text-align:center;line-height:1.35;margin-top:12px;max-width:180px;'>{note}</div>"
        f"</div></div>"
    )


def _result_bar_html(label: str, score: float, note: str, value_label: str | None = None) -> str:
    color = _result_band_color(int(score))
    track = get_token("border_subtle")
    text_main = get_token("text_primary")
    text_muted = get_token("text_secondary")
    clamped = max(0, min(100, int(round(score))))
    right_text = value_label or f"{clamped}%"
    return (
        f"<div style='margin:8px 0 14px 0;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:6px;'>"
        f"<span style='color:{text_main};font-size:13px;font-weight:600;'>{label}</span>"
        f"<span style='color:{color};font-size:13px;font-weight:700;'>{right_text}</span>"
        f"</div>"
        f"<div style='background:{track};border-radius:999px;height:8px;width:100%;overflow:hidden;'>"
        f"<div style='background:{color};width:{clamped}%;height:8px;border-radius:999px;'></div>"
        f"</div>"
        f"<div style='color:{text_muted};font-size:12px;line-height:1.45;margin-top:6px;'>{note}</div>"
        f"</div>"
    )


def _result_summary_html(
    percentage: float,
    outcome_text: str,
    score_note: str,
    answered_count: int,
    total_questions: int,
    completion_rate: float,
    correct_count: int,
    incorrect_count: int,
    skipped_count: int,
    correct_rate: float,
    pass_percent: float,
    pass_progress: float,
) -> str:
    return (
        f"<div style='display:flex;gap:20px;align-items:center;flex-wrap:wrap;width:100%;'>"
        f"<div style='flex:0 1 280px;min-width:240px;'>"
        f"{_result_ring_html(percentage, 'Overall Attempt Result', outcome_text, 'Score')}"
        f"</div>"
        f"<div style='flex:1 1 420px;min-width:320px;'>"
        f"{_result_bar_html('Score Percentage', percentage, score_note, f'{percentage:.1f}%')}"
        f"{_result_bar_html('Completion Rate', completion_rate, f'You answered {answered_count} of {total_questions} questions in this attempt.', f'{answered_count}/{total_questions}')}"
        f"{_result_bar_html('Correct Answer Rate', correct_rate, f'{correct_count} correct, {incorrect_count} incorrect, and {skipped_count} skipped.', f'{correct_count}/{total_questions}')}"
        f"{_result_bar_html('Pass Threshold Progress', pass_progress, f'The current set expects {pass_percent:.0f}% for a pass outcome.', f'{pass_percent:.0f}% target')}"
        f"</div>"
        f"</div>"
    )


def _registry_filters(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    def values_for(key: str) -> list[str]:
        return sorted({entry.get(key, "General") for entry in entries if entry.get(key)})

    return {
        "category": values_for("category"),
        "role_family": values_for("role_family"),
        "difficulty": values_for("difficulty"),
    }


def _safe_reset_answer_widgets() -> None:
    keys = st.session_state.get(QUESTION_KEYS_KEY, [])
    for key in keys:
        st.session_state.pop(key, None)
    st.session_state[QUESTION_KEYS_KEY] = []


def _make_question_widget_key(set_id: str, question_id: str) -> str:
    return f"ia_answer__{set_id}__{question_id}"


def _question_card_header(index: int, total: int, question: dict[str, Any]) -> None:
    badge_parts = [f"Question {index} of {total}"]
    if question.get("topic"):
        badge_parts.append(question["topic"])
    if question.get("difficulty"):
        badge_parts.append(question["difficulty"])
    badge_text = " | ".join(badge_parts)
    st.markdown(f"**{badge_text}**")
    st.write(question["prompt"])


def _render_single_question(question: dict[str, Any], set_id: str, index: int, total: int) -> None:
    widget_key = _make_question_widget_key(set_id, question["id"])
    tracked_keys = st.session_state.setdefault(QUESTION_KEYS_KEY, [])
    if widget_key not in tracked_keys:
        tracked_keys.append(widget_key)

    with st.container(border=True):
        _question_card_header(index=index, total=total, question=question)

        if question["type"] == "single_choice":
            options = [option["id"] for option in question["options"]]
            labels = {option["id"]: option["label"] for option in question["options"]}
            st.radio(
                "Select one answer",
                options=options,
                key=widget_key,
                format_func=lambda option_id: labels.get(option_id, option_id),
                index=None,
            )
        elif question["type"] == "multiple_choice":
            st.multiselect(
                "Select all that apply",
                options=[option["id"] for option in question["options"]],
                key=widget_key,
                format_func=lambda option_id: next(
                    (option["label"] for option in question["options"] if option["id"] == option_id),
                    option_id,
                ),
            )
        elif question["type"] == "dropdown":
            select_options = ["__ia_select__"] + [option["id"] for option in question["options"]]
            st.selectbox(
                "Choose an answer",
                options=select_options,
                key=widget_key,
                format_func=lambda option_id: "Select an option" if option_id == "__ia_select__" else next(
                    (option["label"] for option in question["options"] if option["id"] == option_id),
                    option_id,
                ),
            )
        elif question["type"] == "true_false":
            st.radio(
                "Choose one",
                options=["true", "false"],
                key=widget_key,
                format_func=lambda option_id: "True" if option_id == "true" else "False",
                index=None,
            )
        elif question["type"] == "numeric_input":
            st.text_input(
                "Enter your answer",
                key=widget_key,
                placeholder=question.get("placeholder") or "Type a numeric answer",
            )
        elif question["type"] == "text_input":
            st.text_area(
                "Enter your answer",
                key=widget_key,
                height=100,
                placeholder=question.get("placeholder") or "Type your answer",
            )


def _collect_answers(question_set: dict[str, Any]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    for section in question_set.get("sections", []):
        for question in section.get("questions", []):
            widget_key = _make_question_widget_key(question_set["set_id"], question["id"])
            value = st.session_state.get(widget_key)
            if question["type"] == "dropdown" and value == "__ia_select__":
                value = ""
            answers[question["id"]] = value
    return answers


def _render_set_overview(entry: dict[str, Any], question_set: dict[str, Any]) -> None:
    left, mid, right = st.columns(3)
    left.metric("Questions", question_set["question_count"])
    mid.metric("Difficulty", question_set["difficulty"])
    right.metric("Estimated Time", f"{entry.get('estimated_minutes') or question_set.get('estimated_minutes') or 0} min")

    if entry.get("description"):
        st.write(entry["description"])
    elif question_set.get("description"):
        st.write(question_set["description"])

    instructions = question_set.get("instructions", [])
    if instructions:
        with st.expander("How this set works", expanded=True):
            for item in instructions:
                st.write(f"- {item}")


def _render_results(result: dict[str, Any], review_settings: dict[str, Any]) -> None:
    st.subheader("Results")
    total_questions = max(1, len(result.get("question_results", [])))
    answered_count = max(0, total_questions - int(result["skipped_count"]))
    completion_rate = (answered_count / total_questions) * 100
    correct_rate = (int(result["correct_count"]) / total_questions) * 100
    pass_progress = (
        min(100.0, (float(result["percentage"]) / float(result["pass_percent"])) * 100.0)
        if float(result["pass_percent"]) > 0
        else 100.0
    )
    outcome_text = "Pass" if result["percentage"] >= result["pass_percent"] else "Review Needed"
    outcome_note = (
        f"Scored {result['total_obtained']:.2f} out of {result['total_marks']:.2f} marks."
        if outcome_text == "Pass"
        else f"Scored {result['total_obtained']:.2f} out of {result['total_marks']:.2f} marks and missed the current target."
    )

    st.markdown(
        _result_summary_html(
            float(result["percentage"]),
            outcome_text,
            outcome_note,
            answered_count,
            total_questions,
            completion_rate,
            int(result["correct_count"]),
            int(result["incorrect_count"]),
            int(result["skipped_count"]),
            correct_rate,
            float(result["pass_percent"]),
            pass_progress,
        ),
        unsafe_allow_html=True,
    )

    timer_snapshot = result.get("timer_snapshot", {})
    if timer_snapshot.get("timer_enabled"):
        st.write(
            f"Time used: {timer_snapshot['elapsed_seconds'] // 60:d} min {timer_snapshot['elapsed_seconds'] % 60:02d} sec"
        )
        if timer_snapshot.get("expired"):
            st.warning("This attempt exceeded the set time limit before submission.")

    st.subheader("Section Summary")
    for section in result.get("section_summary", []):
        section_score = (
            (float(section["obtained"]) / float(section["marks"])) * 100.0
            if float(section["marks"]) > 0
            else 0.0
        )
        header_col, meta_col = st.columns([1.4, 1], vertical_alignment="center")
        with header_col:
            st.markdown(
                _result_bar_html(
                    section["section_title"],
                    section_score,
                    (
                        f"Answered {max(0, int(section['questions']) - int(section['skipped']))} of {section['questions']} questions "
                        f"and earned {section['obtained']:.2f} out of {section['marks']:.2f} marks."
                    ),
                    f"{section['obtained']:.2f} / {section['marks']:.2f}",
                ),
                unsafe_allow_html=True,
            )
        with meta_col:
            mini1, mini2, mini3 = st.columns(3)
            mini1.metric("Correct", section["correct"])
            mini2.metric("Skipped", section["skipped"])
            mini3.metric("Questions", section["questions"])

    st.subheader("Answer Review")
    for question in result.get("question_results", []):
        with st.container(border=True):
            st.write(question["prompt"])
            if question["is_correct"]:
                st.success(f"Your answer: {question['user_answer_display']}")
            elif question["is_skipped"]:
                st.info("This question was skipped.")
            else:
                st.error(f"Your answer: {question['user_answer_display']}")

            if review_settings.get("show_correct_answers", True):
                st.write(f"Correct answer: {question['correct_answer_display']}")
            if review_settings.get("show_explanations", True) and question.get("explanation"):
                st.write(f"Explanation: {question['explanation']}")


def _render_export_section(entry: dict[str, Any], result: dict[str, Any], review_settings: dict[str, Any]) -> None:
    st.subheader("Download Results")
    st.caption(
        "Save this completed attempt for review, submission notes, or offline practice tracking."
    )

    csv_bytes = build_interview_prep_csv(result, review_settings)
    pdf_bytes = build_interview_prep_pdf(entry, result, review_settings)
    docx_bytes = build_interview_prep_docx(entry, result, review_settings)

    cols = st.columns(3 if docx_bytes is not None else 2)
    file_stub = f"interview_prep_{result.get('set_id', 'attempt')}"

    with cols[0]:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"{file_stub}.csv",
            mime="text/csv",
            key=f"{file_stub}_csv_download",
            width="stretch",
        )
    with cols[1]:
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{file_stub}.pdf",
            mime="application/pdf",
            key=f"{file_stub}_pdf_download",
            width="stretch",
        )

    if docx_bytes is not None:
        with cols[2]:
            st.download_button(
                "Download DOCX",
                data=docx_bytes,
                file_name=f"{file_stub}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"{file_stub}_docx_download",
                width="stretch",
            )


def render_interview_prep() -> None:
    st.title("Interview Prep")
    st.write(
        "Practice aptitude and interview question sets in one place. Choose a set, start a timed or untimed attempt, "
        "and review your score with answer explanations."
    )

    try:
        registry_bundle = load_registry_bundle()
    except (IALoadError, OSError, ValueError) as exc:
        st.error(f"Interview Prep could not be loaded. {exc}")
        return

    if registry_bundle["errors"]:
        st.error("Interview Prep is missing required configuration and could not be opened.")
        for item in registry_bundle["errors"]:
            st.write(f"- {item}")
        return

    entries = registry_bundle["entries"]
    if not entries:
        st.info("No practice sets are currently available.")
        return

    filters = _registry_filters(entries)
    top_cols = st.columns(4)
    selected_category = top_cols[0].selectbox("Category", ["All"] + filters["category"])
    selected_role = top_cols[1].selectbox("Role Focus", ["All"] + filters["role_family"])
    selected_difficulty = top_cols[2].selectbox("Difficulty", ["All"] + filters["difficulty"])
    selected_sort = top_cols[3].selectbox("Sort By", ["Recommended", "Title", "Difficulty", "Estimated Time"])

    filtered_entries = [
        entry
        for entry in entries
        if (selected_category == "All" or entry["category"] == selected_category)
        and (selected_role == "All" or entry["role_family"] == selected_role)
        and (selected_difficulty == "All" or entry["difficulty"] == selected_difficulty)
    ]

    if selected_sort == "Title":
        filtered_entries.sort(key=lambda item: item["title"])
    elif selected_sort == "Difficulty":
        filtered_entries.sort(key=lambda item: (item["difficulty"], item["title"]))
    elif selected_sort == "Estimated Time":
        filtered_entries.sort(key=lambda item: (item["estimated_minutes"], item["title"]))

    if not filtered_entries:
        st.info("No practice sets match the current filters.")
        return

    set_labels = [
        f"{entry['title']} - {entry['difficulty']} - {entry['question_count']} questions"
        for entry in filtered_entries
    ]
    selected_label = st.selectbox("Choose a practice set", set_labels)
    selected_entry = filtered_entries[set_labels.index(selected_label)]

    try:
        set_bundle = load_question_set(selected_entry)
    except (IALoadError, OSError, ValueError) as exc:
        st.error(f"The selected practice set could not be opened. {exc}")
        return

    if set_bundle["errors"]:
        st.error("The selected practice set contains invalid question data.")
        for item in set_bundle["errors"]:
            st.write(f"- {item}")
        return

    question_set = set_bundle["payload"]
    _render_set_overview(selected_entry, question_set)

    current_set_id = question_set["set_id"]
    if st.session_state.get(LAST_SET_KEY) != current_set_id:
        st.session_state[LAST_SET_KEY] = current_set_id
        st.session_state.pop(ACTIVE_ATTEMPT_KEY, None)
        st.session_state.pop(LAST_RESULT_KEY, None)
        _safe_reset_answer_widgets()

    settings_cols = st.columns([1.2, 1.2, 1, 1])
    timer_supported = bool(question_set.get("timer", {}).get("enabled"))
    timed_mode = settings_cols[0].toggle(
        "Timed Attempt",
        value=timer_supported,
        disabled=not timer_supported,
        help="Use the configured set timer when the set supports timed practice.",
    )
    show_explanations = settings_cols[1].toggle(
        "Show Explanations",
        value=bool(question_set.get("review", {}).get("show_explanations", True)),
        help="Display explanations during answer review after you submit.",
    )

    start_col, reset_col = settings_cols[2], settings_cols[3]
    if start_col.button("Start Practice Set", type="primary", width="stretch"):
        _safe_reset_answer_widgets()
        st.session_state[ACTIVE_ATTEMPT_KEY] = build_attempt(question_set, timed_mode=timed_mode)
        st.session_state.pop(LAST_RESULT_KEY, None)
        st.rerun()

    active_attempt = st.session_state.get(ACTIVE_ATTEMPT_KEY)
    same_set_active = bool(active_attempt and active_attempt.get("set_id") == current_set_id)

    if reset_col.button("Reset Current Attempt", width="stretch", disabled=not same_set_active):
        _safe_reset_answer_widgets()
        st.session_state.pop(ACTIVE_ATTEMPT_KEY, None)
        st.session_state.pop(LAST_RESULT_KEY, None)
        st.rerun()

    if same_set_active and active_attempt.get("status") == "in_progress":
        render_timer_panel(ACTIVE_ATTEMPT_KEY)
        st.subheader("Questions")

        total_questions = question_set["question_count"]
        running_index = 0
        with st.form(key=f"ia_form__{current_set_id}"):
            for section in question_set.get("sections", []):
                st.markdown(f"### {section['title']}")
                if section.get("description"):
                    st.write(section["description"])
                for question in section.get("questions", []):
                    running_index += 1
                    _render_single_question(
                        question=question,
                        set_id=current_set_id,
                        index=running_index,
                        total=total_questions,
                    )

            submitted = st.form_submit_button("Submit Answers", type="primary", width="stretch")

        if submitted:
            attempt_after_submit = finalize_attempt(active_attempt)
            st.session_state[ACTIVE_ATTEMPT_KEY] = attempt_after_submit
            answers = _collect_answers(question_set)
            result = score_question_set(question_set, answers, attempt_after_submit)
            result["review_settings"] = {
                "show_correct_answers": bool(question_set.get("review", {}).get("show_correct_answers", True)),
                "show_explanations": bool(show_explanations),
            }
            st.session_state[LAST_RESULT_KEY] = result
            st.rerun()

    last_result = st.session_state.get(LAST_RESULT_KEY)
    if last_result and last_result.get("set_id") == current_set_id:
        _render_results(last_result, last_result.get("review_settings", question_set.get("review", {})))
        st.divider()
        _render_export_section(
            selected_entry,
            last_result,
            last_result.get("review_settings", question_set.get("review", {})),
        )
    elif not same_set_active:
        st.info("Choose a set and start an attempt to begin practicing.")
