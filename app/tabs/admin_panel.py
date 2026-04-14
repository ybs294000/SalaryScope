"""
admin_panel.py
==============
Admin diagnostics and monitoring panel for SalaryScope.
"""

import streamlit as st
import sys
import platform
import datetime
import gc
from app.core.auth import is_admin
from app.core.database import _get_firestore_client
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
        model_counts = {}
        actual_salaries = []

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

        pct_somewhat = round(somewhat / total * 100, 1) if total > 0 else 0
        pct_no = round(no / total * 100, 1) if total > 0 else 0

        dir_total = too_high + about_right + too_low
        pct_too_high    = round(too_high    / dir_total * 100, 1) if dir_total > 0 else 0
        pct_about_right = round(about_right / dir_total * 100, 1) if dir_total > 0 else 0
        pct_too_low     = round(too_low     / dir_total * 100, 1) if dir_total > 0 else 0

        pct_actual_salary = round(len(actual_salaries) / total * 100, 1) if total > 0 else 0

        return {
            "total": total,
            "yes": yes, "somewhat": somewhat, "no": no,
            "too_high": too_high, "about_right": about_right, "too_low": too_low,
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
# LOCAL DIAGNOSTICS HELPERS
# ===================================

def _is_local() -> bool:
    try:
        val = st.secrets.get("IS_LOCAL", None)
        if val is not None:
            return bool(val)
    except Exception:
        pass
    try:
        import os as _os
        if _os.environ.get("STREAMLIT_SHARING_MODE"):
            return False
        home = _os.environ.get("HOME", "")
        cwd  = _os.getcwd()
        if home in ("/home/appuser", "/app") or cwd.startswith("/app"):
            return False
    except Exception:
        pass
    return True


def _get_deployment_label() -> str:
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
    Cached for 30 s. cpu_percent uses a short interval (0.1 s) inside the
    cache so the returned value is meaningful rather than always 0.0.
    """
    result = {}
    try:
        import psutil, os as _os, time as _time
        proc = psutil.Process(_os.getpid())

        # Prime the cpu_percent counter, then measure after a short pause.
        # 0.15 s is acceptable inside a cached call — it only happens once per
        # 30-second window, never on every Streamlit rerender.
        proc.cpu_percent(interval=None)          # first call primes the counter
        _time.sleep(0.15)
        cpu_p = proc.cpu_percent(interval=None)  # second call returns real value

        with proc.oneshot():
            mem   = proc.memory_info()
            times = proc.cpu_times()
            fds   = None
            thrs  = None
            # Page faults (replaces unreliable RLIMIT_AS)
            page_faults = None
            try:
                faults = proc.memory_full_info()
                # uss = unique set size (Linux/macOS only) — a better "real" RAM figure
                if hasattr(faults, "uss"):
                    result["uss_mb"] = faults.uss / 1024 / 1024
            except Exception:
                pass
            try:
                fds  = proc.num_fds()
            except Exception:
                pass
            try:
                thrs = proc.num_threads()
            except Exception:
                pass
            try:
                ctx = proc.num_ctx_switches()
                result["ctx_voluntary"]   = ctx.voluntary
                result["ctx_involuntary"] = ctx.involuntary
            except Exception:
                pass
            try:
                create_time = proc.create_time()
                import datetime as _dt
                started  = _dt.datetime.fromtimestamp(create_time)
                uptime_s = (_dt.datetime.now() - started).total_seconds()
                result["uptime_s"]   = uptime_s
                result["started_at"] = started.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        result["rss_mb"]     = mem.rss / 1024 / 1024
        result["vms_mb"]     = mem.vms / 1024 / 1024
        result["cpu_pct"]    = cpu_p
        # Format CPU time with a floor so "0.0 s" never appears
        result["cpu_user_s"] = max(round(times.user,   2), 0.01)
        result["cpu_sys_s"]  = max(round(times.system, 2), 0.01)
        if fds  is not None: result["open_fds"] = fds
        if thrs is not None: result["threads"]  = thrs

    except ImportError:
        pass
    except Exception:
        pass
    return result


@st.cache_data(ttl=60)
def _get_system_snapshot() -> dict:
    """System-wide resource metrics. Cached for 60 s."""
    result = {}
    try:
        import psutil

        try:
            result["cpu_logical"]  = psutil.cpu_count(logical=True)
            result["cpu_physical"] = psutil.cpu_count(logical=False)
            freq = psutil.cpu_freq()
            if freq:
                result["cpu_freq_mhz"] = round(freq.current, 0)
        except Exception:
            pass

        try:
            vm = psutil.virtual_memory()
            result["ram_total_mb"]     = vm.total     / 1024 / 1024
            result["ram_available_mb"] = vm.available / 1024 / 1024
            result["ram_used_pct"]     = vm.percent
        except Exception:
            pass

        try:
            sw = psutil.swap_memory()
            result["swap_total_mb"] = sw.total / 1024 / 1024
            result["swap_used_mb"]  = sw.used  / 1024 / 1024
            result["swap_pct"]      = sw.percent
        except Exception:
            pass

        try:
            disk = psutil.disk_usage("/")
            result["disk_total_gb"] = disk.total / 1024 / 1024 / 1024
            result["disk_used_gb"]  = disk.used  / 1024 / 1024 / 1024
            result["disk_free_gb"]  = disk.free  / 1024 / 1024 / 1024
            result["disk_pct"]      = disk.percent
        except Exception:
            pass

        try:
            net = psutil.net_io_counters()
            result["net_sent_mb"] = net.bytes_sent / 1024 / 1024
            result["net_recv_mb"] = net.bytes_recv / 1024 / 1024
            result["net_pkts_sent"] = net.packets_sent
            result["net_pkts_recv"] = net.packets_recv
        except Exception:
            pass

        # Load average (POSIX only — not available on Windows)
        try:
            load = psutil.getloadavg()        # (1min, 5min, 15min)
            result["load_1m"]  = round(load[0], 2)
            result["load_5m"]  = round(load[1], 2)
            result["load_15m"] = round(load[2], 2)
        except Exception:
            pass

        # Boot time
        try:
            import datetime as _dt
            bt = psutil.boot_time()
            result["boot_time"] = _dt.datetime.fromtimestamp(bt).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            pass

    except ImportError:
        pass
    except Exception:
        pass
    return result


@st.cache_data(ttl=120)
def _get_python_env_snapshot() -> dict:
    """Python interpreter and environment details. Cached for 2 min."""
    result = {}
    try:
        import sys as _sys, os as _os, platform as _pl

        result["python_full"]   = _sys.version
        result["python_impl"]   = _pl.python_implementation()
        result["executable"]    = _sys.executable
        result["prefix"]        = _sys.prefix
        result["encoding"]      = _sys.getdefaultencoding()
        result["fs_encoding"]   = _sys.getfilesystemencoding()
        result["platform_full"] = _pl.platform()
        result["node"]          = _pl.node()
        result["cwd"]           = _os.getcwd()
        result["pid"]           = _os.getpid()
        result["recursion_limit"] = _sys.getrecursionlimit()

        try:
            import threading
            result["thread_stack_kb"] = threading.stack_size() // 1024
        except Exception:
            pass

        # POSIX resource limits — only surface the one that is useful:
        # open file descriptor limit. AS and CPU are almost always
        # unlimited and showing "unlimited / unlimited" looks broken.
        try:
            import resource
            soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
            _inf = resource.RLIM_INFINITY
            _fmt = lambda v: "unlimited" if v == _inf else str(v)
            result["rlimit_fd_soft"] = _fmt(soft_fd)
            result["rlimit_fd_hard"] = _fmt(hard_fd)

            # Only include RLIMIT_AS if it is actually constrained
            soft_as, hard_as = resource.getrlimit(resource.RLIMIT_AS)
            if soft_as != _inf or hard_as != _inf:
                result["rlimit_as_soft"] = _fmt(soft_as)
                result["rlimit_as_hard"] = _fmt(hard_as)

            # Only include RLIMIT_CPU if it is actually constrained
            soft_cpu, hard_cpu = resource.getrlimit(resource.RLIMIT_CPU)
            if soft_cpu != _inf or hard_cpu != _inf:
                result["rlimit_cpu_soft"] = _fmt(soft_cpu)
                result["rlimit_cpu_hard"] = _fmt(hard_cpu)

        except ImportError:
            pass
        except Exception:
            pass

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
    """Focused package list for this app. Cached for 5 min."""
    relevant = [
        "streamlit", "pandas", "numpy", "scikit-learn", "xgboost",
        "joblib", "plotly", "requests", "firebase-admin", "google-cloud-firestore",
        "spacy", "mlxtend", "pdfminer.six", "reportlab", "openpyxl",
        "psutil", "distro", "pillow",
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


# =============================================================================
# << SYSTEM PLOTS BLOCK START >>
# Rollback: delete _get_historical_snapshots(), _record_snapshot(),
# _build_system_plots(), and their two call lines inside show_admin_panel().
# =============================================================================

def _record_snapshot() -> None:
    """
    Appends one process + system data point to st.session_state["_diag_history"].
    Called only when the admin explicitly clicks "Capture Snapshot".
    Never runs automatically. Each call is O(1) — no loops, no network.
    Maximum 60 points stored; oldest are dropped to prevent memory growth.
    """
    import datetime as _dt

    try:
        import psutil, os as _os
        proc = psutil.Process(_os.getpid())
        rss  = proc.memory_info().rss / 1024 / 1024

        vm   = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        point = {
            "ts":          _dt.datetime.now().strftime("%H:%M:%S"),
            "rss_mb":      round(rss, 1),
            "ram_used_pct": vm.percent,
            "disk_used_pct": disk.percent,
        }
    except Exception:
        return

    history = st.session_state.get("_diag_history", [])
    history.append(point)
    if len(history) > 60:
        history = history[-60:]
    st.session_state["_diag_history"] = history


def _get_historical_snapshots() -> list[dict]:
    """Returns the accumulated snapshot history from session state."""
    return st.session_state.get("_diag_history", [])


def _build_system_plots(
    proc_snap: dict,
    sys_snap: dict,
) -> None:
    """
    Renders non-auto-refreshing Plotly charts from already-fetched snapshots
    and from the accumulated capture history.

    All data comes from dicts that were already computed and cached —
    this function does zero psutil calls and zero network calls.
    Never called on page load; only called when the user toggles it on.

    Parameters
    ----------
    proc_snap : dict  — output of _get_process_snapshot()
    sys_snap  : dict  — output of _get_system_snapshot()
    """
    import plotly.graph_objects as go
    import plotly.express as px

    _BG       = "#141A22"
    _BG_INNER = "#1B2230"
    _BG_INPUT   = "#1B2230"
    _BORDER   = "#283142"
    _TEXT     = "#E6EAF0"
    _MUTED    = "#9CA6B5"
    _BLUE     = "#4F8EF7"
    _GREEN    = "#34D399"
    _AMBER    = "#F59E0B"
    _RED      = "#EF4444"
    _PURPLE   = "#A78BFA"

    _SAFE   = "#22C55E"   # success
    _WARN   = "#F59E0B"   # warning
    _DANGER = "#EF4444"   # error
    _PRIMARY = "#3E7DE0"  # app primary

    _BASE = dict(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG_INNER,
        font=dict(color=_TEXT, size=12),
        margin=dict(l=50, r=20, t=40, b=50),
    )

    st.caption(
        "Charts are built from already-cached snapshot data. "
        "They do not auto-refresh. Use 'Capture Snapshot' below to add "
        "time-series points manually."
    )

    # ------------------------------------------------------------------
    # ROW 1 — Gauge: Process RSS  |  Gauge: System RAM used %
    # ------------------------------------------------------------------
    st.markdown("**Memory at a glance**")

    rss_mb      = proc_snap.get("rss_mb", 0)
    ram_total   = sys_snap.get("ram_total_mb", 1)
    ram_used_pct = sys_snap.get("ram_used_pct", 0)

    col_g1, col_g2, col_g3 = st.columns(3)

    with col_g1:
        rss_pct = (rss_mb / ram_total) * 100

        if rss_pct < 50:
            bar_color = _SAFE
        elif rss_pct < 80:
            bar_color = _WARN
        else:
            bar_color = _DANGER

        fig_rss = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(rss_mb, 1),
            title=dict(
                text="Process Memory (MB)",
                font=dict(color=_MUTED, size=13)
            ),
            number=dict(
                suffix=" MB",
                font=dict(color=bar_color, size=22)
            ),
            gauge=dict(
                axis=dict(
                    range=[0, max(ram_total, rss_mb * 2)],
                    tickfont=dict(color=_MUTED, size=10),
                    tickcolor=_BORDER,
                ),
                bar=dict(color=bar_color, thickness=0.3),
                bgcolor=_BG_INPUT,
                bordercolor=_BORDER,
                steps=[
                    dict(range=[0, ram_total * 0.5], color="#1E2A3A"),
                    dict(range=[ram_total * 0.5, ram_total * 0.8], color="#2A2215"),
                    dict(range=[ram_total * 0.8, max(ram_total, rss_mb * 2)], color="#2A1515"),
                ],
                threshold=dict(
                    line=dict(color=_DANGER, width=2),
                    thickness=0.75,
                    value=ram_total * 0.8,
                ),
            ),
        ))
        fig_rss.update_layout(height=220, **_BASE)
        st.plotly_chart(fig_rss, width='stretch')

        process_pct = (rss_mb / ram_total) * 100
        st.caption(f"Process uses {process_pct:.2f}% of system RAM")

    with col_g2:
        if ram_used_pct < 60:
            ram_color = _SAFE
        elif ram_used_pct < 80:
            ram_color = _WARN
        else:
            ram_color = _DANGER

        fig_ram = go.Figure(go.Indicator(
            mode="gauge+number",
            value=ram_used_pct,
            title=dict(text="System RAM Used (%)", font=dict(color=_MUTED, size=13)),
            number=dict(suffix="%", font=dict(color=ram_color, size=22)),
            gauge=dict(
                axis=dict(range=[0, 100], tickfont=dict(color=_MUTED, size=10), tickcolor=_BORDER),
                bar=dict(color=ram_color, thickness=0.3),
                bgcolor=_BG_INNER,
                bordercolor=_BORDER,
                steps=[
                    dict(range=[0, 60],  color="#1B2A3A"),
                    dict(range=[60, 80], color="#2A2215"),
                    dict(range=[80, 100], color="#2A1515"),
                ],
                threshold=dict(
                    line=dict(color=_RED, width=2),
                    thickness=0.75,
                    value=85,
                ),
            ),
        ))
        fig_ram.update_layout(height=220, **_BASE)
        st.plotly_chart(fig_ram, width='stretch')

    with col_g3:
        disk_pct = sys_snap.get("disk_pct", 0)

        if disk_pct < 60:
            disk_color = _SAFE
        elif disk_pct < 80:
            disk_color = _WARN
        else:
            disk_color = _DANGER

        disk_pct = sys_snap.get("disk_pct", 0)
        fig_disk = go.Figure(go.Indicator(
            mode="gauge+number",
            value=disk_pct,
            title=dict(text="Disk Used (%)", font=dict(color=_MUTED, size=13)),
            number=dict(suffix="%", font=dict(color=disk_color, size=22)),
            gauge=dict(
                axis=dict(range=[0, 100], tickfont=dict(color=_MUTED, size=10), tickcolor=_BORDER),
                bar=dict(color=disk_color, thickness=0.3),
                bgcolor=_BG_INNER,
                bordercolor=_BORDER,
                steps=[
                    dict(range=[0, 60],  color="#1B2A3A"),
                    dict(range=[60, 80], color="#2A2215"),
                    dict(range=[80, 100], color="#2A1515"),
                ],
            ),
        ))
        fig_disk.update_layout(height=220, **_BASE)
        st.plotly_chart(fig_disk, width='stretch')

    # ------------------------------------------------------------------
    # ROW 2 — Horizontal bar: disk breakdown  |  Context switches
    # ------------------------------------------------------------------
    col_b1, col_b2 = st.columns(2)

    with col_b1:
        st.markdown("**Disk space breakdown**")
        disk_used = sys_snap.get("disk_used_gb", 0)
        disk_free = sys_snap.get("disk_free_gb", 0)
        if disk_used or disk_free:
            fig_disk_bar = go.Figure(go.Bar(
                x=[disk_used, disk_free],
                y=["Disk", "Disk"],
                orientation="h",
                marker_color=[_RED if sys_snap.get("disk_pct", 0) > 80 else _AMBER, _GREEN],
                text=[f"{disk_used:.1f} GB used", f"{disk_free:.1f} GB free"],
                textposition="inside",
                textfont=dict(color="white", size=11),
                name="",
            ))
            fig_disk_bar.update_layout(
                height=140,
                barmode="stack",
                showlegend=False,
                xaxis=dict(
                    title="GB",
                    gridcolor=_BORDER,
                    tickfont=dict(color=_MUTED),
                ),
                yaxis=dict(showticklabels=False),
                **_BASE,
            )
            fig_disk_bar.update_layout(margin=dict(l=10, r=10, t=10, b=40))
            st.plotly_chart(fig_disk_bar, width='stretch')
        else:
            st.caption("Disk data not available.")

    with col_b2:
        st.markdown("**Process context switches**")
        ctx_vol   = proc_snap.get("ctx_voluntary",   None)
        ctx_invol = proc_snap.get("ctx_involuntary", None)
        if ctx_vol is not None and ctx_invol is not None:
            fig_ctx = go.Figure(go.Bar(
                x=["Voluntary", "Involuntary"],
                y=[ctx_vol, ctx_invol],
                marker_color=[_BLUE, _PURPLE],
                text=[f"{ctx_vol:,}", f"{ctx_invol:,}"],
                textposition="outside",
                textfont=dict(color=_TEXT, size=11),
            ))
            fig_ctx.update_layout(
                height=140,
                showlegend=False,
                xaxis=dict(tickfont=dict(color=_MUTED), gridcolor=_BORDER),
                yaxis=dict(tickfont=dict(color=_MUTED), gridcolor=_BORDER),
                **_BASE,
            )
            fig_ctx.update_layout(margin=dict(l=40, r=10, t=10, b=40))
            st.plotly_chart(fig_ctx, width='stretch')
        else:
            st.caption("Context switch data not available (Windows or psutil version).")

    # ------------------------------------------------------------------
    # ROW 3 — Load average bar (POSIX only)
    # ------------------------------------------------------------------
    load_1  = sys_snap.get("load_1m")
    load_5  = sys_snap.get("load_5m")
    load_15 = sys_snap.get("load_15m")

    if load_1 is not None:
        st.markdown("**System load average**")
        logical = sys_snap.get("cpu_logical", 1) or 1
        fig_load = go.Figure()
        fig_load.add_trace(go.Bar(
            x=["1 min", "5 min", "15 min"],
            y=[load_1, load_5, load_15],
            marker_color=[
                _RED if v > logical else (_AMBER if v > logical * 0.7 else _GREEN)
                for v in [load_1, load_5, load_15]
            ],
            text=[f"{v:.2f}" for v in [load_1, load_5, load_15]],
            textposition="outside",
            textfont=dict(color=_TEXT, size=12),
        ))
        # Horizontal reference line at cpu_count
        fig_load.add_hline(
            y=logical,
            line_dash="dot",
            line_color=_AMBER,
            annotation_text=f"CPU count ({logical})",
            annotation_font_color=_AMBER,
            annotation_font_size=11,
        )
        fig_load.update_layout(
            height=200,
            showlegend=False,
            xaxis=dict(tickfont=dict(color=_MUTED), gridcolor=_BORDER),
            yaxis=dict(tickfont=dict(color=_MUTED), gridcolor=_BORDER, title="Load"),
            **_BASE,
        )
        fig_load.update_layout(margin=dict(l=50, r=20, t=20, b=40))
        st.plotly_chart(fig_load, width='stretch')
        st.caption(
            f"Load averages above the CPU count ({logical} logical cores) "
            "indicate sustained saturation."
        )

    # ------------------------------------------------------------------
    # ROW 4 — Time-series: RSS and RAM% over manual captures
    # ------------------------------------------------------------------
    st.divider()
    st.markdown("**Time-series — manual captures**")

    col_cap1, col_cap2 = st.columns([2, 1])
    with col_cap1:
        st.caption(
            "Each click of the button below records one data point from the "
            "current process + system state. Up to 60 points are kept per session. "
            "Points are never collected automatically."
        )
    with col_cap2:
        if st.button(
            ":material/add_chart: Capture Snapshot",
            key="diag_capture_btn",
            help="Add one data point to the time-series charts.",
        ):
            _record_snapshot()
            st.success("Snapshot captured.")

    history = _get_historical_snapshots()

    if len(history) < 2:
        st.info(
            f"{'No snapshots yet.' if not history else '1 snapshot captured.'} "
            "Click 'Capture Snapshot' at least twice to see a time-series chart."
        )
    else:
        ts_labels  = [p["ts"]           for p in history]
        rss_series = [p["rss_mb"]       for p in history]
        ram_series = [p["ram_used_pct"] for p in history]
        dsk_series = [p["disk_used_pct"] for p in history]

        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(
            x=ts_labels, y=rss_series,
            mode="lines+markers",
            name="Process RSS (MB)",
            line=dict(color=_BLUE,  width=2),
            marker=dict(size=6),
        ))
        fig_ts.add_trace(go.Scatter(
            x=ts_labels, y=ram_series,
            mode="lines+markers",
            name="System RAM Used (%)",
            line=dict(color=_GREEN, width=2, dash="dash"),
            marker=dict(size=6),
            yaxis="y2",
        ))
        fig_ts.add_trace(go.Scatter(
            x=ts_labels, y=dsk_series,
            mode="lines+markers",
            name="Disk Used (%)",
            line=dict(color=_AMBER, width=2, dash="dot"),
            marker=dict(size=6),
            yaxis="y2",
        ))
        fig_ts.update_layout(
            height=280,
            xaxis=dict(
                title="Captured at",
                tickfont=dict(color=_MUTED, size=10),
                gridcolor=_BORDER,
            ),
            yaxis=dict(
                title=dict(
                    text="RSS (MB)",
                    font=dict(color=_BLUE)
                ),
                tickfont=dict(color=_BLUE, size=10),
                gridcolor=_BORDER,
            ),
            yaxis2=dict(
                title=dict(
                    text="% Used",
                    font=dict(color=_GREEN)
                ),
                overlaying="y",
                side="right",
                tickfont=dict(color=_GREEN, size=10),
            ),
            legend=dict(
                bgcolor=_BG,
                bordercolor=_BORDER,
                borderwidth=1,
                font=dict(color=_TEXT, size=11),
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
            ),
            **_BASE,
        )
        fig_ts.update_layout(margin=dict(l=60, r=60, t=50, b=50))
        st.plotly_chart(fig_ts, width='stretch')

        if st.button(
            ":material/delete: Clear capture history",
            key="diag_clear_history",
            help="Remove all manually captured snapshots from this session.",
        ):
            st.session_state["_diag_history"] = []
            st.rerun()

# << SYSTEM PLOTS BLOCK END >>


# -----------------------------------
# ADMIN PANEL
# -----------------------------------
def show_admin_panel(user_email):

    if not is_admin():
        st.error("Access denied.")
        return

    st.header(":material/admin_panel_settings: Admin")
    st.caption("System diagnostics and monitoring. All data is fetched on demand to minimise database reads.")
    st.divider()

    # ==============================
    # SYSTEM
    # ==============================
    st.subheader(":material/settings: System")
 
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
    deployment_label = _get_deployment_label()
    c1.metric("Deployment Platform", deployment_label)
    c2.metric("OS", os_info)
    c3.metric("Arch", _get_arch())
    c4.metric("Process ID", os.getpid())

    c6, c7, c8 = st.columns(3)
    c6.metric("Python", sys.version.split()[0])
    c7.metric("Streamlit", st.__version__)
    c8.metric("Scikit-learn", sklearn_version)

    c9, c10, c11 = st.columns(3)
    c9.metric("XGBoost", xgb_version)
    c10.metric("SpaCy", spacy_version)
    c11.metric("Pandas", pd_version)

    # ==============================
    # LOCAL DIAGNOSTICS
    # ==============================
    if _is_local():
        st.divider()
        st.subheader(":material/build: Local Diagnostics")
        st.caption(
            "Extended system diagnostics available because this instance is running locally. "
            "These sections are hidden on remote deployments to avoid exposing environment details."
        )

        # ---------- PROCESS METRICS ----------
        show_process = st.toggle(
            ":material/memory: Show Process Metrics",
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
                    # USS only available on Linux/macOS
                    if "uss_mb" in snap:
                        p3.metric(
                            "USS (Unique Set Size)",
                            f"{snap['uss_mb']:.1f} MB",
                            help="Memory not shared with any other process. More accurate than RSS.",
                        )
                    else:
                        p3.metric("USS (Unique Set Size)", "N/A (Windows)")

                    # Row 2: CPU — value is now real (primed with 0.15 s sleep in cache)
                    p4, p5, p6 = st.columns(3)
                    cpu_val = snap.get("cpu_pct", 0)
                    # Show "< 0.1%" if value rounds to zero but process is running
                    cpu_display = f"{cpu_val:.1f}%" if cpu_val >= 0.1 else "< 0.1%"
                    p4.metric(
                        "CPU Usage",
                        cpu_display,
                        help="Measured over a 0.15 s window inside the cached call.",
                    )
                    # Floor applied in snapshot — never shows "0.0 s"
                    p5.metric("CPU User Time",   f"{snap.get('cpu_user_s', '—')} s")
                    p6.metric("CPU System Time", f"{snap.get('cpu_sys_s',  '—')} s")

                    # Row 3: threads, file descriptors, context switches
                    p7, p8, p9 = st.columns(3)
                    p7.metric(
                        "Threads",
                        snap["threads"] if "threads" in snap else "—",
                    )
                    p8.metric(
                        "Open File Descriptors",
                        snap["open_fds"] if "open_fds" in snap else "N/A (Windows)",
                    )
                    ctx_vol   = snap.get("ctx_voluntary")
                    ctx_invol = snap.get("ctx_involuntary")
                    if ctx_vol is not None:
                        p9.metric(
                            "Context Switches",
                            f"{ctx_vol:,} vol / {ctx_invol:,} invol",
                            help="Voluntary (process yielded) vs involuntary (OS preempted).",
                        )
                    else:
                        p9.metric("Context Switches", "N/A")

                    # Row 4: uptime
                    p10, p11, _ = st.columns(3)
                    if "uptime_s" in snap:
                        uptime_s = int(snap["uptime_s"])
                        h, rem = divmod(uptime_s, 3600)
                        m, s   = divmod(rem, 60)
                        p10.metric("Process Uptime", f"{h}h {m}m {s}s")
                        p11.metric("Started At", snap.get("started_at", "—"))
                    else:
                        p10.metric("Process Uptime", "—")
                        p11.metric("Started At", "—")

        # ---------- SYSTEM RESOURCES ----------
        show_system = st.toggle(
            ":material/storage: Show System Resources",
            key="diag_system_toggle",
            value=False,
        )

        if show_system:
            with st.expander("System Resources", expanded=True):
                if st.button("Refresh System Resources", key="diag_sys_refresh"):
                    _get_system_snapshot.clear()

                ssnap = _get_system_snapshot()

                if not ssnap:
                    st.warning("psutil is not installed or system metrics are unavailable.")
                else:
                    st.caption("Cached for 60 seconds. Click Refresh to fetch immediately.")

                    # CPU
                    st.markdown("**CPU**")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Logical Cores",  ssnap.get("cpu_logical",  "—"))
                    sc2.metric("Physical Cores", ssnap.get("cpu_physical", "—"))
                    sc3.metric(
                        "Clock Speed",
                        f"{ssnap['cpu_freq_mhz']:.0f} MHz" if "cpu_freq_mhz" in ssnap else "—"
                    )

                    # Load average (POSIX only — not shown on Windows)
                    if "load_1m" in ssnap:
                        sl1, sl2, sl3 = st.columns(3)
                        sl1.metric("Load Avg (1 min)",  ssnap["load_1m"])
                        sl2.metric("Load Avg (5 min)",  ssnap["load_5m"])
                        sl3.metric("Load Avg (15 min)", ssnap["load_15m"])

                    # Boot time
                    if "boot_time" in ssnap:
                        st.caption(f"System boot time: {ssnap['boot_time']}")

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
                        sn1, sn2, sn3, sn4 = st.columns(4)
                        sn1.metric("Sent",          f"{ssnap['net_sent_mb']:.1f} MB")
                        sn2.metric("Received",      f"{ssnap['net_recv_mb']:.1f} MB")
                        sn3.metric("Packets Sent",  f"{ssnap.get('net_pkts_sent', '—'):,}"
                                   if isinstance(ssnap.get('net_pkts_sent'), int) else "—")
                        sn4.metric("Packets Recv",  f"{ssnap.get('net_pkts_recv', '—'):,}"
                                   if isinstance(ssnap.get('net_pkts_recv'), int) else "—")

        # ---------- SYSTEM PLOTS ----------
        # << SYSTEM PLOTS BLOCK START — remove toggle + inner block to roll back >>
        show_plots = st.toggle(
            ":material/monitoring: Show System Visualisations",
            key="diag_plots_toggle",
            value=False,
        )

        if show_plots:
            with st.expander("System Visualisations", expanded=True):
                # Reuse already-cached snapshots — no new psutil calls here
                _proc = _get_process_snapshot()
                _sys  = _get_system_snapshot()
                if not _proc and not _sys:
                    st.warning(
                        "psutil is not installed. "
                        "System visualisations require psutil."
                    )
                else:
                    _build_system_plots(_proc, _sys)
        # << SYSTEM PLOTS BLOCK END >>

        # ---------- PYTHON ENVIRONMENT ----------
        show_env = st.toggle(
            ":material/code: Show Python Environment",
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

                    st.markdown("**Interpreter**")
                    e1, e2 = st.columns(2)
                    e1.metric("Implementation", esnap.get("python_impl", "—"))
                    e2.metric("Default Encoding", esnap.get("encoding", "—"))

                    st.text(f"Full version: {esnap.get('python_full', '—')}")
                    st.text(f"Executable: {esnap.get('executable', '—')}")
                    st.text(f"Prefix: {esnap.get('prefix', '—')}")
                    st.text(f"Working dir: {esnap.get('cwd', '—')}")
                    st.text(f"Hostname: {esnap.get('node', '—')}")
                    st.text(f"Platform: {esnap.get('platform_full', '—')}")

                    st.markdown("**Runtime Limits**")
                    rl1, rl2 = st.columns(2)
                    rl1.metric("Recursion Limit", esnap.get("recursion_limit", "—"))
                    rl2.metric(
                        "Thread Stack",
                        f"{esnap['thread_stack_kb']} KB"
                        if "thread_stack_kb" in esnap else "—",
                    )

                    # File descriptor limit — shown always (useful and not trivial)
                    if "rlimit_fd_soft" in esnap:
                        st.markdown("**OS Resource Limits (POSIX)**")
                        st.metric(
                            "File Descriptors (soft / hard)",
                            f"{esnap['rlimit_fd_soft']} / {esnap['rlimit_fd_hard']}",
                            help="Maximum number of open file descriptors for this process.",
                        )
                    # Address space — only shown if actually constrained (not unlimited)
                    if "rlimit_as_soft" in esnap:
                        st.metric(
                            "Address Space (soft / hard)",
                            f"{esnap['rlimit_as_soft']} / {esnap['rlimit_as_hard']}",
                        )
                    # CPU time — only shown if actually constrained (not unlimited)
                    if "rlimit_cpu_soft" in esnap:
                        st.metric(
                            "CPU Time limit (soft / hard)",
                            f"{esnap['rlimit_cpu_soft']} / {esnap['rlimit_cpu_hard']}",
                        )

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
                                width='stretch',
                                hide_index=True,
                            )
                        else:
                            st.caption("No relevant environment variables detected.")

        # ---------- INSTALLED PACKAGES ----------
        show_pkgs = st.toggle(
            ":material/inventory_2: Show Installed Packages",
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
                    missing   = df_pkgs[df_pkgs["status"] != "installed"]
                    installed = df_pkgs[df_pkgs["status"] == "installed"]

                    st.dataframe(installed, width='stretch', hide_index=True)

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
    st.subheader(":material/cloud: Firebase")

    try:
        project_id = st.secrets["FIREBASE_SERVICE_ACCOUNT"]["project_id"]
    except:
        project_id = "Not set"

    api_key_status     = "Available" if "FIREBASE_API_KEY"          in st.secrets else "Missing"
    service_acc_status = "Available" if "FIREBASE_SERVICE_ACCOUNT"  in st.secrets else "Missing"

    c1, c2, c3 = st.columns(3)
    c1.metric("Project ID",      project_id)
    c2.metric("API Key",         api_key_status)
    c3.metric("Service Account", service_acc_status)

    firebase_url = st.secrets.get("FIREBASE_CONSOLE_URL")
    if firebase_url:
        st.markdown(f"[Open Firebase Console]({firebase_url})")

    st.divider()

    # ==============================
    # USERS
    # ==============================
    st.subheader(":material/group: Users")

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
    st.subheader(":material/analytics: Feedback Analytics")

    if st.button("Load Feedback Analytics", key="feedback_btn"):
        with st.spinner("Loading feedback data..."):
            stats = _get_feedback_stats()
        st.session_state["feedback_stats"] = stats

    if "feedback_stats" in st.session_state and st.session_state["feedback_stats"]:
        stats = st.session_state["feedback_stats"]

        with st.expander("View Feedback Analytics", expanded=True):

            @st.fragment
            def render_feedback_dashboard():

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Feedback",   stats["total"])
                k2.metric("Accuracy",         f"{stats['pct_positive']}%",
                          help="Percentage of 'Yes' responses")
                k3.metric("Average Rating",   stats["avg_star"])

                if stats["median_actual"] is not None:
                    k4.metric("Median Actual Salary", f"${stats['median_actual']:,.0f}")
                else:
                    k4.metric("Median Actual Salary", "N/A")

                st.markdown("#### Breakdown")

                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Yes",      f"{stats['pct_positive']}%")
                b2.metric("Somewhat", f"{stats['pct_somewhat']}%")
                b3.metric("No",       f"{stats['pct_no']}%")
                b4.metric("Actual Salary Coverage", f"{stats['pct_actual_salary']}%",
                          help="Users who reported actual salary")

                st.divider()
                left, right = st.columns([1, 1])

                with left:
                    st.markdown("#### Feedback Accuracy Distribution")
                    if stats["total"] > 0:
                        import plotly.graph_objects as go
                        fig_acc = go.Figure(data=[go.Pie(
                            labels=["Yes", "Somewhat", "No"],
                            values=[stats["yes"], stats["somewhat"], stats["no"]],
                            hole=0.4,
                            marker=dict(colors=["#4F8EF7", "#38BDF8", "#F59E0B"]),
                            textinfo="label+percent",
                            textposition="inside",
                            textfont=dict(color="white"),
                        )])
                        fig_acc.update_layout(
                            height=350,
                            paper_bgcolor="#141A22",
                            plot_bgcolor="#1B2230",
                            font=dict(color="#E6EAF0"),
                            showlegend=False,
                            margin=dict(l=10, r=10, t=30, b=10),
                        )
                        st.plotly_chart(fig_acc, width='stretch')

                with right:
                    st.markdown("#### Prediction Direction")
                    dir_total = stats["too_high"] + stats["about_right"] + stats["too_low"]
                    if dir_total > 0:
                        import plotly.graph_objects as go
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
                            margin=dict(l=10, r=10, t=30, b=10),
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
                    fig_mc.update_traces(
                        textposition="outside",
                        textfont=dict(color="white"),
                    )
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
    # RECENT ACTIVITY
    # ==============================
    st.subheader(":material/history: Recent Activity")

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
                    st.write("Star Rating:  ", f"{'★' * int(star) if isinstance(star, (int, float)) else star}")
                    st.write("Accuracy:     ", accuracy)
                    st.write("Direction:    ", direction)
                    if isinstance(salary, (int, float)):
                        st.write("Predicted Salary: ", f"${salary:,.2f}")
                    actual = item.get("actual_salary")
                    if isinstance(actual, (int, float)) and actual > 0:
                        st.write("Reported Actual Salary: ", f"${actual:,.2f}")

    st.divider()

    # ==============================
    # MEMORY & CACHE
    # ==============================
    st.subheader(":material/memory: Memory & Cache")

    mem = _mem_mb()

    col1, col2 = st.columns([3, 1])

    if mem >= 0:
        col1.metric("RAM Usage", f"{mem:.1f} MB")
    else:
        col1.caption("psutil not installed")

    if col2.button("Run Garbage Collection", key="run_gc_btn",
                   help="Force Python garbage collection"):
        before    = mem
        collected = gc.collect()
        after     = _mem_mb()
        st.success(f"Collected {collected} objects")
        st.caption(f"{before:.1f} → {after:.1f} MB")

    if col2.button("Clear Cache", key="clr_cache_btn",
                   help="Clear all @st.cache_data caches"):
        st.cache_data.clear()
        st.success("Cache cleared")

    # ==============================
    # SESSION
    # ==============================
    st.divider()
    st.subheader(":material/key: Session State")
    with st.expander("Session Keys & State Info"):

        total_keys = len(st.session_state)
        st.metric("Total Session Keys", total_keys)

        admin_keys    = [k for k in st.session_state if k.startswith("admin") or k == "is_admin"]
        scenario_keys = [k for k in st.session_state if k.startswith("sc_") or "scenario" in k.lower()]
        bulk_keys     = [k for k in st.session_state if k.startswith("bulk_")]
        resume_keys   = [k for k in st.session_state if k.startswith("resume_")]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Admin Keys",    len(admin_keys))
        c2.metric("Scenario Keys", len(scenario_keys))
        c3.metric("Bulk Keys",     len(bulk_keys))
        c4.metric("Resume Keys",   len(resume_keys))

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
        datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    )