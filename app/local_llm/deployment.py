"""
Deployment detection helpers for local LLM routing.
Mirrors the app's local-vs-cloud logic without importing UI tabs.
"""

from __future__ import annotations

import os


def is_local_runtime() -> bool:
    try:
        import streamlit as st
        val = st.secrets.get("IS_LOCAL", None)
        if val is not None:
            return bool(val)
    except Exception:
        pass

    try:
        if os.environ.get("STREAMLIT_SHARING_MODE"):
            return False
        home = os.environ.get("HOME", "")
        cwd = os.getcwd()
        if home in ("/home/appuser", "/app") or cwd.startswith("/app"):
            return False
    except Exception:
        pass
    return True


def deployment_label() -> str:
    return "Local" if is_local_runtime() else "Streamlit Cloud"
