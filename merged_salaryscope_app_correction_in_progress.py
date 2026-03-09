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
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error, confusion_matrix
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import matplotlib.pyplot as plt
from reportlab.lib.utils import ImageReader

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="SalaryScope",
    layout="wide"
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
    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--text-main) !important;
    }

    .stTextInput input,
    .stNumberInput input {
        background-color: var(--bg-input) !important;
        color: var(--text-main) !important;
    }

    .stTextInput > div > div:focus-within,
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

    /* ── Dataframe ── */
    [data-testid="stDataFrame"], .stDataFrame {
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    .stDataFrame thead th {
        background-color: var(--bg-input) !important;
        color: var(--text-main) !important;
    }

    .stDataFrame tbody tr:nth-child(even) td {
        background-color: #121826 !important;
    }

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
# MODEL LOADING — App 1 (RF Regressor + Classifier)
# ==================================================
@st.cache_resource
def load_app1_model_package():
    return joblib.load("model/rf_model_grid.pkl")

@st.cache_resource
def load_app1_classifier_package():
    return joblib.load("model/salary_band_classifier.pkl")

# ==================================================
# MODEL LOADING — App 2 (XGBoost)
# ==================================================
@st.cache_resource
def load_app2_model():
    package = joblib.load("model/salaryscope_3755_production_model.pkl")
    return package["model"], package["metadata"]

@st.cache_resource
def get_shap_explainer(_model_a2):
    xgb_model_inner = _model_a2.named_steps["model"]
    return shap.TreeExplainer(xgb_model_inner)
# ==================================================
# DATASET LOADING
# ==================================================
@st.cache_data
def load_app1_dataset():
    return pd.read_csv("data/Salary_no_race.csv")

@st.cache_data
def load_app2_dataset():
    df2 = pd.read_csv("data/ds_salaries.csv")
    drop_cols = [c for c in ["salary", "salary_currency", "work_year"] if c in df2.columns]
    df2 = df2.drop(drop_cols, axis=1)
    return df2


# ==================================================
# LOAD EVERYTHING
# ==================================================
app1_package = load_app1_model_package()
app1_model = app1_package["model"]
app1_metadata = app1_package["metadata"]

app1_classifier_package = load_app1_classifier_package()
app1_salary_band_model = app1_classifier_package["model"]
app1_classifier_metadata = app1_classifier_package["metadata"]

app2_model, app2_metadata = load_app2_model()

df_app1 = load_app1_dataset()
df_app2 = load_app2_dataset()

# App1 dropdown options
app1_job_titles = sorted(df_app1["Job Title"].dropna().value_counts().head(40).index.tolist())
app1_countries = sorted(df_app1["Country"].dropna().unique().tolist())
if "Other" not in app1_countries:
    app1_countries.append("Other")
app1_genders = sorted(df_app1["Gender"].dropna().unique())

# App2 dropdown options
app2_job_titles = sorted(df_app2["job_title"].dropna().value_counts().head(50).index.tolist())
app2_countries = sorted(df_app2["company_location"].dropna().unique().tolist())
if "Other" not in app2_countries:
    app2_countries.append("Other")
app2_experience_levels = sorted(df_app2["experience_level"].dropna().unique().tolist())
app2_employment_types = sorted(df_app2["employment_type"].dropna().unique().tolist())
app2_company_sizes = sorted(df_app2["company_size"].dropna().unique().tolist())
app2_remote_ratios = sorted(df_app2["remote_ratio"].dropna().unique().tolist())

# --------------------------------------------------
# App 1 — Static Model Comparison
# --------------------------------------------------
APP1_MODEL_COMPARISON = [
    {
        "Model": "Linear Regression",
        "MAE": 16012.620611,
        "RMSE": 21756.922474,
        "Test R²": 0.830029
    },
    {
        "Model": "Decision Tree Regression",
        "MAE": 12444.189339,
        "RMSE": 17431.514795,
        "Test R²": 0.890894
    },
    {
        "Model": "Gradient Boosting Regression",
        "MAE": 11675.906507,
        "RMSE": 16119.781676,
        "Test R²": 0.906697
    },
    {
        "Model": "XGBoost (GridSearchCV)",
        "MAE": 4867.432239,
        "RMSE": 8387.966889,
        "Test R²": 0.974737
    },
    {
        "Model": "Random Forest (GridSearchCV)",
        "MAE": app1_metadata["mae"],
        "RMSE": app1_metadata["rmse"],
        "Test R²": app1_metadata["test_r2"]
    }
]

APP1_CLASSIFIER_MODEL_COMPARISON = [
    {
        "Model": "Logistic Regression",
        "Accuracy": 0.885479,
        "Precision": 0.884436,
        "Recall": 0.885223,
        "F1 Score": 0.884560
    },
    {
        "Model": "Decision Tree (GridSearchCV)",
        "Accuracy": 0.9580838323353293,
        "Precision": 0.955748,
        "Recall": 0.955771,
        "F1 Score": 0.9578319811766254
    },
    {
        "Model": "Random Forest (GridSearchCV)",
        "Accuracy": 0.9550898203592815,
        "Precision": 0.954998,
        "Recall": 0.955027,
        "F1 Score": 0.9549969713538009
    },
    {
        "Model": "XGBoost",
        "Accuracy": 0.961078,
        "Precision": 0.961073,
        "Recall": 0.961009,
        "F1 Score": 0.960915
    },
    {
        "Model": "Bagging (GridSearchCV)",
        "Accuracy": 0.9655688622754491,
        "Precision": 0.962593,
        "Recall": 0.962502,
        "F1 Score": 0.9654772893701115
    }
]

# --------------------------------------------------
# App 2 — Static Model Comparison
# --------------------------------------------------
APP2_MODEL_COMPARISON = [
    {
        "Model": "Linear Regression (Baseline)",
        "Train R²": 0.4869,
        "Test R²": 0.3663,
        "MAE": 37959,
        "RMSE": 50017
    },
    {
        "Model": "Gradient Boosting (Raw)",
        "Train R²": 0.4778,
        "Test R²": 0.4047,
        "MAE": 36942,
        "RMSE": 48480
    },
    {
        "Model": "Random Forest (Log)",
        "Train R²": 0.7459,
        "Test R²": 0.5809,
        "MAE": 35644,
        "RMSE": 48085
    },
    {
        "Model": "XGBoost (Log)",
        "Train R²": 0.7139,
        "Test R²": 0.5815,
        "MAE": 35641,
        "RMSE": 48316
    },
    {
        "Model": "XGBoost (Raw + Engineered) ⭐",
        "Train R²": 0.6601,
        "Test R²": 0.5912,
        "MAE": 34519,
        "RMSE": 46452
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
EXPERIENCE_REVERSE = {v: k for k, v in EXPERIENCE_MAP.items()}
EMPLOYMENT_REVERSE = {v: k for k, v in EMPLOYMENT_MAP.items()}
COMPANY_SIZE_REVERSE = {v: k for k, v in COMPANY_SIZE_MAP.items()}
REMOTE_REVERSE = {v: k for k, v in REMOTE_MAP.items()}

app2_country_display_options = []
for code in app2_countries:
    if code in COUNTRY_NAME_MAP:
        app2_country_display_options.append(f"{COUNTRY_NAME_MAP[code]} ({code})")
    else:
        app2_country_display_options.append(code)

# --------------------------------------------------
# App 1 — Salary Band Labels
# --------------------------------------------------
SALARY_BAND_LABELS = {
    "Low": "Early Career Range",
    "Medium": "Professional Range",
    "High": "Executive Range"
}

# --------------------------------------------------
# App 1 — Required Columns for Bulk
# --------------------------------------------------
APP1_REQUIRED_COLUMNS = [
    "Age", "Years of Experience", "Education Level",
    "Senior", "Gender", "Job Title", "Country"
]

# --------------------------------------------------
# App 2 — Required Columns for Bulk
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

# --------------------------------------------------
# Custom ReportLab canvas for page numbering
# --------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        self._saved_page_states.append(dict(self.__dict__))
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        page = self._pageNumber
        text = f"Page {page} of {page_count}"
        self.setFont("Helvetica", 9)
        self.drawCentredString(300, 20, text)

# --------------------------------------------------
# PDF Metadata Helper
# --------------------------------------------------
def apply_pdf_metadata(c, title, subject):
    c.setTitle(title)
    c.setAuthor("SalaryScope")
    c.setSubject(subject)
    c.setCreator("SalaryScope - Salary Prediction System")
    c.setKeywords("salary prediction, machine learning, salaryscope")


# ==================================================
# APP 1 — PDF: Manual Prediction
# ==================================================
def app1_generate_manual_pdf(data_dict, prediction, lower_bound, upper_bound, salary_band_label, metadata, classifier_metadata):
    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)
    width, height = letter
    apply_pdf_metadata(c, "SalaryScope Salary Prediction Report",
                       "Manual Salary Prediction Report generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(left_margin, y, "Salary Prediction Report")
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 25
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Input Details")
    c.setFont("Helvetica", 11)
    for key, value in data_dict.items():
        y -= 18
        c.drawString(left_margin + 15, y, f"{key}: {value}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 25
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Prediction Results")
    c.setFont("Helvetica", 11)
    monthly = prediction / 12
    weekly = prediction / 52
    hourly = prediction / (52 * 40)
    y -= 18
    c.drawString(left_margin + 15, y, f"Predicted Annual Salary: ${prediction:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Estimated Salary Level: {salary_band_label}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Monthly (Approx): ${monthly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Weekly (Approx): ${weekly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Hourly (Approx, 40hr/week): ${hourly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Likely Salary Range (95% CI): ${lower_bound:,.2f} - ${upper_bound:,.2f}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 25
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Model Information")
    c.setFont("Helvetica", 11)
    y -= 18
    c.drawString(left_margin + 15, y, "Salary Prediction Model: Random Forest Regressor")
    y -= 18
    c.drawString(left_margin + 15, y, f"Test R²: {metadata['test_r2']:.4f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Cross-Validation R²: {metadata['cv_mean_r2']:.4f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"MAE: ${metadata['mae']:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"RMSE: ${metadata['rmse']:,.2f}")
    y -= 20
    c.drawString(left_margin + 15, y, f"Salary Level Classifier: {classifier_metadata.get('model_type','Classifier')}")
    if "accuracy" in classifier_metadata:
        y -= 18
        c.drawString(left_margin + 15, y, f"Accuracy: {classifier_metadata['accuracy']:.4f}")
    if "precision_macro" in classifier_metadata:
        y -= 18
        c.drawString(left_margin + 15, y, f"Precision (Macro): {classifier_metadata['precision_macro']:.4f}")
    if "recall_macro" in classifier_metadata:
        y -= 18
        c.drawString(left_margin + 15, y, f"Recall (Macro): {classifier_metadata['recall_macro']:.4f}")
    if "f1_macro" in classifier_metadata:
        y -= 18
        c.drawString(left_margin + 15, y, f"F1 Score (Macro): {classifier_metadata['f1_macro']:.4f}")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 1 — PDF: Bulk Prediction
# ==================================================
def app1_generate_bulk_pdf(analytics_df):
    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)
    width, height = letter

    apply_pdf_metadata(
        c,
        "SalaryScope Bulk Salary Prediction Report",
        "Bulk salary analytics generated by SalaryScope"
    )

    left_margin = 50
    right_margin = width - 50
    y = height - 55

    # ==================================================
    # PAGE 1 — EXECUTIVE SUMMARY
    # ==================================================

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")

    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Bulk Salary Prediction Report")

    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y -= 15
    c.line(left_margin, y, right_margin, y)

    # Summary metrics
    avg_salary = analytics_df["Predicted Annual Salary"].mean()
    min_salary = analytics_df["Predicted Annual Salary"].min()
    max_salary = analytics_df["Predicted Annual Salary"].max()
    std_salary = analytics_df["Predicted Annual Salary"].std()
    std_salary = 0 if pd.isna(std_salary) else std_salary
    total_records = analytics_df.shape[0]
    median_salary = analytics_df["Predicted Annual Salary"].median()
    q1_salary = analytics_df["Predicted Annual Salary"].quantile(0.25)
    q3_salary = analytics_df["Predicted Annual Salary"].quantile(0.75)
    iqr_salary = q3_salary - q1_salary

    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left_margin, y, "Summary Statistics")

    y -= 22
    c.setFont("Helvetica", 11)

    spacing = 17
    c.drawString(left_margin + 10, y, f"Total Records Processed: {total_records}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Average Predicted Salary: ${avg_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Median Predicted Salary: ${median_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Minimum Predicted Salary: ${min_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Maximum Predicted Salary: ${max_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Salary Standard Deviation: ${std_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Interquartile Range (IQR): ${iqr_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 20, y, f"(Q1: ${q1_salary:,.2f}  |  Q3: ${q3_salary:,.2f})")


    # Wrapped Insight
    y -= 30
    c.setFont("Helvetica-Oblique", 10)

    spread = max_salary - min_salary
    insight_text = (
        f"Insight: The predicted salary spread is ${spread:,.2f}. "
        "This reflects variation associated with experience, education level, and seniority."
    )

    max_width = right_margin - left_margin
    words = insight_text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14

    # Salary Distribution Chart
    y -= 20
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Salary Distribution")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.hist(
        analytics_df["Predicted Annual Salary"],
        bins=min(12, len(analytics_df)),
        color="#1A4F8A",
        edgecolor="#FFFFFF",
        linewidth=0.7,
        alpha=1.0
    )
    ax.set_facecolor("#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    ax.grid(axis="y", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    ax.tick_params(colors="#111111", labelsize=9)
    ax.set_title("Distribution of Predicted Salaries", fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax.set_xlabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    ax.set_ylabel("Count", fontsize=10, color="#111111", labelpad=6)

    chart_buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer, format="png", dpi=150, facecolor="white")
    plt.close(fig)
    chart_buffer.seek(0)

    img = ImageReader(chart_buffer)

    image_width = 500
    image_height = 290
    x_position = (width - image_width) / 2

    y -= image_height + 12
    c.drawImage(
        img,
        x_position,
        y,
        width=image_width,
        height=image_height,
        preserveAspectRatio=True,
        mask='auto'
    )

    # -----------------------------------------
    # Histogram Interpretation
    # -----------------------------------------
    y -= 20
    c.setFont("Helvetica-Oblique", 10)

    mean_salary = analytics_df["Predicted Annual Salary"].mean()
    median_salary = analytics_df["Predicted Annual Salary"].median()

    if mean_salary > median_salary:
        shape_comment = "slightly right-skewed"
    elif mean_salary < median_salary:
        shape_comment = "slightly left-skewed"
    else:
        shape_comment = "approximately symmetric"

    hist_text = (
        f"Interpretation: The salary distribution appears {shape_comment}. "
        f"The mean salary is ${mean_salary:,.2f} and the median salary is "
        f"${median_salary:,.2f}, indicating the overall central tendency "
        f"of the predicted salaries."
    )

    max_width = right_margin - left_margin
    words = hist_text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14

    # Footer page 1
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ==================================================
    # PAGE 2 — DETAILED ANALYTICS
    # ==================================================
    c.showPage()
    y = height - 55

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Analytical Breakdown")

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Average Salary by Education Level")

    edu_group = (
        analytics_df.groupby("Education Level")["Predicted Annual Salary"]
        .mean()
        .reset_index()
    )

    edu_map = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
    edu_group["Education Level"] = edu_group["Education Level"].map(edu_map)

    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in edu_group.iterrows():
        c.drawString(left_margin + 10, y,
            f"{row['Education Level']}: ${row['Predicted Annual Salary']:,.2f}")
        y -= 16

    # Senior Comparison
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Average Salary by Seniority")

    senior_group = (
        analytics_df.groupby("Senior")["Predicted Annual Salary"]
        .mean()
        .reset_index()
    )

    senior_map = {0: "Non-Senior", 1: "Senior"}
    senior_group["Senior"] = senior_group["Senior"].map(senior_map)

    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in senior_group.iterrows():
        c.drawString(left_margin + 10, y,
            f"{row['Senior']}: ${row['Predicted Annual Salary']:,.2f}")
        y -= 16

    # Country Summary (Top 5)
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Average Predicted Salary by Country")

    country_group = (
        analytics_df.groupby("Country")["Predicted Annual Salary"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary", ascending=False)
    )

    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in country_group.iterrows():
        c.drawString(left_margin + 10, y,
            f"{row['Country']}: ${row['Predicted Annual Salary']:,.2f}")
        y -= 16

    # ----------------------------
    # Salary Distribution Boxplot
    # ----------------------------
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Salary Distribution (Box Plot)")

    # Create boxplot
    fig_box, ax_box = plt.subplots(figsize=(7.5, 3.5))

    bp = ax_box.boxplot(
        analytics_df["Predicted Annual Salary"],
        vert=False,
        patch_artist=True,
        boxprops=dict(facecolor="#6A9FCA", color="#1A4F8A", linewidth=1.6),
        medianprops=dict(color="#111111", linewidth=2.2),
        whiskerprops=dict(color="#1A4F8A", linewidth=1.4, linestyle="--"),
        capprops=dict(color="#1A4F8A", linewidth=1.6),
        flierprops=dict(marker="o", markerfacecolor="#1A4F8A", markeredgecolor="#1A4F8A", markersize=4, alpha=0.8)
    )

    ax_box.set_facecolor("#FFFFFF")
    fig_box.patch.set_facecolor("#FFFFFF")
    ax_box.grid(axis="x", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax_box.set_axisbelow(True)
    ax_box.spines["top"].set_visible(False)
    ax_box.spines["right"].set_visible(False)
    ax_box.spines["left"].set_color("#444444")
    ax_box.spines["bottom"].set_color("#444444")
    ax_box.tick_params(colors="#111111", labelsize=9)
    ax_box.set_title("Predicted Salary Spread", fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax_box.set_xlabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)

    chart_buffer_box = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer_box, format="png", dpi=150, facecolor="white")
    plt.close(fig_box)
    chart_buffer_box.seek(0)

    img_box = ImageReader(chart_buffer_box)

    image_width = 480
    image_height = 200
    x_position = (width - image_width) / 2

    y -= image_height + 10

    c.drawImage(
        img_box,
        x_position,
        y,
        width=image_width,
        height=image_height,
        preserveAspectRatio=True,
        mask='auto'
    )

    # -----------------------------------------
    # Page 2 Overall Interpretation
    # -----------------------------------------
    y -= 30
    c.setFont("Helvetica-Oblique", 10)

    analysis_text = (
        "Interpretation: This section presents a breakdown of predicted "
        "salaries across education levels and seniority, along with an "
        "overview of the overall salary distribution within the uploaded dataset."
    )

    max_width = right_margin - left_margin
    words = analysis_text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14

    # Footer page 2
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ==================================================
    # PAGE 3 — COUNTRY SALARY VISUALIZATION
    # ==================================================
    c.showPage()
    y = height - 55

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Average Predicted Salary by Country")

    # Prepare grouped data (max 5 countries)
    country_group_chart = (
        analytics_df.groupby("Country")["Predicted Annual Salary"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary", ascending=False)
        .head(5)
    )

    # Create bar chart
    fig_country_chart, ax_country = plt.subplots(figsize=(7.5, 4.5))

    bar_colors = ["#1A4F8A", "#1F5FA3", "#2470BA", "#2980CC", "#3590D8"]
    n_bars = len(country_group_chart)
    colors_to_use = bar_colors[:n_bars]

    ax_country.bar(
        country_group_chart["Country"],
        country_group_chart["Predicted Annual Salary"],
        color=colors_to_use,
        edgecolor="#FFFFFF",
        linewidth=0.7
    )

    ax_country.set_facecolor("#FFFFFF")
    fig_country_chart.patch.set_facecolor("#FFFFFF")
    ax_country.grid(axis="y", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax_country.set_axisbelow(True)
    ax_country.spines["top"].set_visible(False)
    ax_country.spines["right"].set_visible(False)
    ax_country.spines["left"].set_color("#444444")
    ax_country.spines["bottom"].set_color("#444444")
    ax_country.tick_params(colors="#111111", labelsize=9)
    ax_country.set_title("Average Predicted Salary by Country", fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax_country.set_xlabel("Country", fontsize=10, color="#111111", labelpad=6)
    ax_country.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)

    plt.xticks(rotation=20)

    chart_buffer_country = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer_country, format="png", dpi=150, facecolor="white")
    plt.close(fig_country_chart)
    chart_buffer_country.seek(0)

    img_country = ImageReader(chart_buffer_country)

    image_width = 500
    image_height = 300
    x_position = (width - image_width) / 2

    y -= image_height + 20

    c.drawImage(
        img_country,
        x_position,
        y,
        width=image_width,
        height=image_height,
        preserveAspectRatio=True,
        mask='auto'
    )

    # -----------------------------------------
    # Interpretation Text
    # -----------------------------------------
    y -= 25
    c.setFont("Helvetica-Oblique", 10)

    top_country = country_group_chart.iloc[0]["Country"]
    top_salary = country_group_chart.iloc[0]["Predicted Annual Salary"]

    bottom_country = country_group_chart.iloc[-1]["Country"]
    bottom_salary = country_group_chart.iloc[-1]["Predicted Annual Salary"]

    country_spread = top_salary - bottom_salary

    interpretation_text = (
        f"Interpretation: Among the selected countries, {top_country} "
        f"shows the highest average predicted salary (${top_salary:,.2f}), "
        f"while {bottom_country} shows the lowest (${bottom_salary:,.2f}). "
        f"The difference of ${country_spread:,.2f} highlights regional "
        f"variations in predicted compensation."
    )

    max_width = right_margin - left_margin
    words = interpretation_text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14

    # Footer page 3
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 1 — PDF: Model Analytics
# ==================================================
def app1_generate_model_analytics_pdf(metadata, model, df, model_comparison,
                                       classifier_metadata, salary_band_model):
    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)
    width, height = letter
    apply_pdf_metadata(c, "SalaryScope Model Analytics Report",
                       "Machine learning model diagnostics generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 55
    max_width = right_margin - left_margin

    # PAGE 1 — REGRESSION MODEL SUMMARY
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Model Analytics Report")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)
    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left_margin, y, "Regression Model: Random Forest")
    y -= 22
    c.setFont("Helvetica", 11)
    spacing = 17
    c.drawString(left_margin + 10, y, f"Test R²: {metadata['test_r2']:.4f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Cross-Validation R² (Mean): {metadata['cv_mean_r2']:.4f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"MAE: ${metadata['mae']:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"RMSE: ${metadata['rmse']:,.2f}")

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Model Comparison (Regression)")
    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin + 5, y, "Model")
    c.drawString(left_margin + 260, y, "R²")
    c.drawString(left_margin + 320, y, "MAE")
    c.drawString(left_margin + 400, y, "RMSE")
    y -= 10
    c.line(left_margin, y, right_margin, y)
    y -= 15
    c.setFont("Helvetica", 10)
    sorted_models = sorted(model_comparison, key=lambda x: x["Test R²"], reverse=True)
    for row in sorted_models:
        c.drawString(left_margin + 5, y, row["Model"][:34])
        c.drawString(left_margin + 260, y, f"{row['Test R²']:.4f}")
        c.drawString(left_margin + 320, y, f"${row['MAE']:,.0f}")
        c.drawString(left_margin + 400, y, f"${row['RMSE']:,.0f}")
        y -= 15

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 2 — FEATURE IMPORTANCE (Regression)
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Feature Importance — Regression Model")

    rf_model = model.named_steps["model"]
    preprocessor = model.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out()
    importances = rf_model.feature_importances_
    importance_df = (
        pd.DataFrame({"Feature": feature_names, "Importance": importances})
        .sort_values(by="Importance", ascending=False)
        .head(15)
    )
    fig_imp, ax_imp = plt.subplots(figsize=(7.5, 4.5))
    ax_imp.barh(importance_df["Feature"][::-1], importance_df["Importance"][::-1],
                color="#1A4F8A", edgecolor="#FFFFFF", linewidth=0.7)
    ax_imp.set_facecolor("#FFFFFF")
    fig_imp.patch.set_facecolor("#FFFFFF")
    ax_imp.grid(axis="x", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax_imp.set_axisbelow(True)
    ax_imp.spines["top"].set_visible(False)
    ax_imp.spines["right"].set_visible(False)
    ax_imp.spines["left"].set_color("#444444")
    ax_imp.spines["bottom"].set_color("#444444")
    ax_imp.tick_params(colors="#111111", labelsize=9)
    ax_imp.set_title("Top 15 Feature Importances (Regression)", fontsize=12, fontweight="bold", color="#111111", pad=10)
    chart_buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer, format="png", dpi=150, facecolor="white")
    plt.close(fig_imp)
    chart_buffer.seek(0)
    img_imp = ImageReader(chart_buffer)
    image_width = 500
    image_height = 300
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_imp, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 3 — PREDICTED VS ACTUAL
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Predicted vs Actual Analysis")

    X_rf = df.drop("Salary", axis=1)
    y_rf = df["Salary"]
    X_train_rf, X_test_rf, y_train_rf, y_test_rf = train_test_split(X_rf, y_rf, test_size=0.2, random_state=42)
    y_pred_rf = model.predict(X_test_rf)

    fig1, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax1.scatter(y_test_rf, y_pred_rf, alpha=0.5, color="#1A4F8A")
    min_val = min(y_test_rf.min(), y_pred_rf.min())
    max_val = max(y_test_rf.max(), y_pred_rf.max())
    ax1.plot([min_val, max_val], [min_val, max_val], color="red", linewidth=1.5)
    ax1.set_title("Predicted vs Actual Salary")
    ax1.set_xlabel("Actual Salary")
    ax1.set_ylabel("Predicted Salary")
    ax1.grid(True)
    buf1 = BytesIO()
    plt.tight_layout()
    plt.savefig(buf1, format="png", dpi=150, facecolor="white")
    plt.close(fig1)
    buf1.seek(0)
    img1 = ImageReader(buf1)
    y -= 260
    c.drawImage(img1, left_margin, y, width=500, height=250)
    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    text2 = ("Interpretation: Points closer to the diagonal line represent "
             "accurate predictions. Greater dispersion indicates prediction error.")
    words = text2.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 4 — RESIDUAL ANALYSIS
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Residual Analysis")
    residuals = y_test_rf - y_pred_rf
    fig2, ax2 = plt.subplots(figsize=(7.5, 3.5))
    ax2.scatter(y_pred_rf, residuals, alpha=0.6)
    ax2.axhline(0, color="red", linestyle="--")
    ax2.set_title("Residuals vs Predicted Values")
    ax2.set_xlabel("Predicted Salary")
    ax2.set_ylabel("Residual")
    ax2.grid(True)
    buf2 = BytesIO()
    plt.tight_layout()
    plt.savefig(buf2, format="png", dpi=150, facecolor="white")
    plt.close(fig2)
    buf2.seek(0)
    img2 = ImageReader(buf2)
    y -= 230
    c.drawImage(img2, left_margin, y, width=500, height=200)
    fig3, ax3 = plt.subplots(figsize=(7.5, 3))
    ax3.hist(residuals, bins=30, edgecolor="black")
    ax3.set_title("Residual Distribution")
    ax3.set_xlabel("Residual")
    ax3.set_ylabel("Count")
    ax3.grid(axis="y", linestyle="--", alpha=0.6)
    buf3 = BytesIO()
    plt.tight_layout()
    plt.savefig(buf3, format="png", dpi=150, facecolor="white")
    plt.close(fig3)
    buf3.seek(0)
    img3 = ImageReader(buf3)
    y -= 220
    c.drawImage(img3, left_margin, y, width=500, height=180)
    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    text3 = ("Interpretation: Residuals centered around zero indicate balanced "
             "model errors. A symmetric distribution suggests stable predictive behavior.")
    words = text3.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 5 — CLASSIFICATION MODEL
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Salary Level Classification Model")
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Performance Metrics")
    c.setFont("Helvetica", 11)
    y -= 18
    c.drawString(left_margin + 10, y, f"Accuracy: {classifier_metadata.get('accuracy',0):.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Precision (Macro): {classifier_metadata.get('precision_macro',0):.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Recall (Macro): {classifier_metadata.get('recall_macro',0):.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"F1 Score (Macro): {classifier_metadata.get('f1_macro',0):.4f}")

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Confusion Matrix")
    cm = np.array(classifier_metadata.get("confusion_matrix"))
    fig_cm, ax_cm = plt.subplots(figsize=(7.5, 4.5))
    norm = plt.Normalize(vmin=cm.min(), vmax=cm.max())
    im = ax_cm.imshow(cm, cmap="Blues", norm=norm)
    labels_display = ["Early Career Range", "Professional Range", "Executive Range"]
    ax_cm.set_xticks(range(len(labels_display)))
    ax_cm.set_yticks(range(len(labels_display)))
    ax_cm.set_xticklabels(labels_display, rotation=20, ha="right")
    ax_cm.set_yticklabels(labels_display)
    ax_cm.set_xlabel("Predicted Label")
    ax_cm.set_ylabel("Actual Label")
    ax_cm.set_title("Salary Level Classification Confusion Matrix", pad=12)
    ax_cm.set_xticks(np.arange(-.5, 3, 1), minor=True)
    ax_cm.set_yticks(np.arange(-.5, 3, 1), minor=True)
    ax_cm.grid(which="minor", color="gray", linestyle="-", linewidth=0.5)
    ax_cm.tick_params(which="minor", bottom=False, left=False)
    threshold = cm.max() / 2
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            color = "white" if cm[i, j] > threshold else "black"
            ax_cm.text(j, i, cm[i, j], ha="center", va="center",
                       color=color, fontsize=10, fontweight="bold")
    fig_cm.colorbar(im, ax=ax_cm).ax.set_ylabel("Count", rotation=90)
    buf_cm = BytesIO()
    plt.tight_layout()
    plt.savefig(buf_cm, format="png", dpi=150, facecolor="white")
    plt.close(fig_cm)
    buf_cm.seek(0)
    img_cm = ImageReader(buf_cm)
    image_width = 420
    image_height = 250
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_cm, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Feature Importance (Classifier)")
    bagging_model = salary_band_model.named_steps["classifier"]
    preprocessor_cls = salary_band_model.named_steps["preprocessor"]
    feature_names_cls = preprocessor_cls.get_feature_names_out()
    n_features = len(feature_names_cls)
    all_importances = []
    for tree, feat_idx in zip(bagging_model.estimators_, bagging_model.estimators_features_):
        full_importance = np.zeros(n_features)
        full_importance[feat_idx] = tree.feature_importances_
        all_importances.append(full_importance)
    importances_cls = np.mean(all_importances, axis=0)
    importance_cls_df = (
        pd.DataFrame({"Feature": feature_names_cls, "Importance": importances_cls})
        .sort_values(by="Importance", ascending=False)
        .head(15)
    )
    fig_imp_cls, ax_imp_cls = plt.subplots(figsize=(7, 4))
    ax_imp_cls.barh(importance_cls_df["Feature"][::-1], importance_cls_df["Importance"][::-1])
    ax_imp_cls.set_title("Top Feature Importances (Classifier)")
    ax_imp_cls.grid(axis="x", linestyle="--", alpha=0.6)
    buf_imp = BytesIO()
    plt.tight_layout()
    plt.savefig(buf_imp, format="png", dpi=150, facecolor="white")
    plt.close(fig_imp_cls)
    buf_imp.seek(0)
    img_imp = ImageReader(buf_imp)
    image_width = 480
    image_height = 260
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_imp, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 2 — PDF: Manual Prediction
# ==================================================
def app2_generate_manual_pdf(data_dict, prediction, lower_bound, upper_bound):
    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)
    width, height = letter
    apply_pdf_metadata(c, "SalaryScope Salary Prediction Report",
                       "Manual Salary Prediction Report generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(left_margin, y, "Salary Prediction Report")
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 25
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Input Details")
    c.setFont("Helvetica", 11)
    for key, value in data_dict.items():
        y -= 18
        c.drawString(left_margin + 15, y, f"{key}: {value}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 25
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Prediction Results")
    c.setFont("Helvetica", 11)
    monthly = prediction / 12
    weekly = prediction / 52
    hourly = prediction / (52 * 40)
    y -= 18
    c.drawString(left_margin + 15, y, f"Predicted Annual Salary: ${prediction:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Monthly (Approx): ${monthly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Weekly (Approx): ${weekly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Hourly (Approx, 40hr/week): ${hourly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y,
                 f"Likely Salary Range (95% CI): ${lower_bound:,.2f} - ${upper_bound:,.2f}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 25
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Model Information")
    c.setFont("Helvetica", 11)
    y -= 18
    c.drawString(left_margin + 15, y, "Prediction Model: XGBoost Regressor")
    y -= 18
    c.drawString(left_margin + 15, y, "Target Transformation: log1p(salary_in_usd)")
    y -= 18
    c.drawString(left_margin + 15, y,
                 "Feature Engineering: Job title seniority/domain features + interaction term")
    y -= 18
    c.drawString(left_margin + 15, y, f"R² (log scale): {app2_metadata['test_r2_log_scale']:.4f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"MAE: ${app2_metadata['mae_usd']:,.0f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"RMSE: ${app2_metadata['rmse_usd']:,.0f}")
    y -= 18
    c.drawString(left_margin + 15, y,
                 "Confidence interval estimated from variance across boosted trees.")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 2 — PDF: Bulk Prediction
# ==================================================
def app2_generate_bulk_pdf(analytics_df):
    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)
    width, height = letter
    apply_pdf_metadata(c, "SalaryScope Bulk Salary Prediction Report",
                       "Bulk salary analytics generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 55
    max_width = right_margin - left_margin

    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Bulk Salary Prediction Report")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    avg_salary = analytics_df["Predicted Annual Salary (USD)"].mean()
    min_salary = analytics_df["Predicted Annual Salary (USD)"].min()
    max_salary = analytics_df["Predicted Annual Salary (USD)"].max()
    std_salary = analytics_df["Predicted Annual Salary (USD)"].std()
    std_salary = 0 if pd.isna(std_salary) else std_salary
    total_records = analytics_df.shape[0]
    median_salary = analytics_df["Predicted Annual Salary (USD)"].median()
    q1_salary = analytics_df["Predicted Annual Salary (USD)"].quantile(0.25)
    q3_salary = analytics_df["Predicted Annual Salary (USD)"].quantile(0.75)
    iqr_salary = q3_salary - q1_salary

    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left_margin, y, "Summary Statistics")
    y -= 22
    c.setFont("Helvetica", 11)
    spacing = 17
    c.drawString(left_margin + 10, y, f"Total Records Processed: {total_records}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Average Predicted Salary: ${avg_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Median Predicted Salary: ${median_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Minimum Predicted Salary: ${min_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Maximum Predicted Salary: ${max_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Salary Standard Deviation: ${std_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Interquartile Range (IQR): ${iqr_salary:,.2f}")
    y -= spacing
    c.drawString(left_margin + 20, y, f"(Q1: ${q1_salary:,.2f}  |  Q3: ${q3_salary:,.2f})")

    y -= 30
    c.setFont("Helvetica-Oblique", 10)
    spread = max_salary - min_salary
    insight_text = (
        f"Insight: The predicted salary spread is ${spread:,.2f}. "
        "This variation reflects differences in experience level, company size, "
        "work arrangement, and geographic location among the uploaded records."
    )
    words = insight_text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14

    y -= 20
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Salary Distribution")
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.hist(analytics_df["Predicted Annual Salary (USD)"],
            bins=min(12, len(analytics_df)),
            color="#1A4F8A", edgecolor="#FFFFFF", linewidth=0.7, alpha=1.0)
    ax.set_facecolor("#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    ax.grid(axis="y", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    ax.tick_params(colors="#111111", labelsize=9)
    ax.set_title("Distribution of Predicted Salaries", fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax.set_xlabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    ax.set_ylabel("Count", fontsize=10, color="#111111", labelpad=6)
    chart_buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer, format="png", dpi=150, facecolor="white")
    plt.close(fig)
    chart_buffer.seek(0)
    img = ImageReader(chart_buffer)
    image_width = 500
    image_height = 290
    x_position = (width - image_width) / 2
    y -= image_height + 12
    c.drawImage(img, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    mean_s = analytics_df["Predicted Annual Salary (USD)"].mean()
    med_s = analytics_df["Predicted Annual Salary (USD)"].median()
    shape_comment = "slightly right-skewed" if mean_s > med_s else (
        "slightly left-skewed" if mean_s < med_s else "approximately symmetric")
    hist_text = (
        f"Interpretation: The salary distribution appears {shape_comment}. "
        f"The mean salary is ${mean_s:,.2f} and the median salary is "
        f"${med_s:,.2f}, indicating the overall central tendency of the predicted salaries."
    )
    words = hist_text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, "Helvetica-Oblique", 10) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    for line in lines:
        c.drawString(left_margin, y, line)
        y -= 14

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 2 — ANALYTICAL BREAKDOWN
    EXPERIENCE_MAP_PDF = {"EN": "Entry Level", "MI": "Mid Level", "SE": "Senior Level", "EX": "Executive Level"}
    COMPANY_SIZE_MAP_PDF = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}
    REMOTE_MAP_PDF = {0: "On-site", 50: "Hybrid", 100: "Fully Remote"}

    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Analytical Breakdown")

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Average Predicted Salary by Experience Level")
    exp_group = (analytics_df.groupby("experience_level")["Predicted Annual Salary (USD)"]
                 .mean().reset_index())
    exp_group["experience_level"] = exp_group["experience_level"].map(EXPERIENCE_MAP_PDF)
    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in exp_group.iterrows():
        c.drawString(left_margin + 10, y,
                     f"{row['experience_level']}: ${row['Predicted Annual Salary (USD)']:,.2f}")
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Average Predicted Salary by Company Size")
    size_group = (analytics_df.groupby("company_size")["Predicted Annual Salary (USD)"]
                  .mean().reset_index())
    size_group["company_size"] = size_group["company_size"].map(COMPANY_SIZE_MAP_PDF)
    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in size_group.iterrows():
        c.drawString(left_margin + 10, y,
                     f"{row['company_size']}: ${row['Predicted Annual Salary (USD)']:,.2f}")
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Average Predicted Salary by Work Mode")
    remote_group = (analytics_df.groupby("remote_ratio")["Predicted Annual Salary (USD)"]
                    .mean().reset_index())
    remote_group["remote_ratio"] = remote_group["remote_ratio"].map(REMOTE_MAP_PDF)
    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in remote_group.iterrows():
        c.drawString(left_margin + 10, y,
                     f"{row['remote_ratio']}: ${row['Predicted Annual Salary (USD)']:,.2f}")
        y -= 16

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Top Countries by Average Predicted Salary")
    country_group = (analytics_df.groupby("company_location")["Predicted Annual Salary (USD)"]
                     .mean().reset_index()
                     .sort_values(by="Predicted Annual Salary (USD)", ascending=False)
                     .head(5))
    country_group["company_location"] = country_group["company_location"].map(
        lambda x: COUNTRY_NAME_MAP.get(x, x))
    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in country_group.iterrows():
        c.drawString(left_margin + 10, y,
                     f"{row['company_location']}: ${row['Predicted Annual Salary (USD)']:,.2f}")
        y -= 16

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Salary Distribution (Box Plot)")
    fig_box, ax_box = plt.subplots(figsize=(7.5, 3.5))
    ax_box.boxplot(analytics_df["Predicted Annual Salary (USD)"], vert=False, patch_artist=True,
                   boxprops=dict(facecolor="#6A9FCA", color="#1A4F8A", linewidth=1.6),
                   medianprops=dict(color="#111111", linewidth=2.2),
                   whiskerprops=dict(color="#1A4F8A", linewidth=1.4, linestyle="--"),
                   capprops=dict(color="#1A4F8A", linewidth=1.6),
                   flierprops=dict(marker="o", markerfacecolor="#1A4F8A",
                                   markeredgecolor="#1A4F8A", markersize=4, alpha=0.8))
    ax_box.set_title("Predicted Salary Spread", fontsize=12, fontweight="bold")
    chart_buffer_box = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer_box, format="png", dpi=150)
    plt.close(fig_box)
    chart_buffer_box.seek(0)
    img_box = ImageReader(chart_buffer_box)
    image_width = 480
    image_height = 200
    x_position = (width - image_width) / 2
    y -= image_height + 10
    c.drawImage(img_box, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 2 — PDF: Model Analytics
# ==================================================
def app2_generate_model_analytics_pdf(metadata, model, df, model_comparison):
    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)
    width, height = letter
    apply_pdf_metadata(c, "SalaryScope Model Analytics Report",
                       "Machine learning model diagnostics generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 55
    max_width = right_margin - left_margin

    def draw_wrapped_text(canvas_obj, text, x, y_pos, max_text_width,
                          font_name="Helvetica-Oblique", font_size=10, line_gap=14):
        canvas_obj.setFont(font_name, font_size)
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if canvas_obj.stringWidth(test_line, font_name, font_size) <= max_text_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        for line in lines:
            canvas_obj.drawString(x, y_pos, line)
            y_pos -= line_gap
        return y_pos

    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Model Analytics Report")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left_margin, y, "Performance Metrics")
    y -= 22
    c.setFont("Helvetica", 11)
    spacing = 17
    r2 = metadata["test_r2_log_scale"]
    mae = metadata["mae_usd"]
    rmse = metadata["rmse_usd"]
    c.drawString(left_margin + 10, y, f"Test R² (log scale): {r2:.4f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Mean Absolute Error (MAE): ${mae:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Root Mean Squared Error (RMSE): ${rmse:,.2f}")

    y -= 30
    performance_text = (
        f"Interpretation: The model explains approximately {r2 * 100:.1f}% of the "
        "variation in salary outcomes on the transformed scale. MAE reflects the "
        "average prediction error in USD, while RMSE places greater emphasis on larger errors."
    )
    y = draw_wrapped_text(c, performance_text, left_margin, y, max_width)

    y -= 25
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left_margin, y, "Model Comparison")
    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin + 5, y, "Model")
    c.drawString(left_margin + 260, y, "R²")
    c.drawString(left_margin + 320, y, "MAE")
    c.drawString(left_margin + 400, y, "RMSE")
    y -= 10
    c.line(left_margin, y, right_margin, y)
    y -= 15
    c.setFont("Helvetica", 10)
    sorted_models = sorted(model_comparison, key=lambda x: x["Test R²"], reverse=True)
    for row in sorted_models:
        c.drawString(left_margin + 5, y, row["Model"][:34])
        c.drawString(left_margin + 260, y, f"{row['Test R²']:.4f}")
        c.drawString(left_margin + 320, y, f"${row['MAE']:,.0f}")
        c.drawString(left_margin + 400, y, f"${row['RMSE']:,.0f}")
        y -= 15

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 2 — FEATURE IMPORTANCE
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Feature Importance")
    xgb_model_inner = model.named_steps["model"]
    preprocessor_a2 = model.named_steps["preprocessor"]
    feature_names_a2 = preprocessor_a2.get_feature_names_out()
    importances_a2 = xgb_model_inner.feature_importances_
    importance_df_a2 = (
        pd.DataFrame({"Feature": feature_names_a2, "Importance": importances_a2})
        .sort_values("Importance", ascending=False)
        .head(15)
    )
    fig_imp, ax_imp = plt.subplots(figsize=(7.5, 4.5))
    ax_imp.barh(importance_df_a2["Feature"][::-1], importance_df_a2["Importance"][::-1],
                color="#1A4F8A", edgecolor="#FFFFFF", linewidth=0.7)
    ax_imp.set_facecolor("#FFFFFF")
    fig_imp.patch.set_facecolor("#FFFFFF")
    ax_imp.grid(axis="x", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax_imp.set_axisbelow(True)
    ax_imp.spines["top"].set_visible(False)
    ax_imp.spines["right"].set_visible(False)
    ax_imp.spines["left"].set_color("#444444")
    ax_imp.spines["bottom"].set_color("#444444")
    ax_imp.tick_params(colors="#111111", labelsize=9)
    ax_imp.set_title("Top 15 Feature Importances", fontsize=12, fontweight="bold", color="#111111", pad=10)
    chart_buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(chart_buffer, format="png", dpi=150, facecolor="white")
    plt.close(fig_imp)
    chart_buffer.seek(0)
    img_imp = ImageReader(chart_buffer)
    image_width = 500
    image_height = 300
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_imp, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")
    y -= 20
    feature_text = (
        "Interpretation: Feature importance shows which transformed variables contribute "
        "most strongly to salary prediction."
    )
    y = draw_wrapped_text(c, feature_text, left_margin, y, max_width)
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 3 — PREDICTED VS ACTUAL
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Predicted vs Actual Analysis")
    data_full = df.copy()
    drop_cols2 = [col for col in ["salary", "salary_currency", "work_year"] if col in data_full.columns]
    data_full = data_full.drop(drop_cols2, axis=1)
    y_true = data_full["salary_in_usd"]
    X_a2 = data_full.drop("salary_in_usd", axis=1)
    tf_a2 = X_a2["job_title"].apply(title_features)
    tf_a2 = pd.DataFrame(list(tf_a2))
    X_a2 = pd.concat([X_a2.reset_index(drop=True), tf_a2.reset_index(drop=True)], axis=1)
    required_cols = ["title_is_exec", "title_is_mgmt", "title_is_junior", "title_is_senior", "title_domain"]
    for col_r in required_cols:
        if col_r not in X_a2.columns:
            X_a2[col_r] = 0 if col_r != "title_domain" else "unknown"
    X_a2["exp_x_domain"] = X_a2["experience_level"].astype(str) + "_" + X_a2["title_domain"].astype(str)
    X_a2.columns = X_a2.columns.astype(str)
    X_train_a2, X_test_a2, y_train_a2, y_test_a2 = train_test_split(X_a2, y_true, test_size=0.2, random_state=42)
    preds_log = model.predict(X_test_a2)
    preds_a2 = np.expm1(preds_log)
    fig_pred, ax_pred = plt.subplots(figsize=(7.5, 4.5))
    ax_pred.scatter(y_test_a2, preds_a2, alpha=0.6, color="#1A4F8A", edgecolors="none")
    min_val = min(y_test_a2.min(), preds_a2.min())
    max_val = max(y_test_a2.max(), preds_a2.max())
    ax_pred.plot([min_val, max_val], [min_val, max_val], color="red", linewidth=1.5)
    ax_pred.set_facecolor("#FFFFFF")
    fig_pred.patch.set_facecolor("#FFFFFF")
    ax_pred.grid(True, linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax_pred.set_axisbelow(True)
    ax_pred.spines["top"].set_visible(False)
    ax_pred.spines["right"].set_visible(False)
    ax_pred.spines["left"].set_color("#444444")
    ax_pred.spines["bottom"].set_color("#444444")
    ax_pred.tick_params(colors="#111111", labelsize=9)
    ax_pred.set_title("Predicted vs Actual", fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax_pred.set_xlabel("Actual Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    ax_pred.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    buf_pred = BytesIO()
    plt.tight_layout()
    plt.savefig(buf_pred, format="png", dpi=150, facecolor="white")
    plt.close(fig_pred)
    buf_pred.seek(0)
    img_pred = ImageReader(buf_pred)
    image_width = 500
    image_height = 300
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_pred, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")
    y -= 20
    pred_text = ("Interpretation: Each point represents one test observation. "
                 "Points closer to the diagonal reference line indicate more accurate predictions.")
    y = draw_wrapped_text(c, pred_text, left_margin, y, max_width)
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 4 — RESIDUAL ANALYSIS
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Residual Analysis")
    residuals_a2 = y_test_a2 - preds_a2
    fig_res, ax_res = plt.subplots(figsize=(7.5, 4.0))
    ax_res.hist(residuals_a2, bins=30, color="#1A4F8A", edgecolor="#FFFFFF", linewidth=0.7, alpha=1.0)
    ax_res.set_facecolor("#FFFFFF")
    fig_res.patch.set_facecolor("#FFFFFF")
    ax_res.grid(axis="y", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax_res.set_axisbelow(True)
    ax_res.spines["top"].set_visible(False)
    ax_res.spines["right"].set_visible(False)
    ax_res.spines["left"].set_color("#444444")
    ax_res.spines["bottom"].set_color("#444444")
    ax_res.tick_params(colors="#111111", labelsize=9)
    ax_res.set_title("Residual Distribution", fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax_res.set_xlabel("Residual", fontsize=10, color="#111111", labelpad=6)
    ax_res.set_ylabel("Count", fontsize=10, color="#111111", labelpad=6)
    buf_res = BytesIO()
    plt.tight_layout()
    plt.savefig(buf_res, format="png", dpi=150, facecolor="white")
    plt.close(fig_res)
    buf_res.seek(0)
    img_res = ImageReader(buf_res)
    image_width = 500
    image_height = 280
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_res, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")
    y -= 20
    mean_residual = residuals_a2.mean()
    bias_text = "slight underprediction" if mean_residual > 0 else (
        "slight overprediction" if mean_residual < 0 else "minimal systematic bias")
    residual_text = (
        f"Interpretation: Residuals represent the difference between actual and predicted salaries. "
        f"A distribution centered near zero suggests balanced error behavior. "
        f"Shifts away from zero may indicate {bias_text}."
    )
    y = draw_wrapped_text(c, residual_text, left_margin, y, max_width)
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 1 — Bulk Validation
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
    bulk_df = bulk_df[APP1_REQUIRED_COLUMNS]
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
# APP 2 — Bulk Validation
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
    bulk_df = bulk_df[APP2_REQUIRED_COLUMNS]
    try:
        bulk_df["remote_ratio"] = pd.to_numeric(bulk_df["remote_ratio"])
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
# SESSION STATE
# ==================================================
for key in [
    "active_model",
    "bulk_result_df", "bulk_uploaded_name", "bulk_pdf_buffer",
    "manual_pdf_buffer", "manual_prediction_result"
]:
    if key not in st.session_state:
        if key == "active_model":
            st.session_state[key] = "App 1 — Random Forest (General Salary)"
        else:
            st.session_state[key] = None


# ==================================================
# TITLE
# ==================================================
st.markdown(
    "<h1 style='text-align:center;'>SalaryScope</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<h3 style='text-align:center; color:#9BA3B0; font-weight:400;'>Salary Prediction System using Machine Learning</h3>",
    unsafe_allow_html=True
)
st.divider()

# ==================================================
# MODEL SWITCHER
# ==================================================
MODEL_OPTIONS = [
    "App 1 — Random Forest (General Salary)",
    "App 2 — XGBoost (Data Science Salary)"
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
    st.session_state.manual_prediction_result = None
    st.rerun()

IS_APP1 = (st.session_state.active_model == MODEL_OPTIONS[0])

if IS_APP1:
    st.caption("**Active Model:** Random Forest Regressor + Salary Level Classifier — trained on general salary dataset (`Salary_no_race.csv`).")
else:
    st.caption("**Active Model:** XGBoost Regressor (log-transformed) — trained on data science salary dataset (`ds_salaries.csv`).")

st.divider()

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Manual Prediction", "Bulk Scanner", "Model Analytics", "Data Insights", "About"
])


# ==================================================
# TAB 1: MANUAL PREDICTION
# ==================================================
with tab1:

    # ------------------------------------------------------------------
    # APP 1 — Manual Prediction
    # ------------------------------------------------------------------
    if IS_APP1:

        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input("Age", 18, 70, 30)
            education = st.selectbox(
                "Education Level",
                [0, 1, 2, 3],
                format_func=lambda x: {
                    0: "High School",
                    1: "Bachelor's Degree",
                    2: "Master's Degree",
                    3: "PhD"
                }[x]
            )
            gender = st.selectbox("Gender", app1_genders)
            job_title = st.selectbox("Job Title", app1_job_titles)

        with col2:
            experience = st.number_input("Years of Experience", 0.0, 40.0, 5.0, 0.5)
            senior = st.selectbox(
                "Senior Position",
                [0, 1],
                format_func=lambda x: "Yes" if x == 1 else "No"
            )
            country = st.selectbox("Country", app1_countries)

        st.caption("If your country is not listed, select 'Other'.")
        st.divider()

        if st.button("Predict Salary", use_container_width=True, type="primary"):

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

            rf_model_inner = app1_model.named_steps["model"]
            preprocessor_inner = app1_model.named_steps["preprocessor"]
            processed_input = preprocessor_inner.transform(input_df)
            tree_predictions = np.array([
                tree.predict(processed_input)[0]
                for tree in rf_model_inner.estimators_
            ])
            std_dev = np.std(tree_predictions)
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

            st.session_state.manual_prediction_result = {
                "input_details": input_details,
                "prediction": prediction,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "salary_band_label": salary_band_label
            }
            st.session_state.manual_pdf_buffer = None

        if st.session_state.manual_prediction_result is not None:
            data = st.session_state.manual_prediction_result
            prediction = data["prediction"]
            lower_bound = data["lower_bound"]
            upper_bound = data["upper_bound"]
            salary_band_label = data["salary_band_label"]
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
                    border: 1px solid #3E7DE0;
                    border-left: 5px solid #3E7DE0;
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
            st.caption("Range estimated using standard deviation of predictions across individual trees in the Random Forest model.")
            st.divider()

            if st.button("Prepare PDF Report", use_container_width=True):
                st.session_state.manual_pdf_buffer = app1_generate_manual_pdf(
                    data["input_details"], prediction, lower_bound, upper_bound,
                    data["salary_band_label"], app1_metadata, app1_classifier_metadata
                )
            if st.session_state.manual_pdf_buffer is not None:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.manual_pdf_buffer,
                    file_name="salary_prediction_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
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

            job_title_a2 = st.selectbox("Job Title", app2_job_titles)

            employee_residence_input = st.text_input("Employee Residence (Country Code)", value="US")
            employee_residence = employee_residence_input.strip().upper()
            is_valid_residence = len(employee_residence) == 2 and employee_residence.isalpha()
            if employee_residence and not is_valid_residence:
                st.warning("Country code must be exactly 2 alphabetic letters (e.g., US, IN, GB).")

        with col2:
            remote_label = st.selectbox(
                "Work Mode",
                [REMOTE_MAP[x] for x in [0, 50, 100] if x in app2_remote_ratios]
            )
            remote_ratio = REMOTE_REVERSE[remote_label]

            company_location_label = st.selectbox("Company Location", app2_country_display_options)
            if "(" in company_location_label:
                company_location = company_location_label.split("(")[-1].replace(")", "").strip()
            else:
                company_location = company_location_label

            company_size_label = st.selectbox(
                "Company Size",
                [COMPANY_SIZE_MAP[x] for x in app2_company_sizes]
            )
            company_size = COMPANY_SIZE_REVERSE[company_size_label]

        st.caption("Use ISO country codes like US, CA, IN, GB. Unknown values are handled safely.")
        st.divider()

        if st.button("Predict Salary", use_container_width=True, type="primary"):
            if not is_valid_residence:
                st.error("Please enter a valid 2-letter employee residence country code.")
                st.stop()
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

                xgb_model_a2 = app2_model.named_steps["model"]
                booster_a2 = xgb_model_a2.get_booster()
                processed_input_a2 = app2_model.named_steps["preprocessor"].transform(input_df_a2)
                dmatrix_a2 = xgb.DMatrix(processed_input_a2)
                tree_predictions_log_a2 = []
                for i in range(xgb_model_a2.n_estimators):
                    tree_pred = booster_a2.predict(dmatrix_a2, iteration_range=(i, i + 1))[0]
                    tree_predictions_log_a2.append(tree_pred)
                tree_predictions_log_a2 = np.array(tree_predictions_log_a2)
                tree_predictions_usd_a2 = np.expm1(tree_predictions_log_a2)
                std_dev_a2 = float(np.std(tree_predictions_usd_a2))
                lower_bound_a2 = max(prediction_a2 - 1.96 * std_dev_a2, 0.0)
                upper_bound_a2 = prediction_a2 + 1.96 * std_dev_a2

                input_details_a2 = {
                    "Experience Level": experience_label,
                    "Employment Type": employment_label,
                    "Job Title": job_title_a2,
                    "Employee Residence": f"{COUNTRY_NAME_MAP.get(employee_residence, employee_residence)} ({employee_residence})",
                    "Work Mode": remote_label,
                    "Company Location": COUNTRY_NAME_MAP.get(company_location, company_location),
                    "Company Size": company_size_label
                }

                st.session_state.manual_prediction_result = {
                    "input_details": input_details_a2,
                    "prediction": prediction_a2,
                    "lower_bound": lower_bound_a2,
                    "upper_bound": upper_bound_a2
                }
                st.session_state.manual_pdf_buffer = None

            except Exception as e:
                st.error("Prediction failed. Please check input values.")
                st.exception(e)
                st.session_state.manual_prediction_result = None
                st.session_state.manual_pdf_buffer = None

        if st.session_state.manual_prediction_result is not None:
            data_a2 = st.session_state.manual_prediction_result
            prediction_a2 = data_a2["prediction"]
            lower_bound_a2 = data_a2["lower_bound"]
            upper_bound_a2 = data_a2["upper_bound"]
            monthly_a2 = prediction_a2 / 12
            weekly_a2 = prediction_a2 / 52
            hourly_a2 = prediction_a2 / (52 * 40)

            st.markdown("### Estimated Annual Salary")
            st.metric("Annual Salary (USD)", f"${prediction_a2:,.2f}")
            st.divider()
            st.markdown("### Breakdown (Approximate)")
            col_m2, col_w2, col_h2 = st.columns(3)
            col_m2.metric("Monthly (Approx)", f"${monthly_a2:,.2f}")
            col_w2.metric("Weekly (Approx)", f"${weekly_a2:,.2f}")
            col_h2.metric("Hourly (Approx, 40hr/week)", f"${hourly_a2:,.2f}")
            st.divider()
            st.markdown("### Likely Salary Range (95% Confidence Interval)")
            col_low2, col_high2 = st.columns(2)
            col_low2.metric("Lower Estimate", f"${lower_bound_a2:,.2f}")
            col_high2.metric("Upper Estimate", f"${upper_bound_a2:,.2f}")
            st.caption("Range estimated using variation across individual trees in the XGBoost model.")
            st.divider()

            if st.button("Prepare PDF Report", use_container_width=True):
                st.session_state.manual_pdf_buffer = app2_generate_manual_pdf(
                    data_a2["input_details"], prediction_a2,
                    lower_bound_a2, upper_bound_a2
                )
            if st.session_state.manual_pdf_buffer is not None:
                st.download_button(
                    label="Download Prediction Summary (PDF)",
                    data=st.session_state.manual_pdf_buffer,
                    file_name="salary_prediction_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )


# ==================================================
# TAB 2: BULK SCANNER
# ==================================================
with tab2:

    col1, col2, col3 = st.columns(3)

    # -------------------------------------------------------
    # APP 1 — Bulk Scanner
    # -------------------------------------------------------
    if IS_APP1:

        with col1:
            st.subheader("Sample File")
            sample_df_a1 = df_app1.head(5)
            st.markdown("**Sample Preview:**")
            st.dataframe(sample_df_a1, use_container_width=True)
            st.markdown("### Download Sample")
            sample_format_a1 = st.selectbox("Select sample format", ["CSV", "XLSX", "JSON", "SQL"],
                                             key="sample_format_select")
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
                    sql_lines_s.append(
                        "INSERT INTO salaries VALUES "
                        f"({row['Age']}, {row['Years of Experience']}, "
                        f"{row['Education Level']}, {row['Senior']}, "
                        f"'{row['Gender']}', '{row['Job Title']}', "
                        f"'{row['Country']}');"
                    )
                file_data_s = "\n".join(sql_lines_s)
                file_name_s = "sample.sql"
                mime_s = "text/sql"
            st.download_button("Download Sample File", data=file_data_s,
                               file_name=file_name_s, mime=mime_s, use_container_width=True)

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
                                                    key="drive_format_select")
                    try:
                        with st.spinner("Downloading file from Google Drive..."):
                            response_a1 = requests.get(direct_url_a1)
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
                is_valid_a1, validation_error_a1 = app1_validate_bulk_dataframe(bulk_df_a1)
                if not is_valid_a1:
                    st.error(validation_error_a1)
                    bulk_df_a1 = None
                else:
                    bulk_df_a1 = bulk_df_a1[APP1_REQUIRED_COLUMNS]
                    st.markdown("**Uploaded File Preview:**")
                    st.dataframe(bulk_df_a1.head(), use_container_width=True)

        with col3:
            st.subheader("Run Prediction")
            has_data_a1 = "bulk_df_a1" in locals() and bulk_df_a1 is not None
            if not has_data_a1:
                st.info("Upload a file or provide a public Google Drive link to generate bulk salary predictions.")
            else:
                run_clicked_a1 = st.button("Run Bulk Prediction", use_container_width=True, type="primary")
                if run_clicked_a1:
                    try:
                        with st.spinner("Running bulk salary prediction..."):
                            preds_a1 = app1_model.predict(bulk_df_a1)
                            band_preds_a1 = app1_salary_band_model.predict(bulk_df_a1)
                            band_labels_a1 = [SALARY_BAND_LABELS.get(b, "Unknown") for b in band_preds_a1]
                            result_df_a1 = bulk_df_a1.copy()
                            result_df_a1["Predicted Annual Salary"] = preds_a1
                            result_df_a1["Estimated Salary Level"] = band_labels_a1
                            st.session_state.bulk_result_df = result_df_a1
                    except Exception:
                        st.error("Prediction failed. Please ensure the uploaded data matches the required structure and values.")
                        st.session_state.bulk_result_df = None
                        st.session_state.bulk_pdf_buffer = None

                if st.session_state.bulk_result_df is not None:
                    st.markdown("**Result Preview:**")
                    st.dataframe(st.session_state.bulk_result_df.head(), use_container_width=True)
                    st.divider()
                    st.markdown("### Export Results")
                    export_format_a1 = st.selectbox("Select export format", ["CSV", "XLSX", "JSON", "SQL"],
                                                     key="export_format_select")
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
                            "Predicted_Annual_Salary REAL, Estimated_Salary_Level TEXT);"
                        ]
                        for _, row in export_df_a1.iterrows():
                            sql_lines_e.append(
                                "INSERT INTO salary_predictions VALUES "
                                f"({row['Age']}, {row['Years of Experience']}, "
                                f"{row['Education Level']}, {row['Senior']}, "
                                f"'{row['Gender']}', '{row['Job Title']}', "
                                f"'{row['Country']}', {row['Predicted Annual Salary']}, "
                                f"'{row['Estimated Salary Level']}');"
                            )
                        file_data_e = "\n".join(sql_lines_e)
                        file_name_e = "results.sql"
                        mime_e = "text/sql"
                    st.download_button("Download File", data=file_data_e,
                                       file_name=file_name_e, mime=mime_e, use_container_width=True)

        # Bulk Analytics — App 1
        if st.session_state.bulk_result_df is not None:
            st.divider()
            st.header("Bulk Prediction Analytics")

            if st.button("Prepare Bulk PDF Report", use_container_width=True):
                st.session_state.bulk_pdf_buffer = app1_generate_bulk_pdf(
                    st.session_state.bulk_result_df
                )
            if "bulk_pdf_buffer" in st.session_state and st.session_state.bulk_pdf_buffer is not None:
                st.download_button(
                    label="Download Bulk Prediction Summary (PDF)",
                    data=st.session_state.bulk_pdf_buffer,
                    file_name="bulk_salary_summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
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

            st.divider()
            st.subheader("Salary Distribution")
            fig_hist_a1 = px.histogram(
                analytics_df_a1, x="Predicted Annual Salary",
                nbins=min(25, len(analytics_df_a1)),
                title="Distribution of Predicted Annual Salaries",
                color_discrete_sequence=["#4F8EF7"]
            )
            fig_hist_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
            _apply_theme(fig_hist_a1, {"xaxis_title": "Predicted Salary (USD)", "yaxis_title": "Count"})
            st.plotly_chart(fig_hist_a1, use_container_width=True)

            st.divider()
            st.subheader("Average Salary by Salary Level")
            band_salary_a1 = (analytics_df_a1.groupby("Estimated Salary Level")["Predicted Annual Salary"]
                              .mean().reset_index())
            fig_band_a1 = px.bar(band_salary_a1, x="Estimated Salary Level",
                                  y="Predicted Annual Salary",
                                  title="Average Predicted Salary by Salary Level",
                                  color="Estimated Salary Level",
                                  color_discrete_sequence=["#38BDF8", "#4F8EF7", "#A78BFA"])
            _apply_theme(fig_band_a1)
            st.plotly_chart(fig_band_a1, use_container_width=True)

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
            _apply_theme(fig_edu_band_a1)
            st.plotly_chart(fig_edu_band_a1, use_container_width=True)

            st.divider()
            st.subheader("Salary vs Experience Trend")
            fig_trend_a1 = px.scatter(
                analytics_df_a1, x="Years of Experience", y="Predicted Annual Salary",
                trendline="ols", trendline_color_override="#F59E0B",
                title="Predicted Salary vs Experience",
                color_discrete_sequence=["#4F8EF7"]
            )
            fig_trend_a1.update_traces(marker=dict(size=7, opacity=0.65))
            _apply_theme(fig_trend_a1)
            st.plotly_chart(fig_trend_a1, use_container_width=True)

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
            _apply_theme(fig_edu_bulk_a1)
            st.plotly_chart(fig_edu_bulk_a1, use_container_width=True)

            st.divider()
            st.subheader("Average Predicted Salary by Country")
            country_group_a1 = (analytics_df_a1.groupby("Country")["Predicted Annual Salary"]
                                .mean().reset_index()
                                .sort_values(by="Predicted Annual Salary", ascending=False))
            fig_country_bulk_a1 = px.bar(
                country_group_a1, x="Country", y="Predicted Annual Salary",
                title="Average Predicted Salary by Country",
                color="Country",
                color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B","#FB923C","#F472B6","#22D3EE"]
            )
            _apply_theme(fig_country_bulk_a1)
            st.plotly_chart(fig_country_bulk_a1, use_container_width=True)

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
            _apply_theme(fig_senior_bulk_a1)
            st.plotly_chart(fig_senior_bulk_a1, use_container_width=True)

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
                                          "#F59E0B","#FB923C","#F472B6","#22D3EE","#6366F1","#10B981"]
            )
            _apply_theme(fig_job_box_a1)
            fig_job_box_a1.update_layout(xaxis_title="Job Title",
                                          yaxis_title="Predicted Salary (USD)", showlegend=False)
            st.plotly_chart(fig_job_box_a1, use_container_width=True)

    # -------------------------------------------------------
    # APP 2 — Bulk Scanner
    # -------------------------------------------------------
    else:

        with col1:
            st.subheader("Sample File")
            sample_df_a2 = df_app2[APP2_REQUIRED_COLUMNS].head(5)
            st.markdown("Sample Preview:")
            st.dataframe(sample_df_a2, use_container_width=True)
            st.markdown("### Download Sample")
            sample_format_a2 = st.selectbox("Select sample format", ["CSV", "XLSX", "JSON", "SQL"],
                                             key="sample_format_select")
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
                               file_name=file_name_s2, mime=mime_s2, use_container_width=True)

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
                                                    key="drive_format_select")
                    try:
                        with st.spinner("Downloading file from Google Drive..."):
                            response_a2 = requests.get(direct_url_a2)
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
                is_valid_a2, validation_error_a2 = app2_validate_bulk_dataframe(bulk_df_a2)
                if not is_valid_a2:
                    st.error(validation_error_a2)
                    bulk_df_a2 = None
                else:
                    bulk_df_a2 = bulk_df_a2[APP2_REQUIRED_COLUMNS]
                    st.markdown("Uploaded File Preview:")
                    st.dataframe(bulk_df_a2.head(), use_container_width=True)

        with col3:
            st.subheader("Run Prediction")
            has_data_a2 = "bulk_df_a2" in locals() and bulk_df_a2 is not None
            if not has_data_a2:
                st.info("Upload a file or provide a public Google Drive link to generate bulk salary predictions.")
            else:
                run_clicked_a2 = st.button("Run Bulk Prediction", use_container_width=True, type="primary")
                if run_clicked_a2:
                    try:
                        with st.spinner("Running bulk salary prediction..."):
                            engineered_rows_a2 = []
                            for _, row in bulk_df_a2.iterrows():
                                j, s, ex, mg, dm = title_features(row["job_title"])
                                exd = f"{row['experience_level']}_{dm}"
                                engineered_rows_a2.append({
                                    "experience_level": row["experience_level"],
                                    "employment_type": row["employment_type"],
                                    "job_title": row["job_title"],
                                    "employee_residence": row["employee_residence"],
                                    "remote_ratio": int(row["remote_ratio"]),
                                    "company_location": row["company_location"],
                                    "company_size": row["company_size"],
                                    "title_is_junior": j,
                                    "title_is_senior": s,
                                    "title_is_exec": ex,
                                    "title_is_mgmt": mg,
                                    "title_domain": dm,
                                    "exp_x_domain": exd
                                })
                            prediction_df_a2 = pd.DataFrame(engineered_rows_a2)
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
                    st.dataframe(st.session_state.bulk_result_df.head(), use_container_width=True)
                    st.divider()
                    st.markdown("### Export Results")
                    export_format_a2 = st.selectbox("Select export format", ["CSV", "XLSX", "JSON", "SQL"],
                                                     key="export_format_select")
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
                                       file_name=file_name_e2, mime=mime_e2, use_container_width=True)

        # Bulk Analytics — App 2
        if st.session_state.bulk_result_df is not None:
            st.divider()
            st.header("Bulk Prediction Analytics")
            if st.button("Prepare Bulk PDF Report", use_container_width=True):
                st.session_state.bulk_pdf_buffer = app2_generate_bulk_pdf(
                    st.session_state.bulk_result_df
                )
            if "bulk_pdf_buffer" in st.session_state and st.session_state.bulk_pdf_buffer is not None:
                st.download_button(
                    label="Download Bulk Prediction Summary (PDF)",
                    data=st.session_state.bulk_pdf_buffer,
                    file_name="bulk_salary_summary.pdf",
                    mime="application/pdf",
                    use_container_width=True
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
            st.subheader("Predicted Salary Distribution")
            fig_hist_a2 = px.histogram(
                analytics_df_a2, x="Predicted Annual Salary (USD)",
                nbins=min(25, len(analytics_df_a2)),
                title="Distribution of Predicted Annual Salaries",
                labels={"Predicted Annual Salary (USD)": "Predicted Annual Salary (USD)"},
                color_discrete_sequence=["#4F8EF7"]
            )
            fig_hist_a2.update_layout(xaxis_title="Predicted Annual Salary (USD)",
                                       yaxis_title="Number of Records")
            _apply_theme(fig_hist_a2)
            st.plotly_chart(fig_hist_a2, use_container_width=True)

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
                        "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"}
            )
            fig_exp_a2.update_layout(xaxis_title="Experience Level",
                                      yaxis_title="Average Predicted Salary (USD)", showlegend=False)
            _apply_theme(fig_exp_a2)
            st.plotly_chart(fig_exp_a2, use_container_width=True)

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
                        "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"}
            )
            fig_size_a2.update_layout(xaxis_title="Company Size",
                                       yaxis_title="Average Predicted Salary (USD)", showlegend=False)
            _apply_theme(fig_size_a2)
            st.plotly_chart(fig_size_a2, use_container_width=True)

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
                        "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"}
            )
            fig_remote_a2.update_layout(xaxis_title="Work Mode",
                                         yaxis_title="Average Predicted Salary (USD)", showlegend=False)
            _apply_theme(fig_remote_a2)
            st.plotly_chart(fig_remote_a2, use_container_width=True)

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
                        "Predicted Annual Salary (USD)": "Average Predicted Salary (USD)"}
            )
            fig_country_a2.update_layout(xaxis_title="Country",
                                          yaxis_title="Average Predicted Salary (USD)", showlegend=False)
            _apply_theme(fig_country_a2)
            st.plotly_chart(fig_country_a2, use_container_width=True)


