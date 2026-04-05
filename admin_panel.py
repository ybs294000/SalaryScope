import streamlit as st
import sys, platform, datetime, gc, os
from auth import is_admin


# -------------------------------
# SYSTEM INFO HELPERS
# -------------------------------
def get_system_info():
    try:
        import psutil
        cpu_count = psutil.cpu_count()
        ram = psutil.virtual_memory()
        return {
            "cpu": cpu_count,
            "ram_total": ram.total / (1024**3),
            "ram_used": ram.used / (1024**3),
            "ram_percent": ram.percent
        }
    except:
        return None


def get_process_memory():
    try:
        import psutil, os
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024**2)
    except:
        return -1


# -------------------------------
# ADMIN PANEL
# -------------------------------
def show_admin_panel(user_email):

    if not is_admin():
        st.error("Access denied.")
        return

    st.header("Admin")
    st.caption("System diagnostics — lightweight, safe, and meaningful.")
    st.divider()

    # =========================
    # PLATFORM
    # =========================
    st.subheader("Platform")

    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("OS", platform.system())
    c3.metric("Architecture", platform.machine())

    st.metric("Streamlit", st.__version__)

    sysinfo = get_system_info()
    if sysinfo:
        c1, c2, c3 = st.columns(3)
        c1.metric("CPU Cores", sysinfo["cpu"])
        c2.metric("RAM Used", f"{sysinfo['ram_used']:.1f} GB")
        c3.metric("RAM Usage", f"{sysinfo['ram_percent']}%")

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

    st.divider()

    # =========================
    # AUTH
    # =========================
    st.subheader("Authentication")

    c1, c2 = st.columns(2)
    c1.metric("User", user_email)
    c2.metric("Admin", "Yes" if st.session_state.get("is_admin") else "No")

    expiry = st.session_state.get("_session_expiry")
    if expiry:
        st.caption(f"Session expires at: {expiry}")

    st.divider()

    # =========================
    # MODEL HEALTH CHECK
    # =========================


    # =========================
    # MEMORY (APP LEVEL)
    # =========================
    st.subheader("Memory (App Process)")

    mem = get_process_memory()
    if mem >= 0:
        col1, col2 = st.columns(2)
        col1.metric("App Memory", f"{mem:.1f} MB")

        if col2.button("Run GC"):
            before = mem
            collected = gc.collect()
            after = get_process_memory()
            st.success(f"Collected {collected} objects")
            st.caption(f"{before:.1f} → {after:.1f} MB")
    else:
        st.caption("psutil not installed")

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