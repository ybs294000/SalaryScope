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
from resume_analysis import (
    extract_text_from_pdf,
    extract_resume_features,
    calculate_resume_score,
    education_label,

    extract_resume_features_a2, 
    calculate_resume_score_a2, 
    APP2_ALLOWED_ISO_CODES_A2
)
from feedback import feedback_ui

from batch_prediction_tab import render_batch_prediction_tab

from scenario_analysis_tab import render_scenario_tab

from model_analytics_tab import render_model_analytics_tab

from data_insights_tab import render_data_insights_tab

from about_tab import render_about_tab

from currency_utils import render_currency_converter, get_active_currency, get_active_rates
from tax_utils import render_tax_adjuster
from col_utils import render_col_adjuster
from ctc_utils import render_ctc_adjuster
from takehome_utils import render_takehome_adjuster
from savings_utils import render_savings_adjuster
from loan_utils import render_loan_adjuster

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

            render_ctc_adjuster(gross_usd=prediction, location_hint=country, widget_key="manual_a1_ctc")
            th = render_takehome_adjuster(gross_usd=prediction, location_hint=country,
                                           widget_key="manual_a1_th", net_usd=None)
            net_monthly = th.get("net_monthly", prediction / 12)
            render_savings_adjuster(net_monthly_usd=net_monthly, location_hint=country,
                                     widget_key="manual_a1_sav", gross_usd=prediction)
            render_loan_adjuster(net_monthly_usd=net_monthly, location_hint=country,
                                 widget_key="manual_a1_loan", gross_usd=prediction)

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
          
            render_ctc_adjuster(gross_usd=prediction_a2, location_hint=company_location, widget_key="manual_a2_ctc")
            th_a2 = render_takehome_adjuster(gross_usd=prediction_a2, location_hint=company_location,
                                           widget_key="manual_a2_th", net_usd=None)
            net_monthly_a2 = th_a2.get("net_monthly_a2", prediction_a2 / 12)
            render_savings_adjuster(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                     widget_key="manual_a2_sav", gross_usd=prediction_a2)
            render_loan_adjuster(net_monthly_usd=net_monthly_a2, location_hint=company_location,
                                 widget_key="manual_a2_loan", gross_usd=prediction_a2)
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

    st.header(":material/description: Resume Analysis")
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