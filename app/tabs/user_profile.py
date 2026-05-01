from app.theme import apply_theme, get_colorway, get_token
import streamlit as st
import pandas as pd
import json
from app.core.auth import logout, get_logged_in_user
from app.core.database import get_user_predictions
import plotly.express as px
from io import BytesIO

# Account management (change password, delete account).
# Rollback: remove this import and the three render_account_management_section()
# calls below (all marked -- ROLLBACK: account_management --).
# No other changes are needed in this file.
from app.core.account_management import render_account_management_section


def _build_history_export(export_df: pd.DataFrame, export_format: str):
    if export_format == "CSV":
        return (
            export_df.to_csv(index=False).encode("utf-8"),
            "salaryscope_prediction_history.csv",
            "text/csv",
        )

    if export_format == "JSON":
        return (
            export_df.to_json(orient="records", indent=2).encode("utf-8"),
            "salaryscope_prediction_history.json",
            "application/json",
        )

    buffer = BytesIO()
    export_df.to_excel(buffer, index=False)
    return (
        buffer.getvalue(),
        "salaryscope_prediction_history.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def show_profile():
    st.header(":material/account_circle: User Profile")

    username = get_logged_in_user()

    if not username:
        st.warning("You are not logged in.")
        st.stop()

    # Account identity block
    st.markdown(
        f"""
        <div style="
            padding: 14px 18px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background-color: var(--bg-card);
            margin-bottom: 4px;
        ">
            <div style="font-size: 11px; font-weight: 600; color: var(--text-muted);
                        letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 4px;">
                Signed in as
            </div>
            <div style="font-size: 15px; font-weight: 600; color: var(--text-main);
                        word-break: break-all;">
                {username}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Review your saved prediction history, revisit past inputs, and export your records when needed.")

    st.divider()

    rows = get_user_predictions(username)

    if not rows:
        st.info("No predictions recorded yet. Run a prediction to see your history here.")

        st.divider()

        # -- ROLLBACK: account_management --
        render_account_management_section()
        # -- ROLLBACK end --

        if st.button(":material/logout: Logout", key="profile_logout_empty"):
            logout()
        return

    df = pd.DataFrame(
        rows,
        columns=[
            "Prediction ID",
            "Model",
            "Inputs",
            "Predicted Salary",
            "Date"
        ]
    )

    # --------------------------------
    # Datetime handling
    # --------------------------------
    df["DateTime"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["DateTime"])
    df = df.sort_values("DateTime").reset_index(drop=True)

    if df.empty:
        st.info("No valid prediction records found.")

        st.divider()

        # -- ROLLBACK: account_management --
        render_account_management_section()
        # -- ROLLBACK end --

        if st.button(":material/logout: Logout", key="profile_logout_invalid"):
            logout()
        return

    df["DateDisplay"] = df["DateTime"].dt.strftime("%d %b %Y, %H:%M")
    df = df.sort_values("DateTime", ascending=False).reset_index(drop=True)

    # -----------------------------
    # Dashboard Metrics
    # -----------------------------
    st.subheader(":material/insights: Prediction Summary")

    total_predictions = len(df)
    avg_salary = df["Predicted Salary"].mean()
    latest_salary = df.iloc[0]["Predicted Salary"]
    min_salary = df["Predicted Salary"].min()
    max_salary = df["Predicted Salary"].max()
    top_model = df["Model"].mode().iloc[0] if not df["Model"].mode().empty else "N/A"

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Predictions", total_predictions)
    col2.metric("Average Predicted Salary", f"${avg_salary:,.2f}")
    col3.metric("Latest Prediction", f"${latest_salary:,.2f}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Highest Prediction", f"${max_salary:,.2f}")
    col5.metric("Lowest Prediction", f"${min_salary:,.2f}")
    col6.metric("Most Used Model", top_model)

    st.divider()

    # -----------------------------
    # Filters
    # -----------------------------
    st.subheader(":material/filter_list: Filters")

    filter_cols = st.columns([1.2, 1.2, 1])
    model_options = ["All"] + sorted(df["Model"].dropna().unique().tolist())
    selected_model = filter_cols[0].selectbox("Model", model_options, key="profile_model_filter")
    history_window = filter_cols[1].selectbox(
        "History window",
        ["All records", "Latest 100", "Latest 250", "Latest 500"],
        key="profile_history_window",
    )
    show_inputs_mode = filter_cols[2].selectbox(
        "Input view",
        ["Readable list", "Raw JSON"],
        key="profile_input_view_mode",
    )

    filtered_df = df.copy()
    if selected_model != "All":
        filtered_df = filtered_df[filtered_df["Model"] == selected_model].copy()

    if history_window != "All records":
        limit = int(history_window.split()[1])
        filtered_df = filtered_df.head(limit).copy()

    if filtered_df.empty:
        st.info("No saved predictions match the current filter.")
        st.divider()

        # -- ROLLBACK: account_management --
        render_account_management_section()
        # -- ROLLBACK end --

        if st.button(":material/logout: Logout", key="profile_logout_filtered_empty"):
            logout()
        return

    filtered_total = len(filtered_df)
    filtered_avg_salary = filtered_df["Predicted Salary"].mean()
    filtered_latest_salary = filtered_df.iloc[0]["Predicted Salary"]
    filtered_min = filtered_df["Predicted Salary"].min()
    filtered_max = filtered_df["Predicted Salary"].max()

    if selected_model != "All" or history_window != "All records":
        st.caption(f"Showing {filtered_total} record(s) matching your current filters.")
        summary_cols = st.columns(3)
        summary_cols[0].metric("Visible Records", filtered_total)
        summary_cols[1].metric("Visible Average", f"${filtered_avg_salary:,.2f}")
        summary_cols[2].metric("Visible Latest", f"${filtered_latest_salary:,.2f}")
        sum2_cols = st.columns(3)
        sum2_cols[0].metric("Visible High", f"${filtered_max:,.2f}")
        sum2_cols[1].metric("Visible Low", f"${filtered_min:,.2f}")

    st.divider()

    # -----------------------------
    # Prediction History Chart
    # -----------------------------
    st.subheader(":material/show_chart: Prediction History Chart")

    df_chart = filtered_df.tail(500).sort_values("DateTime")

    colorway = get_colorway()
    color_map = {
        "Random Forest":        colorway[0],
        "XGBoost":              colorway[1],
        "Random Forest Resume": colorway[7] if len(colorway) > 7 else colorway[3],
        "XGBoost Resume":       colorway[3],
    }

    fig = px.scatter(
        df_chart,
        x="DateTime",
        y="Predicted Salary",
        color="Model",
        title="Prediction History",
        color_discrete_map=color_map,
        hover_data={"DateTime": False, "DateDisplay": True, "Predicted Salary": True, "Model": True},
    )

    fig.update_traces(
        marker=dict(
            size=10,
            opacity=0.85,
            line=dict(width=1, color="rgba(0,0,0,0.15)"),
        )
    )

    fig.update_xaxes(tickformat="%d %b\n%H:%M", nticks=6, title_text="Time")
    fig.update_yaxes(title_text="Predicted Salary (USD)")
    apply_theme(fig, extra={
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        "margin": {"l": 60, "r": 30, "t": 40, "b": 60},
    })
    st.plotly_chart(fig, width="stretch")

    st.divider()

    # -----------------------------
    # Prediction History Table
    # -----------------------------
    st.subheader(":material/history: Prediction History")

    df_display = filtered_df.copy()
    df_display["Predicted Salary"] = df_display["Predicted Salary"].apply(lambda x: f"${x:,.2f}")

    table_df = df_display[["Model", "Predicted Salary", "DateDisplay"]].rename(
        columns={"DateDisplay": "Date"}
    )

    st.dataframe(table_df.head(500), width="stretch", hide_index=True)

    st.divider()

    # -----------------------------
    # View Prediction Inputs
    # -----------------------------
    st.subheader(":material/list: View Prediction Inputs")

    selection = st.selectbox(
        "Select a prediction",
        filtered_df.index,
        format_func=lambda x: f"{filtered_df.loc[x, 'Model']}  --  {filtered_df.loc[x, 'DateDisplay']}",
        key="profile_prediction_select",
    )

    selected_row = filtered_df.loc[selection]

    try:
        inputs = json.loads(selected_row["Inputs"])
    except Exception:
        inputs = {"raw_input_data": selected_row["Inputs"]}

    st.markdown("**Input Details**")

    if show_inputs_mode == "Raw JSON":
        st.code(json.dumps(inputs, indent=2, ensure_ascii=False), language="json")
    else:
        input_rows = pd.DataFrame(
            [{"Field": key, "Value": value} for key, value in inputs.items()]
        )
        st.dataframe(input_rows, width="stretch", hide_index=True)

    st.divider()

    # -----------------------------
    # Export Prediction History
    # -----------------------------
    st.subheader(":material/download: Export Prediction History")

    export_col1, export_col2 = st.columns([1, 2])

    export_format = export_col1.selectbox(
        "Format",
        ["CSV", "XLSX", "JSON"],
        key="profile_export_format",
    )

    export_df = filtered_df.copy()

    def safe_json(x):
        try:
            return json.dumps(json.loads(x), indent=2)
        except Exception:
            return str(x)

    export_df["Inputs"] = export_df["Inputs"].apply(safe_json)
    file_data, filename, mime = _build_history_export(export_df, export_format)

    st.download_button(
        label=f"Download {export_format} ({filtered_total} record{'s' if filtered_total != 1 else ''})",
        data=file_data,
        file_name=filename,
        mime=mime,
        width="stretch",
        key=f"profile_history_download_{export_format.lower()}",
    )

    st.divider()

    # -- ROLLBACK: account_management --
    render_account_management_section()
    # -- ROLLBACK end --

    if st.button(":material/logout: Logout"):
        logout()