# ==================================================
# TAB 3: MODEL ANALYTICS
# ==================================================
with tab3:

    st.header("Model Analytics & Performance Evaluation")

    # -------------------------------------------------------
    # APP 1 — Model Analytics
    # -------------------------------------------------------
    if IS_APP1:

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
        st.dataframe(styled_df_a1, use_container_width=True)

        fig_compare_a1 = px.bar(
            comparison_df_a1, x="Model", y="Test R²",
            title="Model Comparison (Test R²)", color="Model",
            color_discrete_sequence=_MODEL_COLORS
        )
        _apply_theme(fig_compare_a1, {"xaxis_title": "Model", "yaxis_title": "Test R²", "showlegend": False})
        st.plotly_chart(fig_compare_a1, use_container_width=True)

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
        st.plotly_chart(fig_radar_a1, use_container_width=True)

        st.divider()
        st.subheader("Tuned Hyperparameters")
        st.write(app1_metadata["best_params"])

        st.divider()
        st.subheader("Feature Importance")
        rf_model_a1 = app1_model.named_steps["model"]
        preprocessor_a1 = app1_model.named_steps["preprocessor"]
        feature_names_a1 = preprocessor_a1.get_feature_names_out()
        importances_a1 = rf_model_a1.feature_importances_
        importance_df_a1 = (
            pd.DataFrame({"Feature": feature_names_a1, "Importance": importances_a1})
            .sort_values(by="Importance", ascending=False)
        )
        fig_fi_a1 = px.bar(
            importance_df_a1.head(15), x="Importance", y="Feature",
            orientation="h", title="Top Feature Importances (Random Forest)",
            color="Importance",
            color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
        )
        fig_fi_a1.update_coloraxes(showscale=False)
        _apply_theme(fig_fi_a1)
        st.plotly_chart(fig_fi_a1, use_container_width=True)

        st.divider()
        st.subheader("Cumulative Feature Importance")
        importance_sorted_a1 = importance_df_a1.sort_values(by="Importance", ascending=False).reset_index(drop=True)
        importance_sorted_a1["Cumulative Importance"] = importance_sorted_a1["Importance"].cumsum()
        fig_cumul_a1 = px.line(
            importance_sorted_a1, x=importance_sorted_a1.index + 1, y="Cumulative Importance",
            title="Cumulative Feature Importance", markers=True
        )
        _apply_theme(fig_cumul_a1, {"xaxis_title": "Number of Features", "yaxis_title": "Cumulative Importance"})
        fig_cumul_a1.add_hline(y=0.80, line_dash="dash", line_color="#F59E0B")
        st.plotly_chart(fig_cumul_a1, use_container_width=True)

        st.header("Advanced Model Diagnostics")
        X_a1_diag = df_app1.drop("Salary", axis=1)
        y_a1_diag = df_app1["Salary"]
        X_train_a1d, X_test_a1d, y_train_a1d, y_test_a1d = train_test_split(
            X_a1_diag, y_a1_diag, test_size=0.2, random_state=42)
        y_test_pred_a1d = app1_model.predict(X_test_a1d)

        st.subheader("Predicted vs Actual Values")
        fig_avp_a1 = go.Figure()
        fig_avp_a1.add_trace(go.Scatter(x=y_test_a1d, y=y_test_pred_a1d, mode="markers",
                                         name="Predictions", marker=dict(color="#3E7DE0", opacity=0.6)))
        min_val_a1 = min(y_test_a1d.min(), y_test_pred_a1d.min())
        max_val_a1 = max(y_test_a1d.max(), y_test_pred_a1d.max())
        fig_avp_a1.add_trace(go.Scatter(x=[min_val_a1, max_val_a1], y=[min_val_a1, max_val_a1],
                                         mode="lines", name="Ideal Fit",
                                         line=dict(color="#EF4444", width=2)))
        _apply_theme(fig_avp_a1, {"title": "Predicted vs Actual Salary",
                                   "xaxis_title": "Actual Salary", "yaxis_title": "Predicted Salary"})
        st.plotly_chart(fig_avp_a1, use_container_width=True)

        st.divider()
        st.subheader("Residual Plot")
        residuals_a1d = y_test_a1d - y_test_pred_a1d
        fig_res_a1 = go.Figure()
        fig_res_a1.add_trace(go.Scatter(x=y_test_pred_a1d, y=residuals_a1d, mode="markers",
                                         marker=dict(color="#3E7DE0", opacity=0.6)))
        fig_res_a1.add_hline(y=0, line_dash="dash", line_color="#EF4444")
        _apply_theme(fig_res_a1, {"title": "Residuals vs Predicted Values",
                                   "xaxis_title": "Predicted Salary",
                                   "yaxis_title": "Residual (Actual - Predicted)"})
        st.plotly_chart(fig_res_a1, use_container_width=True)

        st.divider()
        st.subheader("Residual Distribution")
        fig_rdist_a1 = px.histogram(x=residuals_a1d, nbins=30,
                                     labels={"x": "Residual"}, title="Distribution of Residuals",
                                     color_discrete_sequence=["#A78BFA"])
        fig_rdist_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
        _apply_theme(fig_rdist_a1, {"xaxis_title": "Residual", "yaxis_title": "Count"})
        st.plotly_chart(fig_rdist_a1, use_container_width=True)

        st.divider()
        st.subheader("Random Forest Prediction Uncertainty")
        rf_model_unc = app1_model.named_steps["model"]
        preprocessor_unc = app1_model.named_steps["preprocessor"]
        sample_df_unc = X_test_a1d.sample(min(100, len(X_test_a1d)), random_state=42)
        processed_sample_unc = preprocessor_unc.transform(sample_df_unc)
        tree_preds_unc = []
        for tree in rf_model_unc.estimators_:
            tree_preds_unc.append(tree.predict(processed_sample_unc))
        tree_preds_unc = np.array(tree_preds_unc)
        uncertainty_unc = tree_preds_unc.std(axis=0)
        fig_unc_a1 = px.histogram(x=uncertainty_unc, nbins=25,
                                   title="Distribution of Prediction Uncertainty Across Trees",
                                   labels={"x": "Prediction Standard Deviation", "y": "Count"},
                                   color_discrete_sequence=["#A78BFA"])
        fig_unc_a1.update_traces(marker_line_color="#1B2230", marker_line_width=0.8)
        _apply_theme(fig_unc_a1)
        st.plotly_chart(fig_unc_a1, use_container_width=True)

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
            if "Bagging" in row["Model"]:
                return ["background-color: #1E2A3A"] * len(row)
            return [""] * len(row)

        styled_cls_df_a1 = classifier_comparison_df_a1.style.apply(highlight_selected_classifier, axis=1)
        st.dataframe(styled_cls_df_a1, use_container_width=True)

        fig_cls_compare_a1 = px.bar(
            classifier_comparison_df_a1, x="Model", y="F1 Score",
            title="Classification Model Comparison (F1 Score)",
            color="Model", color_discrete_sequence=_MODEL_COLORS
        )
        _apply_theme(fig_cls_compare_a1, {"xaxis_title": "Model", "yaxis_title": "F1 Score", "showlegend": False})
        st.plotly_chart(fig_cls_compare_a1, use_container_width=True)

        st.divider()
        st.subheader("Tuned Hyperparameters")
        st.write(app1_classifier_metadata["best_params"])

        st.divider()
        st.subheader("Confusion Matrix")
        salary_band_labels_cm = pd.qcut(df_app1["Salary"], q=3, labels=["Low", "Medium", "High"])
        X_cls_cm = df_app1.drop("Salary", axis=1)
        y_cls_cm = salary_band_labels_cm
        X_train_cls, X_test_cls, y_train_cls, y_test_cls = train_test_split(
            X_cls_cm, y_cls_cm, test_size=0.2, random_state=42)
        y_pred_cls = app1_salary_band_model.predict(X_test_cls)
        cm_a1 = confusion_matrix(y_test_cls, y_pred_cls, labels=["Low", "Medium", "High"])
        fig_cm_a1 = px.imshow(
            cm_a1, text_auto=True,
            labels=dict(x="Predicted Label", y="Actual Label", color="Count"),
            x=["Early Career Range", "Professional Range", "Executive Range"],
            y=["Early Career Range", "Professional Range", "Executive Range"],
            title="Salary Level Classification Confusion Matrix",
            color_continuous_scale="Blues"
        )
        _apply_theme(fig_cm_a1)
        st.plotly_chart(fig_cm_a1, use_container_width=True)

        st.divider()
        st.subheader("Feature Importance (Classifier)")
        bagging_model_a1 = app1_salary_band_model.named_steps["classifier"]
        preprocessor_cls_a1 = app1_salary_band_model.named_steps["preprocessor"]
        feature_names_cls_a1 = preprocessor_cls_a1.get_feature_names_out()
        n_features_cls_a1 = len(feature_names_cls_a1)
        all_importances_cls_a1 = []
        for tree_cls, feat_idx_cls in zip(bagging_model_a1.estimators_, bagging_model_a1.estimators_features_):
            full_imp = np.zeros(n_features_cls_a1)
            full_imp[feat_idx_cls] = tree_cls.feature_importances_
            all_importances_cls_a1.append(full_imp)
        importances_cls_a1 = np.mean(all_importances_cls_a1, axis=0)
        importance_cls_df_a1 = (
            pd.DataFrame({"Feature": feature_names_cls_a1, "Importance": importances_cls_a1})
            .sort_values(by="Importance", ascending=False)
        )
        fig_cls_imp_a1 = px.bar(
            importance_cls_df_a1.head(15), x="Importance", y="Feature",
            orientation="h", title="Top Feature Importances (Salary Level Classifier)",
            color="Importance",
            color_continuous_scale=[[0, "#1E4799"], [0.5, "#4F8EF7"], [1.0, "#38BDF8"]]
        )
        fig_cls_imp_a1.update_coloraxes(showscale=False)
        _apply_theme(fig_cls_imp_a1)
        st.plotly_chart(fig_cls_imp_a1, use_container_width=True)

        st.divider()
        analytics_pdf_buffer_a1 = app1_generate_model_analytics_pdf(
            app1_metadata, app1_model, df_app1,
            APP1_MODEL_COMPARISON, app1_classifier_metadata, app1_salary_band_model
        )
        st.download_button(
            label="Download Model Analytics Report (PDF)",
            data=analytics_pdf_buffer_a1,
            file_name="model_analytics_report.pdf",
            mime="application/pdf",
            use_container_width=True
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
        st.dataframe(comparison_df_a2, use_container_width=True)

        st.divider()
        st.subheader("Model Performance Comparison")
        fig_compare_a2 = px.bar(comparison_df_a2, x="Model", y="Test R²",
                                 color="Model", title="Model Comparison Based on Test R²")
        fig_compare_a2.update_layout(xaxis_title="Model", yaxis_title="Test R²", showlegend=False)
        _apply_theme(fig_compare_a2)
        st.plotly_chart(fig_compare_a2, use_container_width=True)

        st.divider()
        st.subheader("Model Configuration")
        config_df_a2 = pd.DataFrame({
            "Parameter": ["Model Type", "Dataset Size", "Trees (n_estimators)", "Max Depth",
                          "Learning Rate", "Target Transformation"],
            "Value": [metadata_a2["model_type"], metadata_a2["dataset_size"],
                      metadata_a2["n_estimators"], metadata_a2["max_depth"],
                      metadata_a2["learning_rate"], metadata_a2["target_transformation"]]
        })
        st.dataframe(config_df_a2, use_container_width=True)

        st.divider()
        data_full_a2 = load_app2_dataset()
        drop_cols_a2 = [c for c in ["salary", "salary_currency", "work_year"] if c in data_full_a2.columns]
        data_full_a2 = data_full_a2.drop(drop_cols_a2, axis=1)
        y_raw_a2 = data_full_a2["salary_in_usd"]
        X_full_a2 = data_full_a2.drop("salary_in_usd", axis=1)
        tf_full_a2 = X_full_a2["job_title"].apply(title_features)
        tf_full_a2 = pd.DataFrame(
            tf_full_a2.tolist(),
            columns=["title_is_junior", "title_is_senior", "title_is_exec", "title_is_mgmt", "title_domain"]
        )
        X_full_a2 = pd.concat([X_full_a2, tf_full_a2], axis=1)
        X_full_a2["exp_x_domain"] = (X_full_a2["experience_level"].astype(str) + "_" +
                                      X_full_a2["title_domain"].astype(str))
        preds_log_full_a2 = app2_model.predict(X_full_a2)
        preds_full_a2 = np.expm1(preds_log_full_a2)

        st.subheader("Predicted vs Actual Salaries")
        fig_avp_a2 = go.Figure()
        fig_avp_a2.add_trace(go.Scatter(x=y_raw_a2, y=preds_full_a2, mode="markers",
                                         marker=dict(opacity=0.5)))
        min_val_a2 = min(y_raw_a2.min(), preds_full_a2.min())
        max_val_a2 = max(y_raw_a2.max(), preds_full_a2.max())
        fig_avp_a2.add_trace(go.Scatter(x=[min_val_a2, max_val_a2], y=[min_val_a2, max_val_a2],
                                         mode="lines", name="Ideal Fit"))
        fig_avp_a2.update_layout(xaxis_title="Actual Salary", yaxis_title="Predicted Salary")
        _apply_theme(fig_avp_a2)
        st.plotly_chart(fig_avp_a2, use_container_width=True)

        st.divider()
        st.subheader("Residual Plot")
        residuals_a2d = y_raw_a2 - preds_full_a2
        fig_res_a2 = go.Figure()
        fig_res_a2.add_trace(go.Scatter(x=preds_full_a2, y=residuals_a2d, mode="markers",
                                         marker=dict(opacity=0.5)))
        fig_res_a2.add_hline(y=0)
        fig_res_a2.update_layout(xaxis_title="Predicted Salary",
                                  yaxis_title="Residual (Actual - Predicted)")
        _apply_theme(fig_res_a2)
        st.plotly_chart(fig_res_a2, use_container_width=True)

        st.divider()
        st.subheader("Residual Distribution")
        fig_rdist_a2 = px.histogram(x=residuals_a2d, nbins=30,
                                     title="Distribution of Residuals",
                                     labels={"x": "Residual"})
        _apply_theme(fig_rdist_a2)
        st.plotly_chart(fig_rdist_a2, use_container_width=True)

        st.divider()
        st.subheader("Feature Importance by Category")
        xgb_model_a2_diag = app2_model.named_steps["model"]
        preprocessor_a2_diag = app2_model.named_steps["preprocessor"]
        sample_X_a2_diag = X_full_a2.sample(min(300, len(X_full_a2)), random_state=42)
        processed_sample_a2 = preprocessor_a2_diag.transform(sample_X_a2_diag)
        feature_names_a2_diag = preprocessor_a2_diag.get_feature_names_out()
        explainer_a2 = get_shap_explainer(app2_model)
        shap_values_a2 = explainer_a2.shap_values(processed_sample_a2)
        shap_importance_a2 = np.abs(shap_values_a2).mean(axis=0)
        fi_a2 = pd.DataFrame({"feature": feature_names_a2_diag, "importance": shap_importance_a2})

        def map_group_a2(fname):
            fname = fname.replace("cat__", "").replace("num__", "")
            if fname.startswith("employee_residence_"): return "Employee Residence"
            if fname.startswith("company_location_"): return "Company Location"
            if fname.startswith("experience_level_"): return "Experience Level"
            if fname.startswith("employment_type_"): return "Employment Type"
            if fname.startswith("company_size_"): return "Company Size"
            if fname.startswith("remote_ratio"): return "Work Mode"
            if fname.startswith("job_title_"): return "Job Title"
            if fname.startswith("title_is_"): return "Title Seniority Signals"
            if fname.startswith("title_domain_"): return "Job Domain"
            if fname.startswith("exp_x_domain_"): return "Experience × Domain Interaction"
            return "Other"

        fi_a2["group"] = fi_a2["feature"].apply(map_group_a2)
        grouped_importance_a2 = (fi_a2.groupby("group", as_index=False)["importance"]
                                  .sum().sort_values("importance", ascending=False))
        fig_grouped_a2 = px.bar(grouped_importance_a2, x="importance", y="group",
                                 orientation="h", title="Grouped Feature Importance")
        fig_grouped_a2.update_layout(yaxis=dict(autorange="reversed"),
                                      xaxis_title="Total Model Influence", yaxis_title="Feature Group")
        _apply_theme(fig_grouped_a2)
        st.plotly_chart(fig_grouped_a2, use_container_width=True)

        st.subheader("Predicted Salary Distribution")
        fig_pred_dist_a2 = px.histogram(x=preds_full_a2, nbins=30,
                                         title="Distribution of Predicted Salaries",
                                         labels={"x": "Predicted Salary"})
        _apply_theme(fig_pred_dist_a2)
        st.plotly_chart(fig_pred_dist_a2, use_container_width=True)

        st.divider()
        st.subheader("Top Feature Drivers (SHAP Analysis)")
        st.caption(
            "SHAP values measure how strongly each feature influences the model's predictions. "
            "Higher values indicate stronger impact on predicted salary."
        )
        raw_feature_names_a2 = preprocessor_a2_diag.get_feature_names_out()
        feature_names_clean_a2 = [clean_feature_name(f) for f in raw_feature_names_a2]
        shap_df_a2 = (
            pd.DataFrame({"Feature": feature_names_clean_a2, "SHAP Importance": shap_importance_a2})
            .sort_values("SHAP Importance", ascending=False)
        )
        fig_shap_a2 = px.bar(
            shap_df_a2.head(15), x="SHAP Importance", y="Feature",
            orientation="h", color="SHAP Importance",
            color_continuous_scale="Blues",
            title="Top Features Influencing Salary Predictions"
        )
        fig_shap_a2.update_layout(yaxis=dict(autorange="reversed"),
                                   xaxis_title="Average |SHAP Value|",
                                   yaxis_title="Feature", coloraxis_showscale=False)
        _apply_theme(fig_shap_a2)
        st.plotly_chart(fig_shap_a2, use_container_width=True)

        st.divider()
        pdf_buffer_a2 = app2_generate_model_analytics_pdf(
            metadata_a2, app2_model, data_full_a2, APP2_MODEL_COMPARISON
        )
        st.download_button(
            "Download Model Analytics Report (PDF)",
            data=pdf_buffer_a2,
            file_name="model_analytics_report.pdf",
            mime="application/pdf",
            use_container_width=True
        )


# ==================================================
# TAB 4: DATA INSIGHTS
# ==================================================
with tab4:

    st.header("Dataset Insights & Exploratory Analysis")

    # -------------------------------------------------------
    # APP 1 — Data Insights
    # -------------------------------------------------------
    if IS_APP1:

        st.subheader("Dataset Overview")
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
        _apply_theme(fig_hist_di_a1, {"xaxis_title": "Salary (USD)", "yaxis_title": "Count"})
        st.plotly_chart(fig_hist_di_a1, use_container_width=True)

        st.divider()
        st.subheader("Average Salary by Education Level")
        edu_map_di = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
        edu_salary_di = df_app1.groupby("Education Level")["Salary"].mean().reset_index()
        edu_salary_di["Education Level"] = edu_salary_di["Education Level"].map(edu_map_di)
        fig_edu_di_a1 = px.bar(edu_salary_di, x="Education Level", y="Salary",
                                title="Average Salary by Education",
                                color="Education Level",
                                color_discrete_sequence=["#4F8EF7", "#38BDF8", "#34D399", "#A78BFA"])
        _apply_theme(fig_edu_di_a1)
        st.plotly_chart(fig_edu_di_a1, use_container_width=True)

        st.divider()
        st.subheader("Salary vs Years of Experience")
        fig_exp_di_a1 = px.scatter(df_app1, x="Years of Experience", y="Salary",
                                    trendline="ols",
                                    title="Salary vs Experience (with Trend Line)",
                                    color_discrete_sequence=["#4F8EF7"])
        fig_exp_di_a1.update_traces(marker=dict(opacity=0.55, size=5), selector=dict(mode="markers"))
        _apply_theme(fig_exp_di_a1)
        st.plotly_chart(fig_exp_di_a1, use_container_width=True)

        st.divider()
        st.subheader("Senior vs Non-Senior Salary Comparison")
        senior_salary_di = df_app1.groupby("Senior")["Salary"].mean().reset_index()
        senior_salary_di["Senior"] = senior_salary_di["Senior"].map({0: "Non-Senior", 1: "Senior"})
        fig_senior_di_a1 = px.bar(senior_salary_di, x="Senior", y="Salary",
                                   title="Average Salary by Seniority",
                                   color="Senior",
                                   color_discrete_sequence=["#38BDF8", "#4F8EF7"])
        _apply_theme(fig_senior_di_a1)
        st.plotly_chart(fig_senior_di_a1, use_container_width=True)

        st.divider()
        st.subheader("Average Salary by Country")
        country_salary_di = df_app1.groupby("Country")["Salary"].mean().reset_index()
        fig_country_di_a1 = px.bar(country_salary_di, x="Country", y="Salary",
                                    title="Average Salary by Country",
                                    color="Country",
                                    color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA",
                                                              "#F59E0B","#FB923C","#F472B6","#22D3EE"])
        _apply_theme(fig_country_di_a1)
        st.plotly_chart(fig_country_di_a1, use_container_width=True)

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

        data_full_di_a2 = load_app2_dataset()

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
        st.subheader("Distribution of Data Science Salaries")
        fig_hist_di_a2 = px.histogram(data_full_di_a2, x="salary_in_usd", nbins=30,
                                       title="Distribution of Annual Salaries for Data Science Roles",
                                       labels={"salary_in_usd": "Annual Salary (USD)",
                                               "count": "Number of Employees"},
                                       color_discrete_sequence=["#4F8EF7"])
        fig_hist_di_a2.update_layout(xaxis_title="Annual Salary (USD)",
                                      yaxis_title="Number of Employees")
        _apply_theme(fig_hist_di_a2)
        st.plotly_chart(fig_hist_di_a2, use_container_width=True)

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
                                     yaxis_title="Average Annual Salary (USD)", showlegend=False)
        _apply_theme(fig_exp_di_a2)
        st.plotly_chart(fig_exp_di_a2, use_container_width=True)

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
                                      yaxis_title="Average Annual Salary (USD)", showlegend=False)
        _apply_theme(fig_size_di_a2)
        st.plotly_chart(fig_size_di_a2, use_container_width=True)

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
                                        yaxis_title="Average Annual Salary (USD)", showlegend=False)
        _apply_theme(fig_remote_di_a2)
        st.plotly_chart(fig_remote_di_a2, use_container_width=True)

        st.divider()
        st.subheader("Top Countries by Average Salary")
        country_group_di_a2 = (data_full_di_a2.groupby("Company Location")["salary_in_usd"]
                                .mean().reset_index()
                                .sort_values(by="salary_in_usd", ascending=False)
                                .head(10))
        fig_country_di_a2 = px.bar(
            country_group_di_a2, x="Company Location", y="salary_in_usd",
            title="Top Countries with Highest Average Data Science Salaries",
            color="Company Location",
            labels={"Company Location": "Country", "salary_in_usd": "Average Annual Salary (USD)"},
            color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B",
                                      "#FB923C","#F472B6","#22D3EE"]
        )
        fig_country_di_a2.update_layout(xaxis_title="Country",
                                         yaxis_title="Average Annual Salary (USD)", showlegend=False)
        _apply_theme(fig_country_di_a2)
        st.plotly_chart(fig_country_di_a2, use_container_width=True)

        st.divider()
        st.subheader("Salary Distribution by Job Title")
        top_jobs_di_a2 = data_full_di_a2["job_title"].value_counts().head(10).index
        job_df_di_a2 = data_full_di_a2[data_full_di_a2["job_title"].isin(top_jobs_di_a2)]
        fig_job_di_a2 = px.box(
            job_df_di_a2, x="job_title", y="salary_in_usd",
            title="Salary Distribution Across Major Data Science Roles",
            color="job_title",
            labels={"job_title": "Data Science Job Role", "salary_in_usd": "Annual Salary (USD)"},
            color_discrete_sequence=["#4F8EF7","#38BDF8","#34D399","#A78BFA","#F59E0B",
                                      "#FB923C","#F472B6","#22D3EE","#6366F1","#10B981"]
        )
        fig_job_di_a2.update_layout(xaxis_title="Data Science Job Role",
                                     yaxis_title="Annual Salary (USD)", showlegend=False)
        _apply_theme(fig_job_di_a2)
        st.plotly_chart(fig_job_di_a2, use_container_width=True)


