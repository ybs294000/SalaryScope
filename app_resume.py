import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import re
import ast
import requests
from io import BytesIO
from urllib.parse import urlparse, parse_qs
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64
from pdf_utils import (
    app1_generate_manual_pdf,
    app1_generate_resume_pdf,
    app1_generate_bulk_pdf,
    app1_generate_scenario_pdf,
    cached_app1_model_analytics_pdf,

    app2_generate_manual_pdf,
    app2_generate_resume_pdf,
    app2_generate_bulk_pdf,
    app2_generate_scenario_pdf,
    cached_app2_model_analytics_pdf
)
from insights_engine import generate_insights_app2, generate_insights_app1

from recommendations import (
    generate_recommendations_app1,
    generate_recommendations_app2,
    render_recommendations
)

from negotiation_tips import (
    generate_negotiation_tips_app1,
    generate_negotiation_tips_app2,
    render_negotiation_tips
)
from resume_nlp import (
    extract_text_from_pdf,
    extract_resume_features,
    calculate_resume_score,
    education_label,

    extract_resume_features_a2, 
    calculate_resume_score_a2, 
    APP2_ALLOWED_ISO_CODES_A2
)
from feedback import feedback_ui

from currency_utils import render_currency_converter, get_active_currency, get_active_rates
from tax_utils import render_tax_adjuster
from col_utils import render_col_adjuster

from auth import login_ui, register_ui, logout, get_logged_in_user
from auth import is_admin
from admin_panel import show_admin_panel

from user_profile import show_profile
from database import init_db, create_prediction_table, save_prediction
from database import delete_expired_sessions
if "db_initialized" not in st.session_state:
    init_db()
    create_prediction_table()
    st.session_state.db_initialized = True
# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="SalaryScope",
    layout="wide",
    #page_icon="SalaryScope_Icon.png"
)
# ============================================================
# DARK PROFESSIONAL — App 1 Theme (applied globally)
# ============================================================
st.markdown(
    """
    <style>

    /* ── Root palette — Dark Professional ── */
    :root {
        --primary:   #3E7DE0;
        --primary-hover:#2F6CD0;
        --bg-main:   #0C1118;
        --bg-card:   #141A22;
        --bg-input:  #1B2230;
        --border:    #283142;
        --text-main: #E6EAF0;
        --text-muted:#9CA6B5;
        --success:   #22C55E;
        --warning:   #F59E0B;
        --error:     #EF4444;
    }

    /* ── App background ── */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-main) !important;
        color: var(--text-main) !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: var(--bg-card) !important;
        border-right: 1px solid var(--border) !important;
    }

    /* ── Titles ── */
    h1 {
        color: var(--primary) !important;
        letter-spacing: -0.5px;
    }

    h2, h3 { color: var(--text-main) !important; }
    h4, h5, h6 { color: var(--text-muted) !important; }

    p, li, span, div {
        color: var(--text-main) !important;
    }

    /* ── Tabs container ── */
    [data-baseweb="tab-list"] {
        background-color: var(--bg-card) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        gap: 12px !important;
        border: 1px solid var(--border) !important;
    }

    button[data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 6px !important;
        color: var(--text-muted) !important;
        transition: color 0.2s ease !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {
        font-size: 17px !important;
        font-weight: 500 !important;
    }

    /* ── Inputs ── */
    /*.stTextInput > div > div,*/
    .stNumberInput > div > div,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--text-main) !important;
    }
  

    /*.stTextInput input,*/
    .stNumberInput input {
        background-color: var(--bg-input) !important;
        color: var(--text-main) !important;
    }

    /*.stTextInput > div > div:focus-within,*/
    .stNumberInput > div > div:focus-within,
    .stSelectbox > div > div:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 2px rgba(62,125,224,0.25) !important;
    }


    /* ── Labels ── */
    label, .stLabel, [data-testid="stWidgetLabel"] {
        color: var(--text-muted) !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    /* ── Primary buttons ── */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid*="primary"] {
        background-color: var(--primary) !important;
        border: none !important;
        border-radius: 6px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: background-color 0.2s ease !important;
    }

    .stButton > button[kind="primary"]:hover {
        background-color: var(--primary-hover) !important;
    }

    /* ── Secondary / download buttons ── */
    .stButton > button,
    .stDownloadButton > button {
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--text-main) !important;
        font-weight: 500 !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 14px 18px !important;
    }

    [data-testid="stMetricLabel"] { color: var(--text-muted) !important; }
    [data-testid="stMetricValue"] { color: var(--primary) !important; font-weight: 700 !important; }


    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background-color: var(--bg-card) !important;
        border: 2px dashed var(--border) !important;
        border-radius: 8px !important;
        padding: 16px 18px !important;
    }

    [data-testid="stFileUploader"] > div {
        margin-top: 6px !important;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--primary) !important;
    }

    /* ── Divider ── */
    hr {
        border-color: var(--border) !important;
        opacity: 0.7 !important;
    }

    /* ── Caption ── */
    .stCaption, small { color: var(--text-muted) !important; }

    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# Custom Plotly Theme (from App 1)
# --------------------------------------------------
_BG_CARD    = "#141A22"
_BG_INPUT   = "#1B2230"
_BORDER     = "#283142"
_TEXT_MAIN  = "#E6EAF0"
_TEXT_MUTED = "#9CA6B5"

_COLORWAY = [
    "#4F8EF7",
    "#38BDF8",
    "#34D399",
    "#A78BFA",
    "#F59E0B",
    "#FB923C",
    "#F472B6",
    "#22D3EE",
]

_MODEL_COLORS = ["#6EB3FF", "#4F8EF7", "#3366CC", "#1E4799", "#0F2A5C"]

_BASE_LAYOUT = dict(
    paper_bgcolor=_BG_CARD,
    plot_bgcolor=_BG_INPUT,
    font=dict(color=_TEXT_MAIN, family="Inter, Segoe UI, sans-serif", size=13),
    title=dict(font=dict(color=_TEXT_MAIN, size=16)),
    colorway=_COLORWAY,
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


def _apply_theme(fig, extra=None):
    """Inline the dark theme into a plotly figure."""
    layout = dict(_BASE_LAYOUT)
    if extra:
        layout.update(extra)
    fig.update_layout(**layout)
    return fig

# ==================================================
# CAREER CLUSTER FEATURE ENGINEERING
# Required to load clustering pipeline
# ==================================================

def add_career_score(X):

    X = X.copy()

    X["Career Score"] = (
        X["Years of Experience"] +
        (X["Education Level"] * 2)
    )

    return X[
        [
            "Years of Experience",
            "Education Level",
            "Career Score"
        ]
    ]
# ==================================================
# MODEL LOADING — App 1 (RF Regressor + Classifier)
# ==================================================
@st.cache_resource
def load_app1_model_package():
    return joblib.load("model/rf_model_grid.pkl")

@st.cache_resource
def load_app1_classifier_package():
    return joblib.load("model/salary_band_classifier.pkl")

@st.cache_resource
def load_app1_cluster_package():
    return joblib.load("model/career_cluster_pipeline.pkl")
# ==================================================
# MODEL LOADING — App 2 (XGBoost)
# ==================================================
@st.cache_resource
def load_app2_model():
    package = joblib.load("model/salaryscope_3755_production_model.pkl")
    return package["model"], package["metadata"]

# ==================================================
# DATASET LOADING
# ==================================================
@st.cache_data
def load_app1_dataset():
    return pd.read_csv("data/Salary_Streamlit_App.csv")

@st.cache_data
def load_app2_dataset():
    df2 = pd.read_csv("data/ds_salaries_Streamlit_App.csv")
    drop_cols = [c for c in ["salary", "salary_currency", "work_year"] if c in df2.columns]
    df2 = df2.drop(drop_cols, axis=1)
    return df2
# ==================================================
# ASSOCIATION RULES LOADING (APP 1)
# ==================================================
@st.cache_data
def load_association_rules_a1_v2():
    df = pd.read_csv("data/association_rules.csv")

    def parse_itemset(val):
        parsed = ast.literal_eval(val)
        # Convert to sorted comma-joined string — fully hashable by pandas
        return "|".join(sorted([str(x) for x in parsed]))

    df["antecedents"] = df["antecedents"].apply(parse_itemset)
    df["consequents"] = df["consequents"].apply(parse_itemset)
    return df
# ==================================================
# ANALYTICS LOADING — App 1 (Precomputed Tab3 Data)
# ==================================================
@st.cache_resource
def load_app1_analytics():
    import pickle
    with open("model/app1_analytics.pkl", "rb") as f:
        return pickle.load(f)
# ==================================================
# APP 2 ANALYTICS LOADER (PICKLE)
# ==================================================
@st.cache_data
def load_app2_analytics():
    import pickle
    with open("model/app2_analytics.pkl", "rb") as f:
        return pickle.load(f)
# ================================================
#   APP LOGO
# ================================================
@st.cache_data
def get_base64_image(path):
    with open(path, "rb") as img:
        return base64.b64encode(img.read()).decode()

logo_base64 = get_base64_image("static/android-chrome-512x512.png")
# ================================================
#
# ================================================
@st.cache_data
def prepare_app1_dropdowns(df_app1):
    job_titles = sorted(df_app1["Job Title"].dropna().value_counts().head(40).index.tolist())
    countries = sorted(df_app1["Country"].dropna().unique().tolist())
    if "Other" not in countries:
        countries.append("Other")
    genders = sorted(df_app1["Gender"].dropna().unique())
    return job_titles, countries, genders
# ================================================
#
# =================================================
@st.cache_data
def prepare_app2_dropdowns(df_app2):
    job_titles = sorted(df_app2["job_title"].dropna().value_counts().head(60).index.tolist())
    countries = sorted(df_app2["company_location"].dropna().unique().tolist())
    if "Other" not in countries:
        countries.append("Other")
    experience_levels = sorted(df_app2["experience_level"].dropna().unique().tolist())
    employment_types = sorted(df_app2["employment_type"].dropna().unique().tolist())
    company_sizes = sorted(df_app2["company_size"].dropna().unique().tolist())
    remote_ratios = sorted(df_app2["remote_ratio"].dropna().unique().tolist())
    return (
        job_titles,
        countries,
        experience_levels,
        employment_types,
        company_sizes,
        remote_ratios,
    )

# ==================================================
# LOAD EVERYTHING OLD
# ==================================================

df_app1 = load_app1_dataset()
df_app2 = load_app2_dataset()
#assoc_rules_a1 = load_association_rules_a1()
assoc_rules_a1_v2 = load_association_rules_a1_v2()

# App1 dropdown options
app1_job_titles, app1_countries, app1_genders = prepare_app1_dropdowns(df_app1)

#App2 dropdown options
(
    app2_job_titles,
    app2_countries,
    app2_experience_levels,
    app2_employment_types,
    app2_company_sizes,
    app2_remote_ratios
) = prepare_app2_dropdowns(df_app2)

# --------------------------------------------------
# App 1 — Static Model Comparison
# --------------------------------------------------
APP1_MODEL_COMPARISON = [
    {
        "Model": "Linear Regression",
        "MAE": 16884.376635,
        "RMSE": 23008.684282,
        "Test R²": 0.799584
    },
    {
        "Model": "Decision Tree Regression",
        "MAE": 13973.727758,
        "RMSE": 19079.721423,
        "Test R²": 0.862186
    },
    {
        "Model": "Gradient Boosting Regression",
        "MAE": 12405.046692,
        "RMSE": 16871.279240,
        "Test R²": 0.892243
    },
    {
        "Model": "XGBoost (GridSearchCV)",
        "MAE": 5861.980002,
        "RMSE": 10337.127946,
        "Test R²": 0.959547
    },
    {
        "Model": "Random Forest (GridSearchCV)",
        "MAE": 4926.799420,
        "RMSE": 9760.508203,
        "Test R²": 0.963934
    }
]

APP1_CLASSIFIER_MODEL_COMPARISON = [
    {
        "Model": "Logistic Regression",
        "Accuracy": 0.888241,
        "Precision": 0.887198,
        "Recall": 0.887834,
        "F1 Score": 0.887355
    },
    {
        "Model": "Decision Tree",
        "Accuracy": 0.948494,
        "Precision": 0.948465,
        "Recall": 0.948308,
        "F1 Score": 0.948118
    },
    {
        "Model": "Random Forest",
        "Accuracy": 0.958212,
        "Precision": 0.958104,
        "Recall": 0.958129,
        "F1 Score": 0.958005
    },
    {
        "Model": "XGBoost",
        "Accuracy": 0.963071,
        "Precision": 0.962977,
        "Recall": 0.962966,
        "F1 Score": 0.962846
    },
    {
        "Model": "HistGradientBoosting (Final Model)",
        "Accuracy": 0.965986,
        "Precision": 0.965955,
        "Recall": 0.965887,
        "F1 Score": 0.965795
    }
]
# --------------------------------------------------
# App 2 — Static Model Comparison
# --------------------------------------------------
APP2_MODEL_COMPARISON = [
    {
        "Model": "Linear Regression (Raw)",
        "Test R²": 0.3486,
        "MAE": 40169,
        "RMSE": 53380
    },
    {
        "Model": "Gradient Boosting (Raw)",
        "Test R²": 0.3989,
        "MAE": 38921,
        "RMSE": 51278
    },
    {
        "Model": "Random Forest (Log)",
        "Test R²": 0.5759,
        "MAE": 37878,
        "RMSE": 51768
    },
    {
        "Model": "XGBoost (Log)",
        "Test R²": 0.5944,
        "MAE": 37668,
        "RMSE": 51505
    },
    {
        "Model": "XGBoost (Raw + Engineered)",
        "Test R²": 0.5949,
        "MAE": 35913,
        "RMSE": 48774
    }
]
# --------------------------------------------------
# App 2 — Human-readable mappings
# --------------------------------------------------
EXPERIENCE_MAP = {
    "EN": "Entry Level",
    "MI": "Mid Level",
    "SE": "Senior Level",
    "EX": "Executive Level"
}
EMPLOYMENT_MAP = {
    "FT": "Full Time",
    "PT": "Part Time",
    "CT": "Contract",
    "FL": "Freelance"
}
COMPANY_SIZE_MAP = {
    "S": "Small Company",
    "M": "Medium Company",
    "L": "Large Company"
}
REMOTE_MAP = {
    0: "On-site",
    50: "Hybrid",
    100: "Fully Remote"
}
COUNTRY_NAME_MAP = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada",
    "ES": "Spain", "IN": "India", "DE": "Germany", "FR": "France",
    "BR": "Brazil", "GR": "Greece", "PT": "Portugal", "AU": "Australia",
    "NL": "Netherlands", "MX": "Mexico", "IE": "Ireland", "SG": "Singapore",
    "AT": "Austria", "JP": "Japan", "NG": "Nigeria", "PL": "Poland",
    "CH": "Switzerland", "TR": "Turkey", "IT": "Italy", "SI": "Slovenia",
    "CO": "Colombia", "UA": "Ukraine", "BE": "Belgium", "PR": "Puerto Rico",
    "DK": "Denmark", "PK": "Pakistan", "LV": "Latvia", "AR": "Argentina",
    "FI": "Finland", "CZ": "Czech Republic", "RU": "Russia", "TH": "Thailand",
    "HR": "Croatia", "LU": "Luxembourg", "AS": "American Samoa",
    "AE": "United Arab Emirates", "IL": "Israel", "ID": "Indonesia",
    "CF": "Central African Republic", "GH": "Ghana", "SE": "Sweden",
    "LT": "Lithuania", "EE": "Estonia", "KE": "Kenya", "RO": "Romania",
    "HU": "Hungary", "HK": "Hong Kong", "MA": "Morocco",
    "BA": "Bosnia and Herzegovina", "VN": "Vietnam", "MK": "North Macedonia",
    "AM": "Armenia", "CR": "Costa Rica", "BO": "Bolivia", "SK": "Slovakia",
    "IR": "Iran", "BS": "Bahamas", "AL": "Albania", "EG": "Egypt",
    "MY": "Malaysia", "PH": "Philippines", "HN": "Honduras", "DZ": "Algeria",
    "IQ": "Iraq", "CN": "China", "NZ": "New Zealand", "CL": "Chile",
    "MD": "Moldova", "MT": "Malta"
}
COUNTRY_NAME_MAP.update({
    "UZ": "Uzbekistan",
    "CY": "Cyprus",
    "KW": "Kuwait",
    "DO": "Dominican Republic",
    "TN": "Tunisia",
    "BG": "Bulgaria",
    "JE": "Jersey",
    "RS": "Serbia"
})
EXPERIENCE_REVERSE = {v: k for k, v in EXPERIENCE_MAP.items()}
EMPLOYMENT_REVERSE = {v: k for k, v in EMPLOYMENT_MAP.items()}
COMPANY_SIZE_REVERSE = {v: k for k, v in COMPANY_SIZE_MAP.items()}
REMOTE_REVERSE = {v: k for k, v in REMOTE_MAP.items()}


app2_country_display_options = []
for code in app2_countries:
    name = COUNTRY_NAME_MAP.get(code)
    if name:
        app2_country_display_options.append(f"{name} ({code})")
    else:
        app2_country_display_options.append(code)

app2_employee_residence_codes = sorted(df_app2["employee_residence"].dropna().unique().tolist())
app2_employee_residence_display_options = []
for code in app2_employee_residence_codes:
    name = COUNTRY_NAME_MAP.get(code)
    if name:
        app2_employee_residence_display_options.append(f"{name} ({code})")
    else:
        app2_employee_residence_display_options.append(code)
if "Other" not in app2_employee_residence_display_options:
    app2_employee_residence_display_options.append("Other")
# --------------------------------------------------
# App 1 — Salary Band Labels
# --------------------------------------------------
SALARY_BAND_LABELS = {
    "Low": "Early Career Range",
    "Medium": "Professional Range",
    "High": "Executive Range"
}

# --------------------------------------------------
# App 1 — Required Columns for Batch
# --------------------------------------------------
APP1_REQUIRED_COLUMNS = [
    "Age", "Years of Experience", "Education Level",
    "Senior", "Gender", "Job Title", "Country"
]

# --------------------------------------------------
# App 2 — Required Columns for Batch
# --------------------------------------------------
APP2_REQUIRED_COLUMNS = [
    "experience_level", "employment_type", "job_title",
    "employee_residence", "remote_ratio", "company_location", "company_size"
]

# --------------------------------------------------
# App 2 — Feature engineering helpers
# --------------------------------------------------
def normalize_title(s):
    if pd.isna(s):
        return ""
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9\s\+]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def title_features(title):
    t = normalize_title(title)
    junior = int(any(k in t for k in ["intern", "jr", "junior", "entry"]))
    senior = int(any(k in t for k in ["senior", "sr", "staff", "lead", "principal"]))
    exec_  = int(any(k in t for k in ["head", "director", "vp", "chief"]))
    is_mgmt = int(any(k in t for k in ["manager", "head", "director", "vp", "chief", "lead"]))
    domain = "other"
    if any(k in t for k in ["analyst", "analytics"]):
        domain = "analytics"
    if any(k in t for k in ["data engineer", "etl", "pipeline"]):
        domain = "data_eng"
    if any(k in t for k in ["data scientist", "scientist"]):
        domain = "scientist"
    if any(k in t for k in ["machine learning", "ml engineer", "mlops"]):
        domain = "ml_ai"
    return junior, senior, exec_, is_mgmt, domain

def clean_feature_name(feature):
    feature = feature.replace("cat__", "").replace("num__", "")
    parts = feature.split("_")
    if feature.startswith("employee_residence_"):
        return f"Employee Residence: {parts[-1]}"
    if feature.startswith("company_location_"):
        return f"Company Location: {parts[-1]}"
    if feature.startswith("experience_level_"):
        level_map = {"EN": "Entry", "MI": "Mid", "SE": "Senior", "EX": "Executive"}
        return f"Experience Level: {level_map.get(parts[-1], parts[-1])}"
    if feature.startswith("company_size_"):
        size_map = {"S": "Small", "M": "Medium", "L": "Large"}
        return f"Company Size: {size_map.get(parts[-1], parts[-1])}"
    if feature.startswith("remote_ratio_"):
        remote_map = {"0": "On-site", "50": "Hybrid", "100": "Remote"}
        return f"Work Mode: {remote_map.get(parts[-1], parts[-1])}"
    if feature == "title_is_senior":
        return "Title Indicates Senior Role"
    if feature == "title_is_junior":
        return "Title Indicates Junior Role"
    if feature == "title_is_exec":
        return "Title Indicates Executive Role"
    if feature == "title_is_mgmt":
        return "Title Indicates Management Role"
    if feature.startswith("title_domain_"):
        domain_map = {"ml_ai": "ML / AI", "scientist": "Data Scientist",
                      "analytics": "Analytics", "data_eng": "Data Engineering", "other": "Other Domain"}
        return f"Job Domain: {domain_map.get(parts[-1], parts[-1])}"
    return feature.replace("_", " ").title()

# =================================================
#
# =================================================
@st.cache_data
def prepare_app2_analytics_input(df):
    data_full = df.copy()

    drop_cols = [c for c in ["salary", "salary_currency", "work_year"] if c in data_full.columns]
    data_full = data_full.drop(drop_cols, axis=1)

    y_true = data_full["salary_in_usd"]
    X_full = data_full.drop("salary_in_usd", axis=1)

    tf_full = X_full["job_title"].apply(title_features)
    tf_full = pd.DataFrame(
        tf_full.tolist(),
        columns=[
            "title_is_junior",
            "title_is_senior",
            "title_is_exec",
            "title_is_mgmt",
            "title_domain"
        ]
    )

    X_full = pd.concat([X_full.reset_index(drop=True), tf_full.reset_index(drop=True)], axis=1)

    for col_r in ["title_is_exec", "title_is_mgmt", "title_is_junior", "title_is_senior", "title_domain"]:
        if col_r not in X_full.columns:
            X_full[col_r] = 0 if col_r != "title_domain" else "unknown"

    X_full["exp_x_domain"] = X_full["experience_level"].astype(str) + "_" + X_full["title_domain"].astype(str)
    X_full.columns = X_full.columns.astype(str)

    return X_full, y_true

# -------------------------------------------------
# Random Sampler
# --------------------------------------------------
def get_plot_df(df, max_points=2000):
    if len(df) > max_points:
        return df.sample(max_points, random_state=42)
    return df

# ==================================================
# REUSABLE LEADERBOARD GENERATOR
# ==================================================
def generate_salary_leaderboard(
    df,
    job_col,
    salary_col,
    min_records=2,
    top_n=10
):
    """
    Generates ranked leaderboard of job roles by average salary.

    Parameters:
    - df: DataFrame
    - job_col: column name for job titles
    - salary_col: column name for salary
    - min_records: minimum records per job (for reliability)
    - top_n: number of top rows to return
    """

    # Group and aggregate
    role_avg = (
        df.groupby(job_col, as_index=False)
        .agg(
            Average_Salary_USD=(salary_col, "mean"),
            Records=(job_col, "count")
        )
    )

    # Reliability filter
    role_avg = role_avg[role_avg["Records"] >= min_records].copy()

    # Sort descending
    role_avg = role_avg.sort_values(
        by="Average_Salary_USD",
        ascending=False
    ).reset_index(drop=True)

    # Rank
    role_avg["Rank"] = range(1, len(role_avg) + 1)

    # Medal logic
    def add_medal(rank, title):
        if rank == 1:
            return f"{title} \U0001F947"
        elif rank == 2:
            return f"{title} \U0001F948"
        elif rank == 3:
            return f"{title} \U0001F949"
        return title

    role_avg["Job Title"] = role_avg.apply(
        lambda row: add_medal(row["Rank"], row[job_col]),
        axis=1
    )

    # Final formatting
    leaderboard = role_avg.head(top_n).copy()
    leaderboard["Average Salary (USD)"] = leaderboard["Average_Salary_USD"].round(2)

    leaderboard = leaderboard[
        ["Rank", "Job Title", "Average Salary (USD)", "Records"]
    ]

    return leaderboard
# ==================================================
# ASSOCIATION FUNCTIONS (APP 1)
# ==================================================
def get_assoc_insight_a1(education, experience, country, job_group, predicted_salary, rules):

    def extract_salary(consequents):
        for item in consequents:
            if "Salary_Category" in item:
                return item.replace("Salary_Category_", "")
        return None

    def clean(x):
        return (
            x.replace("Education_Category_", "")
             .replace("Experience_Category_", "")
             .replace("Salary_Category_", "")
             .replace("Job_Group_", "")
             .replace("Country_", "")
             .replace("_", " ")
        )

    best_rule = None
    best_conf = 0

    # ==============================
    # STEP 1: EXACT MATCH (with country)
    # ==============================
    if country != "Other":
        for _, row in rules.iterrows():
            #ant = list(row["antecedents"])
            ant = row["antecedents"].split("|")

            #cons = list(row["consequents"])
            cons = row["consequents"].split("|")

            if (
                f"Education_Category_{education}" in ant and
                f"Experience_Category_{experience}" in ant and
                f"Job_Group_{job_group}" in ant and
                f"Country_{country}" in ant and
                f"Salary_Category_{predicted_salary}" in cons
            ):
                conf = round(row["confidence"] * 100, 2)

                return (
                    f"Professionals with {clean(experience)} experience, working in {clean(job_group)} roles "
                    f"and holding {clean(education)} education in {clean(country)} are strongly associated with "
                    f"{clean(predicted_salary)} salary levels. "
                    f"This pattern shows a high reliability with a confidence of {conf}%, indicating a consistent trend in the dataset."
                )

    # ==============================
    # STEP 2: FALLBACK (ignore country)
    # ==============================
    for _, row in rules.iterrows():
        #ant = list(row["antecedents"])
        ant = row["antecedents"].split("|")

        #cons = list(row["consequents"])
        cons = row["consequents"].split("|")

        if (
            f"Education_Category_{education}" in ant and
            f"Experience_Category_{experience}" in ant and
            f"Job_Group_{job_group}" in ant
        ):
            if row["confidence"] > best_conf:
                best_conf = row["confidence"]
                best_rule = row

    if best_rule is not None:
        salary = extract_salary(best_rule["consequents"])
        conf = round(best_conf * 100, 2)

        return (
            f"{clean(experience)}-level professionals in {clean(job_group)} roles with "
            f"{clean(education)} education are most frequently associated with {clean(salary)} salary ranges. "
            f"The rule has a confidence of {conf}%, suggesting a strong and reliable relationship between these attributes."
        )

    # ==============================
    # STEP 3: MINIMAL (experience only)
    # ==============================
    for _, row in rules.iterrows():
        #ant = list(row["antecedents"])
        ant = row["antecedents"].split("|")

        #cons = list(row["consequents"])
        cons = row["consequents"].split("|")

        if f"Experience_Category_{experience}" in ant:
            salary = extract_salary(cons)

            return (
                f"Based on observed patterns, {clean(experience)}-level professionals tend to fall within "
                f"{clean(salary)} salary ranges. This reflects general trends associated with career progression."
            )

    return "No strong association pattern was found for the selected combination."


# ==================================================
# ASSOCIATION FUNCTIONS (IMPROVED VERSION)
# ==================================================
def get_assoc_insight_a1_improved(
    education,
    experience,
    country,
    job_group,
    predicted_salary,
    rules,
    years_experience=None   # <-- NEW (pass from app.py)
):

    def extract_salary(consequents):
        for item in consequents:
            if "Salary_Category" in item:
                return item.replace("Salary_Category_", "")
        return None

    def clean(x):
        return (
            x.replace("Education_Category_", "")
             .replace("Experience_Category_", "")
             .replace("Salary_Category_", "")
             .replace("Job_Group_", "")
             .replace("Country_", "")
             .replace("_", " ")
        )

    # ============================================
    # SANITY FILTER
    # ============================================
    def is_unrealistic(rule_salary, experience, country, education):

        if rule_salary == "Low":
            if experience == "Senior" and (country == "USA" or education in ["Master", "PhD"]):
                return True

        if rule_salary == "Low" and experience == "Mid":
            return True

        return False

    # ============================================
    # STEP 1: FILTER RULES
    # ============================================
    candidates = []

    for _, row in rules.iterrows():

        if row["confidence"] < 0.5:
            continue
        if row["lift"] < 1.1:
            continue
        if row["support"] < 0.02:
            continue

        #ant = list(row["antecedents"])
        ant = row["antecedents"].split("|")

        match_score = 0

        if f"Education_Category_{education}" in ant:
            match_score += 1
        if f"Experience_Category_{experience}" in ant:
            match_score += 2
        if f"Job_Group_{job_group}" in ant:
            match_score += 1
        if country != "Other" and f"Country_{country}" in ant:
            match_score += 1

        if match_score > 0:
            candidates.append((row, match_score))

    if not candidates:
        return (
            f"Based on general dataset patterns, {clean(experience)}-level professionals "
            f"show structured salary progression trends depending on role and experience."
        )

    # ============================================
    # STEP 2: BEST RULE
    # ============================================
    best_rule = None
    best_score = -1

    for row, match_score in candidates:

        score = (
            match_score * 3 +
            row["confidence"] * 2 +
            row["lift"] * 1.5 +
            row["support"] -
            (0.1 * len(row["antecedents"]))
        )

        if score > best_score:
            best_score = score
            best_rule = row

    # ============================================
    # STEP 3: ALIGN WITH MODEL
    # ============================================
    aligned_rule = None
    best_align_score = -1

    for row, match_score in candidates:

        #cons = list(row["consequents"])
        cons = row["consequents"].split("|")

        salary = extract_salary(cons)

        if salary != predicted_salary:
            continue

        if is_unrealistic(salary, experience, country, education):
            continue

        score = (
            match_score * 3 +
            row["confidence"] * 2 +
            row["lift"] +
            row["support"]
        )

        if score > best_align_score:
            best_align_score = score
            aligned_rule = row

    # ============================================
    # STEP 4: FINAL RULE
    # ============================================
    if extract_salary(best_rule["consequents"]) == predicted_salary:
        final_rule = best_rule
    elif aligned_rule is not None:
        final_rule = aligned_rule
    else:
        final_rule = best_rule

    # ============================================
    # STEP 5: FINAL SANITY CHECK
    # ============================================
    final_salary = extract_salary(final_rule["consequents"])

    contradiction = is_unrealistic(final_salary, experience, country, education)

    # ADD THIS CONDITION
    if experience == "Senior" and final_salary != "High":
        contradiction = True

    if contradiction:

        fallback_rule = None
        fallback_score = -1

        for row, match_score in candidates:

            #cons = list(row["consequents"])
            cons = row["consequents"].split("|")

            salary = extract_salary(cons)

            if is_unrealistic(salary, experience, country, education):
                continue

            score = (
                match_score * 3 +
                row["confidence"] * 2 +
                row["lift"] +
                row["support"]
            )

            if score > fallback_score:
                fallback_score = score
                fallback_rule = row

        if fallback_rule is not None:
            final_rule = fallback_rule
            final_salary = extract_salary(final_rule["consequents"])
            contradiction = False
        else:
            return (
                f"{clean(experience)}-level professionals in {clean(job_group)} roles "
                f"typically follow structured salary progression patterns influenced by experience and role."
            )

    # ============================================
    # STEP 6: OUTPUT (NUMERIC FIX HERE)
    # ============================================
    #cons = list(final_rule["consequents"])
    cons = final_rule["consequents"].split("|")

    rule_salary = extract_salary(cons)
    conf = round(final_rule["confidence"] * 100, 2)

    # CORE IDEA IMPLEMENTED HERE
    if contradiction and years_experience is not None:
        exp_text = f"professionals with {years_experience:.1f} years of experience"
    else:
        exp_text = f"{clean(experience)}-level professionals"

    job_text = clean(job_group)
    edu_text = clean(education)
    country_text = clean(country) if country != "Other" else None

    if country_text:
        return (
            f"{exp_text} in {job_text} roles with {edu_text} education "
            f"in {country_text} are most frequently associated with {clean(rule_salary)} salary ranges. "
            f"The rule shows a confidence of {conf}%, indicating a strong and reliable relationship."
        )
    else:
        return (
            f"{exp_text} in {job_text} roles with {edu_text} education "
            f"are most frequently associated with {clean(rule_salary)} salary ranges. "
            f"The rule shows a confidence of {conf}%, indicating a strong and reliable relationship."
        )
# --------------------------------------------------
# Helper: Convert Google Drive link
# --------------------------------------------------
def convert_drive_link(url):
    if "drive.google.com" not in url:
        return None
    parsed = urlparse(url)
    if "file/d/" in url:
        file_id = url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    query = parse_qs(parsed.query)
    if "id" in query:
        return f"https://drive.google.com/uc?export=download&id={query['id'][0]}"
    return None

# ==================================================
# APP 1 — Batch Validation
# ==================================================
def app1_validate_bulk_dataframe(bulk_df):
    if bulk_df is None or bulk_df.empty:
        return False, "The uploaded file is empty. Please upload a valid file with data."
    missing_cols = [col for col in APP1_REQUIRED_COLUMNS if col not in bulk_df.columns]
    if missing_cols:
        return False, (
            "Missing required columns:\n\n"
            f"{', '.join(missing_cols)}\n\n"
            "Please ensure your file contains all required fields."
        )
    bulk_df = bulk_df[APP1_REQUIRED_COLUMNS].copy()
    numeric_columns = ["Age", "Years of Experience", "Education Level", "Senior"]
    for col in numeric_columns:
        try:
            bulk_df[col] = pd.to_numeric(bulk_df[col])
        except Exception:
            return False, f"Column '{col}' must contain only numeric values."
    if not bulk_df["Senior"].isin([0, 1]).all():
        return False, "Column 'Senior' must contain only 0 (No) or 1 (Yes)."
    if not bulk_df["Education Level"].isin([0, 1, 2, 3]).all():
        return False, "Column 'Education Level' must contain only 0, 1, 2, or 3."
    if not bulk_df["Gender"].isin(app1_genders).all():
        return False, (
            "Invalid values found in 'Gender'.\n\n"
            f"Allowed values: {', '.join(app1_genders)}"
        )
    if not bulk_df["Country"].isin(app1_countries).all():
        return False, (
            "Invalid values found in 'Country'.\n\n"
            f"Allowed values: {', '.join(app1_countries)}"
        )
    return True, None


# ==================================================
# APP 2 — Batch Validation
# ==================================================
def app2_validate_bulk_dataframe(bulk_df):
    if bulk_df is None or bulk_df.empty:
        return False, "The uploaded file is empty."
    missing_cols = [col for col in APP2_REQUIRED_COLUMNS if col not in bulk_df.columns]
    if missing_cols:
        return False, (
            "Missing required columns:\n\n"
            f"{', '.join(missing_cols)}"
        )
    # FIX: ensure this is a copy (prevents SettingWithCopyWarning)
    bulk_df = bulk_df[APP2_REQUIRED_COLUMNS].copy()
    try:
        # FIX: use .loc for safe assignment
        bulk_df.loc[:, "remote_ratio"] = pd.to_numeric(bulk_df["remote_ratio"])
    except Exception:
        return False, "remote_ratio must be numeric."
    if not bulk_df["remote_ratio"].isin(app2_remote_ratios).all():
        return False, "remote_ratio must be one of: 0, 50, 100."
    if not bulk_df["experience_level"].isin(app2_experience_levels).all():
        return False, "Invalid values found in experience_level."
    if not bulk_df["employment_type"].isin(app2_employment_types).all():
        return False, "Invalid values found in employment_type."
    if not bulk_df["company_size"].isin(app2_company_sizes).all():
        return False, "Invalid values found in company_size."
    return True, None


# ==================================================
# LOGIN SESSION STATE
# --------------------------------------------------
# IMPORTANT: These keys must be initialised with
# `not in` guards BEFORE calling get_logged_in_user().
# Never unconditionally overwrite them at module level —
# on Streamlit Cloud all users share the same Python
# process, so overwriting would bleed one user's state
# into another user's fresh browser session.
# ==================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None

# Now verify — get_logged_in_user() checks st.session_state
# internally and is safe to call on every rerun.
username = get_logged_in_user()
if username:
    # Legitimate authenticated session for this browser tab
    st.session_state.logged_in = True
    st.session_state.username = username
elif not st.session_state.logged_in:
    # No active session for this browser tab — ensure clean state
    st.session_state.username = None
# ==================================================
# SESSION STATE
# ==================================================
for key in [
    "active_model",
    "bulk_result_df", "bulk_uploaded_name", "bulk_pdf_buffer",
    "manual_pdf_buffer", "manual_prediction_result",
    "manual_pdf_ready"
]:
    if key not in st.session_state:
        if key == "active_model":
            st.session_state[key] = "Model 1 — General Salary (Random Forest)"
        elif key == "manual_pdf_ready":
            st.session_state[key] = False
        else:
            st.session_state[key] = None
# ==================================================
# TITLE
# ==================================================
st.markdown(
    f"""
    <div style="display:flex;
                justify-content:center;
                align-items:center;
                gap:14px;
                margin-bottom:6px;">
        <img src="data:image/png;base64,{logo_base64}" width="70">
                <h1 style="margin:0;
                   background: linear-gradient(135deg, #4F8EF7 0%, #60A5FA 50%, #93C5FD 100%);
                   -webkit-background-clip:text;
                   -webkit-text-fill-color:transparent;
                   background-clip:text;">
            SalaryScope
        </h1>
    </div>

    <h3 style="text-align:center; color:#9BA3B0; font-weight:400; margin-top:0;">
        Salary Prediction System using Machine Learning
    </h3>
    """,
    unsafe_allow_html=True
)
st.divider()

# ==================================================
# USER ACCOUNT SIDEBAR (SECURE VERSION)
# ==================================================

with st.sidebar:

    st.header("Account")

    if username:

        st.success(f"Logged in as: {username}")

        if st.button("Logout"):
            logout()

    else:

        option = st.radio(
            "Account Options",
            ["Login", "Register", "Continue without login"]
        )

        if option == "Login":
            login_ui()

        elif option == "Register":
            register_ui()

        else:
            st.info("You can use the application without logging in.")


# ==================================================
# HEADER USER INDICATOR (SECURE VERSION)
# ==================================================

header_left, header_right = st.columns([8, 2])

with header_right:

    if st.session_state.logged_in:

        display_username = st.session_state.get("username", "User")
        first_letter = display_username[0].upper()

        st.markdown(
            f"""
            <div style="text-align:right; padding-top:10px;">
                <span style="
                    display:inline-block;
                    width:28px;
                    height:28px;
                    border-radius:50%;
                    background:#4F8EF7;
                    color:white;
                    text-align:center;
                    line-height:28px;
                    font-weight:bold;
                    margin-right:4px;
                ">
                    {first_letter}
                </span>
                <span style="color:#9CA6B5; font-size:14px;">
                    {display_username}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
# ==================================================
# MODEL SWITCHER
# ==================================================
MODEL_OPTIONS = [
    "Model 1 — General Salary (Random Forest)",
    "Model 2 — Data Science Salary (XGBoost)"
]

selected_model = st.selectbox(
    "Select Prediction Model",
    MODEL_OPTIONS,
    index=MODEL_OPTIONS.index(st.session_state.active_model),
    key="model_selector"
)

# Reset session state whenever model switches
if selected_model != st.session_state.active_model:
    st.session_state.active_model = selected_model
    st.session_state.bulk_result_df = None
    st.session_state.bulk_uploaded_name = None
    st.session_state.bulk_pdf_buffer = None
    st.session_state.manual_pdf_buffer = None
    st.session_state.manual_pdf_ready = False
    st.session_state.manual_prediction_result = None

IS_APP1 = (st.session_state.active_model == MODEL_OPTIONS[0])

# ==================================================
# LOAD EVERYTHING NEW
# ==================================================
if IS_APP1:
    app1_package = load_app1_model_package()
    app1_model = app1_package["model"]
    app1_metadata = app1_package["metadata"]

    app1_classifier_package = load_app1_classifier_package()
    app1_salary_band_model = app1_classifier_package["model"]
    app1_classifier_metadata = app1_classifier_package["metadata"]

    app1_cluster_package_a1 = load_app1_cluster_package()
    app1_cluster_model_a1 = app1_cluster_package_a1["model"]
    app1_cluster_metadata_a1 = app1_cluster_package_a1["metadata"]

else:
    app2_model, app2_metadata = load_app2_model()

if IS_APP1:
    st.caption("**Active Model:** Random Forest Regressor + Salary Level Classifier — trained on general salary dataset (`Salary.csv`).")
else:
    st.caption("**Active Model:** XGBoost Regressor (log-transformed) — trained on data science salary dataset (`ds_salaries.csv`).")

st.divider()

# ==================================================
# TABS
# ==================================================
tabs = [
    "Manual Prediction",
    "Resume Analysis",
    "Batch Prediction",
    "Scenario Analysis", 
    "Model Analytics",
    "Data Insights"
]

if st.session_state.logged_in:
    tabs.append("Profile")

    # ONLY ADMIN SEES THIS
    if is_admin():
        tabs.append("Admin")

tabs.append("About")

tab_objects = st.tabs(tabs)

# ==================================================
# TAB 1: MANUAL PREDICTION
# ==================================================
with tab_objects[0]:

    # ------------------------------------------------------------------
    # APP 1 — Manual Prediction
    # ------------------------------------------------------------------
    if IS_APP1:
        col1, col2 = st.columns(2)

        with col1:
            #age = st.number_input("Age", 18, 70, 30)
            age = st.slider("Age", 18, 70, 30)

            edu_options = [0, 1, 2, 3]
            default_edu = 1  # Bachelor's
            education = st.selectbox(
                "Education Level",
                edu_options,
                index=edu_options.index(default_edu),
                format_func=lambda x: {
                    0: "High School",
                    1: "Bachelor's Degree",
                    2: "Master's Degree",
                    3: "PhD"
                }[x]
            )
            gender = st.selectbox("Gender", app1_genders)
            #job_title = st.selectbox("Job Title", app1_job_titles)
            default_job_a1 = "Software Engineer"
            job_title = st.selectbox(
                "Job Title",
                app1_job_titles,
                index=app1_job_titles.index(default_job_a1) if default_job_a1 in app1_job_titles else 0
            )
        with col2:
            #experience = st.number_input("Years of Experience", 0.0, 40.0, 5.0, 0.5)
            experience = st.slider("Years of Experience", 0.0, 40.0, 5.0, step=0.5)
            senior = st.selectbox(
                "Senior Position",
                [0, 1],
                format_func=lambda x: "Yes" if x == 1 else "No"
            )
            default_country_a1 = "USA"

            country = st.selectbox(
                "Country",
                app1_countries,
                index=app1_countries.index(default_country_a1) if default_country_a1 in app1_countries else 0
            )
        st.caption("If your country is not listed, select 'Other'.")
        st.divider()

        if st.button("Predict Salary", width='stretch', type="primary"):

            minimum_working_age = 18
            if age - experience < minimum_working_age:
                st.error(
                    "Years of experience is not realistic for the selected age. "
                    "Please ensure experience aligns with a reasonable working age."
                )
                st.stop()

            input_df = pd.DataFrame([{
                "Age": age,
                "Years of Experience": experience,
                "Education Level": education,
                "Senior": senior,
                "Gender": gender,
                "Job Title": job_title,
                "Country": country
            }])

            prediction = app1_model.predict(input_df)[0]

            band_pred = app1_salary_band_model.predict(input_df)[0]
            salary_band_label = SALARY_BAND_LABELS.get(band_pred, "Unknown")

            # ==============================
            # MAP INPUT → ASSOCIATION FORMAT (A1)
            # ==============================
            edu_map_a1 = {
                0: "High School",
                1: "Bachelor",
                2: "Master",
                3: "PhD"
            }
            education_cat_a1 = edu_map_a1.get(education, "Unknown")
            if experience <= 2:
                exp_cat_a1 = "Entry"
            elif experience <= 5:
                exp_cat_a1 = "Mid"
            else:
                exp_cat_a1 = "Senior"
            def map_job_group_a1(title):
                t = title.lower()
                if any(x in t for x in ["engineer", "developer", "data", "scientist", "analyst", "architect", "it", "network"]):
                    return "Tech"
                elif any(x in t for x in ["manager", "director", "vp", "chief", "ceo"]):
                    return "Management"
                elif any(x in t for x in ["marketing", "sales", "brand", "advertising"]):
                    return "Marketing_Sales"
                elif any(x in t for x in ["hr", "human resources", "recruit"]):
                    return "HR"
                elif any(x in t for x in ["finance", "financial", "account"]):
                    return "Finance"
                elif any(x in t for x in ["designer", "ux", "graphic", "creative"]):
                    return "Design"
                else:
                    return "Operations"
            job_group_a1 = map_job_group_a1(job_title)

            assoc_text_a1_improved = get_assoc_insight_a1_improved(
                education_cat_a1,
                exp_cat_a1,
                country,
                job_group_a1,
                band_pred,
                assoc_rules_a1_v2,
                years_experience=experience   # <-- REQUIRED
            )

            # Predict cluster
            cluster_pred_a1 = app1_cluster_model_a1.predict(
                pd.DataFrame([{
                    "Years of Experience": experience,
                    "Education Level": education
                }])
            )[0]

            # Map to stage label
            stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})
            career_stage_label = stage_map.get(int(cluster_pred_a1), "Unknown")

            a1 = load_app1_analytics()
            std_dev = a1["residual_std"]
            lower_bound = max(prediction - 1.96 * std_dev, 0)
            upper_bound = prediction + 1.96 * std_dev

            input_details = {
                "Age": age,
                "Years of Experience": experience,
                "Education Level": {0: "High School", 1: "Bachelor's Degree",
                                    2: "Master's Degree", 3: "PhD"}[education],
                "Senior Position": "Yes" if senior == 1 else "No",
                "Gender": gender,
                "Job Title": job_title,
                "Country": country
            }
            # Save prediction AFTER input_details exists
            if st.session_state.get("logged_in"):
                save_prediction(
                    st.session_state.username,
                    "Random Forest",
                    input_details,
                    float(prediction)
                )
            st.session_state.manual_prediction_result = {
                "input_details": input_details,
                "prediction": prediction,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "salary_band_label": salary_band_label,
                "career_stage_label": career_stage_label,
                "assoc_text_a1_improved" : assoc_text_a1_improved

            }
            st.session_state.manual_pdf_buffer = None
            st.session_state.manual_pdf_ready = False

        if st.session_state.manual_prediction_result is not None:
            data = st.session_state.manual_prediction_result
            prediction = data["prediction"]
            lower_bound = data["lower_bound"]
            upper_bound = data["upper_bound"]
            salary_band_label = data["salary_band_label"]
            career_stage_label = data["career_stage_label"]
            assoc_text_a1_improved = data["assoc_text_a1_improved"]
            monthly = prediction / 12
            weekly = prediction / 52
            hourly = prediction / (52 * 40)

            st.markdown("<h3 style='text-align: center;'>Estimated Annual Salary</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #3E7DE0;
                    border-left: 5px solid #3E7DE0;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>ANNUAL SALARY (USD)</div>
                    <div style='color: #4F8EF7; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>${prediction:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.divider()
            st.markdown("<h3 style='text-align: center;'>Estimated Salary Level</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #818CF8;
                    border-left: 5px solid #818CF8;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>CAREER SALARY LEVEL</div>
                    <div style='color: #4F8EF7; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>{salary_band_label}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            # -------------------------------------------------------
            # CAREER STAGE (CLUSTER MODEL)
            # -------------------------------------------------------

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Career Stage</h3>", unsafe_allow_html=True)

            # Display UI (same style as salary band)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #A78BFA;
                    border-left: 5px solid #A78BFA;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>
                        CAREER STAGE (PROGRESSION SEGMENT)
                    </div>
                    <div style='color: #A78BFA; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>
                        {career_stage_label}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.caption(
                "Career stage is determined using an unsupervised clustering model based on "
                "experience and education. It represents your relative position in career progression."
            )
            
            # -------------------------------------------------------
            # ASSOCIATION INSIGHT (APP 1)
            # -------------------------------------------------------

            st.divider()

            st.markdown("<h3 style='text-align: center;'>Pattern Insight (Data Association)</h3>", unsafe_allow_html=True)

            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #F59E0B;
                    border-left: 5px solid #F59E0B;
                    border-radius: 10px;
                    padding: 24px 32px;
                    margin: 8px auto;
                '>
                    <div style='color: #E5E7EB; font-size: 18px; font-weight: 500; line-height: 1.4;'>{assoc_text_a1_improved}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.caption(
                "This insight is generated using association rule mining (Apriori algorithm), "
                "identifying patterns between education, experience, job role, and salary levels."
            )
            st.caption("Note: This insight reflects general dataset patterns and may not always align with individual predictions.")

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Breakdown (Approximate)</h3>", unsafe_allow_html=True)
            col_m, col_w, col_h = st.columns(3)
            col_m.metric("Monthly (Approx)", f"${monthly:,.2f}")
            col_w.metric("Weekly (Approx)", f"${weekly:,.2f}")  
            col_h.metric("Hourly (Approx, 40hr/week)", f"${hourly:,.2f}")
            st.divider()
            st.markdown("<h3 style='text-align: center;'>Likely Salary Range (95% Confidence Interval)</h3>", unsafe_allow_html=True)
            col_low, col_high = st.columns(2)
            col_low.metric("Lower Estimate", f"${lower_bound:,.2f}")
            col_high.metric("Upper Estimate", f"${upper_bound:,.2f}")
            st.caption("Range estimated using standard deviation of model residuals observed during training.")

            st.divider()
            render_currency_converter(usd_amount=prediction, location_hint=country, widget_key="manual_a1")
            active_currency = get_active_currency("manual_a1")
            active_rates    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction, location_hint=country, widget_key="manual_a1_tax",
                                converted_currency=active_currency, rates=active_rates)
            render_col_adjuster(gross_usd=prediction, work_country=country, widget_key="manual_a1_col")

            st.divider()
            st.markdown("<h3 style='text-align: left;'>Salary Negotiation Tips</h3>", unsafe_allow_html=True)

            negotiation_tips_a1 = generate_negotiation_tips_app1(
                prediction=prediction,
                salary_band_label=salary_band_label,
                career_stage_label=career_stage_label,
                experience=data["input_details"]["Years of Experience"],
                job_title=data["input_details"]["Job Title"],
                country=data["input_details"]["Country"],
                senior=1 if data["input_details"]["Senior Position"] == "Yes" else 0,
                market_type="info"   # Model 1 has no market comparison, so default to info
            )

            render_negotiation_tips(negotiation_tips_a1)

            st.caption("These tips help you approach salary discussions effectively based on your experience and role.")

            st.divider()
            insights_a1 = generate_insights_app1(data["input_details"])
            recs_a1 = generate_recommendations_app1(data["input_details"])
            st.markdown("<h3 style='text-align: left;'>Career Recommendations</h3>", unsafe_allow_html=True)
            render_recommendations(recs_a1)
            st.caption("These recommendations focus on long-term career growth and skill development based on your profile.")

            # ==============================================
            # FEEDBACK
            # ==============================================
            st.divider()
            feedback_ui(prediction, "Random Forest", data["input_details"])            
            # ---------------- PDF GENERATION ----------------
            st.divider()
            if st.button("Prepare PDF Report", width='stretch'):
                st.session_state.manual_pdf_buffer = app1_generate_manual_pdf(
                    data["input_details"], data["prediction"], data["lower_bound"], data["upper_bound"],
                    data["salary_band_label"], app1_metadata, app1_classifier_metadata, data["career_stage_label"], app1_cluster_metadata_a1
                )
                st.session_state.manual_pdf_ready = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.manual_pdf_ready:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.manual_pdf_ready:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.manual_pdf_buffer,
                    file_name="salary_prediction_report.pdf",
                    mime="application/pdf",
                    width='stretch'
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True
                )
    # ------------------------------------------------------------------
    # APP 2 — Manual Prediction
    # ------------------------------------------------------------------
    else:

        col1, col2 = st.columns(2)

        with col1:
            experience_label = st.selectbox(
                "Experience Level",
                [EXPERIENCE_MAP[x] for x in ["EN", "MI", "SE", "EX"] if x in app2_experience_levels]
            )
            experience_level = EXPERIENCE_REVERSE[experience_label]

            employment_label = st.selectbox(
                "Employment Type",
                [EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types]
            )
            employment_type = EMPLOYMENT_REVERSE[employment_label]

            default_job = "Data Scientist"

            job_title_a2 = st.selectbox(
                "Job Title",
                app2_job_titles,
                index=app2_job_titles.index(default_job) if default_job in app2_job_titles else 0
            )

            default_res = "United States (US)"

            employee_residence_label = st.selectbox(
                "Employee Residence",
                app2_employee_residence_display_options,
                index=app2_employee_residence_display_options.index(default_res)
                if default_res in app2_employee_residence_display_options else 0
            )
            if employee_residence_label == "Other":
                employee_residence = "Other"
            elif "(" in employee_residence_label:
                employee_residence = employee_residence_label.split("(")[-1].replace(")", "").strip()
            else:
                employee_residence = employee_residence_label

        with col2:
            remote_label = st.selectbox(
                "Work Mode",
                [REMOTE_MAP[x] for x in [0, 50, 100] if x in app2_remote_ratios]
            )
            remote_ratio = REMOTE_REVERSE[remote_label]

            default_loc = "United States (US)"

            company_location_label = st.selectbox(
                "Company Location",
                app2_country_display_options,
                index=app2_country_display_options.index(default_loc)
                if default_loc in app2_country_display_options else 0
            )
            if "(" in company_location_label:
                company_location = company_location_label.split("(")[-1].replace(")", "").strip()
            else:
                company_location = company_location_label

            company_size_label = st.selectbox(
                "Company Size",
                [COMPANY_SIZE_MAP[x] for x in app2_company_sizes]
            )
            company_size = COMPANY_SIZE_REVERSE[company_size_label]

        st.caption("Select employee residence from the list. If the country is not listed, choose 'Other'.")
        st.divider()

        if st.button("Predict Salary", width='stretch', type="primary"):

            try:
                junior_a2, senior_a2, exec_a2, is_mgmt_a2, domain_a2 = title_features(job_title_a2)
                exp_x_domain_a2 = f"{experience_level}_{domain_a2}"

                input_df_a2 = pd.DataFrame([{
                    "experience_level": experience_level,
                    "employment_type": employment_type,
                    "job_title": job_title_a2,
                    "employee_residence": employee_residence,
                    "remote_ratio": int(remote_ratio),
                    "company_location": company_location,
                    "company_size": company_size,
                    "title_is_junior": junior_a2,
                    "title_is_senior": senior_a2,
                    "title_is_exec": exec_a2,
                    "title_is_mgmt": is_mgmt_a2,
                    "title_domain": domain_a2,
                    "exp_x_domain": exp_x_domain_a2
                }])

                pred_log_a2 = app2_model.predict(input_df_a2)[0]
                prediction_a2 = float(np.expm1(pred_log_a2))

                #xgb_model_a2 = app2_model.named_steps["model"]
                #booster_a2 = xgb_model_a2.get_booster()
                #processed_input_a2 = app2_model.named_steps["preprocessor"].transform(input_df_a2)
                #import xgboost as xgb
                #dmatrix_a2 = xgb.DMatrix(processed_input_a2)
                #tree_predictions_log_a2 = []
                #for i in range(xgb_model_a2.n_estimators):
                #    tree_pred = booster_a2.predict(dmatrix_a2, iteration_range=(i, i + 1))[0]
                #    tree_predictions_log_a2.append(tree_pred)
                #tree_predictions_log_a2 = np.array(tree_predictions_log_a2)
                #tree_predictions_usd_a2 = np.expm1(tree_predictions_log_a2)
                #std_dev_a2 = float(np.std(tree_predictions_usd_a2))
                #lower_bound_a2 = max(prediction_a2 - 1.96 * std_dev_a2, 0.0)
                #upper_bound_a2 = prediction_a2 + 1.96 * std_dev_a2

                if employee_residence == "Other":
                    res_display = "Other"
                else:
                    res_name = COUNTRY_NAME_MAP.get(employee_residence)
                    res_display = f"{res_name} ({employee_residence})" if res_name else employee_residence
                
                loc_name = COUNTRY_NAME_MAP.get(company_location)
                loc_display = f"{loc_name} ({company_location})" if loc_name else company_location

                input_details_a2 = {
                    "Experience Level": experience_label,
                    "Employment Type": employment_label,
                    "Job Title": job_title_a2,
                    "Employee Residence": res_display,
                    "Work Mode": remote_label,
                    "Company Location": loc_display,
                    "Company Size": company_size_label
                }
                if st.session_state.get("logged_in"):
                    save_prediction(
                        st.session_state.username,
                        "XGBoost",
                        input_details_a2,
                        float(prediction_a2)
                    )

                st.session_state.manual_prediction_result = {
                    "input_details": input_details_a2,
                    "prediction": prediction_a2,
                  #  "lower_bound": lower_bound_a2,
                  #  "upper_bound": upper_bound_a2
                }
                st.session_state.manual_pdf_buffer = None
                st.session_state.manual_pdf_ready = False

            except Exception as e:
                st.error("Prediction failed. Please check input values.")
                st.exception(e)
                st.session_state.manual_prediction_result = None
                st.session_state.manual_pdf_buffer = None

        if st.session_state.manual_prediction_result is not None:
            data_a2 = st.session_state.manual_prediction_result
            prediction_a2 = data_a2["prediction"]
            #lower_bound_a2 = data_a2["lower_bound"]
            #upper_bound_a2 = data_a2["upper_bound"]
            monthly_a2 = prediction_a2 / 12
            weekly_a2 = prediction_a2 / 52
            hourly_a2 = prediction_a2 / (52 * 40)

            st.markdown("<h3 style='text-align: center;'>Estimated Annual Salary</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #3E7DE0;
                    border-left: 5px solid #3E7DE0;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>ANNUAL SALARY (USD)</div>
                    <div style='color: #4F8EF7; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>${prediction_a2:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Breakdown (Approximate)</h3>", unsafe_allow_html=True)
            col_m2, col_w2, col_h2 = st.columns(3)
            col_m2.metric("Monthly (Approx)", f"${monthly_a2:,.2f}")
            col_w2.metric("Weekly (Approx)", f"${weekly_a2:,.2f}")
            col_h2.metric("Hourly (Approx, 40hr/week)", f"${hourly_a2:,.2f}")
            #st.divider()
            #st.markdown("<h3 style='text-align: center;'>Likely Salary Range (95% Confidence Interval)</h3>", unsafe_allow_html=True)
            #col_low2, col_high2 = st.columns(2)
            #col_low2.metric("Lower Estimate", f"${lower_bound_a2:,.2f}")
            #col_high2.metric("Upper Estimate", f"${upper_bound_a2:,.2f}")
            #st.caption("Range estimated using variation across individual trees in the XGBoost model.")

            st.divider()
            render_currency_converter(usd_amount=prediction_a2, location_hint=company_location, widget_key="manual_a2")
            active_currency_a2 = get_active_currency("manual_a2")
            active_rates_a2    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction_a2, location_hint=company_location, widget_key="manual_a2_tax",
                                converted_currency=active_currency_a2, rates=active_rates_a2)
            render_col_adjuster(gross_usd=prediction_a2, work_country=company_location, widget_key="manual_a2_col")
           # render_currency_converter(
           #     usd_amount=prediction_a2,       # or prediction_a2 for App 2
           #     location_hint=company_location,       # or company_location for App 2
           #     widget_key="manual_a2",      # use "manual_a2", "resume_a1", "resume_a2" per call-site
           # )

            # =====================================================
            # SMART INSIGHTS (APP 2)
            # =====================================================

            insights_a2 = generate_insights_app2(
                data_a2["input_details"],
                prediction_a2,
                df_app2,
                title_features
            )

            recs_a2 = generate_recommendations_app2(
                data_a2["input_details"],
                prediction_a2,
                df_app2,
                title_features
            )

            #st.divider()
            #st.subheader("Smart Insights")

            # Market message
            #if insights["market_type"] == "success":
            #    st.success(insights["market_msg"])
            #elif insights["market_type"] == "warning":
            #    st.warning(insights["market_msg"])
            #else:
            #    st.info(insights["market_msg"])

            # Role
            #st.caption(f"Domain Focus: {insights['role']}")
            st.divider()

            st.markdown("<h3 style='text-align: left;'>Salary Negotiation Tips</h3>", unsafe_allow_html=True)

            negotiation_tips_a2 = generate_negotiation_tips_app2(
                prediction=prediction_a2,
                experience_label=data_a2["input_details"]["Experience Level"],
                company_size_label=data_a2["input_details"]["Company Size"],
                remote_label=data_a2["input_details"]["Work Mode"],
                company_location=company_location,   # ISO code already available in scope
                job_title=data_a2["input_details"]["Job Title"],
                role=insights_a2["role"],               # already computed from insights_engine
                market_type=insights_a2["market_type"]  # already computed from insights_engine
            )

            render_negotiation_tips(negotiation_tips_a2)
            st.caption("These tips help you approach salary discussions effectively based on your experience and role.")

            # Recommendations
            st.divider()
            st.subheader("Career Recommendations")
            render_recommendations(recs_a2)
            st.caption("These recommendations focus on long-term career growth and skill development based on your profile.")

            # ==============================================
            # FEEDBACK
            # ==============================================
            st.divider()
            feedback_ui(prediction_a2, "XGBoost", data_a2["input_details"])

            # ---------------- PDF GENERATION ----------------
            st.divider()
            if st.button("Prepare PDF Report", width='stretch'):
                st.session_state.manual_pdf_buffer = app2_generate_manual_pdf(
                    data_a2["input_details"], data_a2["prediction"],
                    None, None, app2_metadata
                )
                st.session_state.manual_pdf_ready = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.manual_pdf_ready:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.manual_pdf_ready:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.manual_pdf_buffer,
                    file_name="salary_prediction_report.pdf",
                    mime="application/pdf",
                    width='stretch'
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True
                )

