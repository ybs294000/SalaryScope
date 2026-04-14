# account_management.py
#
# Provides three self-contained account management UI functions:
#
#   render_change_password_ui()  -- change password with current-password
#                                   confirmation and strength validation
#   render_delete_account_ui()   -- permanent account deletion with
#                                   password confirmation and typed phrase
#   render_confirm_password_ui() -- re-authentication widget (shared helper;
#                                   may also be called from other modules)
#
# Each function is independently rollbackable -- see the Rollback note
# at the top of each section below.
#
# Dependencies (no circular imports):
#   - streamlit
#   - requests
#   - app.core.rate_limiter  (optional, lazy import; fails open if absent)
#   - app.core.password_policy (lazy import inside render_change_password_ui)
#   - app.core.auth (get_logged_in_user; lazy import to avoid circular dep)
#   - app.core.database (_db, clear_pending_verification_db; lazy import,
#     only in render_delete_account_ui)
#
# Integration:
#   In user_profile.py, call render_account_management_section() once,
#   before the logout button. That is the only symbol imported from here.
#
# -- ROLLBACK: change_password --
#   Remove render_change_password_ui from this file.
#   Remove its call in render_account_management_section.
#
# -- ROLLBACK: delete_account --
#   Remove render_delete_account_ui from this file.
#   Remove its call in render_account_management_section.
#
# -- ROLLBACK: entire module --
#   In user_profile.py, remove the import of render_account_management_section
#   and its three call sites. Delete this file.

import streamlit as st
import requests as http_requests

_FIREBASE_AUTH_BASE: str = "https://identitytoolkit.googleapis.com/v1/accounts"

# Session-state key used to carry the deletion-success flag across the
# st.rerun() boundary in render_delete_account_ui.
_DELETE_SUCCESS_KEY: str = "_acct_mgmt_delete_success"


# ---------------------------------------------------------------------------
# MODULE-LEVEL HELPERS
# No external I/O at import time. All Firebase calls go through _safe_post.
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """
    Return the Firebase API key from st.secrets.

    Returns an empty string if the key is missing or if st.secrets is
    unavailable. Callers treat an empty string as "Firebase not configured".
    """
    try:
        key = st.secrets.get("FIREBASE_API_KEY")
        return key if isinstance(key, str) and key else ""
    except Exception:
        return ""


def _safe_post(url: str, payload: dict) -> dict:
    """
    POST payload to url as JSON and return the parsed response dict.

    Always returns a dict. On any network or parse failure, returns a dict
    with an "error" key containing a normalised message code so that callers
    can use a single code path for both Firebase errors and local errors.
    """
    try:
        resp = http_requests.post(url, json=payload, timeout=8)
        try:
            return resp.json()
        except ValueError:
            # Firebase returned a non-JSON body (e.g. 502 from their CDN).
            return {
                "error": {
                    "message": f"INVALID_RESPONSE_{resp.status_code}"
                }
            }
    except http_requests.exceptions.Timeout:
        return {"error": {"message": "NETWORK_TIMEOUT"}}
    except http_requests.exceptions.ConnectionError:
        return {"error": {"message": "NO_INTERNET"}}
    except Exception:
        return {"error": {"message": "NETWORK_ERROR"}}


def _firebase_error_message(response: dict) -> str:
    """
    Translate a Firebase REST API error response into a user-facing string.

    Falls back to a sanitised version of the raw code for any unknown error.
    Handles malformed response dicts defensively.
    """
    if not isinstance(response, dict):
        return "An unexpected error occurred. Please try again."

    error_block = response.get("error")
    if not isinstance(error_block, dict):
        return "An unexpected error occurred. Please try again."

    raw = error_block.get("message", "UNKNOWN_ERROR")
    if not isinstance(raw, str):
        raw = "UNKNOWN_ERROR"

    mapping: dict = {
        "INVALID_LOGIN_CREDENTIALS": "Incorrect password.",
        "INVALID_PASSWORD":          "Incorrect password.",
        "EMAIL_NOT_FOUND":           "No account found with this email.",
        "USER_DISABLED":             "This account has been disabled.",
        "WEAK_PASSWORD : Password should be at least 6 characters": (
            "Password must be at least 6 characters."
        ),
        "TOO_MANY_ATTEMPTS_TRY_LATER": (
            "Too many attempts. Please wait before trying again."
        ),
        "CREDENTIAL_TOO_OLD_LOGIN_AGAIN": (
            "Your session is too old to perform this action. "
            "Please log out and log back in."
        ),
        "TOKEN_EXPIRED":  "Your session has expired. Please log out and log back in.",
        "INVALID_ID_TOKEN": "Your session is invalid. Please log out and log back in.",
        "AUTH_DISABLED":  "Authentication is not configured.",
        "NETWORK_TIMEOUT": "Request timed out. Please try again.",
        "NO_INTERNET":     "No internet connection.",
        "NETWORK_ERROR":   "Network error. Please try again.",
    }

    # Cover non-JSON CDN responses like INVALID_RESPONSE_502.
    if raw.startswith("INVALID_RESPONSE_"):
        return "Firebase returned an unexpected response. Please try again."

    return mapping.get(raw, raw.replace("_", " ").capitalize())


