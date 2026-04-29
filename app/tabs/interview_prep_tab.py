import streamlit as st

from app.interview_aptitude_prep import render_interview_prep


def render_interview_prep_tab() -> None:
    """Thin wrapper for the interview preparation feature."""
    render_interview_prep()
