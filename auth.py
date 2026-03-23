import streamlit as st
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta

from database import create_user, get_user, create_session, get_session, delete_session


# ---------------------------------------------------
# PASSWORD FUNCTIONS
# ---------------------------------------------------

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)


# ---------------------------------------------------
# SESSION TOKEN FUNCTIONS
# ---------------------------------------------------

SESSION_DURATION_HOURS = 24


def generate_token():
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------
# CREATE SESSION
# ---------------------------------------------------

def create_login_session(username):
    token = generate_token()
    token_hash = hash_token(token)

    expiry = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)

    create_session(username, token_hash, expiry)

    # Store in session_state (isolated per browser/session)
    st.session_state.session_token = token
    st.session_state.username = username
    st.session_state.logged_in = True

    return token


# ---------------------------------------------------
# GET CURRENT USER
# ---------------------------------------------------

def get_logged_in_user():
    token = st.session_state.get("session_token")

    if not token:
        st.session_state.logged_in = False
        st.session_state.username = None
        return None

    token_hash = hash_token(token)
    session = get_session(token_hash)

    if not session:
        st.session_state.session_token = None
        st.session_state.logged_in = False
        st.session_state.username = None
        return None

    username = session[1]
    expires_at = session[3]

    try:
        expires_at = datetime.fromisoformat(expires_at)
    except Exception:
        st.session_state.session_token = None
        st.session_state.logged_in = False
        st.session_state.username = None
        return None

    if datetime.utcnow() > expires_at:
        delete_session(token_hash)
        st.session_state.session_token = None
        st.session_state.logged_in = False
        st.session_state.username = None
        return None

    # Sync state
    st.session_state.username = username
    st.session_state.logged_in = True

    return username


# ---------------------------------------------------
# DESTROY SESSION
# ---------------------------------------------------

def destroy_session():
    token = st.session_state.get("session_token")

    if token:
        token_hash = hash_token(token)
        delete_session(token_hash)

    st.session_state.session_token = None
    st.session_state.logged_in = False
    st.session_state.username = None


# ---------------------------------------------------
# LOGIN UI
# ---------------------------------------------------

def login_ui():
    st.subheader("User Login")

    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "" or password == "":
            st.warning("Please enter username and password")
            return False

        user = get_user(username)

        if user is None:
            st.error("User not found")
            return False

        stored_hash = user[3]

        if verify_password(password, stored_hash):
            create_login_session(username)
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Incorrect password")

    st.divider()

    # Google login disabled for stability
    # st.markdown("**Or sign in using Google**")
    # google_login()

    return False


# ---------------------------------------------------
# REGISTER UI
# ---------------------------------------------------

def register_ui():
    st.subheader("Create Account")

    username = st.text_input("New Username").strip()
    email = st.text_input("Email").strip()
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        if username == "" or password == "":
            st.warning("Username and password required")
            return

        if len(password) < 6:
            st.warning("Password must be at least 6 characters")
            return

        password_hash = hash_password(password)

        try:
            create_user(username, email, password_hash)
            st.success("Account created. You can now login.")
        except Exception:
            st.error("Username already exists")


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------

def logout():
    destroy_session()
    st.rerun()