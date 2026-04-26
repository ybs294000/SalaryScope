"""
Prompt builders for local LLM drafting tasks and chat assistant mode.
"""

from __future__ import annotations

import json
from textwrap import dedent

from .knowledge import APP_HELP_TEXT, MODE_HELP


def _json_block(data: dict | None) -> str:
    if not data:
        return "{}"
    return json.dumps(data, indent=2, ensure_ascii=True, sort_keys=True)


def build_resume_summary_prompts(
    *,
    candidate_name: str,
    target_role: str,
    years_experience: str,
    education: str,
    skills_csv: str,
    resume_text: str,
) -> tuple[str, str]:
    system_prompt = dedent(
        """
        You are a careful resume-writing assistant for an academic salary-analysis app.
        Write concise, professional output only from the information provided.
        Do not invent employers, degrees, projects, or achievements.
        If some information is missing, stay general instead of guessing.
        Keep the tone polished and recruiter-friendly.
        """
    ).strip()

    user_prompt = dedent(
        f"""
        Create two sections:
        1. A 4-6 line professional summary.
        2. Three short bullets titled "Key strengths".

        Constraints:
        - Use plain English.
        - Do not use hype words like "world-class" or "best-in-class".
        - Do not mention salary.
        - Ground the summary only in the provided resume information.

        Candidate name: {candidate_name or "Not provided"}
        Target role: {target_role or "Not provided"}
        Years of experience: {years_experience or "Not provided"}
        Education: {education or "Not provided"}
        Skills: {skills_csv or "Not provided"}

        Resume content:
        {resume_text.strip() or "No resume text provided."}
        """
    ).strip()
    return system_prompt, user_prompt


def build_negotiation_script_prompts(
    *,
    job_title: str,
    location: str,
    years_experience: str,
    predicted_salary_text: str,
    target_salary_text: str,
    negotiation_style: str,
    extra_context: str,
) -> tuple[str, str]:
    system_prompt = dedent(
        """
        You are a drafting assistant for salary negotiation communication.
        Generate practical, professional wording only.
        Do not claim legal authority, market certainty, percentile rankings,
        or guaranteed outcomes.
        The script must sound realistic for a candidate speaking to a recruiter
        or hiring manager.
        Treat all structured inputs from the app as the source of truth.
        Do not contradict, revise, challenge, or second-guess the provided
        salary prediction reference.
        """
    ).strip()

    user_prompt = dedent(
        f"""
        Create a negotiation package with these sections:
        1. Email draft
        2. Short call script
        3. Three talking points

        Constraints:
        - Keep the tone: {negotiation_style or "Professional"}.
        - Mention the app estimate as a reference point, not as market truth.
        - Stay aligned with the provided estimate and profile details.
        - Do not sound aggressive.
        - Keep the email under 180 words.
        - Keep the call script under 120 words.

        Job title: {job_title or "Not provided"}
        Location: {location or "Not provided"}
        Years of experience: {years_experience or "Not provided"}
        Predicted salary reference: {predicted_salary_text or "Not provided"}
        Target salary: {target_salary_text or "Not provided"}
        Additional context: {extra_context or "None"}
        """
    ).strip()
    return system_prompt, user_prompt


def build_chat_system_prompt(
    *,
    mode: str,
    tone: str,
    context_payload: dict | None,
) -> str:
    mode_help = MODE_HELP.get(mode, "Stay within SalaryScope-related assistance.")
    context_block = _json_block(context_payload)
    return dedent(
        f"""
        You are SalaryScope's local AI assistant.

        Role:
        - You are an assistant layer on top of SalaryScope, not the salary prediction engine.
        - The displayed SalaryScope prediction and structured app data are the source of truth.
        - You must not contradict, question, or revise the prediction shown by the app.

        Core rules:
        - Stay inside SalaryScope-related tasks unless the user asks something small and adjacent.
        - Use only the provided app context and conversation context.
        - If information is missing, say that clearly instead of inventing details.
        - Never use placeholder text such as [Job Title], [Location], X, Y, or similar stand-ins.
        - If a required value is missing, explicitly say it is not available in the current app context.
        - Do not make percentile, above-market, guaranteed, or future-salary claims.
        - Do not give strong causal career advice from correlational salary data.
        - When discussing model outputs, present them as SalaryScope results or model-based reference estimates.
        - Do not say the output is wrong, unreliable, or not reflective of reality.
        - A good phrasing style is: "This is the app's model-based estimate, useful as a structured reference for interpretation and discussion."
        - Keep answers concise, practical, and helpful. Prefer 4-8 sentences unless the user asks for more.
        - For drafting tasks, prefer compact but complete outputs over longer drafts that may trail off.
        - End with a complete sentence. Do not stop mid-sentence or mid-paragraph.
        - Start directly with the answer. Do not open with generic greetings or self-introductions.
        - Preferred tone: {tone}.

        Active mode:
        - {mode}
        - {mode_help}

        SalaryScope app knowledge:
        {APP_HELP_TEXT}

        Current structured app context:
        {context_block}
        """
    ).strip()


def build_chat_user_prompt(
    *,
    user_message: str,
    context_note: str = "",
) -> str:
    normalized = user_message.strip().lower()
    identity_prompts = {
        "who are you?",
        "who are you",
        "what are you?",
        "what are you",
        "what can you do?",
        "what can you do",
    }
    if normalized in identity_prompts:
        extra_identity = (
            "Answer in 2 to 4 short sentences only. "
            "State that you are SalaryScope's local assistant, mention the main kinds of help you provide, "
            "and stop there. Do not list every feature in the app. Do not write headings."
        )
        context_note = f"{context_note} {extra_identity}".strip()

    if context_note:
        return dedent(
            f"""
            User request:
            {user_message}

            Extra note:
            {context_note}
            """
        ).strip()
    return user_message.strip()
