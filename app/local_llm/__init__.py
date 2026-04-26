"""
Local LLM prototype package for optional, offline-friendly text features.

This package is intentionally isolated from the main app so it can be tested
and evolved without modifying the existing SalaryScope tabs.
"""

from .service import (
    generate_assistant_reply,
    generate_negotiation_script,
    generate_resume_summary,
    get_backend_label,
    is_local_llm_available,
    list_local_models,
)
from .storage import init_chat_db

__all__ = [
    "generate_assistant_reply",
    "generate_negotiation_script",
    "generate_resume_summary",
    "get_backend_label",
    "init_chat_db",
    "is_local_llm_available",
    "list_local_models",
]
