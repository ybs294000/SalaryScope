# SOFTWARE DESIGN DOCUMENT (SDD)

## Project Title: SalaryScope

---

## 1. INTRODUCTION

### 1.1 Purpose

This document describes the internal design and architecture of the SalaryScope system. It explains how the system is structured, how components interact, and how data flows through the application.

---

### 1.2 Scope

SalaryScope is a machine learning-based web application designed to predict salaries using structured inputs and resume data. The system integrates machine learning models, natural language processing, and cloud-based storage.

---

## 2. SYSTEM ARCHITECTURE

### 2.1 Architecture Overview

The system follows a modular layered architecture:

- Presentation Layer (UI)
- Application Layer (Logic)
- Processing Layer (ML + NLP)
- Data Layer (Firestore + datasets)

---

### 2.2 Architecture Flow

```
User → Streamlit UI → Application Logic → ML/NLP Models → Output
                                                        ↓
                                              Firestore Database
```

---

## 3. MODULE DESIGN

### 3.1 User Interface Module

- Built using Streamlit
- Provides tab-based navigation
- Handles user inputs and displays results

Tabs include:

- Manual Prediction
- Resume Analysis
- Batch Prediction
- Scenario Analysis
- Model Analytics
- Profile
- About

The Manual Prediction tab includes a collapsible feedback form rendered after each prediction result.

---

### 3.2 Authentication Module

- Uses Firebase Authentication (REST API)
- Handles:
  - User registration
  - Login
  - Logout
- Session management using Streamlit session state
- Session expiry after 24 hours

---

### 3.3 Prediction Module

#### Model 1

- Random Forest Regressor
- HistGradientBoostingClassifier
- KMeans Clustering
- Apriori Algorithm

#### Model 2

- XGBoost Regressor

**Responsibilities:**

- Process input features
- Generate salary predictions
- Provide additional insights

---

### 3.4 Resume NLP Module

This module extracts structured features from resumes.

#### Pipeline

```
PDF → Text Extraction → Cleaning → Feature Extraction → Structured Data
```

#### Components

| Tool            | Purpose                  |
|-----------------|--------------------------|
| pdfplumber      | Extract text from PDF    |
| Regex           | Extract experience       |
| spaCy           | NLP processing           |
| PhraseMatcher   | Skill detection          |
| Alias mapping   | Job title detection      |
| NER             | Country extraction       |

---

### 3.5 Database Module

- Uses Firebase Firestore

#### Collections

```
users/{username}
predictions/{username}/records/{id}
feedback/{auto-id}
```

**Responsibilities:**

- Store user data
- Store prediction history
- Retrieve data for profile
- Store structured prediction feedback from all users

---

### 3.7 Feedback Module

- Implemented in `feedback.py`
- Independent of the predictions and user modules
- Provides a collapsible UI component rendered in the Manual Prediction tab after a result is generated

**Responsibilities:**

- Collect structured user feedback on prediction accuracy
- Save feedback to Firestore under a dedicated `feedback/` collection
- Accept submissions from both logged-in and anonymous users

**Feedback Fields Collected:**

| Field           | Type    | Description                              |
|-----------------|---------|------------------------------------------|
| username        | String  | Email if logged in, "anonymous" otherwise |
| model_used      | String  | Model that produced the prediction       |
| input_data      | JSON    | All input fields used for the prediction |
| predicted_salary| Float   | The salary value predicted               |
| accuracy_rating | String  | Yes / Somewhat / No                      |
| direction       | String  | Too High / About Right / Too Low         |
| star_rating     | Integer | 1 to 5                                   |
| actual_salary   | Float   | Optional; None if not provided           |
| created_at      | String  | UTC timestamp of submission              |

**UI Behaviour:**

- Appears as a collapsible expander below the prediction result
- Submission is one-time per prediction within a session (form replaced by confirmation message after submit)
- Session key is scoped to model name and predicted salary value to reset automatically on new predictions

---

