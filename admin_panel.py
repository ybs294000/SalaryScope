import streamlit as st
import sys, platform, datetime, gc
from auth import is_admin


def _mem_mb():
    try:
        import psutil, os
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except:
        return -1


def show_admin_panel(user_email):

    if not is_admin():
        st.error("Access denied.")
        return

    st.header("Admin")
    st.caption("System diagnostics. No user data is accessed.")
    st.divider()

    # =========================
    # PLATFORM
    # =========================
    st.subheader("Platform")

    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("OS", platform.system())
    c3.metric("Arch", platform.machine())

    st.metric("Streamlit", st.__version__)
    st.divider()

    # =========================
    # FIREBASE CONFIG
    # =========================
    st.subheader("Firebase")

    try:
        project_id = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"]
    except:
        project_id = "Not set"

    api_key_status = "Available" if "FIREBASE_API_KEY" in st.secrets else "Missing"

    c1, c2 = st.columns(2)
    c1.metric("Project ID", project_id)
    c2.metric("API Key", api_key_status)

    st.divider()

    # =========================
    # AUTH STATUS
    # =========================
    st.subheader("Authentication")

    c1, c2 = st.columns(2)

    c1.metric("Logged User", user_email)
    c2.metric("Admin", "Yes" if st.session_state.get("is_admin") else "No")

    expiry = st.session_state.get("_session_expiry")
    if expiry:
        st.caption(f"Session expires at: {expiry}")

    st.divider()

    # =========================
    # MODEL STATUS
    # =========================
    st.subheader("Model Status")

    try:
        import joblib
        st.success("joblib loaded")
    except:
        st.error("joblib missing")

    import os
    model_files = [
        "model/rf_model_grid.pkl",
        "model/salaryscope_3755_production_model.pkl"
    ]

    for f in model_files:
        st.write(f"{f}: {'Found' if os.path.exists(f) else 'Missing'}")

    st.divider()

    # =========================
    # MEMORY
    # =========================
    st.subheader("Memory")

    mem = _mem_mb()
    if mem >= 0:
        col1, col2 = st.columns(2)
        col1.metric("RAM Usage", f"{mem:.1f} MB")

        if col2.button("Run GC"):
            before = mem
            collected = gc.collect()
            after = _mem_mb()
            st.success(f"Freed {collected} objects")
            st.caption(f"{before:.1f} → {after:.1f} MB")
    else:
        st.caption("Install psutil for memory stats")

    st.divider()

    # =========================
    # CACHE
    # =========================
    st.subheader("Cache")

    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared")

    st.divider()

    # =========================
    # SESSION DEBUG
    # =========================
    st.subheader("Session")

    st.metric("Session Keys", len(st.session_state))

    if st.checkbox("Show session keys"):
        st.json(list(st.session_state.keys()))

    st.metric(
        "UTC Time",
        datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    )