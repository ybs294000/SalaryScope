"""
model_card.py
=============
Model Card UI component for the Model Hub.

A model card is a structured, scannable summary of a model's identity,
performance, capabilities, and data provenance.  It appears in the Model Hub
when a user selects a model, giving them informed context before running a
prediction.

Design approach
---------------
The card is rendered as a Streamlit expander (collapsed by default on small
screens, expanded by default on first load of a model) using only native
Streamlit widgets and minimal HTML.  No third-party card libraries.

Data source
-----------
Model card data lives in the registry entry (models_registry.json) under an
optional "model_card" key.  This allows admins to supply rich metadata at
upload time or update it later by pushing the registry.  If the key is absent,
the card renders a minimal view from the always-present registry fields.

Schema for registry "model_card" key
--------------------------------------
All fields are optional.  The card degrades gracefully when any are absent.

{
  "model_card": {
    "intended_use":        "Predict annual salary in USD for data roles.",
    "out_of_scope":        "Not suitable for non-tech roles or non-USD salaries.",
    "training_data":       "ds_salaries.csv, Kaggle, ~3700 records, 2020-2023.",
    "evaluation_data":     "20% holdout, stratified by experience level.",
    "metrics": {
      "r2":  0.594,
      "mae": 35913,
      "rmse": 48774
    },
    "metric_labels": {
      "r2":   "Test R-squared",
      "mae":  "Mean Absolute Error (USD)",
      "rmse": "Root Mean Squared Error (USD)"
    },
    "limitations":         "Training data may not reflect post-2023 market shifts.",
    "ethical_notes":       "Predictions reflect historical pay gaps in the dataset.",
    "authors":             "SalaryScope Team",
    "license":             "MIT",
    "contact":             "admin@example.com",
    "tags":                ["salary", "data science", "xgboost"],
    "framework":           "XGBoost 2.x + sklearn pipeline",
    "bundle_format":       "onnx",
    "links": {
      "Paper":       "https://arxiv.org/...",
      "Dataset":     "https://kaggle.com/...",
      "Source code": "https://github.com/..."
    }
  }
}

Extensibility
-------------
To add a new section to the card:
1. Add a helper function _render_yourfield(card, meta) at the bottom of this file.
2. Call it inside render_model_card() in the appropriate position.
No other file needs changing.

Removal contract
----------------
To remove the model card entirely:
1. Delete this file.
2. Remove the model_card import and _render_model_card_panel() call from
   model_hub_tab.py (inside the EXTENDED MODES block).
No other file needs changing.
"""

from __future__ import annotations

from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_model_card(
    selected_meta: dict,
    expanded: bool = False,
) -> None:
    """
    Render the model card for the currently selected model.

    Parameters
    ----------
    selected_meta  : Registry entry dict for the selected model.
    expanded       : Whether the expander is open by default.
    """
    card = selected_meta.get("model_card") or {}

    with st.expander(
        ":material/badge: Model Card",
        expanded=expanded,
    ):
        _render_identity_section(card, selected_meta)
        _render_metrics_section(card)
        _render_use_section(card)
        _render_data_section(card)
        _render_caveats_section(card)
        _render_meta_section(card, selected_meta)
        _render_links_section(card)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_identity_section(card: dict, meta: dict) -> None:
    """Display name, description, tags, version, and format badge."""
    name        = meta.get("display_name", "Untitled Model")
    description = card.get("description") or meta.get("description") or ""
    tags        = card.get("tags") or []
    version     = meta.get("version", "N/A")
    fmt         = meta.get("bundle_format") or card.get("bundle_format") or "pickle"
    target      = meta.get("target", "")

    fmt_color = "#22C55E" if fmt == "onnx" else "#F59E0B"
    fmt_label = "ONNX" if fmt == "onnx" else "Pickle"

    # Header row: name + format badge + version
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px;">
            <span style="font-size: 1.1rem; font-weight: 700; color: var(--text-main, #E2E8F0);">
                {name}
            </span>
            <span style="
                background: {fmt_color}22;
                color: {fmt_color};
                border: 1px solid {fmt_color}55;
                border-radius: 4px;
                font-size: 0.72rem;
                font-weight: 600;
                padding: 2px 7px;
                letter-spacing: 0.05em;
            ">{fmt_label}</span>
            <span style="
                background: #6B728022;
                color: #94A3B8;
                border: 1px solid #6B728055;
                border-radius: 4px;
                font-size: 0.72rem;
                padding: 2px 7px;
            ">v{version}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if target:
        st.caption(f"Predicts: **{target}**")

    if description:
        st.markdown(description)

    if tags:
        tag_html = " ".join(
            f'<span style="'
            f'background: #4F8EF722; color: #93C5FD; border: 1px solid #4F8EF744;'
            f'border-radius: 12px; font-size: 0.72rem; padding: 2px 9px; margin-right: 4px;'
            f'">{t}</span>'
            for t in tags
        )
        st.markdown(tag_html, unsafe_allow_html=True)

    _maybe_divider(card, [
        "metrics", "intended_use", "out_of_scope",
        "training_data", "evaluation_data", "limitations",
        "ethical_notes", "authors", "license", "links",
    ])


