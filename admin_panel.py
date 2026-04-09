import streamlit as st
import sys
import platform
import datetime
import gc
from auth import is_admin
from database import _get_firestore_client
import os
# -----------------------------------
# OS INFO HELPER
# -----------------------------------
def _get_os_info():
    try:
        system = platform.system()

        if system == "Windows":
            return f"Windows {platform.release()}"

        elif system == "Linux":
            try:
                import distro
                distro_name = distro.name(pretty=True).replace("GNU/Linux", "").strip()
                return distro_name
            except:
                return "Linux"

        elif system == "Darwin":
            mac_ver = platform.mac_ver()[0]
            return f"macOS {mac_ver}" if mac_ver else "macOS"

        return system

    except:
        return "Unknown"
# -----------------------------------
# ARCHITECTURE INFO HELPER
# -----------------------------------
def _get_arch():
    try:
        arch = platform.machine().lower()

        if arch in ["amd64", "x86_64"]:
            return "x86_64"

        elif "arm" in arch or "aarch" in arch:
            return "ARM64"

        return arch.upper()

    except:
        return "Unknown"
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
# FEEDBACK ANALYTICS (CACHED)
# -----------------------------------
@st.cache_data(ttl=300)
def _get_feedback_stats():
    """
    Single-pass aggregation over the feedback collection.
    Returns lightweight scalar / short-list results only.
    """
    try:
        db = _get_firestore_client()
        docs = db.collection("feedback").stream()

        total = 0
        yes = somewhat = no = 0
        too_high = about_right = too_low = 0
        star_sum = 0
        star_count = 0
        model_counts = {}          # {"Random Forest": N, "XGBoost": N, …}
        actual_salaries = []       # for median / avg comparison (capped at 500)

        for doc in docs:
            data = doc.to_dict()
            total += 1

            acc = data.get("accuracy_rating")
            if acc == "Yes":
                yes += 1
            elif acc == "Somewhat":
                somewhat += 1
            elif acc == "No":
                no += 1

            direction = data.get("direction")
            if direction == "Too High":
                too_high += 1
            elif direction == "About Right":
                about_right += 1
            elif direction == "Too Low":
                too_low += 1

            star = data.get("star_rating")
            if isinstance(star, (int, float)):
                star_sum += star
                star_count += 1

            model = data.get("model_used", "Unknown")
            model_counts[model] = model_counts.get(model, 0) + 1

            actual = data.get("actual_salary")
            if isinstance(actual, (int, float)) and actual > 0 and len(actual_salaries) < 500:
                actual_salaries.append(actual)

        avg_star = round(star_sum / star_count, 2) if star_count > 0 else 0
        pct_positive = round(yes / total * 100, 1) if total > 0 else 0

        import statistics
        median_actual = round(statistics.median(actual_salaries), 2) if actual_salaries else None

        # ---- Percentages ----
        pct_somewhat = round(somewhat / total * 100, 1) if total > 0 else 0
        pct_no = round(no / total * 100, 1) if total > 0 else 0

        dir_total = too_high + about_right + too_low
        pct_too_high = round(too_high / dir_total * 100, 1) if dir_total > 0 else 0
        pct_about_right = round(about_right / dir_total * 100, 1) if dir_total > 0 else 0
        pct_too_low = round(too_low / dir_total * 100, 1) if dir_total > 0 else 0

        pct_actual_salary = (
            round(len(actual_salaries) / total * 100, 1)
            if total > 0 else 0
        )

        return {
            "total": total,
            "yes": yes,
            "somewhat": somewhat,
            "no": no,
            "too_high": too_high,
            "about_right": about_right,
            "too_low": too_low,
            "avg_star": avg_star,
            "pct_positive": pct_positive,
            "pct_somewhat": pct_somewhat,
            "pct_no": pct_no,

            "pct_too_high": pct_too_high,
            "pct_about_right": pct_about_right,
            "pct_too_low": pct_too_low,

            "pct_actual_salary": pct_actual_salary,
            "model_counts": model_counts,
            "median_actual": median_actual,
            "actual_salary_count": len(actual_salaries),
        }

    except Exception:
        return None

# -----------------------------------
# RECENT FEEDBACK (LIMITED)
# -----------------------------------
@st.cache_data(ttl=120)
def _get_recent_feedback(limit=5):
    try:
        db = _get_firestore_client()

        docs = (
            db.collection("feedback")
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
            .stream()
        )

        return [doc.to_dict() for doc in docs]

    except:
        return None

