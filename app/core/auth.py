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


def _safe_request(method, url, **kwargs):
    try:
        kwargs.setdefault("timeout", 5)  # prevents hanging
        response = http_requests.request(method, url, **kwargs)
        return response.json()

    except http_requests.exceptions.Timeout:
        return {"error": {"message": "NETWORK_TIMEOUT"}}

    except http_requests.exceptions.ConnectionError:
        return {"error": {"message": "NO_INTERNET"}}

    except Exception:
        return {"error": {"message": "NETWORK_ERROR"}}

def _has_internet():
    try:
        http_requests.get("https://www.google.com", timeout=2)
        return True
    except:
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

FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


def _get_firebase_api_key():
    try:
        return st.secrets.get("FIREBASE_API_KEY")
    except Exception:
        return None


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
        "returnSecureToken": True
    })


def _firebase_sign_up_email(email: str, password: str) -> dict:
    api_key = _get_firebase_api_key()

    if not api_key:
        return {"error": {"message": "AUTH_DISABLED"}}

    url = f"{FIREBASE_AUTH_BASE}:signUp?key={api_key}"
    return _safe_request("POST", url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True
    })


def _firebase_error_message(response: dict) -> str:
    raw = response.get("error", {}).get("message", "UNKNOWN_ERROR")
    messages = {
        "EMAIL_NOT_FOUND": "No account found with this email.",
        "INVALID_PASSWORD": "Incorrect password.",
        "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
        "USER_DISABLED": "This account has been disabled.",
        "EMAIL_EXISTS": "An account with this email already exists.",
        "WEAK_PASSWORD : Password should be at least 6 characters": "Password must be at least 6 characters.",
        "INVALID_EMAIL": "Invalid email address.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed attempts. Please try again later.",
        "AUTH_DISABLED": "Authentication is disabled (Firebase not configured).",
        "NO_INTERNET": "No internet connection. Please check your network.",
        "NETWORK_TIMEOUT": "Request timed out. Try again.",
        "NETWORK_ERROR": "Network error. Please try again.",
    }
    return messages.get(raw, raw.replace("_", " ").capitalize())


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

SESSION_DURATION_HOURS = 24


def _init_session_state():
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

def _set_logged_in(email: str, id_token: str):
    _init_session_state()
    expiry = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    st.session_state.logged_in = True
    st.session_state.username = email
    st.session_state._firebase_id_token = id_token
    st.session_state._session_expiry = expiry

    st.session_state.is_admin = (
        email.strip().lower() == st.secrets.get("ADMIN_EMAIL", "").strip().lower()
    )

def _clear_session():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state._firebase_id_token = None
    st.session_state._session_expiry = None


# ---------------------------------------------------
# PUBLIC API
# ---------------------------------------------------

def get_logged_in_user():
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


def create_login_session(username: str):
    pass


def destroy_session():
    _clear_session()


# ---------------------------------------------------
# LEGACY PASSWORD HELPERS
# ---------------------------------------------------

def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password: str, hashed):
    return bcrypt.checkpw(password.encode(), hashed)


def generate_token():
    return secrets.token_urlsafe(32)


