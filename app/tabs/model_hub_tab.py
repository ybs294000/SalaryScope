"""
model_hub_tab.py
================
Streamlit UI for the Model Hub feature.

Layout
------
  [Header + model selector]
  [User: Prediction panel]
  [Admin: Upload bundle]
  [Admin: Registry manager (activate / deactivate / rollback)]
  [Admin: Schema editor]

Architecture rules enforced here
---------------------------------
- No business logic in this file. All logic lives in app/model_hub/*.
- No circular imports. This file depends on model_hub only.
- No HTML cards. st.container / st.expander used for layout.
- No st.info / st.success / st.warning for styled messages — use _msg().
- No HTML headings — use st.header / st.subheader.
- Material icons only via :material/icon_name: in st.markdown / st.caption,
  NOT inside html strings.
- No emojis.
- st.fragment used for sections that should not trigger full reruns.

Inline message helper (_msg)
-----------------------------
Mirrors the card/banner style from savings_utils.py to keep colours aligned
with the rest of the app (dark professional theme):
  _msg("text", "info")     -> blue left border
  _msg("text", "success")  -> green left border
  _msg("text", "warning")  -> amber left border
  _msg("text", "error")    -> red left border
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import streamlit as st
from app.theme import util_info_banner_html, get_token
from app.model_hub.registry import (
    fetch_registry,
    get_active_models,
    get_model_by_id,
    add_model_to_registry,
    set_model_active,
    rollback_to_version,
    push_registry,
)
from app.model_hub.loader import load_bundle, clear_bundle_cache
from app.model_hub.predictor import predict
from app.model_hub.schema_parser import render_schema_form, get_result_label
from app.model_hub.validator import (
    validate_schema,
    validate_schema_vs_columns,
    parse_schema_json,
    validate_bundle_files,
    detect_bundle_format,
    validate_aliases,
    validate_resume_config,
)
from app.model_hub.uploader import upload_bundle, upload_bundle_onnx, upload_schema_only, upload_aliases_only, upload_resume_config_only

# ==========================================================================
# EXTENDED MODES - BEGIN
# These imports enable Manual, Batch, Resume, and Scenario prediction modes
# for Model Hub bundles.  Each import is independently removable:
#   - Remove the import + the corresponding _render_hub_*_mode() call below.
#   - No other file needs changing.
# ==========================================================================
try:
    from app.model_hub.extended_modes.hub_manual_tab import render_hub_manual_mode as _hub_manual
    _HUB_MANUAL_AVAILABLE = True
except Exception:
    _HUB_MANUAL_AVAILABLE = False

try:
    from app.model_hub.extended_modes.hub_batch_tab import render_hub_batch_mode as _hub_batch
    _HUB_BATCH_AVAILABLE = True
except Exception:
    _HUB_BATCH_AVAILABLE = False

try:
    from app.model_hub.extended_modes.hub_resume_tab import render_hub_resume_mode as _hub_resume
    _HUB_RESUME_AVAILABLE = True
except Exception:
    _HUB_RESUME_AVAILABLE = False

try:
    from app.model_hub.extended_modes.hub_scenario_tab import render_hub_scenario_mode as _hub_scenario
    _HUB_SCENARIO_AVAILABLE = True
except Exception:
    _HUB_SCENARIO_AVAILABLE = False

try:
    from app.model_hub.extended_modes.model_card import render_model_card as _render_model_card
    _MODEL_CARD_AVAILABLE = True
except Exception:
    _MODEL_CARD_AVAILABLE = False
# ==========================================================================
# EXTENDED MODES - END
# ==========================================================================

# Currency converter — import is lazy-guarded so the tab works even if
# currency_utils is unavailable (e.g. lite app without the full utils tree).
try:
    from app.utils.currency_utils import render_currency_converter, guess_currency
    _CURRENCY_AVAILABLE = True
except Exception:
    _CURRENCY_AVAILABLE = False

logger = logging.getLogger(__name__)


def _msg(text: str, kind: str = "info") -> None:
    from app.theme import util_status_box_html

    border_key = {
        "info":    "util_blue",
        "success": "status_success",
        "warning": "status_warning",
        "error":   "status_error",
    }.get(kind, "util_blue")

    bg_key = {
        "info":    "banner_info_bg",
        "success": "banner_ok_bg",
        "warning": "banner_warn_bg",
        "error":   "banner_err_bg",
    }.get(kind, "banner_info_bg")

    st.markdown(
        util_status_box_html(
            message=text,
            color=get_token(border_key),
            bg=get_token(bg_key),
        ),
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Registry cache (per session, TTL-driven)
# ---------------------------------------------------------------------------
_REGISTRY_CACHE_KEY = "mh_registry_cache"
_REGISTRY_TTL_S     = 120   # seconds before refetching


def _get_registry(force: bool = False) -> dict:
    """
    Return a registry dict from session cache or HuggingFace.
    Raises RuntimeError if fetch fails — caller handles display.
    """
    import time
    now = time.monotonic()
    cache = st.session_state.get(_REGISTRY_CACHE_KEY)

    if (
        not force
        and cache is not None
        and now - cache.get("_fetched_at", 0) < _REGISTRY_TTL_S
    ):
        return cache

    registry = fetch_registry()
    registry["_fetched_at"] = now
    st.session_state[_REGISTRY_CACHE_KEY] = registry
    return registry


def _invalidate_registry_cache() -> None:
    st.session_state.pop(_REGISTRY_CACHE_KEY, None)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_model_hub_tab(
    user: Optional[dict] = None,
    is_admin_user: bool = False,
) -> None:
    """
    Render the full Model Hub tab.

    Parameters
    ----------
    user          : Logged-in user dict (from auth layer). None = not logged in.
    is_admin_user : True if user has admin privileges.
    """
    st.header(":material/hub: Model Hub")
    st.caption(
        "Run predictions using curated models available in the hub. "
        "Each model has its own input schema and target variable."
    )

    # --- Auth gate ---
    if user is None:
        _msg(
            "You must be logged in to use the Model Hub. "
            "Please log in from the sidebar.",
            "warning",
        )
        return

    st.divider()

    # --- Load registry ---
    try:
        registry = _get_registry()
    except RuntimeError as exc:
        _msg(f"Could not load model registry: {exc}", "error")
        if is_admin_user:
            st.caption(
                "Check HF_REPO_ID and HF_TOKEN in your secrets configuration."
            )
        return

    active_models = get_active_models(registry)

    # --- Prediction panel (all logged-in users) ---
    _render_prediction_panel(active_models, user)

    st.divider()

    # --- Admin-only sections ---
    if is_admin_user:
        _render_admin_section(registry, user)


# ---------------------------------------------------------------------------
# Prediction panel
# ---------------------------------------------------------------------------

@st.fragment
def _render_prediction_panel(active_models: list[dict], user: dict) -> None:
    """Prediction model selector and form — isolated fragment."""
    st.subheader(":material/model_training: Model Selection")

    if not active_models:
        _msg(
            "No active models are available at the moment. "
            "Ask an admin to upload and activate a model.",
            "info",
        )
        return

    # Build display options
    options     = {m["display_name"]: m for m in active_models}
    model_names = list(options.keys())

    col_sel, col_info, col_info2 = st.columns([3, 1, 1])
    with col_sel:
        chosen_name = st.selectbox(
            "Select a model",
            options=model_names,
            key="mh_model_selector",
            help="Only approved, active models appear here.",
        )

    selected_meta = options[chosen_name]

    num_inputs   = selected_meta.get("num_inputs")
    num_features = selected_meta.get("num_features")

    with col_info:
        st.metric(
            "Input Fields",
            num_inputs if num_inputs is not None else "N/A",
            help="Number of fields you fill in to make a prediction.",
        )

    with col_info2:
        st.metric(
            "Model Features",
            num_features if num_features is not None else "N/A",
            help=(
                "Total columns the model was trained on. "
                "May be higher than input fields when categorical variables "
                "are one-hot encoded (e.g. job_title becomes one column per value)."
            ),
        )

    if selected_meta.get("description"):
        st.caption(selected_meta["description"])

    # Version / target info
    info_parts = []
    if selected_meta.get("target"):
        info_parts.append(f"Target: **{selected_meta['target']}**")
    if selected_meta.get("uploaded_at"):
        info_parts.append(f"Uploaded: {selected_meta['uploaded_at'][:10]}")
    if selected_meta.get("version"):
        info_parts.append(f"Version: {selected_meta['version']}")
    if info_parts:
        st.caption("  |  ".join(info_parts))

    # ==========================================================================
    # MODEL CARD: renders structured metadata for the selected model.
    # To remove: delete model_card.py and this block.
    # ==========================================================================
    if _MODEL_CARD_AVAILABLE:
        _render_model_card(selected_meta, expanded=False)
    # ==========================================================================

    #st.divider()

    # --- Load bundle ---
    load_key = f"mh_load_{selected_meta['id']}"
    if st.button(
        ":material/download: Load Model",
        key=load_key,
        help="Download and cache the model bundle. Only needed once per session.",
    ):
        with st.spinner("Loading model bundle from HuggingFace..."):
            try:
                bundle = load_bundle(selected_meta, force_reload=True)
                st.session_state["mh_active_bundle_id"] = selected_meta["id"]
                _msg(f"Model '{chosen_name}' loaded successfully.", "success")
            except RuntimeError as exc:
                _msg(f"Failed to load model: {exc}", "error")
                st.session_state.pop("mh_active_bundle_id", None)
                return

    # Check if bundle is already in cache
    from app.model_hub.loader import BUNDLE_CACHE_KEY
    cached_bundles = st.session_state.get(BUNDLE_CACHE_KEY, {})
    active_bundle  = cached_bundles.get(selected_meta["id"])

    # Backfill num_inputs from the live schema for models uploaded before this
    # field was added to the registry (so the metric always shows the correct count).
    if active_bundle is not None and selected_meta.get("num_inputs") is None:
        selected_meta["num_inputs"] = len(active_bundle.schema.get("fields", []))

    if active_bundle is None:
        _msg(
            "Model not loaded yet. Click 'Load Model' to download the bundle.",
            "info",
        )
        return

    # The prediction form, batch upload, resume analysis, and scenario analysis
    # are all available in the tabs below.  There is no separate inline form here
    # to avoid showing the same inputs twice.

    # ==========================================================================
    # EXTENDED MODES - BEGIN
    # Renders Manual / Batch / Resume / Scenario sub-tabs for the loaded bundle.
    # This block is completely self-contained.  To remove it, delete everything
    # between "EXTENDED MODES - BEGIN" and "EXTENDED MODES - END".
    # ==========================================================================
    _render_extended_modes_panel(active_bundle, selected_meta)
    # ==========================================================================
    # EXTENDED MODES - END
    # ==========================================================================


def _render_extended_modes_panel(active_bundle: Any, selected_meta: dict) -> None:
    """
    Render the extended prediction modes sub-tab panel for a loaded bundle.

    Shows Manual / Batch / Resume / Scenario sub-tabs below the existing
    single-prediction panel.  Each mode is gated on its availability flag so
    removing any extended_modes submodule simply drops that tab from the UI
    without errors.

    This function is called from _render_prediction_panel (inside a fragment)
    so it participates in the same fragment rerun boundary.  Each inner mode
    manages its own session state keys using the model_id as a namespace.
    """
    # Only show if at least one extended mode is available.
    any_available = (
        _HUB_MANUAL_AVAILABLE
        or _HUB_BATCH_AVAILABLE
        or _HUB_RESUME_AVAILABLE
        or _HUB_SCENARIO_AVAILABLE
    )
    if not any_available:
        return

    st.divider()
    st.subheader(":material/apps: Prediction Modes")
    st.caption(
        "Use the same loaded model in different modes below. "
        "All modes read from the same schema and bundle."
    )

    # Build tab list dynamically from what is available.
    tab_labels = []
    if _HUB_MANUAL_AVAILABLE:
        tab_labels.append(":material/edit_note: Manual")
    if _HUB_BATCH_AVAILABLE:
        tab_labels.append(":material/batch_prediction: Batch")
    if _HUB_RESUME_AVAILABLE:
        tab_labels.append(":material/description: Resume")
    if _HUB_SCENARIO_AVAILABLE:
        tab_labels.append(":material/analytics: Scenario")

    tab_objects = st.tabs(tab_labels)
    tab_idx = 0

    if _HUB_MANUAL_AVAILABLE:
        with tab_objects[tab_idx]:
            _hub_manual(active_bundle, selected_meta, _msg)
        tab_idx += 1

    if _HUB_BATCH_AVAILABLE:
        with tab_objects[tab_idx]:
            _hub_batch(active_bundle, selected_meta, _msg)
        tab_idx += 1

    if _HUB_RESUME_AVAILABLE:
        with tab_objects[tab_idx]:
            _hub_resume(active_bundle, selected_meta, _msg)
        tab_idx += 1

    if _HUB_SCENARIO_AVAILABLE:
        with tab_objects[tab_idx]:
            _hub_scenario(active_bundle, selected_meta, _msg)


def _render_prediction_result(stored: dict) -> None:
    """
    Render a stored prediction result dict.

    Called on every fragment rerun (form submit OR toggle click) so the
    result card and currency toggle stay visible after any widget interaction.

    Parameters
    ----------
    stored : dict with keys value, model_id, target, warnings, raw_input.
             Written to session_state by the form submit handler.
    """
    value     = stored["value"]
    model_id  = stored["model_id"]
    target    = stored.get("target", "Predicted Value")
    warnings  = stored.get("warnings", [])
    raw_input = stored.get("raw_input", {})

    st.divider()
    st.subheader(":material/insights: Prediction Result")

    # Primary result card
    from app.theme import hub_result_card_html

    formatted = _format_prediction(value, target)
    st.markdown(hub_result_card_html(formatted, target), unsafe_allow_html=True)

    # Warnings from prediction
    for w in warnings:
        _msg(w, "warning")

    # Input summary
    with st.expander(":material/list: Input Summary", expanded=False):
        for k, v in raw_input.items():
            st.text(f"{k}: {v}")

    # Currency conversion — shown only when result is available and
    # currency_utils is present. Caller can remove this block independently
    # without affecting anything else: just delete from here to END_CURRENCY.
    # START_CURRENCY
    if _CURRENCY_AVAILABLE:
        # Try to derive a location hint from the raw inputs so the converter
        # pre-selects a sensible default currency. Checks common field names.
        _location_hint = None
        for _field_name in ("country", "location", "employee_residence",
                            "company_location", "country_code"):
            if _field_name in raw_input:
                _location_hint = str(raw_input[_field_name])
                break
        render_currency_converter(
            usd_amount    = value,
            location_hint = _location_hint,
            widget_key    = f"mh_currency_{model_id}",
            show_breakdown= True,
        )
    # END_CURRENCY


def _format_prediction(value: float, target: str) -> str:
    """Format the prediction value based on target name heuristics."""
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


# ---------------------------------------------------------------------------
# Admin section
# ---------------------------------------------------------------------------

def _render_admin_section(registry: dict, user: dict) -> None:
    """All admin-only panels, gated behind is_admin check in caller."""
    st.subheader(":material/admin_panel_settings: Admin Controls")
    st.caption("These controls are visible to admin users only.")

    tab_upload, tab_registry, tab_schema = st.tabs([
        "Upload Bundle",
        "Registry Manager",
        "Schema Editor",
    ])

    with tab_upload:
        _render_upload_panel(registry, user)

    with tab_registry:
        _render_registry_manager(registry)

    with tab_schema:
        _render_schema_editor()


# ---------------------------------------------------------------------------
# Upload panel
# ---------------------------------------------------------------------------

@st.fragment
def _render_upload_panel(registry: dict, user: dict) -> None:
    st.subheader(":material/upload: Upload Model Bundle")
    _msg(
        "Upload all three files (model.pkl, columns.pkl, schema.json) together. "
        "Each upload creates a new versioned bundle folder — existing bundles are never overwritten.",
        "info",
    )
    _msg(
        "ONNX bundles (model.onnx + columns.json) are the recommended format — "
        "no arbitrary code execution on load. "
        "Pickle bundles (model.pkl + columns.pkl) are also supported for compatibility. "
        "Never upload files from untrusted sources.",
        "info",
    )

    with st.expander(":material/upload_file: Bundle Upload", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            display_name = st.text_input(
                "Display Name",
                placeholder="e.g. Software Engineering Salaries (US)",
                key="mh_up_name",
                help="Name shown in the model selector dropdown.",
            )
            target = st.text_input(
                "Target Variable",
                placeholder="e.g. salary_in_usd",
                key="mh_up_target",
                help="Name of the column the model predicts.",
            )
        with col2:
            description = st.text_area(
                "Description (optional)",
                placeholder="Describe the dataset, use case, and model type.",
                key="mh_up_desc",
                height=100,
            )
            family_id = st.text_input(
                "Family ID (optional)",
                placeholder="e.g. swe_salary_us (for rollback grouping)",
                key="mh_up_family",
                help="Group related model versions under one family for rollback.",
            )

        # ==========================================================================
        # MODEL CARD - BEGIN
        # Optional structured metadata stored in the registry entry.
        # Displayed in the Model Card expander when users select the model.
        # To remove model card support: delete from MODEL CARD - BEGIN to END,
        # and remove model_card_json from all _do_upload* calls below.
        # ==========================================================================
        with st.expander(":material/badge: Model Card Metadata (optional)", expanded=False):
            st.caption(
                "Fill in any fields you want to appear on the model card. "
                "All fields are optional. You can also paste raw JSON directly."
            )
            mc_col1, mc_col2 = st.columns(2)
            with mc_col1:
                mc_intended = st.text_area(
                    "Intended use",
                    key="mh_up_mc_intended",
                    placeholder="What this model is designed to predict and for whom.",
                    height=80,
                )
                mc_limitations = st.text_area(
                    "Limitations",
                    key="mh_up_mc_limitations",
                    placeholder="Known limitations, edge cases, or data gaps.",
                    height=80,
                )
                mc_training_data = st.text_input(
                    "Training data",
                    key="mh_up_mc_training",
                    placeholder="e.g. ds_salaries.csv, Kaggle, ~3700 records, 2020-2023",
                )
                mc_framework = st.text_input(
                    "Framework",
                    key="mh_up_mc_framework",
                    placeholder="e.g. XGBoost 2.x + sklearn pipeline",
                )
            with mc_col2:
                mc_out_of_scope = st.text_area(
                    "Out of scope",
                    key="mh_up_mc_oos",
                    placeholder="Inputs or use cases this model should not be used for.",
                    height=80,
                )
                mc_ethical = st.text_area(
                    "Ethical notes",
                    key="mh_up_mc_ethical",
                    placeholder="Bias considerations, fairness notes, or known gaps.",
                    height=80,
                )
                mc_authors = st.text_input(
                    "Authors",
                    key="mh_up_mc_authors",
                    placeholder="e.g. SalaryScope Team",
                )
                mc_license = st.text_input(
                    "License",
                    key="mh_up_mc_license",
                    placeholder="e.g. MIT",
                )
            mc_tags_raw = st.text_input(
                "Tags (comma-separated)",
                key="mh_up_mc_tags",
                placeholder="e.g. salary, data science, xgboost",
            )
            st.caption(
                "Performance metrics and external links can be added by editing "
                "the registry entry JSON directly after upload, or via the "
                "Model Card JSON field below."
            )
            mc_raw_json = st.text_area(
                "Raw model_card JSON override (optional)",
                key="mh_up_mc_raw",
                placeholder='{"metrics": {"r2": 0.59, "mae": 35913}, "links": {"Dataset": "https://..."}}',
                height=80,
                help=(
                    "Advanced: paste a full or partial model_card JSON object. "
                    "This is merged with the fields above. "
                    "Raw JSON takes precedence on key conflicts."
                ),
            )

        def _build_model_card_dict() -> dict:
            """Assemble model_card dict from upload panel widget values."""
            import json as _json
            card: dict = {}
            mc_intended_val  = st.session_state.get("mh_up_mc_intended", "").strip()
            mc_oos_val       = st.session_state.get("mh_up_mc_oos", "").strip()
            mc_limitations_v = st.session_state.get("mh_up_mc_limitations", "").strip()
            mc_ethical_val   = st.session_state.get("mh_up_mc_ethical", "").strip()
            mc_training_val  = st.session_state.get("mh_up_mc_training", "").strip()
            mc_framework_val = st.session_state.get("mh_up_mc_framework", "").strip()
            mc_authors_val   = st.session_state.get("mh_up_mc_authors", "").strip()
            mc_license_val   = st.session_state.get("mh_up_mc_license", "").strip()
            mc_tags_val      = st.session_state.get("mh_up_mc_tags", "").strip()
            mc_raw_val       = st.session_state.get("mh_up_mc_raw", "").strip()

            if mc_intended_val:  card["intended_use"]   = mc_intended_val
            if mc_oos_val:       card["out_of_scope"]   = mc_oos_val
            if mc_limitations_v: card["limitations"]    = mc_limitations_v
            if mc_ethical_val:   card["ethical_notes"]  = mc_ethical_val
            if mc_training_val:  card["training_data"]  = mc_training_val
            if mc_framework_val: card["framework"]      = mc_framework_val
            if mc_authors_val:   card["authors"]        = mc_authors_val
            if mc_license_val:   card["license"]        = mc_license_val
            if mc_tags_val:
                card["tags"] = [t.strip() for t in mc_tags_val.split(",") if t.strip()]

            if mc_raw_val:
                try:
                    raw_parsed = _json.loads(mc_raw_val)
                    if isinstance(raw_parsed, dict):
                        card.update(raw_parsed)
                except _json.JSONDecodeError:
                    pass  # invalid raw JSON is silently ignored at build time

            return card
        # ==========================================================================
        # MODEL CARD - END
        # ==========================================================================

        st.divider()
        st.markdown("**Upload Files**")

        st.markdown("**Format — choose one:**")
        fmt_choice = st.radio(
            "Bundle format",
            options=["ONNX (recommended)", "Pickle (legacy)"],
            key="mh_up_fmt",
            horizontal=True,
            help=(
                "ONNX: model.onnx + columns.json — no arbitrary code execution on load. "
                "Pickle: model.pkl + columns.pkl — compatible with all sklearn/XGBoost models."
            ),
        )
        is_onnx_upload = fmt_choice.startswith("ONNX")

        st.divider()
        st.markdown("**Upload Files**")

        if is_onnx_upload:
            f_model   = st.file_uploader("model.onnx",    type=["onnx"], key="mh_up_model")
            f_columns = st.file_uploader("columns.json",  type=["json"], key="mh_up_columns",
                                         help="JSON array of feature column names, e.g. [\"age\", \"country_US\", ...]")
        else:
            f_model   = st.file_uploader("model.pkl",   type=["pkl"],  key="mh_up_model")
            f_columns = st.file_uploader("columns.pkl", type=["pkl"],  key="mh_up_columns")

        f_schema  = st.file_uploader("schema.json", type=["json"], key="mh_up_schema")
        f_aliases = st.file_uploader(
            "aliases.json (optional)",
            type=["json"],
            key="mh_up_aliases",
            help=(
                "Optional sidecar for large alias sets (e.g. 118 country names). "
                "Format: {field_name: {model_value: display_label, ...}}. "
                "Leave empty if all values are already human-readable."
            ),
        )

        # LEXICON UPLOADERS - BEGIN
        # Bundle-level lexicons override the global app-level JSON files
        # for resume extraction when this model is loaded. Both are optional.
        # If omitted, the global app-level lexicons/ files are used as fallback.
        st.divider()
        st.markdown("**Resume Extraction Lexicons (optional)**")
        st.caption(
            "Upload custom lexicons to override the app-level defaults for resume "
            "feature extraction when this model is used. Both files are optional and "
            "independent. Omitting either falls back to the shared global lexicon."
        )
        lex_col1, lex_col2 = st.columns(2)
        with lex_col1:
            f_skills_lex = st.file_uploader(
                "skills.json (optional)",
                type=["json"],
                key="mh_up_skills_lex",
                help=(
                    "Custom skill phrase list for this model. "
                    "Must match skills.json format: "
                    "{category_name: [phrase, phrase, ...]}. "
                    "Overrides the global skills.json for resume extraction."
                ),
            )
        with lex_col2:
            f_titles_lex = st.file_uploader(
                "job_titles.json (optional)",
                type=["json"],
                key="mh_up_titles_lex",
                help=(
                    "Custom job title alias map for this model. "
                    "Must match job_titles.json format: "
                    "{Canonical Title: [alias, alias, ...]}. "
                    "Overrides the global job_titles.json for resume extraction."
                ),
            )
        # LEXICON UPLOADERS - END

        # RESUME CONFIG UPLOADER - BEGIN
        # resume_config.json selectively overrides extraction engine defaults
        # (scoring weights, extractor keyword lists, field-name-to-extractor
        # mappings, text preprocessing flags) for this specific bundle.
        # Completely optional -- omitting it leaves all engine defaults unchanged.
        st.divider()
        st.markdown("**Resume Extraction Config (optional)**")
        st.caption(
            "Upload a resume_config.json to override extraction engine defaults "
            "for this specific model. All keys are optional -- only include the "
            "settings you want to change. See hub_resume_engine.py for the full "
            "format reference."
        )
        f_resume_cfg = st.file_uploader(
            "resume_config.json (optional)",
            type=["json"],
            key="mh_up_resume_cfg",
            help=(
                "Per-bundle resume extraction config. Supported top-level keys: "
                "'scoring' (weight overrides), 'extractors' (keyword/pattern lists), "
                "'field_name_mapping' (extra field-name to extractor-id pairs), "
                "'preprocessing' (strip_urls, max_text_length). "
                "Omitting this file leaves all engine defaults active."
            ),
        )
        # Show a live validation preview as soon as a file is selected
        if f_resume_cfg is not None:
            _rc_preview_bytes = f_resume_cfg.read()
            f_resume_cfg.seek(0)
            try:
                import json as _json_rc
                _rc_parsed = _json_rc.loads(_rc_preview_bytes.decode("utf-8"))
                _rc_issues = validate_resume_config(_rc_parsed)
                if _rc_issues:
                    for _iss in _rc_issues:
                        # Warnings (unrecognised keys) are advisory only
                        _kind = "warning" if "unrecognised" in _iss else "error"
                        _msg(_iss, _kind)
                else:
                    _msg("resume_config.json is valid.", "success")
            except Exception as _rc_exc:
                _msg(f"resume_config.json is not valid JSON: {_rc_exc}", "error")
        # RESUME CONFIG UPLOADER - END

        # Validate completeness using format-aware checker
        uploaded_names = []
        if f_model:
            uploaded_names.append("model.onnx" if is_onnx_upload else "model.pkl")
        if f_columns:
            uploaded_names.append("columns.json" if is_onnx_upload else "columns.pkl")
        if f_schema:
            uploaded_names.append("schema.json")

        missing = validate_bundle_files(uploaded_names)
        if missing and uploaded_names:
            _msg(f"Bundle incomplete. Still missing: {', '.join(missing)}", "warning")

        if is_onnx_upload and uploaded_names:
            _msg(
                "ONNX format — no pickle deserialisation on load.",
                "success",
            )

        if st.button(
            ":material/cloud_upload: Upload Bundle",
            key="mh_do_upload",
            disabled=bool(missing) or not display_name or not target,
            type="primary",
        ):
            aliases_bytes        = f_aliases.read()    if f_aliases    else None
            skills_lex_bytes     = f_skills_lex.read() if f_skills_lex else None
            titles_lex_bytes     = f_titles_lex.read() if f_titles_lex else None
            resume_cfg_bytes     = f_resume_cfg.read() if f_resume_cfg else None
            model_card_dict      = _build_model_card_dict()
            if is_onnx_upload:
                _do_upload_onnx(
                    f_model.read(), f_columns.read(), f_schema.read(),
                    display_name, description, target, family_id,
                    user, registry,
                    aliases_bytes       = aliases_bytes,
                    model_card_dict     = model_card_dict or None,
                    skills_lex_bytes    = skills_lex_bytes,
                    titles_lex_bytes    = titles_lex_bytes,
                    resume_cfg_bytes    = resume_cfg_bytes,
                )
            else:
                _do_upload(
                    f_model.read(), f_columns.read(), f_schema.read(),
                    display_name, description, target, family_id,
                    user, registry,
                    aliases_bytes       = aliases_bytes,
                    model_card_dict     = model_card_dict or None,
                    skills_lex_bytes    = skills_lex_bytes,
                    titles_lex_bytes    = titles_lex_bytes,
                    resume_cfg_bytes    = resume_cfg_bytes,
                )


def _upload_lexicon_sidecar(
    data: Optional[bytes],
    folder_path: str,
    filename: str,
    label: str,
) -> None:
    """
    Upload a lexicon JSON sidecar to the bundle folder on HuggingFace.
    Silent no-op when data is None (lexicon not provided at upload time).
    Logs a warning on failure but does not abort the main upload.
    """
    if data is None:
        return
    try:
        from app.model_hub._hf_client import upload_file_bytes
        if not folder_path.endswith("/"):
            folder_path += "/"
        upload_file_bytes(
            path_in_repo   = folder_path + filename,
            data           = data,
            commit_message = f"Upload {label} for {folder_path}",
        )
    except Exception as exc:
        _msg(
            f"Warning: {label} upload failed ({exc}). "
            "Resume extraction will fall back to global app-level lexicons.",
            "warning",
        )


def _do_upload(
    model_bytes: bytes,
    columns_bytes: bytes,
    schema_bytes: bytes,
    display_name: str,
    description: str,
    target: str,
    family_id: str,
    user: dict,
    registry: dict,
    aliases_bytes: Optional[bytes] = None,
    model_card_dict: Optional[dict] = None,
    skills_lex_bytes: Optional[bytes] = None,
    titles_lex_bytes: Optional[bytes] = None,
    resume_cfg_bytes: Optional[bytes] = None,
) -> None:
    uploaded_by = user.get("email") or user.get("username") or "admin"

    with st.spinner("Validating and uploading bundle..."):
        try:
            result = upload_bundle(
                model_bytes         = model_bytes,
                columns_bytes       = columns_bytes,
                schema_bytes        = schema_bytes,
                display_name        = display_name,
                description         = description,
                target              = target,
                uploaded_by         = uploaded_by,
                family_id           = family_id or None,
                aliases_bytes       = aliases_bytes if aliases_bytes else None,
                resume_config_bytes = resume_cfg_bytes if resume_cfg_bytes else None,
            )
        except (ValueError, RuntimeError) as exc:
            _msg(f"Upload failed: {exc}", "error")
            return

    for w in result.warnings:
        _msg(w, "warning")

    # Upload optional lexicon sidecars to the same bundle folder.
    # These override global app-level lexicons for this model's resume extraction.
    _upload_lexicon_sidecar(skills_lex_bytes, result.folder_path, "skills.json",
                             "skills lexicon")
    _upload_lexicon_sidecar(titles_lex_bytes, result.folder_path, "job_titles.json",
                             "job titles lexicon")

    if model_card_dict:
        result.registry_entry["model_card"] = model_card_dict

    # Track whether bundle-level sidecars were uploaded
    if skills_lex_bytes:
        result.registry_entry["has_skills_lexicon"] = True
    if titles_lex_bytes:
        result.registry_entry["has_titles_lexicon"] = True
    # has_resume_config is already set by upload_bundle when resume_config_bytes
    # was provided -- no extra flag needed here.

    try:
        new_registry = add_model_to_registry(registry, result.registry_entry)
        push_registry(new_registry)
        _invalidate_registry_cache()
        _msg(
            f"Bundle '{result.folder_name}' uploaded and registered successfully. "
            f"Folder: {result.folder_path}",
            "success",
        )
    except (ValueError, RuntimeError) as exc:
        _msg(
            f"Bundle files uploaded but registry update failed: {exc}. "
            "Manually add the entry to models_registry.json.",
            "error",
        )
        st.code(json.dumps(result.registry_entry, indent=2))


def _do_upload_onnx(
    onnx_bytes: bytes,
    columns_json_bytes: bytes,
    schema_bytes: bytes,
    display_name: str,
    description: str,
    target: str,
    family_id: str,
    user: dict,
    registry: dict,
    aliases_bytes: Optional[bytes] = None,
    model_card_dict: Optional[dict] = None,
    skills_lex_bytes: Optional[bytes] = None,
    titles_lex_bytes: Optional[bytes] = None,
    resume_cfg_bytes: Optional[bytes] = None,
) -> None:
    uploaded_by = user.get("email") or user.get("username") or "admin"

    with st.spinner("Validating and uploading ONNX bundle..."):
        try:
            result = upload_bundle_onnx(
                onnx_bytes          = onnx_bytes,
                columns_json_bytes  = columns_json_bytes,
                schema_bytes        = schema_bytes,
                display_name        = display_name,
                description         = description,
                target              = target,
                uploaded_by         = uploaded_by,
                family_id           = family_id or None,
                aliases_bytes       = aliases_bytes if aliases_bytes else None,
                resume_config_bytes = resume_cfg_bytes if resume_cfg_bytes else None,
            )
        except (ValueError, RuntimeError) as exc:
            _msg(f"Upload failed: {exc}", "error")
            return

    for w in result.warnings:
        _msg(w, "warning")

    _upload_lexicon_sidecar(skills_lex_bytes, result.folder_path, "skills.json",
                             "skills lexicon")
    _upload_lexicon_sidecar(titles_lex_bytes, result.folder_path, "job_titles.json",
                             "job titles lexicon")

    if model_card_dict:
        result.registry_entry["model_card"] = model_card_dict

    if skills_lex_bytes:
        result.registry_entry["has_skills_lexicon"] = True
    if titles_lex_bytes:
        result.registry_entry["has_titles_lexicon"] = True
    # has_resume_config is already set by upload_bundle_onnx when resume_cfg_bytes
    # was provided -- no extra flag needed here.

    try:
        new_registry = add_model_to_registry(registry, result.registry_entry)
        push_registry(new_registry)
        _invalidate_registry_cache()
        _msg(
            f"ONNX bundle '{result.folder_name}' uploaded and registered successfully. "
            f"Folder: {result.folder_path}",
            "success",
        )
    except (ValueError, RuntimeError) as exc:
        _msg(
            f"Bundle files uploaded but registry update failed: {exc}. "
            "Manually add the entry to models_registry.json.",
            "error",
        )
        st.code(json.dumps(result.registry_entry, indent=2))


# ---------------------------------------------------------------------------
# Registry manager
# ---------------------------------------------------------------------------

@st.fragment
def _render_registry_manager(registry: dict) -> None:
    st.subheader(":material/list_alt: Registry Manager")
    st.caption(
        "Activate, deactivate, or roll back models. "
        "Deactivated models remain in storage but are hidden from users."
    )

    if st.button(":material/refresh: Refresh Registry", key="mh_reg_refresh"):
        _invalidate_registry_cache()
        st.rerun()

    all_models = registry.get("models", [])
    if not all_models:
        _msg("No models found in the registry.", "info")
        return

    for idx, model in enumerate(all_models):
        mid          = model.get("id", f"unknown_{idx}")
        dname        = model.get("display_name", mid)
        active       = model.get("active", True)
        uploaded_at  = model.get("uploaded_at", "")[:10]
        version      = model.get("version", "N/A")
        size_mb      = (model.get("size_bytes", 0) or 0) / 1024 / 1024
        family       = model.get("family_id", "")

        status_icon  = ":material/check_circle:" if active else ":material/cancel:"
        status_label = "Active" if active else "Inactive"

        with st.expander(
            f"{status_icon} {dname}  [{status_label}]  |  v{version}  |  {uploaded_at}",
            expanded=False,
        ):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Status",   status_label)
            c2.metric("Version",  version)
            c3.metric("Size",     f"{size_mb:.1f} MB" if size_mb else "N/A")
            c4.metric(
                "Input Fields",
                model.get("num_inputs", "N/A"),
                help="Number of fields shown to the user in the prediction form.",
            )
            c5.metric(
                "Model Features",
                model.get("num_features", "N/A"),
                help="Total columns in columns.pkl (includes OHE-expanded columns).",
            )

            if model.get("description"):
                st.caption(model["description"])
            if family:
                st.caption(f"Family ID: {family}")
            st.caption(f"Path: {model.get('path', 'N/A')}")
            st.caption(f"Target: {model.get('target', 'N/A')}")
            st.caption(f"Uploaded by: {model.get('uploaded_by', 'N/A')}")
            _fmt = model.get("bundle_format", "pickle")
            _fmt_label = ":material/lock: ONNX" if _fmt == "onnx" else ":material/warning: Pickle"
            st.caption(f"Format: {_fmt_label}")

            # Show optional sidecar badges so admins can see at a glance what
            # was uploaded alongside the core bundle files.
            _sidecar_parts = []
            if model.get("has_aliases"):
                _sidecar_parts.append("aliases.json")
            if model.get("has_skills_lexicon"):
                _sidecar_parts.append("skills.json")
            if model.get("has_titles_lexicon"):
                _sidecar_parts.append("job_titles.json")
            if model.get("has_resume_config"):
                _sidecar_parts.append("resume_config.json")
            if _sidecar_parts:
                st.caption(f"Sidecars: {', '.join(_sidecar_parts)}")

            btn_col1, btn_col2, btn_col3 = st.columns(3)

            with btn_col1:
                if active:
                    if st.button("Deactivate", key=f"mh_deact_{mid}"):
                        _toggle_model(registry, mid, False)
                else:
                    if st.button("Activate", key=f"mh_act_{mid}", type="primary"):
                        _toggle_model(registry, mid, True)

            with btn_col2:
                if family:
                    if st.button(
                        "Rollback to this version",
                        key=f"mh_rollback_{mid}",
                        help=f"Deactivate all other models in family '{family}' and activate this one.",
                    ):
                        _do_rollback(registry, mid)

            with btn_col3:
                if st.button(
                    ":material/delete_sweep: Clear cache",
                    key=f"mh_clearcache_{mid}",
                    help="Remove this model from session memory.",
                ):
                    clear_bundle_cache(mid)
                    _msg(f"Cache cleared for '{dname}'.", "info")


def _toggle_model(registry: dict, model_id: str, active: bool) -> None:
    try:
        new_reg = set_model_active(registry, model_id, active)
        push_registry(new_reg)
        _invalidate_registry_cache()
        verb = "activated" if active else "deactivated"
        _msg(f"Model '{model_id}' {verb}.", "success")
        st.rerun()
    except (ValueError, RuntimeError) as exc:
        _msg(f"Failed to update model status: {exc}", "error")


def _do_rollback(registry: dict, model_id: str) -> None:
    try:
        new_reg = rollback_to_version(registry, model_id)
        push_registry(new_reg)
        _invalidate_registry_cache()
        _msg(f"Rolled back to '{model_id}'. All other family members deactivated.", "success")
        st.rerun()
    except (ValueError, RuntimeError) as exc:
        _msg(f"Rollback failed: {exc}", "error")


# ---------------------------------------------------------------------------
# Schema editor
# ---------------------------------------------------------------------------

@st.fragment
def _render_schema_editor() -> None:
    """
    GUI schema editor + file upload option.
    Modular: removing this function leaves the rest of the system fully functional.
    Schema created here can be downloaded and used in bundle uploads.
    """
    st.subheader(":material/edit_note: Schema Editor")
    st.caption(
        "Build or edit a schema.json interactively, or upload an existing one. "
        "Download the result and include it in your model bundle upload."
    )

    editor_tab, upload_tab = st.tabs(["Visual Editor", "Upload / Validate"])

    with editor_tab:
        _render_visual_schema_editor()

    with upload_tab:
        _render_schema_upload_validator()


def _render_visual_schema_editor() -> None:
    """Interactive field-by-field schema builder."""

    # Initialise fields list in session
    if "mh_schema_fields" not in st.session_state:
        st.session_state["mh_schema_fields"] = []

    fields: list[dict] = st.session_state["mh_schema_fields"]

    # --- Add field form ---
    with st.expander(":material/add_circle: Add Field", expanded=len(fields) == 0):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            new_name = st.text_input("Field name (snake_case)", key="mh_se_name",
                                     placeholder="e.g. years_experience")
        with fc2:
            new_type = st.selectbox("Data type", ["int", "float", "category", "bool", "str"],
                                    key="mh_se_type")
        with fc3:
            new_ui = st.selectbox("UI widget",
                                  ["slider", "selectbox", "number_input", "text_input", "checkbox"],
                                  key="mh_se_ui")

        new_label   = st.text_input("Display label (optional)", key="mh_se_label")
        new_help    = st.text_input("Help text (optional)",     key="mh_se_help")
        # Layout position controls (optional)
        lc1, lc2 = st.columns(2)

        with lc1:
            new_row = st.number_input(
                "Row group (optional)",
                min_value=1, max_value=50, value=1,
                key="mh_se_row",
            )
            use_row = st.checkbox("Assign to a row group", key="mh_se_use_row", value=False)

        with lc2:
            new_col_span = st.selectbox(
                "Column span (optional)",
                options=[1, 2, 3],
                index=0,
                key="mh_se_col_span",
            )
        # Conditional constraints
        if new_ui == "slider" or new_ui == "number_input":
            nc1, nc2, nc3 = st.columns(3)
            new_min     = nc1.number_input("Min", value=0.0, key="mh_se_min")
            new_max     = nc2.number_input("Max", value=100.0, key="mh_se_max")
            new_default = nc3.number_input("Default", value=0.0, key="mh_se_default")
            new_step    = st.number_input("Step (optional, 0 = auto)", value=0.0, key="mh_se_step", min_value=0.0)
        elif new_ui == "selectbox":
            raw_values  = st.text_input(
                "Allowed values — model values (comma-separated)",
                key="mh_se_values",
                placeholder="S, M, L",
                help=(
                    "Exact values the model was trained on. "
                    "Use aliases below if you want friendlier labels in the form."
                ),
            )
            new_default = st.text_input("Default value (optional)", key="mh_se_default_cat")
            raw_aliases = st.text_area(
                "Aliases — display labels (optional)",
                key="mh_se_aliases",
                placeholder="S: Small (< 50 employees)\nM: Medium (50-250 employees)\nL: Large (> 250 employees)",
                height=90,
                help=(
                    "One entry per line in the format   model_value: Display Label. "
                    "Leave blank to show model values as-is. "
                    "Example: US: United States  |  GB: United Kingdom"
                ),
            )
        elif new_ui == "checkbox":
            new_default = st.checkbox("Default checked?", key="mh_se_default_bool")

        if st.button(":material/add: Add Field", key="mh_se_add"):
            if not new_name:
                _msg("Field name is required.", "error")
            elif any(f["name"] == new_name for f in fields):
                _msg(f"Field '{new_name}' already exists.", "error")
            else:
                entry: dict = {
                    "name": new_name.strip(),
                    "type": new_type,
                    "ui":   new_ui,
                }
                if use_row:
                    entry["row"] = int(new_row)
                    entry["col_span"] = int(new_col_span)
                if new_label:
                    entry["label"] = new_label.strip()
                if new_help:
                    entry["help"] = new_help.strip()

                if new_ui in ("slider", "number_input"):
                    entry["min"]     = float(new_min) if new_type == "float" else int(new_min)
                    entry["max"]     = float(new_max) if new_type == "float" else int(new_max)
                    entry["default"] = float(new_default) if new_type == "float" else int(new_default)
                    if new_step and new_step > 0:
                        entry["step"] = float(new_step) if new_type == "float" else int(new_step)
                elif new_ui == "selectbox":
                    vals = [v.strip() for v in raw_values.split(",") if v.strip()]
                    entry["values"] = vals
                    if new_default and new_default in vals:
                        entry["default"] = new_default
                    # Parse aliases: each non-empty line should be "value: Label"
                    parsed_aliases = {}
                    for alias_line in raw_aliases.splitlines():
                        alias_line = alias_line.strip()
                        if not alias_line or ":" not in alias_line:
                            continue
                        alias_key, _, alias_label = alias_line.partition(":")
                        alias_key   = alias_key.strip()
                        alias_label = alias_label.strip()
                        if alias_key and alias_label and alias_key in vals:
                            parsed_aliases[alias_key] = alias_label
                        elif alias_key and alias_key not in vals:
                            _msg(
                                f"Alias key '{alias_key}' is not in the values list — skipped.",
                                "warning",
                            )
                    if parsed_aliases:
                        entry["aliases"] = parsed_aliases
                elif new_ui == "checkbox":
                    entry["default"] = bool(new_default)

                st.session_state["mh_schema_fields"].append(entry)
                _msg(f"Field '{new_name}' added.", "success")
                st.rerun()
                
    # --- Schema-level settings ---
    with st.expander("Schema-level settings (layout + result label)", expanded=False):
        sc1, sc2 = st.columns(2)

        with sc1:
            st.selectbox(
                "Form grid columns",
                options=[1, 2, 3],
                key="mh_se_grid_cols",
            )

        with sc2:
            st.text_input(
                "Result card label (optional)",
                key="mh_se_result_label",
                placeholder="e.g. Estimated Salary",
        )
    # --- Current fields list ---
    if fields:
        st.markdown("**Current Fields**")
        for i, field in enumerate(fields):
            f_name = field.get("name", f"field_{i}")
            with st.expander(
                f":material/tune: {f_name}  [{field.get('ui')}  /  {field.get('type')}]",
                expanded=False,
            ):
                st.json(field)
                if st.button(":material/delete: Remove", key=f"mh_se_del_{i}"):
                    st.session_state["mh_schema_fields"].pop(i)
                    st.rerun()

        # Validate
        schema_draft = {"fields": fields}

        _grid = st.session_state.get("mh_se_grid_cols", 1)
        _rlabel = st.session_state.get("mh_se_result_label", "").strip()

        if _grid > 1:
            schema_draft["layout"] = {"columns": _grid}

        if _rlabel:
            schema_draft["result_label"] = _rlabel

        issues = validate_schema(schema_draft)
        if issues:
            for iss in issues:
                _msg(iss, "warning")
        else:
            _msg(f"Schema is valid — {len(fields)} field(s) defined.", "success")

        # Export
        schema_json_str = json.dumps(schema_draft, indent=2)
        st.download_button(
            label=":material/download: Download schema.json",
            data=schema_json_str.encode("utf-8"),
            file_name="schema.json",
            mime="application/json",
            key="mh_se_download",
        )

        if st.button(":material/delete_forever: Clear all fields", key="mh_se_clear"):
            st.session_state["mh_schema_fields"] = []
            st.rerun()
    else:
        _msg("No fields added yet. Use the form above to build your schema.", "info")


def _render_schema_upload_validator() -> None:
    """Upload, validate, and optionally push schema.json for an existing model."""
    st.caption(
        "Upload a schema.json to validate it, preview the UI it will generate, "
        "or push it to an existing model bundle."
    )

    uploaded = st.file_uploader(
        "schema.json",
        type=["json"],
        key="mh_sv_file",
    )

    if not uploaded:
        return

    raw = uploaded.read()
    schema, issues = parse_schema_json(raw)

    if issues:
        for iss in issues:
            _msg(iss, "error")
        return

    _msg(f"Schema is valid — {len(schema.get('fields', []))} field(s).", "success")

    with st.expander(":material/preview: Preview raw schema", expanded=False):
        st.json(schema)

    with st.expander(":material/preview: Preview generated UI (read-only)", expanded=False):
        st.caption("This is how the input form will look to users.")
        render_schema_form(schema, key_prefix="mh_preview")

    st.divider()
    st.markdown("**Push to existing bundle (optional)**")
    st.caption(
        "Update schema.json or aliases.json in an existing bundle without "
        "re-uploading model.pkl and columns.pkl."
    )
    bundle_path = st.text_input(
        "Bundle path (e.g. models/model_20260415_ab12cd/)",
        key="mh_sv_path",
        placeholder="models/model_YYYYMMDDHHMMSS_xxxxxx/",
    )
    model_id = st.text_input(
        "Model ID (same as folder name)",
        key="mh_sv_id",
        placeholder="model_YYYYMMDDHHMMSS_xxxxxx",
    )

    push_col1, push_col2 = st.columns(2)
    with push_col1:
        if st.button(":material/cloud_upload: Push schema.json", key="mh_sv_push",
                     disabled=not bundle_path or not model_id):
            try:
                upload_schema_only(raw, model_id, bundle_path)
                clear_bundle_cache(model_id)
                _msg(
                    f"schema.json pushed to '{bundle_path}'. "
                    "Cache cleared — next Load Model will use the updated schema.",
                    "success",
                )
            except (ValueError, RuntimeError) as exc:
                _msg(f"Push failed: {exc}", "error")

    st.divider()
    st.markdown("**Push aliases.json to existing bundle (optional)**")
    st.caption(
        "Upload a new or replacement aliases.json sidecar. "
        "The file is validated against the schema above before upload."
    )
    f_aliases_push = st.file_uploader(
        "aliases.json",
        type=["json"],
        key="mh_sv_aliases",
        help="Format: {field_name: {model_value: display_label, ...}}",
    )
    with push_col2:
        if st.button(
            ":material/cloud_upload: Push aliases.json",
            key="mh_sv_push_aliases",
            disabled=not bundle_path or not model_id or not f_aliases_push,
        ):
            try:
                upload_aliases_only(
                    aliases_bytes = f_aliases_push.read(),
                    model_id      = model_id,
                    bundle_path   = bundle_path,
                    schema        = schema,
                )
                _msg(
                    f"aliases.json pushed to '{bundle_path}'. "
                    "Cache cleared — next Load Model will show updated labels.",
                    "success",
                )
            except (ValueError, RuntimeError) as exc:
                _msg(f"Push failed: {exc}", "error")

    st.divider()
    st.markdown("**Push resume_config.json to existing bundle (optional)**")
    st.caption(
        "Upload a new or replacement resume_config.json sidecar. "
        "The file is validated before upload. "
        "Affects resume extraction scoring, keyword lists, and field mappings "
        "for this bundle only. All keys are optional -- include only overrides."
    )
    f_rc_push = st.file_uploader(
        "resume_config.json",
        type=["json"],
        key="mh_sv_resume_cfg",
        help=(
            "Supported top-level keys: scoring, extractors, "
            "field_name_mapping, preprocessing. "
            "See hub_resume_engine.py for the full format reference."
        ),
    )
    if f_rc_push is not None:
        _rc_push_bytes = f_rc_push.read()
        f_rc_push.seek(0)
        try:
            import json as _json_rc_push
            _rc_push_parsed = _json_rc_push.loads(_rc_push_bytes.decode("utf-8"))
            _rc_push_issues = validate_resume_config(_rc_push_parsed)
            if _rc_push_issues:
                for _iss in _rc_push_issues:
                    _kind = "warning" if "unrecognised" in _iss else "error"
                    _msg(_iss, _kind)
            else:
                _msg("resume_config.json is valid.", "success")
        except Exception as _rc_push_exc:
            _msg(f"resume_config.json is not valid JSON: {_rc_push_exc}", "error")

    if st.button(
        ":material/cloud_upload: Push resume_config.json",
        key="mh_sv_push_resume_cfg",
        disabled=not bundle_path or not model_id or not f_rc_push,
    ):
        try:
            upload_resume_config_only(
                resume_config_bytes = f_rc_push.read(),
                model_id            = model_id,
                bundle_path         = bundle_path,
            )
            _msg(
                f"resume_config.json pushed to '{bundle_path}'. "
                "Cache cleared — next Load Model will use the updated config.",
                "success",
            )
        except (ValueError, RuntimeError) as exc:
            _msg(f"Push failed: {exc}", "error")