# ===================================
# DETAILED LOCAL ANALYTICS
# ===================================
# =============================================================================
# LOCAL DIAGNOSTICS — admin_panel.py INSERT
# =============================================================================
# INSERTION POINT:
#   Find the block near the bottom of show_admin_panel() that reads:
#
#       st.divider()
#       st.subheader("Memory & Cache")
#
#   Insert the ENTIRE block below BEFORE that line.
#   Do not remove or move the existing Memory & Cache section.
# =============================================================================
#
# Also add these two helper functions ABOVE show_admin_panel() in admin_panel.py,
# alongside the existing helpers like _mem_mb(), _get_os_info(), etc.
# The helper functions are in PART A.
# The insertion block for inside show_admin_panel() is in PART B.
# =============================================================================


# =============================================================================
# PART A — Helper functions (add above show_admin_panel, with existing helpers)
# =============================================================================

def _is_local() -> bool:
    """
    Returns True if the app is running locally (not on Streamlit Cloud or
    any remote deployment). Reads the IS_LOCAL secret/config flag first;
    falls back to environment variable detection.
    """
    try:
        # Primary: explicit flag set by the developer in secrets.toml
        # In secrets.toml (local):  IS_LOCAL = true
        # In Streamlit Cloud secrets: IS_LOCAL = false  (or omit it)
        val = st.secrets.get("IS_LOCAL", None)
        if val is not None:
            return bool(val)
    except Exception:
        pass

    # Secondary: Streamlit Cloud sets STREAMLIT_SHARING_MODE or
    # runs inside a specific container environment.
    try:
        import os as _os
        # Streamlit Cloud exposes this variable in its runtime
        if _os.environ.get("STREAMLIT_SHARING_MODE"):
            return False
        # Render, Railway, Heroku, etc. typically set PORT
        # but so does local Docker — so we don't rely on PORT alone.
        # A missing HOME or a /app working directory is a stronger signal.
        home = _os.environ.get("HOME", "")
        cwd  = _os.getcwd()
        if home in ("/home/appuser", "/app") or cwd.startswith("/app"):
            return False
    except Exception:
        pass

    return True  # assume local if nothing says otherwise


def _get_deployment_label() -> str:
    """Human-readable deployment platform label."""
    try:
        import os as _os
        if st.secrets.get("IS_LOCAL", None) is True:
            return "Local"
        if st.secrets.get("IS_LOCAL", None) is False:
            return "Streamlit Cloud"
        if _os.environ.get("STREAMLIT_SHARING_MODE"):
            return "Streamlit Cloud"
        home = _os.environ.get("HOME", "")
        cwd  = _os.getcwd()
        if home in ("/home/appuser", "/app") or cwd.startswith("/app"):
            return "Streamlit Cloud"
    except Exception:
        pass
    return "Local"


@st.cache_data(ttl=30)
def _get_process_snapshot() -> dict:
    """
    Collects process-level metrics via psutil.
    Cached for 30 seconds to prevent UI lag on reruns.
    Returns an empty dict if psutil is unavailable.
    """
    result = {}
    try:
        import psutil, os as _os
        proc = psutil.Process(_os.getpid())

        with proc.oneshot():  # single kernel call for all attributes
            mem   = proc.memory_info()
            cpu_p = proc.cpu_percent(interval=None)  # non-blocking
            times = proc.cpu_times()
            fds   = None
            thrs  = None
            try:
                fds  = proc.num_fds()       # POSIX only
            except Exception:
                pass
            try:
                thrs = proc.num_threads()
            except Exception:
                pass
            try:
                create_time = proc.create_time()
                import datetime as _dt
                started = _dt.datetime.fromtimestamp(create_time)
                uptime_s = (_dt.datetime.now() - started).total_seconds()
                result["uptime_s"]   = uptime_s
                result["started_at"] = started.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        result["rss_mb"]      = mem.rss / 1024 / 1024
        result["vms_mb"]      = mem.vms / 1024 / 1024
        result["cpu_pct"]     = cpu_p
        result["cpu_user_s"]  = round(times.user, 2)
        result["cpu_sys_s"]   = round(times.system, 2)
        if fds  is not None: result["open_fds"]   = fds
        if thrs is not None: result["threads"]    = thrs

    except ImportError:
        pass
    except Exception:
        pass
    return result


