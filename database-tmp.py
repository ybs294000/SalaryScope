import streamlit as st
from datetime import datetime
import json

# ---------------------------------------------------
# FIRESTORE CLIENT
# ---------------------------------------------------

@st.cache_resource
def _get_firestore_client():
    """
    Initialise and cache the Firestore client.
    Credentials come from st.secrets["FIREBASE_SERVICE_ACCOUNT"]
    which should be the full service account JSON as a TOML table.
    """
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        sa = dict(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
        # Streamlit secrets escapes newlines in private_key — fix them
        if "private_key" in sa:
            sa["private_key"] = sa["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(sa)
        firebase_admin.initialize_app(cred)

    return firestore.client()


def _db():
    return _get_firestore_client()


# ---------------------------------------------------
# LEGACY SQLITE STUB
# Kept so that app.py's `init_db()` and
# `create_prediction_table()` calls don't crash.
# They are now no-ops — all data lives in Firestore.
# ---------------------------------------------------

def init_db():
    """No-op: database is now Firestore."""
    pass


def create_prediction_table():
    """No-op: predictions are stored in Firestore."""
    pass


def delete_expired_sessions():
    """No-op: sessions live in st.session_state, not in a DB."""
    pass


# ---------------------------------------------------
# USER FUNCTIONS
# ---------------------------------------------------

def ensure_firestore_user(username: str, email: str, display_name: str = None):
    """
    Create a Firestore user document if one doesn't already exist.
    Safe to call multiple times (idempotent).
    """
    db = _db()
    ref = db.collection("users").document(username)
    doc = ref.get()
    if not doc.exists:
        ref.set({
            "username": username,
            "email": email,
            "display_name": display_name or username,
            "created_at": datetime.utcnow().isoformat(),
            "auth_provider": "firebase",
        })


def get_user(username: str):
    """
    Return a user tuple (user_id, username, email, password_hash)
    to keep compatibility with any legacy call sites.
    Returns None if not found.
    """
    db = _db()
    doc = db.collection("users").document(username).get()
    if not doc.exists:
        return None
    d = doc.to_dict()
    # Return a tuple matching the old SQLite schema
    return (d.get("username"), d.get("username"), d.get("email"), b"firebase_auth")


def create_user(username: str, email: str, password_hash):
    """
    Legacy compatibility shim — delegates to ensure_firestore_user.
    password_hash is ignored (Firebase manages passwords).
    """
    ensure_firestore_user(username, email)


# ---------------------------------------------------
# SESSION FUNCTIONS
# These are stubs — sessions now live entirely in
# st.session_state (per-browser, not shared).
# Kept so auth.py call sites don't break.
# ---------------------------------------------------

def create_session(username: str, token_hash: str, expires_at):
    """No-op: sessions are managed in st.session_state."""
    pass


def get_session(token_hash: str):
    """No-op: sessions are managed in st.session_state."""
    return None


def delete_session(token_hash: str):
    """No-op: sessions are managed in st.session_state."""
    pass


# ---------------------------------------------------
# PREDICTION FUNCTIONS  (Firestore-backed)
# Same signatures as before — drop-in replacement.
# ---------------------------------------------------

def save_prediction(username: str, model_used: str, input_data: dict, predicted_salary: float):
    """
    Save a salary prediction to Firestore under:
      predictions/{username}/records/{auto-id}
    """
    db = _db()
    db.collection("predictions").document(username).collection("records").add({
        "model_used": model_used,
        "input_data": json.dumps(input_data),
        "predicted_salary": predicted_salary,
        "created_at": datetime.utcnow().isoformat(),
    })


def get_user_predictions(username: str):
    """
    Return a list of tuples matching the old SQLite schema:
      (prediction_id, model_used, input_data, predicted_salary, created_at)

    Ordered by created_at descending, capped at 500 records.
    """
    db = _db()
    docs = (
        db.collection("predictions")
        .document(username)
        .collection("records")
        .order_by("created_at", direction="DESCENDING")
        .limit(500)
        .stream()
    )

    rows = []
    for doc in docs:
        d = doc.to_dict()
        rows.append((
            doc.id,                          # prediction_id
            d.get("model_used", ""),
            d.get("input_data", "{}"),
            d.get("predicted_salary", 0.0),
            d.get("created_at", ""),
        ))

    # Reverse so oldest-first (matches original ORDER BY created_at ASC in profile chart)
    rows.reverse()
    return rows
