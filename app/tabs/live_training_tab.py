"""
live_training_tab.py
====================
The "Live Model" tab for SalaryScope.

This tab has two independent panels:

  Panel A -- Training (admin + local only, guarded by is_local())
    Step 1: Configure search parameters (domains, countries)
    Step 2: Fetch data from Adzuna API (real live salary listings)
    Step 3: Clean and audit data
    Step 4: Train GradientBoostingRegressor
    Step 5: Upload to HuggingFace Hub
    Step 6: Rollback manager

  Panel B -- Prediction (all logged-in users, local + cloud)
    Loads the current model from HuggingFace.
    Input form with full feature set (experience, education, title, size,
    location, work mode, contract type).
    Output: predicted salary + 80% interval + model provenance card.

IMPORTANT NOTICE TO USERS
--------------------------
This is an EXPERIMENTAL feature. The live model is trained on Adzuna job
listing salary data, which has several known limitations:
  - Salary ranges from job postings are not verified actual compensation.
  - The training dataset size is modest (hundreds to low thousands of records).
  - Some features (company size, education) cannot be inferred from Adzuna.
  - Cross-currency normalisation introduces approximation error.
  - Model performance (R2, MAE) will typically be LOWER than the main
    historical-data models (Model 1 and Model 2).

Users requiring accurate salary estimates should prefer Model 1 (Random
Forest) or Model 2 (XGBoost), both trained on a curated historical dataset
that is significantly larger and more feature-rich than the Adzuna live feed.

Quota safety
------------
The Adzuna free tier allows 250 requests per day. Fetching is capped at 25%
(62 requests per session) to preserve quota across multiple training runs.
Override with ADZUNA_MAX_REQUESTS_OVERRIDE in secrets.

Rollback
--------
EXTERNAL (persistent): each upload is versioned on HuggingFace. Rollback
  Manager lets the admin promote any version to current.
INTERNAL (session-only): Discard button clears session artefact before upload.
COMPLETE REMOVAL: remove the import in app_resume.py.

is_local() convention
---------------------
Training Panel A is shown only when _is_local() returns True. On Streamlit
Cloud, admins see a read-only status card instead.

No unicode outside string literals. Icons use :material/icon_name: syntax only.
"""

from __future__ import annotations

import os
import streamlit as st

from app.core.auth import is_admin
from app.utils.live_training_datasource import (
    fetch_adzuna_salary_records,
    get_fetch_quality_summary,
    is_adzuna_configured,
    SUPPORTED_COUNTRIES,
    DOMAIN_TITLES,
    DEFAULT_DOMAINS,
    DEFAULT_SESSION_MAX_REQS,
    FREE_TIER_DAILY_LIMIT,
    QUOTA_SAFETY_FRACTION,
)
from app.utils.live_training_cleaner import (
    clean_adzuna_records,
    MIN_RECORDS_FOR_TRAINING,
)
from app.utils.live_model_trainer import (
    train_live_model,
    serialise_artefact,
)
from app.utils.live_model_storage import (
    is_storage_configured,
    upload_model,
    download_current_model,
    get_ledger,
    rollback_to_version,
)
from app.utils.live_model_predictor import (
    load_live_model_from_bytes,
    predict_salary,
    EXPERIENCE_DISPLAY,
    EXPERIENCE_NUM_MAP,
    _DEFAULT_CATEGORY,
)

# ---------------------------------------------------------------------------
# IS_LOCAL DETECTION (mirrors admin_panel.py exactly)
# ---------------------------------------------------------------------------

def _is_local() -> bool:
    try:
        val = st.secrets.get("IS_LOCAL", None)
        if val is not None:
            return bool(val)
    except Exception:
        pass
    try:
        if os.environ.get("STREAMLIT_SHARING_MODE"):
            return False
        home = os.environ.get("HOME", "")
        cwd  = os.getcwd()
        if home in ("/home/appuser", "/app") or cwd.startswith("/app"):
            return False
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# SESSION STATE KEYS -- prefixed "lt_" to avoid clashes with existing keys
# ---------------------------------------------------------------------------

_K_RAW       = "lt_raw_records"
_K_FETCH_RPT = "lt_fetch_report"
_K_CLEAN_DF  = "lt_clean_df"
_K_AUDIT     = "lt_clean_audit"
_K_ART       = "lt_artefact"
_K_ART_BYTES = "lt_artefact_bytes"
_K_REPORT    = "lt_train_report"
_K_UPLOADED  = "lt_upload_done"
_K_LIVE_ART  = "lt_live_artefact"
_K_LIVE_BYTES= "lt_live_bytes"
_K_PRED      = "lt_prediction"
_K_LEDGER    = "lt_ledger"