@st.cache_data(ttl=60)
def _get_system_snapshot() -> dict:
    """
    Collects system-wide resource metrics.
    Cached for 60 seconds — system stats change slowly enough.
    Returns an empty dict if psutil is unavailable.
    """
    result = {}
    try:
        import psutil

        # ---- CPU ----
        try:
            result["cpu_logical"]   = psutil.cpu_count(logical=True)
            result["cpu_physical"]  = psutil.cpu_count(logical=False)
            freq = psutil.cpu_freq()
            if freq:
                result["cpu_freq_mhz"] = round(freq.current, 0)
        except Exception:
            pass

        # ---- RAM ----
        try:
            vm = psutil.virtual_memory()
            result["ram_total_mb"]     = vm.total    / 1024 / 1024
            result["ram_available_mb"] = vm.available / 1024 / 1024
            result["ram_used_pct"]     = vm.percent
        except Exception:
            pass

        # ---- Swap ----
        try:
            sw = psutil.swap_memory()
            result["swap_total_mb"] = sw.total / 1024 / 1024
            result["swap_used_mb"]  = sw.used  / 1024 / 1024
            result["swap_pct"]      = sw.percent
        except Exception:
            pass

        # ---- Disk (primary partition only) ----
        try:
            disk = psutil.disk_usage("/")
            result["disk_total_gb"] = disk.total / 1024 / 1024 / 1024
            result["disk_used_gb"]  = disk.used  / 1024 / 1024 / 1024
            result["disk_free_gb"]  = disk.free  / 1024 / 1024 / 1024
            result["disk_pct"]      = disk.percent
        except Exception:
            pass

        # ---- Network counters (delta since process start — informational) ----
        try:
            net = psutil.net_io_counters()
            result["net_sent_mb"] = net.bytes_sent / 1024 / 1024
            result["net_recv_mb"] = net.bytes_recv / 1024 / 1024
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass
    return result


@st.cache_data(ttl=120)
def _get_python_env_snapshot() -> dict:
    """
    Collects Python interpreter and environment details.
    Cached for 2 minutes — these never change at runtime.
    """
    result = {}
    try:
        import sys as _sys, os as _os, platform as _pl

        result["python_full"]    = _sys.version
        result["python_impl"]    = _pl.python_implementation()  # CPython, PyPy, etc.
        result["executable"]     = _sys.executable
        result["prefix"]         = _sys.prefix
        result["encoding"]       = _sys.getdefaultencoding()
        result["fs_encoding"]    = _sys.getfilesystemencoding()
        result["platform_full"]  = _pl.platform()
        result["node"]           = _pl.node()          # hostname
        result["cwd"]            = _os.getcwd()
        result["pid"]            = _os.getpid()

        # Recursion / thread limits
        result["recursion_limit"] = _sys.getrecursionlimit()
        try:
            import threading
            result["thread_stack_kb"] = threading.stack_size() // 1024
        except Exception:
            pass

        # Resource limits (POSIX only)
        try:
            import resource
            soft_mem, hard_mem = resource.getrlimit(resource.RLIMIT_AS)
            soft_cpu, hard_cpu = resource.getrlimit(resource.RLIMIT_CPU)
            soft_fd,  hard_fd  = resource.getrlimit(resource.RLIMIT_NOFILE)
            _inf = resource.RLIM_INFINITY

            def _fmt_lim(v):
                return "unlimited" if v == _inf else str(v)

            result["rlimit_mem_soft"]  = _fmt_lim(soft_mem)
            result["rlimit_mem_hard"]  = _fmt_lim(hard_mem)
            result["rlimit_cpu_soft"]  = _fmt_lim(soft_cpu)
            result["rlimit_cpu_hard"]  = _fmt_lim(hard_cpu)
            result["rlimit_fd_soft"]   = _fmt_lim(soft_fd)
            result["rlimit_fd_hard"]   = _fmt_lim(hard_fd)
        except ImportError:
            pass  # Windows — resource module not available
        except Exception:
            pass

        # Environment variables relevant to the app (safe subset only)
        safe_env_keys = [
            "HOME", "PATH", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV",
            "PORT", "STREAMLIT_SHARING_MODE", "TZ", "LANG", "LC_ALL",
        ]
        result["env_vars"] = {
            k: os.environ.get(k, "(not set)")
            for k in safe_env_keys
        }

    except Exception:
        pass
    return result