def _re_authenticate(email: str, password: str) -> dict:
    """
    Re-authenticate the current user via the Firebase signInWithPassword
    endpoint. Returns the raw response dict (always a dict, never raises).
    """
    api_key = _get_api_key()
    if not api_key:
        return {"error": {"message": "AUTH_DISABLED"}}

    url = f"{_FIREBASE_AUTH_BASE}:signInWithPassword?key={api_key}"
    return _safe_post(url, {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })


def _firebase_update_password(id_token: str, new_password: str) -> dict:
    """
    Change the Firebase account password for the given id_token.
    Returns the raw response dict (always a dict, never raises).
    """
    api_key = _get_api_key()
    if not api_key:
        return {"error": {"message": "AUTH_DISABLED"}}

    url = f"{_FIREBASE_AUTH_BASE}:update?key={api_key}"
    return _safe_post(url, {
        "idToken": id_token,
        "password": new_password,
        "returnSecureToken": True,
    })


def _firebase_delete_account(id_token: str) -> dict:
    """
    Permanently delete the Firebase Authentication account for id_token.
    Returns the raw response dict (always a dict, never raises).
    """
    api_key = _get_api_key()
    if not api_key:
        return {"error": {"message": "AUTH_DISABLED"}}

    url = f"{_FIREBASE_AUTH_BASE}:delete?key={api_key}"
    return _safe_post(url, {"idToken": id_token})


def _get_rate_limiter():
    """
    Lazily import rate_limiter functions.

    Returns (check_rate_limit, record_attempt, clear_attempts) if the
    module is available, or (None, None, None) if it has been rolled back.
    The None fallback means rate limiting is silently skipped rather than
    crashing the auth flow.
    """
    try:
        from app.core.rate_limiter import (
            check_rate_limit,
            record_attempt,
            clear_attempts,
        )
        return check_rate_limit, record_attempt, clear_attempts
    except ImportError:
        return None, None, None
    except Exception:
        return None, None, None


def _get_logged_in_user() -> str:
    """
    Lazily import and call get_logged_in_user from auth.py.
    Returns None on any import or runtime error.
    """
    try:
        from app.core.auth import get_logged_in_user
        return get_logged_in_user()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# render_confirm_password_ui
# ---------------------------------------------------------------------------
# Rollback: remove this function only when both render_change_password_ui
# and render_delete_account_ui have also been removed.