def _init_state() -> None:
    defaults: dict = {
        _K_RAW:       None,
        _K_FETCH_RPT: None,
        _K_CLEAN_DF:  None,
        _K_AUDIT:     None,
        _K_ART:       None,
        _K_ART_BYTES: None,
        _K_REPORT:    None,
        _K_UPLOADED:  False,
        _K_LIVE_ART:  None,
        _K_LIVE_BYTES:None,
        _K_PRED:      None,
        _K_LEDGER:    None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# DISPLAY MAPS
# ---------------------------------------------------------------------------

_EXP_LABELS  = list(EXPERIENCE_DISPLAY.values())
_EXP_REV     = {v: k for k, v in EXPERIENCE_DISPLAY.items()}

_CS_DISPLAY  = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}
_CS_REV      = {v: k for k, v in _CS_DISPLAY.items()}

_REM_DISPLAY = {0: "On-site", 50: "Hybrid", 100: "Fully Remote"}
_REM_REV     = {v: k for k, v in _REM_DISPLAY.items()}

_EDU_DISPLAY = {
    0: "High School",
    1: "Bachelor's Degree",
    2: "Master's Degree",
    3: "PhD",
}

_CONTRACT_DISPLAY = {0: "Permanent / Full-time", 1: "Contract / Freelance / Temp"}


# ---------------------------------------------------------------------------
# SMALL UI HELPERS
# ---------------------------------------------------------------------------

def _badge(ok: bool, ok_text: str = "OK", fail_text: str = "Issue") -> str:
    color = "#22C55E" if ok else "#EF4444"
    text  = ok_text if ok else fail_text
    return (
        f"<span style='background:{color};color:#fff;font-size:11px;"
        f"font-weight:600;padding:2px 8px;border-radius:4px;'>{text}</span>"
    )