# ==================================================
# TAB 2: RESUME ANALYSIS
# ==================================================
with tab_objects[1]:

    st.header("Resume Analysis")
    st.caption(
        "Upload a resume PDF to automatically extract structured features using NLP. "
        "The extracted fields can be reviewed and edited before salary prediction."
    )

    if not IS_APP1:
        # ----------------------------------------------------------------
        # APP 2 — Resume Analysis Tab (XGBoost DS Salary Model)
        # All variables/functions use _a2 suffix or app2_ prefix
        # ----------------------------------------------------------------
        # ==============================
        # FRAGMENT DEFINITIONS (APP 2)
        # ==============================

        @st.fragment
        def render_resume_editor_a2():
            feats_a2 = st.session_state.resume_features_a2

            with st.expander("View Extracted Resume Text"):
                st.text_area(
                    "Extracted Text",
                    st.session_state.resume_text_a2,
                    height=250,
                    key="resume_extracted_text_preview_a2"
                )

            st.subheader("Detected Features")
            st.caption("Review and edit the extracted fields before prediction.")

            col_ra1, col_ra2 = st.columns(2)

            # --- Experience Level ---
            exp_level_options_a2 = [
                x for x in ["EN", "MI", "SE", "EX"]
                if x in app2_experience_levels
            ]
            exp_level_display_a2 = [EXPERIENCE_MAP[x] for x in exp_level_options_a2]
            detected_exp_code_a2 = feats_a2.get("experience_level_a2", "MI")
            if detected_exp_code_a2 not in exp_level_options_a2:
                detected_exp_code_a2 = exp_level_options_a2[0]
            default_exp_idx_a2 = exp_level_options_a2.index(detected_exp_code_a2)

            with col_ra1:
                st.selectbox(
                    "Experience Level",
                    exp_level_display_a2,
                    index=default_exp_idx_a2,
                    key="resume_experience_level_a2"
                )
                st.selectbox(
                    "Employment Type",
                    [EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types],
                    index=[
                        EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"]
                        if x in app2_employment_types
                    ].index(
                        EMPLOYMENT_MAP.get(feats_a2.get("employment_type_a2", "FT"), "Full Time")
                    ) if EMPLOYMENT_MAP.get(feats_a2.get("employment_type_a2", "FT"), "Full Time") in [
                        EMPLOYMENT_MAP[x] for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types
                    ] else 0,
                    key="resume_employment_type_a2"
                )
                detected_job_a2 = feats_a2.get("job_title_a2", app2_job_titles[0])
                st.selectbox(
                    "Job Title",
                    app2_job_titles,
                    index=app2_job_titles.index(detected_job_a2)
                    if detected_job_a2 in app2_job_titles else 0,
                    key="resume_job_title_a2"
                )

                st.selectbox(
                    "Company Size",
                    [COMPANY_SIZE_MAP[x] for x in app2_company_sizes],
                    index=[COMPANY_SIZE_MAP[x] for x in app2_company_sizes].index(
                        COMPANY_SIZE_MAP.get(
                            feats_a2.get("company_size_a2", "M"), "Medium Company"
                        )
                    ) if COMPANY_SIZE_MAP.get(
                        feats_a2.get("company_size_a2", "M"), "Medium Company"
                    ) in [COMPANY_SIZE_MAP[x] for x in app2_company_sizes] else 0,
                    key="resume_company_size_a2"
                )
            # --- Employee Residence (country extracted from resume) ---
            detected_iso_a2 = feats_a2.get("employee_residence_a2", "US")

            # Build display label for detected country
            detected_res_name_a2 = COUNTRY_NAME_MAP.get(detected_iso_a2)
            if detected_res_name_a2:
                detected_res_display_a2 = f"{detected_res_name_a2} ({detected_iso_a2})"
            else:
                detected_res_display_a2 = detected_iso_a2

            if detected_res_display_a2 not in app2_employee_residence_display_options:
                detected_res_display_a2 = (
                    "United States (US)"
                    if "United States (US)" in app2_employee_residence_display_options
                    else app2_employee_residence_display_options[0]
                )

            with col_ra2:
                st.selectbox(
                    "Employee Residence",
                    app2_employee_residence_display_options,
                    index=app2_employee_residence_display_options.index(detected_res_display_a2),
                    key="resume_employee_residence_a2"
                )

                # Work mode
                remote_val_a2 = feats_a2.get("remote_ratio_a2", 0)
                remote_display_options_a2 = [
                    REMOTE_MAP[x] for x in [0, 50, 100] if x in app2_remote_ratios
                ]
                remote_detected_label_a2 = REMOTE_MAP.get(remote_val_a2, "On-site")
                if remote_detected_label_a2 not in remote_display_options_a2:
                    remote_detected_label_a2 = remote_display_options_a2[0]

                st.selectbox(
                    "Work Mode",
                    remote_display_options_a2,
                    index=remote_display_options_a2.index(remote_detected_label_a2),
                    key="resume_remote_ratio_a2"
                )

                # Company location — same as residence by default (can be edited)
                detected_loc_a2 = feats_a2.get("company_location_a2", "US")
                detected_loc_name_a2 = COUNTRY_NAME_MAP.get(detected_loc_a2)
                if detected_loc_name_a2:
                    detected_loc_display_a2 = f"{detected_loc_name_a2} ({detected_loc_a2})"
                else:
                    detected_loc_display_a2 = detected_loc_a2

                if detected_loc_display_a2 not in app2_country_display_options:
                    detected_loc_display_a2 = (
                        "United States (US)"
                        if "United States (US)" in app2_country_display_options
                        else app2_country_display_options[0]
                    )

                st.selectbox(
                    "Company Location",
                    app2_country_display_options,
                    index=app2_country_display_options.index(detected_loc_display_a2),
                    key="resume_company_location_a2"
                )


            st.caption(
                "Employee Residence and Company Location are auto-detected from the resume. "
                "They default to the same country — adjust if needed."
            )

        @st.fragment
        def render_resume_score_a2():
            score_a2 = st.session_state.resume_score_data_a2
            feats_a2 = st.session_state.resume_features_a2

            st.divider()
            st.subheader("Resume Score Breakdown")

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Total Score", f"{score_a2['total_score_a2']}/100")
            col_s2.metric("Experience Score", score_a2["experience_score_a2"])
            col_s3.metric("Skills Score", score_a2["skills_score_a2"])
            col_s4.metric("Role Relevance", score_a2["title_score_a2"])

            st.caption(f"Profile Strength: {score_a2['level_a2']}")
            st.write(f"Experience: {score_a2['experience_note_a2']}")
            st.write(f"Skills: {score_a2['skills_note_a2']}")
            st.write(f"Role: {score_a2['title_note_a2']}")

            if score_a2["skills_detected_a2"]:
                st.markdown(
                    f"**DS/ML Skills Detected ({score_a2['ds_skill_count_a2']}):** "
                    f"{score_a2['skills_detected_str_a2']}"
                )
            else:
                st.markdown("**Detected Skills:** None")

            with st.expander("Detection Sources"):
                st.json(feats_a2["sources_a2"])

        @st.fragment
        def render_resume_prediction_a2():
            st.divider()

            if st.button(
                "Predict Salary from Resume",
                type="primary",
                width="stretch",
                key="resume_predict_button_a2"
            ):
                # Read widget values from session state
                exp_level_label_a2 = st.session_state.resume_experience_level_a2
                experience_level_a2 = EXPERIENCE_REVERSE.get(exp_level_label_a2, "MI")

                emp_label_a2 = st.session_state.resume_employment_type_a2
                employment_type_a2 = EMPLOYMENT_REVERSE.get(emp_label_a2, "FT")

                job_title_a2 = st.session_state.resume_job_title_a2

                # Parse employee residence
                res_label_a2 = st.session_state.resume_employee_residence_a2
                if res_label_a2 == "Other":
                    employee_residence_a2 = "US"
                elif "(" in res_label_a2:
                    employee_residence_a2 = res_label_a2.split("(")[-1].replace(")", "").strip()
                else:
                    employee_residence_a2 = res_label_a2

                remote_label_a2 = st.session_state.resume_remote_ratio_a2
                remote_ratio_a2 = REMOTE_REVERSE.get(remote_label_a2, 0)

                # Parse company location
                loc_label_a2 = st.session_state.resume_company_location_a2
                if "(" in loc_label_a2:
                    company_location_a2 = loc_label_a2.split("(")[-1].replace(")", "").strip()
                else:
                    company_location_a2 = loc_label_a2

                company_size_label_a2 = st.session_state.resume_company_size_a2
                company_size_a2 = COMPANY_SIZE_REVERSE.get(company_size_label_a2, "M")

                score_a2 = st.session_state.resume_score_data_a2

                try:
                    junior_a2_r, senior_a2_r, exec_a2_r, is_mgmt_a2_r, domain_a2_r = title_features(job_title_a2)
                    exp_x_domain_a2_r = f"{experience_level_a2}_{domain_a2_r}"

                    input_df_a2_r = pd.DataFrame([{
                        "experience_level": experience_level_a2,
                        "employment_type": employment_type_a2,
                        "job_title": job_title_a2,
                        "employee_residence": employee_residence_a2,
                        "remote_ratio": int(remote_ratio_a2),
                        "company_location": company_location_a2,
                        "company_size": company_size_a2,
                        "title_is_junior": junior_a2_r,
                        "title_is_senior": senior_a2_r,
                        "title_is_exec": exec_a2_r,
                        "title_is_mgmt": is_mgmt_a2_r,
                        "title_domain": domain_a2_r,
                        "exp_x_domain": exp_x_domain_a2_r
                    }])

                    pred_log_a2_r = app2_model.predict(input_df_a2_r)[0]
                    prediction_a2_r = float(np.expm1(pred_log_a2_r))

                    # Build display labels
                    res_name_a2_r = COUNTRY_NAME_MAP.get(employee_residence_a2)
                    res_display_a2_r = (
                        f"{res_name_a2_r} ({employee_residence_a2})"
                        if res_name_a2_r else employee_residence_a2
                    )
                    loc_name_a2_r = COUNTRY_NAME_MAP.get(company_location_a2)
                    loc_display_a2_r = (
                        f"{loc_name_a2_r} ({company_location_a2})"
                        if loc_name_a2_r else company_location_a2
                    )

                    input_details_a2_r = {
                        "Experience Level": EXPERIENCE_MAP.get(experience_level_a2, experience_level_a2),
                        "Employment Type": EMPLOYMENT_MAP.get(employment_type_a2, employment_type_a2),
                        "Job Title": job_title_a2,
                        "Employee Residence": res_display_a2_r,
                        "Work Mode": REMOTE_MAP.get(remote_ratio_a2, str(remote_ratio_a2)),
                        "Company Location": loc_display_a2_r,
                        "Company Size": company_size_label_a2,
                        "Detected Skills": score_a2["skills_detected_str_a2"],
                        "Resume Score": score_a2["total_score_a2"]
                    }

                    if st.session_state.get("logged_in"):
                        save_prediction(
                            st.session_state.username,
                            "XGBoost Resume",
                            input_details_a2_r,
                            float(prediction_a2_r)
                        )

                    st.session_state.resume_prediction_result_a2 = {
                        "input_details_a2": input_details_a2_r,
                        "prediction_a2": prediction_a2_r,
                        "resume_score_data_a2": score_a2,
                        "company_location_code_a2": company_location_a2,
                        "experience_level_a2": experience_level_a2,
                        "job_title_a2": job_title_a2,
                    }
                    st.session_state.resume_pdf_buffer_a2 = None
                    st.session_state.resume_pdf_ready_a2 = False

                    st.rerun()

                except Exception as e_a2:
                    st.error("Prediction failed. Please check the input values.")
                    st.exception(e_a2)
                    st.session_state.resume_prediction_result_a2 = None

        @st.fragment
        def render_resume_results_a2():
            data_a2_r = st.session_state.resume_prediction_result_a2
            prediction_a2_r = data_a2_r["prediction_a2"]
            score_a2 = data_a2_r["resume_score_data_a2"]

            monthly_a2_r = prediction_a2_r / 12
            weekly_a2_r = prediction_a2_r / 52
            hourly_a2_r = prediction_a2_r / (52 * 40)

            st.divider()
            st.markdown(
                "<h3 style='text-align: center;'>Resume Profile Score</h3>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #34D399;
                    border-left: 5px solid #34D399;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600;
                                letter-spacing: 0.5px; margin-bottom: 8px;'>RESUME SCORE</div>
                    <div style='color: #34D399; font-size: 42px; font-weight: 700;
                                letter-spacing: -1px;'>{score_a2["total_score_a2"]}/100</div>
                    <div style='color: #E6EAF0; font-size: 16px; margin-top: 8px;'>
                        {score_a2["level_a2"]} Profile
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                "<h3 style='text-align: center;'>Estimated Annual Salary</h3>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #3E7DE0;
                    border-left: 5px solid #3E7DE0;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600;
                                letter-spacing: 0.5px; margin-bottom: 8px;'>ANNUAL SALARY (USD)</div>
                    <div style='color: #4F8EF7; font-size: 42px; font-weight: 700;
                                letter-spacing: -1px;'>${prediction_a2_r:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown(
                "<h3 style='text-align: center;'>Score Breakdown</h3>",
                unsafe_allow_html=True
            )
            c1a2, c2a2, c3a2 = st.columns(3)
            c1a2.metric("Experience", score_a2["experience_score_a2"])
            c2a2.metric("Skills", score_a2["skills_score_a2"])
            c3a2.metric("Role Relevance", score_a2["title_score_a2"])

            st.divider()
            st.markdown(
                "<h3 style='text-align: center;'>Breakdown (Approximate)</h3>",
                unsafe_allow_html=True
            )
            col_m_a2, col_w_a2, col_h_a2 = st.columns(3)
            col_m_a2.metric("Monthly (Approx)", f"${monthly_a2_r:,.2f}")
            col_w_a2.metric("Weekly (Approx)", f"${weekly_a2_r:,.2f}")
            col_h_a2.metric("Hourly (Approx, 40hr/week)", f"${hourly_a2_r:,.2f}")

            st.divider()
            #render_currency_converter(
            #    usd_amount=prediction_a2_r,
            #    location_hint=data_a2_r["company_location_code_a2"],
            #    widget_key="resume_a2",   
            #)
            render_currency_converter(usd_amount=prediction_a2_r, location_hint=data_a2_r["company_location_code_a2"], widget_key="resume_a2")
            active_currency_a2_r = get_active_currency("resume_a2")
            active_rates_a2_r    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction_a2_r, location_hint=data_a2_r["company_location_code_a2"], widget_key="resume_a2_tax",
                                converted_currency=active_currency_a2_r, rates=active_rates_a2_r)
            render_col_adjuster(gross_usd=prediction_a2_r, work_country=data_a2_r["company_location_code_a2"], widget_key="resume_a2_col")

            # --- Smart Insights & Negotiation Tips ---
            st.divider()
            insights_a2_r = generate_insights_app2(
                data_a2_r["input_details_a2"],
                prediction_a2_r,
                df_app2,
                title_features
            )

            recs_a2_r = generate_recommendations_app2(
                data_a2_r["input_details_a2"],
                prediction_a2_r,
                df_app2,
                title_features
            )
            st.markdown(
                "<h3 style='text-align: left;'>Salary Negotiation Tips</h3>",
                unsafe_allow_html=True
            )
            negotiation_tips_a2_r = generate_negotiation_tips_app2(
                prediction=prediction_a2_r,
                experience_label=data_a2_r["input_details_a2"]["Experience Level"],
                company_size_label=data_a2_r["input_details_a2"]["Company Size"],
                remote_label=data_a2_r["input_details_a2"]["Work Mode"],
                company_location=data_a2_r["company_location_code_a2"],
                job_title=data_a2_r["job_title_a2"],
                role=insights_a2_r["role"],
                market_type=insights_a2_r["market_type"]
            )
            render_negotiation_tips(negotiation_tips_a2_r)
            st.caption(
                "These tips help you approach salary discussions effectively "
                "based on your experience and role."
            )

            st.divider()
            st.subheader("Career Recommendations")
            render_recommendations(recs_a2_r)
            st.caption(
                "These recommendations focus on long-term career growth "
                "and skill development based on your profile."
            )
            # ---------------- PDF GENERATION ----------------
            st.divider()

            if st.button("Prepare PDF Report", width='stretch', key="resume_pdf_prepare_a2"):

                st.session_state.resume_pdf_buffer_a2 = app2_generate_resume_pdf(
                    st.session_state.resume_prediction_result_a2
                )

                st.session_state.resume_pdf_ready_a2 = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.resume_pdf_ready_a2:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.resume_pdf_ready_a2:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.resume_pdf_buffer_a2,
                    file_name="resume_salary_report_app2.pdf",
                    mime="application/pdf",
                    width='stretch',
                    key="resume_pdf_download_a2"
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True,
                    key="resume_pdf_disabled_a2"
                )
        # ==============================
        # FILE UPLOADER + RESET (APP 2)
        # ==============================

        uploaded_resume_a2 = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf"],
            key="resume_pdf_upload_a2"
        )

        if "last_resume_name_a2" not in st.session_state:
            st.session_state.last_resume_name_a2 = None

        current_resume_name_a2 = uploaded_resume_a2.name if uploaded_resume_a2 else None

        if current_resume_name_a2 != st.session_state.last_resume_name_a2:
            st.session_state.last_resume_name_a2 = current_resume_name_a2
            if uploaded_resume_a2 is None:
                st.session_state.resume_features_a2 = None
                st.session_state.resume_text_a2 = ""
                st.session_state.resume_score_data_a2 = None
                st.session_state.resume_prediction_result_a2 = None

                st.session_state.resume_pdf_ready_a2 = False
                st.session_state.resume_pdf_buffer_a2 = None
        for _key_a2 in [
            "resume_features_a2",
            "resume_text_a2",
            "resume_score_data_a2",
            "resume_prediction_result_a2"
        ]:
            if _key_a2 not in st.session_state:
                st.session_state[_key_a2] = None if _key_a2 != "resume_text_a2" else ""

        if "resume_pdf_ready_a2" not in st.session_state:
            st.session_state.resume_pdf_ready_a2 = False
        if "resume_pdf_buffer_a2" not in st.session_state:
            st.session_state.resume_pdf_buffer_a2 = None
        # ==============================
        # EXTRACTION BUTTON (APP 2)
        # ==============================

        if uploaded_resume_a2 is not None:
            if st.button(
                "Extract Resume Features",
                type="primary",
                width="stretch",
                key="resume_extract_button_a2"
            ):
                try:
                    with st.spinner("Extracting text and analysing resume..."):
                        raw_text_a2 = extract_text_from_pdf(uploaded_resume_a2)

                        if not raw_text_a2.strip():
                            st.error("Could not extract readable text from the PDF.")
                            st.stop()

                        feats_a2 = extract_resume_features_a2(
                            raw_text=raw_text_a2,
                            allowed_job_titles_a2=app2_job_titles,
                            allowed_iso_codes_a2=list(APP2_ALLOWED_ISO_CODES_A2),
                        )
                        score_a2 = calculate_resume_score_a2(feats_a2)

                        st.session_state.resume_text_a2 = raw_text_a2
                        st.session_state.resume_features_a2 = feats_a2
                        st.session_state.resume_score_data_a2 = score_a2
                        st.session_state.resume_prediction_result_a2 = None

                    st.success("Resume processed successfully.")
                except Exception as e_extract_a2:
                    st.error("Failed to process the resume.")
                    st.exception(e_extract_a2)

        # ==============================
        # FRAGMENT CALL SITES (APP 2)
        # ==============================

        if st.session_state.resume_features_a2 is not None:
            render_resume_editor_a2()
            render_resume_score_a2()
            render_resume_prediction_a2()

        if st.session_state.resume_prediction_result_a2 is not None:
            render_resume_results_a2()    

    else:

        # ==============================
        # FRAGMENT DEFINITIONS
        # ==============================

        @st.fragment
        def render_resume_editor():
            features = st.session_state.resume_features

            with st.expander("View Extracted Resume Text"):
                st.text_area(
                    "Extracted Text",
                    st.session_state.resume_text,
                    height=250,
                    key="resume_extracted_text_preview"
                )

            st.subheader("Detected Features")
            st.caption("Review and edit the extracted fields before prediction.")

            col_r1, col_r2 = st.columns(2)

            with col_r1:
                st.slider("Age", 18, 70, 25, key="resume_age")
                st.selectbox(
                    "Education Level",
                    [0, 1, 2, 3],
                    index=[0, 1, 2, 3].index(int(features["education_level"])) if int(features["education_level"]) in [0, 1, 2, 3] else 1,
                    format_func=lambda x: {
                        0: "High School",
                        1: "Bachelor's Degree",
                        2: "Master's Degree",
                        3: "PhD"
                    }[x],
                    key="resume_education"
                )
                st.selectbox(
                    "Gender",
                    app1_genders,
                    key="resume_gender"
                )
                st.selectbox(
                    "Job Title",
                    app1_job_titles,
                    index=app1_job_titles.index(features["job_title"]) if features["job_title"] in app1_job_titles else 0,
                    key="resume_job_title"
                )

            with col_r2:
                st.slider(
                    "Years of Experience",
                    0.0, 40.0,
                    float(features["years_of_experience"]),
                    step=0.5,
                    key="resume_experience"
                )
                detected_senior_default = int(features["senior"])
                st.selectbox(
                    "Senior Position",
                    [0, 1],
                    index=[0, 1].index(detected_senior_default),
                    format_func=lambda x: "Yes" if x == 1 else "No",
                    key="resume_senior"
                )
                st.selectbox(
                    "Country",
                    app1_countries,
                    index=app1_countries.index(features["country"]) if features["country"] in app1_countries else 0,
                    key="resume_country"
                )

        @st.fragment
        def render_resume_score():
            score_data = st.session_state.resume_score_data
            features = st.session_state.resume_features

            st.divider()
            st.subheader("Resume Score Breakdown")

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Total Score", f"{score_data['total_score']}/100")
            col_s2.metric("Experience Score", score_data["experience_score"])
            col_s3.metric("Education Score", score_data["education_score"])
            col_s4.metric("Skills Score", score_data["skills_score"])

            st.caption(f"Profile Strength: {score_data['level']}")
            st.write(f"Experience: {score_data['experience_note']}")
            st.write(f"Education: {score_data['education_note']}")
            st.write(f"Skills: {score_data['skills_note']}")

            if score_data["skills_detected"]:
                st.markdown("**Detected Skills:**")
                st.write(score_data["skills_detected_str"])
            else:
                st.markdown("**Detected Skills:** None")

            with st.expander("Detection Sources"):
                st.json(features["sources"])

        @st.fragment
        def render_resume_prediction():
            st.divider()

            if st.button("Predict Salary from Resume", type="primary", width='stretch', key="resume_predict_button"):

                resume_age = st.session_state.resume_age
                resume_experience = st.session_state.resume_experience
                resume_education = st.session_state.resume_education
                resume_senior = st.session_state.resume_senior
                resume_gender = st.session_state.resume_gender
                resume_job_title = st.session_state.resume_job_title
                resume_country = st.session_state.resume_country
                score_data = st.session_state.resume_score_data

                minimum_working_age = 18
                if resume_age - resume_experience < minimum_working_age:
                    st.error(
                        "Years of experience is not realistic for the selected age. "
                        "Please ensure experience aligns with a reasonable working age."
                    )
                    st.stop()

                input_df = pd.DataFrame([{
                    "Age": resume_age,
                    "Years of Experience": resume_experience,
                    "Education Level": resume_education,
                    "Senior": resume_senior,
                    "Gender": resume_gender,
                    "Job Title": resume_job_title,
                    "Country": resume_country
                }])

                prediction = app1_model.predict(input_df)[0]

                band_pred = app1_salary_band_model.predict(input_df)[0]
                salary_band_label = SALARY_BAND_LABELS.get(band_pred, "Unknown")

                edu_map_a1 = {
                    0: "High School",
                    1: "Bachelor",
                    2: "Master",
                    3: "PhD"
                }
                education_cat_a1 = edu_map_a1.get(resume_education, "Unknown")

                if resume_experience <= 2:
                    exp_cat_a1 = "Entry"
                elif resume_experience <= 5:
                    exp_cat_a1 = "Mid"
                else:
                    exp_cat_a1 = "Senior"

                def map_job_group_a1(title):
                    t = title.lower()
                    if any(x in t for x in ["engineer", "developer", "data", "scientist", "analyst", "architect", "it", "network"]):
                        return "Tech"
                    elif any(x in t for x in ["manager", "director", "vp", "chief", "ceo"]):
                        return "Management"
                    elif any(x in t for x in ["marketing", "sales", "brand", "advertising"]):
                        return "Marketing_Sales"
                    elif any(x in t for x in ["hr", "human resources", "recruit"]):
                        return "HR"
                    elif any(x in t for x in ["finance", "financial", "account"]):
                        return "Finance"
                    elif any(x in t for x in ["designer", "ux", "graphic", "creative"]):
                        return "Design"
                    else:
                        return "Operations"

                job_group_a1 = map_job_group_a1(resume_job_title)

                assoc_text_a1_improved = get_assoc_insight_a1_improved(
                    education_cat_a1,
                    exp_cat_a1,
                    resume_country,
                    job_group_a1,
                    band_pred,
                    assoc_rules_a1_v2,
                    years_experience=resume_experience
                )

                cluster_pred_a1 = app1_cluster_model_a1.predict(
                    pd.DataFrame([{
                        "Years of Experience": resume_experience,
                        "Education Level": resume_education
                    }])
                )[0]

                stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})
                career_stage_label = stage_map.get(int(cluster_pred_a1), "Unknown")

                a1 = load_app1_analytics()
                std_dev = a1["residual_std"]
                lower_bound = max(prediction - 1.96 * std_dev, 0)
                upper_bound = prediction + 1.96 * std_dev

                input_details = {
                    "Age": resume_age,
                    "Years of Experience": resume_experience,
                    "Education Level": {0: "High School", 1: "Bachelor's Degree", 2: "Master's Degree", 3: "PhD"}[resume_education],
                    "Senior Position": "Yes" if resume_senior == 1 else "No",
                    "Gender": resume_gender,
                    "Job Title": resume_job_title,
                    "Country": resume_country,
                    "Detected Skills": score_data["skills_detected_str"],
                    "Resume Score": score_data["total_score"]
                }

                if st.session_state.get("logged_in"):
                    save_prediction(
                        st.session_state.username,
                        "Random Forest Resume",
                        input_details,
                        float(prediction)
                    )

                st.session_state.resume_prediction_result = {
                    "input_details": input_details,
                    "prediction": prediction,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "salary_band_label": salary_band_label,
                    "career_stage_label": career_stage_label,
                    "assoc_text_a1_improved": assoc_text_a1_improved,
                    "resume_score_data": score_data
                }

                # SAME AS MANUAL TAB
                st.session_state.resume_pdf_buffer = None
                st.session_state.resume_pdf_ready = False

                st.rerun()

        @st.fragment
        def render_resume_results():
            data = st.session_state.resume_prediction_result
            prediction = data["prediction"]
            lower_bound = data["lower_bound"]
            upper_bound = data["upper_bound"]
            salary_band_label = data["salary_band_label"]
            career_stage_label = data["career_stage_label"]
            assoc_text_a1_improved = data["assoc_text_a1_improved"]
            score_data = data["resume_score_data"]

            monthly = prediction / 12
            weekly = prediction / 52
            hourly = prediction / (52 * 40)

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Resume Profile Score</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #34D399;
                    border-left: 5px solid #34D399;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>RESUME SCORE</div>
                    <div style='color: #34D399; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>{score_data["total_score"]}/100</div>
                    <div style='color: #E6EAF0; font-size: 16px; margin-top: 8px;'>{score_data["level"]} Profile</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<h3 style='text-align: center;'>Estimated Annual Salary</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #3E7DE0;
                    border-left: 5px solid #3E7DE0;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>ANNUAL SALARY (USD)</div>
                    <div style='color: #4F8EF7; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>${prediction:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Estimated Salary Level</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #818CF8;
                    border-left: 5px solid #818CF8;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>CAREER SALARY LEVEL</div>
                    <div style='color: #4F8EF7; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>{salary_band_label}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Career Stage</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #A78BFA;
                    border-left: 5px solid #A78BFA;
                    border-radius: 10px;
                    padding: 24px 32px;
                    text-align: center;
                    margin: 8px auto;
                '>
                    <div style='color: #9CA6B5; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 8px;'>
                        CAREER STAGE (PROGRESSION SEGMENT)
                    </div>
                    <div style='color: #A78BFA; font-size: 42px; font-weight: 700; letter-spacing: -1px;'>
                        {career_stage_label}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.caption(
                "Career stage is determined using an unsupervised clustering model based on "
                "experience and education."
            )

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Pattern Insight (Data Association)</h3>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #1B2A45 0%, #1B2230 100%);
                    border: 1px solid #F59E0B;
                    border-left: 5px solid #F59E0B;
                    border-radius: 10px;
                    padding: 24px 32px;
                    margin: 8px auto;
                '>
                    <div style='color: #E5E7EB; font-size: 18px; font-weight: 500; line-height: 1.4;'>{assoc_text_a1_improved}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Score Breakdown</h3>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Experience", score_data["experience_score"])
            c2.metric("Education", score_data["education_score"])
            c3.metric("Skills", score_data["skills_score"])

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Breakdown (Approximate)</h3>", unsafe_allow_html=True)
            col_m, col_w, col_h = st.columns(3)
            col_m.metric("Monthly (Approx)", f"${monthly:,.2f}")
            col_w.metric("Weekly (Approx)", f"${weekly:,.2f}")
            col_h.metric("Hourly (Approx, 40hr/week)", f"${hourly:,.2f}")

            st.divider()
            st.markdown("<h3 style='text-align: center;'>Likely Salary Range (95% Confidence Interval)</h3>", unsafe_allow_html=True)
            col_low, col_high = st.columns(2)
            col_low.metric("Lower Estimate", f"${lower_bound:,.2f}")
            col_high.metric("Upper Estimate", f"${upper_bound:,.2f}")

            st.caption("Range estimated using standard deviation of model residuals observed during training.")

         # 
          #  render_currency_converter(
          #      usd_amount=prediction,
          #      location_hint=data["input_details"]["Country"],  # or company_location_code_a2
          #      widget_key="resume_a1",   # or "resume_a2"
          #  )
            st.divider()
            render_currency_converter(usd_amount=prediction, location_hint=data["input_details"]["Country"], widget_key="resume_a1")
            active_currency_a1_r = get_active_currency("resume_a1")
            active_rates_a1_r    = get_active_rates()
            render_tax_adjuster(gross_usd=prediction, location_hint=data["input_details"]["Country"], widget_key="resume_a1_tax",
                                converted_currency=active_currency_a1_r, rates=active_rates_a1_r)
            render_col_adjuster(gross_usd=prediction, work_country=data["input_details"]["Country"], widget_key="resume_a1_col")
            # -------------------------------------------------------
            # SALARY NEGOTIATION TIPS (APP 1 - RESUME)
            # -------------------------------------------------------
            st.divider()

            st.markdown("<h3 style='text-align: left;'>Salary Negotiation Tips</h3>", unsafe_allow_html=True)

            negotiation_tips_a1_r = generate_negotiation_tips_app1(
                prediction=prediction,
                salary_band_label=salary_band_label,
                career_stage_label=career_stage_label,
                experience=data["input_details"]["Years of Experience"],
                job_title=data["input_details"]["Job Title"],
                country=data["input_details"]["Country"],
                senior=1 if data["input_details"]["Senior Position"] == "Yes" else 0,
                market_type="info"
            )

            render_negotiation_tips(negotiation_tips_a1_r)

            st.caption("These tips help you approach salary discussions effectively based on your experience and role.")

            st.divider()

            # -------------------------------------------------------
            # CAREER RECOMMENDATIONS (APP 1 - RESUME)
            # -------------------------------------------------------

            insights_a1_r = generate_insights_app1(data["input_details"])

            st.markdown("<h3 style='text-align: left;'>Career Recommendations</h3>", unsafe_allow_html=True)

            recs_a1_r = generate_recommendations_app1(data["input_details"])
            render_recommendations(recs_a1_r)

            st.caption("These recommendations focus on long-term career growth and skill development based on your profile.")
            # ---------------- PDF GENERATION ----------------
            st.divider()

            if st.button("Prepare PDF Report", width='stretch', key="resume_pdf_prepare"):

                st.session_state.resume_pdf_buffer = app1_generate_resume_pdf(
                    st.session_state.resume_prediction_result
                )

                st.session_state.resume_pdf_ready = True
                st.success("PDF is ready for download.")

            # Optional hint
            if not st.session_state.resume_pdf_ready:
                st.caption("Prepare the PDF to enable download.")

            # Download button (safe)
            if st.session_state.resume_pdf_ready:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.resume_pdf_buffer,
                    file_name="resume_salary_report.pdf",
                    mime="application/pdf",
                    width='stretch',
                    key="resume_pdf_download"
                )
            else:
                st.button(
                    "Download Prediction Summary (PDF)",
                    width='stretch',
                    disabled=True,
                    key="resume_pdf_disabled"
                )
        # ==============================
        # FILE UPLOADER + RESET LOGIC
        # ==============================

        uploaded_resume = st.file_uploader(
            "Upload Resume (PDF)",
            type=["pdf"],
            key="resume_pdf_upload"
        )

        if "last_resume_name" not in st.session_state:
            st.session_state.last_resume_name = None

        current_resume_name = uploaded_resume.name if uploaded_resume else None

        if current_resume_name != st.session_state.last_resume_name:
            st.session_state.last_resume_name = current_resume_name

            st.session_state.resume_pdf_ready = False
            st.session_state.resume_pdf_buffer = None

            if uploaded_resume is None:
                st.session_state.resume_features = None
                st.session_state.resume_text = ""
                st.session_state.resume_score_data = None
                st.session_state.resume_prediction_result = None

        if "resume_features" not in st.session_state:
            st.session_state.resume_features = None
        if "resume_text" not in st.session_state:
            st.session_state.resume_text = ""
        if "resume_score_data" not in st.session_state:
            st.session_state.resume_score_data = None
        if "resume_prediction_result" not in st.session_state:
            st.session_state.resume_prediction_result = None

        if "resume_pdf_ready" not in st.session_state:
            st.session_state.resume_pdf_ready = False
        if "resume_pdf_buffer" not in st.session_state:
            st.session_state.resume_pdf_buffer = None
        # ==============================
        # EXTRACTION (no fragment — must trigger full rerun)
        # ==============================

        if uploaded_resume is not None:
            if st.button("Extract Resume Features", type="primary", width='stretch'):
                try:
                    with st.spinner("Extracting text and analyzing resume..."):
                        raw_text = extract_text_from_pdf(uploaded_resume)

                        if not raw_text.strip():
                            st.error("Could not extract readable text from the PDF.")
                            st.stop()

                        features = extract_resume_features(
                            raw_text=raw_text,
                            allowed_job_titles=app1_job_titles,
                            allowed_countries=app1_countries
                        )
                        score_data = calculate_resume_score(features)

                        st.session_state.resume_text = raw_text
                        st.session_state.resume_features = features
                        st.session_state.resume_score_data = score_data
                        st.session_state.resume_prediction_result = None

                    st.success("Resume processed successfully.")
                except Exception as e:
                    st.error("Failed to process the resume.")
                    st.exception(e)

        # ==============================
        # FRAGMENT CALL SITES
        # ==============================

        if st.session_state.resume_features is not None:
            render_resume_editor()
            render_resume_score()
            render_resume_prediction()

        if st.session_state.resume_prediction_result is not None:
            render_resume_results()
