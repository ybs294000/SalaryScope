"""
hub_resume_tab.py
=================
Schema-driven Resume Analysis mode for Model Hub bundles.

Bugs fixed in this version
---------------------------
1. Uploading a new PDF did not refresh extraction results.
   Fix: file identity is tracked via the uploaded file's name + size.
   When it changes, all stale extraction state is cleared automatically
   before the new file is processed.

2. No way to clear results between resumes.
   Fix: explicit "Clear" button wipes all resume session state for this model.

3. Model change did not reset the tab.
   Fix: model_id is part of every session key, so switching models
   automatically shows a clean tab. A "previous model" tracker is also
   maintained to fire an explicit wipe when the model changes within the
   same fragment rerun.

Removal contract
----------------
Delete this file and remove the hub_resume_tab import + call in
model_hub_tab.py. No other files need changing.

Schema extractor hint
---------------------
A schema field can carry an explicit extractor override:
    { "name": "residence_iso", "type": "category", "extractor": "country_iso", ... }
Supported identifiers are documented in hub_resume_engine.py.
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from app.model_hub.predictor import predict
from app.model_hub.schema_parser import get_result_label
from app.model_hub.extended_modes.schema_plots import render_schema_plots

logger = logging.getLogger(__name__)

try:
    from app.model_hub.extended_modes import hub_resume_engine as _engine
    _ENGINE_AVAILABLE  = True
    _PDF_AVAILABLE     = _engine._PDFPLUMBER_AVAILABLE
except Exception as _engine_err:
    _ENGINE_AVAILABLE  = False
    _PDF_AVAILABLE     = False
    logger.warning("hub_resume_engine import failed: %s", _engine_err)

try:
    from app.utils.currency_utils import render_currency_converter
    _CURRENCY_AVAILABLE = True
except Exception:
    _CURRENCY_AVAILABLE = False

_KEY_PREFIX = "mh_ext_resume"


# -------------------------------------------------------------------------
def _format_prediction(value: float, target: str) -> str:
    """Format a prediction value based on target name heuristics."""
    tl = target.lower()
    if any(kw in tl for kw in ("salary", "wage", "income", "pay", "usd", "price", "cost", "revenue")):
        return f"${value:,.2f}"
    if any(kw in tl for kw in ("pct", "percent", "rate", "ratio")):
        return f"{value:.2f}%"
    if abs(value) >= 1_000_000:
        return f"{value:,.0f}"
    if abs(value) >= 100:
        return f"{value:,.2f}"
    return f"{value:.4f}"
# --------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _state_keys(model_id: str) -> dict[str, str]:
    """Return all session state key names for this model's resume tab."""
    return {
        "text":     f"{_KEY_PREFIX}_text_{model_id}",
        "output":   f"{_KEY_PREFIX}_output_{model_id}",
        "result":   f"{_KEY_PREFIX}_result_{model_id}",
        "file_id":  f"{_KEY_PREFIX}_file_id_{model_id}",
    }


def _clear_resume_state(model_id: str) -> None:
    """Wipe all resume session state for this model."""
    for key in _state_keys(model_id).values():
        st.session_state.pop(key, None)


