# rate_limiter.py
#
# Provides per-action, per-identifier rate limiting suitable for
# Streamlit Cloud (single-process, no shared memory between sessions).
#
# Architecture
# ------------
# Streamlit Cloud runs each user in an isolated Python process. There is
# no shared in-process state between users. A purely in-process store
# (dict) would therefore only limit within one user's session, which is
# insufficient for brute-force protection across users.
#
# This module uses a two-layer approach:
#   Layer 1 -- st.session_state (per-tab, instant, zero latency)
#              Prevents rapid repeated submissions within a single session.
#   Layer 2 -- Firestore (persistent, cross-session)
#              Tracks attempts per (action, identifier) with a logical TTL.
#              Firestore reads/writes add ~100-300 ms per check; performed
#              only on button-click submissions, not on every keystroke.
#
# Both layers fail open -- a Firestore outage or any unexpected error
# never blocks a legitimate user.
#
# Rate limit configuration
# ------------------------
# Defined in _LIMITS: (max_attempts, window_seconds) per action.
# Adjust here without touching any other file.
#
# Actions defined:
#   login           -- sign-in attempts per email
#   register        -- account-creation attempts per email
#   resend_verify   -- verification-email resend requests per email
#   change_password -- password-change attempts per email
#   delete_account  -- account-deletion attempts per email
#   forgot_password -- password-reset email requests per email
#
# Rollback:
#   Delete this file.
#   In auth.py, remove the import of check_rate_limit / record_attempt /
#   clear_attempts and all tagged call sites.
#   In account_management.py, do the same.
#   Optionally drop the Firestore "rate_limits" collection; stale documents
#   expire naturally via the client-side TTL logic on next access.
#   No schema migration required.

import hashlib
import time

import streamlit as st

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

_LIMITS: dict = {
    "login":           (5, 300),    # 5 attempts per 5 minutes
    "register":        (3, 600),    # 3 attempts per 10 minutes
    "resend_verify":   (3, 600),    # 3 requests per 10 minutes
    "change_password": (3, 600),    # 3 attempts per 10 minutes
    "delete_account":  (3, 600),    # 3 attempts per 10 minutes
    "forgot_password": (3, 600),    # 3 requests per 10 minutes
}

_SESSION_PREFIX: str = "_rl_"


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def check_rate_limit(action: str, identifier: str) -> tuple:
    """
    Check whether the (action, identifier) pair is currently rate-limited.

    Returns:
        (allowed: bool, error_message: str | None)
        allowed=True  -> caller may proceed
        allowed=False -> caller is blocked; error_message explains why

    Checks the session layer first (zero latency), then Firestore.
    Fails open on any error in either layer.
    """
    if not isinstance(action, str) or not isinstance(identifier, str):
        return True, None

    if action not in _LIMITS:
        return True, None

    max_attempts, window_seconds = _LIMITS[action]

    # Layer 1: session-state check
    try:
        blocked, wait = _session_check(
            action, identifier, max_attempts, window_seconds
        )
        if blocked:
            return False, _blocked_message(wait)
    except Exception:
        pass  # fail open

    # Layer 2: Firestore check
    try:
        blocked, wait = _firestore_check(
            action, identifier, max_attempts, window_seconds
        )
        if blocked:
            return False, _blocked_message(wait)
    except Exception:
        pass  # fail open

    return True, None


def record_attempt(action: str, identifier: str) -> None:
    """
    Record one failed attempt for (action, identifier).

    Call this AFTER a failed operation (wrong password, API error, etc.).
    Do NOT call this on success -- use clear_attempts() instead.

    Silently ignores all errors so that a logging failure never breaks
    the authentication flow.
    """
    if not isinstance(action, str) or not isinstance(identifier, str):
        return

    if action not in _LIMITS:
        return

    try:
        _session_record(action, identifier)
    except Exception:
        pass

    try:
        _firestore_record(action, identifier)
    except Exception:
        pass