# ==================================================
# TAB 3: BULK SCANNER
# ==================================================
with tab_objects[2]:

    with st.expander("File Format & Input Guide"):
        if IS_APP1:
            st.markdown("""
**Required Columns**
Your file must contain exactly these columns with these exact names:

| Column | Type | Allowed Values |
|---|---|---|
| Age | Integer | 18 to 70 |
| Years of Experience | Float | 0.0 to 40.0 |
| Education Level | Integer | 0 (High School), 1 (Bachelor's), 2 (Master's), 3 (PhD) |
| Senior | Integer | 0 (No), 1 (Yes) |
| Gender | Text | Male, Female, Other |
| Job Title | Text | See supported job titles below |
| Country | Text | See supported countries below |

**Supported File Formats**
- CSV, XLSX, JSON, SQL
- Download the sample file from the left column to use as a template.

**Supported Job Titles**
""")
            st.code(", ".join(app1_job_titles))
            st.markdown("""
**Supported Countries**
""")
            st.code(", ".join(app1_countries))
            st.markdown("""
**Notes**
- Extra columns in your file are ignored — only the required columns are used.
- If your country is not in the supported list, use `Other`.
- Age minus Years of Experience must be at least 18 (unrealistic experience for age will be flagged).
- Maximum file size is 50,000 rows. Files above 10,000 rows may be slower to process.
            """)

        else:
            st.markdown("""
**Required Columns**
Your file must contain exactly these columns with these exact names:

| Column | Type | Allowed Values |
|---|---|---|
| experience_level | Text | EN (Entry), MI (Mid), SE (Senior), EX (Executive) |
| employment_type | Text | FT (Full Time), PT (Part Time), CT (Contract), FL (Freelance) |
| job_title | Text | See supported job titles below |
| employee_residence | Text | ISO 2-letter country code (e.g. US, IN, GB) |
| remote_ratio | Integer | 0 (On-site), 50 (Hybrid), 100 (Fully Remote) |
| company_location | Text | ISO 2-letter country code (e.g. US, IN, GB) |
| company_size | Text | S (Small), M (Medium), L (Large) |

**Supported File Formats**
- CSV, XLSX, JSON, SQL
- Download the sample file from the left column to use as a template.

**Supported Job Titles**
""")
            st.code(", ".join(app2_job_titles))
            st.markdown("""
**Supported Country Codes**
""")
            st.code(", ".join(sorted(COUNTRY_NAME_MAP.keys())))
            st.markdown("""
**Notes**
- Extra columns in your file are ignored — only the required columns are used.
- Use raw codes for experience_level, employment_type, and company_size (e.g. `FT` not `Full Time`).
- employee_residence and company_location must be valid ISO 2-letter country codes present in the supported list.
- Maximum file size is 50,000 rows. Files above 10,000 rows may be slower to process.
            """)
    col1, col2, col3 = st.columns(3)

    # -------------------------------------------------------
    # APP 1 — Batch Prediction
    # -------------------------------------------------------
    if IS_APP1:

        with col1:
            st.subheader("Sample File")
            sample_df_a1 = df_app1.head(5)
            st.markdown("**Sample Preview:**")
            st.dataframe(sample_df_a1, width='stretch')
            st.markdown("### Download Sample")
            sample_format_a1 = st.selectbox("Select sample format", ["CSV", "XLSX", "JSON", "SQL"],
                                             key="sample_format_select_a1")
            if sample_format_a1 == "CSV":
                file_data_s = sample_df_a1.to_csv(index=False).encode("utf-8")
                file_name_s = "sample.csv"
                mime_s = "text/csv"
            elif sample_format_a1 == "JSON":
                file_data_s = sample_df_a1.to_json(orient="records")
                file_name_s = "sample.json"
                mime_s = "application/json"
            elif sample_format_a1 == "XLSX":
                buffer_s = BytesIO()
                sample_df_a1.to_excel(buffer_s, index=False)
                file_data_s = buffer_s.getvalue()
                file_name_s = "sample.xlsx"
                mime_s = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                sql_lines_s = []
                for _, row in sample_df_a1.iterrows():
                    gender = str(row["Gender"]).replace("'", "''")
                    job_title = str(row["Job Title"]).replace("'", "''")
                    country = str(row["Country"]).replace("'", "''")

                    sql_lines_s.append(
                        "INSERT INTO salaries VALUES "
                        f"({row['Age']}, {row['Years of Experience']}, "
                        f"{row['Education Level']}, {row['Senior']}, "
                        f"'{gender}', '{job_title}', '{country}');"
                    )
                file_data_s = "\n".join(sql_lines_s)
                file_name_s = "sample.sql"
                mime_s = "text/sql"
            st.download_button("Download Sample File", data=file_data_s,
                               file_name=file_name_s, mime=mime_s, width='stretch')

        with col2:
            st.subheader("Upload File")
            uploaded_file_a1 = st.file_uploader("Upload CSV, JSON, XLSX or SQL",
                                                 type=["csv", "json", "xlsx", "sql"])
            st.divider()
            st.markdown("### Upload via Public Google Drive Link")
            with st.container(border=True):
                st.markdown("Paste a publicly shared Google Drive file link below.")
                st.caption("Make sure the file is set to 'Anyone with the link can view'.")
                drive_link_a1 = st.text_input(
                    "Google Drive File Link",
                    placeholder="https://drive.google.com/file/d/XXXXXXXX/view?usp=sharing"
                )
                if uploaded_file_a1 is None and not drive_link_a1:
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None

            bulk_df_a1 = None
            file_source_name_a1 = None

            if uploaded_file_a1:
                file_source_name_a1 = uploaded_file_a1.name
                if st.session_state.bulk_uploaded_name != file_source_name_a1:
                    st.session_state.bulk_uploaded_name = file_source_name_a1
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None
                try:
                    if uploaded_file_a1.name.endswith("csv"):
                        bulk_df_a1 = pd.read_csv(uploaded_file_a1)
                    elif uploaded_file_a1.name.endswith("json"):
                        bulk_df_a1 = pd.read_json(uploaded_file_a1)
                    elif uploaded_file_a1.name.endswith("xlsx"):
                        bulk_df_a1 = pd.read_excel(uploaded_file_a1)
                    elif uploaded_file_a1.name.endswith("sql"):
                        content_a1 = uploaded_file_a1.read().decode("utf-8")
                        matches_a1 = re.findall(r"VALUES\s*\((.*?)\);", content_a1)
                        rows_a1 = []
                        for match in matches_a1:
                            rows_a1.append(list(ast.literal_eval(f"({match})")))
                        bulk_df_a1 = pd.DataFrame(rows_a1, columns=APP1_REQUIRED_COLUMNS)
                except Exception:
                    st.error("The uploaded file could not be processed. Please ensure it is a valid and properly formatted file.")
                    bulk_df_a1 = None

            elif drive_link_a1:
                direct_url_a1 = convert_drive_link(drive_link_a1)
                if direct_url_a1 is None:
                    st.error("Invalid Google Drive link. Please provide a valid public sharing link.")
                else:
                    drive_format_a1 = st.selectbox("Select format of Google Drive file",
                                                    ["CSV", "XLSX", "JSON", "SQL"],
                                                    key="drive_format_select_a1")
                    try:
                        with st.spinner("Downloading file from Google Drive..."):
                            response_a1 = requests.get(direct_url_a1,timeout=20)
                        if response_a1.status_code == 200:
                            content_a1 = response_a1.content
                            file_source_name_a1 = drive_link_a1
                            if st.session_state.bulk_uploaded_name != file_source_name_a1:
                                st.session_state.bulk_uploaded_name = file_source_name_a1
                                st.session_state.bulk_result_df = None
                                st.session_state.bulk_pdf_buffer = None
                            if drive_format_a1 == "CSV":
                                bulk_df_a1 = pd.read_csv(BytesIO(content_a1))
                            elif drive_format_a1 == "JSON":
                                bulk_df_a1 = pd.read_json(BytesIO(content_a1))
                            elif drive_format_a1 == "XLSX":
                                bulk_df_a1 = pd.read_excel(BytesIO(content_a1))
                            elif drive_format_a1 == "SQL":
                                text_c = content_a1.decode("utf-8")
                                matches_a1 = re.findall(r"VALUES\s*\((.*?)\);", text_c)
                                rows_a1 = [list(ast.literal_eval(f"({m})")) for m in matches_a1]
                                bulk_df_a1 = pd.DataFrame(rows_a1, columns=APP1_REQUIRED_COLUMNS)
                        else:
                            st.error("Unable to download file from Google Drive. Please check file permissions.")
                    except Exception:
                        st.error("Error downloading or processing Google Drive file. Please verify the link and file format.")
                        bulk_df_a1 = None

            if bulk_df_a1 is not None:

                # ==============================
                # FILE SIZE CONTROL 
                # ==============================
                MAX_ROWS = 50000
                WARNING_ROWS = 10000

                row_count = len(bulk_df_a1)

                if row_count > MAX_ROWS:
                    st.error(f"File too large ({row_count} rows). Maximum allowed is {MAX_ROWS} rows.")
                    st.stop()
                elif row_count > WARNING_ROWS:
                    st.warning(f"Large file detected ({row_count} rows). Performance may be slower.")

                # ==============================
                # VALIDATION (ONLY if still valid)
                # ==============================
                if bulk_df_a1 is not None:
                    is_valid_a1, validation_error_a1 = app1_validate_bulk_dataframe(bulk_df_a1)

                    if not is_valid_a1:
                        st.error(validation_error_a1)
                        bulk_df_a1 = None
                    else:
                        bulk_df_a1 = bulk_df_a1[APP1_REQUIRED_COLUMNS]
                        st.markdown("**Uploaded File Preview:**")
                        st.dataframe(bulk_df_a1.head(), width='stretch')

        with col3:
            st.subheader("Run Prediction")
            has_data_a1 = "bulk_df_a1" in locals() and bulk_df_a1 is not None
            if not has_data_a1:
                st.info("Upload a file or provide a public Google Drive link to generate batch salary predictions.")
            else:
                run_clicked_a1 = st.button("Run Batch Prediction", width='stretch', type="primary")
                if run_clicked_a1:
                    try:
                        with st.spinner("Running batch salary prediction..."):
                            preds_a1 = app1_model.predict(bulk_df_a1)
                            band_preds_a1 = app1_salary_band_model.predict(bulk_df_a1)
                            band_labels_a1 = [SALARY_BAND_LABELS.get(b, "Unknown") for b in band_preds_a1]
                            cluster_preds_a1 = app1_cluster_model_a1.predict(
                                bulk_df_a1[["Years of Experience", "Education Level"]]
                            )
                            stage_map_a1 = app1_cluster_metadata_a1["cluster_stage_mapping"]
                            career_stage_a1 = [stage_map_a1[c] for c in cluster_preds_a1]
                            result_df_a1 = bulk_df_a1.copy()
                            result_df_a1["Predicted Annual Salary"] = preds_a1
                            result_df_a1["Estimated Salary Level"] = band_labels_a1
                            result_df_a1["Career Stage"] = career_stage_a1
                            st.session_state.bulk_result_df = result_df_a1
                    except Exception:
                        st.error("Prediction failed. Please ensure the uploaded data matches the required structure and values.")
                        st.session_state.bulk_result_df = None
                        st.session_state.bulk_pdf_buffer = None

                if st.session_state.bulk_result_df is not None:
                    st.markdown("**Result Preview:**")
                    st.dataframe(st.session_state.bulk_result_df.head(), width='stretch')
                    st.divider()
                    st.markdown("### Export Results")
                    export_format_a1 = st.selectbox("Select export format", ["CSV", "XLSX", "JSON", "SQL"],
                                                     key="export_format_select_a1")
                    result_df_a1 = st.session_state.bulk_result_df
                    export_df_a1 = result_df_a1.copy()
                    export_df_a1["Predicted Annual Salary"] = export_df_a1["Predicted Annual Salary"].round(2)
                    if export_format_a1 == "CSV":
                        file_data_e = export_df_a1.to_csv(index=False).encode("utf-8")
                        file_name_e = "results.csv"
                        mime_e = "text/csv"
                    elif export_format_a1 == "JSON":
                        file_data_e = export_df_a1.to_json(orient="records")
                        file_name_e = "results.json"
                        mime_e = "application/json"
                    elif export_format_a1 == "XLSX":
                        buffer_e = BytesIO()
                        export_df_a1.to_excel(buffer_e, index=False)
                        file_data_e = buffer_e.getvalue()
                        file_name_e = "results.xlsx"
                        mime_e = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else:
                        sql_lines_e = [
                            "CREATE TABLE IF NOT EXISTS salary_predictions ("
                            "Age INTEGER, Years_of_Experience REAL, Education_Level INTEGER, "
                            "Senior INTEGER, Gender TEXT, Job_Title TEXT, Country TEXT, "
                            "Predicted_Annual_Salary REAL, Estimated_Salary_Level TEXT, Predicted_Career_Stage);"
                        ]
                        for _, row in export_df_a1.iterrows():
                            gender = str(row["Gender"]).replace("'", "''")
                            job_title = str(row["Job Title"]).replace("'", "''")
                            country = str(row["Country"]).replace("'", "''")
                            salary_level = str(row["Estimated Salary Level"]).replace("'", "''")
                            career_stage = str(row["Career Stage"]).replace("'", "''")

                            sql_lines_e.append(
                                "INSERT INTO salary_predictions VALUES "
                                f"({row['Age']}, {row['Years of Experience']}, "
                                f"{row['Education Level']}, {row['Senior']}, "
                                f"'{gender}', '{job_title}', "
                                f"'{country}', {row['Predicted Annual Salary']}, "
                                f"'{salary_level}', '{career_stage}');"
                            )
                        file_data_e = "\n".join(sql_lines_e)
                        file_name_e = "results.sql"
                        mime_e = "text/sql"
                    st.download_button("Download File", data=file_data_e,
                                       file_name=file_name_e, mime=mime_e, width='stretch')

        # Batch Analytics — App 1
        if st.session_state.bulk_result_df is not None:

            @st.fragment
            def render_batch_analytics_a1():

                st.divider()
                st.header("Batch Prediction Analytics")

                if st.button("Prepare Batch PDF Report", width='stretch'):
                    with st.spinner("Preparing PDF report..."):
                        st.session_state.bulk_pdf_buffer = app1_generate_bulk_pdf(
                            st.session_state.bulk_result_df
                        )
                if "bulk_pdf_buffer" in st.session_state and st.session_state.bulk_pdf_buffer is not None:
                    st.download_button(
                        label="Download Batch Prediction Summary (PDF)",
                        data=st.session_state.bulk_pdf_buffer,
                        file_name="bulk_salary_summary.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )
                st.divider()
                analytics_df_a1 = st.session_state.bulk_result_df

                st.subheader("Summary Metrics")
                avg_s = analytics_df_a1["Predicted Annual Salary"].mean()
                min_s = analytics_df_a1["Predicted Annual Salary"].min()
                max_s = analytics_df_a1["Predicted Annual Salary"].max()
                std_s = analytics_df_a1["Predicted Annual Salary"].std()
                std_s = 0 if pd.isna(std_s) else std_s
                col1b, col2b, col3b, col4b, col5b = st.columns(5)
                col1b.metric("Total Records", analytics_df_a1.shape[0])
                col2b.metric("Average Salary", f"${avg_s:,.2f}")
                col3b.metric("Minimum Salary", f"${min_s:,.2f}")
                col4b.metric("Maximum Salary", f"${max_s:,.2f}")
                col5b.metric("Salary Std Deviation", f"${std_s:,.2f}")

                st.subheader("Salary Level Summary")
                level_counts = analytics_df_a1["Estimated Salary Level"].value_counts()
                low_count = level_counts.get("Early Career Range", 0)
                med_count = level_counts.get("Professional Range", 0)
                high_count = level_counts.get("Executive Range", 0)
                col_l1, col_l2, col_l3 = st.columns(3)
                col_l1.metric("Early Career Range", low_count)
                col_l2.metric("Professional Range", med_count)
                col_l3.metric("Executive Range", high_count)

                st.subheader("Career Stage Summary")
                stage_counts_a1 = analytics_df_a1["Career Stage"].value_counts()
                entry_count = stage_counts_a1.get("Entry Stage", 0)
                growth_count = stage_counts_a1.get("Growth Stage", 0)
                leader_count = stage_counts_a1.get("Leadership Stage", 0)
                col_c1, col_c2, col_c3 = st.columns(3)
                col_c1.metric("Entry Stage", entry_count)
                col_c2.metric("Growth Stage", growth_count)
                col_c3.metric("Leadership Stage", leader_count)


                st.divider()
                st.subheader("Top Salary Leaderboard")

                leaderboard_a1 = generate_salary_leaderboard(
                    df=analytics_df_a1,
                    job_col="Job Title",
                    salary_col="Predicted Annual Salary"
                )
                st.dataframe(
                    leaderboard_a1,
                    width='stretch',
                    hide_index=True
                )
                st.caption("Ranks job roles by average predicted salary in the uploaded batch. Top 3 roles are highlighted with medals.")
                st.divider()
                st.subheader("Salary Leaderboard Visualization")

                fig_lb_a1 = px.bar(
                    leaderboard_a1.head(10),
                    x="Average Salary (USD)",
                    y="Job Title",
                    orientation="h",
                    title="Top Roles by Salary",
                    #color="Average Salary (USD)",
                    color_discrete_sequence=["#60A5FA"]
                    #color_continuous_scale=[
                    #    [0.0, "#60A5FA"],
                    #    [0.5, "#4F8EF7"],
                    #    [1.0, "#818CF8"]
                    #]
                )
                fig_lb_a1.update_yaxes(categoryorder="total ascending")
                _apply_theme(fig_lb_a1)
                st.plotly_chart(fig_lb_a1, width='stretch')

                #------------------------------------------------------------
                # Sampling only for heavy scatter plots to improve performance
                plot_df_a1 = get_plot_df(analytics_df_a1)
                #------------------------------------------------------------

                st.divider()
                st.subheader("Salary Distribution")
                fig_hist_a1 = px.histogram(
                    analytics_df_a1, x="Predicted Annual Salary",
                    nbins=min(25, len(analytics_df_a1)),
                    title="Distribution of Predicted Annual Salaries",
                    color_discrete_sequence=["#4F8EF7"]
                )
                fig_hist_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
                fig_hist_a1.update_layout(xaxis_title= "Predicted Salary (USD)", yaxis_title= "Count")
                _apply_theme(fig_hist_a1)
                st.plotly_chart(fig_hist_a1, width='stretch')

                st.divider()
                st.subheader("Average Salary by Salary Level")
                band_salary_a1 = (analytics_df_a1.groupby("Estimated Salary Level")["Predicted Annual Salary"]
                                  .mean().reset_index())
                fig_band_a1 = px.bar(band_salary_a1, x="Estimated Salary Level",
                                      y="Predicted Annual Salary",
                                      title="Average Predicted Salary by Salary Level",
                                      color="Estimated Salary Level",
                                      color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"])
                fig_band_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Early Career Range",
                        "Professional Range",
                        "Executive Range"
                    ]
                )
                _apply_theme(fig_band_a1)
                st.plotly_chart(fig_band_a1, width='stretch')

                st.divider()
                st.subheader("Salary Level Distribution by Education")
                edu_band_a1 = (analytics_df_a1.groupby(["Education Level", "Estimated Salary Level"])
                               .size().reset_index(name="Count"))
                edu_band_a1["Education Level"] = edu_band_a1["Education Level"].map(
                    {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"})
                fig_edu_band_a1 = px.bar(
                    edu_band_a1, x="Education Level", y="Count",
                    color="Estimated Salary Level",
                    title="Salary Levels Across Education Levels",
                    barmode="group",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_edu_band_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                _apply_theme(fig_edu_band_a1)
                st.plotly_chart(fig_edu_band_a1, width='stretch')

                st.divider()
                st.subheader("Career Stage Distribution")

                stage_dist_a1 = (
                    analytics_df_a1["Career Stage"]
                    .value_counts()
                    .reset_index()
                )
                stage_dist_a1.columns = ["Career Stage", "Count"]

                fig_stage_dist_a1 = px.bar(
                    stage_dist_a1,
                    x="Career Stage",
                    y="Count",
                    title="Distribution of Career Stages",
                    color="Career Stage",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_stage_dist_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Entry Stage",
                        "Growth Stage",
                        "Leadership Stage"
                    ]
                )
                _apply_theme(fig_stage_dist_a1)
                st.plotly_chart(fig_stage_dist_a1, width='stretch')

                st.divider()
                st.subheader("Average Salary by Career Stage")
                stage_salary_a1 = (
                    analytics_df_a1
                    .groupby("Career Stage")["Predicted Annual Salary"]
                    .mean()
                    .reset_index()
                )
                fig_stage_salary_a1 = px.bar(
                    stage_salary_a1,
                    x="Career Stage",
                    y="Predicted Annual Salary",
                    title="Average Predicted Salary by Career Stage",
                    color="Career Stage",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_stage_salary_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Entry Stage",
                        "Growth Stage",
                        "Leadership Stage"
                    ]
                )
                _apply_theme(fig_stage_salary_a1)
                st.plotly_chart(fig_stage_salary_a1, width='stretch')

                st.divider()
                st.subheader("Career Stage Distribution by Education")

                edu_stage_a1 = (
                    analytics_df_a1
                    .groupby(["Education Level", "Career Stage"])
                    .size()
                    .reset_index(name="Count")
                )
                edu_stage_a1["Education Level"] = edu_stage_a1["Education Level"].map(
                    {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
                )
                fig_edu_stage_a1 = px.bar(
                    edu_stage_a1,
                    x="Education Level",
                    y="Count",
                    color="Career Stage",
                    title="Career Stage Distribution Across Education Levels",
                    barmode="group",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_edu_stage_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                _apply_theme(fig_edu_stage_a1)
                st.plotly_chart(fig_edu_stage_a1, width='stretch')

                st.divider()
                st.subheader("Salary vs Experience Trend")
                fig_trend_a1 = px.scatter(
                    plot_df_a1, x="Years of Experience", y="Predicted Annual Salary",
                    trendline="ols", trendline_color_override="#F59E0B",
                    title="Predicted Salary vs Experience",
                    color_discrete_sequence=["#4F8EF7"]
                )
                fig_trend_a1.update_traces(marker=dict(size=7, opacity=0.65))
                _apply_theme(fig_trend_a1)
                st.plotly_chart(fig_trend_a1, width='stretch')

                st.divider()
                st.subheader("Career Progression Landscape")
                fig_career_landscape = px.scatter(
                    plot_df_a1,
                    x="Years of Experience",
                    y="Predicted Annual Salary",
                    color="Estimated Salary Level",
                    symbol="Career Stage",
                    title="Career Progression and Salary Landscape",
                    labels={
                        "Years of Experience": "Years of Experience",
                        "Predicted Annual Salary": "Predicted Salary (USD)"
                    },
                    color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
                )
                fig_career_landscape.update_traces(
                    marker=dict(size=9, opacity=0.65)
                )
                _apply_theme(fig_career_landscape)
                st.plotly_chart(fig_career_landscape, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Education Level")
                edu_group_a1 = (analytics_df_a1.groupby("Education Level")["Predicted Annual Salary"]
                                .mean().reset_index())
                edu_group_a1["Education Level"] = edu_group_a1["Education Level"].map(
                    {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"})
                fig_edu_bulk_a1 = px.bar(
                    edu_group_a1, x="Education Level", y="Predicted Annual Salary",
                    title="Average Predicted Salary by Education",
                    color="Education Level",
                    color_discrete_sequence=["#4F8EF7", "#38BDF8", "#34D399", "#A78BFA"]
                )
                fig_edu_bulk_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                )
                _apply_theme(fig_edu_bulk_a1)
                st.plotly_chart(fig_edu_bulk_a1, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Country")
                country_group_a1 = (analytics_df_a1.groupby("Country")["Predicted Annual Salary"]
                                    .mean().reset_index()
                                    .sort_values(by="Predicted Annual Salary", ascending=False))
                fig_country_bulk_a1 = px.bar(
                    country_group_a1, x="Country", y="Predicted Annual Salary",
                    title="Average Predicted Salary by Country",
                    color="Country",
                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B","#FB923C","#F472B6","#22D3EE","#818CF8","#6EE7B7"]            )
                fig_country_bulk_a1.update_xaxes(categoryorder="total descending")
                _apply_theme(fig_country_bulk_a1)
                st.plotly_chart(fig_country_bulk_a1, width='stretch')

                st.divider()
                st.subheader("Senior vs Non-Senior Predicted Salary")
                senior_group_a1 = (analytics_df_a1.groupby("Senior")["Predicted Annual Salary"]
                                   .mean().reset_index())
                senior_group_a1["Senior"] = senior_group_a1["Senior"].map({0: "Non-Senior", 1: "Senior"})
                fig_senior_bulk_a1 = px.bar(
                    senior_group_a1, x="Senior", y="Predicted Annual Salary",
                    title="Average Predicted Salary by Seniority",
                    color="Senior",
                    color_discrete_sequence=["#38BDF8", "#4F8EF7"]
                )
                fig_senior_bulk_a1.update_xaxes(
                    categoryorder="array",
                    categoryarray=["Non-Senior", "Senior"]
                )
                _apply_theme(fig_senior_bulk_a1)
                st.plotly_chart(fig_senior_bulk_a1, width='stretch')

                st.divider()
                st.subheader("Predicted Salary Distribution by Job Title")
                job_salary_a1 = analytics_df_a1.copy()
                top_jobs_a1 = job_salary_a1["Job Title"].value_counts().head(10).index
                job_salary_a1 = job_salary_a1[job_salary_a1["Job Title"].isin(top_jobs_a1)]
                fig_job_box_a1 = px.box(
                    job_salary_a1, x="Job Title", y="Predicted Annual Salary",
                    title="Salary Distribution by Job Title (Top 10)",
                    color="Job Title",
                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA",
                                              "#F59E0B","#FB923C","#F472B6","#22D3EE","#6366F1","#14B8A6"]
                )
                fig_job_box_a1.update_layout(xaxis_title="Job Title",
                                              yaxis_title="Predicted Salary (USD)", showlegend=False)
                _apply_theme(fig_job_box_a1)
                st.plotly_chart(fig_job_box_a1, width='stretch')
            render_batch_analytics_a1()
    # -------------------------------------------------------
    # APP 2 — Batch Prediction
    # -------------------------------------------------------
    else:

        with col1:
            st.subheader("Sample File")
            sample_df_a2 = df_app2[APP2_REQUIRED_COLUMNS].head(5)
            st.markdown("Sample Preview:")
            st.dataframe(sample_df_a2, width='stretch')
            st.markdown("### Download Sample")
            sample_format_a2 = st.selectbox("Select sample format", ["CSV", "XLSX", "JSON", "SQL"],
                                             key="sample_format_select_a2")
            if sample_format_a2 == "CSV":
                file_data_s2 = sample_df_a2.to_csv(index=False).encode("utf-8")
                file_name_s2 = "salaryscope_sample.csv"
                mime_s2 = "text/csv"
            elif sample_format_a2 == "JSON":
                file_data_s2 = sample_df_a2.to_json(orient="records")
                file_name_s2 = "salaryscope_sample.json"
                mime_s2 = "application/json"
            elif sample_format_a2 == "XLSX":
                buffer_s2 = BytesIO()
                sample_df_a2.to_excel(buffer_s2, index=False)
                file_data_s2 = buffer_s2.getvalue()
                file_name_s2 = "salaryscope_sample.xlsx"
                mime_s2 = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            else:
                sql_lines_s2 = [
                    "CREATE TABLE IF NOT EXISTS salary_predictions ("
                    "experience_level TEXT, employment_type TEXT, job_title TEXT, "
                    "employee_residence TEXT, remote_ratio INTEGER, "
                    "company_location TEXT, company_size TEXT);"
                ]
                for _, row in sample_df_a2.iterrows():
                    values_s2 = []
                    for col in APP2_REQUIRED_COLUMNS:
                        v = row[col]
                        if isinstance(v, str):
                            v = v.replace("'", "''")
                            values_s2.append(f"'{v}'")
                        else:
                            values_s2.append(str(v))
                    sql_lines_s2.append(
                        f"INSERT INTO salary_predictions ({', '.join(APP2_REQUIRED_COLUMNS)}) "
                        f"VALUES ({', '.join(values_s2)});"
                    )
                file_data_s2 = "\n".join(sql_lines_s2)
                file_name_s2 = "salaryscope_sample.sql"
                mime_s2 = "text/sql"
            st.download_button("Download Sample File", data=file_data_s2,
                               file_name=file_name_s2, mime=mime_s2, width='stretch')

        with col2:
            st.subheader("Upload File")
            uploaded_file_a2 = st.file_uploader("Upload CSV, JSON, XLSX or SQL",
                                                 type=["csv", "json", "xlsx", "sql"])
            st.divider()
            st.markdown("### Upload via Public Google Drive Link")
            with st.container(border=True):
                st.markdown("Paste a publicly shared Google Drive file link below.")
                st.caption("Make sure sharing is set to 'Anyone with the link can view'.")
                drive_link_a2 = st.text_input(
                    "Google Drive File Link",
                    placeholder="https://drive.google.com/file/d/XXXX/view?usp=sharing"
                )
                if uploaded_file_a2 is None and not drive_link_a2:
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None

            bulk_df_a2 = None
            file_source_name_a2 = None

            if uploaded_file_a2:
                file_source_name_a2 = uploaded_file_a2.name
                if st.session_state.bulk_uploaded_name != file_source_name_a2:
                    st.session_state.bulk_uploaded_name = file_source_name_a2
                    st.session_state.bulk_result_df = None
                    st.session_state.bulk_pdf_buffer = None
                try:
                    if uploaded_file_a2.name.endswith("csv"):
                        bulk_df_a2 = pd.read_csv(uploaded_file_a2)
                    elif uploaded_file_a2.name.endswith("json"):
                        bulk_df_a2 = pd.read_json(uploaded_file_a2)
                    elif uploaded_file_a2.name.endswith("xlsx"):
                        bulk_df_a2 = pd.read_excel(uploaded_file_a2)
                    elif uploaded_file_a2.name.endswith("sql"):
                        content_a2 = uploaded_file_a2.read().decode("utf-8")
                        matches_a2 = re.findall(r"VALUES\s*\((.*?)\);", content_a2)
                        rows_a2 = [list(ast.literal_eval(f"({m})")) for m in matches_a2]
                        bulk_df_a2 = pd.DataFrame(rows_a2, columns=APP2_REQUIRED_COLUMNS)
                except Exception:
                    st.error("The uploaded file could not be processed. Please ensure it is a valid and properly formatted file.")
                    bulk_df_a2 = None

            elif drive_link_a2:
                direct_url_a2 = convert_drive_link(drive_link_a2)
                if direct_url_a2 is None:
                    st.error("Invalid Google Drive link. Please provide a valid public sharing link.")
                else:
                    drive_format_a2 = st.selectbox("Select format of Google Drive file",
                                                    ["CSV", "XLSX", "JSON", "SQL"],
                                                    key="drive_format_select_a2")
                    try:
                        with st.spinner("Downloading file from Google Drive..."):
                            response_a2 = requests.get(direct_url_a2, timeout=20)
                        if response_a2.status_code == 200:
                            content_a2 = response_a2.content
                            file_source_name_a2 = drive_link_a2
                            if st.session_state.bulk_uploaded_name != file_source_name_a2:
                                st.session_state.bulk_uploaded_name = file_source_name_a2
                                st.session_state.bulk_result_df = None
                                st.session_state.bulk_pdf_buffer = None
                            if drive_format_a2 == "CSV":
                                bulk_df_a2 = pd.read_csv(BytesIO(content_a2))
                            elif drive_format_a2 == "JSON":
                                bulk_df_a2 = pd.read_json(BytesIO(content_a2))
                            elif drive_format_a2 == "XLSX":
                                bulk_df_a2 = pd.read_excel(BytesIO(content_a2))
                            else:
                                text_c2 = content_a2.decode("utf-8")
                                matches_a2 = re.findall(r"VALUES\s*\((.*?)\);", text_c2)
                                rows_a2 = [list(ast.literal_eval(f"({m})")) for m in matches_a2]
                                bulk_df_a2 = pd.DataFrame(rows_a2, columns=APP2_REQUIRED_COLUMNS)
                        else:
                            st.error("Unable to download file from Google Drive. Please check file permissions.")
                    except Exception:
                        st.error("Error downloading or processing Google Drive file. Please verify the link and file format.")
                        bulk_df_a2 = None

            if bulk_df_a2 is not None:

                # ==============================
                # FILE SIZE CONTROL 
                # ==============================
                MAX_ROWS = 50000
                WARNING_ROWS = 10000

                row_count = len(bulk_df_a2)

                if row_count > MAX_ROWS:
                    st.error(f"File too large ({row_count} rows). Maximum allowed is {MAX_ROWS} rows.")
                    st.stop()
                elif row_count > WARNING_ROWS:
                    st.warning(f"Large file detected ({row_count} rows). Performance may be slower.")

                # ==============================
                # VALIDATION
                # ==============================
                if bulk_df_a2 is not None:
                    is_valid_a2, validation_error_a2 = app2_validate_bulk_dataframe(bulk_df_a2)

                    if not is_valid_a2:
                        st.error(validation_error_a2)
                        bulk_df_a2 = None
                    else:
                        bulk_df_a2 = bulk_df_a2[APP2_REQUIRED_COLUMNS]
                        st.markdown("Uploaded File Preview:")
                        st.dataframe(bulk_df_a2.head(), width='stretch')

        with col3:
            st.subheader("Run Prediction")
            has_data_a2 = "bulk_df_a2" in locals() and bulk_df_a2 is not None
            if not has_data_a2:
                st.info("Upload a file or provide a public Google Drive link to generate batch salary predictions.")
            else:
                run_clicked_a2 = st.button("Run Batch Prediction", width='stretch', type="primary")
                if run_clicked_a2:
                    try:
                        with st.spinner("Running batch salary prediction..."):
                            tf_bulk_a2 = bulk_df_a2["job_title"].apply(title_features)
                            tf_bulk_a2 = pd.DataFrame(
                                tf_bulk_a2.tolist(),
                                columns=[
                                    "title_is_junior",
                                    "title_is_senior",
                                    "title_is_exec",
                                    "title_is_mgmt",
                                    "title_domain"
                                ]
                            )
                            prediction_df_a2 = bulk_df_a2.reset_index(drop=True).copy()
                            prediction_df_a2["remote_ratio"] = prediction_df_a2["remote_ratio"].astype(int)
                            prediction_df_a2 = pd.concat([prediction_df_a2, tf_bulk_a2], axis=1)
                            prediction_df_a2["exp_x_domain"] = (
                                prediction_df_a2["experience_level"].astype(str)
                                + "_"
                                + prediction_df_a2["title_domain"].astype(str)
                            )
                            preds_log_a2 = app2_model.predict(prediction_df_a2)
                            preds_usd_a2 = np.expm1(preds_log_a2)
                            result_df_a2 = bulk_df_a2.copy()
                            result_df_a2["Predicted Annual Salary (USD)"] = np.round(preds_usd_a2, 2)
                            st.session_state.bulk_result_df = result_df_a2
                    except Exception:
                        st.error("Prediction failed. Please ensure the uploaded data matches the required structure and values.")
                        st.session_state.bulk_result_df = None
                        st.session_state.bulk_pdf_buffer = None

                if st.session_state.bulk_result_df is not None:
                    st.markdown("Result Preview:")
                    st.dataframe(st.session_state.bulk_result_df.head(), width='stretch')
                    st.divider()
                    st.markdown("### Export Results")
                    export_format_a2 = st.selectbox("Select export format", ["CSV", "XLSX", "JSON", "SQL"],
                                                     key="export_format_select_a2")
                    result_df_a2 = st.session_state.bulk_result_df
                    export_df_a2 = result_df_a2.copy()
                    export_df_a2["Predicted Annual Salary (USD)"] = export_df_a2["Predicted Annual Salary (USD)"].round(2)
                    if export_format_a2 == "CSV":
                        file_data_e2 = export_df_a2.to_csv(index=False).encode("utf-8")
                        file_name_e2 = "salary_predictions.csv"
                        mime_e2 = "text/csv"
                    elif export_format_a2 == "JSON":
                        file_data_e2 = export_df_a2.to_json(orient="records")
                        file_name_e2 = "salary_predictions.json"
                        mime_e2 = "application/json"
                    elif export_format_a2 == "XLSX":
                        buffer_e2 = BytesIO()
                        export_df_a2.to_excel(buffer_e2, index=False)
                        file_data_e2 = buffer_e2.getvalue()
                        file_name_e2 = "salary_predictions.xlsx"
                        mime_e2 = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else:
                        sql_lines_e2 = [
                            "CREATE TABLE IF NOT EXISTS salary_predictions ("
                            "experience_level TEXT, employment_type TEXT, job_title TEXT, "
                            "employee_residence TEXT, remote_ratio INTEGER, "
                            "company_location TEXT, company_size TEXT, "
                            "predicted_annual_salary_usd REAL);"
                        ]
                        for _, row in export_df_a2.iterrows():
                            exp_l = str(row["experience_level"]).replace("'","''")
                            emp_t = str(row["employment_type"]).replace("'","''")
                            jt = str(row["job_title"]).replace("'","''")
                            er = str(row["employee_residence"]).replace("'","''")
                            cl = str(row["company_location"]).replace("'","''")
                            cs = str(row["company_size"]).replace("'","''")
                            rr = int(row["remote_ratio"])
                            ps = round(float(row["Predicted Annual Salary (USD)"]), 2)
                            sql_lines_e2.append(
                                "INSERT INTO salary_predictions "
                                "(experience_level, employment_type, job_title, employee_residence, "
                                "remote_ratio, company_location, company_size, predicted_annual_salary_usd) "
                                f"VALUES ('{exp_l}', '{emp_t}', '{jt}', '{er}', {rr}, '{cl}', '{cs}', {ps});"
                            )
                        file_data_e2 = "\n".join(sql_lines_e2)
                        file_name_e2 = "salary_predictions.sql"
                        mime_e2 = "text/sql"
                    st.download_button("Download File", data=file_data_e2,
                                       file_name=file_name_e2, mime=mime_e2, width='stretch')

        # Batch Analytics — App 2
        if st.session_state.bulk_result_df is not None:
            @st.fragment
            def render_batch_analytics_a2():
                st.divider()
                st.header("Batch Prediction Analytics")

                if st.button("Prepare Batch PDF Report", width='stretch'):
                    with st.spinner("Preparing PDF report..."):
                        st.session_state.bulk_pdf_buffer = app2_generate_bulk_pdf(
                            st.session_state.bulk_result_df, COUNTRY_NAME_MAP
                        )
                if "bulk_pdf_buffer" in st.session_state and st.session_state.bulk_pdf_buffer is not None:
                    st.download_button(
                        label="Download Batch Prediction Summary (PDF)",
                        data=st.session_state.bulk_pdf_buffer,
                        file_name="bulk_salary_summary.pdf",
                        mime="application/pdf",
                        width='stretch'
                    )
                st.divider()
                analytics_df_a2 = st.session_state.bulk_result_df

                st.subheader("Summary Metrics")
                avg_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].mean()
                min_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].min()
                max_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].max()
                std_s2 = analytics_df_a2["Predicted Annual Salary (USD)"].std()
                std_s2 = 0 if pd.isna(std_s2) else std_s2
                col1c, col2c, col3c, col4c, col5c = st.columns(5)
                col1c.metric("Total Records", analytics_df_a2.shape[0])
                col2c.metric("Average Salary", f"${avg_s2:,.2f}")
                col3c.metric("Minimum Salary", f"${min_s2:,.2f}")
                col4c.metric("Maximum Salary", f"${max_s2:,.2f}")
                col5c.metric("Salary Std Deviation", f"${std_s2:,.2f}")

                st.divider()
                st.subheader("Top Salary Leaderboard")

                leaderboard_a2 = generate_salary_leaderboard(
                    df=analytics_df_a2,
                    job_col="job_title",
                    salary_col="Predicted Annual Salary (USD)"
                )
                st.dataframe(
                    leaderboard_a2,
                    width='stretch',
                    hide_index=True
                )

                st.caption(
                    "Ranks job roles by average predicted salary in the uploaded batch. "
                    "Top 3 roles are highlighted with medals."
                )
                st.divider()
                st.subheader("Salary Leaderboard Visualization")

                fig_lb_a2 = px.bar(
                    leaderboard_a2.head(10),
                    x="Average Salary (USD)",
                    y="Job Title",
                    orientation="h",
                    title="Top Roles by Salary",
                    #color="Average Salary (USD)",
                    color_discrete_sequence=["#60A5FA"]
                    #color_continuous_scale=[
                    #    [0.0, "#4F8EF7"],
                    #    [0.5, "#60A5FA"],
                    #    [1.0, "#818CF8"]
                    #]
                )
                fig_lb_a2.update_yaxes(categoryorder="total ascending")
                _apply_theme(fig_lb_a2)
                st.plotly_chart(fig_lb_a2, width='stretch')

                st.divider()
                st.subheader("Predicted Salary Distribution")
                fig_hist_a2 = px.histogram(
                    analytics_df_a2, x="Predicted Annual Salary (USD)",
                    nbins=min(25, len(analytics_df_a2)),
                    title="Distribution of Predicted Annual Salaries",
                    labels={"Predicted Annual Salary (USD)": "Predicted Annual Salary (USD)"},
                    color_discrete_sequence=["#4F8EF7"]
                )
                fig_hist_a2.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
                fig_hist_a2.update_layout(xaxis_title="Predicted Annual Salary (USD)",
                                           yaxis_title="Number of Records")
                _apply_theme(fig_hist_a2)
                st.plotly_chart(fig_hist_a2, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Experience Level")
                exp_group_a2 = (analytics_df_a2.groupby("experience_level")["Predicted Annual Salary (USD)"]
                                .mean().reset_index())
                exp_group_a2["Experience Level"] = exp_group_a2["experience_level"].map(EXPERIENCE_MAP)
                fig_exp_a2 = px.bar(
                    exp_group_a2, x="Experience Level", y="Predicted Annual Salary (USD)",
                    title="Average Predicted Annual Salary by Experience Level",
                    color="Experience Level",
                    labels={"Experience Level": "Experience Level",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                        color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA"]
                )
                fig_exp_a2.update_layout(xaxis_title="Experience Level",
                                          yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                fig_exp_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Entry Level",
                        "Mid Level",
                        "Senior Level",
                        "Executive Level"
                    ]
                )
                _apply_theme(fig_exp_a2)
                st.plotly_chart(fig_exp_a2, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Company Size")
                size_group_a2 = (analytics_df_a2.groupby("company_size")["Predicted Annual Salary (USD)"]
                                 .mean().reset_index())
                size_group_a2["Company Size"] = size_group_a2["company_size"].map(COMPANY_SIZE_MAP)
                fig_size_a2 = px.bar(
                    size_group_a2, x="Company Size", y="Predicted Annual Salary (USD)",
                    title="Average Predicted Annual Salary by Company Size",
                    color="Company Size",
                    labels={"Company Size": "Company Size",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                    color_discrete_sequence=["#38BDF8","#4F8EF7","#A78BFA"]
                )
                fig_size_a2.update_layout(xaxis_title="Company Size",
                                           yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                fig_size_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "Small Company",
                        "Medium Company",
                        "Large Company"
                    ]
                )
                _apply_theme(fig_size_a2)
                st.plotly_chart(fig_size_a2, width='stretch')

                st.divider()
                st.subheader("Average Predicted Salary by Work Mode")
                remote_group_a2 = (analytics_df_a2.groupby("remote_ratio")["Predicted Annual Salary (USD)"]
                                   .mean().reset_index())
                remote_group_a2["Work Mode"] = remote_group_a2["remote_ratio"].map(REMOTE_MAP)
                fig_remote_a2 = px.bar(
                    remote_group_a2, x="Work Mode", y="Predicted Annual Salary (USD)",
                    title="Average Predicted Annual Salary by Work Mode",
                    color="Work Mode",
                    labels={"Work Mode": "Work Mode",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                    color_discrete_sequence=["#38BDF8","#4F8EF7","#34D399"]
                )
                fig_remote_a2.update_layout(xaxis_title="Work Mode",
                                             yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                fig_remote_a2.update_xaxes(
                    categoryorder="array",
                    categoryarray=[
                        "On-site",
                        "Hybrid",
                        "Fully Remote"
                    ]
                )
                _apply_theme(fig_remote_a2)
                st.plotly_chart(fig_remote_a2, width='stretch')

                st.divider()
                st.subheader("Top Countries by Average Predicted Salary")
                country_group_a2 = (analytics_df_a2.groupby("company_location")["Predicted Annual Salary (USD)"]
                                    .mean().reset_index()
                                    .sort_values(by="Predicted Annual Salary (USD)", ascending=False)
                                    .head(10))
                country_group_a2["Country"] = country_group_a2["company_location"].map(
                    lambda x: COUNTRY_NAME_MAP.get(x, x))
                fig_country_a2 = px.bar(
                    country_group_a2, x="Country", y="Predicted Annual Salary (USD)",
                    title="Top Countries by Average Predicted Annual Salary",
                    color="Country",
                    labels={"Country": "Country",
                            "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"},
                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B","#FB923C","#F472B6","#22D3EE","#818CF8","#6EE7B7"]
                )
                fig_country_a2.update_layout(xaxis_title="Country",
                                              yaxis_title="Average Predicted Salary (USD)", showlegend=True)
                _apply_theme(fig_country_a2)
                st.plotly_chart(fig_country_a2, width='stretch')

            render_batch_analytics_a2()

# ==================================================
# TAB 4: SCENARIO ANALYSIS / WHAT-IF SIMULATION
# ==================================================
with tab_objects[3]:

    def render_scenario_tab():
        st.header("Scenario Analysis & What-If Simulation")
        st.caption(
            "Build and compare multiple salary prediction scenarios side by side. "
            "Adjust parameters, run all scenarios at once, and explore how changes "
            "in experience, education, role, or location affect estimated salary."
        )

        # ------------------------------------------------------------------
        # APP 1 — Scenario Analysis
        # ------------------------------------------------------------------
        if IS_APP1:

            st.subheader("Configure Scenarios")
            st.caption("Add up to 5 scenarios. Each scenario runs through both the salary regressor and salary level classifier.")

            if "scenarios_a1" not in st.session_state:
                st.session_state.scenarios_a1 = [
                    {
                        "label": "Scenario 1",
                        "age": 28,
                        "experience": 3.0,
                        "education": 1,
                        "senior": 0,
                        "gender": app1_genders[0],
                        "job_title": "Software Engineer" if "Software Engineer" in app1_job_titles else app1_job_titles[0],
                        "country": "USA" if "USA" in app1_countries else app1_countries[0]
                    }
                ]

            if st.button("Add Scenario", key="add_scenario_a1") and len(st.session_state.scenarios_a1) < 5:
                idx = len(st.session_state.scenarios_a1) + 1
                st.session_state.scenarios_a1.append({
                    "label": f"Scenario {idx}",
                    "age": 30,
                    "experience": 5.0,
                    "education": 1,
                    "senior": 0,
                    "gender": app1_genders[0],
                    "job_title": "Software Engineer" if "Software Engineer" in app1_job_titles else app1_job_titles[0],
                    "country": "USA" if "USA" in app1_countries else app1_countries[0]
                })

            to_delete = None

            for i, sc in enumerate(st.session_state.scenarios_a1):
                with st.container(border=True):
                    col_lbl, col_del = st.columns([6, 1])
                    with col_lbl:
                        sc["label"] = st.text_input(
                            "Scenario Name",
                            value=sc["label"],
                            key=f"sc_a1_label_{i}"
                        )
                    with col_del:
                        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                        if len(st.session_state.scenarios_a1) > 1:
                            if st.button("Remove", key=f"sc_a1_del_{i}"):
                                to_delete = i

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        sc["age"] = st.slider(
                            "Age", 18, 70, sc["age"],
                            key=f"sc_a1_age_{i}"
                        )

                        sc["gender"] = st.selectbox(
                            "Gender", app1_genders,
                            index=app1_genders.index(sc["gender"]) if sc["gender"] in app1_genders else 0,
                            key=f"sc_a1_gender_{i}"
                        )


                    with col_b:
                        sc["experience"] = st.slider(
                            "Years of Experience", 0.0, 40.0,
                            sc["experience"], step=0.5,
                            key=f"sc_a1_exp_{i}"
                        )
                        sc["senior"] = st.selectbox(
                            "Senior Position",
                            [0, 1],
                            index=sc["senior"],
                            format_func=lambda x: "Yes" if x == 1 else "No",
                            key=f"sc_a1_senior_{i}"
                        )
                    with col_c:
                        sc["education"] = st.selectbox(
                            "Education Level",
                            [0, 1, 2, 3],
                            index=sc["education"],
                            format_func=lambda x: {
                                0: "High School",
                                1: "Bachelor's",
                                2: "Master's",
                                3: "PhD"
                            }[x],
                            key=f"sc_a1_edu_{i}"
                        )

                        sc["job_title"] = st.selectbox(
                            "Job Title", app1_job_titles,
                            index=app1_job_titles.index(sc["job_title"]) if sc["job_title"] in app1_job_titles else 0,
                            key=f"sc_a1_job_{i}"
                        )
                        sc["country"] = st.selectbox(
                            "Country", app1_countries,
                            index=app1_countries.index(sc["country"]) if sc["country"] in app1_countries else 0,
                            key=f"sc_a1_country_{i}"
                        )

            if to_delete is not None:
                st.session_state.scenarios_a1.pop(to_delete)
                st.rerun()

            st.divider()

            if st.button("Run All Scenarios", type="primary", width="stretch", key="run_scenarios_a1"):

                results_a1 = []
                errors_a1 = []

                for i, sc in enumerate(st.session_state.scenarios_a1):
                    min_age = 18
                    if sc["age"] - sc["experience"] < min_age:
                        errors_a1.append(
                            f"**{sc['label']}**: Years of experience is not realistic for the selected age."
                        )
                        continue

                    input_df = pd.DataFrame([{
                        "Age": sc["age"],
                        "Years of Experience": sc["experience"],
                        "Education Level": sc["education"],
                        "Senior": sc["senior"],
                        "Gender": sc["gender"],
                        "Job Title": sc["job_title"],
                        "Country": sc["country"]
                    }])

                    pred = float(app1_model.predict(input_df)[0])
                    band = app1_salary_band_model.predict(input_df)[0]
                    band_label = SALARY_BAND_LABELS.get(band, "Unknown")

                    cluster_pred = app1_cluster_model_a1.predict(
                        pd.DataFrame([{
                            "Years of Experience": sc["experience"],
                            "Education Level": sc["education"]
                        }])
                    )[0]
                    stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})
                    career_stage = stage_map.get(int(cluster_pred), "Unknown")

                    a1_anal = load_app1_analytics()
                    std_dev = a1_anal["residual_std"]
                    lower = max(pred - 1.96 * std_dev, 0)
                    upper = pred + 1.96 * std_dev

                    results_a1.append({
                        "Scenario": sc["label"],
                        "Job Title": sc["job_title"],
                        "Experience (yrs)": sc["experience"],
                        "Education": {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}[sc["education"]],
                        "Country": sc["country"],
                        "Senior": "Yes" if sc["senior"] == 1 else "No",
                        "Predicted Salary (USD)": round(pred, 2),
                        "Lower Bound": round(lower, 2),
                        "Upper Bound": round(upper, 2),
                        "Salary Level": band_label,
                        "Career Stage": career_stage,
                    })

                for err in errors_a1:
                    st.error(err)

                st.session_state.scenario_results_a1 = results_a1
                st.session_state.scenario_pdf_ready = False
                st.session_state.scenario_pdf_buffer = None
            # ------ RESULTS ------
            if "scenario_results_a1" in st.session_state and st.session_state.scenario_results_a1:
                @st.fragment
                def render_scenario_results_a1():
                    results_a1 = st.session_state.scenario_results_a1
                    res_df_a1 = pd.DataFrame(results_a1)

                    st.caption("Results are based on model predictions learned from historical data and may reflect dataset-specific patterns.")

                    st.divider()
                    st.subheader("Comparison Table")
                    st.dataframe(res_df_a1, width='stretch', hide_index=True)

                    best_row = res_df_a1.loc[res_df_a1["Predicted Salary (USD)"].idxmax()]
                    st.success(f"Highest predicted salary: {best_row['Scenario']} — ${best_row['Predicted Salary (USD)']:,.0f}")
                    
                    st.divider()
                    st.subheader("Predicted Salary Comparison")

                    fig_sc_bar_a1 = px.bar(
                        res_df_a1,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Scenario",
                        title="Predicted Annual Salary by Scenario",
                        color_discrete_sequence=_COLORWAY,
                        text="Predicted Salary (USD)"
                    )
                    fig_sc_bar_a1.update_traces(
                        texttemplate="$%{text:,.0f}",
                        textposition="outside"
                    )
                    _apply_theme(fig_sc_bar_a1)
                    st.plotly_chart(fig_sc_bar_a1, width='stretch')
                    st.caption("This chart compares predicted salaries across different user-defined scenarios.")

                    st.divider()
                    st.subheader("Salary Range (95% Confidence Interval)")

                    fig_ci_a1 = go.Figure()
                    for _, row in res_df_a1.iterrows():
                        fig_ci_a1.add_trace(go.Bar(
                            name=row["Scenario"],
                            x=[row["Scenario"]],
                            y=[row["Upper Bound"] - row["Lower Bound"]],
                            base=[row["Lower Bound"]],
                            text=f"${row['Predicted Salary (USD)']:,.0f}",
                            textposition="outside",
                        ))
                    fig_ci_a1.add_trace(go.Scatter(
                        x=res_df_a1["Scenario"],
                        y=res_df_a1["Predicted Salary (USD)"],
                        mode="markers",
                        marker=dict(color="#fef6e4", size=10),
                        name="Point Estimate"
                    ))
                    _apply_theme(fig_ci_a1, {
                        "title": "Salary Confidence Intervals per Scenario",
                        "barmode": "overlay",
                        "yaxis_title": "Salary (USD)"
                    })
                    st.plotly_chart(fig_ci_a1, width='stretch')

                    st.divider()
                    st.subheader("Salary Level Distribution Across Scenarios")

                    fig_band_sc_a1 = px.bar(
                        res_df_a1,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Salary Level",
                        title="Scenarios Colored by Salary Level",
                        color_discrete_map={
                            "Early Career Range": "#38BDF8",
                            "Professional Range": "#4F8EF7",
                            "Executive Range": "#A78BFA"
                        }
                    )
                    _apply_theme(fig_band_sc_a1)
                    st.plotly_chart(fig_band_sc_a1, width='stretch')

                    st.divider()
                    st.subheader("Career Stage Across Scenarios")

                    fig_stage_sc_a1 = px.bar(
                        res_df_a1,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Career Stage",
                        title="Scenarios Colored by Career Stage",
                        color_discrete_map={
                            "Entry Stage": "#38BDF8",
                            "Growth Stage": "#4F8EF7",
                            "Leadership Stage": "#A78BFA"
                        }
                    )
                    _apply_theme(fig_stage_sc_a1)
                    st.plotly_chart(fig_stage_sc_a1, width='stretch')

                    st.divider()
                    st.subheader("Experience vs Predicted Salary")

                    fig_exp_sc_a1 = px.scatter(
                        res_df_a1,
                        x="Experience (yrs)",
                        y="Predicted Salary (USD)",
                        color="Scenario",
                        size="Predicted Salary (USD)",
                        hover_data=["Job Title", "Education", "Country", "Salary Level", "Career Stage"],
                        title="Experience vs Predicted Salary (Bubble = Salary Magnitude)",
                        color_discrete_sequence=_COLORWAY,
                        text="Scenario"
                    )
                    fig_exp_sc_a1.update_traces(textposition="top center")
                    _apply_theme(fig_exp_sc_a1)
                    st.plotly_chart(fig_exp_sc_a1, width='stretch')

                    st.divider()
                    st.subheader("Salary Sensitivity — Experience Sweep")
                    st.caption(
                        "Pick one scenario as a baseline and see how predicted salary changes "
                        "as Years of Experience increases from 0 to 40, holding all other inputs fixed."
                    )

                    sweep_scenario_a1 = st.selectbox(
                        "Select Baseline Scenario for Sweep",
                        options=[sc["label"] for sc in st.session_state.scenarios_a1],
                        key="sweep_scenario_select_a1"
                    )

                    base_sc_a1 = next(
                        (s for s in st.session_state.scenarios_a1 if s["label"] == sweep_scenario_a1),
                        st.session_state.scenarios_a1[0]
                    )

                    sweep_exp_vals = [x * 0.5 for x in range(0, 81)]
                    sweep_rows = []
                    for exp_val in sweep_exp_vals:
                        sweep_df = pd.DataFrame([{
                            "Age": max(base_sc_a1["age"], int(18 + exp_val)),
                            "Years of Experience": exp_val,
                            "Education Level": base_sc_a1["education"],
                            "Senior": base_sc_a1["senior"],
                            "Gender": base_sc_a1["gender"],
                            "Job Title": base_sc_a1["job_title"],
                            "Country": base_sc_a1["country"]
                        }])
                        sweep_pred = float(app1_model.predict(sweep_df)[0])
                        sweep_rows.append({"Years of Experience": exp_val, "Predicted Salary (USD)": sweep_pred})

                    sweep_df_plot = pd.DataFrame(sweep_rows)

                    fig_sweep_a1 = px.line(
                        sweep_df_plot,
                        x="Years of Experience",
                        y="Predicted Salary (USD)",
                        title=f"Salary Sensitivity: Experience Sweep — {sweep_scenario_a1}",
                        color_discrete_sequence=["#4F8EF7"]
                    )
                    fig_sweep_a1.update_traces(line=dict(width=2.5))
                    _apply_theme(fig_sweep_a1)
                    st.plotly_chart(fig_sweep_a1, width='stretch')
                    st.caption("This chart shows how predicted salary changes as years of experience increase while all other factors remain constant.")

                    st.divider()
                    st.subheader("Salary Sensitivity — Education Sweep")
                    st.caption(
                        "See how predicted salary changes across each education level "
                        "for the selected baseline scenario."
                    )

                    edu_labels = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
                    edu_sweep_rows = []
                    for edu_val in [0, 1, 2, 3]:
                        edu_sweep_df = pd.DataFrame([{
                            "Age": base_sc_a1["age"],
                            "Years of Experience": base_sc_a1["experience"],
                            "Education Level": edu_val,
                            "Senior": base_sc_a1["senior"],
                            "Gender": base_sc_a1["gender"],
                            "Job Title": base_sc_a1["job_title"],
                            "Country": base_sc_a1["country"]
                        }])
                        edu_pred = float(app1_model.predict(edu_sweep_df)[0])
                        edu_sweep_rows.append({
                            "Education": edu_labels[edu_val],
                            "Predicted Salary (USD)": edu_pred
                        })

                    edu_sweep_df_plot = pd.DataFrame(edu_sweep_rows)

                    fig_edu_sweep_a1 = px.bar(
                        edu_sweep_df_plot,
                        x="Education",
                        y="Predicted Salary (USD)",
                        title=f"Salary by Education Level — {sweep_scenario_a1}",
                        color="Education",
                        color_discrete_sequence=["#4F8EF7", "#38BDF8", "#34D399", "#A78BFA"],
                        text="Predicted Salary (USD)"
                    )
                    fig_edu_sweep_a1.update_traces(
                        texttemplate="$%{text:,.0f}",
                        textposition="outside"
                    )
                    fig_edu_sweep_a1.update_xaxes(
                        categoryorder="array",
                        categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
                    )
                    _apply_theme(fig_edu_sweep_a1)
                    st.plotly_chart(fig_edu_sweep_a1, width='stretch')
                    st.caption("This chart compares predicted salary across different education levels for the same baseline profile.")

                    st.divider()
                    st.subheader("Export Scenario Results")
                    export_format_sc_a1 = st.selectbox(
                        "Select export format",
                        ["CSV", "XLSX", "JSON"],
                        key="sc_export_format_a1"
                    )
                    if export_format_sc_a1 == "CSV":
                        sc_file_data = res_df_a1.to_csv(index=False).encode("utf-8")
                        sc_file_name = "scenario_results.csv"
                        sc_mime = "text/csv"
                    elif export_format_sc_a1 == "XLSX":
                        sc_buf = BytesIO()
                        res_df_a1.to_excel(sc_buf, index=False)
                        sc_file_data = sc_buf.getvalue()
                        sc_file_name = "scenario_results.xlsx"
                        sc_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else:
                        sc_file_data = res_df_a1.to_json(orient="records")
                        sc_file_name = "scenario_results.json"
                        sc_mime = "application/json"

                    st.download_button(
                        "Download Scenario Results",
                        data=sc_file_data,
                        file_name=sc_file_name,
                        mime=sc_mime,
                        width="stretch"
                    )
                    # ---------------- PDF GENERATION (SCENARIO APP 1) ----------------
                    st.divider()

                    if st.button("Prepare PDF Report", width='stretch', key="scenario_pdf_prepare"):

                        st.session_state.scenario_pdf_buffer = app1_generate_scenario_pdf(
                            pd.DataFrame(st.session_state.scenario_results_a1)
                        )

                        st.session_state.scenario_pdf_ready = True
                        st.success("PDF is ready for download.")

                    # Optional hint
                    if not st.session_state.get("scenario_pdf_ready", False):
                        st.caption("Prepare the PDF to enable download.")

                    # Download button (safe)
                    if st.session_state.get("scenario_pdf_ready", False):
                        st.download_button(
                            label="Download Scenario Report (PDF)",
                            data=st.session_state.scenario_pdf_buffer,
                            file_name="scenario_analysis_app1.pdf",
                            mime="application/pdf",
                            width='stretch',
                            key="scenario_pdf_download"
                        )
                    else:
                        st.button(
                            "Download Scenario Report (PDF)",
                            width='stretch',
                            disabled=True,
                            key="scenario_pdf_disabled"
                        )
                render_scenario_results_a1()

        # ------------------------------------------------------------------
        # APP 2 — Scenario Analysis
        # ------------------------------------------------------------------
        else:

            st.subheader("Configure Scenarios")
            st.caption("Add up to 5 scenarios. Each scenario runs through the XGBoost salary regressor.")

            if "scenarios_a2" not in st.session_state:
                st.session_state.scenarios_a2 = [
                    {
                        "label": "Scenario 1",
                        "experience_level": "SE",
                        "employment_type": "FT",
                        "job_title": "Data Scientist" if "Data Scientist" in app2_job_titles else app2_job_titles[0],
                        "employee_residence": "US",
                        "remote_ratio": 0,
                        "company_location": "US",
                        "company_size": "M"
                    }
                ]

            if st.button("Add Scenario", key="add_scenario_a2") and len(st.session_state.scenarios_a2) < 5:
                idx = len(st.session_state.scenarios_a2) + 1
                st.session_state.scenarios_a2.append({
                    "label": f"Scenario {idx}",
                    "experience_level": "SE",
                    "employment_type": "FT",
                    "job_title": "Data Scientist" if "Data Scientist" in app2_job_titles else app2_job_titles[0],
                    "employee_residence": "US",
                    "remote_ratio": 0,
                    "company_location": "US",
                    "company_size": "M"
                })

            to_delete_a2 = None

            for i, sc in enumerate(st.session_state.scenarios_a2):
                with st.container(border=True):
                    col_lbl, col_del = st.columns([6, 1])
                    with col_lbl:
                        sc["label"] = st.text_input(
                            "Scenario Name",
                            value=sc["label"],
                            key=f"sc_a2_label_{i}"
                        )
                    with col_del:
                        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                        if len(st.session_state.scenarios_a2) > 1:
                            if st.button("Remove", key=f"sc_a2_del_{i}"):
                                to_delete_a2 = i

                    col_a2, col_b2, col_c2 = st.columns(3)

                    exp_options_a2 = [x for x in ["EN", "MI", "SE", "EX"] if x in app2_experience_levels]
                    emp_options_a2 = [x for x in ["FT", "PT", "CT", "FL"] if x in app2_employment_types]
                    remote_options_a2 = [x for x in [0, 50, 100] if x in app2_remote_ratios]
                    size_options_a2 = list(app2_company_sizes)

                    with col_a2:
                        exp_display = st.selectbox(
                            "Experience Level",
                            [EXPERIENCE_MAP[x] for x in exp_options_a2],
                            index=exp_options_a2.index(sc["experience_level"]) if sc["experience_level"] in exp_options_a2 else 0,
                            key=f"sc_a2_exp_{i}"
                        )
                        sc["experience_level"] = EXPERIENCE_REVERSE.get(exp_display, "SE")

                        emp_display = st.selectbox(
                            "Employment Type",
                            [EMPLOYMENT_MAP[x] for x in emp_options_a2],
                            index=emp_options_a2.index(sc["employment_type"]) if sc["employment_type"] in emp_options_a2 else 0,
                            key=f"sc_a2_emp_{i}"
                        )
                        sc["employment_type"] = EMPLOYMENT_REVERSE.get(emp_display, "FT")

                    with col_b2:
                        sc["job_title"] = st.selectbox(
                            "Job Title", app2_job_titles,
                            index=app2_job_titles.index(sc["job_title"]) if sc["job_title"] in app2_job_titles else 0,
                            key=f"sc_a2_job_{i}"
                        )

                        remote_display = st.selectbox(
                            "Work Mode",
                            [REMOTE_MAP[x] for x in remote_options_a2],
                            index=remote_options_a2.index(sc["remote_ratio"]) if sc["remote_ratio"] in remote_options_a2 else 0,
                            key=f"sc_a2_remote_{i}"
                        )
                        sc["remote_ratio"] = REMOTE_REVERSE.get(remote_display, 0)

                    with col_c2:
                        # Employee residence
                        detected_res_a2_sc = COUNTRY_NAME_MAP.get(sc["employee_residence"])
                        detected_res_display_a2_sc = (
                            f"{detected_res_a2_sc} ({sc['employee_residence']})"
                            if detected_res_a2_sc else sc["employee_residence"]
                        )
                        if detected_res_display_a2_sc not in app2_employee_residence_display_options:
                            detected_res_display_a2_sc = (
                                "United States (US)"
                                if "United States (US)" in app2_employee_residence_display_options
                                else app2_employee_residence_display_options[0]
                            )
                        res_display_sc = st.selectbox(
                            "Employee Residence",
                            app2_employee_residence_display_options,
                            index=app2_employee_residence_display_options.index(detected_res_display_a2_sc),
                            key=f"sc_a2_res_{i}"
                        )
                        if res_display_sc == "Other":
                            sc["employee_residence"] = "US"
                        elif "(" in res_display_sc:
                            sc["employee_residence"] = res_display_sc.split("(")[-1].replace(")", "").strip()
                        else:
                            sc["employee_residence"] = res_display_sc

                        # Company location
                        detected_loc_a2_sc = COUNTRY_NAME_MAP.get(sc["company_location"])
                        detected_loc_display_a2_sc = (
                            f"{detected_loc_a2_sc} ({sc['company_location']})"
                            if detected_loc_a2_sc else sc["company_location"]
                        )
                        if detected_loc_display_a2_sc not in app2_country_display_options:
                            detected_loc_display_a2_sc = (
                                "United States (US)"
                                if "United States (US)" in app2_country_display_options
                                else app2_country_display_options[0]
                            )
                        loc_display_sc = st.selectbox(
                            "Company Location",
                            app2_country_display_options,
                            index=app2_country_display_options.index(detected_loc_display_a2_sc),
                            key=f"sc_a2_loc_{i}"
                        )
                        if "(" in loc_display_sc:
                            sc["company_location"] = loc_display_sc.split("(")[-1].replace(")", "").strip()
                        else:
                            sc["company_location"] = loc_display_sc

                        size_display_sc = st.selectbox(
                            "Company Size",
                            [COMPANY_SIZE_MAP[x] for x in size_options_a2],
                            index=size_options_a2.index(sc["company_size"]) if sc["company_size"] in size_options_a2 else 0,
                            key=f"sc_a2_size_{i}"
                        )
                        sc["company_size"] = COMPANY_SIZE_REVERSE.get(size_display_sc, "M")

            if to_delete_a2 is not None:
                st.session_state.scenarios_a2.pop(to_delete_a2)
                st.rerun()

            st.divider()

            if st.button("Run All Scenarios", type="primary", width="stretch", key="run_scenarios_a2"):

                results_a2 = []

                for sc in st.session_state.scenarios_a2:
                    try:
                        jr, sr, ex, mg, dom = title_features(sc["job_title"])
                        exp_x_dom = f"{sc['experience_level']}_{dom}"

                        input_df_a2_sc = pd.DataFrame([{
                            "experience_level": sc["experience_level"],
                            "employment_type": sc["employment_type"],
                            "job_title": sc["job_title"],
                            "employee_residence": sc["employee_residence"],
                            "remote_ratio": int(sc["remote_ratio"]),
                            "company_location": sc["company_location"],
                            "company_size": sc["company_size"],
                            "title_is_junior": jr,
                            "title_is_senior": sr,
                            "title_is_exec": ex,
                            "title_is_mgmt": mg,
                            "title_domain": dom,
                            "exp_x_domain": exp_x_dom
                        }])

                        pred_log = app2_model.predict(input_df_a2_sc)[0]
                        pred_usd = float(np.expm1(pred_log))

                        res_name = COUNTRY_NAME_MAP.get(sc["employee_residence"], sc["employee_residence"])
                        loc_name = COUNTRY_NAME_MAP.get(sc["company_location"], sc["company_location"])

                        results_a2.append({
                            "Scenario": sc["label"],
                            "Job Title": sc["job_title"],
                            "Experience Level": EXPERIENCE_MAP.get(sc["experience_level"], sc["experience_level"]),
                            "Employment": EMPLOYMENT_MAP.get(sc["employment_type"], sc["employment_type"]),
                            "Work Mode": REMOTE_MAP.get(sc["remote_ratio"], str(sc["remote_ratio"])),
                            "Company Size": COMPANY_SIZE_MAP.get(sc["company_size"], sc["company_size"]),
                            "Residence": res_name,
                            "Company Location": loc_name,
                            "Predicted Salary (USD)": round(pred_usd, 2)
                        })

                    except Exception as e_sc:
                        st.error(f"Prediction failed for **{sc['label']}**: {e_sc}")

                st.session_state.scenario_results_a2 = results_a2

                st.session_state.scenario_pdf_ready_a2 = False
                st.session_state.scenario_pdf_buffer_a2 = None
            # ------ RESULTS ------
            if "scenario_results_a2" in st.session_state and st.session_state.scenario_results_a2:
                @st.fragment
                def render_scenario_results_a2():
                    results_a2 = st.session_state.scenario_results_a2
                    res_df_a2 = pd.DataFrame(results_a2)
                    st.caption("Results are based on model predictions learned from historical data and may reflect dataset-specific patterns.")

                    st.divider()
                    st.subheader("Comparison Table")
                    st.dataframe(res_df_a2, width='stretch', hide_index=True)

                    best_row_a2 = res_df_a2.loc[res_df_a2["Predicted Salary (USD)"].idxmax()]
                    st.success(f"Highest predicted salary: {best_row_a2['Scenario']} — ${best_row_a2['Predicted Salary (USD)']:,.0f}")

                    st.divider()
                    st.subheader("Predicted Salary Comparison")

                    fig_sc_bar_a2 = px.bar(
                        res_df_a2,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Scenario",
                        title="Predicted Annual Salary by Scenario",
                        color_discrete_sequence=_COLORWAY,
                        text="Predicted Salary (USD)"
                    )
                    fig_sc_bar_a2.update_traces(
                        texttemplate="$%{text:,.0f}",
                        textposition="outside"
                    )
                    _apply_theme(fig_sc_bar_a2)
                    st.plotly_chart(fig_sc_bar_a2, width='stretch')
                    st.caption("This chart compares predicted salaries across different user-defined scenarios.")

                    st.divider()
                    st.subheader("Salary by Experience Level")

                    fig_exp_sc_a2 = px.bar(
                        res_df_a2,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Experience Level",
                        title="Scenarios Colored by Experience Level",
                        color_discrete_map={
                            "Entry Level": "#38BDF8",
                            "Mid Level": "#4F8EF7",
                            "Senior Level": "#A78BFA",
                            "Executive Level": "#F59E0B"
                        }
                    )
                    _apply_theme(fig_exp_sc_a2)
                    st.plotly_chart(fig_exp_sc_a2, width='stretch')
                    st.caption("This chart shows how predicted salary varies across experience levels for different scenarios.")

                    st.divider()
                    st.subheader("Salary by Company Size")

                    fig_size_sc_a2 = px.bar(
                        res_df_a2,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Company Size",
                        title="Scenarios Colored by Company Size",
                        color_discrete_map={
                            "Small Company": "#38BDF8",
                            "Medium Company": "#4F8EF7",
                            "Large Company": "#A78BFA"
                        }
                    )
                    _apply_theme(fig_size_sc_a2)
                    st.plotly_chart(fig_size_sc_a2, width='stretch')
                    st.caption("This chart compares predicted salary across different company sizes for each scenario.")

                    st.divider()
                    st.subheader("Salary by Work Mode")

                    fig_remote_sc_a2 = px.bar(
                        res_df_a2,
                        x="Scenario",
                        y="Predicted Salary (USD)",
                        color="Work Mode",
                        title="Scenarios Colored by Work Mode",
                        color_discrete_map={
                            "On-site": "#38BDF8",
                            "Hybrid": "#4F8EF7",
                            "Fully Remote": "#34D399"
                        }
                    )
                    _apply_theme(fig_remote_sc_a2)
                    st.plotly_chart(fig_remote_sc_a2, width='stretch')
                    st.caption("This chart shows how predicted salary varies based on work mode (on-site, hybrid, remote).")

                    st.divider()
                    st.subheader("Salary Sensitivity — Experience Level Sweep")
                    st.caption(
                        "Pick one scenario as a baseline and see how predicted salary changes "
                        "across all four experience levels, holding all other inputs fixed."
                    )

                    sweep_scenario_a2 = st.selectbox(
                        "Select Baseline Scenario for Sweep",
                        options=[sc["label"] for sc in st.session_state.scenarios_a2],
                        key="sweep_scenario_select_a2"
                    )

                    base_sc_a2 = next(
                        (s for s in st.session_state.scenarios_a2 if s["label"] == sweep_scenario_a2),
                        st.session_state.scenarios_a2[0]
                    )

                    sweep_exp_rows_a2 = []
                    for exp_code in ["EN", "MI", "SE", "EX"]:
                        jr2, sr2, ex2, mg2, dom2 = title_features(base_sc_a2["job_title"])
                        exp_x_dom2 = f"{exp_code}_{dom2}"
                        sweep_input = pd.DataFrame([{
                            "experience_level": exp_code,
                            "employment_type": base_sc_a2["employment_type"],
                            "job_title": base_sc_a2["job_title"],
                            "employee_residence": base_sc_a2["employee_residence"],
                            "remote_ratio": int(base_sc_a2["remote_ratio"]),
                            "company_location": base_sc_a2["company_location"],
                            "company_size": base_sc_a2["company_size"],
                            "title_is_junior": jr2,
                            "title_is_senior": sr2,
                            "title_is_exec": ex2,
                            "title_is_mgmt": mg2,
                            "title_domain": dom2,
                            "exp_x_domain": exp_x_dom2
                        }])
                        sw_pred = float(np.expm1(app2_model.predict(sweep_input)[0]))
                        sweep_exp_rows_a2.append({
                            "Experience Level": EXPERIENCE_MAP[exp_code],
                            "Predicted Salary (USD)": sw_pred
                        })

                    sweep_exp_df_a2 = pd.DataFrame(sweep_exp_rows_a2)

                    fig_sweep_exp_a2 = px.line(
                        sweep_exp_df_a2,
                        x="Experience Level",
                        y="Predicted Salary (USD)",
                        title=f"Salary Sensitivity: Experience Level Sweep — {sweep_scenario_a2}",
                        markers=True,
                        color_discrete_sequence=["#4F8EF7"],
                        text="Predicted Salary (USD)"
                    )
                    fig_sweep_exp_a2.update_traces(
                        texttemplate="$%{text:,.0f}",
                        textposition="top center"
                    )
                    fig_sweep_exp_a2.update_xaxes(
                        categoryorder="array",
                        categoryarray=["Entry Level", "Mid Level", "Senior Level", "Executive Level"]
                    )
                    _apply_theme(fig_sweep_exp_a2)
                    st.plotly_chart(fig_sweep_exp_a2, width='stretch')
                    st.caption("This chart shows how predicted salary changes across experience levels while all other inputs remain constant.")

                    st.divider()
                    st.subheader("Salary Sensitivity — Company Size Sweep")
                    st.caption(
                        "See how predicted salary changes across company sizes "
                        "for the selected baseline scenario."
                    )

                    size_sweep_rows_a2 = []
                    for size_code in ["S", "M", "L"]:
                        jr3, sr3, ex3, mg3, dom3 = title_features(base_sc_a2["job_title"])
                        exp_x_dom3 = f"{base_sc_a2['experience_level']}_{dom3}"
                        size_sweep_input = pd.DataFrame([{
                            "experience_level": base_sc_a2["experience_level"],
                            "employment_type": base_sc_a2["employment_type"],
                            "job_title": base_sc_a2["job_title"],
                            "employee_residence": base_sc_a2["employee_residence"],
                            "remote_ratio": int(base_sc_a2["remote_ratio"]),
                            "company_location": base_sc_a2["company_location"],
                            "company_size": size_code,
                            "title_is_junior": jr3,
                            "title_is_senior": sr3,
                            "title_is_exec": ex3,
                            "title_is_mgmt": mg3,
                            "title_domain": dom3,
                            "exp_x_domain": exp_x_dom3
                        }])
                        sz_pred = float(np.expm1(app2_model.predict(size_sweep_input)[0]))
                        size_sweep_rows_a2.append({
                            "Company Size": COMPANY_SIZE_MAP[size_code],
                            "Predicted Salary (USD)": sz_pred
                        })

                    size_sweep_df_a2 = pd.DataFrame(size_sweep_rows_a2)

                    fig_sweep_size_a2 = px.bar(
                        size_sweep_df_a2,
                        x="Company Size",
                        y="Predicted Salary (USD)",
                        title=f"Salary by Company Size — {sweep_scenario_a2}",
                        color="Company Size",
                        color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"],
                        text="Predicted Salary (USD)"
                    )
                    fig_sweep_size_a2.update_traces(
                        texttemplate="$%{text:,.0f}",
                        textposition="outside"
                    )
                    fig_sweep_size_a2.update_xaxes(
                        categoryorder="array",
                        categoryarray=["Small Company", "Medium Company", "Large Company"]
                    )
                    _apply_theme(fig_sweep_size_a2)
                    st.plotly_chart(fig_sweep_size_a2, width='stretch')
                    st.caption("This chart shows how predicted salary changes across company sizes for the selected baseline scenario.")

                    st.divider()
                    st.subheader("Export Scenario Results")
                    export_format_sc_a2 = st.selectbox(
                        "Select export format",
                        ["CSV", "XLSX", "JSON"],
                        key="sc_export_format_a2"
                    )
                    if export_format_sc_a2 == "CSV":
                        sc_file_data_a2 = res_df_a2.to_csv(index=False).encode("utf-8")
                        sc_file_name_a2 = "scenario_results.csv"
                        sc_mime_a2 = "text/csv"
                    elif export_format_sc_a2 == "XLSX":
                        sc_buf_a2 = BytesIO()
                        res_df_a2.to_excel(sc_buf_a2, index=False)
                        sc_file_data_a2 = sc_buf_a2.getvalue()
                        sc_file_name_a2 = "scenario_results.xlsx"
                        sc_mime_a2 = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    else:
                        sc_file_data_a2 = res_df_a2.to_json(orient="records")
                        sc_file_name_a2 = "scenario_results.json"
                        sc_mime_a2 = "application/json"

                    st.download_button(
                        "Download Scenario Results",
                        data=sc_file_data_a2,
                        file_name=sc_file_name_a2,
                        mime=sc_mime_a2,
                        width="stretch"
                    )
                    # ---------------- PDF GENERATION (SCENARIO APP 2) ----------------
                    st.divider()

                    if st.button("Prepare PDF Report", width='stretch', key="scenario_pdf_prepare_a2"):

                        st.session_state.scenario_pdf_buffer_a2 = app2_generate_scenario_pdf(
                            pd.DataFrame(st.session_state.scenario_results_a2)
                        )

                        st.session_state.scenario_pdf_ready_a2 = True
                        st.success("PDF is ready for download.")

                    # Optional hint
                    if not st.session_state.get("scenario_pdf_ready_a2", False):
                        st.caption("Prepare the PDF to enable download.")

                    # Download button (safe)
                    if st.session_state.get("scenario_pdf_ready_a2", False):
                        st.download_button(
                            label="Download Scenario Report (PDF)",
                            data=st.session_state.scenario_pdf_buffer_a2,
                            file_name="scenario_analysis_app2.pdf",
                            mime="application/pdf",
                            width='stretch',
                            key="scenario_pdf_download_a2"
                        )
                    else:
                        st.button(
                            "Download Scenario Report (PDF)",
                            width='stretch',
                            disabled=True,
                            key="scenario_pdf_disabled_a2"
                        )
                render_scenario_results_a2()
    
    render_scenario_tab()
# ==================================================
# TAB 5: MODEL ANALYTICS
# ==================================================
with tab_objects[4]:

    @st.fragment
    def render_model_analytics_tab():
        st.header("Model Analytics & Performance Evaluation")

        # -------------------------------------------------------
        # APP 1 — Model Analytics
        # -------------------------------------------------------
        if IS_APP1:
            # ============================
            # LOAD PRECOMPUTED ANALYTICS
            # ============================
            a1 = load_app1_analytics()
            st.caption(
                "The model was optimized using GridSearchCV with 5-fold cross-validation "
                "and evaluated on a held-out test set. The final deployed model was "
                "retrained on the complete dataset using the selected hyperparameters."
            )
            st.divider()

            st.subheader("Performance Metrics")
            col1d, col2d = st.columns(2)
            col1d.metric("Test R²", round(app1_metadata["test_r2"], 4))
            col2d.metric("Cross-Val R² (Mean)", round(app1_metadata["cv_mean_r2"], 4))
            col3d, col4d = st.columns(2)
            col3d.metric("MAE (Test)", round(app1_metadata["mae"], 2))
            col4d.metric("RMSE (Test)", round(app1_metadata["rmse"], 2))

            st.divider()
            st.subheader("Model Comparison")
            comparison_df_a1 = pd.DataFrame(APP1_MODEL_COMPARISON)
            comparison_df_a1 = comparison_df_a1.sort_values(by="Test R²", ascending=False)

            def highlight_selected(row):
                if "Random Forest" in row["Model"]:
                    return ["background-color: #1E2A3A"] * len(row)
                return [""] * len(row)

            styled_df_a1 = comparison_df_a1.style.apply(highlight_selected, axis=1)
            st.dataframe(styled_df_a1, width='stretch')

            fig_compare_a1 = px.bar(
                comparison_df_a1, x="Model", y="Test R²",
                title="Model Comparison (Test R²)", color="Model",
                color_discrete_sequence=_MODEL_COLORS
            )
            fig_compare_a1.update_layout(xaxis_title= "Model", yaxis_title= "Test R²", showlegend= False)
            _apply_theme(fig_compare_a1)
            st.plotly_chart(fig_compare_a1, width='stretch')

            st.divider()
            st.subheader("Model Performance Radar")
            comparison_radar_a1 = comparison_df_a1.copy()
            comparison_radar_a1["MAE_norm"] = comparison_radar_a1["MAE"] / comparison_radar_a1["MAE"].max()
            comparison_radar_a1["RMSE_norm"] = comparison_radar_a1["RMSE"] / comparison_radar_a1["RMSE"].max()
            fig_radar_a1 = go.Figure()
            for _, row in comparison_radar_a1.iterrows():
                fig_radar_a1.add_trace(go.Scatterpolar(
                    r=[row["Test R²"], 1 - row["MAE_norm"], 1 - row["RMSE_norm"]],
                    theta=["R²", "MAE (inverted)", "RMSE (inverted)"],
                    fill="toself", name=row["Model"]
                ))
            fig_radar_a1.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
            _apply_theme(fig_radar_a1, {"title": "Model Performance Comparison"})
            st.plotly_chart(fig_radar_a1, width='stretch')

            st.divider()
            st.subheader("Tuned Hyperparameters")
            st.write(app1_metadata["best_params"])

            st.divider()
            st.subheader("Feature Importance")

            grouped_importance_df_a1 = a1["grouped_importance"]        
            fig_fi_a1 = px.bar(
                grouped_importance_df_a1,
                x="Importance",
                y="Original_Feature",
                orientation="h",
                title="Feature Importance (Grouped Variables)",
                color="Importance",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )

            fig_fi_a1.update_coloraxes(showscale=False)

            _apply_theme(fig_fi_a1)

            st.plotly_chart(fig_fi_a1, width='stretch')
            st.divider()
            st.subheader("Cumulative Feature Importance")
            importance_sorted_a1 = a1["importance_sorted"]
            fig_cumul_a1 = px.line(
                importance_sorted_a1, x=importance_sorted_a1.index + 1, y="Cumulative Importance",
                title="Cumulative Feature Importance", markers=True
            )
            fig_cumul_a1.update_layout(xaxis_title= "Number of Features", yaxis_title= "Cumulative Importance")
            _apply_theme(fig_cumul_a1)
            fig_cumul_a1.add_hline(y=0.80, line_dash="dash", line_color="#F59E0B")
            st.plotly_chart(fig_cumul_a1, width='stretch')

            st.header("Advanced Model Diagnostics")
            y_test_a1d = a1["y_test"]
            y_test_pred_a1d = a1["y_pred"]

            st.subheader("Predicted vs Actual Values")
            fig_avp_a1 = go.Figure()
            fig_avp_a1.add_trace(go.Scatter(x=y_test_a1d, y=y_test_pred_a1d, mode="markers",
                                             name="Predictions", marker=dict(color="#3E7DE0", opacity=0.6)))
            min_val_a1 = min(y_test_a1d.min(), y_test_pred_a1d.min())
            max_val_a1 = max(y_test_a1d.max(), y_test_pred_a1d.max())
            fig_avp_a1.add_trace(go.Scatter(x=[min_val_a1, max_val_a1], y=[min_val_a1, max_val_a1],
                                             mode="lines", name="Ideal Fit",
                                             line=dict(color="#EF4444", width=2)))
            fig_avp_a1.update_layout(title= "Predicted vs Actual Salary",
                                       xaxis_title= "Actual Salary", yaxis_title= "Predicted Salary")
            _apply_theme(fig_avp_a1)
            st.plotly_chart(fig_avp_a1, width='stretch')

            st.divider()
            st.subheader("Residual Plot")
            residuals_a1d = a1["residuals"]
            fig_res_a1 = go.Figure()
            fig_res_a1.add_trace(go.Scatter(x=y_test_pred_a1d, y=residuals_a1d, mode="markers",
                                             marker=dict(color="#3E7DE0", opacity=0.6)))
            fig_res_a1.add_hline(y=0, line_dash="dash", line_color="#EF4444")
            fig_res_a1.update_layout(title= "Residuals vs Predicted Values",
                                       xaxis_title= "Predicted Salary",
                                       yaxis_title= "Residual (Actual - Predicted)")
            _apply_theme(fig_res_a1)
            st.plotly_chart(fig_res_a1, width='stretch')

            st.divider()
            st.subheader("Residual Distribution")
            fig_rdist_a1 = px.histogram(x=residuals_a1d, nbins=30,
                                         labels={"x": "Residual"}, title="Distribution of Residuals",
                                         color_discrete_sequence=["#A78BFA"])
            fig_rdist_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            fig_rdist_a1.update_layout(xaxis_title="Residual", yaxis_title= "Count")
            _apply_theme(fig_rdist_a1)
            st.plotly_chart(fig_rdist_a1, width='stretch')

            st.divider()
            st.subheader("Random Forest Prediction Uncertainty")
            uncertainty_unc = a1["uncertainty"]
            fig_unc_a1 = px.histogram(x=uncertainty_unc, nbins=25,
                                       title="Distribution of Prediction Uncertainty Across Trees",
                                       labels={"x": "Prediction Standard Deviation", "y": "Count"},
                                       color_discrete_sequence=["#A78BFA"])
            fig_unc_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            _apply_theme(fig_unc_a1)
            st.plotly_chart(fig_unc_a1, width='stretch')

            st.divider()
            st.header("Salary Level Classification Model")
            st.caption(
                "The classifier predicts salary level categories based on input features. "
                "It complements the regression model by providing an interpretable salary band."
            )
            col1e, col2e = st.columns(2)
            col1e.metric("Accuracy", round(app1_classifier_metadata.get("accuracy", 0), 4))
            col2e.metric("F1 Score (Macro)", round(app1_classifier_metadata.get("f1_macro", 0), 4))
            col3e, col4e = st.columns(2)
            col3e.metric("Precision (Macro)", round(app1_classifier_metadata.get("precision_macro", 0), 4))
            col4e.metric("Recall (Macro)", round(app1_classifier_metadata.get("recall_macro", 0), 4))

            st.divider()
            st.subheader("Classification Model Comparison")
            classifier_comparison_df_a1 = pd.DataFrame(APP1_CLASSIFIER_MODEL_COMPARISON)
            classifier_comparison_df_a1 = classifier_comparison_df_a1.sort_values(by="F1 Score", ascending=False)

            def highlight_selected_classifier(row):
                if "HistGradientBoosting" in row["Model"]:
                    return ["background-color: #1E2A3A"] * len(row)
                return [""] * len(row)

            styled_cls_df_a1 = classifier_comparison_df_a1.style.apply(highlight_selected_classifier, axis=1)
            st.dataframe(styled_cls_df_a1, width='stretch')

            fig_cls_compare_a1 = px.bar(
                classifier_comparison_df_a1, x="Model", y="F1 Score",
                title="Classification Model Comparison (F1 Score)",
                color="Model", color_discrete_sequence=_MODEL_COLORS
            )
            fig_cls_compare_a1.update_layout(xaxis_title= "Model", yaxis_title= "F1 Score", showlegend= False)
            _apply_theme(fig_cls_compare_a1)
            st.plotly_chart(fig_cls_compare_a1, width='stretch')

            st.divider()
            st.subheader("Tuned Hyperparameters")
            st.write(app1_classifier_metadata["best_params"])

            st.divider()
            st.subheader("Confusion Matrix")

            cm_a1 = np.array(app1_classifier_metadata.get("confusion_matrix", [[0, 0, 0], [0, 0, 0], [0, 0, 0]]))

            fig_cm_a1 = px.imshow(
                cm_a1,
                text_auto=True,
                labels=dict(x="Predicted Label", y="Actual Label", color="Count"),
                x=["Early Career Range", "Professional Range", "Executive Range"],
                y=["Early Career Range", "Professional Range", "Executive Range"],
                title="Salary Level Classification Confusion Matrix",
                color_continuous_scale="Blues"
            )

            _apply_theme(fig_cm_a1)
            st.plotly_chart(fig_cm_a1, width='stretch')

            st.divider()
            st.subheader("Feature Importance (Classifier)")

            # Load feature importance from metadata (no computation)
            importance_dict = app1_classifier_metadata.get("feature_importance", {})

            importance_cls_df_a1 = (
                pd.DataFrame(list(importance_dict.items()), columns=["Feature", "Importance"])
                .sort_values(by="Importance", ascending=False)
            )
            # Reverse order so highest importance appears at the top
            importance_cls_df_a1 = importance_cls_df_a1.iloc[::-1]
            fig_cls_imp_a1 = px.bar(
                importance_cls_df_a1.head(15),
                x="Importance",
                y="Feature",
                orientation="h",
                title="Feature Importances (Salary Level Classifier)",
                color="Importance",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )

            fig_cls_imp_a1.update_coloraxes(showscale=False)

            _apply_theme(fig_cls_imp_a1)

            st.plotly_chart(fig_cls_imp_a1, width='stretch')


            # ========================================================
            # CAREER STAGE CLUSTERING MODEL ANALYTICS
            # ========================================================

            st.divider()
            st.header("Career Stage Clustering Model")

            st.caption(
                "This model segments individuals into career stages using KMeans clustering "
                "based on Years of Experience and Education Level. A derived Career Score "
                "feature enhances separation between progression levels."
            )
            # -------------------------------------------------------
            # CLUSTER QUALITY METRICS
            # -------------------------------------------------------

            st.divider()
            st.subheader("Clustering Quality Metrics")

            col1c, col2c = st.columns(2)

            col1c.metric(
                "Silhouette Score",
                round(app1_cluster_metadata_a1.get("silhouette_score", 0), 4)
            )

            col2c.metric(
                "Davies-Bouldin Score",
                round(app1_cluster_metadata_a1.get("davies_bouldin_score", 0), 4)
            )

            # -------------------------------------------------------
            # MODEL INFORMATION
            # -------------------------------------------------------
            st.divider()
            st.subheader("Model Configuration")

            config_df_cluster = pd.DataFrame({
                "Parameter": [
                    "Model Type",
                    "Training Dataset",
                    "Dataset Shape",
                    "Features Used",
                    "Engineered Feature",
                    "Number of Clusters"
                ],
                "Value": [
                    str(app1_cluster_metadata_a1.get("model_type")),
                    str(app1_cluster_metadata_a1.get("training_dataset")),
                    str(app1_cluster_metadata_a1.get("dataset_shape")),
                    ", ".join(map(str, app1_cluster_metadata_a1.get("features_used", []))),
                    str(app1_cluster_metadata_a1.get("engineered_feature")),
                    str(app1_cluster_metadata_a1.get("cluster_count"))
                ]
            })

            st.dataframe(config_df_cluster, width='stretch')


            # -------------------------------------------------------
            # CLUSTER DISTRIBUTION
            # -------------------------------------------------------

            st.divider()
            st.subheader("Cluster Distribution")

            cluster_sizes = app1_cluster_metadata_a1.get("cluster_sizes", {})
            stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})

            cluster_df = pd.DataFrame({
                "Cluster": list(cluster_sizes.keys()),
                "Count": list(cluster_sizes.values())
            })

            cluster_df["Career Stage"] = cluster_df["Cluster"].map(stage_map)

            fig_cluster_dist = px.bar(
                cluster_df,
                x="Career Stage",
                y="Count",
                title="Distribution of Career Stages",
                color="Career Stage",
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
            )

            fig_cluster_dist.update_xaxes(
                categoryorder="array",
                categoryarray=["Entry Stage", "Growth Stage", "Leadership Stage"]
            )

            _apply_theme(fig_cluster_dist)

            st.plotly_chart(fig_cluster_dist, width='stretch')

            # -------------------------------------------------------
            # CLUSTER CHARACTERISTICS
            # -------------------------------------------------------

            st.divider()
            st.subheader("Cluster Characteristics")

            cluster_stats = app1_cluster_metadata_a1.get("cluster_statistics", {})

            if cluster_stats:
                cluster_stats_df = pd.DataFrame(cluster_stats)
                cluster_stats_df["Cluster"] = cluster_stats_df.index
                cluster_stats_df["Career Stage"] = cluster_stats_df["Cluster"].map(stage_map)

                if "Years of Experience" in cluster_stats_df.columns:
                    cluster_stats_df = cluster_stats_df.sort_values("Years of Experience")
            else:
                cluster_stats_df = pd.DataFrame()

            st.dataframe(cluster_stats_df, width='stretch')

            # -------------------------------------------------------
            # EXPERIENCE VS SALARY (ACTUAL CLUSTER OUTPUT)
            # -------------------------------------------------------

            st.divider()
            st.subheader("Experience vs Salary by Career Stage")

            cluster_labels = a1["cluster_labels"]

            df_plot = df_app1.copy()
            df_plot["Career Stage"] = [
                stage_map.get(int(c), "Unknown") for c in cluster_labels
            ]

            fig_cluster_scatter = px.scatter(
                df_plot,
                x="Years of Experience",
                y="Salary",
                color="Career Stage",
                title="Experience vs Salary by Career Stage",
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
            )

            fig_cluster_scatter.update_traces(marker=dict(size=6, opacity=0.6))

            _apply_theme(fig_cluster_scatter)

            st.plotly_chart(fig_cluster_scatter, width='stretch')

            # -------------------------------------------------------
            # CLUSTER CENTROIDS
            # -------------------------------------------------------

            st.divider()
            st.subheader("Cluster Centroids (Scaled Feature Space)")

            centroids = app1_cluster_metadata_a1.get("cluster_centroids", {})

            if centroids:
                centroids_df = pd.DataFrame(centroids)
                centroids_df["Cluster"] = centroids_df.index
                centroids_df["Career Stage"] = centroids_df["Cluster"].map(stage_map)
            else:
                centroids_df = pd.DataFrame()

            st.dataframe(centroids_df, width='stretch')

            # -------------------------------------------------------
            # CLUSTER VISUALIZATION (PCA + CENTROIDS)
            # -------------------------------------------------------

            st.divider()
            st.subheader("Cluster Visualization (PCA Projection)")

            X_pca_vis = a1["X_pca"]
            cluster_labels_vis = a1["cluster_labels"]
            centroids_pca = a1["centroids_pca"]

            # Map to stage names
            stage_map = app1_cluster_metadata_a1.get("cluster_stage_mapping", {})
            stage_labels_vis = [stage_map.get(int(c), "Unknown") for c in cluster_labels_vis]

            # Create dataframe
            plot_df = pd.DataFrame({
                "PCA1": X_pca_vis[:, 0],
                "PCA2": X_pca_vis[:, 1],
                "Career Stage": stage_labels_vis
            })

            # ---- Plot points ----
            fig_cluster_pca = px.scatter(
                plot_df,
                x="PCA1",
                y="PCA2",
                color="Career Stage",
                title="Cluster Visualization (PCA Projection)",
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"],
            )

            centroid_labels = [
                stage_map.get(i, f"Cluster {i}") for i in range(len(centroids_pca))
            ]

            for i, (x, y) in enumerate(centroids_pca):
                fig_cluster_pca.add_trace(go.Scatter(
                    x=[x],
                    y=[y],
                    mode="markers+text",
                    showlegend=False,
                    marker=dict(
                        symbol="x",
                        size=14,
                        color="#EF4444",
                        line=dict(width=2),
                    ),
                    text=[centroid_labels[i]],
                    textposition="top center",
                    name=f"Centroid: {centroid_labels[i]}"
                ))

            # Style
            _apply_theme(fig_cluster_pca)
            fig_cluster_pca.update_layout(legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_cluster_pca, width='stretch')
            # -------------------------------------------------------
            # SCALER INFORMATION
            # -------------------------------------------------------

            st.divider()
            st.subheader("Feature Scaling Parameters")

            scaler_df = pd.DataFrame({
                "Feature": ["Years of Experience", "Education Level", "Career Score"],
                "Mean": app1_cluster_metadata_a1.get("scaler_mean", []),
                "Scale": app1_cluster_metadata_a1.get("scaler_scale", [])
            })

            st.dataframe(scaler_df, width='stretch')


            # ========================================================
            # ASSOCIATION RULE MINING (APRIORI)
            # ========================================================

            st.divider()
            st.header("Association Rule Mining Model")

            st.caption(
                "The Apriori algorithm identifies frequent patterns and relationships between features such as "
                "education level, experience category, job group, and salary category. "
                "Rules are evaluated using support (frequency), confidence (reliability), and lift (strength of association)."
            )

            # -----------------------------
            # LOAD RULES
            # -----------------------------
            rules_df = assoc_rules_a1_v2.copy()
            rules_df = rules_df[rules_df["lift"] > 1]
            # Clean columns (convert list → readable string)
            #rules_df["antecedents"] = rules_df["antecedents"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
            #rules_df["consequents"] = rules_df["consequents"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
            # -----------------------------
            # CLEAN RULE TEXT (Human-readable)
            # -----------------------------
            def clean_text(x):
                return (
                    x.replace("Education_Category_", "")
                     .replace("Experience_Category_", "")
                     .replace("Salary_Category_", "")
                     .replace("Job_Group_", "")
                     .replace("Country_", "")
                     .replace("_", " ")
                )

            rules_df["antecedents"] = rules_df["antecedents"].apply(
                lambda x: ", ".join([clean_text(i) for i in x]) if isinstance(x, list) else str(x)
            )

            rules_df["consequents"] = rules_df["consequents"].apply(
                lambda x: ", ".join([clean_text(i) for i in x]) if isinstance(x, list) else str(x)
            )
            # Create readable rule
            rules_df["rule"] = rules_df["antecedents"] + " → " + rules_df["consequents"]

            rules_df["support"] = rules_df["support"].round(3)
            rules_df["confidence"] = rules_df["confidence"].round(3)
            rules_df["lift"] = rules_df["lift"].round(3)
            rules_df = rules_df.sort_values(by="lift", ascending=False)
            # -----------------------------
            # RULE METRICS SUMMARY
            # -----------------------------
            st.divider()
            st.subheader("Rule Metrics Summary")

            col1r, col2r, col3r = st.columns(3)

            col1r.metric("Total Rules", len(rules_df))
            col2r.metric("Max Confidence", round(rules_df["confidence"].max(), 3))
            col3r.metric("Max Lift", round(rules_df["lift"].max(), 3))

            st.caption(
                "Higher lift (>1) indicates strong associations. "
                "Confidence represents rule reliability, while support reflects frequency in dataset."
            )
            # -----------------------------
            # TOP RULES TABLE
            # -----------------------------
            st.divider()
            st.subheader("Top Association Rules (Ranked by Lift)")

            top_rules = rules_df.sort_values(by="lift", ascending=False).head(10)

            st.dataframe(
                top_rules[["rule", "support", "confidence", "lift"]],
                width='stretch'
            )

            # -----------------------------
            # PLOT 1: TOP RULES BY LIFT
            # -----------------------------
            st.divider()
            st.subheader("Rule Strength Analysis (Lift)")

            fig_lift = px.bar(
                top_rules,
                x="lift",
                y="rule",
                orientation="h",
                title="Top Rules by Lift",
                color="lift",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )

            fig_lift.update_coloraxes(showscale=False)

            _apply_theme(fig_lift)
            st.plotly_chart(fig_lift, width='stretch')

            # -----------------------------
            # PLOT 2: SUPPORT VS CONFIDENCE
            # -----------------------------
            st.divider()
            st.subheader("Support vs Confidence Distribution")

            fig_scatter = px.scatter(
                rules_df,
                x="support",
                y="confidence",
                size="lift",
                hover_data=["rule"],
                title="Support vs Confidence (Bubble size represents Lift)",
                color="lift",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
            )

            fig_scatter.update_coloraxes(showscale=False)

            _apply_theme(fig_scatter)
            st.plotly_chart(fig_scatter, width='stretch')
            st.caption(
                "Most rules cluster at low support but high confidence, indicating strong but less frequent patterns. "
                "High-lift rules highlight meaningful associations between career attributes and salary categories."
            )

            # ========================================================
            # RESUME NLP MODULE (FEATURE EXTRACTION SYSTEM)
            # ========================================================

            st.divider()
            st.header("Resume NLP Module")

            st.caption(
                "This module processes unstructured resume text and converts it into structured "
                "features used by the machine learning model. Unlike predictive models, this is a "
                "rule-based NLP system designed for efficient and interpretable feature extraction."
            )

            # -------------------------------
            # SYSTEM OVERVIEW
            # -------------------------------
            st.subheader("System Overview")

            nlp_overview_df = pd.DataFrame({
                "Component": [
                    "Text Extraction",
                    "Text Preprocessing",
                    "Experience Extraction",
                    "Education Detection",
                    "Skill Detection",
                    "Job Title Detection",
                    "Country Detection",
                    "Seniority Derivation"
                ],
                "Method": [
                    "pdfplumber (PDF parsing)",
                    "Regex-based cleaning",
                    "Regex pattern matching",
                    "Rule-based keyword patterns",
                    "spaCy PhraseMatcher",
                    "spaCy PhraseMatcher with alias mapping",
                    "spaCy NER + alias mapping",
                    "Rule-based logic (experience + title)"
                ]
            })

            st.dataframe(nlp_overview_df, width='stretch')

            # -------------------------------
            # PIPELINE FLOW
            # -------------------------------
            st.divider()
            st.subheader("NLP Processing Pipeline")

            st.markdown("""
            **Pipeline Flow:**

            PDF Resume \u2192 Text Extraction \u2192 Text Cleaning \u2192 NLP Processing \u2192 Feature Extraction \u2192 Structured Input \u2192 Machine Learning Model
            """)

            # -------------------------------
            # DESIGN CHOICES
            # -------------------------------
            st.divider()
            st.subheader("Design Rationale")

            st.markdown("""
            - No labeled resume dataset was available for supervised NLP training  
            - Rule-based NLP ensures deterministic and interpretable outputs  
            - Faster processing compared to deep learning models  
            - Suitable for extracting structured attributes (skills, experience, etc.)
            """)

            # -------------------------------
            # LIMITATIONS
            # -------------------------------
            st.divider()
            st.subheader("Limitations")

            st.markdown("""
            - Performance depends on resume formatting and keyword presence  
            - May miss implicit or uncommon skill expressions  
            - Not designed for semantic understanding (no deep NLP model used)
            """)

            st.divider()
            analytics_pdf_buffer_a1 = cached_app1_model_analytics_pdf(
                app1_metadata,
                APP1_MODEL_COMPARISON,
                app1_classifier_metadata,
                a1,
                app1_cluster_metadata_a1,
                assoc_rules_a1_v2,
                app1_model,
                app1_salary_band_model
            )
            st.download_button(
                label="Download Model Analytics Report (PDF)",
                data=analytics_pdf_buffer_a1,
                file_name="model_analytics_report.pdf",
                mime="application/pdf",
                width='stretch'
            )

        # -------------------------------------------------------
        # APP 2 — Model Analytics
        # -------------------------------------------------------
        else:

            metadata_a2 = app2_metadata
            st.caption(
                "The salary prediction model uses an XGBoost regression model trained "
                "on the full dataset after evaluation using a held-out test split."
            )
            st.divider()

            st.subheader("Model Performance Metrics")
            col1f, col2f, col3f = st.columns(3)
            col1f.metric("Test R² (log scale)", f"{metadata_a2.get('test_r2_log_scale',0):.4f}")
            col2f.metric("MAE (USD)", f"${metadata_a2.get('mae_usd',0):,.0f}")
            col3f.metric("RMSE (USD)", f"${metadata_a2.get('rmse_usd',0):,.0f}")

            st.divider()
            st.subheader("Model Comparison")
            comparison_df_a2 = pd.DataFrame(APP2_MODEL_COMPARISON)
            comparison_df_a2 = comparison_df_a2.sort_values(by="Test R²", ascending=False)
            st.dataframe(comparison_df_a2, width='stretch')

            st.divider()
            st.subheader("Model Performance Comparison")
            fig_compare_a2 = px.bar(comparison_df_a2, x="Model", y="Test R²",
                                     color="Model", title="Model Comparison Based on Test R²", color_discrete_sequence=_MODEL_COLORS)
            fig_compare_a2.update_layout(xaxis_title="Model", yaxis_title="Test R²", showlegend=False)
            _apply_theme(fig_compare_a2)
            st.plotly_chart(fig_compare_a2, width='stretch')

            st.divider()
            st.subheader("Model Configuration")
            config_df_a2 = pd.DataFrame({
                "Parameter": [
                    "Model Type",
                    "Dataset Size",
                    "Trees (n_estimators)",
                    "Max Depth",
                    "Learning Rate",
                    "Target Transformation"
                ],
                "Value": [
                    str(metadata_a2.get("model_type")),
                    str(metadata_a2.get("dataset_size")),
                    str(metadata_a2.get("n_estimators")),
                    str(metadata_a2.get("max_depth")),
                    str(metadata_a2.get("learning_rate")),
                    str(metadata_a2.get("target_transformation"))
                ]
            })

            st.dataframe(config_df_a2, width='stretch')

            st.divider()
            analytics_a2 = load_app2_analytics()

            y_raw_a2 = analytics_a2["y_actual"]
            preds_full_a2 = analytics_a2["y_pred"]
            residuals_a2d = analytics_a2["residuals"]
            uncertainty_a2 = analytics_a2["uncertainty"]
            grouped_importance_a2 = analytics_a2["grouped_importance"]
            shap_df_a2 = analytics_a2["shap_top"]
            preds_distribution_a2 = analytics_a2["pred_distribution"]

            st.subheader("Predicted vs Actual Salaries")
            fig_avp_a2 = go.Figure()
            fig_avp_a2.add_trace(go.Scatter(x=y_raw_a2, y=preds_full_a2, mode="markers", name="Predictions",
                                             marker=dict(color="#3E7DE0", opacity=0.6)))
            min_val_a2 = min(y_raw_a2.min(), preds_full_a2.min())
            max_val_a2 = max(y_raw_a2.max(), preds_full_a2.max())
            fig_avp_a2.add_trace(go.Scatter(x=[min_val_a2, max_val_a2], y=[min_val_a2, max_val_a2],
                                             mode="lines", name="Ideal Fit", line=dict(color="#EF4444", width=2)))
            fig_avp_a2.update_layout(title= "Predicted vs Actual Salary", xaxis_title="Actual Salary", yaxis_title="Predicted Salary")
            _apply_theme(fig_avp_a2)
            st.plotly_chart(fig_avp_a2, width='stretch')

            st.divider()
            st.subheader("Residual Plot")
            fig_res_a2 = go.Figure()
            fig_res_a2.add_trace(go.Scatter(x=preds_full_a2, y=residuals_a2d, mode="markers",
                                             marker=dict(color="#3E7DE0", opacity=0.6)))
            fig_res_a2.add_hline(y=0, line_dash="dash", line_color="#EF4444")
            fig_res_a2.update_layout(title="Residuals vs Predicted Values", xaxis_title="Predicted Salary",
                                      yaxis_title="Residual (Actual - Predicted)")
            _apply_theme(fig_res_a2)
            st.plotly_chart(fig_res_a2, width='stretch')

            st.divider()
            st.subheader("Residual Distribution")
            fig_rdist_a2 = px.histogram(x=residuals_a2d, nbins=30,
                                         title="Distribution of Residuals",
                                         labels={"x": "Residual"}, color_discrete_sequence=["#A78BFA"])
            fig_rdist_a2.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            _apply_theme(fig_rdist_a2, {
                "title": "Distribution of Residuals",
                "xaxis_title": "Residual",
                "yaxis_title": "Count"
            })
            st.plotly_chart(fig_rdist_a2, width='stretch')

            st.divider()
            st.subheader("Prediction Uncertainty")

            fig_unc_a2 = px.histogram(
                x=uncertainty_a2,
                nbins=25,
                title="Distribution of Prediction Uncertainty",
                labels={
                    "x": "Prediction Standard Deviation",
                    "y": "Count"
                },
                color_discrete_sequence=["#A78BFA"]
            )

            fig_unc_a2.update_traces(
                marker_line_color="#1B2230",
                marker_line_width=0.8
            )

            _apply_theme(fig_unc_a2)

            st.plotly_chart(fig_unc_a2, width='stretch')

            st.divider()
            st.subheader("Feature Importance by Category")

            fig_grouped_a2 = px.bar(grouped_importance_a2, x="importance", y="group",
                                     orientation="h", title="Grouped Feature Importance", color="importance", color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1, "#38BDF8"]])
            fig_grouped_a2.update_coloraxes(showscale=False)
            fig_grouped_a2.update_layout(yaxis=dict(autorange="reversed"),
                                          xaxis_title="Total Model Influence", yaxis_title="Feature Group")
            _apply_theme(fig_grouped_a2)
            st.plotly_chart(fig_grouped_a2, width='stretch')

            st.subheader("Predicted Salary Distribution")
            fig_pred_dist_a2 = px.histogram(x=preds_distribution_a2, nbins=30,
                                             title="Distribution of Predicted Salaries",
                                             labels={"x": "Predicted Salary"}, color_discrete_sequence=["#A78BFA"])
            fig_pred_dist_a2.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            _apply_theme(fig_pred_dist_a2)
            st.plotly_chart(fig_pred_dist_a2, width='stretch')

            st.divider()
            st.subheader("Top Feature Drivers (SHAP Analysis)")
            st.caption(
                "SHAP values measure how strongly each feature influences the model's predictions. "
                "Higher values indicate stronger impact on predicted salary."
            )

            fig_shap_a2 = px.bar(
                shap_df_a2.head(15), x="SHAP Importance", y="Feature",
                orientation="h", color="SHAP Importance",
                color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1, "#38BDF8"]],
                title="Top Features Influencing Salary Predictions"
            )
            fig_shap_a2.update_layout(yaxis=dict(autorange="reversed"),
                                       xaxis_title="Average |SHAP Value|",
                                       yaxis_title="Feature", coloraxis_showscale=False)
            _apply_theme(fig_shap_a2)
            st.plotly_chart(fig_shap_a2, width='stretch')

            st.divider()
            analytics_pdf_buffer_a2 = cached_app2_model_analytics_pdf(
                metadata_a2,
                APP2_MODEL_COMPARISON,
                analytics_a2,
                app2_model
            )
            st.download_button(
                label="Download Model Analytics Report (PDF)",
                data=analytics_pdf_buffer_a2,
                file_name="model_analytics_report.pdf",
                mime="application/pdf",
                width='stretch'
            )
    render_model_analytics_tab()
