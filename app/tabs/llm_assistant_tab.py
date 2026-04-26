from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.core.auth import get_logged_in_user
from app.local_llm.client import LocalLLMError, LocalLLMTimeoutError
from app.local_llm.config import LocalLLMConfig
from app.local_llm.exporters import export_conversation_pdf, export_message_pdf
from app.local_llm.knowledge import APP_HELP_TEXT
from app.local_llm.service import (
    get_backend_label,
    generate_assistant_reply,
    is_local_llm_available,
    list_assistant_models,
)
from app.local_llm.deployment import is_local_runtime
from app.local_llm.storage_router import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_messages,
    init_chat_storage,
    list_conversations,
    record_export,
    update_conversation_meta,
)


ASSISTANT_MODES = [
    "App Help",
    "Prediction Companion",
    "Negotiation Assistant",
    "Resume Assistant",
    "Report Writer",
]

ASSISTANT_TONES = [
    "Professional and grounded",
    "Formal and concise",
    "Warm and collaborative",
]

PERFORMANCE_PROFILES = [
    "Fast",
    "Balanced",
    "Detailed",
]

QUICK_PROMPTS = {
    "App Help": [
        "How should I use batch prediction correctly in this app?",
        "What are the main limitations of SalaryScope for an academic demo?",
    ],
    "Prediction Companion": [
        "Explain the latest prediction in simple terms without changing the estimate.",
        "What does the salary range or context shown by the app mean?",
        "Give me cautious negotiation tips based on the latest prediction.",
        "What kind of job titles are close to this role, and how should I describe them carefully?",
    ],
    "Negotiation Assistant": [
        "Draft a polite salary negotiation email based on the latest SalaryScope estimate.",
        "Write a short recruiter call script aligned with the displayed prediction.",
    ],
    "Resume Assistant": [
        "Summarize the latest resume analysis for a recruiter.",
        "Write a short strengths summary from the extracted resume information.",
    ],
    "Report Writer": [
        "Write a concise report-ready interpretation of the latest prediction.",
        "Create a short narrative summary suitable for a PDF appendix.",
    ],
}


def _format_salary(amount) -> str:
    try:
        return f"${float(amount):,.2f}"
    except Exception:
        return str(amount)


def _current_username() -> str:
    username = get_logged_in_user()
    if username:
        return username
    return "local_anonymous"


def _conversation_label(item: dict) -> str:
    updated = str(item.get("updated_at", ""))
    stamp = updated.replace("T", " ")[:16] if updated else ""
    return f"{item['title']} [{item['mode']}] {stamp}".strip()


@st.cache_data(ttl=20, show_spinner=False)
def _cached_llm_status() -> tuple[bool, str]:
    return is_local_llm_available()


@st.cache_data(ttl=20, show_spinner=False)
def _cached_model_options() -> list[str]:
    return list_assistant_models()


