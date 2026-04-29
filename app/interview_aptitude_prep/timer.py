from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st


USE_LIVE_TIMER = True


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_duration(total_seconds: int | None) -> str:
    if total_seconds is None:
        return "Untimed"
    seconds = max(0, int(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def build_attempt(question_set: dict[str, Any], timed_mode: bool) -> dict[str, Any]:
    timer_config = question_set.get("timer", {})
    timer_supported = bool(timer_config.get("enabled", False))
    timer_enabled = bool(timed_mode and timer_supported)
    time_limit_seconds = None
    if timer_enabled:
        time_limit_seconds = int(timer_config.get("time_limit_seconds") or 0) or None

    return {
        "set_id": question_set["set_id"],
        "title": question_set["title"],
        "started_at": to_iso(utc_now()),
        "submitted_at": None,
        "timer_enabled": timer_enabled,
        "time_limit_seconds": time_limit_seconds,
        "timer_enforced": bool(timer_config.get("enforce_on_submit", True)),
        "status": "in_progress",
    }


def finalize_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    updated = dict(attempt)
    updated["submitted_at"] = to_iso(utc_now())
    updated["status"] = "submitted"
    return updated


def get_timer_snapshot(attempt: dict[str, Any] | None) -> dict[str, Any]:
    if not attempt:
        return {
            "timer_enabled": False,
            "elapsed_seconds": 0,
            "remaining_seconds": None,
            "expired": False,
        }

    started_at = parse_iso(attempt.get("started_at"))
    submitted_at = parse_iso(attempt.get("submitted_at"))
    end_time = submitted_at or utc_now()
    elapsed_seconds = 0
    if started_at is not None:
        elapsed_seconds = max(0, int((end_time - started_at).total_seconds()))

    time_limit_seconds = attempt.get("time_limit_seconds")
    remaining_seconds = None
    expired = False
    if attempt.get("timer_enabled") and time_limit_seconds is not None:
        remaining_seconds = max(0, int(time_limit_seconds) - elapsed_seconds)
        expired = remaining_seconds <= 0

    return {
        "timer_enabled": bool(attempt.get("timer_enabled")),
        "elapsed_seconds": elapsed_seconds,
        "remaining_seconds": remaining_seconds,
        "expired": expired,
        "time_limit_seconds": time_limit_seconds,
    }


def _render_timer_body(attempt_key: str) -> None:
    attempt = st.session_state.get(attempt_key)
    snapshot = get_timer_snapshot(attempt)
    if not snapshot["timer_enabled"]:
        return

    elapsed = format_duration(snapshot["elapsed_seconds"])
    remaining = format_duration(snapshot["remaining_seconds"])
    cols = st.columns(2)
    cols[0].metric("Time Elapsed", elapsed)
    cols[1].metric("Time Remaining", remaining)

    if snapshot["expired"]:
        st.warning("The time limit has been reached. Submit your answers to finish this attempt.")


def render_timer_panel(attempt_key: str) -> None:
    attempt = st.session_state.get(attempt_key)
    if not attempt or not attempt.get("timer_enabled"):
        return

    if USE_LIVE_TIMER and hasattr(st, "fragment"):
        try:
            @st.fragment(run_every=1)
            def _live_timer() -> None:
                _render_timer_body(attempt_key)

            _live_timer()
            return
        except Exception:
            pass

    _render_timer_body(attempt_key)
