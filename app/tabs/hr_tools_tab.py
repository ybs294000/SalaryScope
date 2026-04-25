"""
app/tabs/hr_tools_tab.py
-------------------------
Entry point for the HR Tools tab. Renders five sub-tools via inner
sub-tabs. All business logic and sub-tool modules live under app/hr_tools/.

Integration in app_resume.py:
    from app.tabs.hr_tools_tab import render_hr_tools_tab

    # Add to tabs list (insert before About):
    tabs.append(":material/corporate_fare: HR Tools")

    # In the tab rendering block:
    hr_index = tabs.index(":material/corporate_fare: HR Tools")
    with tab_objects[hr_index]:
        render_hr_tools_tab(
            is_app1=IS_APP1,
            app1_model=app1_model if IS_APP1 else None,
            app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
            app1_job_titles=app1_job_titles,
            app1_countries=app1_countries,
            app1_genders=app1_genders,
            app2_model=app2_model if not IS_APP1 else None,
            app2_job_titles=app2_job_titles,
            app2_experience_levels=app2_experience_levels,
            app2_employment_types=app2_employment_types,
            app2_company_sizes=app2_company_sizes,
            app2_remote_ratios=app2_remote_ratios,
            app2_country_display_options=app2_country_display_options,
            app2_employee_residence_display_options=app2_employee_residence_display_options,
            SALARY_BAND_LABELS=SALARY_BAND_LABELS,
            EXPERIENCE_MAP=EXPERIENCE_MAP,
            EMPLOYMENT_MAP=EMPLOYMENT_MAP,
            COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
            REMOTE_MAP=REMOTE_MAP,
            EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
            EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
            COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
            COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
            title_features=title_features,
        )

Removing this tab:
    - Remove the import above.
    - Remove the tab label from the tabs list.
    - Remove the with block above.
    - Delete this file and the app/hr_tools/ directory.
    - Nothing else in the app is affected.
"""
# Note: sub-tool modules live in app/hr_tools/, not app/tabs/hr_tools/.

import streamlit as st

# Each sub-tool is imported individually so any one can be removed.
# If a module is missing the corresponding sub-tab is silently skipped.

_MODULES = {}

try:
    from app.hr_tools.hiring_budget import render_hiring_budget
    _MODULES["hiring_budget"] = render_hiring_budget
except ImportError:
    pass

try:
    from app.hr_tools.benchmarking_table import render_benchmarking_table
    _MODULES["benchmarking_table"] = render_benchmarking_table
except ImportError:
    pass

try:
    from app.hr_tools.candidate_comparison import render_candidate_comparison
    _MODULES["candidate_comparison"] = render_candidate_comparison
except ImportError:
    pass

try:
    from app.hr_tools.offer_checker import render_offer_checker
    _MODULES["offer_checker"] = render_offer_checker
except ImportError:
    pass

try:
    from app.hr_tools.team_audit import render_team_audit
    _MODULES["team_audit"] = render_team_audit
except ImportError:
    pass


def render_hr_tools_tab(**kwargs):
    """
    Renders the HR Tools tab with inner sub-tabs for each tool.
    All kwargs are forwarded transparently to each sub-tool renderer.
    If a sub-tool module is missing it is silently omitted.
    """

    st.markdown(
        """
        <div style="margin-bottom: 18px;">
            <h2 style="margin-bottom: 4px;">HR & Employer Tools</h2>
            <p style="color: var(--text-muted); margin-top: 0; font-size: 14px;">
                Compensation planning and benchmarking tools for HR teams and hiring managers.
                All salary estimates are produced by the currently active ML model.
                Each tool allows manual overrides where model estimates may not reflect
                company-specific context.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sub_tab_config = []

    if "hiring_budget" in _MODULES:
        sub_tab_config.append((":material/payments: Hiring Budget", "hiring_budget"))

    if "benchmarking_table" in _MODULES:
        sub_tab_config.append((":material/table_chart: Salary Benchmarking", "benchmarking_table"))

    if "candidate_comparison" in _MODULES:
        sub_tab_config.append((":material/people: Candidate Comparison", "candidate_comparison"))

    if "offer_checker" in _MODULES:
        sub_tab_config.append((":material/fact_check: Offer Checker", "offer_checker"))

    if "team_audit" in _MODULES:
        sub_tab_config.append((":material/manage_accounts: Team Audit", "team_audit"))

    if not sub_tab_config:
        st.warning("No HR tool modules are available. Check that app/hr_tools/ is present.")
        return

    labels = [label for label, _ in sub_tab_config]
    keys   = [key   for _, key   in sub_tab_config]

    sub_tabs = st.tabs(labels)

    for tab_obj, key in zip(sub_tabs, keys):
        with tab_obj:
            try:
                _MODULES[key](**kwargs)
            except Exception as exc:
                st.error(f"Error loading this tool: {exc}")