def _salary_card(label: str, value: str, color: str = "#4F8EF7") -> None:
    st.markdown(
        f"""
        <div style='
            background:linear-gradient(135deg,#1B2A45 0%,#1B2230 100%);
            border:1px solid #283142;border-left:5px solid {color};
            border-radius:10px;padding:24px 32px;text-align:center;margin:8px auto;
        '>
            <div style='color:#9CA6B5;font-size:13px;font-weight:600;
                        letter-spacing:.5px;margin-bottom:8px;'>{label}</div>
            <div style='color:{color};font-size:42px;font-weight:700;
                        letter-spacing:-1px;'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _experimental_warning_banner() -> None:
    st.warning(
        "**Experimental Feature** -- This live model is trained on Adzuna job "
        "posting data and is provided for exploratory use only. Prediction "
        "accuracy is expected to be lower than the main models. For reliable "
        "salary estimates, use **Model 1 (Random Forest)** or **Model 2 (XGBoost)** "
        "which are trained on a larger, curated historical dataset.",
        icon=":material/science:",
    )


# ===========================================================================
# PANEL A -- LIVE TRAINING
# ===========================================================================

def _render_training_panel() -> None:
    st.subheader(":material/model_training: Live Model Training")
    st.caption(
        "Fetch real salary data from the Adzuna Jobs API, train a "
        "GradientBoostingRegressor, and upload it to HuggingFace Hub "
        "so cloud users can make predictions. "
        f"Quota guard: fetching stops at {QUOTA_SAFETY_FRACTION:.0%} of the "
        f"{FREE_TIER_DAILY_LIMIT}/day Adzuna free tier "
        f"({DEFAULT_SESSION_MAX_REQS} requests per session by default)."
    )

    if not is_adzuna_configured():
        st.error(
            "Adzuna API credentials not found. "
            "Add ADZUNA_APP_ID and ADZUNA_APP_KEY to .streamlit/secrets.toml. "
            "Register free at https://developer.adzuna.com"
        )
        return

    # -----------------------------------------------------------------------
    # STEP 1 -- Configure search
    # -----------------------------------------------------------------------
    st.markdown("#### :material/search: Step 1 -- Configure Data Fetch")

    with st.expander("Search parameters", expanded=True):
        # Domain-based selection replaces the raw text area of titles
        st.markdown("**Select job domains to include**")
        st.caption(
            "Each domain contributes a curated set of generic search terms. "
            "Selecting more domains increases coverage and training data volume "
            "but uses more API quota. A multi-domain dataset produces a more "
            "general-purpose model."
        )
        all_domain_names = list(DOMAIN_TITLES.keys())
        selected_domains = st.multiselect(
            "Job domains",
            options=all_domain_names,
            default=DEFAULT_DOMAINS,
            key="lt_domains_input",
        )

        # Optional: let admin see and fine-tune the titles for selected domains
        derived_titles: list[str] = []
        for d in selected_domains:
            derived_titles.extend(DOMAIN_TITLES.get(d, []))
        derived_titles = list(dict.fromkeys(derived_titles))  # preserve order, dedup

        with st.expander(
            f"Preview search terms ({len(derived_titles)} titles from selected domains)",
            expanded=False,
        ):
            raw_titles_override = st.text_area(
                "Edit titles if needed (one per line)",
                value="\n".join(derived_titles),
                height=220,
                key="lt_titles_override",
                help=(
                    "These are derived from the selected domains above. "
                    "You can remove or add terms before fetching. "
                    "Keep terms concise -- Adzuna uses partial keyword matching."
                ),
            )
        if raw_titles_override.strip():
            job_titles = [t.strip() for t in raw_titles_override.splitlines() if t.strip()]
        else:
            job_titles = derived_titles

        st.divider()

        country_opts = {v: k for k, v in SUPPORTED_COUNTRIES.items()}
        default_country_names = [
            SUPPORTED_COUNTRIES[c]
            for c in ["us", "gb", "ca", "au", "in", "de"]
            if c in SUPPORTED_COUNTRIES
        ]
        selected_country_names = st.multiselect(
            "Countries to include",
            options=list(country_opts.keys()),
            default=default_country_names,
            key="lt_countries_input",
        )
        countries = [country_opts[n] for n in selected_country_names]

        max_records = st.slider(
            "Maximum records to collect",
            min_value=200,
            max_value=5000,
            value=2000,
            step=100,
            key="lt_max_records",
            help=(
                "Each page = 1 API request (50 results/page). "
                f"Default quota cap: {DEFAULT_SESSION_MAX_REQS} requests/session "
                f"({QUOTA_SAFETY_FRACTION:.0%} of {FREE_TIER_DAILY_LIMIT}/day). "
                "With that cap you can collect roughly 1500-2500 salary records "
                "per session depending on listing coverage. "
                "Model performance improves significantly above 500 records. "
                "Training on fewer than 200 records will produce unreliable results."
            ),
        )

        # Show how many requests the current config will likely require
        estimated_reqs = min(len(job_titles) * len(countries) * 3, max_records // 25 + 1)
        quota_est_pct  = (estimated_reqs / FREE_TIER_DAILY_LIMIT) * 100
        st.caption(
            f"Estimated API requests for this config: ~{estimated_reqs} "
            f"({quota_est_pct:.0f}% of daily free quota). "
            f"Hard stop at {DEFAULT_SESSION_MAX_REQS} requests per session."
        )

    if not job_titles:
        st.warning("Select at least one domain (or add titles manually).")
        return
    if not countries:
        st.warning("Select at least one country.")
        return

    st.divider()

    # -----------------------------------------------------------------------
    # STEP 2 -- Fetch data
    # -----------------------------------------------------------------------
    st.markdown("#### :material/download: Step 2 -- Fetch from Adzuna API")
    st.caption(
        f"Will search {len(job_titles)} title(s) x {len(countries)} country/ies. "
        "Results are cached for 1 hour; use Refresh to force a new fetch."
    )

    col_btn, col_refresh = st.columns([3, 1])
    with col_btn:
        fetch_clicked = st.button(
            ":material/cloud_download: Fetch Salary Data",
            key="lt_fetch_btn",
            type="primary",
        )
    with col_refresh:
        st.write("")
        if st.button(":material/refresh: Refresh Cache", key="lt_refresh_cache"):
            fetch_adzuna_salary_records.clear()
            for k in (_K_RAW, _K_FETCH_RPT, _K_CLEAN_DF, _K_AUDIT, _K_ART, _K_REPORT):
                st.session_state[k] = None
            st.rerun()

    if fetch_clicked:
        with st.spinner("Fetching from Adzuna API... (may take 30-120 seconds)"):
            records, fetch_rpt = fetch_adzuna_salary_records(
                job_titles=job_titles,
                countries=countries,
                max_records=max_records,
            )
        st.session_state[_K_RAW]       = records
        st.session_state[_K_FETCH_RPT] = fetch_rpt
        st.session_state[_K_CLEAN_DF]  = None
        st.session_state[_K_AUDIT]     = None
        st.session_state[_K_ART]       = None
        st.session_state[_K_REPORT]    = None
        st.session_state[_K_UPLOADED]  = False

    raw_records = st.session_state.get(_K_RAW)
    fetch_rpt   = st.session_state.get(_K_FETCH_RPT)

    if fetch_rpt is not None:
        ok_badge = _badge(fetch_rpt["ok"], "Data Retrieved", "Fetch Failed")
        st.markdown(
            f"**Fetch Result:** {ok_badge} -- {fetch_rpt['reason']}",
            unsafe_allow_html=True,
        )

        quota_pct = fetch_rpt.get("quota_used_pct", 0.0)
        if fetch_rpt.get("quota_stopped"):
            st.warning(
                f"Session request cap reached ({DEFAULT_SESSION_MAX_REQS} requests, "
                f"{quota_pct:.1f}% of daily free quota used). "
                "The fetch was stopped early. To collect more records, "
                "set ADZUNA_MAX_REQUESTS_OVERRIDE in secrets or run again tomorrow."
            )
        else:
            st.caption(
                f"API quota used this session: {fetch_rpt.get('requests_made', 0)} requests "
                f"({quota_pct:.1f}% of {FREE_TIER_DAILY_LIMIT}/day free tier)."
            )

        if fetch_rpt.get("warnings"):
            with st.expander(
                f"{len(fetch_rpt['warnings'])} fetch warning(s)", expanded=False
            ):
                for w in fetch_rpt["warnings"][:30]:
                    st.caption(w)

        if raw_records:
            qs = get_fetch_quality_summary(raw_records)
            fc1, fc2, fc3, fc4 = st.columns(4)
            fc1.metric("Total Listings", qs["total"])
            fc2.metric("Countries",      len(qs["countries"]))
            fc3.metric("Salary Median",  f"${qs['salary_median']:,.0f}")
            fc4.metric("Salary Range",
                       f"${qs['salary_min']:,.0f} - ${qs['salary_max']:,.0f}")
            if qs.get("categories"):
                st.caption(
                    "Adzuna categories found: "
                    + ", ".join(sorted(qs["categories"])[:12])
                    + ("..." if len(qs["categories"]) > 12 else "")
                )
    else:
        st.info("Configure search parameters and click 'Fetch Salary Data'.")

    st.divider()

    # -----------------------------------------------------------------------
    # STEP 3 -- Clean and audit
    # -----------------------------------------------------------------------
    st.markdown("#### :material/cleaning_services: Step 3 -- Clean and Audit Data")
    st.caption(
        "The cleaner normalises raw Adzuna titles to canonical names "
        "(e.g. 'Senior Data Scientist III at Acme Ltd' -> 'Data Scientist'), "
        "infers experience level and remote ratio from title keywords, "
        "removes duplicates and salary outliers, and drops records with no "
        "matching canonical title rule."
    )

    if not raw_records:
        st.caption("Fetch data first.")
    else:
        if st.button(":material/check_circle: Run Data Cleaner", key="lt_clean_btn"):
            with st.spinner("Cleaning records..."):
                df_clean, audit = clean_adzuna_records(raw_records)
            st.session_state[_K_CLEAN_DF] = df_clean
            st.session_state[_K_AUDIT]    = audit
            st.session_state[_K_ART]      = None
            st.session_state[_K_REPORT]   = None

    audit    = st.session_state.get(_K_AUDIT)
    df_clean = st.session_state.get(_K_CLEAN_DF)

    if audit is not None:
        ok_badge = _badge(audit["ok"], "Ready to Train", "Not Enough Data")
        st.markdown(
            f"**Cleaning Result:** {ok_badge} -- {audit['reason']}",
            unsafe_allow_html=True,
        )
        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("Total Raw",     audit["total_raw"])
        ac2.metric("Clean Records", audit["total_clean"])
        ac3.metric("Dropped",       audit["dropped"])
        ac4.metric("Drop Rate",     f"{audit['drop_rate']:.0%}")

        ss = audit.get("salary_stats", {})
        if ss:
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Min",    f"${ss['min']:,.0f}")
            sc2.metric("Max",    f"${ss['max']:,.0f}")
            sc3.metric("Median", f"${ss['median']:,.0f}")
            sc4.metric("StdDev", f"${ss['std']:,.0f}")

        if audit["warnings"]:
            with st.expander(
                f":material/warning: {len(audit['warnings'])} cleaning warning(s)",
                expanded=False,
            ):
                for w in audit["warnings"][:50]:
                    st.caption(w)

        if df_clean is not None and not df_clean.empty:
            with st.expander(":material/table_chart: Preview cleaned data", expanded=False):
                st.dataframe(df_clean.head(30), use_container_width=True, hide_index=True)

            if "job_title" in df_clean.columns:
                with st.expander(":material/bar_chart: Title distribution (top 20)", expanded=False):
                    top_titles = (
                        df_clean["job_title"]
                        .value_counts()
                        .head(20)
                        .reset_index()
                        .rename(columns={"count": "Count", "job_title": "Canonical Title"})
                    )
                    st.dataframe(top_titles, use_container_width=True, hide_index=True)
    else:
        st.caption("Run the cleaner to inspect data quality before training.")

    st.divider()

    # -----------------------------------------------------------------------
    # STEP 4 -- Train
    # -----------------------------------------------------------------------
    st.markdown("#### :material/smart_toy: Step 4 -- Train Model")

    if df_clean is None or df_clean.empty:
        st.caption("Clean data first.")
    elif not (audit or {}).get("ok"):
        st.warning((audit or {}).get("reason", "Not enough clean records to train."))
    else:
        folds = min(5, max(3, len(df_clean) // 50))
        st.info(
            f"Ready to train on {len(df_clean)} clean records "
            f"with {folds}-fold cross-validation. "
            f"Feature set: {len(st.session_state.get(_K_CLEAN_DF).columns) - 1} "  # type: ignore
            f"input features + salary target."
        )
        st.caption(
            "Training time varies by dataset size: typically 30-120 seconds "
            "for 500-3000 records on a modern CPU."
        )
        if st.button(
            ":material/play_arrow: Train Model Now",
            key="lt_train_btn",
            type="primary",
        ):
            prev_bytes = st.session_state.get(_K_LIVE_BYTES)
            with st.spinner("Training... (30-120 seconds depending on data size)"):
                artefact, report = train_live_model(
                    df_clean, previous_model_bytes=prev_bytes
                )
            st.session_state[_K_ART]       = artefact
            st.session_state[_K_REPORT]    = report
            st.session_state[_K_ART_BYTES] = (
                serialise_artefact(artefact) if artefact else None
            )
            st.session_state[_K_UPLOADED]  = False

    report   = st.session_state.get(_K_REPORT)
    artefact = st.session_state.get(_K_ART)

    if report is not None:
        ok_badge = _badge(report["ok"], "Training OK", "Training Failed")
        st.markdown(
            f"**Training Result:** {ok_badge} -- {report['reason']}",
            unsafe_allow_html=True,
        )
        if report["ok"] and report.get("details"):
            d = report["details"]
            tr1, tr2, tr3 = st.columns(3)
            tr1.metric("CV R2 (mean)", f"{d['cv_r2_mean']:.4f}")
            tr2.metric("CV R2 (std)",  f"{d['cv_r2_std']:.4f}")
            tr3.metric("CV MAE",       f"${d['cv_mae_mean']:,.0f}")
            tr4, tr5, tr6 = st.columns(3)
            tr4.metric("Test R2",   f"{d['test_r2']:.4f}")
            tr5.metric("Test MAE",  f"${d['test_mae']:,.0f}")
            tr6.metric("Test RMSE", f"${d['test_rmse']:,.0f}")
            st.caption(
                "Adzuna salary data reflects posted salary ranges, not verified "
                "compensation. R2 of 0.30-0.55 is typical for cross-country "
                "salary regression on posting data with inferred features. "
                "An R2 below 0.30 or a Test MAE above $30,000 indicates "
                "insufficient or poorly distributed training data -- consider "
                "adding more domains or countries and retraining."
            )

    st.divider()

    # -----------------------------------------------------------------------
    # STEP 5 -- Upload to HuggingFace
    # -----------------------------------------------------------------------
    st.markdown("#### :material/cloud_upload: Step 5 -- Upload to HuggingFace Hub")

    if not is_storage_configured():
        st.error(
            "HuggingFace storage not configured. "
            "Add HF_TOKEN and HF_REPO to .streamlit/secrets.toml."
        )
    elif artefact is None:
        st.caption("Train a model first.")
    elif st.session_state.get(_K_UPLOADED):
        st.success("Model uploaded in this session. Train a new one or use rollback.")
    else:
        meta    = artefact.get("metadata", {})
        version = meta.get("version", "unknown")
        st.write(
            f"Version: **{version}** | "
            f"Samples: **{meta.get('n_samples', '?')}** | "
            f"Test R2: **{meta.get('test_r2', 0):.4f}** | "
            f"Test MAE: **${meta.get('test_mae', 0):,.0f}**"
        )

        col_up, col_disc = st.columns(2)

        with col_up:
            if st.button(
                ":material/upload: Upload to HuggingFace Hub",
                key="lt_upload_btn",
                type="primary",
            ):
                art_bytes = st.session_state.get(_K_ART_BYTES)
                with st.spinner("Uploading..."):
                    fname, err = upload_model(art_bytes, version, meta)
                if err:
                    st.error(f"Upload failed: {err}")
                else:
                    st.success(f"Uploaded as {fname}. Now available for prediction.")
                    st.session_state[_K_UPLOADED] = True
                    st.session_state[_K_LEDGER]   = None

        with col_disc:
            if st.button(
                ":material/undo: Discard (internal rollback)",
                key="lt_discard_btn",
                help="Discard this training result without touching HuggingFace.",
            ):
                for k in (_K_ART, _K_ART_BYTES, _K_REPORT):
                    st.session_state[k] = None
                st.rerun()

    st.divider()

    # -----------------------------------------------------------------------
    # STEP 6 -- Rollback manager
    # -----------------------------------------------------------------------
    st.markdown("#### :material/history: Step 6 -- Rollback Manager")
    st.caption(
        "Every uploaded model is kept permanently on HuggingFace. "
        "Promote any previous version to current with one click."
    )

    if not is_storage_configured():
        st.caption("Configure HuggingFace storage to use rollback.")
        return

    col_rbl, col_ref = st.columns([4, 1])
    with col_ref:
        if st.button(":material/refresh: Refresh", key="lt_ledger_refresh"):
            st.session_state[_K_LEDGER] = None

    if st.session_state.get(_K_LEDGER) is None:
        with st.spinner("Loading version history..."):
            ledger, err = get_ledger()
        if err:
            st.error(f"Could not load ledger: {err}")
            ledger = []
        st.session_state[_K_LEDGER] = ledger

    ledger = st.session_state.get(_K_LEDGER, [])

    if not ledger:
        st.info("No version history yet. Upload a model to start.")
        return

    for entry in reversed(ledger):
        is_cur = entry.get("is_current", False)
        label  = f"{entry.get('version', '?')}{'  [CURRENT]' if is_cur else ''}"
        with st.expander(label, expanded=is_cur):
            le1, le2, le3, le4 = st.columns(4)
            le1.metric("Samples",    entry.get("n_samples", "-"))
            le2.metric("Test R2",    f"{entry.get('test_r2', 0):.4f}")
            le3.metric("Test MAE",   f"${entry.get('test_mae', 0):,.0f}")
            le4.metric("Trained At", str(entry.get("trained_at", "-"))[:19])

            if not is_cur:
                rb_key = f"lt_rb_{entry.get('version', 'x')}"
                if st.button(
                    f":material/restore: Rollback to {entry.get('version')}",
                    key=rb_key,
                ):
                    fname = entry.get("filename", "")
                    with st.spinner(f"Rolling back to {fname}..."):
                        ok, msg = rollback_to_version(fname)
                    if ok:
                        st.success(msg)
                        st.session_state[_K_LIVE_ART]  = None
                        st.session_state[_K_LIVE_BYTES] = None
                        st.session_state[_K_LEDGER]     = None
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.caption("This version is currently active.")


def _render_cloud_status() -> None:
    """Read-only training status shown to admins on Streamlit Cloud."""
    st.subheader(":material/cloud: Live Training Status (Cloud)")
    st.info(
        "Live training is available only on the local development instance. "
        "On Streamlit Cloud, train locally and upload to HuggingFace Hub. "
        "The prediction panel below serves the latest uploaded model automatically."
    )
    if not is_storage_configured():
        st.caption("HuggingFace storage not configured (HF_TOKEN / HF_REPO missing).")
        return
    with st.spinner("Loading version history..."):
        ledger, err = get_ledger()
    if err:
        st.warning(f"Could not load version history: {err}")
        return
    if not ledger:
        st.caption("No model uploaded yet.")
        return
    current = next((e for e in reversed(ledger) if e.get("is_current")), None)
    if current:
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("Active Version", current.get("version", "-"))
        cc2.metric("Trained On",     f"{current.get('n_samples', '-')} samples")
        cc3.metric("Test R2",        f"{current.get('test_r2', 0):.4f}")
        cc4.metric("Test MAE",       f"${current.get('test_mae', 0):,.0f}")


# ===========================================================================
# PANEL B -- PREDICTION
# ===========================================================================

def _render_prediction_panel() -> None:
    st.subheader(":material/insights: Live Model Prediction")

    _experimental_warning_banner()

    st.caption(
        "Predict salary using the community-trained GradientBoosting model, "
        "built from real Adzuna job listing data. "
        "This model is **experimental** and is expected to have lower accuracy "
        "than Model 1 and Model 2, which are trained on larger historical "
        "compensation datasets. Treat results as rough directional estimates only."
    )

    if not is_storage_configured():
        st.warning(
            "Prediction requires HF_TOKEN and HF_REPO in secrets. "
            "Configure HuggingFace storage to enable this panel."
        )
        return

    live_artefact = st.session_state.get(_K_LIVE_ART)
    meta          = (live_artefact or {}).get("metadata", {})

    col_load, col_info = st.columns([2, 2])
    with col_load:
        if st.button(
            ":material/download: Load / Refresh Live Model",
            key="lt_load_btn",
        ):
            with st.spinner("Downloading from HuggingFace..."):
                model_bytes, err = download_current_model()
            if err:
                st.error(f"Could not load live model: {err}")
            else:
                artefact, load_err = load_live_model_from_bytes(model_bytes)
                if load_err:
                    st.error(f"Deserialisation failed: {load_err}")
                else:
                    st.session_state[_K_LIVE_ART]  = artefact
                    st.session_state[_K_LIVE_BYTES] = model_bytes
                    st.session_state[_K_PRED]       = None
                    st.rerun()

    if live_artefact is None:
        st.info(
            "Click 'Load Live Model' to download the latest model from HuggingFace. "
            "Once loaded, it stays cached for this session."
        )
        return

    with col_info:
        test_r2 = meta.get("test_r2", 0)
        r2_color = "#EF4444" if test_r2 < 0.3 else ("#F59E0B" if test_r2 < 0.5 else "#22C55E")
        st.markdown(
            f"""
            <div style='
                background:#141A22;border:1px solid #283142;
                border-radius:8px;padding:10px 14px;
                font-size:12px;color:#9CA6B5;
            '>
                <strong style='color:#E6EAF0;'>Live Model</strong><br>
                Version: {meta.get("version", "?")} &nbsp;|&nbsp;
                Samples: {meta.get("n_samples", "?")}<br>
                Test R2: <span style='color:{r2_color};font-weight:700;'>
                    {test_r2:.4f}</span> &nbsp;|&nbsp;
                Test MAE: ${meta.get("test_mae", 0):,.0f}<br>
                Source: Adzuna live salary listings
            </div>
            """,
            unsafe_allow_html=True,
        )
        if test_r2 < 0.3:
            st.warning(
                "This model version has low predictive accuracy (R2 < 0.30). "
                "Consider retraining with more data or use Model 1 / Model 2 instead."
            )

    st.divider()
    st.markdown("#### Enter Profile Details")

    col1, col2 = st.columns(2)

    with col1:
        exp_label = st.selectbox(
            "Experience Level",
            _EXP_LABELS,
            index=1,
            key="lt_pred_exp",
            help=(
                "The model infers experience from title keywords at training time. "
                "For best results, select the level that matches your actual seniority."
            ),
        )
        experience_level = _EXP_REV[exp_label]

        education_level = st.selectbox(
            "Education Level",
            list(_EDU_DISPLAY.keys()),
            format_func=lambda x: _EDU_DISPLAY[x],
            index=1,
            key="lt_pred_edu",
            help=(
                "Education is not available in Adzuna data and defaults to "
                "Bachelor's during training, so this field has limited influence "
                "on the live model. It is kept for consistency with other models."
            ),
        )

        job_title_input = st.text_input(
            "Job Title",
            value="Data Scientist",
            max_chars=150,
            key="lt_pred_job",
            help=(
                "Enter a job title such as 'Data Scientist', 'Software Engineer', "
                "'Product Manager'. The predictor normalises your input to the "
                "nearest canonical training label. If no match is found, the raw "
                "title is used and the model may fall back to an average estimate."
            ),
        )

        contract_label = st.selectbox(
            "Employment Type",
            list(_CONTRACT_DISPLAY.values()),
            key="lt_pred_contract",
        )
        is_contract = 1 if contract_label == _CONTRACT_DISPLAY[1] else 0

    with col2:
        cs_label = st.selectbox(
            "Company Size",
            list(_CS_DISPLAY.values()),
            index=1,
            key="lt_pred_cs",
            help=(
                "Company size is not available in Adzuna data and defaults to "
                "Medium during training, so this field has limited influence on "
                "the live model."
            ),
        )
        company_size = _CS_REV[cs_label]

        company_location = st.text_input(
            "Company Location (ISO 2-letter code)",
            value="US",
            max_chars=2,
            key="lt_pred_loc",
            help="2-letter ISO country code. Examples: US, GB, IN, DE, CA, AU",
        ).strip().upper()

        rem_label = st.selectbox(
            "Work Mode",
            list(_REM_DISPLAY.values()),
            key="lt_pred_remote",
            help=(
                "Remote ratio is inferred from title keywords at training time "
                "(e.g. 'Remote Data Scientist' -> 100). Your selection here "
                "adjusts the model input accordingly."
            ),
        )
        remote_ratio = _REM_REV[rem_label]

        category_label = st.selectbox(
            "Job Category (Adzuna)",
            options=[
                "IT Jobs",
                "Accounting & Finance Jobs",
                "Engineering Jobs",
                "Healthcare & Nursing Jobs",
                "Sales Jobs",
                "Marketing Jobs",
                "Scientific & QA Jobs",
                "Consultancy Jobs",
                "Unknown",
            ],
            index=0,
            key="lt_pred_category",
            help=(
                "Select the broad category that best matches the role. "
                "This matches Adzuna's category labels used at training time."
            ),
        )

    st.caption(
        "Note: fields marked with an asterisk (*) have reduced influence on "
        "this model because Adzuna does not provide them in listings. "
        "Education (*) and Company Size (*) are inferred defaults. "
        "Results should be treated as indicative only."
    )
    st.divider()

    if st.button(
        ":material/calculate: Predict with Live Model",
        key="lt_predict_btn",
        type="primary",
        use_container_width=True,
    ):
        errors = []
        if not job_title_input.strip():
            errors.append("Job title cannot be empty.")
        if len(company_location) != 2 or not company_location.isalpha():
            errors.append("Company location must be a 2-letter ISO code (e.g. US, GB).")
        if errors:
            for e in errors:
                st.error(e)
        else:
            pred, lower, upper, err = predict_salary(
                artefact=live_artefact,
                experience_level=experience_level,
                education_level=education_level,
                remote_ratio=remote_ratio,
                job_title=job_title_input.strip(),
                company_size=company_size,
                company_location=company_location,
                is_contract=is_contract,
                category_label=category_label,
            )
            if err:
                st.error(f"Prediction failed: {err}")
                st.session_state[_K_PRED] = None
            else:
                st.session_state[_K_PRED] = {
                    "pred": pred, "lower": lower, "upper": upper,
                    "inputs": {
                        "Experience Level":  exp_label,
                        "Education Level":   _EDU_DISPLAY[education_level],
                        "Job Title":         job_title_input.strip(),
                        "Employment Type":   contract_label,
                        "Company Size":      cs_label,
                        "Company Location":  company_location,
                        "Work Mode":         rem_label,
                        "Job Category":      category_label,
                    },
                }

    result = st.session_state.get(_K_PRED)
    if result is None:
        return

    pred  = result["pred"]
    lower = result["lower"]
    upper = result["upper"]

    _salary_card("ANNUAL SALARY ESTIMATE (USD) -- LIVE MODEL", f"${pred:,.2f}", "#34D399")

    st.divider()
    st.markdown(
        "<h3 style='text-align:center;'>Breakdown (Approximate)</h3>",
        unsafe_allow_html=True,
    )
    bk1, bk2, bk3 = st.columns(3)
    bk1.metric("Monthly",          f"${pred / 12:,.2f}")
    bk2.metric("Weekly",           f"${pred / 52:,.2f}")
    bk3.metric("Hourly (40 h/wk)", f"${pred / (52 * 40):,.2f}")

    st.divider()
    st.markdown(
        "<h3 style='text-align:center;'>Salary Range (80% Interval)</h3>",
        unsafe_allow_html=True,
    )
    iv1, iv2 = st.columns(2)
    iv1.metric("Lower Estimate", f"${lower:,.2f}")
    iv2.metric("Upper Estimate", f"${upper:,.2f}")
    st.caption(
        "Interval estimated using 1.28 x test MAE (approximate 80% interval). "
        "The live model is trained on posted salary ranges which have high natural "
        "variance across countries and job levels, so this interval may be wide."
    )

    st.divider()
    mi1, mi2, mi3, mi4 = st.columns(4)
    mi1.metric("Model Version", meta.get("version", "-"))
    mi2.metric("Trained On",    f"{meta.get('n_samples', '?')} listings")
    mi3.metric("Test R2",       f"{meta.get('test_r2', 0):.4f}")
    mi4.metric("Test MAE",      f"${meta.get('test_mae', 0):,.0f}")
    st.caption(
        "This is an experimental live model trained on Adzuna job posting salary "
        "data. Performance is typically lower than Model 1 (Random Forest) and "
        "Model 2 (XGBoost), which are trained on larger, curated historical "
        "compensation datasets. For the most reliable salary estimates, "
        "please use Model 1 or Model 2 from the main prediction tabs."
    )


# ===========================================================================
# PUBLIC ENTRY POINT
# ===========================================================================

def render_live_training_tab() -> None:
    """
    Called from app_resume.py.
    Requires the user to be logged in (enforced in app_resume.py).
    Admin sees the training panel; all logged-in users see the prediction panel.
    """
    _init_state()

    st.markdown(
        "<h2 style='text-align:center;'>Live Community Model</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#9CA6B5;'>"
        "A GradientBoosting salary model trained on real Adzuna job listing data. "
        "Trained locally by the admin, served globally via HuggingFace Hub. "
        "This feature is <strong>experimental</strong> -- see the notice below."
        "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    if is_admin():
        if _is_local():
            _render_training_panel()
        else:
            _render_cloud_status()
        st.divider()

    _render_prediction_panel()