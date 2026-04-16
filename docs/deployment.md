# SalaryScope — Deployment Guide
**Version:** 1.1.0  
**Project:** SalaryScope — Salary Prediction System using Machine Learning  
**Author:** Yash Shah  
**Document Type:** Deployment and Operations Guide

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Firebase Project Setup](#3-firebase-project-setup)
4. [HuggingFace Repository Setup](#4-huggingface-repository-setup)
5. [Local Development Setup](#5-local-development-setup)
6. [Streamlit Cloud Deployment](#6-streamlit-cloud-deployment)
7. [Secrets Configuration Reference](#7-secrets-configuration-reference)
8. [Model Artefact Preparation and Upload](#8-model-artefact-preparation-and-upload)
9. [Two-App Deployment Strategy](#9-two-app-deployment-strategy)
10. [Post-Deployment Verification](#10-post-deployment-verification)
11. [Operations and Maintenance](#11-operations-and-maintenance)
12. [Rollback Procedures](#12-rollback-procedures)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Overview

SalaryScope is deployed as a Streamlit Cloud application. It depends on three external services:

| Service | Purpose | Cost Tier |
|---|---|---|
| Streamlit Cloud | Application hosting | Free tier |
| Firebase Authentication | User login, registration, email verification | Spark (free) plan |
| Firebase Firestore | Persistent data storage | Spark (free) plan |
| HuggingFace | Model artefact and Model Hub registry storage | Free (private dataset repo) |

The application is split into two deployments:

| App | File | Description |
|---|---|---|
| Full App | `app_resume.py` | Includes NLP resume analysis (spaCy + pdfplumber) |
| Lite App | `app.py` | No resume analysis; lower memory footprint |

Both apps share the same Firebase project, Firestore database, and HuggingFace repository.

---

## 2. Prerequisites

### 2.1 Accounts Required

- [GitHub](https://github.com) account — for source code hosting and Streamlit Cloud connection
- [Streamlit Community Cloud](https://streamlit.io/cloud) account — for deployment
- [Firebase](https://firebase.google.com) account (Google account) — for Authentication and Firestore
- [HuggingFace](https://huggingface.co) account — for model storage

### 2.2 Local Development Tools

```bash
# Python 3.13+
python --version

# pip
pip --version

# git
git --version
```

### 2.3 Python Packages (for local development)

Install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Key packages include: `streamlit`, `scikit-learn`, `xgboost`, `shap`, `mlxtend`, `spacy`, `pdfplumber`, `firebase-admin`, `huggingface_hub>=0.20`, `reportlab`, `plotly`, `pandas`, `numpy`, `joblib`, `babel`, `bcrypt`, `psutil`, `requests`, `onnxruntime>=1.18` (required for loading ONNX bundles at runtime), `skl2onnx>=1.17` (used offline when converting sklearn models to ONNX — not required for running the app).

For resume analysis, also download the spaCy English model:

```bash
python -m spacy download en_core_web_sm
```

---

## 3. Firebase Project Setup

### 3.1 Create a Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com).
2. Click **Add Project**, name it (e.g. `salaryscope`), and follow the setup wizard.
3. You do not need Google Analytics for this project.

### 3.2 Enable Firebase Authentication

1. In the Firebase Console, navigate to **Build → Authentication**.
2. Click **Get started**.
3. Under **Sign-in providers**, enable **Email/Password**.
4. Enable the **Email link (passwordless sign-in)** option only if needed (not required for SalaryScope).

### 3.3 Enable Firestore

1. Navigate to **Build → Firestore Database**.
2. Click **Create database**.
3. Choose **Start in production mode** (you will add security rules next).
4. Select a region close to your expected user base.

### 3.4 Firestore Security Rules

Set the following security rules to allow the application backend (service account) full access while blocking direct client access:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // All access via Admin SDK (service account) only.
    // No direct client-side Firebase SDK access is used by SalaryScope.
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

Since SalaryScope uses the Firebase Admin SDK (server-side), these rules do not affect the application — the Admin SDK bypasses Firestore security rules by default.

### 3.5 Get the Firebase Web API Key

1. In the Firebase Console, click the gear icon → **Project settings**.
2. Under the **General** tab, scroll to **Your apps**.
3. If no web app exists, click **Add app → Web** and register it.
4. Copy the **Web API Key** (also labelled `apiKey` in the Firebase config). This is `FIREBASE_API_KEY` in Streamlit secrets.

### 3.6 Generate a Service Account Key

1. In **Project settings → Service accounts**.
2. Click **Generate new private key**.
3. Download the JSON file. This file contains all fields needed for `FIREBASE_SERVICE_ACCOUNT` in Streamlit secrets.

> **Security:** Keep this JSON file private. Do not commit it to version control. Delete the local copy after configuring secrets.

### 3.7 Create the Admin User

1. In Firebase Console → **Authentication → Users**, click **Add user**.
2. Enter the email and a strong password for the admin account.
3. This email will be set as `ADMIN_EMAIL` in Streamlit secrets.
4. Alternatively, register through the application — but the account must be email-verified before admin features work.

---

## 4. HuggingFace Repository Setup

### 4.1 Create a Dataset Repository

1. Log in to [HuggingFace](https://huggingface.co).
2. Click your avatar → **New Dataset**.
3. Name the repository (e.g. `salaryscope-models`).
4. Set visibility to **Private**.
5. Click **Create dataset**.

The `HF_REPO_ID` will be in the format `your-username/salaryscope-models`.

### 4.2 Create an Access Token

1. Click your avatar → **Settings → Access Tokens**.
2. Click **New token**.
3. Name it (e.g. `salaryscope-write`).
4. Set **Role** to **Write** (required for model uploads and registry updates).
5. Click **Generate a token** and copy it. This is `HF_TOKEN` in Streamlit secrets.

> The token is shown only once. Store it securely before closing the page.

### 4.3 Initialise the Registry

The `models_registry.json` file is created automatically the first time a model is uploaded via the Model Hub admin interface. If you want to initialise it manually, create a file with the following content and upload it to the root of the dataset repo:

```json
{
  "models": []
}
```

Upload via the HuggingFace web interface or with the SDK:

```python
from huggingface_hub import HfApi
api = HfApi(token="your-hf-token")
api.upload_file(
    path_or_fileobj=b'{"models": []}',
    path_in_repo="models_registry.json",
    repo_id="your-username/salaryscope-models",
    repo_type="dataset"
)
```

---

## 5. Local Development Setup

### 5.1 Clone the Repository

```bash
git clone https://github.com/your-username/salaryscope.git
cd salaryscope
```

### 5.2 Install Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 5.3 Configure Local Secrets

Create the file `.streamlit/secrets.toml` in the project root. This file must not be committed to version control (it is listed in `.gitignore`).

```toml
# .streamlit/secrets.toml

FIREBASE_API_KEY = "your-firebase-web-api-key"
ADMIN_EMAIL = "admin@yourdomain.com"
HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxx"
HF_REPO_ID = "your-username/salaryscope-models"
IS_LOCAL = true

[FIREBASE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n"
client_email = "firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
universe_domain = "googleapis.com"
```

> **Important:** The `private_key` field must have actual newlines (not `\n` as a literal two-character sequence). When copying from the downloaded service account JSON, replace all `\n` in the private key value with real newlines.

### 5.4 Place Model Artefacts

Model artefacts are downloaded from HuggingFace at startup. For local development, either:

- Ensure HuggingFace secrets are configured and the repo contains the artefacts (they will be downloaded on first run).
- Or place artefact files locally in the path expected by the loading code and temporarily adjust the loading logic.

### 5.5 Run Locally

```bash
# Full app (with resume analysis)
streamlit run app_resume.py

# Lite app (without resume analysis)
streamlit run app.py
```

The application will be available at `http://localhost:8501`.

---

## 6. Streamlit Cloud Deployment

### 6.1 Push to GitHub

Ensure the repository is pushed to GitHub. The repository must be public or accessible to the Streamlit Cloud account.

```bash
git add .
git commit -m "Initial deployment"
git push origin main
```

Ensure `.gitignore` excludes:

```
.streamlit/secrets.toml
*.pkl
__pycache__/
.env
```

### 6.2 Create a Streamlit Cloud App

1. Go to [share.streamlit.io](https://share.streamlit.io).
2. Click **New app**.
3. Connect your GitHub account if not already connected.
4. Select the repository, branch (`main`), and main file (`app_resume.py` for the full app, `app.py` for the lite app).
5. Click **Deploy**.

### 6.3 Configure Secrets in Streamlit Cloud

1. In the Streamlit Cloud dashboard, find the deployed app.
2. Click the **three-dot menu → Settings → Secrets**.
3. Paste the full contents of your `.streamlit/secrets.toml` file into the secrets editor.
4. Click **Save**.

> **Important:** Do not set `IS_LOCAL = true` in the Streamlit Cloud secrets. Either omit the key entirely or set it to `false`. The `IS_LOCAL` flag enables local-only features (CoL index save/reset to disk) that do not work on Streamlit Cloud.

### 6.4 Trigger a Reboot

After saving secrets, click **Reboot app** to ensure the new secrets take effect.

---

## 7. Secrets Configuration Reference

The following table lists all secrets used by the application.

| Key | Type | Required (Full App) | Required (Lite App) | Description |
|---|---|---|---|---|
| `FIREBASE_API_KEY` | String | Yes | Yes | Firebase project web API key (from Project Settings → General → Web API Key) |
| `FIREBASE_SERVICE_ACCOUNT` | TOML table | Yes | Yes | Full Firebase service account JSON as a TOML table. All fields from the downloaded JSON must be present |
| `ADMIN_EMAIL` | String | Yes | No | Email address that receives admin privileges. Only needed for the Admin Panel tab (full app only) |
| `HF_TOKEN` | String | Yes | No | HuggingFace access token with write scope. Only needed for model artefact loading and Model Hub (full app only) |
| `HF_REPO_ID` | String | Yes | No | HuggingFace dataset repository in the form `"owner/repo-name"`. Only needed for full app |
| `IS_LOCAL` | Boolean | No | No | Set to `true` in local development to enable disk-based CoL index override save/reset. Omit or set `false` on Streamlit Cloud |

### 7.1 FIREBASE\_SERVICE\_ACCOUNT Format

The service account JSON downloaded from Firebase contains these fields. All must be present in the TOML table:

```toml
[FIREBASE_SERVICE_ACCOUNT]
type = "service_account"
project_id = "your-project-id"
private_key_id = "abc123"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "firebase-adminsdk@your-project.iam.gserviceaccount.com"
client_id = "123456789012345678"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
universe_domain = "googleapis.com"
```

> **Note on `private_key`:** Streamlit secrets escapes newlines in string values. The application handles this automatically in `database.py` by replacing `\\n` with `\n` after reading from secrets. You do not need to manually modify the key when pasting into Streamlit Cloud's secrets editor — paste the raw JSON value including the literal `\n` sequences.

---

## 8. Model Artefact Preparation and Upload

### 8.1 Built-in Model Artefacts (App 1 and App 2)

The built-in model artefacts (Random Forest, XGBoost, KMeans, etc.) are trained in Jupyter notebooks and uploaded to the HuggingFace repository during the development phase. The application downloads them at startup using `@st.cache_resource`.

**Artefacts to upload for App 1:**

```
app1_model.pkl
app1_metadata.json
app1_salary_band_model.pkl
app1_classifier_metadata.json
app1_cluster_model.pkl
app1_cluster_metadata.json
assoc_rules_a1_v2.pkl
app1_analytics.pkl
app1_model_comparison.json
app1_classifier_comparison.json
df_app1.pkl
```

**Artefacts to upload for App 2:**

```
app2_model.pkl
app2_metadata.json
app2_analytics.pkl
app2_model_comparison.json
df_app2.pkl
```

**Uploading via Python:**

```python
from huggingface_hub import HfApi
import os

api = HfApi(token="your-hf-token")
repo_id = "your-username/salaryscope-models"

files_to_upload = [
    "app1_model.pkl",
    "app1_metadata.json",
    # ... all artefact files
]

for filename in files_to_upload:
    api.upload_file(
        path_or_fileobj=filename,
        path_in_repo=filename,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Upload {filename}"
    )
    print(f"Uploaded {filename}")
```

### 8.2 Model Hub Bundles (Admin Upload)

Model Hub bundles are uploaded through the application's Model Hub admin interface, not manually. Each bundle consists of:

**ONNX format (recommended):**

| File | Required | Description |
|---|---|---|
| `model.onnx` | Yes | ONNX computation graph — no pickle deserialisation on load |
| `columns.json` | Yes | JSON array of feature column names — plain text, no pickle risk |
| `schema.json` | Yes | UI field definitions (see Data Dictionary §6.3) |
| `aliases.json` | No | Display labels for selectbox fields. Upload alongside or push separately. |

**Pickle format (legacy):**

| File | Required | Description |
|---|---|---|
| `model.pkl` | Yes | sklearn-compatible estimator saved with `joblib.dump()` |
| `columns.pkl` | Yes | Ordered list of feature column names saved with `joblib.dump()` |
| `schema.json` | Yes | UI field definitions (see Data Dictionary §6.3) |
| `aliases.json` | No | Display labels for selectbox fields. Upload alongside or push separately. |

**Preparing an ONNX bundle (recommended):**

```python
import json
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

# Export trained sklearn model to ONNX
columns = list(X_train.columns)   # ordered list of feature column names
initial_type = [("float_input", FloatTensorType([None, len(columns)]))]
onnx_model = convert_sklearn(trained_model, initial_types=initial_type, target_opset=17)

with open("model.onnx", "wb") as f:
    f.write(onnx_model.SerializeToString())

# Save columns as JSON (plain text — no pickle)
with open("columns.json", "w") as f:
    json.dump(columns, f)
```

**Preparing a pickle bundle (legacy):**

```python
import joblib
import json

# Save model
joblib.dump(trained_model, "model.pkl")

# Save columns (must be a list of strings in the exact order the model expects)
joblib.dump(list(X_train.columns), "columns.pkl")

# Create schema.json
schema = {
    "fields": [
        {
            "name": "years_experience",
            "type": "float",
            "ui": "slider",
            "label": "Years of Experience",
            "min": 0.0,
            "max": 40.0,
            "default": 5.0,
            "step": 0.5
        },
        {
            "name": "job_title",
            "type": "category",
            "ui": "selectbox",
            "label": "Job Title",
            "values": ["Software Engineer", "Data Scientist", "Product Manager"]
        }
        # ... more fields
    ]
}

with open("schema.json", "w") as f:
    json.dump(schema, f, indent=2)

# Optional: create aliases.json for fields with cryptic model values
# (use a sidecar file for large sets; inline "aliases" key in schema.json for small sets)
aliases = {
    "experience_level": {
        "EN": "Entry Level (0-4 years)",
        "MI": "Mid Level (5-12 years)",
        "SE": "Senior (13-22 years)",
        "EX": "Executive / Principal (23+ years)"
    }
    # Add more fields as needed. Omit fields whose values are already human-readable.
}

with open("aliases.json", "w") as f:
    json.dump(aliases, f, indent=2)
```

**Uploading through the admin UI:**

1. Log in with the admin account.
2. Navigate to the **Model Hub** tab.
3. Scroll to **Upload Bundle**.
4. Select **ONNX (recommended)** or **Pickle (legacy)** from the format radio.
5. Upload the model file (`model.onnx` or `model.pkl`) and columns file (`columns.json` or `columns.pkl`).
6. Upload `schema.json`. Optionally upload `aliases.json` in the same step.
7. Fill in Display Name, Description, and Target Variable Name.
8. Click **Upload Bundle**.

**Pushing aliases.json to an existing bundle** (without re-uploading the full bundle):

1. Go to **Model Hub → Schema Editor → Upload / Validate** tab.
2. Upload the `aliases.json` file.
3. Enter the bundle path (e.g. `models/model_20260415_abc123/`) and the model ID.
4. Click **Push aliases.json to bundle**.
5. Click **Load Model** in the prediction panel to reload with the new aliases applied.

---

## 9. Two-App Deployment Strategy

The application is deployed as two separate Streamlit Cloud apps from the same GitHub repository.

### 9.1 Why Two Apps

The lite app (`app.py`) is a substantially stripped-down version of the full app, not just a version without resume analysis. It was built to run comfortably within Streamlit Cloud free-tier memory limits by removing the most resource-intensive features and their dependencies (spaCy, pdfplumber, HuggingFace Hub, the 11 financial utility modules, and several entire tabs).

The full app (`app_resume.py`) requires more RAM due to spaCy's `en_core_web_sm` model, pdfplumber, and the full financial tools chain, and is more appropriate for users who need all features.

### 9.2 Deploying Both Apps

Repeat the steps in Section 6 twice — once pointing to `app_resume.py` (full app) and once pointing to `app.py` (lite app).

**Secrets for the Lite App:** The lite app does not use HuggingFace at all. `HF_TOKEN` and `HF_REPO_ID` can be omitted from the lite app's Streamlit Cloud secrets. `ADMIN_EMAIL` can also be omitted since there is no Admin Panel. Only `FIREBASE_API_KEY` and `FIREBASE_SERVICE_ACCOUNT` are strictly required for the lite app.

### 9.3 Shared Resources

Both apps share:
- The same Firebase project (Authentication + Firestore)
- The same model artefacts (downloaded from HuggingFace on the full app; the lite app loads them the same way)
- The same Firestore collections (`users`, `predictions`) — prediction history made on either app appears in the same Profile tab

### 9.4 Feature Differences (Full App vs Lite App)

| Feature / Tab | Full App (`app_resume.py`) | Lite App (`app.py`) |
|---|---|---|
| Manual Prediction | ✅ | ✅ |
| Batch Prediction | ✅ | ✅ |
| Model Analytics | ✅ | ✅ |
| Data Insights | ✅ | ✅ |
| Profile tab | ✅ | ✅ |
| About tab | ✅ (modular, from `about_tab.py`) | ✅ (inline, simplified) |
| Resume Analysis tab | ✅ | ❌ |
| Scenario Analysis tab | ✅ | ❌ |
| Model Hub tab | ✅ | ❌ |
| Admin Panel tab | ✅ | ❌ |
| Financial tools (11 modules) | ✅ | ❌ |
| Prediction feedback system | ✅ | ❌ |
| Salary negotiation tips | ✅ | ✅ |
| Career recommendations | ✅ | ✅ |
| spaCy / pdfplumber | ✅ | ❌ |
| HuggingFace Hub dependency | ✅ | ❌ |
| `ADMIN_EMAIL` secret required | Yes | No |
| `HF_TOKEN` / `HF_REPO_ID` required | Yes | No |
| Memory usage | Higher | Significantly lower |
| Startup time | Slower | Faster |

> **Note on the Lite App About tab:** The lite app renders its About content inline in `app.py` rather than importing `about_tab.py`. The content is a simplified version — it omits resume analysis, scenario analysis, Model Hub, and financial tools from the feature list.

> **Note on text input styling:** The lite app applies CSS styling to `.stTextInput` elements (which is commented out in the full app). This is a minor cosmetic difference with no functional impact.

---

## 10. Post-Deployment Verification

After deploying, verify the following:

### 10.1 Application Load

- Open the deployed URL in a browser.
- Confirm the app loads without errors.
- Check that both Model 1 and Model 2 can be selected from the sidebar dropdown.
- Confirm the dark theme is applied correctly.

### 10.2 Prediction Functionality

- Navigate to Manual Prediction and run a prediction with both models.
- Verify the results display correctly (salary card, breakdown, negotiation tips, recommendations).

### 10.3 Authentication

- Register a new account. Verify a confirmation email is received.
- Click the verification link. Verify login works after verification.
- Log in and check that the Profile tab appears.
- Log out and confirm the Profile tab disappears.

### 10.4 Firestore Connectivity

- Make a manual prediction while logged in.
- Navigate to the Profile tab and verify the prediction appears in the history.

### 10.5 HuggingFace Connectivity

- Navigate to the Model Hub tab while logged in.
- Verify the model registry loads (or shows an empty state if no models are uploaded).
- If a bundle with `aliases.json` is present, load it and verify that selectbox fields display human-readable labels (e.g. "Senior (13-22 years)" instead of "SE").

### 10.6 Admin Panel

- Log in with the admin account.
- Navigate to the Admin Panel tab.
- Verify it loads without "Access denied".
- Confirm system diagnostics display correctly.

### 10.7 Resume Analysis (Full App Only)

- Navigate to the Resume Analysis tab.
- Upload a simple PDF resume.
- Verify extraction runs and returns features.

### 10.8 PDF Generation

- Run a manual prediction and click Prepare PDF Report.
- Verify the download button appears and the PDF downloads correctly.

---

## 11. Operations and Maintenance

### 11.1 Monitoring

Streamlit Cloud does not provide built-in application monitoring. Monitor the application by:

- Checking the Streamlit Cloud dashboard for crash logs (available under the app's **Manage app → Logs** section).
- Using the Admin Panel's system diagnostics (RAM usage, session state, cache status).
- Periodically loading the feedback analytics in the Admin Panel to verify Firestore connectivity and user activity.

### 11.2 Updating the Application

1. Make code changes locally and test with `streamlit run app_resume.py`.
2. Commit and push to the GitHub repository.
3. Streamlit Cloud automatically detects the push and redeploys within a few minutes.
4. For both apps (full and lite), redeploy is triggered automatically from the same push.

### 11.3 Updating Model Artefacts

To update a built-in model artefact (e.g. a retrained Random Forest model):

1. Save the new model with joblib: `joblib.dump(new_model, "app1_model.pkl")`.
2. Upload to HuggingFace, overwriting the existing file:

```python
api.upload_file(
    path_or_fileobj="app1_model.pkl",
    path_in_repo="app1_model.pkl",
    repo_id=repo_id,
    repo_type="dataset",
    commit_message="Update App 1 model - v1.2"
)
```

3. Click **Reboot app** in the Streamlit Cloud dashboard to force a fresh download (the `@st.cache_resource` cache is cleared on reboot).

### 11.4 Managing Model Hub Models

Use the Model Hub admin interface (Registry Manager) to:

- **Deactivate a model:** Hides it from the user dropdown without deleting the bundle.
- **Reactivate a model:** Makes it visible again.
- **Rollback to a previous version:** Deactivates all family members except the target version.

Model bundle files are never deleted from HuggingFace through the UI — deactivation only updates the registry.

### 11.5 Clearing Stale Rate Limit Records

Rate limit records in Firestore under `rate_limits/` are deleted lazily when the window expires on next access. No manual cleanup is normally needed. If you need to reset a specific user's rate limit (e.g. for a locked-out legitimate user), you can delete the relevant Firestore document manually:

1. Open the Firebase Console → Firestore Database → `rate_limits` collection.
2. Find the document with the ID matching `{action}__{sha256_prefix}`.
3. Delete it.

### 11.6 Firestore Quota Management

The Firestore Spark (free) plan has daily read/write limits. To stay within them:

- The Admin Panel's feedback stats use `@st.cache_data(ttl=300)` — cached for 5 minutes.
- Recent feedback uses `@st.cache_data(ttl=120)`.
- Prediction queries are limited to 500 records.
- Rate limit documents are lazily deleted.

If the application approaches Firestore limits, consider upgrading to the Blaze (pay-as-you-go) plan or adding more aggressive caching.

### 11.7 Updating Financial Data

Tax brackets, CoL indices, CTC rates, PF rates, loan rates, and investment return benchmarks are hardcoded in the respective utility modules (`tax_utils.py`, `col_utils.py`, etc.). To update them:

1. Open the relevant utility file in the repository.
2. Update the data tables.
3. Commit and push. Streamlit Cloud will redeploy automatically.

---

## 12. Rollback Procedures

### 12.1 Rollback the Application Code

Streamlit Cloud deploys from the latest commit on the connected branch. To roll back:

```bash
# Option 1: Revert the last commit
git revert HEAD
git push origin main

# Option 2: Reset to a specific commit (force push — use with caution)
git reset --hard <commit-hash>
git push --force origin main
```

Streamlit Cloud will redeploy from the new HEAD.

### 12.2 Rollback a Model Hub Bundle

Use the Model Hub Registry Manager admin interface:

1. In the Registry Manager, find the model family.
2. Click **Rollback** next to the version you want to restore.
3. The system will activate that version and deactivate all others in the family.

### 12.3 Rollback a Built-in Model Artefact

1. Re-upload the previous version of the artefact to HuggingFace (the HuggingFace repo maintains full version history).
2. Reboot the Streamlit app to clear the cache and force a fresh download.

### 12.4 Rollback Optional Features

Several features are designed with explicit rollback markers in source code (comments tagged `-- ROLLBACK:`). To disable a feature:

| Feature | Files to modify | What to remove |
|---|---|---|
| Email verification | `auth.py`, `email_verification.py`, `database.py` | Import + 3 call sites in `auth.py`; `save_pending_verification` + `get_pending_verification_db` in `database.py`; delete `email_verification.py` |
| Password policy | `auth.py`, `account_management.py`, `password_policy.py` | Import + call sites tagged `-- ROLLBACK: password_policy --`; delete `password_policy.py` |
| Rate limiter | `auth.py`, `account_management.py`, `rate_limiter.py` | Import + call sites tagged `-- ROLLBACK: rate_limiter --`; delete `rate_limiter.py` |
| Extended feedback | `feedback.py` | Remove `extended` parameter and `_collect_extended_data()` call; remove `EXTENDED DATA BLOCK` sections |
| Change password | `account_management.py`, `user_profile.py` | Remove `render_change_password_ui()` and its call |
| Delete account | `account_management.py`, `user_profile.py` | Remove `render_delete_account_ui()` and its call |

---

## 13. Troubleshooting

### 13.1 Application Fails to Start

**Symptom:** Streamlit Cloud shows a startup error or the app crashes immediately.

**Diagnosis:** Check the **Logs** in the Streamlit Cloud dashboard (Manage app → Logs).

**Common causes:**

| Error | Cause | Resolution |
|---|---|---|
| `KeyError: 'FIREBASE_API_KEY'` | Secret not configured | Add the missing secret in Streamlit Cloud settings |
| `ModuleNotFoundError: No module named 'spacy'` | `requirements.txt` not complete | Verify spacy is listed in `requirements.txt` |
| `OSError: [E050] Can't find model 'en_core_web_sm'` | spaCy model not downloaded | Add `spacy==x.x.x` and the model download to startup; or use the lite app |
| `RuntimeError: Firebase not configured` | `FIREBASE_API_KEY` is empty | Verify the key in Streamlit secrets |
| Memory limit exceeded | App too large for free tier | Switch to the lite app for the public deployment |

### 13.2 Authentication Not Working

**Symptom:** Login fails with a generic error, or registration succeeds but login is rejected.

**Common causes:**

| Issue | Resolution |
|---|---|
| Firebase API key wrong | Verify `FIREBASE_API_KEY` matches the web API key in Firebase Console → Project Settings |
| Email not verified | Ensure the verification email was clicked; use the resend option |
| Account does not exist | Register first; Firebase Authentication must have the account |
| Rate limited | Wait for the rate limit window (5 minutes for login, 10 for registration) to expire |
| Wrong password | Use Forgot Password to reset |

### 13.3 Firestore Errors

**Symptom:** Predictions are not saved, or the Profile tab shows no history.

**Common causes:**

| Issue | Resolution |
|---|---|
| Service account JSON missing or invalid | Re-check `FIREBASE_SERVICE_ACCOUNT` in secrets; ensure all fields are present |
| Private key has escaped newlines | Paste the raw JSON private key value; Streamlit Cloud secrets escape `\n` automatically |
| Firestore not enabled | Enable Firestore in the Firebase Console |
| Quota exceeded | Check Firebase Console → Usage; upgrade to Blaze plan if needed |

### 13.4 HuggingFace Errors

**Symptom:** Models fail to load; Model Hub shows "Could not load model registry".

**Common causes:**

| Issue | Resolution |
|---|---|
| `HF_TOKEN` missing or expired | Generate a new token in HuggingFace settings; update the secret |
| `HF_REPO_ID` wrong format | Must be `"owner/repo-name"`; check for typos |
| Repo is public, not private | The repo must be accessible with the provided token |
| Artefact file missing from repo | Verify the file exists in the HuggingFace repo using the web interface |
| Aliases not showing after push | The bundle cache must be cleared. Click **Clear cache** next to the model in the Registry Manager, then click **Load Model** again. `schema.json` and `aliases.json` are always fetched fresh (`force_download=True`) but the session-state bundle cache is only cleared on explicit reload. |
| Form still single-column after adding layout to schema | The bundle cache holds the old schema. Clear the cache and click **Load Model** again. |
| Result card still shows raw target name after adding result_label | Same cause — clear cache and reload. |

### 13.5 Currency Converter Shows No Data

**Symptom:** Currency tool toggle appears but shows an error about rate data.

**Cause:** The application could not reach `open.er-api.com`.

**Resolution:** This is transient and will resolve when the API is reachable. A fallback to a local rates file (`data/exchange_rates_fallback.json`) will be used if present. Add this file to the repository with a recent rates snapshot to ensure the tool always works:

```bash
curl https://open.er-api.com/v6/latest/USD > data/exchange_rates_fallback.json
```

### 13.6 Admin Panel Inaccessible

**Symptom:** The Admin Panel tab is not visible, or shows "Access denied".

**Cause:** The logged-in account's email does not match `ADMIN_EMAIL` (case-insensitive).

**Resolution:** Verify that `ADMIN_EMAIL` in secrets exactly matches the email used to log in. Differences in case, trailing spaces, or domain differences will prevent admin access.

### 13.7 PDF Generation Fails

**Symptom:** Clicking Prepare PDF Report shows an error.

**Cause:** Usually a ReportLab or matplotlib import issue, or a corrupt analytics data object.

**Resolution:** Check the Streamlit Cloud logs. Ensure `reportlab` and `matplotlib` are in `requirements.txt`. For model analytics PDFs, rebooting the app clears the cache and regenerates them.

---

*End of Deployment Guide*
