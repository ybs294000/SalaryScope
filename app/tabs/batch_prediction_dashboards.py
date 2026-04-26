"""
batch_prediction_dashboards.py
------------------------------
Grouped dashboard renderers for Batch Prediction results.

These dashboards are designed to sit directly after batch prediction results
instead of sending users to a separate analytics destination. That keeps the
workflow tight and avoids duplicating large prediction DataFrames in memory.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.theme import get_colorway, get_colorway_3_stages, get_token


def render_batch_dashboards_app1(
    analytics_df: pd.DataFrame,
    apply_theme,
    get_plot_df,
    generate_salary_leaderboard,
) -> None:
    st.header("Batch Prediction Dashboards")
    st.caption(
        "Explore the prediction results through grouped dashboards for salary distribution, progression patterns, and role-level comparisons."
    )

    sampled_df = get_plot_df(analytics_df)

    with st.expander(":material/dashboard: Dashboard 1 -- Prediction Overview", expanded=True):
        _render_app1_summary_metrics(analytics_df)
        _render_app1_overview_charts(analytics_df, apply_theme, generate_salary_leaderboard)

    with st.expander(":material/trending_up: Dashboard 2 -- Growth, Stage and Education", expanded=False):
        _render_app1_progression_charts(analytics_df, sampled_df, apply_theme)

    with st.expander(":material/public: Dashboard 3 -- Role, Country and Seniority", expanded=False):
        _render_app1_segmentation_charts(analytics_df, apply_theme, generate_salary_leaderboard)

    with st.expander(":material/monitoring: Dashboard 4 -- Advanced Statistical Views", expanded=False):
        _render_app1_advanced_charts(analytics_df, apply_theme)


def render_batch_dashboards_app2(
    analytics_df: pd.DataFrame,
    apply_theme,
    generate_salary_leaderboard,
    EXPERIENCE_MAP,
    COMPANY_SIZE_MAP,
    REMOTE_MAP,
    COUNTRY_NAME_MAP,
) -> None:
    st.header("Batch Prediction Dashboards")
    st.caption(
        "Explore the prediction results through grouped dashboards for salary distribution, experience patterns, and geography-level comparisons."
    )

    with st.expander(":material/dashboard: Dashboard 1 -- Prediction Overview", expanded=True):
        _render_app2_summary_metrics(analytics_df, EXPERIENCE_MAP)
        _render_app2_overview_charts(analytics_df, apply_theme, generate_salary_leaderboard)

    with st.expander(":material/apartment: Dashboard 2 -- Experience, Company and Work Mode", expanded=False):
        _render_app2_structure_charts(
            analytics_df,
            apply_theme,
            EXPERIENCE_MAP,
            COMPANY_SIZE_MAP,
            REMOTE_MAP,
        )

    with st.expander(":material/travel_explore: Dashboard 3 -- Role and Geography", expanded=False):
        _render_app2_location_charts(
            analytics_df,
            apply_theme,
            generate_salary_leaderboard,
            COUNTRY_NAME_MAP,
        )

    with st.expander(":material/monitoring: Dashboard 4 -- Advanced Statistical Views", expanded=False):
        _render_app2_advanced_charts(
            analytics_df,
            apply_theme,
            EXPERIENCE_MAP,
            COMPANY_SIZE_MAP,
            REMOTE_MAP,
        )


def _render_app1_summary_metrics(df: pd.DataFrame) -> None:
    avg_s = df["Predicted Annual Salary"].mean()
    median_s = df["Predicted Annual Salary"].median()
    min_s = df["Predicted Annual Salary"].min()
    max_s = df["Predicted Annual Salary"].max()

    level_counts = df["Estimated Salary Level"].value_counts()
    stage_counts = df["Career Stage"].value_counts()

    top_row = st.columns(4)
    top_row[0].metric("Records", f"{df.shape[0]:,}")
    top_row[1].metric("Average Salary", f"${avg_s:,.0f}")
    top_row[2].metric("Median Salary", f"${median_s:,.0f}")
    top_row[3].metric("Max Salary", f"${max_s:,.0f}")

    bottom_row = st.columns(3)
    bottom_row[0].metric("Min Salary", f"${min_s:,.0f}")
    bottom_row[1].metric("Professional Range", int(level_counts.get("Professional Range", 0)))
    bottom_row[2].metric("Growth Stage", int(stage_counts.get("Growth Stage", 0)))
    st.write(f"Salary range in this batch: \\${min_s:,.0f} to \\${max_s:,.0f}")


def _render_app1_overview_charts(df: pd.DataFrame, apply_theme, generate_salary_leaderboard) -> None:
    leaderboard = generate_salary_leaderboard(
        df=df,
        job_col="Job Title",
        salary_col="Predicted Annual Salary",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("This histogram shows how prediction counts are spread across salary values. Taller bars mean more records fell into that salary band.")
        fig = px.histogram(
            df,
            x="Predicted Annual Salary",
            nbins=min(25, len(df)),
            title="Predicted Salary Distribution",
            color_discrete_sequence=[get_colorway()[0]],
        )
        fig.update_traces(marker_line_color=get_token("surface_overlay", "#1B2230"), marker_line_width=0.8)
        fig.update_layout(xaxis_title="Predicted Salary (USD)", yaxis_title="Count")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("Use this to compare which roles land highest on average in the current batch. It highlights role-level pay differences, not how many records each role has.")
        fig = px.bar(
            leaderboard.head(10),
            x="Average Salary (USD)",
            y="Job Title",
            orientation="h",
            title="Top Roles by Average Predicted Salary",
            color_discrete_sequence=[get_colorway()[0]],
        )
        fig.update_yaxes(categoryorder="total ascending")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    c3, c4, c5 = st.columns([1, 1, 0.9])
    with c3:
        st.caption("This compares the average predicted salary across SalaryScope's salary-level groupings.")
        band_salary = (
            df.groupby("Estimated Salary Level")["Predicted Annual Salary"]
            .mean()
            .reset_index()
        )
        fig = px.bar(
            band_salary,
            x="Estimated Salary Level",
            y="Predicted Annual Salary",
            title="Average Salary by Salary Level",
            color="Estimated Salary Level",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=["Early Career Range", "Professional Range", "Executive Range"],
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c4:
        st.caption("This compares the average predicted salary across broad career-stage groupings.")
        stage_salary = (
            df.groupby("Career Stage")["Predicted Annual Salary"]
            .mean()
            .reset_index()
        )
        fig = px.bar(
            stage_salary,
            x="Career Stage",
            y="Predicted Annual Salary",
            title="Average Salary by Career Stage",
            color="Career Stage",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=["Entry Stage", "Growth Stage", "Leadership Stage"],
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c5:
        st.caption("This donut chart shows how the uploaded batch is split across SalaryScope's salary levels.")
        level_mix = (
            df["Estimated Salary Level"]
            .value_counts()
            .reindex(["Early Career Range", "Professional Range", "Executive Range"], fill_value=0)
            .reset_index()
        )
        level_mix.columns = ["Estimated Salary Level", "Count"]
        fig = px.pie(
            level_mix,
            names="Estimated Salary Level",
            values="Count",
            hole=0.55,
            title="Salary Level Share",
            color="Estimated Salary Level",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")


def _render_app1_progression_charts(df: pd.DataFrame, sampled_df: pd.DataFrame, apply_theme) -> None:
    edu_stage = (
        df.groupby(["Education Level", "Career Stage"])
        .size()
        .reset_index(name="Count")
    )
    edu_stage["Education Level"] = edu_stage["Education Level"].map(
        {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
    )

    edu_band = (
        df.groupby(["Education Level", "Estimated Salary Level"])
        .size()
        .reset_index(name="Count")
    )
    edu_band["Education Level"] = edu_band["Education Level"].map(
        {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Grouped bars show how often each salary level appears within each education segment.")
        fig = px.bar(
            edu_band,
            x="Education Level",
            y="Count",
            color="Estimated Salary Level",
            title="Salary Level Mix Across Education",
            barmode="group",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_xaxes(categoryorder="array", categoryarray=["High School", "Bachelor's", "Master's", "PhD"])
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("Grouped bars show how often each career stage appears within each education segment.")
        fig = px.bar(
            edu_stage,
            x="Education Level",
            y="Count",
            color="Career Stage",
            title="Career Stage Mix Across Education",
            barmode="group",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_xaxes(categoryorder="array", categoryarray=["High School", "Bachelor's", "Master's", "PhD"])
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    c3, = st.columns(1)
    with c3:
        st.caption("Each point is one predicted record. The trend line helps show the overall relationship between experience and predicted salary.")
        fig = px.scatter(
            sampled_df,
            x="Years of Experience",
            y="Predicted Annual Salary",
            trendline="ols",
            trendline_color_override=get_token("status_warning", "#F59E0B"),
            title="Predicted Salary vs Experience",
            color_discrete_sequence=[get_colorway()[0]],
        )
        fig.update_traces(marker=dict(size=7, opacity=0.65))
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    st.caption("This landscape combines salary level and career stage in one view, so you can spot clusters, overlap, and outliers across experience.")
    fig = px.scatter(
        sampled_df,
        x="Years of Experience",
        y="Predicted Annual Salary",
        color="Estimated Salary Level",
        symbol="Career Stage",
        title="Career Progression Landscape",
        color_discrete_sequence=get_colorway_3_stages(),
    )
    fig.update_traces(marker=dict(size=9, opacity=0.65))
    apply_theme(fig)
    st.plotly_chart(fig, width="stretch")


def _render_app1_segmentation_charts(df: pd.DataFrame, apply_theme, generate_salary_leaderboard) -> None:
    country_group = (
        df.groupby("Country")["Predicted Annual Salary"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary", ascending=False)
        .head(10)
    )

    senior_group = (
        df.groupby("Senior")["Predicted Annual Salary"]
        .mean()
        .reset_index()
    )
    senior_group["Senior"] = senior_group["Senior"].map({0: "Non-Senior", 1: "Senior"})

    job_salary = df.copy()
    top_jobs = job_salary["Job Title"].value_counts().head(10).index
    job_salary = job_salary[job_salary["Job Title"].isin(top_jobs)]

    c1, c2 = st.columns(2)
    with c1:
        st.caption("This compares average predicted salary across the highest-paying countries represented in the batch.")
        fig = px.bar(
            country_group,
            x="Country",
            y="Predicted Annual Salary",
            title="Top Countries by Average Predicted Salary",
            color="Country",
            color_discrete_sequence=get_colorway()[:8],
        )
        fig.update_xaxes(categoryorder="total descending")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("This shows the average pay gap between senior and non-senior profiles in the uploaded predictions.")
        fig = px.bar(
            senior_group,
            x="Senior",
            y="Predicted Annual Salary",
            title="Average Salary by Seniority",
            color="Senior",
            color_discrete_sequence=get_colorway()[:2],
        )
        fig.update_xaxes(categoryorder="array", categoryarray=["Non-Senior", "Senior"])
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    st.dataframe(
        generate_salary_leaderboard(df, "Job Title", "Predicted Annual Salary"),
        width="stretch",
        hide_index=True,
    )
    st.caption("Top roles are ranked by average predicted salary within the uploaded batch.")

    fig = px.box(
        job_salary,
        x="Job Title",
        y="Predicted Annual Salary",
        title="Predicted Salary Distribution by Job Title",
        color="Job Title",
        color_discrete_sequence=get_colorway()[:8],
    )
    fig.update_layout(xaxis_title="Job Title", yaxis_title="Predicted Salary (USD)", showlegend=False)
    apply_theme(fig)
    st.plotly_chart(fig, width="stretch")


def _render_app2_summary_metrics(df: pd.DataFrame, EXPERIENCE_MAP) -> None:
    avg_s = df["Predicted Annual Salary (USD)"].mean()
    median_s = df["Predicted Annual Salary (USD)"].median()
    min_s = df["Predicted Annual Salary (USD)"].min()
    max_s = df["Predicted Annual Salary (USD)"].max()
    std_s = df["Predicted Annual Salary (USD)"].std()
    std_s = 0 if pd.isna(std_s) else std_s
    top_experience_code = _safe_mode_label(df["experience_level"])
    top_experience_label = EXPERIENCE_MAP.get(top_experience_code, top_experience_code)

    top_row = st.columns(4)
    top_row[0].metric("Records", f"{df.shape[0]:,}")
    top_row[1].metric("Average Salary", f"${avg_s:,.0f}")
    top_row[2].metric("Median Salary", f"${median_s:,.0f}")
    top_row[3].metric("Max Salary", f"${max_s:,.0f}")

    bottom_row = st.columns(3)
    bottom_row[0].metric("Min Salary", f"${min_s:,.0f}")
    bottom_row[1].metric("Top Experience Group", top_experience_label)
    bottom_row[2].metric("Std Deviation", f"${std_s:,.0f}")
    st.write(f"Salary range in this batch: \\${min_s:,.0f} to \\${max_s:,.0f}")


def _render_app2_overview_charts(df: pd.DataFrame, apply_theme, generate_salary_leaderboard) -> None:
    leaderboard = generate_salary_leaderboard(
        df=df,
        job_col="job_title",
        salary_col="Predicted Annual Salary (USD)",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("This histogram shows how prediction counts are spread across salary values. Taller bars mean more records fell into that salary band.")
        fig = px.histogram(
            df,
            x="Predicted Annual Salary (USD)",
            nbins=min(25, len(df)),
            title="Predicted Salary Distribution",
            color_discrete_sequence=[get_colorway()[0]],
        )
        fig.update_traces(marker_line_color=get_token("surface_overlay", "#1B2230"), marker_line_width=0.8)
        fig.update_layout(xaxis_title="Predicted Salary (USD)", yaxis_title="Count")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("Use this to compare which roles land highest on average in the current batch. It highlights role-level pay differences, not how many records each role has.")
        fig = px.bar(
            leaderboard.head(10),
            x="Average Salary (USD)",
            y="Job Title",
            orientation="h",
            title="Top Roles by Average Predicted Salary",
            color_discrete_sequence=[get_colorway()[0]],
        )
        fig.update_yaxes(categoryorder="total ascending")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    st.caption("This donut chart shows how the uploaded batch is split across work arrangements.")
    workmode_mix = (
        df["remote_ratio"]
        .map({0: "On-site", 50: "Hybrid", 100: "Fully Remote"})
        .value_counts()
        .reindex(["On-site", "Hybrid", "Fully Remote"], fill_value=0)
        .reset_index()
    )
    workmode_mix.columns = ["Work Mode", "Count"]
    fig = px.pie(
        workmode_mix,
        names="Work Mode",
        values="Count",
        hole=0.55,
        title="Work Mode Share",
        color="Work Mode",
        color_discrete_sequence=get_colorway()[:3],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    apply_theme(fig)
    st.plotly_chart(fig, width="stretch")

    st.dataframe(leaderboard, width="stretch", hide_index=True)
    st.caption("Top roles are ranked by average predicted salary within the uploaded batch.")


def _render_app2_structure_charts(df: pd.DataFrame, apply_theme, EXPERIENCE_MAP, COMPANY_SIZE_MAP, REMOTE_MAP) -> None:
    exp_group = (
        df.groupby("experience_level")["Predicted Annual Salary (USD)"]
        .mean()
        .reset_index()
    )
    exp_group["Experience Level"] = exp_group["experience_level"].map(EXPERIENCE_MAP)

    size_group = (
        df.groupby("company_size")["Predicted Annual Salary (USD)"]
        .mean()
        .reset_index()
    )
    size_group["Company Size"] = size_group["company_size"].map(COMPANY_SIZE_MAP)

    remote_group = (
        df.groupby("remote_ratio")["Predicted Annual Salary (USD)"]
        .mean()
        .reset_index()
    )
    remote_group["Work Mode"] = remote_group["remote_ratio"].map(REMOTE_MAP)

    c1, c2 = st.columns(2)
    with c1:
        st.caption("This compares the average predicted salary across experience levels from entry to executive.")
        fig = px.bar(
            exp_group,
            x="Experience Level",
            y="Predicted Annual Salary (USD)",
            title="Average Salary by Experience Level",
            color="Experience Level",
            color_discrete_sequence=get_colorway()[:4],
        )
        fig.update_xaxes(categoryorder="array", categoryarray=["Entry Level", "Mid Level", "Senior Level", "Executive Level"])
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("This compares the average predicted salary across company-size segments.")
        fig = px.bar(
            size_group,
            x="Company Size",
            y="Predicted Annual Salary (USD)",
            title="Average Salary by Company Size",
            color="Company Size",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_xaxes(categoryorder="array", categoryarray=["Small Company", "Medium Company", "Large Company"])
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    st.caption("This compares the average predicted salary across on-site, hybrid, and remote work arrangements.")
    fig = px.bar(
        remote_group,
        x="Work Mode",
        y="Predicted Annual Salary (USD)",
        title="Average Salary by Work Mode",
        color="Work Mode",
        color_discrete_sequence=get_colorway()[:3],
    )
    apply_theme(fig)
    st.plotly_chart(fig, width="stretch")


def _render_app2_location_charts(df: pd.DataFrame, apply_theme, generate_salary_leaderboard, COUNTRY_NAME_MAP) -> None:
    country_group = (
        df.groupby("company_location")["Predicted Annual Salary (USD)"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary (USD)", ascending=False)
        .head(10)
    )
    country_group["Country"] = country_group["company_location"].map(lambda x: COUNTRY_NAME_MAP.get(x, x))

    c1, c2 = st.columns(2)
    with c1:
        st.caption("This compares average predicted salary across the highest-paying company locations represented in the batch.")
        fig = px.bar(
            country_group,
            x="Country",
            y="Predicted Annual Salary (USD)",
            title="Top Countries by Average Predicted Salary",
            color="Country",
            color_discrete_sequence=get_colorway()[:8],
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("This helps compare how experience-level pay shifts across the top company locations in the batch.")
        role_country = (
            df.groupby(["company_location", "experience_level"])["Predicted Annual Salary (USD)"]
            .mean()
            .reset_index()
        )
        role_country["Country"] = role_country["company_location"].map(lambda x: COUNTRY_NAME_MAP.get(x, x))
        role_country["Experience Level"] = role_country["experience_level"]
        top_countries = country_group["company_location"].tolist()
        role_country = role_country[role_country["company_location"].isin(top_countries)]
        fig = px.bar(
            role_country,
            x="Country",
            y="Predicted Annual Salary (USD)",
            color="Experience Level",
            barmode="group",
            title="Experience Mix Across Top Company Locations",
            color_discrete_sequence=get_colorway()[:4],
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")


def _render_app1_advanced_charts(df: pd.DataFrame, apply_theme) -> None:
    st.caption("Use these views to inspect distribution shape, percentile spread, and how the main numeric fields move together.")

    career_order = ["Entry Stage", "Growth Stage", "Leadership Stage"]
    salary_level_order = ["Early Career Range", "Professional Range", "Executive Range"]
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Violin width shows where predictions are most concentrated. The inner box helps you compare the typical range and median for each salary level.")
        violin_df = df.copy()
        violin_df["Estimated Salary Level"] = pd.Categorical(
            violin_df["Estimated Salary Level"],
            categories=salary_level_order,
            ordered=True,
        )
        fig = px.violin(
            violin_df,
            x="Estimated Salary Level",
            y="Predicted Annual Salary",
            color="Estimated Salary Level",
            title="Salary Density by Salary Level",
            color_discrete_sequence=get_colorway_3_stages(),
            box=True,
            points=False,
        )
        fig.update_layout(showlegend=False)
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("The heatmap shows how strongly the numeric fields move together. Values closer to 1 or -1 indicate stronger positive or negative relationships.")
        heatmap_df = df[["Age", "Years of Experience", "Education Level", "Senior", "Predicted Annual Salary"]].copy()
        heatmap_df = heatmap_df.rename(columns={"Predicted Annual Salary": "Predicted Salary"})
        corr = heatmap_df.corr(numeric_only=True).round(2)
        fig = px.imshow(
            corr,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title="Correlation Heatmap for Core Numeric Fields",
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        st.caption("An ECDF chart shows percentile position directly. If one line rises faster at lower salaries, that segment is concentrated more heavily in the lower range.")
        fig = px.ecdf(
            df,
            y="Predicted Annual Salary",
            color="Career Stage",
            title="Cumulative Salary Distribution by Career Stage",
            color_discrete_sequence=get_colorway_3_stages(),
        )
        fig.update_layout(xaxis_title="Share of Records", yaxis_title="Predicted Salary (USD)")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c4:
        st.caption("The vertical band shows the middle spread from the 10th to 90th percentile, while the line marks the median. Wider bands mean more variation within that stage.")
        quantiles = (
            df.groupby("Career Stage")["Predicted Annual Salary"]
            .quantile([0.1, 0.5, 0.9])
            .unstack()
            .reindex(career_order)
            .reset_index()
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=quantiles["Career Stage"],
                y=quantiles[0.9] - quantiles[0.1],
                base=quantiles[0.1],
                marker_color=get_colorway()[1],
                opacity=0.35,
                name="10th to 90th percentile band",
                hovertemplate="%{x}<br>10th: $%{base:,.0f}<br>90th: $%{y:+,.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=quantiles["Career Stage"],
                y=quantiles[0.5],
                mode="lines+markers",
                marker=dict(size=9, color=get_colorway()[0]),
                line=dict(width=3, color=get_colorway()[0]),
                name="Median salary",
                hovertemplate="%{x}<br>Median: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Median Salary with 10th-90th Percentile Band",
            xaxis_title="Career Stage",
            yaxis_title="Predicted Salary (USD)",
            barmode="overlay",
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")


def _render_app2_advanced_charts(df: pd.DataFrame, apply_theme, EXPERIENCE_MAP, COMPANY_SIZE_MAP, REMOTE_MAP) -> None:
    st.caption("Use these views to inspect distribution shape, cumulative salary spread, and median differences across structural factors.")

    median_pivot = (
        df.assign(
            Experience_Level=df["experience_level"].map(EXPERIENCE_MAP),
            Company_Size=df["company_size"].map(COMPANY_SIZE_MAP),
        )
        .pivot_table(
            index="Experience_Level",
            columns="Company_Size",
            values="Predicted Annual Salary (USD)",
            aggfunc="median",
        )
        .reindex(index=["Entry Level", "Mid Level", "Senior Level", "Executive Level"])
        .reindex(columns=["Small Company", "Medium Company", "Large Company"])
    )

    exp_violin_df = df.copy()
    exp_violin_df["Experience Level"] = exp_violin_df["experience_level"].map(EXPERIENCE_MAP)
    exp_violin_df["Experience Level"] = pd.Categorical(
        exp_violin_df["Experience Level"],
        categories=["Entry Level", "Mid Level", "Senior Level", "Executive Level"],
        ordered=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.caption("Violin width shows where predictions are most concentrated. The inner box helps you compare the typical range and median for each experience level.")
        fig = px.violin(
            exp_violin_df,
            x="Experience Level",
            y="Predicted Annual Salary (USD)",
            color="Experience Level",
            title="Salary Density by Experience Level",
            color_discrete_sequence=get_colorway()[:4],
            box=True,
            points=False,
        )
        fig.update_layout(showlegend=False)
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c2:
        st.caption("This heatmap compares median salary across two dimensions at once: experience level and company size.")
        fig = px.imshow(
            median_pivot,
            text_auto=".0f",
            aspect="auto",
            color_continuous_scale="Blues",
            title="Median Salary by Experience Level and Company Size",
        )
        fig.update_coloraxes(colorbar_title="Median Salary")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        st.caption("This box plot compares salary spread across work modes. The line shows the median, and the box shows the typical middle range.")
        workmode_df = df.copy()
        workmode_df["Work Mode"] = workmode_df["remote_ratio"].map(REMOTE_MAP)
        fig = px.box(
            workmode_df,
            x="Work Mode",
            y="Predicted Annual Salary (USD)",
            color="Work Mode",
            title="Salary Distribution by Work Mode",
            color_discrete_sequence=get_colorway()[:3],
            points=False,
        )
        fig.update_layout(showlegend=False, xaxis_title="Work Mode", yaxis_title="Predicted Salary (USD)")
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")

    with c4:
        st.caption("The vertical band shows the middle spread from the 10th to 90th percentile, while the line marks the median. Wider bands mean more variation within that experience level.")
        quantiles = (
            exp_violin_df.groupby("Experience Level")["Predicted Annual Salary (USD)"]
            .quantile([0.1, 0.5, 0.9])
            .unstack()
            .reindex(["Entry Level", "Mid Level", "Senior Level", "Executive Level"])
            .reset_index()
        )
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=quantiles["Experience Level"],
                y=quantiles[0.9] - quantiles[0.1],
                base=quantiles[0.1],
                marker_color=get_colorway()[1],
                opacity=0.35,
                name="10th to 90th percentile band",
                hovertemplate="%{x}<br>10th: $%{base:,.0f}<br>90th: $%{y:+,.0f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=quantiles["Experience Level"],
                y=quantiles[0.5],
                mode="lines+markers",
                marker=dict(size=9, color=get_colorway()[0]),
                line=dict(width=3, color=get_colorway()[0]),
                name="Median salary",
                hovertemplate="%{x}<br>Median: $%{y:,.0f}<extra></extra>",
            )
        )
        fig.update_layout(
            title="Median Salary with 10th-90th Percentile Band",
            xaxis_title="Experience Level",
            yaxis_title="Predicted Salary (USD)",
            barmode="overlay",
        )
        apply_theme(fig)
        st.plotly_chart(fig, width="stretch")


def _safe_mode_label(series: pd.Series) -> str:
    if series.empty:
        return "N/A"
    mode = series.mode(dropna=True)
    if mode.empty:
        return "N/A"
    return str(mode.iloc[0])