@st.cache_data(ttl=300)
def _get_installed_packages_subset() -> list[dict]:
    """
    Returns a focused list of installed packages relevant to this app.
    Avoids iterating all packages (which can be slow and memory-heavy).
    Cached for 5 minutes.
    """
    relevant = [
        "streamlit", "pandas", "numpy", "scikit-learn", "xgboost",
        "joblib", "plotly", "requests", "firebase-admin", "google-cloud-firestore",
        "spacy", "mlxtend", "pdfminer.six", "reportlab", "openpyxl",
        "psutil", "distro", "python-docx", "pillow",
    ]
    result = []
    try:
        import importlib.metadata as _meta
        for pkg in relevant:
            try:
                version = _meta.version(pkg)
                result.append({"package": pkg, "version": version, "status": "installed"})
            except _meta.PackageNotFoundError:
                result.append({"package": pkg, "version": "—", "status": "not found"})
            except Exception:
                result.append({"package": pkg, "version": "error", "status": "error"})
    except ImportError:
        pass
    except Exception:
        pass
    return result



# -----------------------------------
# ADMIN PANEL
# -----------------------------------
def show_admin_panel(user_email):

    if not is_admin():
        st.error("Access denied.")
        return

    st.header("Admin")
    st.caption("System diagnostics and monitoring. All data is fetched on demand to minimise database reads.")
    st.divider()

    # ==============================
    # SYSTEM
    # ==============================
    st.subheader("System")

    try:
        import sklearn
        sklearn_version = sklearn.__version__
    except Exception:
        sklearn_version = "Not available"

    try:
        import xgboost as xgb
        xgb_version = xgb.__version__
    except Exception:
        xgb_version = "Not available"

    try:
        import pandas as pd
        pd_version = pd.__version__
    except Exception:
        pd_version = "Not available"   

    try:
        import spacy
        spacy_version = spacy.__version__
    except Exception:
        spacy_version = "Not available" 

    try:
        import mlxtend as mlx
        mlxtend_version = mlx.__version__
    except Exception:
        mlxtend_version = "Not available"

    os_info = _get_os_info()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("OS", os_info)
    c3.metric("Arch", _get_arch())
    c4.metric("Process ID", os.getpid())

    c5, c6, c7 = st.columns(3)
    c5.metric("Streamlit", st.__version__)
    c6.metric("Scikit-learn", sklearn_version)
    c7.metric("XGBoost", xgb_version)

    c8, c9, _ = st.columns(3)
    c8.metric("SpaCy", spacy_version)
    c9.metric("Pandas", pd_version)

    st.divider()

    # ==============================
    # LOCAL DIAGNOSTICS
    # ==============================
    if _is_local():

        st.subheader("Local Diagnostics")
        st.caption(
            "Extended system diagnostics available because this instance is running locally. "
            "These sections are hidden on remote deployments to avoid exposing environment details."
        )

        # ---------- PROCESS METRICS ----------
        show_process = st.toggle(
            "Show Process Metrics",
            key="diag_process_toggle",
            value=False,
        )

        if show_process:
            with st.expander("Process Metrics", expanded=True):
                if st.button("Refresh Process Metrics", key="diag_proc_refresh"):
                    _get_process_snapshot.clear()

                snap = _get_process_snapshot()

                if not snap:
                    st.warning(
                        "psutil is not installed or process metrics are unavailable. "
                        "Install psutil to enable this section."
                    )
                else:
                    st.caption(
                        "Metrics are cached for 30 seconds. "
                        "Click Refresh to fetch a new snapshot immediately."
                    )

                    # Row 1: memory
                    p1, p2, p3 = st.columns(3)
                    p1.metric("RSS (Physical RAM)", f"{snap.get('rss_mb', 0):.1f} MB")
                    p2.metric("VMS (Virtual Memory)", f"{snap.get('vms_mb', 0):.1f} MB")
                    p3.metric("CPU Usage (Non-blocking)", f"{snap.get('cpu_pct', 0):.1f}%")

                    # Row 2: CPU time, threads, file descriptors
                    p4, p5, p6 = st.columns(3)
                    p4.metric("CPU User Time", f"{snap.get('cpu_user_s', '—')} s")
                    p5.metric("CPU System Time", f"{snap.get('cpu_sys_s', '—')} s")
                    if "threads" in snap:
                        p6.metric("Threads", snap["threads"])
                    else:
                        p6.metric("Threads", "—")

                    # Row 3: file descriptors, uptime
                    p7, p8, p9 = st.columns(3)
                    if "open_fds" in snap:
                        p7.metric("Open File Descriptors", snap["open_fds"])
                    else:
                        p7.metric("Open File Descriptors", "N/A (Windows)")

                    if "uptime_s" in snap:
                        uptime_s = int(snap["uptime_s"])
                        h, rem = divmod(uptime_s, 3600)
                        m, s   = divmod(rem, 60)
                        p8.metric("Process Uptime", f"{h}h {m}m {s}s")
                        p9.metric("Started At", snap.get("started_at", "—"))
                    else:
                        p8.metric("Process Uptime", "—")
                        p9.metric("Started At", "—")

        # ---------- SYSTEM RESOURCES ----------
        show_system = st.toggle(
            "Show System Resources",
            key="diag_system_toggle",
            value=False,
        )

        if show_system:
            with st.expander("System Resources", expanded=True):
                if st.button("Refresh System Resources", key="diag_sys_refresh"):
                    _get_system_snapshot.clear()

                ssnap = _get_system_snapshot()

                if not ssnap:
                    st.warning(
                        "psutil is not installed or system metrics are unavailable."
                    )
                else:
                    st.caption("Cached for 60 seconds. Click Refresh to fetch immediately.")

                    # CPU
                    st.markdown("**CPU**")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Logical Cores", ssnap.get("cpu_logical", "—"))
                    sc2.metric("Physical Cores", ssnap.get("cpu_physical", "—"))
                    sc3.metric(
                        "Clock Speed",
                        f"{ssnap['cpu_freq_mhz']:.0f} MHz" if "cpu_freq_mhz" in ssnap else "—"
                    )

                    # RAM
                    st.markdown("**RAM**")
                    sr1, sr2, sr3 = st.columns(3)
                    sr1.metric(
                        "Total RAM",
                        f"{ssnap['ram_total_mb']:.0f} MB" if "ram_total_mb" in ssnap else "—"
                    )
                    sr2.metric(
                        "Available RAM",
                        f"{ssnap['ram_available_mb']:.0f} MB" if "ram_available_mb" in ssnap else "—"
                    )
                    sr3.metric(
                        "RAM Used",
                        f"{ssnap['ram_used_pct']:.1f}%" if "ram_used_pct" in ssnap else "—"
                    )

                    # Swap
                    if ssnap.get("swap_total_mb", 0) > 0:
                        st.markdown("**Swap**")
                        ss1, ss2, ss3 = st.columns(3)
                        ss1.metric("Total Swap", f"{ssnap['swap_total_mb']:.0f} MB")
                        ss2.metric("Used Swap",  f"{ssnap['swap_used_mb']:.0f} MB")
                        ss3.metric("Swap Used",  f"{ssnap['swap_pct']:.1f}%")

                    # Disk
                    st.markdown("**Disk (primary partition)**")
                    sd1, sd2, sd3, sd4 = st.columns(4)
                    sd1.metric(
                        "Total",
                        f"{ssnap['disk_total_gb']:.1f} GB" if "disk_total_gb" in ssnap else "—"
                    )
                    sd2.metric(
                        "Used",
                        f"{ssnap['disk_used_gb']:.1f} GB" if "disk_used_gb" in ssnap else "—"
                    )
                    sd3.metric(
                        "Free",
                        f"{ssnap['disk_free_gb']:.1f} GB" if "disk_free_gb" in ssnap else "—"
                    )
                    sd4.metric(
                        "Used %",
                        f"{ssnap['disk_pct']:.1f}%" if "disk_pct" in ssnap else "—"
                    )

                    # Network
                    if "net_sent_mb" in ssnap:
                        st.markdown("**Network I/O (cumulative since system boot)**")
                        sn1, sn2 = st.columns(2)
                        sn1.metric("Sent",     f"{ssnap['net_sent_mb']:.1f} MB")
                        sn2.metric("Received", f"{ssnap['net_recv_mb']:.1f} MB")

        # ---------- PYTHON ENVIRONMENT ----------
        show_env = st.toggle(
            "Show Python Environment",
            key="diag_env_toggle",
            value=False,
        )

        if show_env:
            with st.expander("Python Environment", expanded=True):
                esnap = _get_python_env_snapshot()

                if not esnap:
                    st.warning("Could not collect Python environment details.")
                else:
                    st.caption("Cached for 2 minutes. These values do not change at runtime.")

                    # Interpreter
                    st.markdown("**Interpreter**")
                    e1, e2 = st.columns(2)
                    e1.metric("Implementation", esnap.get("python_impl", "—"))
                    e2.metric("Default Encoding", esnap.get("encoding", "—"))

                    st.text(f"Full version : {esnap.get('python_full', '—')}")
                    st.text(f"Executable   : {esnap.get('executable', '—')}")
                    st.text(f"Prefix       : {esnap.get('prefix', '—')}")
                    st.text(f"Working dir  : {esnap.get('cwd', '—')}")
                    st.text(f"Hostname     : {esnap.get('node', '—')}")
                    st.text(f"Platform     : {esnap.get('platform_full', '—')}")

                    # Limits
                    st.markdown("**Runtime Limits**")
                    l1, l2 = st.columns(2)
                    l1.metric("Recursion Limit", esnap.get("recursion_limit", "—"))
                    l2.metric(
                        "Thread Stack",
                        f"{esnap['thread_stack_kb']} KB" if "thread_stack_kb" in esnap else "—"
                    )

                    if "rlimit_fd_soft" in esnap:
                        st.markdown("**OS Resource Limits (POSIX)**")
                        r1, r2, r3 = st.columns(3)
                        r1.metric(
                            "File Descriptors",
                            f"{esnap['rlimit_fd_soft']} / {esnap['rlimit_fd_hard']}"
                        )
                        r2.metric(
                            "CPU Time (s)",
                            f"{esnap['rlimit_cpu_soft']} / {esnap['rlimit_cpu_hard']}"
                        )
                        r3.metric(
                            "Address Space",
                            f"{esnap['rlimit_mem_soft']} / {esnap['rlimit_mem_hard']}"
                        )

                    # Selected environment variables
                    if "env_vars" in esnap:
                        st.markdown("**Relevant Environment Variables**")
                        env_rows = [
                            {"Variable": k, "Value": v}
                            for k, v in esnap["env_vars"].items()
                            if v != "(not set)"
                        ]
                        if env_rows:
                            import pandas as _pd
                            st.dataframe(
                                _pd.DataFrame(env_rows),
                                width="stretch",
                                hide_index=True,
                            )
                        else:
                            st.caption("No relevant environment variables detected.")

        # ---------- INSTALLED PACKAGES ----------
        show_pkgs = st.toggle(
            "Show Installed Packages",
            key="diag_pkgs_toggle",
            value=False,
        )

        if show_pkgs:
            with st.expander("Installed Packages (App-Relevant)", expanded=True):
                st.caption(
                    "Shows only packages relevant to this application. "
                    "Cached for 5 minutes."
                )
                pkgs = _get_installed_packages_subset()

                if pkgs:
                    import pandas as _pd
                    df_pkgs = _pd.DataFrame(pkgs)
                    # Highlight missing
                    missing = df_pkgs[df_pkgs["status"] != "installed"]
                    installed = df_pkgs[df_pkgs["status"] == "installed"]

                    st.dataframe(installed, width="stretch", hide_index=True)

                    if not missing.empty:
                        st.warning(
                            f"{len(missing)} relevant package(s) not found: "
                            + ", ".join(missing["package"].tolist())
                        )
                else:
                    st.warning("Could not retrieve package information.")
    # ==============================
    # FIREBASE
    # ==============================
    st.divider()
    st.subheader("Firebase")

    try:
        project_id = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"]
    except:
        project_id = "Not set"

    api_key_status = "Available" if "FIREBASE_API_KEY" in st.secrets else "Missing"
    service_acc_status = "Available" if "FIREBASE_SERVICE_ACCOUNT" in st.secrets else "Missing"

    c1, c2, c3 = st.columns(3)
    c1.metric("Project ID", project_id)
    c2.metric("API Key", api_key_status)
    c3.metric("Service Account", service_acc_status)

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
    # FEEDBACK ANALYTICS
    # ==============================
    st.subheader("Feedback Analytics")

    if st.button("Load Feedback Analytics", key="feedback_btn"):
        with st.spinner("Loading feedback data..."):
            stats = _get_feedback_stats()
        st.session_state["feedback_stats"] = stats

    # Output in expander
    if "feedback_stats" in st.session_state and st.session_state["feedback_stats"]:
        stats = st.session_state["feedback_stats"]

        with st.expander("View Feedback Analytics", expanded=True):

            @st.fragment
            def render_feedback_dashboard():

                # -------------------------
                # Metrics
                # -------------------------

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Feedback", stats["total"])
                k2.metric("Accuracy", f"{stats['pct_positive']}%", help="Percentage of 'Yes' responses")
                k3.metric("Average Rating", stats["avg_star"])

                if stats["median_actual"] is not None:
                    k4.metric("Median Actual Salary", f"${stats['median_actual']:,.0f}")
                else:
                    k4.metric("Median Actual Salary", "N/A")

                st.markdown("#### Breakdown")

                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Yes", f"{stats['pct_positive']}%")
                b2.metric("Somewhat", f"{stats['pct_somewhat']}%")
                b3.metric("No", f"{stats['pct_no']}%")
                b4.metric("Actual Salary Coverage", f"{stats['pct_actual_salary']}%", help="Users who reported actual salary")
                
                st.divider()
                # Main layout: metrics (left) + chart (right)
                left, right = st.columns([1, 1])
                with left:
                    st.markdown("#### Feedback Accuracy Distribution")

                    if stats["total"] > 0:
                        import plotly.graph_objects as go

                        fig_acc = go.Figure(data=[
                            go.Pie(
                                labels=["Yes", "Somewhat", "No"],
                                values=[stats["yes"], stats["somewhat"], stats["no"]],
                                hole=0.4,
                                marker=dict(
                                    colors=["#4F8EF7", "#38BDF8", "#F59E0B"]
                                ),
                                textinfo="label+percent",
                                textposition="inside",
                                textfont=dict(color="white"),
                                #pull=[0.02, 0.02, 0.04]
                            )
                        ])

                        fig_acc.update_layout(
                            height=350,
                            paper_bgcolor="#141A22",
                            plot_bgcolor="#1B2230",
                            font=dict(color="#E6EAF0"),
                            showlegend=False,
                            margin=dict(l=10, r=10, t=30, b=10)
                        )

                        st.plotly_chart(fig_acc, width='stretch')
                    
                # -------------------------
                # RIGHT: Chart
                # -------------------------
                with right:
                    st.markdown("#### Prediction Direction")
                    dir_total = stats["too_high"] + stats["about_right"] + stats["too_low"]
                    if dir_total > 0:
                        fig_dir = go.Figure(go.Pie(
                            labels=["Too High", "About Right", "Too Low"],
                            values=[stats["too_high"], stats["about_right"], stats["too_low"]],
                            hole=0.42,
                            marker=dict(colors=["#EF4444", "#34D399", "#4F8EF7"]),
                            textinfo="label+percent",
                            textposition="inside",
                            textfont=dict(color="white", size=11),
                        ))
                        fig_dir.update_layout(
                            height=350,
                            paper_bgcolor="#141A22",
                            plot_bgcolor="#1B2230",
                            font=dict(color="#E6EAF0"),
                            showlegend=False,
                            margin=dict(l=10, r=10, t=30, b=10)
                        )
                        st.plotly_chart(fig_dir, width='stretch')

                    else:
                        st.caption("No feedback data available")

                if stats["model_counts"]:
                    st.markdown("#### Feedback Submissions by Model")
                    import plotly.express as px
                    mc = stats["model_counts"]
                    fig_mc = px.bar(
                        x=list(mc.keys()),
                        y=list(mc.values()),
                        labels={"x": "Model", "y": "Feedback Count"},
                        color_discrete_sequence=["#4F8EF7"],
                        text=list(mc.values()),
                    )
                    fig_mc.update_traces(textposition="outside", textfont=dict(color="white"))
                    fig_mc.update_layout(
                        title="Feedback Count per Model",
                        xaxis_title="Model",
                        yaxis_title="Count",
                        paper_bgcolor="#141A22",
                        plot_bgcolor="#1B2230",
                        showlegend=False,
                    )
                    st.plotly_chart(fig_mc, width='stretch')

                st.caption("Loaded on demand to minimize database reads")

            render_feedback_dashboard()

    st.divider()
    # ==============================
    # RECENT ACTIVITY OLD
    # ==============================
    #st.subheader("Recent Activity")

    #if st.button("Show Recent Feedback", key="recent_btn_old"):
    #    with st.spinner("Fetching recent feedback..."):
    #        feedback = _get_recent_feedback()
    #    st.session_state["recent_feedback"] = feedback

    ## Output in expander
    #if "recent_feedback" in st.session_state and st.session_state["recent_feedback"]:
    #    feedback = st.session_state["recent_feedback"]

    #    with st.expander("View Recent Feedback", expanded=True):
