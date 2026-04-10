# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## Project Title: SalaryScope

---

## 1. Introduction

### 1.1 Purpose

The purpose of this document is to define the software requirements for the **SalaryScope** application. It provides a detailed description of system functionality, constraints, and overall architecture.

SalaryScope is a machine learning-based web application designed to predict salaries based on user-provided inputs or resume data. It aims to assist students, job seekers, and professionals in understanding expected salary ranges.

---

### 1.2 Scope

SalaryScope is a web-based system built using Python and Streamlit that:

- Predicts salaries using machine learning models
- Supports manual input and resume-based prediction
- Provides insights such as salary levels, career stages, and recommendations
- Stores user prediction history
- Allows batch processing and scenario comparison

The system integrates:

- Machine Learning models
- Natural Language Processing (NLP)
- Cloud-based authentication and storage (Firebase)

---

### 1.3 Definitions and Acronyms

| Term     | Meaning                                   |
|----------|-------------------------------------------|
| ML       | Machine Learning                          |
| NLP      | Natural Language Processing               |
| API      | Application Programming Interface         |
| SRS      | Software Requirements Specification       |
| UI       | User Interface                            |
| Firebase | Cloud backend service for auth & database |

---

### 1.4 Overview

This document includes:

- System description
- Functional and non-functional requirements
- System architecture
- Data handling and processing
- External integrations

---

## 2. Overall Description

### 2.1 Product Perspective

SalaryScope is a standalone web application that combines:

- **Frontend:** Streamlit-based UI
- **Backend:** Python-based ML and NLP pipelines
- **Database:** Firebase Firestore
- **Authentication:** Firebase Authentication

---

### 2.2 Product Functions

The system provides:

1. Salary Prediction (Manual Input)
2. Resume-based Prediction (PDF upload + NLP)
3. Batch Prediction (multiple records)
4. Scenario Analysis (comparison tool)
5. Model Analytics and Insights
6. User Authentication and Profile Management
7. Prediction History Storage and Export
8. Prediction Feedback Collection (structured, available to all users)

---

### 2.3 User Classes

| User Type        | Description                               |
|------------------|-------------------------------------------|
| Guest User       | Can use prediction features without login |
| Registered User  | Can save and view prediction history      |
| Admin (implicit) | Firebase-managed backend                  |

---

### 2.4 Operating Environment

| Component   | Details              |
|-------------|----------------------|
| Platform    | Web browser          |
| Backend     | Python 3.13          |
| Framework   | Streamlit            |
| Database    | Firebase Firestore   |
| NLP         | spaCy                |
| ML Libraries| Scikit-learn, XGBoost|

---

### 2.5 Constraints

- Requires internet for Firebase services
- Model accuracy depends on dataset quality
- Resume parsing depends on text extraction accuracy
- Python version compatibility (recommended 3.13)

---

### 2.6 Assumptions

- Users provide valid input data
- Resume is in readable PDF format
- Firebase credentials are correctly configured

---

## 3. System Architecture

### 3.1 Architecture Overview

The system follows a modular architecture:

- Presentation Layer (UI)
- Processing Layer (ML + NLP)
- Data Layer (Firestore + datasets)

---

### 3.2 High-Level Architecture

```
User → Streamlit UI → Processing Layer → ML/NLP Models → Results
                                                       ↓
                                              Firebase (Storage)
```

---

### 3.3 Modules

#### 3.3.1 User Interface Module

- Built using Streamlit
- Contains tabs for all features

#### 3.3.2 Authentication Module

- Firebase Authentication
- Email/password login
- Session handling via Streamlit state

#### 3.3.3 Prediction Module

- Random Forest (general salary)
- XGBoost (data science roles)

#### 3.3.4 Resume NLP Module

- PDF extraction using pdfplumber
- Feature extraction using regex and spaCy
- Skill detection using PhraseMatcher

#### 3.3.5 Database Module

- Firestore for user data and prediction history

#### 3.3.6 Analytics Module

- Model performance visualization
- Charts using Plotly and Matplotlib

#### 3.3.7 Feedback Module

