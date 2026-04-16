"""
_hf_client.py
=============
HuggingFace Dataset Repo helpers for the Model Hub.

Uses the official `huggingface_hub` SDK (v0.20+) instead of raw HTTP calls.
The old raw-requests approach used a deprecated upload endpoint (HTTP 410).
The SDK always uses the correct current API internally.

Install requirement
-------------------
    pip install huggingface_hub>=0.20

Secrets
-------
HF_TOKEN   — HuggingFace access token with write scope.
HF_REPO_ID — Dataset repo in the form "owner/repo-name".

Both are read from st.secrets first, then os.environ.
Never hard-coded here.

Security
--------
- Private repos are fully supported — token is passed on every call.
- Pickle loading is NOT done here. loader.py handles that with size checks.
- Token is never logged or printed.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Suppress the noisy "Xet Storage fallback" info message that huggingface_hub
# emits when uploading BytesIO objects. The upload still works correctly via
# standard HTTP — Xet just requires a file path rather than a buffer, so the
# SDK falls back transparently. No action needed from our side.
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Configuration — resolved once at import time
# ---------------------------------------------------------------------------

def _get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read from st.secrets first, then env, then default."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, default)


HF_TOKEN:   Optional[str] = _get_secret("HF_TOKEN")
HF_REPO_ID: str           = _get_secret("HF_REPO_ID") or "__unset__"

REGISTRY_PATH: str = "models_registry.json"

# Size limits — enforced by callers before passing data here
MAX_MODEL_FILE_BYTES: int = 200 * 1024 * 1024   # 200 MB


# ---------------------------------------------------------------------------
# Internal: get a configured HfApi instance
# ---------------------------------------------------------------------------

def _api():
    """Return a HfApi instance configured with the current token."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise RuntimeError(
            "huggingface_hub is not installed. "
            "Add `huggingface_hub>=0.20` to your requirements.txt and reinstall."
        )
    return HfApi(token=HF_TOKEN or None)


def _check_repo_configured() -> None:
    if HF_REPO_ID == "__unset__" or not HF_REPO_ID:
        raise EnvironmentError(
            "HuggingFace repo not configured. "
            "Set HF_REPO_ID in .streamlit/secrets.toml:\n"
            '    HF_REPO_ID = "your-username/your-repo-name"'
        )


def _check_token_configured() -> None:
    if not HF_TOKEN:
        raise PermissionError(
            "HF_TOKEN is not set. "
            "Add it to .streamlit/secrets.toml:\n"
            '    HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxx"\n'
            "The token needs write scope for uploads."
        )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_file_bytes(path_in_repo: str, force: bool = False) -> bytes:
    """
    Download a single file from the HuggingFace dataset repo.
    Returns raw bytes.

    Parameters
    ----------
    path_in_repo : Path within the repo (e.g. 'models/model_abc/schema.json').
    force        : If True, bypass the huggingface_hub local disk cache and
                   always fetch from the remote. Use for small metadata files
                   (schema.json, aliases.json) that may be updated in-place.
                   Leave False for large binary files (model.pkl) that are
                   immutable once written to a versioned bundle folder.

    Raises:
        FileNotFoundError -- file does not exist (404)
        PermissionError  -- auth failure (401/403)
        RuntimeError     -- any other error
    """
    _check_repo_configured()

    try:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError
    except ImportError:
        raise RuntimeError("huggingface_hub>=0.20 is required.")

    try:
        local_path = hf_hub_download(
            repo_id        = HF_REPO_ID,
            filename       = path_in_repo,
            repo_type      = "dataset",
            token          = HF_TOKEN or None,
            force_download = force,
        )
        with open(local_path, "rb") as f:
            return f.read()

    except EntryNotFoundError:
        raise FileNotFoundError(
            f"File '{path_in_repo}' not found in repo '{HF_REPO_ID}'."
        )
    except RepositoryNotFoundError:
        raise FileNotFoundError(
            f"Repo '{HF_REPO_ID}' not found or not accessible. "
            "Check HF_REPO_ID and that HF_TOKEN has access to this repo."
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
            raise PermissionError(
                f"Access denied to '{path_in_repo}'. "
                "Check that HF_TOKEN is valid and has read access."
            )
        raise RuntimeError(
            f"Could not download '{path_in_repo}' from '{HF_REPO_ID}': {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_file_bytes(
    path_in_repo: str,
    data: bytes,
    commit_message: str = "Upload via Model Hub",
) -> None:
    """
    Upload raw bytes to path_in_repo in the HuggingFace dataset repo.

    Uses HfApi.create_commit with CommitOperationAdd — the correct current API.
    The old /upload/ endpoint that returned HTTP 410 is NOT used here.

    Raises:
        PermissionError -- token missing or lacks write access
        RuntimeError    -- any upload or commit failure
    """
    _check_repo_configured()
    _check_token_configured()

    try:
        from huggingface_hub import CommitOperationAdd
    except ImportError:
        raise RuntimeError("huggingface_hub>=0.20 is required.")

    api = _api()

    operation = CommitOperationAdd(
        path_in_repo    = path_in_repo,
        path_or_fileobj = io.BytesIO(data),
    )

    try:
        api.create_commit(
            repo_id        = HF_REPO_ID,
            repo_type      = "dataset",
            operations     = [operation],
            commit_message = commit_message,
        )
        logger.debug("Uploaded '%s' to '%s'.", path_in_repo, HF_REPO_ID)

    except Exception as exc:
        msg = str(exc).lower()
        if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg:
            raise PermissionError(
                f"Upload of '{path_in_repo}' failed — access denied. "
                "Ensure HF_TOKEN has write scope on this dataset repo."
            )
        raise RuntimeError(
            f"Upload of '{path_in_repo}' to '{HF_REPO_ID}' failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# File size check (non-blocking — returns None if unavailable)
# ---------------------------------------------------------------------------

def file_size_bytes(path_in_repo: str) -> Optional[int]:
    """
    Return the size in bytes of a file in the repo without downloading it.
    Returns None if the size cannot be determined (non-fatal).
    """
    _check_repo_configured()
    try:
        api  = _api()
        info = api.get_paths_info(
            repo_id   = HF_REPO_ID,
            paths     = [path_in_repo],
            repo_type = "dataset",
        )
        if info:
            return getattr(info[0], "size", None)
    except Exception as exc:
        logger.debug("Could not check file size for '%s': %s", path_in_repo, exc)
    return None


# ---------------------------------------------------------------------------
# List repo files under a prefix
# ---------------------------------------------------------------------------

def list_repo_paths(prefix: str = "models/") -> list[str]:
    """
    List all file paths in the repo under the given prefix.
    Returns [] on any error (non-fatal).
    """
    _check_repo_configured()
    try:
        api   = _api()
        items = api.list_repo_tree(
            repo_id      = HF_REPO_ID,
            path_in_repo = prefix,
            repo_type    = "dataset",
            recursive    = True,
        )
        return [item.path for item in items if hasattr(item, "path")]
    except Exception as exc:
        logger.debug("list_repo_paths error: %s", exc)
    return []