#
#            for i, item in enumerate(feedback, 1):
#                with st.expander(f"Entry {i} | {item.get('model_used')}"):
#                    st.write("Rating:", item.get("star_rating"))
#                    st.write("Accuracy:", item.get("accuracy_rating"))
#                    # ---- FORMATTED SALARY ----
#                    salary = item.get("predicted_salary")
#                    if isinstance(salary, (int, float)):
#                        st.write("Predicted Salary:", f"${salary:,.2f}")
#                    else:
#                        st.write("Predicted Salary:", salary)
#    st.divider()

    # ==============================
    # RECENT ACTIVITY
    # ==============================
    st.subheader("Recent Activity")

    if st.button("Show Recent Feedback", key="recent_btn"):
        with st.spinner("Fetching recent feedback…"):
            feedback = _get_recent_feedback()
        st.session_state["recent_feedback"] = feedback

    if "recent_feedback" in st.session_state and st.session_state["recent_feedback"]:
        feedback = st.session_state["recent_feedback"]

        with st.expander("Recent Feedback Entries", expanded=True):
            for i, item in enumerate(feedback, 1):
                model_label = item.get("model_used", "Unknown")
                star        = item.get("star_rating", "—")
                accuracy    = item.get("accuracy_rating", "—")
                direction   = item.get("direction", "—")
                salary      = item.get("predicted_salary")
                ts          = item.get("created_at")

                header_parts = [f"Entry {i}", model_label]
                if ts and hasattr(ts, "strftime"):
                    header_parts.append(ts.strftime("%Y-%m-%d %H:%M UTC"))
                elif ts:
                    header_parts.append(str(ts)[:16])

                with st.expander(" | ".join(header_parts)):
                    st.write("Star Rating: ", f"{'★' * int(star) if isinstance(star, (int, float)) else star}")
                    st.write("Accuracy: ", accuracy)
                    st.write("Direction: ", direction)

                    if isinstance(salary, (int, float)):
                        st.write("Predicted Salary: ", f"${salary:,.2f}")

                    actual = item.get("actual_salary")
                    if isinstance(actual, (int, float)) and actual > 0:
                        st.write("Reported Actual Salary: ", f"${actual:,.2f}")

    st.divider()

    # ==============================
    # MEMORY & CACHE
    # ==============================
    st.subheader("Memory & Cache")

    mem = _mem_mb()

    col1, col2 = st.columns([3, 1])

    # RAM Metric (big card)
    if mem >= 0:
        col1.metric("RAM Usage", f"{mem:.1f} MB")
    else:
        col1.caption("psutil not installed")

    # Buttons (stacked, compact)
    if col2.button("Run Garbage Collection", key="run_gc_btn", help="Force Python garbage collection"):
        before = mem
        collected = gc.collect()
        after = _mem_mb()

        st.success(f"Collected {collected} objects")
        st.caption(f"{before:.1f} → {after:.1f} MB")

    if col2.button("Clear Cache", key="clr_cache_btn", help="Clear all @st.cache_data caches"):
        st.cache_data.clear()
        st.success("Cache cleared")
    # ==============================
    # SESSION
    # ==============================
    st.divider()
    st.subheader("Session")
    with st.expander("Advanced: Session Debug"):

        total_keys = len(st.session_state)
        st.metric("Total Session Keys", total_keys)

        # Key category breakdown — lightweight, no raw data shown
        admin_keys    = [k for k in st.session_state if k.startswith("admin") or k == "is_admin"]
        scenario_keys = [k for k in st.session_state if k.startswith("sc_") or "scenario" in k.lower()]
        bulk_keys     = [k for k in st.session_state if k.startswith("bulk_")]
        resume_keys   = [k for k in st.session_state if k.startswith("resume_")]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Admin Keys", len(admin_keys))
        c2.metric("Scenario Keys", len(scenario_keys))
        c3.metric("Bulk Keys", len(bulk_keys))
        c4.metric("Resume Keys", len(resume_keys))

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