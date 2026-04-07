import streamlit as st
import sys
import platform
import datetime
import gc
from auth import is_admin
from database import _get_firestore_client

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
        pd_version = "Not available" 

    os_info = _get_os_info()

    c1, c2, c3 = st.columns(3)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("OS", os_info)
    c3.metric("Arch", _get_arch())

    c4, c5, c6 = st.columns(3)
    c4.metric("Streamlit", st.__version__)
    c5.metric("Scikit-learn", sklearn_version)
    c6.metric("XGBoost", xgb_version)

    c7, c8, _ = st.columns(3)
    c7.metric("SpaCy", spacy_version)
    c8.metric("Pandas", pd_version)
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
                k3.metric("Avg Rating", stats["avg_star"])

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
        admin_keys    = [k for k in st.session_state if "admin" in k.lower()]
        scenario_keys = [k for k in st.session_state if "scenario" in k.lower()]
        bulk_keys     = [k for k in st.session_state if "bulk" in k.lower()]
        resume_keys   = [k for k in st.session_state if "resume" in k.lower()]

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