# ==================================================
# TAB 6: DATA INSIGHTS
# ==================================================
with tab_objects[5]:

    @st.fragment
    def render_data_insights_tab():
        st.header("Dataset Insights & Exploratory Analysis")

        # -------------------------------------------------------
        # APP 1 — Data Insights
        # -------------------------------------------------------
        if IS_APP1:

            st.subheader("Dataset Overview")
            st.caption(
                "This section explores patterns within the general salary dataset used "
                "to train the prediction model. The visualizations highlight how salaries "
                "vary across education levels, experience, job roles, and geographic regions."
            )
            col1g, col2g, col3g = st.columns(3)
            col1g.metric("Total Records", df_app1.shape[0])
            col2g.metric("Total Features", df_app1.shape[1])
            col3g.metric("Unique Job Titles", df_app1["Job Title"].nunique())

            st.divider()
            st.subheader("Salary Summary Statistics")
            st.dataframe(df_app1["Salary"].describe())

            st.divider()
            st.subheader("Salary Distribution")
            fig_hist_di_a1 = px.histogram(df_app1, x="Salary", nbins=25,
                                           title="Salary Distribution",
                                           color_discrete_sequence=["#4F8EF7"])
            fig_hist_di_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            fig_hist_di_a1.update_layout(xaxis_title = "Salary (USD)", yaxis_title= "Count")
            _apply_theme(fig_hist_di_a1)
            st.plotly_chart(fig_hist_di_a1, width='stretch')

            st.divider()
            st.subheader("Average Salary by Education Level")
            edu_map_di = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
            edu_salary_di = df_app1.groupby("Education Level")["Salary"].mean().reset_index()
            edu_salary_di["Education Level"] = edu_salary_di["Education Level"].map(edu_map_di)
            fig_edu_di_a1 = px.bar(edu_salary_di, x="Education Level", y="Salary",
                                    title="Average Salary by Education",
                                    color="Education Level",
                                    color_discrete_sequence=["#4F8EF7", "#38BDF8", "#34D399", "#A78BFA"])
            fig_edu_di_a1.update_xaxes(
                categoryorder="array",
                categoryarray=["High School", "Bachelor's", "Master's", "PhD"]
            )
            _apply_theme(fig_edu_di_a1)
            st.plotly_chart(fig_edu_di_a1, width='stretch')

            st.divider()
            st.subheader("Salary vs Years of Experience")
            fig_exp_di_a1 = px.scatter(df_app1, x="Years of Experience", y="Salary",
                                        trendline="ols",trendline_color_override="#F59E0B",
                                        title="Salary vs Experience (with Trend Line)",
                                        color_discrete_sequence=["#4F8EF7"])
            fig_exp_di_a1.update_traces(marker=dict(opacity=0.55, size=5), selector=dict(mode="markers"))
            _apply_theme(fig_exp_di_a1)
            st.plotly_chart(fig_exp_di_a1, width='stretch')

            st.divider()
            st.subheader("Senior vs Non-Senior Salary Comparison")
            senior_salary_di = df_app1.groupby("Senior")["Salary"].mean().reset_index()
            senior_salary_di["Senior"] = senior_salary_di["Senior"].map({0: "Non-Senior", 1: "Senior"})
            fig_senior_di_a1 = px.bar(senior_salary_di, x="Senior", y="Salary",
                                       title="Average Salary by Seniority",
                                       color="Senior",
                                       color_discrete_sequence=["#38BDF8", "#4F8EF7"])
            fig_senior_di_a1.update_xaxes(
                categoryorder="array",
                categoryarray=["Non-Senior", "Senior"]
            )
            _apply_theme(fig_senior_di_a1)
            st.plotly_chart(fig_senior_di_a1, width='stretch')

            st.divider()
            st.subheader("Average Salary by Country")
            country_salary_di = df_app1.groupby("Country")["Salary"].mean().reset_index().sort_values(by="Salary", ascending=False)
            fig_country_di_a1 = px.bar(country_salary_di, x="Country", y="Salary",
                                        title="Average Salary by Country",
                                        color="Country",
                                        color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA",
                                                                  "#F59E0B","#FB923C","#F472B6","#22D3EE"])
            fig_country_di_a1.update_xaxes(categoryorder="total descending")
            _apply_theme(fig_country_di_a1)
            st.plotly_chart(fig_country_di_a1, width='stretch')

        # -------------------------------------------------------
        # APP 2 — Data Insights
        # -------------------------------------------------------
        else:

            st.caption(
                "This section explores patterns within the dataset used to train "
                "the salary prediction model. The visualizations highlight how "
                "salaries vary across experience levels, company sizes, work modes, "
                "job roles, and geographic regions."
            )

            data_full_di_a2 = df_app2.copy()

            EXPERIENCE_LABELS_DI = {"EN": "Entry Level", "MI": "Mid Level",
                                      "SE": "Senior Level", "EX": "Executive Level"}
            COMPANY_SIZE_LABELS_DI = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}
            WORK_MODE_LABELS_DI = {0: "On-site", 50: "Hybrid", 100: "Fully Remote"}

            data_full_di_a2["Experience Level"] = data_full_di_a2["experience_level"].map(EXPERIENCE_LABELS_DI)
            data_full_di_a2["Company Size"] = data_full_di_a2["company_size"].map(COMPANY_SIZE_LABELS_DI)
            data_full_di_a2["Work Mode"] = data_full_di_a2["remote_ratio"].map(WORK_MODE_LABELS_DI)
            data_full_di_a2["Company Location"] = data_full_di_a2["company_location"].map(
                lambda x: COUNTRY_NAME_MAP.get(x, x))

            st.subheader("Dataset Overview")
            col1h, col2h, col3h = st.columns(3)
            col1h.metric("Total Records", data_full_di_a2.shape[0])
            col2h.metric("Total Features", data_full_di_a2.shape[1])
            col3h.metric("Unique Job Titles", data_full_di_a2["job_title"].nunique())

            st.divider()
            st.subheader("Salary Summary Statistics")
            st.dataframe(data_full_di_a2["salary_in_usd"].describe())

            st.divider()
            st.subheader("Distribution of Data Science Salaries")
            fig_hist_di_a2 = px.histogram(data_full_di_a2, x="salary_in_usd", nbins=30,
                                           title="Distribution of Annual Salaries for Data Science Roles",
                                           labels={"salary_in_usd": "Annual Salary (USD)",
                                                   "count": "Number of Employees"},
                                           color_discrete_sequence=["#4F8EF7"])
            fig_hist_di_a2.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            fig_hist_di_a2.update_layout(xaxis_title="Annual Salary (USD)",
                                          yaxis_title="Number of Employees")
            _apply_theme(fig_hist_di_a2)
            st.plotly_chart(fig_hist_di_a2, width='stretch')

            st.divider()
            st.subheader("Average Salary by Experience Level")
            exp_group_di_a2 = (data_full_di_a2.groupby("Experience Level")["salary_in_usd"]
                               .mean().reset_index())
            fig_exp_di_a2 = px.bar(
                exp_group_di_a2, x="Experience Level", y="salary_in_usd",
                title="Average Annual Salary by Experience Level",
                color="Experience Level",
                labels={"Experience Level": "Professional Experience Level",
                        "salary_in_usd": "Average Annual Salary (USD)"},
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#34D399", "#A78BFA"]
            )
            fig_exp_di_a2.update_layout(xaxis_title="Professional Experience Level",
                                         yaxis_title="Average Annual Salary (USD)", showlegend=True)
            fig_exp_di_a2.update_xaxes(
                categoryorder="array",
                categoryarray=["Entry Level", "Mid Level", "Senior Level", "Executive Level"]
            )
            _apply_theme(fig_exp_di_a2)
            st.plotly_chart(fig_exp_di_a2, width='stretch')

            st.divider()
            st.subheader("Average Salary by Company Size")
            size_group_di_a2 = (data_full_di_a2.groupby("Company Size")["salary_in_usd"]
                                .mean().reset_index())
            fig_size_di_a2 = px.bar(
                size_group_di_a2, x="Company Size", y="salary_in_usd",
                title="Average Annual Salary by Company Size",
                color="Company Size",
                labels={"Company Size": "Company Size Category",
                        "salary_in_usd": "Average Annual Salary (USD)"},
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
            )
            fig_size_di_a2.update_layout(xaxis_title="Company Size Category",
                                          yaxis_title="Average Annual Salary (USD)", showlegend=True)
            fig_size_di_a2.update_xaxes(
                categoryorder="array",
                categoryarray=["Small Company", "Medium Company", "Large Company"]
            )
            _apply_theme(fig_size_di_a2)
            st.plotly_chart(fig_size_di_a2, width='stretch')

            st.divider()
            st.subheader("Average Salary by Work Mode")
            remote_group_di_a2 = (data_full_di_a2.groupby("Work Mode")["salary_in_usd"]
                                   .mean().reset_index())
            fig_remote_di_a2 = px.bar(
                remote_group_di_a2, x="Work Mode", y="salary_in_usd",
                title="Average Salary by Work Arrangement",
                color="Work Mode",
                labels={"Work Mode": "Work Arrangement",
                        "salary_in_usd": "Average Annual Salary (USD)"},
                color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"]
            )
            fig_remote_di_a2.update_layout(xaxis_title="Work Arrangement",
                                            yaxis_title="Average Annual Salary (USD)", showlegend=True)
            fig_remote_di_a2.update_xaxes(
                categoryorder="array",
                categoryarray=["On-site", "Hybrid", "Fully Remote"]
            )
            _apply_theme(fig_remote_di_a2)
            st.plotly_chart(fig_remote_di_a2, width='stretch')

            st.divider()
            st.subheader("Top Countries by Average Salary")
            country_stats = (
                data_full_di_a2.groupby("Company Location")
                .agg(
                    avg_salary=("salary_in_usd", "mean"),
                    count=("salary_in_usd", "count")
                )
                .reset_index()
            )

            # Keep only countries with sufficient data
            country_stats = country_stats[country_stats["count"] >= 14]

            # Sort by average salary (and count as tie-breaker)
            country_group_di_a2 = country_stats.sort_values(
                by=["avg_salary", "count"],
                ascending=[False, False]
            ).head(10)
            fig_country_di_a2 = px.bar(
                country_group_di_a2, x="Company Location", y="avg_salary",
                title="Top Countries with Highest Average Data Science Salaries",
                color="Company Location",
                labels={"Company Location": "Country", "salary_in_usd": "Average Annual Salary (USD)"},
                color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B",
                                          "#FB923C","#F472B6","#22D3EE", "#818CF8","#6EE7B7"]
            )
            fig_country_di_a2.update_layout(xaxis_title="Country",
                                             yaxis_title="Average Annual Salary (USD)", showlegend=True)
            _apply_theme(fig_country_di_a2)
            st.plotly_chart(fig_country_di_a2, width='stretch')

            st.divider()
            st.subheader("Salary Distribution by Job Title")
            job_stats = (
                data_full_di_a2.groupby("job_title")
                .agg(
                    count=("salary_in_usd", "count"),
                    avg_salary=("salary_in_usd", "mean")
                )
                .reset_index()
            )

            # Keep only job titles with sufficient data
            job_stats = job_stats[job_stats["count"] >= 20]

            # Select top job titles by frequency
            top_jobs_di_a2 = job_stats.sort_values(
                by="count", ascending=False
            ).head(10)["job_title"]

            job_df_di_a2 = data_full_di_a2[data_full_di_a2["job_title"].isin(top_jobs_di_a2)]
            fig_job_di_a2 = px.box(
                job_df_di_a2, x="job_title", y="salary_in_usd",
                title="Salary Distribution Across Major Data Science Roles",
                color="job_title",
                labels={"job_title": "Data Science Job Role", "salary_in_usd": "Annual Salary (USD)"},
                color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B",
                                          "#FB923C","#F472B6","#22D3EE","#818CF8","#6EE7B7"]
            )
            fig_job_di_a2.update_layout(xaxis_title="Data Science Job Role",
                                         yaxis_title="Annual Salary (USD)", showlegend=False)
            _apply_theme(fig_job_di_a2)
            st.plotly_chart(fig_job_di_a2, width='stretch')
    render_data_insights_tab()

