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

from currency_utils import render_currency_converter, get_active_currency, get_active_rates
from tax_utils import render_tax_adjuster
from col_utils import render_col_adjuster
from ctc_utils import render_ctc_adjuster
from takehome_utils import render_takehome_adjuster
from savings_utils import render_savings_adjuster
from loan_utils import render_loan_adjuster

from feedback import feedback_ui

from resume_analysis import (
    extract_text_from_pdf,
    extract_resume_features,
    calculate_resume_score,
    education_label,

    extract_resume_features_a2, 
    calculate_resume_score_a2, 
    APP2_ALLOWED_ISO_CODES_A2
)

from manual_prediction_tab import render_manual_prediction_tab
from resume_analysis_tab import render_resume_tab
from batch_prediction_tab import render_batch_prediction_tab
from scenario_analysis_tab import render_scenario_tab
from model_analytics_tab import render_model_analytics_tab
from data_insights_tab import render_data_insights_tab
from about_tab import render_about_tab

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
    package = joblib.load("model/ds_xgb_model_grid.pkl")
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
#   APP1 DROPWDOWNS
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
#   APP2 DROPDOWNS
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
        "Test R2": 0.799584
    },
    {
        "Model": "Decision Tree Regression",
        "MAE": 13973.727758,
        "RMSE": 19079.721423,
        "Test R2": 0.862186
    },
    {
        "Model": "Gradient Boosting Regression",
        "MAE": 12405.046692,
        "RMSE": 16871.279240,
        "Test R2": 0.892243
    },
    {
        "Model": "XGBoost (GridSearchCV)",
        "MAE": 5861.980002,
        "RMSE": 10337.127946,
        "Test R2": 0.959547
    },
    {
        "Model": "Random Forest (GridSearchCV)",
        "MAE": 4926.799420,
        "RMSE": 9760.508203,
        "Test R2": 0.963934
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
        "Test R2": 0.3486,
        "MAE": 40169,
        "RMSE": 53380
    },
    {
        "Model": "Gradient Boosting (Raw)",
        "Test R2": 0.3989,
        "MAE": 38921,
        "RMSE": 51278
    },
    {
        "Model": "Random Forest (Log)",
        "Test R2": 0.5759,
        "MAE": 37878,
        "RMSE": 51768
    },
    {
        "Model": "XGBoost (Log)",
        "Test R2": 0.5944,
        "MAE": 37668,
        "RMSE": 51505
    },
    {
        "Model": "XGBoost (Raw + Engineered)",
        "Test R2": 0.5949,
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
# ASSOCIATION FUNCTIONS
# ==================================================
def get_assoc_insight_a1_improved(
    education,
    experience,
    country,
    job_group,
    predicted_salary,
    rules,
    years_experience=None   # <-- (pass from app.py)
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
# USER ACCOUNT SIDEBAR 
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
# HEADER USER INDICATOR
# ==================================================

header_left, header_right = st.columns([8, 2])

with header_right:

    if st.session_state.logged_in:

        display_username = st.session_state.get("username", "User")
        first_letter = display_username[0].upper()

        is_user_admin = is_admin()

        avatar_color = "#E05252" if is_user_admin else "#4F8EF7"

        st.markdown(
            f"""
            <div style="text-align:right; padding-top:10px;">
                <span style="
                    display:inline-block;
                    width:28px;
                    height:28px;
                    border-radius:50%;
                    background:{avatar_color};
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
    st.caption("**Active Model:** Random Forest Regressor + Salary Level Classifier — trained on General Salary dataset.")
else:
    st.caption("**Active Model:** XGBoost Regressor (log-transformed) — trained on Data Science Salary dataset.")

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
    render_manual_prediction_tab(
        IS_APP1=IS_APP1,
        app1_model=app1_model if IS_APP1 else None,
        app1_metadata=app1_metadata if IS_APP1 else None,
        app1_classifier_metadata=app1_classifier_metadata if IS_APP1 else None,
        app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
        app1_cluster_model_a1=app1_cluster_model_a1 if IS_APP1 else None,
        app1_cluster_metadata_a1=app1_cluster_metadata_a1 if IS_APP1 else None,
        app1_job_titles=app1_job_titles,
        app1_countries=app1_countries,
        app1_genders=app1_genders,
        SALARY_BAND_LABELS=SALARY_BAND_LABELS,
        assoc_rules_a1_v2=assoc_rules_a1_v2,
        get_assoc_insight_a1_improved=get_assoc_insight_a1_improved,
        load_app1_analytics=load_app1_analytics,
        app1_generate_manual_pdf=app1_generate_manual_pdf,
        app2_model=app2_model if not IS_APP1 else None,
        app2_metadata=app2_metadata if not IS_APP1 else None,
        app2_job_titles=app2_job_titles,
        app2_experience_levels=app2_experience_levels,
        app2_employment_types=app2_employment_types,
        app2_company_sizes=app2_company_sizes,
        app2_remote_ratios=app2_remote_ratios,
        app2_country_display_options=app2_country_display_options,
        app2_employee_residence_display_options=app2_employee_residence_display_options,
        app2_generate_manual_pdf=app2_generate_manual_pdf,
        df_app2=df_app2,
        EXPERIENCE_MAP=EXPERIENCE_MAP,
        EMPLOYMENT_MAP=EMPLOYMENT_MAP,
        COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
        REMOTE_MAP=REMOTE_MAP,
        COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
        EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
        EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
        COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
        REMOTE_REVERSE=REMOTE_REVERSE,
        title_features=title_features,
    )
# ==================================================
# TAB 2: RESUME ANALYSIS
# ==================================================
with tab_objects[1]:
    render_resume_tab(
        IS_APP1=IS_APP1,
        app1_model=app1_model if IS_APP1 else None,
        app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
        app1_cluster_model_a1=app1_cluster_model_a1 if IS_APP1 else None,
        app1_cluster_metadata_a1=app1_cluster_metadata_a1 if IS_APP1 else None,
        app1_job_titles=app1_job_titles,
        app1_countries=app1_countries,
        app1_genders=app1_genders,
        SALARY_BAND_LABELS=SALARY_BAND_LABELS,
        assoc_rules_a1_v2=assoc_rules_a1_v2,
        get_assoc_insight_a1_improved=get_assoc_insight_a1_improved,
        load_app1_analytics=load_app1_analytics,
        app1_generate_resume_pdf=app1_generate_resume_pdf,
        app2_model=app2_model if not IS_APP1 else None,
        app2_job_titles=app2_job_titles,
        app2_experience_levels=app2_experience_levels,
        app2_employment_types=app2_employment_types,
        app2_company_sizes=app2_company_sizes,
        app2_remote_ratios=app2_remote_ratios,
        app2_country_display_options=app2_country_display_options,
        app2_employee_residence_display_options=app2_employee_residence_display_options,
        app2_generate_resume_pdf=app2_generate_resume_pdf,
        df_app2=df_app2,
        EXPERIENCE_MAP=EXPERIENCE_MAP,
        EMPLOYMENT_MAP=EMPLOYMENT_MAP,
        COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
        REMOTE_MAP=REMOTE_MAP,
        COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
        EXPERIENCE_REVERSE=EXPERIENCE_REVERSE,
        EMPLOYMENT_REVERSE=EMPLOYMENT_REVERSE,
        COMPANY_SIZE_REVERSE=COMPANY_SIZE_REVERSE,
        REMOTE_REVERSE=REMOTE_REVERSE,
        title_features=title_features,
    )
 
# ==================================================
# TAB 3: BULK SCANNER
# ==================================================
with tab_objects[2]:
        render_batch_prediction_tab(
            is_app1=IS_APP1,
            app1_model=app1_model if IS_APP1 else None,
            app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
            app1_cluster_model=app1_cluster_model_a1 if IS_APP1 else None,
            app1_cluster_metadata=app1_cluster_metadata_a1 if IS_APP1 else None,
            app1_job_titles=app1_job_titles,
            app1_countries=app1_countries,
            app2_model=app2_model if not IS_APP1 else None,
            app2_job_titles=app2_job_titles,
            df_app1=df_app1,
            df_app2=df_app2,
            APP1_REQUIRED_COLUMNS=APP1_REQUIRED_COLUMNS,
            APP2_REQUIRED_COLUMNS=APP2_REQUIRED_COLUMNS,
            SALARY_BAND_LABELS=SALARY_BAND_LABELS,
            EXPERIENCE_MAP=EXPERIENCE_MAP,
            COMPANY_SIZE_MAP=COMPANY_SIZE_MAP,
            REMOTE_MAP=REMOTE_MAP,
            COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
            apply_theme=_apply_theme,
            get_plot_df=get_plot_df,
            generate_salary_leaderboard=generate_salary_leaderboard,
            app1_validate_bulk_dataframe=app1_validate_bulk_dataframe,
            app2_validate_bulk_dataframe=app2_validate_bulk_dataframe,
            convert_drive_link=convert_drive_link,
            title_features=title_features,
            app1_generate_bulk_pdf=app1_generate_bulk_pdf,
            app2_generate_bulk_pdf=app2_generate_bulk_pdf,
        )

# ==================================================
# TAB 4: SCENARIO ANALYSIS / WHAT-IF SIMULATION
# ==================================================
with tab_objects[3]:
        render_scenario_tab(
            is_app1=IS_APP1,
            app1_model=app1_model if IS_APP1 else None,
            app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
            app1_cluster_model=app1_cluster_model_a1 if IS_APP1 else None,
            app1_cluster_metadata=app1_cluster_metadata_a1 if IS_APP1 else None,
            app1_analytics_loader=load_app1_analytics,
            app1_genders=app1_genders,
            app1_job_titles=app1_job_titles,
            app1_countries=app1_countries,
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
            REMOTE_REVERSE=REMOTE_REVERSE,
            COUNTRY_NAME_MAP=COUNTRY_NAME_MAP,
            apply_theme=_apply_theme,
            colorway=_COLORWAY,
            title_features=title_features,
            app1_generate_scenario_pdf=app1_generate_scenario_pdf,
            app2_generate_scenario_pdf=app2_generate_scenario_pdf,
        )
# ==================================================
# TAB 5: MODEL ANALYTICS
# ==================================================
with tab_objects[4]:
    render_model_analytics_tab(
        is_app1=IS_APP1,
        # App 1 resources
        app1_model=app1_model if IS_APP1 else None,
        app1_metadata=app1_metadata if IS_APP1 else None,
        app1_classifier_metadata=app1_classifier_metadata if IS_APP1 else None,
        app1_salary_band_model=app1_salary_band_model if IS_APP1 else None,
        app1_cluster_metadata=app1_cluster_metadata_a1 if IS_APP1 else None,
        app1_analytics_loader=load_app1_analytics,
        assoc_rules=assoc_rules_a1_v2 if IS_APP1 else None,
        df_app1=df_app1 if IS_APP1 else None,
        APP1_MODEL_COMPARISON=APP1_MODEL_COMPARISON,
        APP1_CLASSIFIER_MODEL_COMPARISON=APP1_CLASSIFIER_MODEL_COMPARISON,
        # App 2 resources
        app2_model=app2_model if not IS_APP1 else None,
        app2_metadata=app2_metadata if not IS_APP1 else None,
        app2_analytics_loader=load_app2_analytics,
        APP2_MODEL_COMPARISON=APP2_MODEL_COMPARISON,
        # Shared helpers
        apply_theme=_apply_theme,
        model_colors=_MODEL_COLORS,
        # PDF helpers
        cached_app1_model_analytics_pdf=cached_app1_model_analytics_pdf,
        cached_app2_model_analytics_pdf=cached_app2_model_analytics_pdf,
    )
 
# ==================================================
# TAB 6: DATA INSIGHTS
# ==================================================
with tab_objects[5]:
    render_data_insights_tab(IS_APP1, df_app1, df_app2, COUNTRY_NAME_MAP)
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
# TAB 9: ABOUT (Merged from both apps)
# ==================================================
about_index = tabs.index("About")
with tab_objects[about_index]:
    render_about_tab()