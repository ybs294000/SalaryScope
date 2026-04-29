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

    st.caption("Review your saved prediction history, revisit past inputs, and export your records when needed.")

    st.divider()

    rows = get_user_predictions(username)

    if not rows:
        st.info("No predictions recorded yet.")

        st.divider()

        # -- ROLLBACK: account_management --
        render_account_management_section()
        # -- ROLLBACK end --

        if st.button("Logout"):
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

        if st.button("Logout"):
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
    top_model = df["Model"].mode().iloc[0] if not df["Model"].mode().empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Account", username)
    col2.metric("Total Predictions", total_predictions)
    col3.metric("Average Predicted Salary", f"${avg_salary:,.2f}")
    col4.metric("Latest Prediction", f"${latest_salary:,.2f}")

    st.caption(f"Most used model: {top_model}")

    st.divider()

    filter_cols = st.columns([1.2, 1.2, 1])
    model_options = ["All"] + sorted(df["Model"].dropna().unique().tolist())
    selected_model = filter_cols[0].selectbox("Filter by model", model_options, key="profile_model_filter")
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
        render_account_management_section()
        if st.button(":material/logout: Logout", key="profile_logout_filtered_empty"):
            logout()
        return

    filtered_total = len(filtered_df)
    filtered_avg_salary = filtered_df["Predicted Salary"].mean()
    filtered_latest_salary = filtered_df.iloc[0]["Predicted Salary"]

    summary_cols = st.columns(3)
    summary_cols[0].metric("Visible Records", filtered_total)
    summary_cols[1].metric("Visible Average Salary", f"${filtered_avg_salary:,.2f}")
    summary_cols[2].metric("Visible Latest Salary", f"${filtered_latest_salary:,.2f}")

    st.divider()

    # -----------------------------
    # Prediction History Chart
    # -----------------------------
    st.subheader(":material/show_chart: Prediction History Chart")
    df_chart = filtered_df.tail(500).sort_values("DateTime")
    fig = px.scatter(
        df_chart,
        x="DateTime",
        y="Predicted Salary",
        color="Model",
        title="Prediction History",
        color_discrete_map={
            "Random Forest":        get_colorway()[0],
            "XGBoost":              get_colorway()[1],
            "Random Forest Resume": get_colorway()[7] if len(get_colorway()) > 7 else get_colorway()[3],
            "XGBoost Resume":       get_colorway()[3],
        }
    )

    fig.update_traces(
        marker=dict(
            size=10,
            opacity=0.85
        )
    )

    fig.update_xaxes(
        tickformat="%d %b\n%H:%M",
        nticks=6
    )
    fig.update_xaxes(title_text="Time")
    fig.update_yaxes(title_text="Predicted Salary (USD)")
    apply_theme(fig, extra={
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        "margin": {"l": 60, "r": 30, "t": 40, "b": 60},
    })
    st.plotly_chart(fig, width='stretch')

    st.divider()

    # -----------------------------
    # Prediction History Table
    # -----------------------------
    st.subheader(":material/history: Prediction History")

    df_display = filtered_df.copy()
    df_display["Predicted Salary"] = df_display["Predicted Salary"].apply(
        lambda x: f"${x:,.2f}"
    )

    table_df = df_display[
        ["Model", "Predicted Salary", "DateDisplay"]
    ].rename(columns={"DateDisplay": "Date"})

    st.dataframe(
        table_df.head(500),
        width='stretch',
        hide_index=True
    )

    st.divider()

    # -----------------------------
    # View Prediction Inputs
    # -----------------------------
    st.subheader(":material/list: View Prediction Inputs")

    selection = st.selectbox(
        "Select a prediction",
        filtered_df.index,
        format_func=lambda x: f"{filtered_df.loc[x, 'Model']} -- {filtered_df.loc[x, 'DateDisplay']}",
        key="profile_prediction_select",
    )

    selected_row = filtered_df.loc[selection]

    try:
        inputs = json.loads(selected_row["Inputs"])
    except Exception:
        inputs = {"raw_input_data": selected_row["Inputs"]}

    st.markdown("### Input Details")

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

    export_format = st.selectbox(
        "Select export format",
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
        label=f"Download {export_format} History",
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