### 3.6 Analytics Module

- Generates visualizations
- Uses Plotly and Matplotlib

Includes:

- Feature importance
- Residual analysis
- Clustering visualization
- Prediction charts

---

## 4. DATA FLOW DESIGN

### 4.1 Manual Prediction Flow

```
User Input → Feature Encoding → Model Prediction → Output Display
```

---

### 4.2 Resume Prediction Flow

```
Upload Resume → Extract Text → NLP Processing → Feature Extraction → Model Prediction → Output
```

---

### 4.3 Data Storage Flow

```
Prediction Result → Save to Firestore → Retrieve → Display in Profile
```

---

### 4.4 Feedback Flow

```
Prediction Result Displayed → User Opens Feedback Expander → Fills Fields → Submit → Save to Firestore feedback/
```

---

## 5. DATABASE DESIGN

### 5.1 Users Collection

| Field        | Description         |
|--------------|---------------------|
| username     | User identifier     |
| email        | User email address  |
| display_name | Display name        |
| created_at   | Account creation time |

---

### 5.2 Predictions Collection

| Field            | Description              |
|------------------|--------------------------|
| model_used       | ML model used            |
| input_data       | Input features provided  |
| predicted_salary | Salary prediction output |
| created_at       | Prediction timestamp     |

---

### 5.3 Feedback Collection

| Field            | Description                                      |
|------------------|--------------------------------------------------|
| username         | Email if logged in, "anonymous" if not           |
| model_used       | ML model that produced the prediction            |
| input_data       | JSON of all input fields used for the prediction |
| predicted_salary | Salary value that was predicted                  |
| accuracy_rating  | User rating: Yes / Somewhat / No                 |
| direction        | Too High / About Right / Too Low                 |
| star_rating      | Integer rating from 1 to 5                       |
| actual_salary    | User-provided salary in USD; null if skipped     |
| created_at       | UTC timestamp of feedback submission             |

---

## 6. MACHINE LEARNING DESIGN

### 6.1 Model 1 Design

**Input Features:**

- Age
- Experience
- Education
- Job Title
- Country

**Output:**

- Salary
- Salary Level
- Career Stage

---

### 6.2 Model 2 Design

**Input Features:**

- Experience Level
- Job Title
- Company Size
- Location

**Output:**

- Salary (log-transformed)

---

## 7. NLP SYSTEM DESIGN

### 7.1 Feature Extraction

| Feature    | Method              |
|------------|---------------------|
| Experience | Regex               |
| Education  | Pattern matching    |
| Skills     | spaCy PhraseMatcher |
| Job Title  | Alias mapping       |
| Country    | NER + alias         |

---

### 7.2 Resume Scoring

**Score components:**

- Experience
- Education
- Skills

**Output:**

- Total Score (0–100)
- Profile Level (Basic / Moderate / Strong)

---

## 8. SEQUENCE DESIGN

### 8.1 Login Flow

```
User → Enter Credentials → Firebase API → Validate → Session Created
```

---

### 8.2 Prediction Flow

```
User Input → Processing → Model → Result → Display → Save
```

---

## 9. ERROR HANDLING DESIGN

- Input validation checks
- Firebase error handling
- Graceful handling of invalid files
- Default fallbacks for NLP extraction

---

## 10. SECURITY DESIGN

- Authentication via Firebase
- No password storage in app
- Session expiration
- Secure API usage

---

## 11. SCALABILITY DESIGN

- Firestore supports scalable storage
- Modular architecture allows feature expansion
- Models can be replaced or upgraded independently
- Feedback data stored in a separate Firestore collection can be queried independently for future model improvement workflows

---

## 12. CONCLUSION

The design of SalaryScope ensures modularity, scalability, and maintainability. The integration of machine learning, NLP, and cloud services enables the system to provide intelligent salary predictions and insights efficiently. The feedback module adds a lightweight, isolated data collection layer that enables continuous quality assessment without coupling to the core prediction or user systems.