def clear_attempts(action: str, identifier: str) -> None:
    """
    Reset the attempt counter for (action, identifier).

    Call this after a successful authentication event to prevent a
    legitimate user from being locked out by their own past failures.

    Silently ignores all errors.
    """
    if not isinstance(action, str) or not isinstance(identifier, str):
        return

    try:
        _session_clear(action, identifier)
    except Exception:
        pass

    try:
        _firestore_clear(action, identifier)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SESSION LAYER (Layer 1)
# ---------------------------------------------------------------------------

def _session_key(action: str, identifier: str) -> str:
    # Replace characters that can cause issues as dict keys in session_state.
    safe = identifier.replace("@", "_at_").replace(".", "_")
    return f"{_SESSION_PREFIX}{action}_{safe}"


def _session_check(
    action: str,
    identifier: str,
    max_attempts: int,
    window_seconds: int,
) -> tuple:
    """
    Returns (is_blocked: bool, seconds_remaining: float).

    Handles corrupted or unexpected session_state values by treating
    them as an absent record (fail open).
    """
    key = _session_key(action, identifier)
    record = st.session_state.get(key)

    if record is None:
        return False, 0.0

    # Guard against a corrupted session_state value (wrong type or length).
    if not isinstance(record, (tuple, list)) or len(record) != 2:
        # Stale or corrupted -- clear it and fail open.
        try:
            del st.session_state[key]
        except Exception:
            pass
        return False, 0.0

    try:
        attempts = int(record[0])
        window_start = float(record[1])
    except (TypeError, ValueError):
        try:
            del st.session_state[key]
        except Exception:
            pass
        return False, 0.0

    now = time.time()
    elapsed = now - window_start

    # Guard against clock skew producing a negative elapsed time.
    if elapsed < 0:
        elapsed = 0.0

    if elapsed > window_seconds:
        # Window expired -- clean up and allow.
        try:
            del st.session_state[key]
        except Exception:
            pass
        return False, 0.0

    if attempts >= max_attempts:
        return True, max(0.0, window_seconds - elapsed)

    return False, 0.0


def _session_record(action: str, identifier: str) -> None:
    _, window_seconds = _LIMITS[action]
    key = _session_key(action, identifier)
    record = st.session_state.get(key)
    now = time.time()

    # If the existing record is malformed, reset it.
    if record is not None:
        if (
            not isinstance(record, (tuple, list))
            or len(record) != 2
        ):
            record = None
        else:
            try:
                _attempts = int(record[0])
                _window_start = float(record[1])
            except (TypeError, ValueError):
                record = None

    if record is None:
        st.session_state[key] = (1, now)
        return

    attempts = int(record[0])
    window_start = float(record[1])

    if now - window_start > window_seconds or now - window_start < 0:
        # Window expired or clock skew -- start a new window.
        st.session_state[key] = (1, now)
    else:
        st.session_state[key] = (attempts + 1, window_start)


def _session_clear(action: str, identifier: str) -> None:
    key = _session_key(action, identifier)
    st.session_state.pop(key, None)


# ---------------------------------------------------------------------------
# FIRESTORE LAYER (Layer 2)
# ---------------------------------------------------------------------------
# Collection : rate_limits
# Document ID: "{action}__{sha256_prefix_of_identifier}"
# Fields     : attempts (int), window_start (float epoch seconds)
#
# Firestore has no native TTL. Expiry is enforced client-side by comparing
# window_start to the current time. Stale documents are deleted lazily on
# the next access for that key.

def _fs_doc_id(action: str, identifier: str) -> str:
    """
    Derive a Firestore document ID from the action and identifier.
    The identifier is hashed so that PII (email addresses) is never
    stored as a document key in plain text.
    """
    h = hashlib.sha256(identifier.lower().strip().encode("utf-8")).hexdigest()[:16]
    return f"{action}__{h}"


def _get_db():
    """
    Return the Firestore client. Raises if unavailable; callers must
    wrap in try/except.
    """
    from app.core.database import _db
    return _db()