- Implemented in `feedback.py`
- Collapsible UI component in the Manual Prediction tab
- Collects structured feedback after each prediction result
- Saves to Firestore `feedback/` collection, separate from predictions
- Available to both logged-in and anonymous users

#### 3.3.8 Admin Module

- Accessible only to authorized users
- Provides system diagnostics and feedback analytics
- Allows viewing recent feedback and system status

---

## 4. Functional Requirements

### 4.1 User Authentication

- Users shall be able to register using email and password
- Users shall be able to log in and log out
- Sessions shall expire after 24 hours

---

### 4.2 Manual Salary Prediction

Users shall input:

- Education
- Experience
- Job title
- Country

System shall predict salary and display:

- Salary estimate
- Estimated confidence range
- Career stage
- Recommendations

---

### 4.3 Resume Analysis

Users shall upload a PDF resume. System shall extract:

- Experience
- Education
- Skills
- Job title
- Country

System shall generate:

- Salary prediction
- Resume score
- Insights

---

### 4.4 Batch Prediction

- Users shall upload CSV/XLSX/JSON files
- System shall process multiple records
- System shall provide downloadable results

---

### 4.5 Scenario Analysis

- Users shall create multiple scenarios
- System shall compare predictions
- System shall generate visual comparisons

---

### 4.6 User Profile

System shall store prediction history. Users shall view:

- Total predictions
- Average salary
- History chart

Users shall export data.

---

### 4.7 Report Generation

- System shall generate PDF reports
- Reports shall include predictions and insights

---

### 4.8 Prediction Feedback

- After a manual prediction result is displayed, the system shall present a collapsible feedback form
- Users shall be able to rate prediction accuracy: Yes / Somewhat / No
- Users shall be able to indicate direction of error: Too High / About Right / Too Low
- Users shall be able to provide a star rating from 1 to 5
- Users shall optionally provide their actual or expected salary in USD
- The system shall store feedback in Firestore under a dedicated `feedback/` collection
- Feedback shall include the prediction inputs and predicted salary alongside the user ratings
- Feedback submission shall be available to both logged-in and anonymous users
- The system shall allow only one feedback submission per prediction result per session

---

## 5. Non-Functional Requirements

### 5.1 Performance

- System shall respond within a few seconds for predictions
- Batch processing may take longer depending on size

---

### 5.2 Usability

- Interface shall be simple and intuitive
- Tabs shall clearly separate features

---

### 5.3 Security

- Passwords handled by Firebase
- No sensitive data stored locally
- Session expiry implemented

---

### 5.4 Reliability

- System shall handle invalid inputs gracefully
- Errors shall be displayed to users

---

### 5.5 Scalability

- Firestore supports scalable storage
- Modular architecture allows extension

---

## 6. External Interface Requirements

### 6.1 User Interface

- Web-based UI using Streamlit
- Interactive charts and forms

---

### 6.2 Hardware Interface

- No special hardware required

---

### 6.3 Software Interface

| Component     | Purpose             |
|---------------|---------------------|
| Firebase Auth | User authentication |
| Firestore     | Data storage        |
| spaCy         | NLP processing      |
| pdfplumber    | PDF parsing         |
| Scikit-learn  | ML models           |
| XGBoost       | Advanced prediction |

---

## 7. Data Requirements

### 7.1 Input Data

- Manual inputs
- Resume PDF
- Batch files

---

### 7.2 Output Data

- Predicted salary
- Resume score
- Insights and recommendations

---

### 7.3 Storage

Firestore collections:

```
users/
predictions/{username}/records
feedback/{auto-id}
```

Feedback documents store: username, model_used, input_data, predicted_salary, accuracy_rating, direction, star_rating, actual_salary, created_at, extended_data (optional).

---

## 8. System Limitations

- Predictions are estimates, not exact values
- Dataset may not cover all roles or regions
- Resume parsing depends on formatting
- Market trends are not dynamically updated
- Feedback submitted anonymously cannot be linked to a specific user session and carries no personal identifier
- Model predictions do not include real-time market updates or dynamic retraining