def _render_metrics_section(card: dict) -> None:
    """Render performance metrics as st.metric columns."""
    metrics       = card.get("metrics") or {}
    metric_labels = card.get("metric_labels") or {}

    if not metrics:
        return

    st.markdown("**Performance Metrics**")

    items = list(metrics.items())
    cols  = st.columns(min(len(items), 4))

    for i, (key, value) in enumerate(items):
        label = metric_labels.get(key, key.upper())
        col   = cols[i % len(cols)]
        with col:
            if isinstance(value, float):
                if 0.0 <= value <= 1.0 and key.lower() in ("r2", "r_squared", "accuracy", "f1"):
                    col.metric(label, f"{value:.4f}")
                elif abs(value) > 999:
                    col.metric(label, f"{value:,.0f}")
                else:
                    col.metric(label, f"{value:,.4f}")
            else:
                col.metric(label, str(value))

    _maybe_divider(card, [
        "intended_use", "out_of_scope", "training_data",
        "evaluation_data", "limitations", "ethical_notes",
        "authors", "license", "links",
    ])


def _render_use_section(card: dict) -> None:
    """Intended use and out-of-scope use."""
    intended   = card.get("intended_use")
    out_scope  = card.get("out_of_scope")

    if not intended and not out_scope:
        return

    st.markdown("**Use Cases**")
    col1, col2 = st.columns(2)

    if intended:
        with col1:
            st.markdown(
                _info_box("Intended Use", intended, "#22C55E"),
                unsafe_allow_html=True,
            )

    if out_scope:
        with col2:
            st.markdown(
                _info_box("Out of Scope", out_scope, "#EF4444"),
                unsafe_allow_html=True,
            )

    _maybe_divider(card, [
        "training_data", "evaluation_data", "limitations",
        "ethical_notes", "authors", "license", "links",
    ])


def _render_data_section(card: dict) -> None:
    """Training and evaluation data descriptions."""
    training   = card.get("training_data")
    evaluation = card.get("evaluation_data")
    framework  = card.get("framework")

    if not training and not evaluation and not framework:
        return

    st.markdown("**Data and Framework**")

    if training:
        st.caption(f":material/dataset: Training data: {training}")
    if evaluation:
        st.caption(f":material/analytics: Evaluation data: {evaluation}")
    if framework:
        st.caption(f":material/memory: Framework: {framework}")

    _maybe_divider(card, [
        "limitations", "ethical_notes",
        "authors", "license", "links",
    ])


def _render_caveats_section(card: dict) -> None:
    """Limitations and ethical considerations."""
    limitations   = card.get("limitations")
    ethical_notes = card.get("ethical_notes")

    if not limitations and not ethical_notes:
        return

    st.markdown("**Caveats and Ethical Notes**")

    if limitations:
        st.markdown(
            _info_box("Limitations", limitations, "#F59E0B"),
            unsafe_allow_html=True,
        )

    if ethical_notes:
        st.markdown(
            _info_box("Ethical Considerations", ethical_notes, "#A78BFA"),
            unsafe_allow_html=True,
        )

    _maybe_divider(card, ["authors", "license", "links"])


def _render_meta_section(card: dict, meta: dict) -> None:
    """Authors, license, upload metadata."""
    authors     = card.get("authors")
    license_str = card.get("license")
    uploaded_by = meta.get("uploaded_by")
    uploaded_at = (meta.get("uploaded_at") or "")[:10]
    family_id   = meta.get("family_id")

    rows = []
    if authors:
        rows.append(f":material/person: Authors: {authors}")
    if license_str:
        rows.append(f":material/policy: License: {license_str}")
    if uploaded_by:
        rows.append(f":material/upload: Uploaded by: {uploaded_by}")
    if uploaded_at:
        rows.append(f":material/calendar_today: Upload date: {uploaded_at}")
    if family_id:
        rows.append(f":material/folder: Family ID: {family_id}")

    contact = card.get("contact")
    if contact:
        rows.append(f":material/mail: Contact: {contact}")

    if not rows:
        return

    st.markdown("**Provenance**")
    for row in rows:
        st.caption(row)

    _maybe_divider(card, ["links"])


def _render_links_section(card: dict) -> None:
    """External links (paper, dataset, repo, etc.)."""
    links = card.get("links") or {}
    if not links:
        return

    st.markdown("**Links**")
    link_parts = [
        f"[{label}]({url})" for label, url in links.items() if url
    ]
    if link_parts:
        st.markdown("  |  ".join(link_parts))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _info_box(title: str, body: str, accent: str) -> str:
    """Render a small titled info box as HTML."""
    return (
        f'<div style="'
        f'border-left: 3px solid {accent};'
        f'background: {accent}11;'
        f'border-radius: 0 6px 6px 0;'
        f'padding: 10px 14px;'
        f'margin-bottom: 8px;'
        f'">'
        f'<div style="font-size: 0.75rem; font-weight: 600; color: {accent}; margin-bottom: 4px;">'
        f'{title}'
        f'</div>'
        f'<div style="font-size: 0.85rem; color: var(--text-main, #CBD5E1);">'
        f'{body}'
        f'</div>'
        f'</div>'
    )


def _maybe_divider(card: dict, remaining_keys: list[str]) -> None:
    """Show a divider only if at least one of the remaining sections has data."""
    if any(card.get(k) for k in remaining_keys):
        st.divider()
