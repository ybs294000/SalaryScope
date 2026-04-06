import streamlit as st
import sys
import platform
import datetime
import gc

from auth import is_admin
from database import _get_firestore_client


# -----------------------------------
# MEMORY HELPER
# -----------------------------------
def _mem_mb():
    try:
        import psutil, os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except:
        return -1


# -----------------------------------
# FIRESTORE COUNT (SAFE)
# -----------------------------------
def _count_users():
    try:
        db = _get_firestore_client()
        users = list(db.collection("users").stream())
        return len(users)
    except:
        return -1


def _count_predictions():
    try:
        db = _get_firestore_client()
        users = db.collection("predictions").stream()

        total = 0
        for user_doc in users:
            records = db.collection("predictions") \
                        .document(user_doc.id) \
                        .collection("records") \
                        .stream()
            total += len(list(records))

        return total
    except:
        return -1


# -----------------------------------
# ADMIN PANEL
# -----------------------------------
def show_admin_panel(user_email):

    if not is_admin():
        st.error("Access denied.")
        return

    st.header("Admin")
    st.caption("System information. No user personal data is shown.")
    st.divider()

    # ==============================
    # PLATFORM
    # ==============================
    st.subheader("Platform")

    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("Platform", platform.system())
    c3.metric("Arch", platform.machine())

    st.metric("Streamlit Version", st.__version__)

    st.divider()

    # ==============================
    # FIREBASE
    # ==============================
    st.subheader("Firebase")

    project_id = st.secrets.get("FIREBASE_PROJECT_ID", "Not set")

    st.metric("Project ID", project_id)

    st.divider()

    # ==============================
    # USERS
    # ==============================
    st.subheader("Users")

    if st.button("Count Users"):
        with st.spinner("Counting users..."):
            count = _count_users()

        if count >= 0:
            st.metric("Total Users", count)
        else:
            st.warning("Could not fetch users")

    st.divider()

    # ==============================
    # PREDICTIONS
    # ==============================
    st.subheader("Predictions")

    if st.button("Count Predictions"):
        with st.spinner("Counting predictions..."):
            count = _count_predictions()

        if count >= 0:
            st.metric("Total Predictions", count)
        else:
            st.warning("Could not fetch predictions")

    st.divider()

    # ==============================
    # MEMORY
    # ==============================
    st.subheader("Memory")

    mem = _mem_mb()

    if mem >= 0:
        col1, col2 = st.columns(2)

        col1.metric("RAM Usage", f"{mem:.1f} MB")

        if col2.button("Run GC"):
            before = mem
            collected = gc.collect()
            after = _mem_mb()

            st.success(f"Collected {collected} objects")
            st.caption(f"{before:.1f} → {after:.1f} MB")
    else:
        st.caption("Install psutil for memory tracking")

    st.divider()

    # ==============================
    # CACHE
    # ==============================
    st.subheader("Cache")

    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared")

    st.divider()

    # ==============================
    # SESSION
    # ==============================
    st.subheader("Session")

    col1, col2 = st.columns(2)
    col1.metric("Session Keys", len(st.session_state))
    col2.metric(
        "UTC Time",
        datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    )