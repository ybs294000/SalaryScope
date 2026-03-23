import streamlit as st
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta
import requests as http_requests

# ---------------------------------------------------
# FIREBASE CONFIG
# ---------------------------------------------------

FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


def _get_firebase_api_key():
    api_key = st.secrets.get("FIREBASE_API_KEY")
    if not api_key:
        st.error("Missing FIREBASE_API_KEY in Streamlit secrets.")
        st.stop()
    return api_key


# ---------------------------------------------------
# FIREBASE REST API HELPERS
# ---------------------------------------------------

def _firebase_sign_in_email(email: str, password: str) -> dict:
    api_key = _get_firebase_api_key()
    url = f"{FIREBASE_AUTH_BASE}:signInWithPassword?key={api_key}"
    resp = http_requests.post(url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True
    })
    return resp.json()


def _firebase_sign_up_email(email: str, password: str) -> dict:
    api_key = _get_firebase_api_key()
    url = f"{FIREBASE_AUTH_BASE}:signUp?key={api_key}"
    resp = http_requests.post(url, json={
        "email": email,
        "password": password,
        "returnSecureToken": True
    })
    return resp.json()


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
    }
    return messages.get(raw, raw.replace("_", " ").capitalize())


# ---------------------------------------------------
# SESSION STATE — per-browser-session storage
# The token is kept ONLY in st.session_state which is
# isolated per browser tab/session on Streamlit Cloud.
# There is no shared server-side cookie that bleeds
# across users.
# ---------------------------------------------------

SESSION_DURATION_HOURS = 24


def _init_session_state():
    """Safely initialise session keys without overwriting existing values."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "_firebase_id_token" not in st.session_state:
        st.session_state._firebase_id_token = None
    if "_session_expiry" not in st.session_state:
        st.session_state._session_expiry = None


def _set_logged_in(email: str, id_token: str):
    """Mark this browser session as authenticated."""
    _init_session_state()
    expiry = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    st.session_state.logged_in = True
    st.session_state.username = email
    st.session_state._firebase_id_token = id_token
    st.session_state._session_expiry = expiry


def _clear_session():
    """Wipe all auth state for this browser session."""
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state._firebase_id_token = None
    st.session_state._session_expiry = None


# ---------------------------------------------------
# PUBLIC API — same signatures as before
# ---------------------------------------------------

def get_logged_in_user():
    """
    Return the logged-in username for THIS browser session,
    or None if not authenticated / session expired.

    Uses st.session_state only — completely isolated per
    browser tab, no shared state between users.
    """
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
    """
    Kept for backward compatibility.
    With Firebase auth the session lives in st.session_state;
    this is a no-op stub so existing call sites don't break.
    """
    pass


def destroy_session():
    """Clear the auth state for this browser session."""
    _clear_session()


# ---------------------------------------------------
# LEGACY PASSWORD HELPERS (kept, not used for auth)
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
# ---------------------------------------------------
# GOOGLE OAuth LOGIN
# ---------------------------------------------------

def google_login():
    """Google OAuth via streamlit_oauth — sets session state on success."""
    try:
        from streamlit_oauth import OAuth2Component
    except ImportError:
        st.warning("streamlit-oauth not installed. Google login unavailable.")
        return

    GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        st.warning("Google OAuth credentials not configured in secrets.")
        return

    oauth2 = OAuth2Component(
        GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET,
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "https://oauth2.googleapis.com/token",
        "https://oauth2.googleapis.com/revoke",
    )

    result = oauth2.authorize_button(
        name="Sign in with Google",
        redirect_uri=get_current_url(),
        scope="openid email profile",
        key="google_oauth_btn",
        icon="https://www.google.com/favicon.ico",
        use_container_width=True,
    )

    if result and "token" in result:
        access_token = result["token"].get("access_token")
        if not access_token:
            st.error("Google login failed: no access token returned.")
            return

        userinfo_resp = http_requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo = userinfo_resp.json()
        email = userinfo.get("email")
        name = userinfo.get("name", email)

        if not email:
            st.error("Could not retrieve email from Google.")
            return

        # Use a sentinel token for Google OAuth sessions
        _set_logged_in(email, id_token="google_oauth")

        # Ensure Firestore user record exists
        from database import ensure_firestore_user
        ensure_firestore_user(email, email)

        st.success(f"Welcome, {name}!")
        st.rerun()


# ---------------------------------------------------
# LOGIN UI  (signature unchanged)
# ---------------------------------------------------

def login_ui():
    st.subheader("Sign In")

    tab_email, tab_google = st.tabs(["Email & Password", "Google"])

    with tab_email:
        email_input = st.text_input("Email", key="login_email").strip()
        password_input = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_btn", use_container_width=True):
            if not email_input or not password_input:
                st.warning("Please enter your email and password.")
                return False

            result = _firebase_sign_in_email(email_input, password_input)

            if "error" in result:
                st.error(_firebase_error_message(result))
                return False

            email = result.get("email", email_input)
            id_token = result.get("idToken", "")

            # Store in this browser session only
            _set_logged_in(email, id_token)

            # Mirror user in Firestore if first login
            from database import ensure_firestore_user
            ensure_firestore_user(email, email)

            st.success("Login successful!")
            st.rerun()

    with tab_google:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        google_login()

    return False


# ---------------------------------------------------
# REGISTER UI  (signature unchanged)
# ---------------------------------------------------

def register_ui():
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

        from database import ensure_firestore_user
        ensure_firestore_user(firebase_email, firebase_email, display_name=username)

        st.success("Account created! You can now sign in.")


# ---------------------------------------------------
# LOGOUT  (signature unchanged)
# ---------------------------------------------------

def logout():
    destroy_session()
    st.session_state.logged_in = False
    st.session_state.username = None
    st.rerun()