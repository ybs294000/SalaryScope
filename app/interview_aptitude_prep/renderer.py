from __future__ import annotations

from typing import Any

import streamlit as st

from .loader import IALoadError, load_question_set, load_registry_bundle
from .scoring import score_question_set
from .timer import build_attempt, finalize_attempt, render_timer_panel


ACTIVE_ATTEMPT_KEY = "ia_active_attempt"
LAST_RESULT_KEY = "ia_last_result"
LAST_SET_KEY = "ia_last_loaded_set_id"
QUESTION_KEYS_KEY = "ia_question_widget_keys"


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
    row1 = st.columns(4)
    row1[0].metric("Score", f"{result['total_obtained']:.2f} / {result['total_marks']:.2f}")
    row1[1].metric("Percent", f"{result['percentage']:.1f}%")
    row1[2].metric("Correct", result["correct_count"])
    row1[3].metric("Skipped", result["skipped_count"])

    row2 = st.columns(3)
    row2[0].metric("Incorrect", result["incorrect_count"])
    row2[1].metric("Pass Mark", f"{result['pass_percent']:.0f}%")
    row2[2].metric("Outcome", "Pass" if result["percentage"] >= result["pass_percent"] else "Review Needed")

    timer_snapshot = result.get("timer_snapshot", {})
    if timer_snapshot.get("timer_enabled"):
        st.write(
            f"Time used: {timer_snapshot['elapsed_seconds'] // 60:d} min {timer_snapshot['elapsed_seconds'] % 60:02d} sec"
        )
        if timer_snapshot.get("expired"):
            st.warning("This attempt exceeded the set time limit before submission.")

    st.subheader("Section Summary")
    for section in result.get("section_summary", []):
        cols = st.columns(4)
        cols[0].metric(section["section_title"], f"{section['obtained']:.2f} / {section['marks']:.2f}")
        cols[1].metric("Correct", section["correct"])
        cols[2].metric("Skipped", section["skipped"])
        cols[3].metric("Questions", section["questions"])

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
    elif not same_set_active:
        st.info("Choose a set and start an attempt to begin practicing.")