def hash_token(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------
# APP URL
# ---------------------------------------------------

def get_current_url():
    return "https://salaryscope-fhl4g2mmypfzrhwhvjcj6o.streamlit.app"


def get_oauth_redirect_uri():
    return get_current_url()


# ---------------------------------------------------
# LOGIN UI
# ---------------------------------------------------

def login_ui():
    st.subheader("Sign In")

    # If the user registered in this session but has not yet verified,
    # show the verification waiting screen instead of the login form.
    # -- ROLLBACK: remove this block --
    if is_verification_pending():
        email, id_token = get_pending_verification()
        render_verification_pending_ui(email, id_token)
        return
    # -- ROLLBACK end --

    tab_email = st.tabs(["Email & Password"])[0]

    with tab_email:
        email_input = st.text_input("Email", key="login_email").strip()
        password_input = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_btn", use_container_width=True):

            if st.session_state.auth_loading:
                return False

            st.session_state.auth_loading = True

            if not _has_internet():
                st.error("No internet connection.")
                return False
            try:
                if not email_input or not password_input:
                    st.warning("Please enter your email and password.")
                    return False

                result = _firebase_sign_in_email(email_input, password_input)

                if "error" in result:
                    st.error(_firebase_error_message(result))
                    return False

                email = result.get("email", email_input)
                id_token = result.get("idToken", "")

                # Check email verification before creating a session.
                # -- ROLLBACK: remove from here to the next ROLLBACK marker --
                from app.core.email_verification import check_email_verified

                verified, err = check_email_verified(id_token)

                if verified is None:
                    # Network error during check -- fail open with a warning
                    # so a Firebase outage does not permanently lock out users.
                    st.warning(
                        "Could not confirm email verification status due to a network issue. "
                        "Proceeding with login. If you have not verified your email, "
                        "some features may be restricted."
                    )

                elif not verified:
                    # Account exists but email is not verified.
                    # Check if there is a stored id_token from a prior session.
                    stored_token = id_token  # current token is valid for resend

                    try:
                        from app.core.database import get_pending_verification_db, save_pending_verification
                        record = get_pending_verification_db(email)
                        if record and record.get("id_token"):
                            stored_token = record["id_token"]
                        else:
                            save_pending_verification(email, id_token)
                    except Exception:
                        pass

                    set_pending_verification(email, stored_token)
                    st.rerun()
                    return False
                # -- ROLLBACK end --

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

def register_ui():
    # -- ROLLBACK NOTE: the verification pending UI block and the
    #    send_verification_email call below are the only additions here.
    #    Everything else is unchanged from the original.

    # If this session already has a pending verification in progress,
    # show the waiting screen instead of the registration form.
    # This handles the case where the user submits the form and Streamlit reruns.
    if is_verification_pending():
        email, id_token = get_pending_verification()
        st.subheader("Create Account")
        render_verification_pending_ui(email, id_token)
        return

    st.subheader("Create Account")

    username = st.text_input("Display Name", key="reg_username").strip()
    email = st.text_input("Email", key="reg_email").strip()
    password = st.text_input("Password", type="password", key="reg_password")

    if st.button("Register", key="register_btn", use_container_width=True):
        if not username or not email or not password:
            st.warning("All fields are required.")
            return

        if len(password) < 6:
            st.warning("Password must be at least 6 characters.")
            return

        result = _firebase_sign_up_email(email, password)

        if "error" in result:
            st.error(_firebase_error_message(result))
            return

        firebase_email = result.get("email", email)
        id_token = result.get("idToken", "")

        # Create the Firestore user document (display name stored here).
        try:
            from app.core.database import ensure_firestore_user
            ensure_firestore_user(firebase_email, firebase_email, display_name=username)
        except Exception:
            pass

        # Send verification email via Firebase.
        # -- ROLLBACK: remove from here to the next ROLLBACK marker --
        ok, err = send_verification_email(id_token)

        if ok:
            set_pending_verification(firebase_email, id_token)

            try:
                from app.core.database import save_pending_verification
                save_pending_verification(firebase_email, id_token)
            except Exception:
                pass

            st.rerun()
        else:
            # Sending the verification email failed, but the Firebase account
            # was created successfully. Tell the user to try logging in so
            # they can request a resend from the login flow.
            st.warning(
                f"Account created, but we could not send the verification email: {err} "
                "Please try signing in to request a new verification email."
            )
        # -- ROLLBACK end --


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------

def logout():
    destroy_session()
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()

# ----------------------------------------------------
# ADMIN
# ----------------------------------------------------
def is_admin():
    admin_email = st.secrets.get("ADMIN_EMAIL", "").strip().lower()
    user_email = st.session_state.get("username", "").strip().lower()

    return user_email == admin_email