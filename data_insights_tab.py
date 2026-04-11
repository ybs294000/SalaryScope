"""
data_insights.py
----------------
Self-contained Data Insights tab renderer for SalaryScope.

Usage in app_resume.py (replaces the inline render_data_insights_tab):

    from data_insights import render_data_insights_tab
    ...
    with tab_objects[5]:
        render_data_insights_tab(IS_APP1, df_app1, df_app2, COUNTRY_NAME_MAP)

No circular imports: this module imports only stdlib + third-party libraries.
All heavy data is passed in as arguments so datasets are loaded once in the
host app and reused here without double loading.

Chart toggle guide
------------------
Every plot slot carries a comment block like:

    # DEFAULT: <chart type> -- <reason>
    # SIMPLE ALT: comment out the block above and uncomment the block below
    # ... simpler chart code ...

To switch a plot to its simpler alternative, comment out the DEFAULT block
and uncomment the SIMPLE ALT block immediately below it.  The alternatives
use only: histogram, bar, horizontal bar, line, scatter, box, pie, donut.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Colour constants matching the host app dark-professional theme
# ---------------------------------------------------------------------------
_BG_CARD    = "#141A22"
_BG_INPUT   = "#1B2230"
_BORDER     = "#283142"
_TEXT_MAIN  = "#E6EAF0"
_TEXT_MUTED = "#9CA6B5"

_C = [
    "#4F8EF7", "#38BDF8", "#34D399", "#A78BFA",
    "#F59E0B", "#FB923C", "#F472B6", "#22D3EE",
    "#818CF8", "#6EE7B7", "#FCD34D", "#F87171",
]

_EXP_ORDER  = ["Entry Level", "Mid Level", "Senior Level", "Executive Level"]
_SIZE_ORDER = ["Small Company", "Medium Company", "Large Company"]
_MODE_ORDER = ["On-site", "Hybrid", "Fully Remote"]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _themed(fig, extra=None):
    """Apply the app dark theme to any plotly figure."""
    layout = dict(
        paper_bgcolor=_BG_CARD,
        plot_bgcolor=_BG_INPUT,
        font=dict(color=_TEXT_MAIN, family="Inter, Segoe UI, sans-serif", size=13),
        title=dict(font=dict(color=_TEXT_MAIN, size=15)),
        colorway=_C,
        xaxis=dict(
            gridcolor=_BORDER, linecolor=_BORDER,
            tickfont=dict(color=_TEXT_MUTED, size=12),
            title_font=dict(color=_TEXT_MUTED, size=13),
            zerolinecolor=_BORDER, showgrid=True,
        ),
        yaxis=dict(
            gridcolor=_BORDER, linecolor=_BORDER,
            tickfont=dict(color=_TEXT_MUTED, size=12),
            title_font=dict(color=_TEXT_MUTED, size=13),
            zerolinecolor=_BORDER, showgrid=True,
        ),
        legend=dict(
            bgcolor=_BG_CARD, bordercolor=_BORDER, borderwidth=1,
            font=dict(color=_TEXT_MAIN, size=12),
        ),
        hoverlabel=dict(
            bgcolor="#1E2A3A", bordercolor=_BORDER,
            font=dict(color=_TEXT_MAIN, size=12),
        ),
        margin=dict(l=60, r=30, t=50, b=60),
    )
    if extra:
        layout.update(extra)
    fig.update_layout(**layout)
    return fig


def _rule():
    """Thin divider line matching the app border colour."""
    st.markdown(
        "<hr style='border:none;border-top:1px solid #283142;margin:4px 0 10px 0;'>",
        unsafe_allow_html=True,
    )


def _kpi_row(items):
    """
    Render a row of KPI metric tiles.
    items: list of (label, value, delta) tuples.  delta may be None.
    """
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        if delta is not None:
            col.metric(label, value, delta)
        else:
            col.metric(label, value)


def _stats_table(series, label="Salary (USD)"):
    """
    Render a styled st.dataframe showing describe() statistics for a numeric
    series, matching the dark theme.  This mirrors the original app behaviour
    where st.dataframe(df['Salary'].describe()) was used.
    """
    desc = series.describe().rename(label)
    desc.index = ["Count", "Mean", "Std Dev", "Min", "25th Pct", "Median", "75th Pct", "Max"]
    st.dataframe(
        desc.to_frame().style
            .format("{:,.2f}")
            .set_properties(**{
                "background-color": _BG_CARD,
                "color": _TEXT_MAIN,
                "border-color": _BORDER,
            }),
        width='stretch',
    )


# ===========================================================================
# APP 1 DASHBOARDS
# ===========================================================================

@st.fragment
def _app1_dash1(df):
    """
    App1 Dashboard 1: Salary Landscape and Distribution
    Theme: Overall salary shape, seniority and education spread.
    Plots: 1-histogram, 2-box(seniority), 3-box(education) [alt: bar],
           4-scatter(age vs exp) [alt: bar], 5-bar(avg by education).
    Stats table + 4 KPI tiles included.
    """
    with st.expander(":material/bar_chart: Dashboard 1 -- Salary Landscape and Distribution", expanded=True):
        st.caption(
            "Understand the overall shape of salary data -- where salaries cluster, "
            "how spread-out they are, and how seniority and education shift the distribution."
        )
        _rule()

        edu_map   = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
        edu_order = ["High School", "Bachelor's", "Master's", "PhD"]

        # Filters
        fc1, fc2, fc3 = st.columns([2, 2, 2])
        with fc1:
            edu_opts = ["All"] + [edu_map[k] for k in sorted(edu_map)]
            sel_edu = st.selectbox("Education Level", edu_opts, key="d1a1_edu")
        with fc2:
            sel_sr = st.selectbox("Seniority", ["All", "Non-Senior", "Senior"], key="d1a1_sr")
        with fc3:
            sal_cap = st.slider(
                "Salary Cap (USD)",
                int(df["Salary"].min()), int(df["Salary"].max()),
                int(df["Salary"].quantile(0.99)), step=5000, key="d1a1_cap",
                help="Exclude extreme outliers from the distribution charts",
            )

        dff = df[df["Salary"] <= sal_cap].copy()
        dff["Education Label"] = dff["Education Level"].map(edu_map)
        dff["Seniority"]       = dff["Senior"].map({0: "Non-Senior", 1: "Senior"})

        if sel_edu != "All":
            dff = dff[dff["Education Label"] == sel_edu]
        if sel_sr != "All":
            dff = dff[dff["Seniority"] == sel_sr]

        if dff.empty:
            st.warning("No data matches the selected filters.")
            return

        # KPIs
        _rule()
        med_sal   = dff["Salary"].median()
        mean_sal  = dff["Salary"].mean()
        pct_sr    = dff["Senior"].mean() * 100
        avg_exp   = dff["Years of Experience"].mean()
        _kpi_row([
            ("Records in View", f"{len(dff):,}", None),
            ("Median Salary", f"${med_sal:,.0f}", None),
            ("Mean Salary", f"${mean_sal:,.0f}", None),
            ("Senior Share", f"{pct_sr:.1f}%", None),
            ("Avg Experience", f"{avg_exp:.1f} yrs", None),
        ])
        _rule()

        # Stats table
        st.markdown("**Salary Summary Statistics**")
        _stats_table(dff["Salary"], label="Salary (USD)")
        _rule()

        r1c1, r1c2 = st.columns(2)

        # Plot 1: Salary histogram
        # DEFAULT: histogram -- shows the full distribution shape and bin density
        with r1c1:
            fig = px.histogram(
                dff, x="Salary", nbins=30,
                title="Salary Frequency Distribution",
                color_discrete_sequence=["#4F8EF7"],
                labels={"Salary": "Annual Salary (USD)"},
            )
            fig.update_traces(marker_line_color="#0C1118", marker_line_width=0.6)
            fig.update_layout(xaxis_title="Annual Salary (USD)", yaxis_title="Count")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 2: Box by seniority
        with r1c2:
            fig = px.box(
                dff, x="Seniority", y="Salary",
                title="Salary Spread by Seniority",
                color="Seniority",
                color_discrete_sequence=["#38BDF8", "#4F8EF7"],
                category_orders={"Seniority": ["Non-Senior", "Senior"]},
                points="outliers",
                labels={"Salary": "Annual Salary (USD)"},
            )
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        r2c1, r2c2 = st.columns(2)

        # Plot 3: Box by education level (uses unfiltered-by-education data for context)
        with r2c1:
            dff_v = df[df["Salary"] <= sal_cap].copy()
            dff_v["Education Label"] = dff_v["Education Level"].map(edu_map)
            dff_v["Seniority"]       = dff_v["Senior"].map({0: "Non-Senior", 1: "Senior"})
            if sel_sr != "All":
                dff_v = dff_v[dff_v["Seniority"] == sel_sr]
            fig = px.box(
                dff_v, x="Education Label", y="Salary",
                title="Salary Spread by Education Level",
                color="Education Label",
                color_discrete_sequence=_C[:4],
                labels={"Education Label": "", "Salary": "Annual Salary (USD)"},
                category_orders={"Education Label": edu_order},
                points="outliers",
            )
            fig.update_layout(showlegend=False, yaxis_title="Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 4: Scatter age vs experience
        with r2c2:
            samp = dff.sample(min(len(dff), 800), random_state=42)
            fig = px.scatter(
                samp, x="Years of Experience", y="Age",
                title="Age vs Years of Experience",
                color_discrete_sequence=["#4F8EF7"],
                opacity=0.55,
                labels={"Years of Experience": "Experience (yrs)", "Age": "Age (yrs)"},
                trendline="ols",
                trendline_color_override="#F59E0B",
            )
            fig.update_traces(marker=dict(size=4), selector=dict(mode="markers"))
            fig.update_layout(xaxis_title="Experience (yrs)", yaxis_title="Age (yrs)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 5: Bar -- mean vs median salary by education (grouped)
        r3c1, _ = st.columns([3, 1])
        with r3c1:
            agg = (
                dff.groupby("Education Label")["Salary"]
                .agg(["mean", "median"])
                .reset_index()
                .rename(columns={"mean": "Mean", "median": "Median"})
                .set_index("Education Label")
                .reindex(edu_order)
                .reset_index()
            )
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=agg["Education Label"], y=agg["Mean"],
                name="Mean", marker_color="#4F8EF7",
                text=[f"${v:,.0f}" for v in agg["Mean"]],
                textposition="outside", textfont=dict(color=_TEXT_MUTED, size=11),
            ))
            fig.add_trace(go.Bar(
                x=agg["Education Label"], y=agg["Median"],
                name="Median", marker_color="#34D399",
                text=[f"${v:,.0f}" for v in agg["Median"]],
                textposition="outside", textfont=dict(color=_TEXT_MUTED, size=11),
            ))
            fig.update_layout(
                title="Mean vs Median Salary by Education Level",
                barmode="group", xaxis_title="", yaxis_title="Annual Salary (USD)",
            )
            _themed(fig)
            st.plotly_chart(fig, width='stretch')


@st.fragment
def _app1_dash2(df):
    """
    App1 Dashboard 2: Education, Experience and Career Progression
    Theme: How education and experience jointly drive salary growth.
    Plots: 6-scatter(exp vs salary by edu), 7-grouped bar(edu x gender),
           8-line(progression by exp band), 9-bar(senior premium by edu),
           10-bar(top job titles).
    Stats table + KPIs included.
    """
    with st.expander(":material/school: Dashboard 2 -- Education, Experience and Career Progression"):
        st.caption(
            "Explore how education level, years of experience, and gender "
            "jointly shape salary outcomes across career stages."
        )
        _rule()

        edu_map   = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
        edu_order = ["High School", "Bachelor's", "Master's", "PhD"]

        dfc = df.copy()
        dfc["Education Label"] = dfc["Education Level"].map(edu_map)
        dfc["Seniority"]       = dfc["Senior"].map({0: "Non-Senior", 1: "Senior"})

        # Filters
        fa, fb = st.columns([2, 4])
        with fa:
            gender_opts = ["All"] + sorted(dfc["Gender"].dropna().unique().tolist())
            sel_gen = st.selectbox("Gender", gender_opts, key="d2a1_gen")
        with fb:
            emin = int(dfc["Years of Experience"].min())
            emax = int(dfc["Years of Experience"].max())
            exp_rng = st.slider(
                "Experience Range (years)", emin, emax, (emin, emax), key="d2a1_exp"
            )

        dff = dfc[
            (dfc["Years of Experience"] >= exp_rng[0]) &
            (dfc["Years of Experience"] <= exp_rng[1])
        ].copy()
        if sel_gen != "All":
            dff = dff[dff["Gender"] == sel_gen]

        if dff.empty:
            st.warning("No data matches the selected filters.")
            return

        # KPIs
        _rule()
        corr_exp_sal = dff[["Years of Experience", "Salary"]].corr().iloc[0, 1]
        top_edu      = dff.groupby("Education Label")["Salary"].mean().idxmax()
        sr_premium   = (
            dff[dff["Seniority"] == "Senior"]["Salary"].mean() -
            dff[dff["Seniority"] == "Non-Senior"]["Salary"].mean()
        )
        avg_sal = dff["Salary"].mean()
        _kpi_row([
            ("Records in View", f"{len(dff):,}", None),
            ("Mean Salary", f"${avg_sal:,.0f}", None),
            ("Exp-Salary Correlation", f"{corr_exp_sal:.2f}", None),
            ("Highest Paying Education", top_edu, None),
            ("Seniority Premium (avg)", f"${sr_premium:,.0f}", None),
        ])
        _rule()

        # Stats table
        st.markdown("**Salary Summary Statistics**")
        _stats_table(dff["Salary"], label="Salary (USD)")
        _rule()

        r1c1, r1c2 = st.columns(2)

        # Plot 6: Scatter experience vs salary coloured by education
        with r1c1:
            samp = dff.sample(min(len(dff), 800), random_state=42)
            fig = px.scatter(
                samp, x="Years of Experience", y="Salary",
                color="Education Label",
                title="Experience vs Salary (by Education)",
                color_discrete_sequence=_C[:4],
                opacity=0.65,
                category_orders={"Education Label": edu_order},
                labels={"Years of Experience": "Experience (yrs)", "Salary": "Annual Salary (USD)"},
                trendline="ols",
            )
            fig.update_traces(marker=dict(size=5), selector=dict(mode="markers"))
            fig.update_layout(xaxis_title="Experience (yrs)", yaxis_title="Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 7: Grouped bar gender x education
        with r1c2:
            g_edu = (
                dff.groupby(["Education Label", "Gender"])["Salary"]
                .mean().reset_index()
            )
            g_edu = g_edu[g_edu["Education Label"].isin(edu_order)]
            fig = px.bar(
                g_edu, x="Education Label", y="Salary",
                color="Gender",
                barmode="group",
                title="Average Salary by Education Level and Gender",
                color_discrete_sequence=["#F472B6", "#38BDF8", "#34D399"],
                labels={"Education Label": "", "Salary": "Avg Annual Salary (USD)"},
                category_orders={"Education Label": edu_order},
            )
            fig.update_layout(yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        r2c1, r2c2 = st.columns(2)

        # Plot 8: Line -- salary progression by experience band x seniority
        with r2c1:
            dff2 = dff.copy()
            bins     = list(range(0, int(dff2["Years of Experience"].max()) + 6, 5))
            labels_b = [f"{b}-{b+4} yrs" for b in bins[:-1]]
            dff2["Exp Band"] = pd.cut(
                dff2["Years of Experience"], bins=bins, labels=labels_b, right=False
            )
            prog = (
                dff2.groupby(["Exp Band", "Seniority"], observed=True)["Salary"]
                .mean().reset_index()
            )
            fig = px.line(
                prog, x="Exp Band", y="Salary",
                color="Seniority",
                title="Salary Progression by Experience Band",
                markers=True,
                color_discrete_sequence=["#38BDF8", "#A78BFA"],
                labels={"Exp Band": "Experience Band", "Salary": "Avg Annual Salary (USD)"},
            )
            fig.update_layout(xaxis_title="", yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 9: Bar -- senior premium (senior avg - non-senior avg) per education
        with r2c2:
            pass

        # Plot 10: Horizontal bar -- top 10 job titles by average salary
        r3c1, _ = st.columns([3, 1])
        with r3c1:
            job_top = (
                dff.groupby("Job Title")["Salary"].mean().reset_index()
                .sort_values("Salary", ascending=True).tail(10)
            )
            fig = px.bar(
                job_top, x="Salary", y="Job Title",
                orientation="h",
                title="Top 10 Job Titles by Average Salary",
                color_discrete_sequence=["#4F8EF7"],
                text=[f"${v:,.0f}" for v in job_top["Salary"]],
                labels={"Salary": "Avg Annual Salary (USD)", "Job Title": ""},
            )
            fig.update_traces(textposition="outside", textfont=dict(color=_TEXT_MUTED, size=10))
            fig.update_layout(height=350, xaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')


@st.fragment
def _app1_dash3(df):
    """
    App1 Dashboard 3: Job Roles and Geographic Salary Landscape
    Theme: Which roles and countries drive the highest compensation?
    Plots: 11-horizontal bar(top-N roles), 12-bar(country avg), 13-scatter(country
           count vs avg), 14-box(top-5 common titles).
    KPIs included.
    """
    with st.expander(":material/public: Dashboard 3 -- Job Roles and Geographic Salary Landscape"):
        st.caption(
            "Discover which job titles command the highest salaries and how "
            "geographic location shapes compensation in this dataset."
        )
        _rule()

        edu_map = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
        dfc = df.copy()
        dfc["Education Label"] = dfc["Education Level"].map(edu_map)
        dfc["Seniority"]       = dfc["Senior"].map({0: "Non-Senior", 1: "Senior"})

        # Filters
        fa, fb, fc = st.columns([2, 2, 2])
        with fa:
            top_n = st.selectbox("Top N Job Titles", [10, 15, 20], index=0, key="d3a1_topn")
        with fb:
            sel_sr = st.selectbox("Seniority", ["All", "Senior", "Non-Senior"], key="d3a1_sr")
        with fc:
            edu_opts = ["All"] + [edu_map[k] for k in sorted(edu_map)]
            sel_edu  = st.selectbox("Education", edu_opts, key="d3a1_edu")

        dff = dfc.copy()
        if sel_sr != "All":
            dff = dff[dff["Seniority"] == sel_sr]
        if sel_edu != "All":
            dff = dff[dff["Education Label"] == sel_edu]

        if dff.empty:
            st.warning("No data matches the selected filters.")
            return

        # KPIs
        _rule()
        top_country = dff.groupby("Country")["Salary"].mean().idxmax()
        top_job     = dff.groupby("Job Title")["Salary"].mean().idxmax()
        max_country_sal = dff.groupby("Country")["Salary"].mean().max()
        max_job_sal     = dff.groupby("Job Title")["Salary"].mean().max()
        _kpi_row([
            ("Records in View", f"{len(dff):,}", None),
            ("Unique Job Titles", dff["Job Title"].nunique(), None),
            ("Countries", dff["Country"].nunique(), None),
            ("Highest Paying Country", top_country, None),
            ("Highest Paying Role (avg)", f"${max_job_sal:,.0f}", None),
        ])
        _rule()

        # Plot 11: Horizontal bar -- top-N job titles by average salary
        job_agg = (
            dff.groupby("Job Title")["Salary"].mean().reset_index()
            .sort_values("Salary", ascending=True).tail(top_n)
        )
        fig = px.bar(
            job_agg, x="Salary", y="Job Title",
            orientation="h",
            title=f"Top {top_n} Job Titles by Average Salary",
            color_discrete_sequence=["#4F8EF7"],
            text=[f"${v:,.0f}" for v in job_agg["Salary"]],
            labels={"Salary": "Average Annual Salary (USD)", "Job Title": ""},
        )
        fig.update_traces(textposition="outside", textfont=dict(color=_TEXT_MUTED, size=10))
        fig.update_layout(height=max(300, top_n * 28), xaxis_title="Avg Annual Salary (USD)")
        _themed(fig)
        st.plotly_chart(fig, width='stretch')

        _rule()
        r2c1, r2c2 = st.columns(2)

        # Plot 12: Bar -- average salary by country
        with r2c1:
            c_agg = (
                dff.groupby("Country")["Salary"]
                .agg(["mean", "count"]).reset_index()
                .rename(columns={"mean": "Avg Salary", "count": "Count"})
                .sort_values("Avg Salary", ascending=False)
            )
            fig = px.bar(
                c_agg, x="Country", y="Avg Salary",
                title="Average Salary by Country",
                color="Country",
                color_discrete_sequence=_C,
                labels={"Avg Salary": "Avg Annual Salary (USD)"},
            )
            fig.update_layout(
                showlegend=False, xaxis_title="",
                yaxis_title="Avg Annual Salary (USD)", xaxis_tickangle=-30,
            )
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 13: Scatter -- country record count vs avg salary (bubble)
        with r2c2:
            fig = px.scatter(
                c_agg, x="Count", y="Avg Salary",
                size="Count",
                color="Country",
                text="Country",
                title="Country: Sample Size vs Avg Salary",
                labels={"Count": "Number of Records", "Avg Salary": "Avg Annual Salary (USD)"},
                color_discrete_sequence=_C,
                size_max=50,
            )
            fig.update_traces(
                textposition="top center",
                textfont=dict(size=10, color=_TEXT_MUTED),
                marker=dict(opacity=0.8),
            )
            fig.update_layout(
                showlegend=False,
                xaxis_title="Record Count", yaxis_title="Avg Annual Salary (USD)",
            )
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 14: Box -- salary for top-5 most common job titles
        top10 = dff["Job Title"].value_counts().head(10).index.tolist()
        df10  = dff[dff["Job Title"].isin(top10)]
        if not df10.empty:
            fig = px.box(
                df10, x="Job Title", y="Salary",
                color="Job Title",
                title="Salary Range for 10 Most Common Job Titles",
                color_discrete_sequence=_C[:10],
                labels={"Job Title": "", "Salary": "Annual Salary (USD)"},
                points="outliers",
            )
            fig.update_layout(showlegend=False, xaxis_title="")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')


# ===========================================================================
# APP 2 DASHBOARDS
# ===========================================================================

@st.fragment
def _app2_dash1(df):
    """
    App2 Dashboard 1: Salary Landscape and Distribution
    Theme: Overall data science salary shape and employment structure.
    Plots: 1-histogram, 2-box(experience), 3-bar(company size avg),
           4-bar(employment type), 5-pie(employment type share).
    Stats table + KPIs included.
    """
    EXP_MAP  = {"EN": "Entry Level", "MI": "Mid Level", "SE": "Senior Level", "EX": "Executive Level"}
    SIZE_MAP = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}
    EMP_MAP  = {"FT": "Full-Time", "PT": "Part-Time", "CT": "Contract", "FL": "Freelance"}

    dfc = df.copy()
    dfc["Experience Level"] = dfc["experience_level"].map(EXP_MAP)
    dfc["Company Size"]     = dfc["company_size"].map(SIZE_MAP)
    dfc["Employment Type"]  = dfc["employment_type"].map(EMP_MAP)

    with st.expander(":material/bar_chart: Dashboard 1 -- Salary Landscape and Distribution", expanded=True):
        st.caption(
            "Understand the overall shape of data science salary data -- distribution spread, "
            "experience-tier gaps, and how employment structure affects pay."
        )
        _rule()

        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            emp_opts = ["All"] + sorted(dfc["Employment Type"].dropna().unique().tolist())
            sel_emp  = st.selectbox("Employment Type", emp_opts, key="d1a2_emp")
        with fc2:
            size_opts = ["All"] + _SIZE_ORDER
            sel_size  = st.selectbox("Company Size", size_opts, key="d1a2_size")
        with fc3:
            sal_cap = st.slider(
                "Salary Cap (USD)",
                int(dfc["salary_in_usd"].min()),
                int(dfc["salary_in_usd"].max()),
                int(dfc["salary_in_usd"].quantile(0.99)),
                step=5000, key="d1a2_cap",
                help="Exclude extreme outliers from the distribution charts",
            )

        dff = dfc[dfc["salary_in_usd"] <= sal_cap].copy()
        if sel_emp  != "All":
            dff = dff[dff["Employment Type"] == sel_emp]
        if sel_size != "All":
            dff = dff[dff["Company Size"] == sel_size]

        if dff.empty:
            st.warning("No data matches the selected filters.")
            return

        # KPIs
        _rule()
        med_sal  = dff["salary_in_usd"].median()
        mean_sal = dff["salary_in_usd"].mean()
        top_exp  = dff.groupby("Experience Level")["salary_in_usd"].mean().idxmax()
        top_size = dff.groupby("Company Size")["salary_in_usd"].mean().idxmax()
        _kpi_row([
            ("Records in View", f"{len(dff):,}", None),
            ("Median Salary", f"${med_sal:,.0f}", None),
            ("Mean Salary", f"${mean_sal:,.0f}", None),
            ("Highest Paying Exp Tier", top_exp, None),
            ("Highest Paying Company Size", top_size, None),
        ])
        _rule()

        # Stats table
        st.markdown("**Salary Summary Statistics**")
        _stats_table(dff["salary_in_usd"], label="Salary (USD)")
        _rule()

        r1c1, r1c2 = st.columns(2)

        # Plot 1: Salary histogram
        # DEFAULT: histogram -- shows full distribution shape
        with r1c1:
            fig = px.histogram(
                dff, x="salary_in_usd", nbins=30,
                title="Salary Frequency Distribution",
                color_discrete_sequence=["#4F8EF7"],
                labels={"salary_in_usd": "Annual Salary (USD)"},
            )
            fig.update_traces(marker_line_color="#0C1118", marker_line_width=0.6)
            fig.update_layout(xaxis_title="Annual Salary (USD)", yaxis_title="Count")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 2: Box by experience level
        with r1c2:
            fig = px.box(
                dff, x="Experience Level", y="salary_in_usd",
                title="Salary Range by Experience Level",
                color="Experience Level",
                color_discrete_sequence=_C[:4],
                category_orders={"Experience Level": _EXP_ORDER},
                points="outliers",
                labels={"salary_in_usd": "Annual Salary (USD)"},
            )
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        r2c1, r2c2 = st.columns(2)

        # Plot 3: Bar -- average salary by company size
        # DEFAULT: vertical bar -- clean comparison of three size categories
        with r2c1:
            dff_s = dfc[dfc["salary_in_usd"] <= sal_cap].copy()
            if sel_emp != "All":
                dff_s = dff_s[dff_s["Employment Type"] == sel_emp]
            size_agg = (
                dff_s.groupby("Company Size")["salary_in_usd"].mean().reset_index()
                .rename(columns={"salary_in_usd": "Avg Salary"})
                .set_index("Company Size").reindex(_SIZE_ORDER).reset_index()
            )
            fig = px.bar(
                size_agg, x="Company Size", y="Avg Salary",
                title="Average Salary by Company Size",
                color="Company Size",
                color_discrete_sequence=_C[:3],
                text=[f"${v:,.0f}" for v in size_agg["Avg Salary"]],
                labels={"Company Size": "", "Avg Salary": "Avg Annual Salary (USD)"},
                category_orders={"Company Size": _SIZE_ORDER},
            )
            fig.update_traces(textposition="outside", textfont=dict(color=_TEXT_MUTED, size=11))
            fig.update_layout(showlegend=False, yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 4: Bar -- average salary by employment type
        with r2c2:
            emp_agg = (
                dff.groupby("Employment Type")["salary_in_usd"].mean().reset_index()
                .rename(columns={"salary_in_usd": "Avg Salary"})
                .sort_values("Avg Salary", ascending=False)
            )
            fig = px.bar(
                emp_agg, x="Employment Type", y="Avg Salary",
                title="Average Salary by Employment Type",
                color="Employment Type",
                color_discrete_sequence=_C[:4],
                text=[f"${v:,.0f}" for v in emp_agg["Avg Salary"]],
                labels={"Employment Type": "", "Avg Salary": "Avg Annual Salary (USD)"},
            )
            fig.update_traces(textposition="outside", textfont=dict(color=_TEXT_MUTED, size=11))
            fig.update_layout(showlegend=False, yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 5: Donut -- share of records by employment type
        r3c1, r3c2 = st.columns([2, 3])
        with r3c1:
            emp_cnt = dff["Employment Type"].value_counts().reset_index()
            emp_cnt.columns = ["Employment Type", "Count"]
            fig = px.pie(
                emp_cnt, names="Employment Type", values="Count",
                title="Employment Type Share",
                color_discrete_sequence=_C[:4],
                hole=0.45,
            )
            fig.update_traces(textinfo="label+percent", textfont_size=12)
            _themed(fig, extra={"margin": dict(l=10, r=10, t=50, b=10)})
            st.plotly_chart(fig, width='stretch')

        with r3c2:
            st.markdown("**Salary Summary by Employment Type**")
            _rule()
            emp_stats = (
                dff.groupby("Employment Type")["salary_in_usd"]
                .agg(["count", "mean", "median", "std"])
                .reset_index()
                .rename(columns={
                    "Employment Type": "Type",
                    "count": "Count",
                    "mean": "Mean",
                    "median": "Median",
                    "std": "Std Dev",
                })
            )
            st.dataframe(
                emp_stats.style
                    .format({"Count": "{:,.0f}", "Mean": "${:,.0f}", "Median": "${:,.0f}", "Std Dev": "${:,.0f}"})
                    .set_properties(**{
                        "background-color": _BG_CARD,
                        "color": _TEXT_MAIN,
                        "border-color": _BORDER,
                    }),
                width='stretch',
                hide_index=True,
            )


@st.fragment
def _app2_dash2(df):
    """
    App2 Dashboard 2: Work Mode, Company Size and Experience Interactions
    Theme: Cross-factor salary patterns across work arrangement and company scale.
    Plots: 6-grouped bar(exp x size), 7-line(work mode per exp tier),
           8-bar(work mode avg), 9-stacked bar(workforce distribution),
           10-scatter(exp vs salary by work mode).
    KPIs included.
    """
    EXP_MAP  = {"EN": "Entry Level", "MI": "Mid Level", "SE": "Senior Level", "EX": "Executive Level"}
    SIZE_MAP = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}
    MODE_MAP = {0: "On-site", 50: "Hybrid", 100: "Fully Remote"}

    dfc = df.copy()
    dfc["Experience Level"] = dfc["experience_level"].map(EXP_MAP)
    dfc["Company Size"]     = dfc["company_size"].map(SIZE_MAP)
    dfc["Work Mode"]        = dfc["remote_ratio"].map(MODE_MAP)

    with st.expander(":material/corporate_fare: Dashboard 2 -- Work Mode, Company Size and Experience Interactions"):
        st.caption(
            "Examine how company scale and work arrangement interact with experience "
            "level to shape salary -- and identify where cross-factor patterns are strongest."
        )
        _rule()

        # Filters
        fa, fb = st.columns([2, 2])
        with fa:
            sel_exp  = st.selectbox("Experience Level", ["All"] + _EXP_ORDER, key="d2a2_exp")
        with fb:
            sel_mode = st.selectbox("Work Mode", ["All"] + _MODE_ORDER, key="d2a2_mode")

        dff = dfc.copy()
        if sel_exp  != "All":
            dff = dff[dff["Experience Level"] == sel_exp]
        if sel_mode != "All":
            dff = dff[dff["Work Mode"] == sel_mode]

        if dff.empty:
            st.warning("No data matches the selected filters.")
            return

        # KPIs
        _rule()
        top_mode_sal = dfc.groupby("Work Mode")["salary_in_usd"].mean()
        best_mode    = top_mode_sal.idxmax()
        remote_pct   = (dfc["Work Mode"] == "Fully Remote").mean() * 100
        top_size_exp = (
            dfc.groupby(["Experience Level", "Company Size"])["salary_in_usd"]
            .mean().idxmax()
        )
        _kpi_row([
            ("Records in View", f"{len(dff):,}", None),
            ("Highest Paying Work Mode", best_mode, None),
            ("Fully Remote Share", f"{remote_pct:.1f}%", None),
            ("Best Exp + Size Combo", f"{top_size_exp[0]} / {top_size_exp[1]}", None),
        ])
        _rule()

        r1c1, r1c2 = st.columns(2)

        # Plot 6: Grouped bar -- experience level x company size (full dataset)
        # DEFAULT: grouped bar -- side-by-side across experience tiers
        with r1c1:
            agg_es = (
                dfc.groupby(["Experience Level", "Company Size"])["salary_in_usd"]
                .mean().reset_index()
                .rename(columns={"salary_in_usd": "Avg Salary"})
            )
            fig = px.bar(
                agg_es, x="Experience Level", y="Avg Salary",
                color="Company Size",
                barmode="group",
                title="Avg Salary -- Experience Level vs Company Size",
                color_discrete_sequence=_C[:3],
                labels={"Avg Salary": "Avg Annual Salary (USD)"},
                category_orders={"Experience Level": _EXP_ORDER, "Company Size": _SIZE_ORDER},
            )
            fig.update_layout(xaxis_title="", yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 7: Line -- avg salary by work mode per experience tier
        with r1c2:
            agg_me = (
                dfc.groupby(["Experience Level", "Work Mode"])["salary_in_usd"]
                .mean().reset_index()
                .rename(columns={"salary_in_usd": "Avg Salary"})
            )
            fig = px.line(
                agg_me, x="Work Mode", y="Avg Salary",
                color="Experience Level",
                title="Salary by Work Mode Across Experience Tiers",
                markers=True,
                color_discrete_sequence=_C[:4],
                labels={"Avg Salary": "Avg Annual Salary (USD)"},
                category_orders={"Work Mode": _MODE_ORDER, "Experience Level": _EXP_ORDER},
            )
            fig.update_layout(xaxis_title="", yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        r2c1, r2c2 = st.columns(2)

        # Plot 8: Bar -- average salary by work mode
        # DEFAULT: vertical bar with value labels
        with r2c1:
            mode_agg = (
                dff.groupby("Work Mode")["salary_in_usd"].mean().reset_index()
                .rename(columns={"salary_in_usd": "Avg Salary"})
                .set_index("Work Mode").reindex(_MODE_ORDER).reset_index()
            )
            fig = px.bar(
                mode_agg, x="Work Mode", y="Avg Salary",
                title="Average Salary by Work Arrangement",
                color="Work Mode",
                color_discrete_sequence=_C[:3],
                text=[f"${v:,.0f}" for v in mode_agg["Avg Salary"]],
                labels={"Work Mode": "", "Avg Salary": "Avg Annual Salary (USD)"},
                category_orders={"Work Mode": _MODE_ORDER},
            )
            fig.update_traces(textposition="outside", textfont=dict(color=_TEXT_MUTED, size=11))
            fig.update_layout(showlegend=False, yaxis_title="Avg Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 9: Stacked bar -- workforce distribution of experience tiers by company size
        with r2c2:
            cnt = (
                dfc.groupby(["Company Size", "Experience Level"])
                .size().reset_index(name="Count")
            )
            fig = px.bar(
                cnt, x="Company Size", y="Count",
                color="Experience Level",
                title="Workforce Distribution -- Experience Tiers by Company Size",
                color_discrete_sequence=_C[:4],
                labels={"Count": "Number of Records"},
                category_orders={"Company Size": _SIZE_ORDER, "Experience Level": _EXP_ORDER},
                barmode="stack",
            )
            fig.update_layout(xaxis_title="", yaxis_title="Record Count")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')

        # Plot 10: Scatter -- experience level (numeric remote ratio) vs salary by work mode
        r3c1, _ = st.columns([3, 1])
        with r3c1:
            samp = dff.sample(min(len(dff), 600), random_state=42)
            fig = px.scatter(
                samp, x="remote_ratio", y="salary_in_usd",
                color="Work Mode",
                title="Salary vs Remote Ratio (Individual Records)",
                color_discrete_sequence=_C[:3],
                opacity=0.6,
                labels={"remote_ratio": "Remote Ratio (%)", "salary_in_usd": "Annual Salary (USD)"},
                category_orders={"Work Mode": _MODE_ORDER},
            )
            fig.update_traces(marker=dict(size=5))
            fig.update_layout(xaxis_title="Remote Ratio (%)", yaxis_title="Annual Salary (USD)")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')


@st.fragment
def _app2_dash3(df, country_map):
    """
    App2 Dashboard 3: Job Roles and Geographic Salary Patterns
    Theme: Which data science roles and markets offer highest compensation?
    Plots: 11-horizontal bar(top-N roles), 12-bar(top countries),
           13-scatter(country count vs avg), 14-box(top-5 common roles).
    KPIs included.
    """
    EXP_MAP  = {"EN": "Entry Level", "MI": "Mid Level", "SE": "Senior Level", "EX": "Executive Level"}
    SIZE_MAP = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}

    dfc = df.copy()
    dfc["Experience Level"]      = dfc["experience_level"].map(EXP_MAP)
    dfc["Company Size"]          = dfc["company_size"].map(SIZE_MAP)
    dfc["Company Location Full"] = dfc["company_location"].map(lambda x: country_map.get(x, x))

    with st.expander(":material/public: Dashboard 3 -- Job Roles and Geographic Salary Patterns"):
        st.caption(
            "Discover which data science roles and geographic markets offer the "
            "highest compensation, and how dataset representation varies by country."
        )
        _rule()

        # Filters
        fa, fb, fc = st.columns([2, 2, 2])
        with fa:
            top_n    = st.selectbox("Top N Roles", [10, 15, 20], index=0, key="d3a2_topn")
        with fb:
            sel_exp  = st.selectbox("Experience Level", ["All"] + _EXP_ORDER, key="d3a2_exp")
        with fc:
            sel_size = st.selectbox("Company Size", ["All"] + _SIZE_ORDER, key="d3a2_size")

        dff = dfc.copy()
        if sel_exp  != "All":
            dff = dff[dff["Experience Level"] == sel_exp]
        if sel_size != "All":
            dff = dff[dff["Company Size"] == sel_size]

        if dff.empty:
            st.warning("No data matches the selected filters.")
            return

        # KPIs
        _rule()
        c_agg_kpi  = dff.groupby("Company Location Full")["salary_in_usd"].mean()
        top_country = c_agg_kpi.idxmax() if not c_agg_kpi.empty else "N/A"
        role_agg_kpi = (
            dff.groupby("job_title")["salary_in_usd"]
            .agg(["mean", "count"])
        )
        role_agg_kpi = role_agg_kpi[role_agg_kpi["count"] >= 3]
        top_role     = role_agg_kpi["mean"].idxmax() if not role_agg_kpi.empty else "N/A"
        top_role_sal = role_agg_kpi["mean"].max()    if not role_agg_kpi.empty else 0
        _kpi_row([
            ("Records in View", f"{len(dff):,}", None),
            ("Unique Roles", dff["job_title"].nunique(), None),
            ("Countries", dff["Company Location Full"].nunique(), None),
            ("Highest Paying Country", top_country, None),
            ("Top Role Avg Salary", f"${top_role_sal:,.0f}", None),
        ])
        _rule()

        # Plot 11: Horizontal bar -- top-N roles by average salary
        role_agg = (
            dff.groupby("job_title")["salary_in_usd"]
            .agg(["mean", "count"]).reset_index()
            .rename(columns={"mean": "Avg Salary", "count": "Count"})
        )
        role_agg = role_agg[role_agg["Count"] >= 3]
        top_roles = role_agg.sort_values("Avg Salary", ascending=True).tail(top_n)
        fig = px.bar(
            top_roles, x="Avg Salary", y="job_title",
            orientation="h",
            title=f"Top {top_n} Data Science Roles by Average Salary",
            color_discrete_sequence=["#4F8EF7"],
            text=[f"${v:,.0f}" for v in top_roles["Avg Salary"]],
            labels={"Avg Salary": "Avg Annual Salary (USD)", "job_title": ""},
        )
        fig.update_traces(textposition="outside", textfont=dict(color=_TEXT_MUTED, size=10))
        fig.update_layout(height=max(300, top_n * 28), xaxis_title="Avg Annual Salary (USD)")
        _themed(fig)
        st.plotly_chart(fig, width='stretch')

        _rule()
        r2c1 = st.columns(1)

        # Plot 12: Bar -- top 10 countries by average salary
        c_agg = (
            dff.groupby("Company Location Full")["salary_in_usd"]
            .agg(["mean", "count"]).reset_index()
            .rename(columns={"mean": "Avg Salary", "count": "Count"})
        )
        top_c = c_agg[c_agg["Count"] >= 10].sort_values("Avg Salary", ascending=False).head(10)
        fig = px.bar(
            top_c, x="Company Location Full", y="Avg Salary",
            title="Top 10 Countries by Average Data Science Salary",
            color="Company Location Full",
            color_discrete_sequence=_C,
            labels={"Company Location Full": "Country", "Avg Salary": "Avg Annual Salary (USD)"},
        )
        fig.update_layout(
            showlegend=False, xaxis_title="",
            yaxis_title="Avg Annual Salary (USD)", xaxis_tickangle=-30,
        )
        _themed(fig)
        st.plotly_chart(fig, width='stretch')
       
        # Plot 14: Box -- salary for top-5 most common data science roles
        top10 = dff["job_title"].value_counts().head(10).index.tolist()
        df10  = dff[dff["job_title"].isin(top10)]
        if not df10.empty:
            fig = px.box(
                df10, x="job_title", y="salary_in_usd",
                color="job_title",
                title="Salary Range for 10 Most Common Data Science Roles",
                color_discrete_sequence=_C[:10],
                labels={"job_title": "", "salary_in_usd": "Annual Salary (USD)"},
                points="outliers",
            )
            fig.update_layout(showlegend=False, xaxis_title="")
            _themed(fig)
            st.plotly_chart(fig, width='stretch')


# ===========================================================================
# PUBLIC ENTRY POINT
# ===========================================================================

def render_data_insights_tab(
    is_app1: bool,
    df_app1: pd.DataFrame,
    df_app2: pd.DataFrame,
    country_name_map: dict,
    apply_theme_fn=None,
):
    """
    Render the full Data Insights tab.

    Parameters
    ----------
    is_app1 : bool
        True when Model 1 (Random Forest) is active; False for Model 2 (XGBoost).
    df_app1 : pd.DataFrame
        Pre-loaded App1 dataset, passed in from the host app (no double loading).
    df_app2 : pd.DataFrame
        Pre-loaded App2 dataset, passed in from the host app (no double loading).
    country_name_map : dict
        ISO-code to country name mapping from the host app.
    apply_theme_fn : callable, optional
        Accepted for API compatibility but unused; the module manages its own
        theming to remain self-contained.
    """
    st.header(":material/insights: Dataset Insights and Exploratory Analysis")

    if is_app1:
        st.caption(
            "Explore the general salary dataset used to train Model 1. "
            "Three themed dashboards below cover salary distributions, "
            "human capital dimensions, and geographic or role-based patterns. "
            "Each dashboard has independent filters and KPI tiles. "
            "Expand and collapse sections as needed."
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Records", f"{df_app1.shape[0]:,}")
        c2.metric("Features", df_app1.shape[1])
        c3.metric("Unique Job Titles", df_app1["Job Title"].nunique())
        c4.metric("Countries", df_app1["Country"].nunique())

        st.divider()

        _app1_dash1(df_app1)
        _app1_dash2(df_app1)
        _app1_dash3(df_app1)

    else:
        st.caption(
            "Explore the data science salary dataset used to train Model 2. "
            "Three themed dashboards below cover salary distributions, "
            "work mode and company interactions, and role or geographic patterns. "
            "Each dashboard has independent filters and KPI tiles. "
            "Expand and collapse sections as needed."
        )

        df2 = df_app2.copy()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Records", f"{df2.shape[0]:,}")
        c2.metric("Features", df2.shape[1])
        c3.metric("Unique Job Titles", df2["job_title"].nunique())
        c4.metric("Countries", df2["company_location"].nunique())

        st.divider()

        _app2_dash1(df2)
        _app2_dash2(df2)
        _app2_dash3(df2, country_name_map)