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
from app.model_hub.schema_parser import render_schema_form
from app.model_hub.validator import (
    validate_schema,
    validate_schema_vs_columns,
    parse_schema_json,
    validate_bundle_files,
)
from app.model_hub.uploader import upload_bundle, upload_schema_only

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Theme constants (matching rest of app)
# ---------------------------------------------------------------------------
_BG_CARD    = "#141A22"
_BG_INPUT   = "#1B2230"
_BORDER     = "#283142"
_TEXT_MAIN  = "#E6EAF0"
_TEXT_MUTED = "#9CA6B5"
_ACCENT     = "#4F8EF7"

# ---------------------------------------------------------------------------
# Inline message helper — aligned with savings_utils.py card style
# ---------------------------------------------------------------------------
_MSG_COLORS = {
    "info":    ("#1E2D40", "#4F8EF7"),
    "success": ("#1A2E22", "#22C55E"),
    "warning": ("#2E2510", "#F59E0B"),
    "error":   ("#2E1515", "#EF4444"),
}


def _msg(text: str, kind: str = "info") -> None:
    """Render a styled inline message banner matching the app dark theme."""
    bg, border = _MSG_COLORS.get(kind, _MSG_COLORS["info"])
    st.markdown(
        f"<div style='background:{bg};border-left:4px solid {border};"
        f"border-radius:6px;padding:11px 16px;margin:6px 0;"
        f"font-size:13px;color:{_TEXT_MAIN};'>{text}</div>",
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
        "Run predictions using community-trained models. "
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
    st.subheader(":material/model_training: Run a Prediction")

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

    st.divider()

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

    # --- Render prediction form ---
    st.markdown("**Input Parameters**")
    st.caption(
        "Fill in the fields below. The form is generated from this model's schema."
    )

    with st.form(key=f"mh_pred_form_{active_bundle.model_id}"):
        raw_input = render_schema_form(
            schema=active_bundle.schema,
            key_prefix=f"mh_{active_bundle.model_id}",
        )
        submitted = st.form_submit_button(
            ":material/play_arrow: Predict",
            type="primary",
        )

    if submitted:
        _run_and_display_prediction(active_bundle, raw_input, selected_meta)


def _run_and_display_prediction(
    bundle,
    raw_input: dict[str, Any],
    model_meta: dict,
) -> None:
    """Run prediction and render result."""
    try:
        result = predict(bundle, raw_input)
    except (RuntimeError, ValueError) as exc:
        _msg(f"Prediction failed: {exc}", "error")
        return

    target = model_meta.get("target", "Predicted Value")

    st.divider()
    st.subheader(":material/insights: Prediction Result")

    # Primary result card
    formatted = _format_prediction(result.value, target)
    st.markdown(
        f"<div style='background:{_BG_INPUT};border:1px solid {_BORDER};"
        f"border-left:5px solid {_ACCENT};border-radius:10px;"
        f"padding:20px 24px;margin:8px 0;'>"
        f"<div style='color:{_TEXT_MUTED};font-size:11px;font-weight:600;"
        f"letter-spacing:0.5px;margin-bottom:6px;text-transform:uppercase;'>{target}</div>"
        f"<div style='color:{_ACCENT};font-size:32px;font-weight:700;"
        f"letter-spacing:-0.5px;'>{formatted}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Warnings from prediction
    for w in result.warnings:
        _msg(w, "warning")

    # Input summary
    with st.expander(":material/list: Input Summary", expanded=False):
        for k, v in result.raw_input.items():
            st.text(f"{k}: {v}")


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
        "Security notice: model.pkl files are deserialized with joblib (pickle). "
        "Only upload bundles you have trained yourself. "
        "Never upload files from untrusted third parties.",
        "warning",
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

        st.divider()
        st.markdown("**Upload Files**")

        f_model   = st.file_uploader("model.pkl",   type=["pkl"],  key="mh_up_model")
        f_columns = st.file_uploader("columns.pkl", type=["pkl"],  key="mh_up_columns")
        f_schema  = st.file_uploader("schema.json", type=["json"], key="mh_up_schema")

        uploaded_names = []
        if f_model:   uploaded_names.append("model.pkl")
        if f_columns: uploaded_names.append("columns.pkl")
        if f_schema:  uploaded_names.append("schema.json")

        missing = validate_bundle_files(uploaded_names)
        if missing and uploaded_names:
            _msg(f"Bundle incomplete. Still missing: {', '.join(missing)}", "warning")

        if st.button(
            ":material/cloud_upload: Upload Bundle",
            key="mh_do_upload",
            disabled=bool(missing) or not display_name or not target,
            type="primary",
        ):
            _do_upload(
                f_model.read(), f_columns.read(), f_schema.read(),
                display_name, description, target, family_id,
                user, registry,
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
) -> None:
    uploaded_by = user.get("email") or user.get("username") or "admin"

    with st.spinner("Validating and uploading bundle..."):
        try:
            result = upload_bundle(
                model_bytes   = model_bytes,
                columns_bytes = columns_bytes,
                schema_bytes  = schema_bytes,
                display_name  = display_name,
                description   = description,
                target        = target,
                uploaded_by   = uploaded_by,
                family_id     = family_id or None,
            )
        except (ValueError, RuntimeError) as exc:
            _msg(f"Upload failed: {exc}", "error")
            return

    for w in result.warnings:
        _msg(w, "warning")

    # Add to registry and push
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

        # Conditional constraints
        if new_ui == "slider" or new_ui == "number_input":
            nc1, nc2, nc3 = st.columns(3)
            new_min     = nc1.number_input("Min", value=0.0, key="mh_se_min")
            new_max     = nc2.number_input("Max", value=100.0, key="mh_se_max")
            new_default = nc3.number_input("Default", value=0.0, key="mh_se_default")
            new_step    = st.number_input("Step (optional, 0 = auto)", value=0.0, key="mh_se_step", min_value=0.0)
        elif new_ui == "selectbox":
            raw_values  = st.text_input(
                "Allowed values (comma-separated)",
                key="mh_se_values",
                placeholder="Data Scientist, ML Engineer, Software Engineer",
            )
            new_default = st.text_input("Default value (optional)", key="mh_se_default_cat")
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
                elif new_ui == "checkbox":
                    entry["default"] = bool(new_default)

                st.session_state["mh_schema_fields"].append(entry)
                _msg(f"Field '{new_name}' added.", "success")
                st.rerun()

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
        "If you want to update a model bundle's schema without re-uploading "
        "model.pkl and columns.pkl, enter the bundle path below."
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

    if st.button(":material/cloud_upload: Push schema.json to bundle", key="mh_sv_push",
                 disabled=not bundle_path or not model_id):
        try:
            upload_schema_only(raw, model_id, bundle_path)
            clear_bundle_cache(model_id)
            _msg(
                f"schema.json pushed to '{bundle_path}'. "
                "Model cache cleared — next prediction will use the new schema.",
                "success",
            )
        except (ValueError, RuntimeError) as exc:
            _msg(f"Push failed: {exc}", "error")