def _parse_window_start(raw) -> float:
    """
    Coerce a Firestore window_start value to a float epoch timestamp.

    Firestore may return:
      - A float/int (stored directly)
      - An ISO-8601 string (if written by an older version of this code)
      - A datetime object (if written via the Admin SDK with SERVER_TIMESTAMP)
      - None or an unexpected type

    Returns 0.0 on any parse failure so the window is treated as expired
    (fail open).
    """
    if raw is None:
        return 0.0

    if isinstance(raw, (int, float)):
        val = float(raw)
        # Sanity-check: epoch timestamps should be > 1_000_000_000 (year 2001).
        # Negative or absurdly small values indicate corruption.
        return val if val > 1_000_000_000 else 0.0

    if isinstance(raw, str):
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError, AttributeError):
            return 0.0

    # datetime / DatetimeWithNanoseconds from the Admin SDK
    try:
        ts = raw.timestamp()
        return float(ts) if float(ts) > 1_000_000_000 else 0.0
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _firestore_check(
    action: str,
    identifier: str,
    max_attempts: int,
    window_seconds: int,
) -> tuple:
    """
    Returns (is_blocked: bool, seconds_remaining: float).
    Raises on any Firestore error; caller must wrap in try/except.
    """
    db = _get_db()
    doc_id = _fs_doc_id(action, identifier)
    doc = db.collection("rate_limits").document(doc_id).get()

    if not doc.exists:
        return False, 0.0

    data = doc.to_dict() or {}

    # Coerce attempts to int defensively.
    try:
        attempts = int(data.get("attempts", 0))
    except (TypeError, ValueError):
        attempts = 0

    window_start = _parse_window_start(data.get("window_start"))
    now = time.time()
    elapsed = now - window_start

    if elapsed < 0:
        elapsed = 0.0

    if elapsed > window_seconds:
        # Window expired -- lazily delete the stale document.
        try:
            db.collection("rate_limits").document(doc_id).delete()
        except Exception:
            pass
        return False, 0.0

    if attempts >= max_attempts:
        return True, max(0.0, window_seconds - elapsed)

    return False, 0.0


def _firestore_record(action: str, identifier: str) -> None:
    """
    Increment the attempt counter for (action, identifier) in Firestore.
    Raises on any Firestore error; caller must wrap in try/except.
    """
    _, window_seconds = _LIMITS[action]
    db = _get_db()
    doc_id = _fs_doc_id(action, identifier)
    ref = db.collection("rate_limits").document(doc_id)
    doc = ref.get()
    now = time.time()

    if not doc.exists:
        ref.set({"attempts": 1, "window_start": now})
        return

    data = doc.to_dict() or {}

    try:
        attempts = int(data.get("attempts", 0))
    except (TypeError, ValueError):
        attempts = 0

    window_start = _parse_window_start(data.get("window_start"))
    elapsed = now - window_start

    if elapsed < 0 or elapsed > window_seconds:
        # Window expired or clock skew -- start a fresh window.
        ref.set({"attempts": 1, "window_start": now})
    else:
        ref.update({"attempts": attempts + 1})


def _firestore_clear(action: str, identifier: str) -> None:
    """
    Delete the rate-limit document for (action, identifier) from Firestore.
    Raises on any Firestore error; caller must wrap in try/except.
    """
    db = _get_db()
    doc_id = _fs_doc_id(action, identifier)
    db.collection("rate_limits").document(doc_id).delete()


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _blocked_message(seconds_remaining: float) -> str:
    """
    Build a human-readable blocked message from a remaining-seconds value.

    Clamps to a minimum of 1 minute so the message is never "0 minutes".
    """
    try:
        seconds_remaining = float(seconds_remaining)
    except (TypeError, ValueError):
        seconds_remaining = 60.0

    # Always show at least 1 minute to avoid "wait 0 minutes" messages.
    minutes = max(1, int(seconds_remaining // 60) + 1)
    unit = "minute" if minutes == 1 else "minutes"
    return (
        f"Too many failed attempts. "
        f"Please wait {minutes} {unit} before trying again."
    )
