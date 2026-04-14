import streamlit as st
import hashlib
import secrets
import bcrypt
import urllib.parse
from datetime import datetime, timedelta
import requests as http_requests

# Email verification -- all logic is isolated in email_verification.py.
# Rollback: remove this import and the three call sites marked below.
from app.core.email_verification import (
    send_verification_email,
    set_pending_verification,
    get_pending_verification,
    clear_pending_verification,
    is_verification_pending,
    render_verification_pending_ui,
)

# Password policy -- NIST SP 800-63B / OWASP 2024 compliant validation.
# Rollback: remove this import and the call sites marked
# -- ROLLBACK: password_policy -- in register_ui.
from app.core.password_policy import (
    validate_password_strength,
    password_strength_hint,
)

# Rate limiter -- per-action, per-identifier brute-force protection.
# Rollback: remove this import and all call sites marked
# -- ROLLBACK: rate_limiter -- in login_ui, register_ui, and
# forgot_password_ui.
from app.core.rate_limiter import (
    check_rate_limit,
    record_attempt,
    clear_attempts,
)


def _safe_request(method: str, url: str, **kwargs) -> dict:
    """
    Execute an HTTP request and return the parsed JSON response dict.

    Always returns a dict. On any network, timeout, or JSON-parse error,
    returns a dict with an "error" key so callers have a uniform code path.
    """
    try:
        kwargs.setdefault("timeout", 5)
        response = http_requests.request(method, url, **kwargs)
        try:
            return response.json()
        except ValueError:
            # Non-JSON response body (e.g. 502 from Firebase CDN).
            return {
                "error": {
                    "message": f"INVALID_RESPONSE_{response.status_code}"
                }
            }
    except http_requests.exceptions.Timeout:
        return {"error": {"message": "NETWORK_TIMEOUT"}}
    except http_requests.exceptions.ConnectionError:
        return {"error": {"message": "NO_INTERNET"}}
    except Exception:
        return {"error": {"message": "NETWORK_ERROR"}}


def _has_internet() -> bool:
    """
    Return True if a quick connectivity probe succeeds.

    Uses except Exception (not bare except) so KeyboardInterrupt and
    SystemExit are not swallowed.
    """
    try:
        http_requests.get("https://www.google.com", timeout=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------
# GOOGLE OAUTH CALLBACK HANDLER
# (DISABLED)
# ---------------------------------------------------

# def _handle_google_callback():
#     params = st.query_params
#     code = params.get("code")
#     error = params.get("error")
#
#     if error:
#         st.query_params.clear()
#         return
#
#     if not code:
#         return
#
#     CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
#     CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")
#     redirect_uri = "https://salaryscope-fhl4g2mmypfzrhwhvjcj6o.streamlit.app"
#
#     if not CLIENT_ID or not CLIENT_SECRET:
#         st.query_params.clear()
#         return
#
#     token_resp = http_requests.post(
#         "https://oauth2.googleapis.com/token",
#         data={
#             "code": code,
#             "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET,
#             "redirect_uri": redirect_uri,
#             "grant_type": "authorization_code",
#         },
#     )
#     token_data = token_resp.json()
#     access_token = token_data.get("access_token")
#
#     st.query_params.clear()
#
#     if not access_token:
#         st.error("Google login failed: could not obtain access token.")
#         return
#
#     userinfo = http_requests.get(
#         "https://www.googleapis.com/oauth2/v3/userinfo",
#         headers={"Authorization": f"Bearer {access_token}"},
#     ).json()
#
#     email = userinfo.get("email")
#     name = userinfo.get("name", email)
#
#     if not email:
#         st.error("Could not retrieve email from Google.")
#         return
#
#     expiry = datetime.utcnow() + timedelta(hours=24)
#     st.session_state.logged_in = True
#     st.session_state.username = email
#     st.session_state._firebase_id_token = access_token
#     st.session_state._session_expiry = expiry
#
#     try:
#         from app.core.database import ensure_firestore_user
#         ensure_firestore_user(email, email)
#     except Exception:
#         pass
#
#     st.success(f"Welcome, {name}!")
#     st.rerun()

# _handle_google_callback()

# ---------------------------------------------------
# FIREBASE CONFIG
# ---------------------------------------------------

FIREBASE_AUTH_BASE: str = "https://identitytoolkit.googleapis.com/v1/accounts"


def _get_firebase_api_key() -> str:
    """
    Return the Firebase API key from st.secrets.

    Returns an empty string if the secret is missing or unavailable.
    Callers treat an empty string as "Firebase not configured".
    """
    try:
        key = st.secrets.get("FIREBASE_API_KEY")
        return key if isinstance(key, str) and key else ""
    except Exception:
        return ""


# ---------------------------------------------------
# FIREBASE REST API HELPERS
# ---------------------------------------------------

def _firebase_sign_in_email(email: str, password: str) -> dict:
    api_key = _get_firebase_api_key()
    if not api_key:
        return {"error": {"message": "AUTH_DISABLED"}}

    url = f"{FIREBASE_AUTH_BASE}:signInWithPassword?key={api_key}"
    return _safe_request("POST", url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })


