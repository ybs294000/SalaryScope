import streamlit as st
import sys, platform, datetime, gc, os
from auth import is_admin, get_logged_in_user


# -------------------------------
# MEMORY
# -------------------------------
def get_process_memory():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024**2)
    except:
        return -1


# -------------------------------
# ADMIN PANEL
# -------------------------------
def show_admin_panel():

    if not is_admin():
        st.error("Access denied.")
        return

    user_email = get_logged_in_user()

    st.header("Admin")
    st.caption("System diagnostics and configuration.")
    st.divider()

    # =========================
    # PLATFORM
    # =========================
    st.subheader("Platform")

    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("OS", platform.system())
    c3.metric("Architecture", platform.machine())

    st.metric("Streamlit Version", st.__version__)

    st.divider()

    # =========================
    # FIREBASE
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

    # 🔗 Firebase Console (from secrets)
    firebase_url = st.secrets.get("FIREBASE_CONSOLE_URL")
    if firebase_url:
        st.markdown(f"[Open Firebase Console]({firebase_url})")

    st.divider()

    # =========================
    # AUTH
    # =========================
    st.subheader("Authentication")

    c1, c2 = st.columns(2)
    c1.metric("Current User", user_email)
    c2.metric("Admin Access", "Yes" if st.session_state.get("is_admin") else "No")

    expiry = st.session_state.get("_session_expiry")
    if expiry:
        st.caption(f"Session expires at: {expiry}")

    st.divider()

    # =========================
    # APP HEALTH CHECK
    # =========================
    st.subheader("App Health")

    # Secrets check
    secrets_ok = "FIREBASE_SERVICE_ACCOUNT" in st.secrets
    st.metric("Secrets Loaded", "Yes" if secrets_ok else "No")

    # API key check
    api_ok = "FIREBASE_API_KEY" in st.secrets
    st.metric("Firebase Auth", "Configured" if api_ok else "Missing")

    st.divider()

    # =========================
    # MEMORY (APP ONLY)
    # =========================
    st.subheader("App Memory")

    mem = get_process_memory()
    if mem >= 0:
        col1, col2 = st.columns(2)
        col1.metric("Memory Usage", f"{mem:.1f} MB")

        if col2.button("Run Garbage Collection"):
            before = mem
            collected = gc.collect()
            after = get_process_memory()
            st.success(f"Freed {collected} objects")
            st.caption(f"{before:.1f} → {after:.1f} MB")

    st.caption("Streamlit Cloud limit ≈ 2.7 GB")

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