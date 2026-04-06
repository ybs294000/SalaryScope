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

# -----------------------------------
# ADMIN PANEL
# -----------------------------------
def show_admin_panel(user_email):

    if not is_admin():
        st.error("Access denied.")
        return

    st.header("Admin")
    st.caption("System diagnostics and configuration.")
    st.divider()

    # ==============================
    # PLATFORM
    # ==============================
    st.subheader("Platform")

    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("Platform", platform.system())
    c3.metric("Arch", platform.machine())

    c5, c6 = st.columns(2)
    c5.metric("Streamlit Version", st.__version__)
    c6.metric("Scikit-learn Version", sklearn.__version__)
    st.divider()

    # ==============================
    # FIREBASE
    # ==============================
    st.subheader("Firebase")

    try:
        project_id = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"]
    except:
        project_id = "Not set"

    api_key_status = "Available" if "FIREBASE_API_KEY" in st.secrets else "Missing"

    c1, c2 = st.columns(2)
    c1.metric("Project ID", project_id)
    c2.metric("API Key", api_key_status)

    # Use secrets link
    firebase_url = st.secrets.get("FIREBASE_CONSOLE_URL")
    if firebase_url:
        st.markdown(f"[Open Firebase Console]({firebase_url})")

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
    with st.expander("Advanced: Session Debug"):

        st.metric("Total Session Keys", len(st.session_state))

        # Safe display (avoid UI lag)
        if len(st.session_state) < 20:
            if st.checkbox("Show session keys"):
                st.write(list(st.session_state.keys()))
        else:
            st.warning("Large session — showing keys may slow down UI")
            if st.checkbox("Show anyway"):
                st.write(list(st.session_state.keys()))

    st.divider()

    st.metric(
        "Last check (UTC):",
        datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    )