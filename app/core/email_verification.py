# email_verification.py
#
# Handles Firebase email verification for new registrations.
#
# Flow:
#   1. After Firebase account creation, call send_verification_email(id_token).
#      Firebase sends a verification link from its own mail infrastructure.
#   2. On login, call check_email_verified(id_token) to inspect the
#      emailVerified flag returned by Firebase's token lookup endpoint.
#   3. If not verified, call render_verification_pending_ui() to show the
#      waiting screen with a resend option.
#
# Rollback:
#   Delete this file. In auth.py, remove:
#     - the import line for this module
#     - the send_verification_email call in register_ui
#     - the check_email_verified call and pending-UI branch in login_ui
#   In database.py, remove:
#     - save_pending_verification and get_pending_verification functions
#   No other files are affected.
#
# No circular imports: this module only imports streamlit and makes
# HTTP calls to Firebase REST endpoints. It never imports from app.*

import streamlit as st
import requests as http_requests

FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"

_SESSION_PENDING_KEY = "_ev_pending_email"
_SESSION_PENDING_TOKEN = "_ev_pending_token"

# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _get_api_key() -> str | None:
    try:
        return st.secrets.get("FIREBASE_API_KEY")
    except Exception:
        return None


def _safe_post(url: str, payload: dict) -> dict:
    try:
        resp = http_requests.post(url, json=payload, timeout=8)
        return resp.json()
    except http_requests.exceptions.Timeout:
        return {"error": {"message": "NETWORK_TIMEOUT"}}
    except http_requests.exceptions.ConnectionError:
        return {"error": {"message": "NO_INTERNET"}}
    except Exception:
        return {"error": {"message": "NETWORK_ERROR"}}


# ---------------------------------------------------------------------------
# CORE VERIFICATION FUNCTIONS
# ---------------------------------------------------------------------------

def send_verification_email(id_token: str) -> tuple[bool, str | None]:
    """
    Ask Firebase to send an email verification link to the address
    associated with id_token.

    Returns (success: bool, error_message: str | None).
    """
    api_key = _get_api_key()
    if not api_key:
        return False, "Firebase is not configured."

    url = f"{FIREBASE_AUTH_BASE}:sendOobCode?key={api_key}"
    result = _safe_post(url, {
        "requestType": "VERIFY_EMAIL",
        "idToken": id_token,
    })

    if "error" in result:
        raw = result["error"].get("message", "UNKNOWN_ERROR")
        messages = {
            "INVALID_ID_TOKEN": "Session expired. Please register again.",
            "USER_NOT_FOUND": "Account not found. Please register again.",
            "NETWORK_TIMEOUT": "Request timed out. Please try again.",
            "NO_INTERNET": "No internet connection.",
            "NETWORK_ERROR": "Network error. Please try again.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please wait before requesting another email.",
        }
        return False, messages.get(raw, "Could not send verification email. Please try again.")

    return True, None


def check_email_verified(id_token: str) -> tuple[bool | None, str | None]:
    """
    Look up the Firebase account for id_token and return whether the
    email address has been verified.

    Returns:
        (verified: bool | None, error_message: str | None)
        verified=None means the check could not be completed (network issue).
        verified=True means the user clicked the link and is verified.
        verified=False means the email is still unverified.
    """
    api_key = _get_api_key()
    if not api_key:
        return None, "Firebase is not configured."

    url = f"{FIREBASE_AUTH_BASE}:lookup?key={api_key}"
    result = _safe_post(url, {"idToken": id_token})

    if "error" in result:
        raw = result["error"].get("message", "UNKNOWN_ERROR")
        if raw in ("NETWORK_TIMEOUT", "NO_INTERNET", "NETWORK_ERROR"):
            return None, "Could not reach Firebase. Please check your connection."
        return None, "Could not verify email status. Please try again."

    users = result.get("users", [])
    if not users:
        return None, "Account not found."

    return bool(users[0].get("emailVerified", False)), None


# ---------------------------------------------------------------------------
# SESSION STATE HELPERS
# ---------------------------------------------------------------------------
# These keep the "pending verification" state alive across Streamlit reruns
# within the same browser tab session. Firestore persistence (via database.py)
# covers the case where the user closes the tab and comes back later to log in.

def set_pending_verification(email: str, id_token: str) -> None:
    st.session_state[_SESSION_PENDING_KEY] = email
    st.session_state[_SESSION_PENDING_TOKEN] = id_token


def get_pending_verification() -> tuple[str | None, str | None]:
    email = st.session_state.get(_SESSION_PENDING_KEY)
    token = st.session_state.get(_SESSION_PENDING_TOKEN)
    return email, token


def clear_pending_verification() -> None:
    st.session_state.pop(_SESSION_PENDING_KEY, None)
    st.session_state.pop(_SESSION_PENDING_TOKEN, None)


def is_verification_pending() -> bool:
    email, token = get_pending_verification()
    return bool(email and token)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def render_verification_pending_ui(email: str, id_token: str) -> None:
    """
    Render the "check your inbox" screen shown after registration and when
    a user tries to log in with an unverified account.

    Offers a resend button and a check/refresh button.
    The user never leaves the Streamlit app -- they verify in their email
    client and then come back here and click the check button.
    """
    st.info(
        f"A verification email has been sent to **{email}**. "
        "Please check your inbox (and spam folder) and click the link to verify your address. "
        "Once verified, return here and click the button below."
    )

    col_check, col_resend = st.columns(2)

    with col_check:
        if st.button("I have verified my email", key="_ev_check_btn", use_container_width=True, type="primary"):
            verified, err = check_email_verified(id_token)

            if verified is None:
                st.error(err or "Could not check verification status. Please try again.")
                return

            if verified:
                # Clear the pending state so the normal login flow takes over
                clear_pending_verification()

                try:
                    from app.core.database import clear_pending_verification_db
                    clear_pending_verification_db(email)
                except Exception:
                    pass

                st.success("Email verified. You can now sign in.")
                st.rerun()
            else:
                st.warning(
                    "Your email has not been verified yet. "
                    "Please click the link in the email we sent you."
                )

    with col_resend:
        if st.button("Resend verification email", key="_ev_resend_btn", use_container_width=True):
            ok, err = send_verification_email(id_token)
            if ok:
                st.success("Verification email resent. Please check your inbox.")
            else:
                st.error(err or "Could not resend. Please try again.")

    st.caption(
        "The verification link expires after 24 hours. "
        "If you did not receive the email, check your spam folder or use the resend button."
    )