def _firebase_sign_up_email(email: str, password: str) -> dict:
    api_key = _get_firebase_api_key()
    if not api_key:
        return {"error": {"message": "AUTH_DISABLED"}}

    url = f"{FIREBASE_AUTH_BASE}:signUp?key={api_key}"
    return _safe_request("POST", url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })


def _firebase_error_message(response: dict) -> str:
    """
    Translate a Firebase REST API error response into a user-facing string.

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

    messages: dict = {
        "EMAIL_NOT_FOUND":           "No account found with this email.",
        "INVALID_PASSWORD":          "Incorrect password.",
        "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
        "USER_DISABLED":             "This account has been disabled.",
        "EMAIL_EXISTS":              "An account with this email already exists.",
        "WEAK_PASSWORD : Password should be at least 6 characters": (
            "Password must be at least 6 characters."
        ),
        "INVALID_EMAIL":             "Invalid email address.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": (
            "Too many failed attempts. Please try again later."
        ),
        "TOKEN_EXPIRED":   "Your session has expired. Please log out and log back in.",
        "INVALID_ID_TOKEN": "Your session is invalid. Please log out and log back in.",
        "AUTH_DISABLED":   "Authentication is disabled (Firebase not configured).",
        "NO_INTERNET":     "No internet connection. Please check your network.",
        "NETWORK_TIMEOUT": "Request timed out. Try again.",
        "NETWORK_ERROR":   "Network error. Please try again.",
    }

    if raw.startswith("INVALID_RESPONSE_"):
        return "Firebase returned an unexpected response. Please try again."

    return messages.get(raw, raw.replace("_", " ").capitalize())


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

SESSION_DURATION_HOURS: int = 24


def _init_session_state() -> None:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "_firebase_id_token" not in st.session_state:
        st.session_state._firebase_id_token = None
    if "_session_expiry" not in st.session_state:
        st.session_state._session_expiry = None
    if "auth_loading" not in st.session_state:
        st.session_state.auth_loading = False


def _set_logged_in(email: str, id_token: str) -> None:
    _init_session_state()
    expiry = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    st.session_state.logged_in = True
    st.session_state.username = email
    st.session_state._firebase_id_token = id_token
    st.session_state._session_expiry = expiry

    try:
        admin_email = st.secrets.get("ADMIN_EMAIL", "")
        st.session_state.is_admin = (
            isinstance(admin_email, str)
            and email.strip().lower() == admin_email.strip().lower()
        )
    except Exception:
        st.session_state.is_admin = False


def _clear_session() -> None:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state._firebase_id_token = None
    st.session_state._session_expiry = None


# ---------------------------------------------------
# PUBLIC API
# ---------------------------------------------------

def get_logged_in_user() -> str:
    _init_session_state()

    if not st.session_state.logged_in:
        return None

    expiry = st.session_state._session_expiry
    if expiry is None:
        return None

    if datetime.utcnow() > expiry:
        _clear_session()
        return None

    return st.session_state.username


def create_login_session(username: str) -> None:
    pass


def destroy_session() -> None:
    _clear_session()


# ---------------------------------------------------
# LEGACY PASSWORD HELPERS
# ---------------------------------------------------

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, hashed) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------
# APP URL
# ---------------------------------------------------

def get_current_url() -> str:
    return "https://salaryscope-fhl4g2mmypfzrhwhvjcj6o.streamlit.app"


def get_oauth_redirect_uri() -> str:
    return get_current_url()


# ---------------------------------------------------
# LOGIN UI
# ---------------------------------------------------

def login_ui() -> bool:
    st.subheader("Sign In")

    # If the user registered in this session but has not yet verified,
    # show the verification waiting screen instead of the login form.
    # -- ROLLBACK: remove this block --
    if is_verification_pending():
        email, id_token = get_pending_verification()
        render_verification_pending_ui(email, id_token)
        return False
    # -- ROLLBACK end --

    tab_email = st.tabs(["Email & Password"])[0]

    with tab_email:
        email_input = st.text_input("Email", key="login_email").strip()
        password_input = st.text_input(
            "Password", type="password", key="login_password"
        )

        if st.button("Login", key="login_btn", use_container_width=True):

            if st.session_state.get("auth_loading"):
                return False

            st.session_state.auth_loading = True

            try:
                if not email_input or not password_input:
                    st.warning("Please enter your email and password.")
                    return False

                if not _has_internet():
                    st.error("No internet connection.")
                    return False

                # -- ROLLBACK: rate_limiter (login) --
                try:
                    allowed, rl_msg = check_rate_limit("login", email_input)
                    if not allowed:
                        st.error(rl_msg)
                        return False
                except Exception:
                    pass  # fail open
                # -- ROLLBACK: rate_limiter end --

                result = _firebase_sign_in_email(email_input, password_input)

                if "error" in result:
                    st.error(_firebase_error_message(result))
                    # -- ROLLBACK: rate_limiter (login) --
                    try:
                        record_attempt("login", email_input)
                    except Exception:
                        pass
                    # -- ROLLBACK: rate_limiter end --
                    return False

                email = result.get("email", email_input)
                id_token = result.get("idToken", "")

                if not isinstance(id_token, str) or not id_token:
                    st.error(
                        "Login succeeded but no session token was returned. "
                        "Please try again."
                    )
                    return False

                # Check email verification before creating a session.
                # -- ROLLBACK: remove from here to the next ROLLBACK marker --
                from app.core.email_verification import check_email_verified

                try:
                    verified, err = check_email_verified(id_token)
                except Exception:
                    verified = None
                    err = "Could not check email verification status."

                if verified is None:
                    # Network error during check -- fail open so a Firebase
                    # outage does not permanently lock out verified users.
                    st.warning(
                        "Could not confirm email verification status due to "
                        "a network issue. Proceeding with login. If you have "
                        "not verified your email, some features may be "
                        "restricted."
                    )

                elif not verified:
                    stored_token = id_token

                    try:
                        from app.core.database import (
                            get_pending_verification_db,
                            save_pending_verification,
                        )
                        record = get_pending_verification_db(email)
                        if (
                            isinstance(record, dict)
                            and isinstance(record.get("id_token"), str)
                            and record["id_token"]
                        ):
                            stored_token = record["id_token"]
                        else:
                            save_pending_verification(email, id_token)
                    except Exception:
                        pass

                    set_pending_verification(email, stored_token)
                    st.rerun()
                    return False
                # -- ROLLBACK end --

                # Clear rate-limit counter on successful login.
                # -- ROLLBACK: rate_limiter (login) --
                try:
                    clear_attempts("login", email_input)
                except Exception:
                    pass
                # -- ROLLBACK: rate_limiter end --

                _set_logged_in(email, id_token)

                # Clear any stale verification state for this email.
                # -- ROLLBACK: remove this block --
                try:
                    clear_pending_verification()
                    from app.core.database import clear_pending_verification_db
                    clear_pending_verification_db(email)
                except Exception:
                    pass
                # -- ROLLBACK end --

                try:
                    from app.core.database import ensure_firestore_user
                    ensure_firestore_user(email, email)
                except Exception:
                    pass

                st.success("Login successful!")
                st.rerun()

            finally:
                st.session_state.auth_loading = False

    return False


# ---------------------------------------------------
# REGISTER UI
# ---------------------------------------------------

def register_ui() -> None:
    # If this session already has a pending verification in progress,
    # show the waiting screen instead of the registration form.
    if is_verification_pending():
        email, id_token = get_pending_verification()
        st.subheader("Create Account")
        render_verification_pending_ui(email, id_token)
        return

    st.subheader("Create Account")

    username = st.text_input("Display Name", key="reg_username").strip()
    email = st.text_input("Email", key="reg_email").strip()
    password = st.text_input("Password", type="password", key="reg_password")
    password_confirm = st.text_input(
        "Confirm Password", type="password", key="reg_password_confirm"
    )

    # -- ROLLBACK: password_policy (hint) --
    try:
        hint = password_strength_hint()
    except Exception:
        hint = "Minimum 12 characters required."
    st.caption("Password requirements: " + hint)
    # -- ROLLBACK: password_policy end --

    if not st.button("Register", key="register_btn", use_container_width=True):
        return

    # --- Input validation ---
    if not username or not email or not password or not password_confirm:
        st.warning("All fields are required.")
        return

    # -- ROLLBACK: password_policy (confirm match) --
    if password != password_confirm:
        st.error("Passwords do not match.")
        return
    # -- ROLLBACK: password_policy end --

    # -- ROLLBACK: password_policy (strength) --
    try:
        policy_errors = validate_password_strength(password)
    except Exception as exc:
        st.error(f"Password validation error: {exc}")
        return

    if policy_errors:
        for err in policy_errors:
            st.error(err)
        return
    # -- ROLLBACK: password_policy end --

    # -- ROLLBACK: rate_limiter (register) --
    try:
        allowed, rl_msg = check_rate_limit("register", email)
        if not allowed:
            st.error(rl_msg)
            return
    except Exception:
        pass  # fail open
    # -- ROLLBACK: rate_limiter end --

    result = _firebase_sign_up_email(email, password)

    if "error" in result:
        st.error(_firebase_error_message(result))
        # Record the failed attempt ONLY on failure, not on success.
        # -- ROLLBACK: rate_limiter (register) --
        try:
            record_attempt("register", email)
        except Exception:
            pass
        # -- ROLLBACK: rate_limiter end --
        return

    firebase_email = result.get("email", email)
    id_token = result.get("idToken", "")

    if not isinstance(id_token, str) or not id_token:
        st.warning(
            "Account created, but no session token was returned. "
            "Please try signing in."
        )
        return

    # Create the Firestore user document (display name stored here).
    try:
        from app.core.database import ensure_firestore_user
        ensure_firestore_user(firebase_email, firebase_email, display_name=username)
    except Exception:
        pass

    # Send verification email via Firebase.
    # -- ROLLBACK: remove from here to the next ROLLBACK marker --
    try:
        ok, err = send_verification_email(id_token)
    except Exception as exc:
        ok = False
        err = str(exc)

    if ok:
        try:
            set_pending_verification(firebase_email, id_token)
        except Exception:
            pass

        try:
            from app.core.database import save_pending_verification
            save_pending_verification(firebase_email, id_token)
        except Exception:
            pass

        # Inform the user that Firebase verification emails frequently land
        # in spam or junk folders.
        st.info(
            "A verification email has been sent to "
            + firebase_email
            + ". "
            "If you do not see it in your inbox within a few minutes, "
            "please check your spam or junk folder -- automated emails "
            "from Firebase Authentication are sometimes filtered there."
        )

        st.rerun()
    else:
        # The Firebase account was created but the verification email
        # could not be sent. Instruct the user to sign in to request a
        # resend from the login flow.
        st.warning(
            "Account created, but the verification email could not be sent"
            + (f": {err}" if err else ".")
            + " Please try signing in to request a new verification email."
        )
    # -- ROLLBACK end --


# ---------------------------------------------------
# FORGOT PASSWORD UI
# ---------------------------------------------------
# Rollback:
#   Remove this entire function and its call site in your app entrypoint
#   or auth tab. No other files are affected.

def forgot_password_ui() -> None:
    """
    Render the forgot-password / password-reset UI.

    Sends a Firebase PASSWORD_RESET OOB code to the given email address.
    Firebase handles the reset link; no tokens are managed here.

    Account enumeration protection: a generic success message is shown
    regardless of whether the email address exists in the system.

    Spam-folder notice: Firebase password-reset emails are frequently
    filtered to spam, same as verification emails.
    """
    st.subheader("Reset Password")

    email_input = st.text_input(
        "Enter your account email address",
        key="forgot_pw_email",
    ).strip()

    if not st.button(
        "Send Password Reset Email",
        key="forgot_pw_btn",
        use_container_width=True,
    ):
        return

    if not email_input:
        st.warning("Please enter your email address.")
        return

    # -- ROLLBACK: rate_limiter (forgot_password) --
    try:
        allowed, rl_msg = check_rate_limit("forgot_password", email_input)
        if not allowed:
            st.error(rl_msg)
            return
    except Exception:
        pass  # fail open
    # -- ROLLBACK: rate_limiter end --

    api_key = _get_firebase_api_key()
    if not api_key:
        st.error("Authentication is not configured.")
        return

    url = f"{FIREBASE_AUTH_BASE}:sendOobCode?key={api_key}"
    result = _safe_request("POST", url, json={
        "requestType": "PASSWORD_RESET",
        "email": email_input,
    })

    if "error" in result:
        raw = ""
        try:
            raw = result["error"].get("message", "")
        except Exception:
            pass

        # Do not reveal whether the email exists -- return the same
        # generic success message for EMAIL_NOT_FOUND as for a real send.
        if raw == "EMAIL_NOT_FOUND":
            st.success(
                "If an account with that address exists, a password reset "
                "email has been sent. Please check your inbox and spam folder."
            )
            return

        st.error(_firebase_error_message(result))

        # -- ROLLBACK: rate_limiter (forgot_password) --
        try:
            record_attempt("forgot_password", email_input)
        except Exception:
            pass
        # -- ROLLBACK: rate_limiter end --
        return

    # -- ROLLBACK: rate_limiter (forgot_password) --
    try:
        clear_attempts("forgot_password", email_input)
    except Exception:
        pass
    # -- ROLLBACK: rate_limiter end --

    st.success(
        "A password reset email has been sent to "
        + email_input
        + ". "
        "Please check your inbox. If you do not see the email within a "
        "few minutes, check your spam or junk folder -- emails from "
        "Firebase Authentication are sometimes filtered there. "
        "The reset link expires after 1 hour."
    )


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------

def logout() -> None:
    destroy_session()
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()


# ---------------------------------------------------
# ADMIN
# ---------------------------------------------------

def is_admin() -> bool:
    try:
        admin_email = st.secrets.get("ADMIN_EMAIL", "")
        user_email = st.session_state.get("username", "")
        if not isinstance(admin_email, str) or not isinstance(user_email, str):
            return False
        return (
            bool(admin_email)
            and user_email.strip().lower() == admin_email.strip().lower()
        )
    except Exception:
        return False 

        