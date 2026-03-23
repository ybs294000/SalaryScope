import streamlit as st
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta

from database import create_user, get_user, create_session, get_session, delete_session
from streamlit_cookies_manager import EncryptedCookieManager

# Google OAuth imports
from streamlit_oauth import OAuth2Component
import os
import requests
import base64

def get_base64_image(path):
    with open(path, "rb") as img:
        return base64.b64encode(img.read()).decode()

# ---------------------------------------------------
# COOKIE MANAGER (SECURE - USING SECRETS)
# ---------------------------------------------------

if "COOKIE_SECRET" not in st.secrets:
    st.error("Missing COOKIE_SECRET in Streamlit secrets.")
    st.stop()

cookies = EncryptedCookieManager(
    prefix="salaryscope/",
    password=st.secrets["COOKIE_SECRET"]
)

if not cookies.ready():
    st.stop()


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


def create_login_session(username):

    token = generate_token()
    token_hash = hash_token(token)

    expiry = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)

    create_session(username, token_hash, expiry)

    cookies["session_token"] = token
    cookies.save()

    return token


def get_logged_in_user():

    token = cookies.get("session_token")

    if not token:
        return None

    token_hash = hash_token(token)

    session = get_session(token_hash)

    if not session:
        return None

    username = session[1]
    expires_at = session[3]

    try:
        expires_at = datetime.fromisoformat(expires_at)
    except Exception:
        return None

    if datetime.utcnow() > expires_at:
        delete_session(token_hash)
        return None

    return username


def destroy_session():

    token = cookies.get("session_token")

    if token:
        token_hash = hash_token(token)
        delete_session(token_hash)

    cookies["session_token"] = ""
    cookies.save()

# ---------------------------------------------------
# GET CURRENT APP URL (DYNAMIC REDIRECT)
# ---------------------------------------------------

#def get_current_url():
#    try:
#        # Streamlit provides full current URL (localhost / IP / cloud)
#        return st.get_url()
#    except Exception:
#        return "http://localhost:8501"
def get_current_url():
    return "https://salaryscope-fhl4g2mmypfzrhwhvjcj6o.streamlit.app/"
# ---------------------------------------------------
# GOOGLE LOGIN (SECURE INTEGRATION)
# ---------------------------------------------------

def google_login():
    google_icon = get_base64_image("static/google_icon.png")
    label = f"""
    <img src="data:image/png;base64,{google_icon}" width="18" style="vertical-align:middle; margin-right:8px;">
    Sign in with Google
    """
    CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")

    if not CLIENT_ID or not CLIENT_SECRET:
        return

    redirect_uri =  get_current_url()

    oauth2 = OAuth2Component(
        CLIENT_ID,
        CLIENT_SECRET,
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "https://www.googleapis.com/oauth2/v1/userinfo",
    )

    result = oauth2.authorize_button(
        "Sign in with Google",
        redirect_uri=redirect_uri,
        scope="openid email profile",
        key="google_login",
    )

    if result and "token" in result:

        token = result["token"]["access_token"]

        userinfo = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            params={"access_token": token}
        ).json()

        email = userinfo.get("email")

        if email:

            user = get_user(email)

            if user is None:
                create_user(email, email, b"oauth_account")

            # Use SAME secure session system
            create_login_session(email)

            st.session_state.logged_in = True
            st.session_state.username = email

            st.success(f"Logged in as {email}")
            st.rerun()


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

            st.session_state.logged_in = True
            st.session_state.username = username

            st.success("Login successful")
            st.rerun()

        else:
            st.error("Incorrect password")

    st.divider()
    st.markdown("**Or sign in using Google**")

    google_login()

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

    st.session_state.logged_in = False
    st.session_state.username = None

    st.rerun()