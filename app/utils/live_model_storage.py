"""
live_model_storage.py
=====================
Permanent versioned model storage using the HuggingFace Hub (free tier).

Setup (one-time)
----------------
1. Register free at https://huggingface.co
2. Create a private model repository, e.g. "yourname/salaryscope-live"
3. Generate a write-access token at Settings > Access Tokens
4. Add to .streamlit/secrets.toml (local) and Streamlit Cloud Secrets:

    HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxx"
    HF_REPO  = "yourname/salaryscope-live"

Storage layout in the HF repo
-------------------------------
  live_model_current.pkl       always-latest trained model
  live_model_<version>.pkl     every versioned snapshot (kept permanently)
  rollback_ledger.json         ordered history with metrics

Rollback design
---------------
- Every upload writes a versioned snapshot AND updates current.
- rollback_to_version() downloads the chosen snapshot and promotes it
  to current, then updates the ledger.
- On next "Load Model" click in the prediction panel, the rolled-back
  version is served.

Rollback note for this file
---------------------------
Remove import from live_training_tab.py to disable HuggingFace entirely.
"""

from __future__ import annotations

import io
import json
import hashlib
import datetime

import streamlit as st

CURRENT_FILENAME    = "live_model_current.pkl"
LEDGER_FILENAME     = "rollback_ledger.json"
MAX_LEDGER_VERSIONS = 10


def _get_credentials() -> tuple[str | None, str | None]:
    try:
        token = st.secrets.get("HF_TOKEN")
        repo  = st.secrets.get("HF_REPO")
        if token and repo:
            return str(token), str(repo)
    except Exception:
        pass
    return None, None


def _get_api():
    try:
        from huggingface_hub import HfApi
        token, _ = _get_credentials()
        if not token:
            return None
        return HfApi(token=token)
    except (ImportError, Exception):
        return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_ledger(api, repo: str) -> list[dict]:
    try:
        from huggingface_hub import hf_hub_download
        token, _ = _get_credentials()
        path = hf_hub_download(
            repo_id=repo, filename=LEDGER_FILENAME,
            repo_type="model", token=token,
        )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_ledger(api, repo: str, entries: list[dict]) -> str | None:
    try:
        content = json.dumps(entries, indent=2, ensure_ascii=False).encode("utf-8")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content),
            path_in_repo=LEDGER_FILENAME,
            repo_id=repo,
            repo_type="model",
            commit_message="Update rollback ledger",
        )
        return None
    except Exception as exc:
        return str(exc)


def is_storage_configured() -> bool:
    token, repo = _get_credentials()
    return token is not None and repo is not None


def upload_model(
    model_bytes: bytes,
    version: str,
    metadata: dict,
) -> tuple[str | None, str | None]:
    """Upload model. Returns (versioned_filename, error)."""
    token, repo = _get_credentials()
    if not token or not repo:
        return None, "HF_TOKEN or HF_REPO not configured."

    api = _get_api()
    if api is None:
        return None, "huggingface_hub not installed or API init failed."

    versioned_filename = f"live_model_{version}.pkl"

    try:
        api.upload_file(
            path_or_fileobj=io.BytesIO(model_bytes),
            path_in_repo=versioned_filename,
            repo_id=repo, repo_type="model",
            commit_message=f"Add versioned model snapshot {version}",
        )
        api.upload_file(
            path_or_fileobj=io.BytesIO(model_bytes),
            path_in_repo=CURRENT_FILENAME,
            repo_id=repo, repo_type="model",
            commit_message=f"Update current model to {version}",
        )
    except Exception as exc:
        return None, f"Upload failed: {exc}"

    ledger = _load_ledger(api, repo)
    for e in ledger:
        e["is_current"] = False
    ledger.append({
        "version":     version,
        "filename":    versioned_filename,
        "sha256":      _sha256(model_bytes),
        "trained_at":  metadata.get("trained_at", ""),
        "n_samples":   metadata.get("n_samples", 0),
        "test_r2":     metadata.get("test_r2", 0.0),
        "test_mae":    metadata.get("test_mae", 0.0),
        "is_current":  True,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
    })
    if len(ledger) > MAX_LEDGER_VERSIONS:
        ledger = ledger[-MAX_LEDGER_VERSIONS:]

    err = _save_ledger(api, repo, ledger)
    if err:
        return versioned_filename, f"Model uploaded but ledger failed: {err}"

    return versioned_filename, None


def download_current_model() -> tuple[bytes | None, str | None]:
    """Download the current model. Returns (bytes, error)."""
    token, repo = _get_credentials()
    if not token or not repo:
        return None, "HF_TOKEN or HF_REPO not configured."
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=repo, filename=CURRENT_FILENAME,
            repo_type="model", token=token, force_download=True,
        )
        with open(path, "rb") as f:
            return f.read(), None
    except Exception as exc:
        return None, f"Download failed: {exc}"


def download_version(filename: str) -> tuple[bytes | None, str | None]:
    """Download a specific versioned snapshot."""
    token, repo = _get_credentials()
    if not token or not repo:
        return None, "HF_TOKEN or HF_REPO not configured."
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=repo, filename=filename,
            repo_type="model", token=token, force_download=True,
        )
        with open(path, "rb") as f:
            return f.read(), None
    except Exception as exc:
        return None, f"Download failed: {exc}"


def get_ledger() -> tuple[list[dict], str | None]:
    """Return the rollback ledger. Returns (entries, error)."""
    token, repo = _get_credentials()
    if not token or not repo:
        return [], "HF_TOKEN or HF_REPO not configured."
    api = _get_api()
    if api is None:
        return [], "huggingface_hub not available."
    try:
        return _load_ledger(api, repo), None
    except Exception as exc:
        return [], str(exc)


def rollback_to_version(filename: str) -> tuple[bool, str]:
    """
    Promote a versioned snapshot to current.
    Returns (success, message).
    """
    token, repo = _get_credentials()
    if not token or not repo:
        return False, "HF_TOKEN or HF_REPO not configured."

    api = _get_api()
    if api is None:
        return False, "huggingface_hub not available."

    model_bytes, err = download_version(filename)
    if err:
        return False, f"Could not download {filename}: {err}"

    try:
        api.upload_file(
            path_or_fileobj=io.BytesIO(model_bytes),
            path_in_repo=CURRENT_FILENAME,
            repo_id=repo, repo_type="model",
            commit_message=f"Rollback: promote {filename} to current",
        )
    except Exception as exc:
        return False, f"Rollback upload failed: {exc}"

    ledger = _load_ledger(api, repo)
    for e in ledger:
        e["is_current"] = e["filename"] == filename
    err = _save_ledger(api, repo, ledger)
    if err:
        return True, f"Rollback successful but ledger update failed: {err}"

    return True, f"Successfully rolled back to {filename}."