def render_confirm_password_ui(
    email: str,
    action_label: str = "continue",
    key_prefix: str = "confirm",
) -> str:
    """
    Render a confirm-password sub-form and return a fresh Firebase id_token
    on successful re-authentication, or None if not yet confirmed or if
    confirmation failed.

    Parameters
    ----------
    email        : the current user's email address
    action_label : short description used in the prompt text
    key_prefix   : unique widget-key prefix to prevent key collisions
                   when used in multiple places on the same page

    Returns None for every Streamlit run where the user has not yet clicked
    the confirm button, or where the button was clicked but failed.
    """
    if not isinstance(email, str) or not email:
        st.error("Cannot confirm identity: no user email found in session.")
        return None

    st.caption(f"To {action_label}, please confirm your current password.")

    password = st.text_input(
        "Current Password",
        type="password",
        key=f"{key_prefix}_confirm_pw",
    )

    if not st.button(
        "Confirm Identity",
        key=f"{key_prefix}_confirm_btn",
        use_container_width=True,
    ):
        return None

    if not password:
        st.warning("Please enter your current password.")
        return None

    # Rate limiting (rollbackable; fails open if module absent).
    # -- ROLLBACK: rate_limiter --
    check_rl, rec_attempt, clr_attempts = _get_rate_limiter()
    if check_rl is not None:
        try:
            allowed, msg = check_rl(f"{key_prefix}_confirm", email)
            if not allowed:
                st.error(msg)
                return None
        except Exception:
            pass  # fail open
    # -- ROLLBACK: rate_limiter end --

    result = _re_authenticate(email, password)

    if "error" in result:
        st.error(_firebase_error_message(result))
        # -- ROLLBACK: rate_limiter --
        if rec_attempt is not None:
            try:
                rec_attempt(f"{key_prefix}_confirm", email)
            except Exception:
                pass
        # -- ROLLBACK: rate_limiter end --
        return None

    # Clear the rate-limit counter on success.
    # -- ROLLBACK: rate_limiter --
    if clr_attempts is not None:
        try:
            clr_attempts(f"{key_prefix}_confirm", email)
        except Exception:
            pass
    # -- ROLLBACK: rate_limiter end --

    id_token = result.get("idToken")
    if not isinstance(id_token, str) or not id_token:
        st.error(
            "Re-authentication succeeded but no token was returned. "
            "Please try again."
        )
        return None

    return id_token


# ---------------------------------------------------------------------------
# render_change_password_ui
# ---------------------------------------------------------------------------
# Rollback: remove this function and its call in
# render_account_management_section.

def render_change_password_ui() -> None:
    """
    Render the change-password section inside the user profile page.

    Flow:
      1. User enters current password (re-authentication via Firebase).
      2. User enters new password twice.
      3. New password is validated against the password policy.
      4. Firebase password update is called with the fresh id_token.
      5. Session id_token is updated in place -- the user stays logged in.

    Wrapped in a collapsed st.expander so it occupies no space by default.
    """
    # -- ROLLBACK: change_password (start) --
    with st.expander("Change Password", expanded=False):

        email = _get_logged_in_user()
        if not email:
            st.warning("You must be logged in to change your password.")
            return

        # Lazily import password policy (rollbackable).
        # -- ROLLBACK: password_policy --
        try:
            from app.core.password_policy import (
                validate_password_strength,
                password_strength_hint,
            )
            hint = password_strength_hint()
            policy_available = True
        except ImportError:
            validate_password_strength = None
            hint = "Minimum 6 characters."
            policy_available = False
        # -- ROLLBACK: password_policy end --

        st.caption("Password requirements: " + hint)

        st.markdown("**Step 1: Confirm your identity**")
        current_pw = st.text_input(
            "Current Password",
            type="password",
            key="chpw_current",
        )

        st.markdown("**Step 2: Enter new password**")
        new_pw = st.text_input(
            "New Password",
            type="password",
            key="chpw_new",
        )
        new_pw_confirm = st.text_input(
            "Confirm New Password",
            type="password",
            key="chpw_confirm",
        )

        # Live strength feedback shown while typing (no button press needed).
        # -- ROLLBACK: password_policy --
        if new_pw and policy_available and validate_password_strength is not None:
            try:
                live_errors = validate_password_strength(new_pw)
                if live_errors:
                    for err in live_errors:
                        st.caption(f"- {err}")
            except Exception:
                pass
        # -- ROLLBACK: password_policy end --

        if not st.button(
            "Change Password",
            key="chpw_submit_btn",
            use_container_width=True,
            type="primary",
        ):
            return

        # --- Input validation ---
        if not current_pw or not new_pw or not new_pw_confirm:
            st.warning("All fields are required.")
            return

        if new_pw != new_pw_confirm:
            st.error("New passwords do not match.")
            return

        if new_pw == current_pw:
            st.error(
                "New password must be different from the current password."
            )
            return

        # --- Password policy validation ---
        # -- ROLLBACK: password_policy --
        if policy_available and validate_password_strength is not None:
            try:
                policy_errors = validate_password_strength(new_pw)
                if policy_errors:
                    for err in policy_errors:
                        st.error(err)
                    return
            except Exception as exc:
                st.error(f"Password validation error: {exc}")
                return
        # -- ROLLBACK: password_policy end --

        # --- Rate limiting ---
        # -- ROLLBACK: rate_limiter --
        check_rl, rec_attempt, clr_attempts = _get_rate_limiter()
        if check_rl is not None:
            try:
                allowed, msg = check_rl("change_password", email)
                if not allowed:
                    st.error(msg)
                    return
            except Exception:
                pass  # fail open
        # -- ROLLBACK: rate_limiter end --

        # --- Re-authenticate with current password ---
        reauth = _re_authenticate(email, current_pw)
        if "error" in reauth:
            st.error(_firebase_error_message(reauth))
            # -- ROLLBACK: rate_limiter --
            if rec_attempt is not None:
                try:
                    rec_attempt("change_password", email)
                except Exception:
                    pass
            # -- ROLLBACK: rate_limiter end --
            return

        fresh_token = reauth.get("idToken")
        if not isinstance(fresh_token, str) or not fresh_token:
            st.error("Re-authentication failed. Please try again.")
            return

        # --- Update password via Firebase ---
        update_result = _firebase_update_password(fresh_token, new_pw)
        if "error" in update_result:
            st.error(_firebase_error_message(update_result))
            # -- ROLLBACK: rate_limiter --
            if rec_attempt is not None:
                try:
                    rec_attempt("change_password", email)
                except Exception:
                    pass
            # -- ROLLBACK: rate_limiter end --
            return

        # Update the session id_token so the session stays valid.
        new_token = update_result.get("idToken")
        if isinstance(new_token, str) and new_token:
            try:
                st.session_state._firebase_id_token = new_token
            except Exception:
                pass
        else:
            # Firebase did not return a new token (unusual but possible).
            # The old token is now invalid; the user must log in again.
            try:
                st.session_state.logged_in = False
                st.session_state._firebase_id_token = None
            except Exception:
                pass
            st.warning(
                "Password changed, but your session token could not be "
                "refreshed. Please log out and log back in."
            )
            return

        # Clear rate-limit counter on success.
        # -- ROLLBACK: rate_limiter --
        if clr_attempts is not None:
            try:
                clr_attempts("change_password", email)
            except Exception:
                pass
        # -- ROLLBACK: rate_limiter end --

        st.success(
            "Password changed successfully. "
            "You are still logged in with the updated credentials."
        )
    # -- ROLLBACK: change_password (end) --