# ==================================================
# TAB 5: ABOUT (Merged from both apps)
# ==================================================
with tab5:

    st.markdown("## About SalaryScope")

    st.markdown(
        "SalaryScope is a machine learning-based web application "
        "developed as a Final Year B.Tech Project. It provides salary "
        "prediction capabilities through two distinct models, each trained "
        "on a different dataset and targeting different use cases."
    )

    st.divider()

    col_ab1, col_ab2 = st.columns(2)

    with col_ab1:
        st.markdown("### App 1 — Random Forest (General Salary)")
        st.markdown("""
**Dataset:** General salary dataset (`Salary_no_race.csv`)

**Models:**
- Random Forest Regressor (optimized via GridSearchCV) for salary prediction
- Bagging Classifier (optimized via GridSearchCV) for salary level classification

**Input Features:**
- Age, Years of Experience, Education Level, Senior Position, Gender, Job Title, Country

**Salary Level Output:**
- Early Career Range (Low)
- Professional Range (Medium)
- Executive Range (High)

**Features:**
- Manual salary prediction with salary band classification
- Bulk salary estimation with level assignment
- Predicted vs Actual diagnostics
- Prediction uncertainty (per-tree standard deviation)
- Classification confusion matrix & feature importance
- Multi-format export (CSV, JSON, XLSX, SQL)
- Google Drive public link upload
- PDF report generation (manual + bulk + model analytics)
        """)

    with col_ab2:
        st.markdown("### App 2 — XGBoost (Data Science Salary)")
        st.markdown("""
**Dataset:** Data science salary dataset (`ds_salaries.csv`)

**Model:**
- XGBoost Regressor with log-transformed target (`log1p(salary_in_usd)`)
- Custom feature engineering on job titles (seniority, domain, management signals)

**Input Features:**
- Experience Level, Employment Type, Job Title, Employee Residence, Work Mode, Company Location, Company Size

**Features:**
- Manual salary prediction with 95% CI
- Bulk salary estimation
- SHAP-based grouped feature importance
- Predicted vs Actual diagnostics
- Residual analysis
- Multi-format export (CSV, JSON, XLSX, SQL)
- Google Drive public link upload
- PDF report generation (manual + bulk + model analytics)
        """)

    st.divider()

    st.markdown("### Shared System Features")
    st.markdown("""
- Model switcher to toggle between both prediction systems
- Unified dark professional theme across the entire application
- 5-tab layout: Manual Prediction, Bulk Scanner, Model Analytics, Data Insights, About
- ReportLab-based multi-page PDF reports with embedded charts
- State-managed UI to prevent re-computation on interaction
    """)

    st.divider()

    st.markdown("### Technologies Used")
    st.markdown("""
- Python
- Streamlit
- Pandas / NumPy
- Scikit-learn (Random Forest, Bagging Classifier, GridSearchCV)
- XGBoost
- SHAP (SHapley Additive exPlanations)
- Plotly / Matplotlib
- ReportLab (PDF generation)
- Requests (Cloud file retrieval)
    """)
