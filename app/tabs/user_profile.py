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


def show_profile():
    st.header(":material/account_circle: User Profile")

    username = get_logged_in_user()

    if not username:
        st.warning("You are not logged in.")
        st.stop()

    st.write("Username:", username)

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

    # -----------------------------
    # Dashboard Metrics
    # -----------------------------
    st.subheader(":material/insights: Prediction Summary")

    total_predictions = len(df)
    avg_salary = df["Predicted Salary"].mean()
    latest_salary = df.iloc[-1]["Predicted Salary"]

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Predictions", total_predictions)
    col2.metric("Average Predicted Salary", f"${avg_salary:,.2f}")
    col3.metric("Latest Prediction", f"${latest_salary:,.2f}")

    st.divider()

    # -----------------------------
    # Prediction History Chart
    # -----------------------------
    st.subheader(":material/show_chart: Prediction History Chart")
    df_chart = df.tail(500)
    fig = px.scatter(
        df_chart,
        x="DateTime",
        y="Predicted Salary",
        color="Model",
        color_discrete_map={
            "Random Forest":        "#4F8EF7",
            "XGBoost":              "#38BDF8",
            "Random Forest Resume": "#818CF8",
            "XGBoost Resume":       "#A78BFA",
        }
    )

    fig.update_traces(
        marker=dict(
            size=10,
            opacity=0.85
        )
    )

    fig.update_layout(
        paper_bgcolor="#141A22",
        plot_bgcolor="#1B2230",
        font=dict(color="#E6EAF0", family="Inter, Segoe UI, sans-serif", size=13),
        xaxis=dict(
            title="Time",
            gridcolor="#283142",
            linecolor="#283142",
            tickfont=dict(color="#9CA6B5"),
            title_font=dict(color="#9CA6B5")
        ),
        yaxis=dict(
            title="Predicted Salary (USD)",
            gridcolor="#283142",
            linecolor="#283142",
            tickfont=dict(color="#9CA6B5"),
            title_font=dict(color="#9CA6B5")
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="#141A22",
            bordercolor="#283142",
            borderwidth=1
        ),
        margin=dict(l=60, r=30, t=40, b=60)
    )

    fig.update_xaxes(
        tickformat="%d %b\n%H:%M",
        nticks=6
    )

    st.plotly_chart(fig, width='stretch')

    st.divider()

    # -----------------------------
    # Prediction History Table
    # -----------------------------
    st.subheader(":material/history: Prediction History")

    df_display = df.copy()

    df_display["Predicted Salary"] = df_display["Predicted Salary"].apply(
        lambda x: f"${x:,.2f}"
    )

    table_df = df_display[
        ["Model", "Predicted Salary", "DateDisplay"]
    ].rename(columns={"DateDisplay": "Date"})

    st.dataframe(
        table_df.tail(500),
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
        df.index,
        format_func=lambda x: f"{df.loc[x, 'Model']} -- {df.loc[x, 'DateDisplay']}"
    )

    selected_row = df.loc[selection]

    try:
        inputs = json.loads(selected_row["Inputs"])
    except Exception:
        inputs = {"raw_input_data": selected_row["Inputs"]}

    st.markdown("### Input Details")

    for key, value in inputs.items():
        st.write(f"{key}: {value}")

    st.divider()

    # -----------------------------
    # Export Prediction History
    # -----------------------------
    st.subheader(":material/download: Export Prediction History")

    export_format = st.selectbox(
        "Select export format",
        ["CSV", "XLSX", "JSON"]
    )

    if "history_file" not in st.session_state:
        st.session_state.history_file = None
        st.session_state.history_filename = None
        st.session_state.history_mime = None

    if st.button("Prepare Download File"):

        export_df = df.copy()

        def safe_json(x):
            try:
                return json.dumps(json.loads(x), indent=2)
            except Exception:
                return str(x)

        export_df["Inputs"] = export_df["Inputs"].apply(safe_json)

        if export_format == "CSV":
            file_data = export_df.to_csv(index=False).encode("utf-8")
            filename = "salaryscope_prediction_history.csv"
            mime = "text/csv"

        elif export_format == "JSON":
            file_data = export_df.to_json(orient="records", indent=2).encode("utf-8")
            filename = "salaryscope_prediction_history.json"
            mime = "application/json"

        else:
            buffer = BytesIO()
            export_df.to_excel(buffer, index=False)
            file_data = buffer.getvalue()
            filename = "salaryscope_prediction_history.xlsx"
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        st.session_state.history_file = file_data
        st.session_state.history_filename = filename
        st.session_state.history_mime = mime

        st.success("File prepared. You can now download it.")

    if st.session_state.history_file is not None:
        st.download_button(
            label="Download Prediction History",
            data=st.session_state.history_file,
            file_name=st.session_state.history_filename,
            mime=st.session_state.history_mime
        )

    # -- ROLLBACK: account_management --
    render_account_management_section()
    # -- ROLLBACK end --

    if st.button(":material/logout: Logout"):
        logout()