# ---------------------------------------------------------------------------
# render_delete_account_ui
# ---------------------------------------------------------------------------
# Rollback: remove this function and its call in
# render_account_management_section. Also remove _DELETE_SUCCESS_KEY usage.

_DELETE_CONFIRM_PHRASE: str = "delete my account"


def render_delete_account_ui() -> None:
    """
    Render the delete-account section inside the user profile page.

    Flow:
      1. User enters current password (re-authentication via Firebase).
      2. User types the exact phrase "delete my account" to confirm intent.
      3. Firebase Authentication account is permanently deleted.
      4. Firestore user document and pending_verifications record are deleted
         (best-effort; failure does not block the deletion).
      5. Session is cleared, a success flag is set, and st.rerun() is called.
      6. On the next run, the success message is shown before the app reloads.

    Note on st.rerun():
      st.rerun() raises a RerunException internally, which immediately aborts
      script execution. Any st.success() call placed before st.rerun() in the
      same script run will NOT be rendered. This is handled by storing a flag
      in session_state and displaying the message on the following run.

    Note on prediction history:
      Records are intentionally NOT deleted because they contain anonymised
      salary data used for model feedback and are stored under the email key
      which becomes orphaned after account deletion. A separate admin-side
      purge job is the appropriate mechanism if data removal is required.

    Wrapped in a collapsed st.expander so it occupies no space by default.
    """
    # -- ROLLBACK: delete_account (start) --

    # Show deferred success message from the previous run (post-rerun).
    if st.session_state.get(_DELETE_SUCCESS_KEY):
        try:
            del st.session_state[_DELETE_SUCCESS_KEY]
        except Exception:
            pass
        st.success(
            "Your account has been permanently deleted. "
            "You have been signed out."
        )
        return

    with st.expander("Delete Account", expanded=False):

        email = _get_logged_in_user()
        if not email:
            st.warning("You must be logged in to delete your account.")
            return

        st.warning(
            "Deleting your account is permanent and cannot be undone. "
            "Your login credentials will be removed immediately. "
            "Your prediction history will remain in the system in "
            "anonymised form."
        )

        current_pw = st.text_input(
            "Current Password",
            type="password",
            key="del_acct_pw",
        )

        typed_phrase = st.text_input(
            f'Type "{_DELETE_CONFIRM_PHRASE}" to confirm',
            key="del_acct_phrase",
        )

        if not st.button(
            "Permanently Delete My Account",
            key="del_acct_submit_btn",
            use_container_width=True,
        ):
            return

        # --- Input validation ---
        if not current_pw:
            st.warning("Please enter your current password.")
            return

        if not isinstance(typed_phrase, str):
            typed_phrase = ""

        if typed_phrase.strip().lower() != _DELETE_CONFIRM_PHRASE:
            st.error(
                f'You must type exactly "{_DELETE_CONFIRM_PHRASE}" '
                "to confirm deletion."
            )
            return

        # --- Rate limiting ---
        # -- ROLLBACK: rate_limiter --
        check_rl, rec_attempt, clr_attempts = _get_rate_limiter()
        if check_rl is not None:
            try:
                allowed, msg = check_rl("delete_account", email)
                if not allowed:
                    st.error(msg)
                    return
            except Exception:
                pass  # fail open
        # -- ROLLBACK: rate_limiter end --

        # --- Re-authenticate ---
        reauth = _re_authenticate(email, current_pw)
        if "error" in reauth:
            st.error(_firebase_error_message(reauth))
            # -- ROLLBACK: rate_limiter --
            if rec_attempt is not None:
                try:
                    rec_attempt("delete_account", email)
                except Exception:
                    pass
            # -- ROLLBACK: rate_limiter end --
            return

        fresh_token = reauth.get("idToken")
        if not isinstance(fresh_token, str) or not fresh_token:
            st.error("Re-authentication failed. Please try again.")
            return

        # --- Delete Firebase Authentication account ---
        delete_result = _firebase_delete_account(fresh_token)
        if "error" in delete_result:
            st.error(_firebase_error_message(delete_result))
            # -- ROLLBACK: rate_limiter --
            if rec_attempt is not None:
                try:
                    rec_attempt("delete_account", email)
                except Exception:
                    pass
            # -- ROLLBACK: rate_limiter end --
            return

        # --- Best-effort Firestore cleanup ---
        # Each step is wrapped independently so a failure on one does not
        # prevent the others from running.
        try:
            from app.core.database import _db
            db = _db()
            db.collection("users").document(email).delete()
        except Exception:
            pass

        try:
            from app.core.database import clear_pending_verification_db
            clear_pending_verification_db(email)
        except Exception:
            pass

        # --- Clear rate-limit records for this user ---
        # -- ROLLBACK: rate_limiter --
        if clr_attempts is not None:
            for action in ("delete_account", "change_password", "login"):
                try:
                    clr_attempts(action, email)
                except Exception:
                    pass
        # -- ROLLBACK: rate_limiter end --

        # --- Clear session state ---
        # Set all keys individually rather than clearing the whole
        # session_state to avoid wiping unrelated state managed by other
        # modules (e.g. model caches, db_initialized).
        for key in (
            "logged_in",
            "_firebase_id_token",
            "_session_expiry",
            "username",
            "is_admin",
            "auth_loading",
        ):
            try:
                st.session_state[key] = None if key != "logged_in" else False
            except Exception:
                pass

        # Set the deferred success flag BEFORE calling st.rerun(), because
        # st.rerun() raises RerunException immediately and nothing after it
        # in this script run will execute.
        try:
            st.session_state[_DELETE_SUCCESS_KEY] = True
        except Exception:
            pass

        st.rerun()
    # -- ROLLBACK: delete_account (end) --


# ---------------------------------------------------------------------------
# render_account_management_section
# ---------------------------------------------------------------------------
# Single entry point called from user_profile.show_profile().
# Rollback (entire module): remove this call from user_profile.py and
# remove the import. Delete this file.

def render_account_management_section() -> None:
    """
    Render all account management widgets under a labelled section.

    Call this once in show_profile(), before the logout button.
    """
    st.divider()
    st.subheader("Account Management")

    render_change_password_ui()   # -- ROLLBACK: change_password
    render_delete_account_ui()    # -- ROLLBACK: delete_account
