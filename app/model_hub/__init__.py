"""
app/model_hub/__init__.py
=========================
Model Hub package.

Public surface
--------------
Import from the specific submodules for clarity.
This __init__ only re-exports the most commonly needed symbols
to reduce verbosity at call sites.
"""

from app.model_hub.registry import (
    fetch_registry,
    get_active_models,
    get_model_by_id,
    add_model_to_registry,
    set_model_active,
    rollback_to_version,
    push_registry,
)

from app.model_hub.loader import (
    load_bundle,
    clear_bundle_cache,
    ModelBundle,
)

from app.model_hub.predictor import predict, PredictionResult
from app.model_hub.schema_parser import render_schema_form
from app.model_hub.validator import (
    validate_schema,
    validate_schema_vs_columns,
    validate_bundle_files,
    validate_aliases,
    parse_schema_json,
)
from app.model_hub.uploader import upload_bundle, upload_schema_only, upload_aliases_only

__all__ = [
    # registry
    "fetch_registry",
    "get_active_models",
    "get_model_by_id",
    "add_model_to_registry",
    "set_model_active",
    "rollback_to_version",
    "push_registry",
    # loader
    "load_bundle",
    "clear_bundle_cache",
    "ModelBundle",
    # predictor
    "predict",
    "PredictionResult",
    # schema
    "render_schema_form",
    # validator
    "validate_schema",
    "validate_schema_vs_columns",
    "validate_bundle_files",
    "validate_aliases",
    "parse_schema_json",
    # uploader
    "upload_bundle",
    "upload_schema_only",
    "upload_aliases_only",
]
