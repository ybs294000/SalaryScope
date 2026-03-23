import streamlit as st
import hashlib
import secrets
import bcrypt
import urllib.parse
from datetime import datetime, timedelta
import requests as http_requests

# ---------------------------------------------------
# GOOGLE OAUTH CALLBACK HANDLER
# Runs at module level so ?code= is always caught on
# every page load, regardless of sidebar tab state.
# ---------------------------------------------------

def _handle_google_callback():
    params = st.query_params
    code = params.get("code")
    error = params.get("error")

    if error:
        st.query_params.clear()
        return

    if not code:
        return

    CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
    CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = "https://salaryscope-fhl4g2mmypfzrhwhvjcj6o.streamlit.app"

    if not CLIENT_ID or not CLIENT_SECRET:
        st.query_params.clear()
        return

    token_resp = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    token_data = token_resp.json()
    access_token = token_data.get("access_token")

    st.query_params.clear()

    if not access_token:
        st.error("Google login failed: could not obtain access token.")
        return

    userinfo = http_requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    email = userinfo.get("email")
    name = userinfo.get("name", email)

    if not email:
        st.error("Could not retrieve email from Google.")
        return

    expiry = datetime.utcnow() + timedelta(hours=24)
    st.session_state.logged_in = True
    st.session_state.username = email
    st.session_state._firebase_id_token = access_token
    st.session_state._session_expiry = expiry

    try:
        from database import ensure_firestore_user
        ensure_firestore_user(email, email)
    except Exception:
        pass

    st.success(f"Welcome, {name}!")
    st.rerun()


_handle_google_callback()

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


def get_oauth_redirect_uri():
    """
    streamlit-oauth sends the plain app root as redirect_uri.
    This must be registered exactly in Google Cloud Console.
    """
    return get_current_url()


# ---------------------------------------------------
# GOOGLE OAuth LOGIN
# Direct redirect flow — works reliably on Streamlit Cloud.
# streamlit-oauth iframes cause redirect_uri_mismatch errors.
# ---------------------------------------------------

def google_login():
    """
    Google OAuth via direct browser redirect flow.
    Step 1: Button sends user to Google consent page.
    Step 2: Google redirects back with ?code=... in URL.
    Step 3: Exchange code for token, fetch userinfo, log in.
    """
    import urllib.parse

    CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")

    if not CLIENT_ID or not CLIENT_SECRET:
        st.warning("Google OAuth credentials not configured in secrets.")
        return

    redirect_uri = get_current_url()

    # ── Render the Sign in with Google button ──
    # (Callback is handled at module level in _handle_google_callback)
    auth_params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    })
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{auth_params}"

    st.markdown(
        f"""
        <a href="{google_auth_url}" target="_self" style="
            display: inline-block;
            width: 100%;
            padding: 10px 16px;
            background: #ffffff;
            color: #3c4043;
            border: 1px solid #dadce0;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 500;
            text-align: center;
            text-decoration: none;
            box-sizing: border-box;
        ">
            <img src="https://www.google.com/favicon.ico" width="18"
                 style="vertical-align:middle; margin-right:8px;">
            Sign in with Google
        </a>
        """,
        unsafe_allow_html=True,
    )


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