# =================================================
# TAB 7: Add Profile Tab If Logged In
# =================================================
if st.session_state.logged_in:

    profile_index = tabs.index("Profile")

    with tab_objects[profile_index]:
        show_profile()

# ==================================================
# ADMIN TAB
# ==================================================
if "Admin" in tabs:
    admin_index = tabs.index("Admin")

    with tab_objects[admin_index]:

        from auth import is_admin

        if not is_admin():
            st.error("Access denied.")
            st.stop()

        show_admin_panel(st.session_state.username)
# ==================================================
# TAB 8: ABOUT (Merged from both apps)
# ==================================================
about_index = tabs.index("About")
with tab_objects[about_index]:
    st.markdown("## About SalaryScope")

    st.markdown(
        "SalaryScope is a web application that predicts salary based on factors like "
        "education, experience, job title, and location. "
        "It uses machine learning models to give an estimated salary along with some basic insights. "
        "The application supports manual input, resume-based prediction, and batch prediction. "
        "It is designed to help students and job seekers get a general idea of salary expectations."
    )
    with st.expander("Features & Modules"):

        col_ab1, col_ab2 = st.columns(2)

        with col_ab1:
            st.markdown("### Model 1 — General Salary (Random Forest)")
            st.markdown("""
    **Dataset:** General salary dataset (`Salary.csv`)

    **Models:**
    - Random Forest Regressor (optimized via GridSearchCV) for salary prediction
    - HistGradientBoostingClassifier (optimized via GridSearchCV) for salary level classification
    - KMeans Clustering for career stage segmentation (Entry, Growth, Leadership)
    - Apriori Algorithm for association rule mining between career attributes and salary categories

    **Input Features:**
    - Age, Years of Experience, Education Level, Senior Position, Gender, Job Title, Country

    **Salary Level Output:**
    - Early Career Range (Low)
    - Professional Range (Medium)
    - Executive Range (High)

    **Career Stage Output:**
    - Entry Stage
    - Growth Stage
    - Leadership Stage

    **Features:**
    - Manual salary prediction with salary band and career stage classification
    - Pattern insight generation using association rule mining (education, experience, job group, salary level)
    - Salary negotiation tips tailored to experience, seniority, job title, and country
    - Career recommendations based on job group and experience category
    - Resume Analysis: upload a PDF resume to extract features using NLP (spaCy, PhraseMatcher) and predict salary automatically
    - Resume scoring system with experience, education, and skills breakdown (scored out of 100)
    - Detected skill extraction from resume text using a curated technical skill lexicon
    - Batch salary estimation with salary level and career stage assignment per record
    - Predicted vs Actual diagnostics
    - Prediction confidence interval based on residual standard deviation from model evaluation
    - Classification confusion matrix & feature importance
    - Career stage clustering analytics (PCA visualization, silhouette score, Davies-Bouldin score)
    - Association rule analytics (support, confidence, lift visualizations)
    - Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries, salary levels, and career stages, and run sensitivity sweeps across experience and education
    - Multi-format export (CSV, JSON, XLSX, SQL)
    - Google Drive public link upload
    - PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
    - Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
            """)

        with col_ab2:
            st.markdown("### Model 2 — Data Science Salary (XGBoost)")
            st.markdown("""
    **Dataset:** Data science salary dataset (`ds_salaries.csv`)

    **Model:**
    - XGBoost Regressor with log-transformed target (`log1p(salary_in_usd)`)
    - Custom feature engineering on job titles (seniority, domain, management signals)
    - Interaction feature: experience level × job title domain

    **Input Features:**
    - Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

    **Features:**
    - Manual salary prediction with domain-aware smart insights and career recommendations
    - Resume Analysis: upload a PDF resume to extract features using NLP and predict salary automatically
    - Resume scoring system with experience, skills, and role relevance breakdown (scored out of 100)
    - Batch salary estimation
    - Feature importance
    - Predicted vs Actual diagnostics
    - Residual analysis
    - Prediction uncertainty distribution
    - Scenario Analysis: build up to 5 named scenarios side by side, compare predicted salaries by experience level, company size, and work mode, and run sensitivity sweeps across experience levels and company sizes
    - Multi-format export (CSV, JSON, XLSX, SQL)
    - Google Drive public link upload
    - PDF report generation (manual + resume analysis + bulk + scenario analysis + model analytics)
    - Prediction feedback collection (accuracy rating, direction, star rating, optional actual salary)
            """)

        st.divider()

        st.markdown("### Resume Analysis")
        st.markdown("""
    - Available for both models
    - Upload a PDF resume to automatically extract structured features using NLP
    - Text extraction via `pdfplumber`; feature extraction via `spaCy` with `PhraseMatcher`
    - Detects years of experience (regex), education level (pattern matching), job title (phrase matching against allowed titles), country (named entity recognition), and seniority flag
    - Skill detection from a curated lexicon of 50+ technical skills across programming, ML, data, cloud, and tools
    - Resume scoring out of 100 across three dimensions: experience (up to 50), education (up to 35), and skills (up to 30)
    - Profile strength label: Basic, Moderate, or Strong
    - Extracted fields are fully editable before prediction
    - Salary prediction using the same models as manual prediction
    - Results include annual salary, salary level, career stage, association pattern insight, confidence interval, negotiation tips, and career recommendations
        """)

        st.divider()

        st.markdown("### Prediction Feedback")
        st.markdown("""
    - Available in the Manual Prediction tab for both models
    - Appears as a collapsible expander after a prediction is generated
    - Allows users to rate whether the prediction was accurate (Yes / Somewhat / No)
    - Allows users to indicate the direction of error (Too High / About Right / Too Low)
    - Star rating from 1 to 5 for overall prediction quality
    - Optional field to enter actual or expected salary in USD
    - Available to both logged-in and anonymous users
    - Feedback is stored in Firestore under a separate `feedback/` collection alongside the prediction inputs and predicted salary
    - Submission is one-time per prediction result within a session — the form is replaced by a confirmation message after submitting
        """)

        st.divider()

        st.markdown("### Scenario Analysis")
        st.markdown("""
    - Available for both models
    - Build up to 5 fully customisable named scenarios in a single session
    - Each scenario accepts the same inputs as manual prediction for the active model
    - Run all scenarios simultaneously with a single button click
    - Side-by-side comparison table showing predicted salary, salary level, career stage (Model 1) or experience level, company size, and work mode (Model 2) per scenario
    - Bar chart comparing predicted annual salary across all scenarios with dollar labels
    - Charts colored by salary level and career stage (Model 1), or by experience level, company size, and work mode (Model 2)
    - Salary confidence interval chart showing 95% lower and upper bounds per scenario (Model 1)
    - Experience vs Salary bubble scatter plot across scenarios (Model 1)
    - Sensitivity sweep: select a baseline scenario and simulate how salary changes across a continuous experience range 0–40 years (Model 1) or across all four experience levels (Model 2), with all other inputs held fixed
    - Education level sweep: see how predicted salary shifts across High School, Bachelor's, Master's, and PhD for a selected baseline scenario (Model 1)
    - Company size sweep: see how predicted salary changes across Small, Medium, and Large companies for a selected baseline scenario (Model 2)
    - Export scenario results in CSV, XLSX, or JSON format
        """)

        st.divider()

        st.markdown("### User Account System")
        st.markdown("""
    - Email and password registration and login via Firebase Authentication
    - User profile data stored in Firestore
    - Session management via Streamlit session state (per-browser, 24-hour expiry)
        """)

        st.divider()

        st.markdown("### User Profile")
        st.markdown("""
    - Prediction history stored per logged-in user in Firestore (model, inputs, salary, timestamp)
    - Summary dashboard: total predictions, average salary, latest prediction
    - Prediction history chart (scatter plot over time, colored by model)
    - Per-prediction input detail viewer
    - Export prediction history in CSV, XLSX, or JSON format
    - Profile tab visible only when logged in
        """)

        st.divider()

        st.markdown("### Shared System Features")
        st.markdown("""
    - Model switcher to toggle between both prediction systems
    - Unified dark professional theme across the entire application
    - Dynamic tab layout: Manual Prediction, Resume Analysis, Batch Prediction, Scenario Analysis, Model Analytics, Data Insights, Profile (logged-in only), About
    - ReportLab-based multi-page PDF reports with embedded charts
    - State-managed UI to prevent re-computation on interaction
    - Google Drive public link upload for batch files
    - Predictions saved to Firestore for logged-in users
    - Structured prediction feedback collected from all users (logged-in and anonymous) and stored in Firestore
        """)

        st.divider()

        st.markdown("### Technologies Used")
        st.markdown("""
    - Python
    - Streamlit
    - Pandas / NumPy
    - Scikit-learn (Random Forest, HistGradientBoostingClassifier, KMeans, PCA, GridSearchCV)
    - XGBoost
    - MLxtend (Apriori association rule mining)
    - spaCy (NLP for resume feature extraction)
    - pdfplumber (PDF text extraction)
    - Plotly / Matplotlib
    - ReportLab (PDF generation)
    - Firebase Authentication (user login and registration)
    - Firebase Admin SDK / Firestore (user data, prediction storage, and feedback storage)
    - Requests (Cloud file retrieval)
    - bcrypt (password hashing utility)
        """)

    with st.expander("Tab Guide"):
        st.markdown("""
**Manual Prediction**
- Enter your profile details and click Predict Salary to get an instant salary estimate.
- Model 1 shows salary level, career stage, association pattern insight, negotiation tips, and career recommendations.
- Model 2 shows domain-aware smart insights, negotiation tips, and career recommendations.
- After results are shown, expand the Feedback section at the bottom to rate the prediction accuracy.

**Resume Analysis**
- Upload a PDF resume and click Extract Resume Features to run NLP-based extraction.
- Review and edit the detected fields, then click Predict Salary from Resume.
- Results include a resume score, salary estimate, career stage, pattern insight, negotiation tips, and career recommendations.

**Batch Prediction**
- Upload a file (CSV, XLSX, JSON, or SQL) or paste a public Google Drive link to run predictions on multiple records at once.
- Download the sample file first to understand the required column format.
- After prediction, a batch analytics dashboard with charts and a salary leaderboard is displayed.
- Export results in your preferred format using the dropdown and download button.

**Scenario Analysis**
- Build up to 5 named scenarios using the same inputs as manual prediction.
- Click Run All Scenarios to generate predictions for every scenario simultaneously.
- Review the comparison table, salary charts, and confidence interval ranges.
- Use the sensitivity sweep section to simulate how salary changes as experience or education varies, with all other inputs held fixed for a chosen baseline scenario.
- Export scenario results in CSV, XLSX, or JSON format.

**Model Analytics**
- Explore the performance and internals of the active model.
- Includes accuracy metrics, model comparison charts, feature importance, residual diagnostics, and prediction uncertainty.
- Model 1 additionally shows classifier metrics, clustering analytics, and association rule mining visualizations.

**Data Insights**
- Explore the dataset used to train the active model.
- Includes salary distributions and comparisons by education, experience, country, job role, company size, and work mode.

**Profile**
- Visible only when logged in.
- Shows your prediction history, summary statistics, and a timeline chart.
- Allows export of your full prediction history in CSV, XLSX, or JSON format.

**About**
- Describes the application, its models, features, and technologies.
- Contains the Tab Guide, Usage Instructions, and Limitations for reference.
        """)

    with st.expander("Usage Instructions"):
        st.markdown("""
**Getting Started**
- Select a prediction model from the dropdown at the top: Model 1 (Random Forest) for general salary prediction, or Model 2 (XGBoost) for data science roles.
- The active model applies across all tabs.

**Manual Prediction**
- Fill in all input fields in the Manual Prediction tab.
- Click **Predict Salary** to generate results.
- Scroll down to view salary level, career stage, pattern insight, negotiation tips, and recommendations.
- Click **Prepare PDF Report** to generate a downloadable summary, then click **Download** to save it.
- To share feedback on the prediction, expand the **Share Feedback on This Prediction** section at the bottom, fill in the fields, and click **Submit Feedback**. Login is not required.

**Resume Analysis**
- Switch to Model 1 using the model selector.
- Go to the Resume Analysis tab and upload a PDF resume.
- Click **Extract Resume Features** to run NLP extraction.
- Review and edit the detected fields if needed.
- Click **Predict Salary from Resume** to get results.
- Click **Prepare PDF Report** to generate a downloadable summary, then click **Download** to save it.

**Batch Prediction**
- Download the sample file from the left column to understand the required format.
- Upload your file or paste a public Google Drive sharing link in the middle column.
- Click **Run Batch Prediction** to process all records.
- Export results in your preferred format using the dropdown and download button.

**Scenario Analysis**
- Go to the Scenario Analysis tab after selecting your model.
- Each scenario is pre-filled with sensible defaults — rename it and adjust any inputs.
- Click **Add Scenario** to add more scenarios (up to 5) or **Remove** to delete one.
- Click **Run All Scenarios** to predict salaries for all scenarios at once.
- Scroll down to view the comparison table, salary charts, and sensitivity sweeps.
- Select a baseline scenario from the dropdown in the sweep section to simulate how salary responds to changes in experience or education while everything else stays fixed.
- Use the export dropdown and download button to save scenario results.

**Account (Optional)**
- Register or log in from the sidebar to save predictions.
- Logged-in users can view their full prediction history in the Profile tab.
- Sessions expire after 24 hours and require re-login.

**Google Drive Upload**
- Set the file sharing permission to "Anyone with the link can view" before pasting the link.
- Select the correct file format from the dropdown after pasting the link.
        """)

    with st.expander("Limitations"):
        st.markdown("""
    - The models are trained on limited datasets, so predictions may not always match real-world salaries.
    - Some job roles, countries, or inputs may not be fully covered in the dataset.
    - Resume analysis depends on text extraction and may not work properly for all resume formats.
    - Predictions are based on past data and do not consider current market trends or company-specific salaries.
    - Scenario Analysis results are generated by the same underlying model as manual prediction and carry the same limitations.
    - The results should be used only as an estimate, not as an exact salary value.
    - Feedback submitted anonymously cannot be linked to a specific user session and is stored as-is without any personal identifier.
        """)