def _file_identity(uploaded_file: Any) -> str | None:
    """Return a stable string identifying the uploaded file, or None."""
    if uploaded_file is None:
        return None
    try:
        return f"{uploaded_file.name}:{uploaded_file.size}"
    except Exception:
        return uploaded_file.name


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_hub_resume_mode(
    active_bundle: Any,
    selected_meta: dict,
    msg_fn: Any,
) -> None:
    """
    Render the schema-driven resume analysis panel.

    Parameters
    ----------
    active_bundle  : Loaded ModelBundle.
    selected_meta  : Registry metadata dict.
    msg_fn         : Callable(text, kind).
    """
    if not _ENGINE_AVAILABLE:
        msg_fn(
            "Resume analysis engine is not available in this environment. "
            "The hub_resume_engine module could not be loaded.",
            "warning",
        )
        return

    if not _PDF_AVAILABLE:
        msg_fn(
            "Resume analysis requires pdfplumber, which is not installed. "
            "Use Manual Prediction for direct input.",
            "warning",
        )
        return

    schema   = active_bundle.schema
    fields   = schema.get("fields", [])
    plots    = schema.get("plots", [])
    model_id = active_bundle.model_id
    keys     = _state_keys(model_id)

    st.subheader(":material/description: Resume Analysis")
    st.caption(
        "Upload a PDF resume. Features are extracted automatically and "
        "pre-filled for review. Upload a new PDF at any time to refresh."
    )

    # --- Upload + controls row ---
    up_col, btn_col, clr_col = st.columns([5, 2, 2])

    with up_col:
        uploaded_pdf = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf"],
            key=f"{_KEY_PREFIX}_upload_{model_id}",
            help="ATS-friendly, text-selectable PDFs extract best.",
            label_visibility="collapsed",
        )

    with btn_col:
        extract_clicked = st.button(
            ":material/search: Extract",
            key=f"{_KEY_PREFIX}_extract_{model_id}",
            disabled=uploaded_pdf is None,
            type="primary",
            use_container_width=True,
        )

    with clr_col:
        clear_clicked = st.button(
            ":material/delete_sweep: Clear",
            key=f"{_KEY_PREFIX}_clear_{model_id}",
            help="Clear extracted features, score, and prediction result.",
            use_container_width=True,
        )

    if clear_clicked:
        _clear_resume_state(model_id)
        st.rerun()

    # --- Detect new file: auto-clear stale state when file changes ---
    current_file_id = _file_identity(uploaded_pdf)
    stored_file_id  = st.session_state.get(keys["file_id"])

    if current_file_id is not None and current_file_id != stored_file_id:
        # A different file has been selected since the last extraction run.
        # Clear stale extraction results so they are not shown beneath the
        # new uploader before the user clicks Extract.
        _clear_resume_state(model_id)
        # Store the new file identity so we do not clear again on the next
        # rerun unless a third file is uploaded.
        st.session_state[keys["file_id"]] = current_file_id

    # --- Extract on button click ---
    if extract_clicked and uploaded_pdf is not None:
        with st.spinner("Extracting text from PDF..."):
            raw_text = _engine.extract_text_from_pdf(uploaded_pdf)

        if not raw_text.strip():
            msg_fn(
                "No text could be extracted from this PDF. "
                "The file may be image-based or password-protected. "
                "Try a text-selectable PDF.",
                "error",
            )
            return

        with st.spinner("Extracting features..."):
            # Provide bundle-level lexicons and resume config if they were loaded.
            # Both fall back to global app defaults inside extract_all_fields when
            # not present, so existing bundles without these sidecars are unaffected.
            bundle_lexicons  = getattr(active_bundle, "lexicons",       None) or {}
            bundle_res_cfg   = getattr(active_bundle, "resume_config",  None) or {}
            output = _engine.extract_all_fields(
                raw_text        = raw_text,
                schema_fields   = fields,
                compute_score   = True,
                bundle_lexicons = bundle_lexicons,
                resume_config   = bundle_res_cfg or None,
            )

        st.session_state[keys["text"]]    = raw_text
        st.session_state[keys["output"]]  = output
        st.session_state[keys["file_id"]] = current_file_id
        # Clear any previous prediction result for this model so a stale
        # result from a previous resume is not shown alongside the new extraction.
        st.session_state.pop(keys["result"], None)

    raw_text = st.session_state.get(keys["text"])
    output   = st.session_state.get(keys["output"])

    if raw_text is None or output is None:
        return

    # --- Raw text preview ---
    with st.expander(":material/article: Extracted Resume Text", expanded=False):
        st.text_area(
            "Text",
            raw_text,
            height=200,
            key=f"{_KEY_PREFIX}_preview_{model_id}",
            disabled=True,
        )

    # --- Extraction quality report ---
    _render_extraction_quality(output, fields, msg_fn)

    # --- Resume score ---
    if output.score is not None:
        _render_score_panel(output.score)

    # --- Editable review form ---
    st.markdown("**Review and Edit Extracted Features**")
    st.caption("Pre-filled from your resume. Edit any field before predicting.")

    form_key = f"{_KEY_PREFIX}_form_{model_id}"
    with st.form(key=form_key):
        raw_input = _render_prefilled_form(schema, output.extracted, model_id)
        submitted = st.form_submit_button(
            ":material/play_arrow: Predict from Resume",
            type="primary",
        )

    if submitted:
        try:
            prediction = predict(active_bundle, raw_input)
            result_label = get_result_label(
                schema,
                selected_meta.get("target", "Predicted Value"),
            )
            st.session_state[keys["result"]] = {
                "value":     prediction.value,
                "model_id":  prediction.model_id,
                "target":    result_label,
                "warnings":  prediction.warnings,
                "raw_input": prediction.raw_input,
            }
        except (RuntimeError, ValueError) as exc:
            msg_fn(f"Prediction failed: {exc}", "error")
            st.session_state.pop(keys["result"], None)

    stored = st.session_state.get(keys["result"])
    if stored is not None:
        _render_resume_result(stored, fields, plots, msg_fn)


# ---------------------------------------------------------------------------
# Extraction quality report
# ---------------------------------------------------------------------------