def _trim_text(value: str, limit: int = 800) -> str:
    value = str(value or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + " ..."


def _compact_context_payload(payload: dict) -> dict:
    compact = {}
    for key, value in (payload or {}).items():
        if key in {"prediction_data", "input_details", "app_help_text"}:
            continue
        if isinstance(value, str):
            compact[key] = _trim_text(value, 500)
        else:
            compact[key] = value
    return compact


def _messages_signature(messages: list[dict]) -> tuple:
    return tuple(
        (m.get("id"), m.get("role"), m.get("created_at"))
        for m in messages
    )


@st.cache_data(show_spinner=False)
def _cached_conversation_pdf(title: str, subtitle: str, messages: tuple[tuple, ...], full_messages: tuple[tuple[str, str, str], ...]) -> bytes:
    materialized = [
        {"role": role, "created_at": created_at, "content": content}
        for role, created_at, content in full_messages
    ]
    return export_conversation_pdf(title=title, subtitle=subtitle, messages=materialized)


@st.cache_data(show_spinner=False)
def _cached_reply_pdf(title: str, subtitle: str, content: str) -> bytes:
    return export_message_pdf(title=title, subtitle=subtitle, content=content)


def _get_manual_prediction_context() -> dict | None:
    data = st.session_state.get("manual_prediction_result")
    if not data:
        return None

    input_details = data.get("input_details", {}) or {}
    prediction = data.get("prediction")
    lower_bound = data.get("lower_bound")
    upper_bound = data.get("upper_bound")

    extra_notes = []
    if data.get("salary_band_label"):
        extra_notes.append(f"Salary level: {data['salary_band_label']}")
    if data.get("career_stage_label"):
        extra_notes.append(f"Career stage: {data['career_stage_label']}")

    location = (
        input_details.get("Country")
        or input_details.get("Company Location")
        or input_details.get("Employee Residence")
        or "Not provided"
    )
    years_experience = (
        input_details.get("Years of Experience")
        or input_details.get("Experience Level")
        or "Not provided"
    )

    return {
        "source": "manual_prediction",
        "label": "Latest Manual Prediction",
        "job_title": input_details.get("Job Title", "Not provided"),
        "location": location,
        "years_experience": str(years_experience),
        "predicted_salary_text": f"{_format_salary(prediction)} annual salary estimate from SalaryScope",
        "prediction_range_text": (
            f"{_format_salary(lower_bound)} to {_format_salary(upper_bound)}"
            if lower_bound is not None and upper_bound is not None else ""
        ),
        "extra_context": " | ".join(extra_notes) if extra_notes else "None",
    }


def _get_resume_prediction_context() -> dict | None:
    data = st.session_state.get("resume_prediction_result")
    if data:
        input_details = data.get("input_details", {}) or {}
        prediction = data.get("prediction")
        lower_bound = data.get("lower_bound")
        upper_bound = data.get("upper_bound")
        extra_notes = []
        if data.get("salary_band_label"):
            extra_notes.append(f"Salary level: {data['salary_band_label']}")
        if data.get("career_stage_label"):
            extra_notes.append(f"Career stage: {data['career_stage_label']}")
        if input_details.get("Resume Score"):
            extra_notes.append(f"Resume score: {input_details['Resume Score']}")

        return {
            "source": "resume_prediction_app1",
            "label": "Latest Resume Prediction (Model 1)",
            "job_title": input_details.get("Job Title", "Not provided"),
            "location": input_details.get("Country", "Not provided"),
            "years_experience": str(input_details.get("Years of Experience", "Not provided")),
            "predicted_salary_text": f"{_format_salary(prediction)} annual salary estimate from SalaryScope",
            "prediction_range_text": (
                f"{_format_salary(lower_bound)} to {_format_salary(upper_bound)}"
                if lower_bound is not None and upper_bound is not None else ""
            ),
            "extra_context": " | ".join(extra_notes) if extra_notes else "None",
            "resume_text": st.session_state.get("resume_text", ""),
            "candidate_name": st.session_state.get("username", "Candidate"),
            "education": input_details.get("Education Level", "Not provided"),
            "skills_csv": input_details.get("Detected Skills", "Not provided"),
            "target_role": input_details.get("Job Title", "Not provided"),
        }

    data_a2 = st.session_state.get("resume_prediction_result_a2")
    if data_a2:
        input_details_a2 = data_a2.get("input_details_a2", {}) or {}
        prediction_a2 = data_a2.get("prediction_a2")
        extra_notes_a2 = []
        if input_details_a2.get("Resume Score"):
            extra_notes_a2.append(f"Resume score: {input_details_a2['Resume Score']}")
        if input_details_a2.get("Work Mode"):
            extra_notes_a2.append(f"Work mode: {input_details_a2['Work Mode']}")

        return {
            "source": "resume_prediction_app2",
            "label": "Latest Resume Prediction (Model 2)",
            "job_title": input_details_a2.get("Job Title", "Not provided"),
            "location": input_details_a2.get("Company Location", "Not provided"),
            "years_experience": str(input_details_a2.get("Experience Level", "Not provided")),
            "predicted_salary_text": f"{_format_salary(prediction_a2)} annual salary estimate from SalaryScope",
            "extra_context": " | ".join(extra_notes_a2) if extra_notes_a2 else "None",
            "resume_text": st.session_state.get("resume_text_a2", ""),
            "candidate_name": st.session_state.get("username", "Candidate"),
            "education": "Not provided",
            "skills_csv": input_details_a2.get("Detected Skills", "Not provided"),
            "target_role": input_details_a2.get("Job Title", "Not provided"),
        }
    return None


def _build_available_contexts() -> dict[str, dict]:
    contexts = {"General App Context": {"source": "app_help", "label": "General App Context", "app_help_text": APP_HELP_TEXT}}
    manual = _get_manual_prediction_context()
    resume = _get_resume_prediction_context()
    if manual:
        contexts[manual["label"]] = manual
    if resume:
        contexts[resume["label"]] = resume
    return contexts


def _derive_context_for_mode(mode: str, selected_context: dict) -> tuple[dict, str]:
    base = dict(selected_context or {})
    context_note = ""

    if mode == "App Help":
        return {
            "assistant_scope": "SalaryScope app help",
            "app_help_text": APP_HELP_TEXT,
            "selected_context_label": base.get("label", "General App Context"),
        }, "Focus on workflows, supported features, and limitations."

    if mode == "Prediction Companion":
        context_note = "Explain the displayed app result clearly, but do not challenge the estimate."
        return {
            "assistant_scope": "Prediction explanation",
            "selected_context_label": base.get("label", "No specific prediction context"),
            "job_title": base.get("job_title"),
            "location": base.get("location"),
            "years_experience": base.get("years_experience"),
            "predicted_salary_text": base.get("predicted_salary_text"),
            "prediction_range_text": base.get("prediction_range_text"),
            "extra_context": base.get("extra_context"),
        }, context_note

    if mode == "Negotiation Assistant":
        context_note = "Draft negotiation communication aligned with the displayed estimate and user profile."
        return {
            "assistant_scope": "Negotiation drafting",
            "selected_context_label": base.get("label", "Manual context"),
            "job_title": base.get("job_title"),
            "location": base.get("location"),
            "years_experience": base.get("years_experience"),
            "predicted_salary_text": base.get("predicted_salary_text"),
            "extra_context": base.get("extra_context"),
        }, context_note

    if mode == "Resume Assistant":
        context_note = "Summarize resume-related content and extracted information in grounded language."
        return {
            "assistant_scope": "Resume summary and drafting",
            "selected_context_label": base.get("label", "Resume context"),
            "candidate_name": base.get("candidate_name"),
            "target_role": base.get("target_role") or base.get("job_title"),
            "education": base.get("education"),
            "skills_csv": base.get("skills_csv"),
            "resume_text": base.get("resume_text"),
            "predicted_salary_text": base.get("predicted_salary_text"),
            "extra_context": base.get("extra_context"),
        }, context_note

    context_note = "Write concise narrative suitable for inclusion in a PDF appendix or report summary."
    return {
        "assistant_scope": "Report-ready narrative",
        "selected_context_label": base.get("label", "Available app context"),
        "job_title": base.get("job_title"),
        "location": base.get("location"),
        "years_experience": base.get("years_experience"),
        "predicted_salary_text": base.get("predicted_salary_text"),
        "prediction_range_text": base.get("prediction_range_text"),
        "extra_context": base.get("extra_context"),
    }, context_note


def _suggested_title(mode: str, user_message: str) -> str:
    prefix = {
        "App Help": "App Help",
        "Prediction Companion": "Prediction Chat",
        "Negotiation Assistant": "Negotiation Draft",
        "Resume Assistant": "Resume Chat",
        "Report Writer": "Report Draft",
    }.get(mode, "Assistant Chat")
    snippet = " ".join(user_message.strip().split())[:42]
    return f"{prefix}: {snippet}" if snippet else prefix


def _render_chat_history(messages: list[dict]) -> None:
    if not messages:
        st.info(
            "This conversation is empty. Use a quick prompt or type a question below to start."
        )
        return

    for message in messages:
        role = "assistant" if message.get("role") == "assistant" else "user"
        with st.chat_message(role):
            st.markdown(message.get("content", ""))
            created = str(message.get("created_at", ""))
            if created:
                st.caption(created.replace("T", " "))


def render_llm_assistant_tab():
    local_runtime = is_local_runtime()
    username = _current_username()
    is_authenticated = username != "local_anonymous"
    config = LocalLLMConfig.from_env()

    st.header(":material/smart_toy: AI Assistant")
    st.caption(
        "Grounded app assistance with persistent chat history, configurable model backends, and PDF export. "
        "The assistant supports SalaryScope outputs and workflows without replacing the ML models."
    )
    st.caption(
        "SalaryScope Assistant is AI and can make mistakes. Check important details before relying on them."
    )

    if not local_runtime and not is_authenticated:
        st.info(
            "Sign in to use the AI Assistant on Streamlit Cloud. Anonymous AI chat is disabled there so conversations can be tied to a real user account."
        )
        st.caption(
            "Local runs can still use the assistant without login for testing, but cloud usage requires authentication."
        )
        return

    init_chat_storage()

    available, status = _cached_llm_status()
    model_options = _cached_model_options() if available else [config.model]
    backend_label = get_backend_label()

    if "llm_active_conversation_id" not in st.session_state:
        st.session_state.llm_active_conversation_id = None
    if "llm_quick_prompt" not in st.session_state:
        st.session_state.llm_quick_prompt = ""

    top_a, top_b, top_c = st.columns([2, 1, 1])
    with top_a:
        if available:
            st.success(status)
        else:
            st.warning(status)
    with top_b:
        st.metric("Backend", backend_label)
    with top_c:
        st.metric("Chat Owner", username)

    st.info(
        "Use the assistant for app help, explanation, drafting, negotiation tips, job-title clarification, and careful recommendations based on the current SalaryScope workflow."
    )

    contexts = _build_available_contexts()
    conversations = list_conversations(username)

    if conversations and st.session_state.llm_active_conversation_id is None:
        st.session_state.llm_active_conversation_id = conversations[0]["id"]

    left_col, right_col = st.columns([1, 2.2], gap="large")

    with left_col:
        st.subheader("Assistant Controls")

        convo_options = {"Start a new conversation": None}
        for convo in conversations:
            convo_options[_conversation_label(convo)] = convo["id"]

        current_conv_id = st.session_state.llm_active_conversation_id
        default_label = "Start a new conversation"
        for label, cid in convo_options.items():
            if cid == current_conv_id:
                default_label = label
                break

        selected_label = st.selectbox(
            "Conversation",
            list(convo_options.keys()),
            index=list(convo_options.keys()).index(default_label),
            key="llm_conversation_select",
        )
        selected_conv_id = convo_options[selected_label]
        st.session_state.llm_active_conversation_id = selected_conv_id

        active_convo = get_conversation(username, selected_conv_id) if selected_conv_id else None

        default_mode = active_convo["mode"] if active_convo else "Prediction Companion"
        default_model = active_convo["model_name"] if active_convo and active_convo.get("model_name") else config.model
        default_tone = active_convo["tone"] if active_convo and active_convo.get("tone") else ASSISTANT_TONES[0]
        default_profile = st.session_state.get("llm_performance_profile", "Balanced")

        mode = st.selectbox(
            "Assistant Mode",
            ASSISTANT_MODES,
            index=ASSISTANT_MODES.index(default_mode) if default_mode in ASSISTANT_MODES else 0,
        )
        if local_runtime:
            selected_model = st.selectbox(
                "Model",
                model_options,
                index=model_options.index(default_model) if default_model in model_options else 0,
            )
        else:
            deployed_model = model_options[0] if model_options else default_model
            selected_model = deployed_model
            st.selectbox(
                "Cloud Model",
                [deployed_model],
                index=0,
                disabled=True,
                help="The free Hugging Face Space runs one deployed model at a time.",
            )
        tone = st.selectbox(
            "Tone",
            ASSISTANT_TONES,
            index=ASSISTANT_TONES.index(default_tone) if default_tone in ASSISTANT_TONES else 0,
        )
        performance_profile = st.selectbox(
            "Performance",
            PERFORMANCE_PROFILES,
            index=PERFORMANCE_PROFILES.index(default_profile) if default_profile in PERFORMANCE_PROFILES else 1,
            help="Fast keeps replies shorter and usually responds quicker on local hardware.",
        )
        st.session_state.llm_performance_profile = performance_profile

        context_keys = list(contexts.keys())
        preferred_context = "General App Context"
        if mode != "App Help":
            for candidate in (
                "Latest Manual Prediction",
                "Latest Resume Prediction (Model 1)",
                "Latest Resume Prediction (Model 2)",
            ):
                if candidate in contexts:
                    preferred_context = candidate
                    break
        context_label = st.selectbox(
            "Context",
            context_keys,
            index=context_keys.index(preferred_context) if preferred_context in context_keys else 0,
        )
        context_payload, context_note = _derive_context_for_mode(mode, contexts[context_label])

        st.markdown("**Quick Prompts**")
        for idx, prompt in enumerate(QUICK_PROMPTS.get(mode, [])):
            if st.button(prompt, width="stretch", key=f"llm_quick_{mode}_{idx}"):
                st.session_state.llm_quick_prompt = prompt

        st.divider()
        control_a, control_b = st.columns(2)
        with control_a:
            if st.button("New Chat", width="stretch", key="llm_new_chat"):
                st.session_state.llm_active_conversation_id = None
                st.rerun()
        with control_b:
            can_delete = selected_conv_id is not None
            if st.button("Delete Chat", width="stretch", key="llm_delete_chat", disabled=not can_delete):
                delete_conversation(username, selected_conv_id)
                st.session_state.llm_active_conversation_id = None
                st.rerun()

        st.divider()
        with st.expander("Current Context", expanded=False):
            st.json(_compact_context_payload(context_payload))

        with st.expander("Response Focus", expanded=False):
            st.write(context_note)
            st.caption(
                "Fast is best for app help and prediction explanation. "
                "Balanced is a good default. Detailed is best reserved for drafting tasks. "
                "On Streamlit Cloud, the assistant uses a smaller Space-friendly model and shorter outputs."
            )

    with right_col:
        active_messages = get_messages(username, selected_conv_id) if selected_conv_id else []
        _render_chat_history(active_messages)

        prompt_input = st.chat_input("Ask SalaryScope AI Assistant")
        with st.expander("Need a longer prompt?", expanded=False):
            st.caption(
                "Use this for multi-part questions, longer drafting requests, or when you want the assistant to respond in more detail."
            )
            composed_prompt = st.text_area(
                "Long prompt composer",
                key="llm_long_prompt",
                height=140,
                placeholder=(
                    "Example: Give me a negotiation email, three talking points, and two cautious career options "
                    "based on the latest prediction and current role context."
                ),
            )
            send_long_prompt = st.button("Send Long Prompt", key="llm_send_long_prompt", width="stretch")
        if send_long_prompt and composed_prompt.strip():
            prompt_input = composed_prompt.strip()
        if st.session_state.llm_quick_prompt:
            prompt_input = st.session_state.llm_quick_prompt
            st.session_state.llm_quick_prompt = ""

        if prompt_input:
            if not available:
                st.error(f"The configured assistant backend is not available right now. Status: {status}")
            else:
                conversation_id = selected_conv_id
                if conversation_id is None:
                    conversation_id = create_conversation(
                        username=username,
                        title=_suggested_title(mode, prompt_input),
                        mode=mode,
                        model_name=selected_model,
                        tone=tone,
                    )
                    st.session_state.llm_active_conversation_id = conversation_id
                else:
                    update_conversation_meta(
                        username,
                        conversation_id,
                        mode=mode,
                        model_name=selected_model,
                        tone=tone,
                    )
                    if len(active_messages) == 0:
                        update_conversation_meta(
                            username,
                            conversation_id,
                            title=_suggested_title(mode, prompt_input),
                        )

                history_before = get_messages(username, conversation_id)
                add_message(
                    username,
                    conversation_id,
                    role="user",
                    content=prompt_input,
                    context={"mode": mode, "context_payload": _compact_context_payload(context_payload)},
                )

                try:
                    spinner_text = "Generating assistant response..." if local_runtime else "Contacting Hugging Face assistant..."
                    with st.spinner(spinner_text):
                        result = generate_assistant_reply(
                            mode=mode,
                            user_message=prompt_input,
                            context_payload=context_payload,
                            recent_messages=history_before,
                            tone=tone,
                            model_name=selected_model,
                            context_note=context_note,
                            performance_profile=performance_profile,
                        )
                    add_message(
                        username,
                        conversation_id,
                        role="assistant",
                        content=result["content"],
                        context={
                            "mode": mode,
                            "model": result["model"],
                            "performance_profile": result.get("performance_profile", performance_profile),
                        },
                    )
                    st.rerun()
                except LocalLLMTimeoutError:
                    friendly = (
                        "The assistant took too long to respond. "
                        "Try again with `Performance = Fast`, use a shorter prompt, "
                        "or switch to a smaller model such as `llama3.2:1b`, `qwen2.5:0.5b`, or `smollm2:360m`."
                    )
                    st.warning(friendly)
                except LocalLLMError as exc:
                    st.error(
                        "The assistant could not complete this request. "
                        f"Details: {exc}"
                    )

        refreshed_conv_id = st.session_state.llm_active_conversation_id
        refreshed_messages = get_messages(username, refreshed_conv_id) if refreshed_conv_id else []
        refreshed_convo = get_conversation(username, refreshed_conv_id) if refreshed_conv_id else None

        st.divider()
        export_col1, export_col2 = st.columns(2)
        with export_col1:
            if refreshed_convo and refreshed_messages:
                subtitle = (
                    f"{refreshed_convo['mode']} · {refreshed_convo.get('model_name', config.model)} · "
                    f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                )
                convo_pdf = _cached_conversation_pdf(
                    title=refreshed_convo["title"],
                    subtitle=subtitle,
                    messages=_messages_signature(refreshed_messages),
                    full_messages=tuple(
                        (str(m.get("role", "")), str(m.get("created_at", "")), str(m.get("content", "")))
                        for m in refreshed_messages
                    ),
                )
                file_name = f"salaryscope_ai_chat_{refreshed_convo['id']}.pdf"
                clicked = st.download_button(
                    "Download Conversation PDF",
                    data=convo_pdf,
                    file_name=file_name,
                    mime="application/pdf",
                    width="stretch",
                )
                if clicked:
                    record_export(username, refreshed_convo["id"], export_type="conversation_pdf", file_name=file_name)
            else:
                st.button("Download Conversation PDF", width="stretch", disabled=True)

        with export_col2:
            last_assistant = None
            for item in reversed(refreshed_messages):
                if item.get("role") == "assistant":
                    last_assistant = item
                    break
            if refreshed_convo and last_assistant:
                single_pdf = _cached_reply_pdf(
                    title=refreshed_convo["title"],
                    subtitle=f"{refreshed_convo['mode']} · Last assistant reply",
                    content=last_assistant["content"],
                )
                message_file = f"salaryscope_ai_reply_{refreshed_convo['id']}.pdf"
                clicked = st.download_button(
                    "Download Last Reply PDF",
                    data=single_pdf,
                    file_name=message_file,
                    mime="application/pdf",
                    width="stretch",
                )
                if clicked:
                    record_export(username, refreshed_convo["id"], export_type="reply_pdf", file_name=message_file)
            else:
                st.button("Download Last Reply PDF", width="stretch", disabled=True)

        st.caption(
            "The assistant uses recent chat turns plus the selected app context. "
            "When Hugging Face chat storage is configured, logged-in users get separate persistent history there. "
            "Otherwise the assistant falls back to local SQLite."
        )
        if not local_runtime:
            st.caption(
                "Cloud mode is tuned for the free Hugging Face Space path, so responses stay shorter and the deployed model is fixed by Space settings."
            )