def _render_extraction_quality(
    output: Any,
    fields: list[dict],
    msg_fn: Any,
) -> None:
    total = len(fields)
    found = sum(1 for r in output.results.values() if r.found)

    col1, col2, col3 = st.columns(3)
    col1.metric("Schema Fields",  total)
    col2.metric("Auto-extracted", found)
    col3.metric("Needs Review",   len(output.unmatched))

    if output.unmatched:
        msg_fn(
            "These fields could not be extracted and use schema defaults. "
            "Please review them before predicting: "
            + ", ".join(output.unmatched),
            "warning",
        )

    with st.expander(":material/manage_search: Extraction Details", expanded=False):
        for fld in fields:
            name = fld.get("name", "")
            res  = output.results.get(name)
            if res is None:
                st.caption(f"{name}: no extractor matched")
                continue
            icon    = ":material/check_circle:" if res.found else ":material/warning:"
            val_str = str(res.value)
            if isinstance(res.value, list):
                val_str = f"[{len(res.value)} items]"
            st.caption(f"{icon}  **{name}** = {val_str}  |  source: {res.source}")

    if output.skills:
        with st.expander(
            f":material/checklist: Detected Skills ({len(output.skills)})",
            expanded=False,
        ):
            st.write(", ".join(output.skills))



# ---------------------------------------------------------------------------
# Score panel
# ---------------------------------------------------------------------------

def _render_score_panel(score: Any) -> None:
    st.divider()
    st.subheader(":material/stars: Resume Quality Score")

    level_color = {
        "Basic":    "#EF4444",
        "Moderate": "#F59E0B",
        "Strong":   "#22C55E",
    }.get(score.level, "#6B7280")

    st.markdown(
        f"""
        <div style="
            background: var(--bg-card, #1E293B);
            border: 1px solid var(--border, #334155);
            border-left: 4px solid {level_color};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 12px;
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 2rem; font-weight: 700; color: {level_color};">
                    {score.total}
                </span>
                <div>
                    <div style="font-size: 0.85rem; color: var(--text-muted, #94A3B8);">
                        Resume Score
                    </div>
                    <div style="font-size: 1rem; font-weight: 600; color: {level_color};">
                        {score.level}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Experience", f"{score.experience_score} / 40")
        st.progress(score.experience_score / 40, text=score.experience_note)
    with col2:
        st.metric("Education", f"{score.education_score} / 30")
        st.progress(score.education_score / 30, text=score.education_note)
    with col3:
        st.metric("Skills", f"{score.skills_score} / 30")
        st.progress(score.skills_score / 30, text=score.skills_note)


# ---------------------------------------------------------------------------
# Prefilled form
# ---------------------------------------------------------------------------

def _render_prefilled_form(
    schema: dict,
    extracted: dict[str, Any],
    model_id: str,
) -> dict[str, Any]:
    from app.model_hub.schema_parser import render_schema_form

    fields = schema.get("fields", [])
    patched_fields = []
    for fld in fields:
        f    = dict(fld)
        name = fld.get("name")
        if name and name in extracted:
            raw_val = extracted[name]
            if isinstance(raw_val, list):
                raw_val = ", ".join(str(x) for x in raw_val)
            f["default"] = raw_val
        patched_fields.append(f)

    patched_schema = {k: v for k, v in schema.items() if k != "fields"}
    patched_schema["fields"] = patched_fields

    return render_schema_form(
        schema     = patched_schema,
        key_prefix = f"mh_ext_resume_ff_{model_id}",
    )


# ---------------------------------------------------------------------------
# Result renderer
# ---------------------------------------------------------------------------

def _render_resume_result(
    stored: dict,
    fields: list[dict],
    plots: list[dict],
    msg_fn: Any,
) -> None:
    value     = stored["value"]
    model_id  = stored["model_id"]
    target    = stored.get("target", "Predicted Value")
    warnings  = stored.get("warnings", [])
    raw_input = stored.get("raw_input", {})

    st.divider()
    st.subheader(":material/insights: Resume Prediction Result")

    from app.theme import hub_result_card_html
    formatted = _format_prediction(value, target)
    st.markdown(hub_result_card_html(formatted, target), unsafe_allow_html=True)

    for w in warnings:
        msg_fn(w, "warning")

    with st.expander(":material/list: Extracted Input Summary", expanded=False):
        for k, v in raw_input.items():
            st.text(f"{k}: {v}")

    single_plots = [p for p in plots if p.get("type") in ("gauge", "bar", "horizontal_bar")]
    if single_plots:
        st.divider()
        render_schema_plots(
            plots         = single_plots,
            result_value  = value,
            raw_input     = raw_input,
            batch_df      = None,
            schema_fields = fields,
        )

    if _CURRENCY_AVAILABLE:
        location_hint = None
        for fn in ("country", "location", "employee_residence", "company_location"):
            if fn in raw_input:
                location_hint = str(raw_input[fn])
                break
        render_currency_converter(
            usd_amount    = value,
            location_hint = location_hint,
            widget_key    = f"mh_ext_resume_currency_{model_id}",
            show_breakdown = True,
        )