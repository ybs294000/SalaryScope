# PROJECT REPORT

## PROJECT TITLE: SalaryScope

---

## ABSTRACT

SalaryScope is an intelligent web-based application designed to predict salary outcomes using machine learning and data analytics techniques. The system leverages structured datasets and natural language processing to estimate salaries based on multiple factors such as education level, work experience, job role, geographic location, and employment conditions.

The application integrates multiple machine learning models, including Random Forest and XGBoost, to provide accurate and scalable salary predictions across general and data science domains. In addition to manual input-based predictions, SalaryScope supports resume-based analysis, where user-uploaded PDF resumes are processed using NLP techniques to extract relevant features such as skills, experience, and job roles.

The system further enhances user experience by providing advanced features such as batch prediction, scenario analysis, prediction confidence estimation, and personalized career insights. A cloud-based authentication and storage system using Firebase enables secure user management and persistent prediction history tracking.

SalaryScope serves as a decision-support tool for job seekers, students, and professionals, helping them understand salary expectations, improve negotiation strategies, and make informed career decisions. The system also includes a structured feedback mechanism that allows users to rate prediction accuracy and submit optional actual salary data, enabling continuous quality assessment.

---

## KEYWORDS

Machine Learning, Salary Prediction, Data Analytics, Natural Language Processing, Streamlit, Firebase, XGBoost, Random Forest

---

## 1. INTRODUCTION

### 1.1 Background

In today's competitive job market, understanding expected salary ranges is crucial for both job seekers and employers. However, salary determination depends on multiple complex factors such as education, experience, job role, and geographic location.

Traditional approaches rely on static surveys or limited datasets, which do not provide personalized insights. With advancements in machine learning and data analytics, it is now possible to build predictive systems that provide dynamic and data-driven salary estimations.

---

### 1.2 Problem Statement

Many individuals lack access to reliable tools that can estimate salary expectations based on their profile or resume. Existing solutions often:

- Provide generic salary ranges
- Do not consider multiple influencing factors simultaneously
- Lack personalization
- Do not support resume-based analysis

---

### 1.3 Objectives

The main objectives of SalaryScope are:

- To develop a machine learning-based salary prediction system
- To support both manual input and resume-based prediction
- To provide insights such as career stage and salary levels
- To enable batch processing and scenario comparison
- To store and visualize user prediction history
- To collect structured user feedback on prediction accuracy for quality assessment
- To assist users in making informed career decisions

---

## 2. LITERATURE REVIEW

Salary prediction systems have been explored using regression models and data mining techniques. Traditional models include linear regression and decision trees, while modern approaches use ensemble learning methods such as Random Forest and gradient boosting algorithms.

Recent advancements also incorporate Natural Language Processing (NLP) to extract structured information from resumes and unstructured text data. Cloud-based systems like Firebase are commonly used for authentication and scalable data storage.

SalaryScope builds upon these concepts by combining:

- Ensemble machine learning models
- NLP-based resume parsing
- Interactive web-based visualization

---

## 3. SYSTEM OVERVIEW

### 3.1 System Description

SalaryScope is a web-based application that integrates machine learning, NLP, and cloud services to provide salary predictions and insights.

The system allows users to:

- Enter profile details manually
- Upload resumes for automated analysis
- Compare multiple scenarios
- Analyze model performance
- Track prediction history

---

### 3.2 System Workflow

```
User Input → Feature Processing → Model Prediction → Insights Generation → Output Display → Storage
```

---

### 3.3 Modules Overview

1. User Interface Module
2. Authentication Module
3. Prediction Module
4. Resume NLP Module
5. Database Module
6. Analytics Module
7. Feedback Module

---

## 4. METHODOLOGY

### 4.1 Data Collection

Two datasets are used:

1. **General Salary Dataset (Salary.csv)** — Contains demographic and job-related features
2. **Data Science Salary Dataset (ds_salaries.csv)** — Focused on data science and ML roles

---

### 4.2 Data Preprocessing

- Handling missing values
- Encoding categorical variables
- Feature scaling (where required)
- Feature engineering (job title, experience interactions)

---

### 4.3 Model Development

#### Model 1 — Random Forest (General Salary)

- **Algorithm:** Random Forest Regressor
- **Hyperparameter tuning:** GridSearchCV
- **Additional models:**
  - HistGradientBoostingClassifier (salary level)
  - KMeans (career stage clustering)
  - Apriori (association rules)

---

#### Model 2 — XGBoost (Data Science Salary)

- **Algorithm:** XGBoost Regressor
- **Target transformation:** log1p(salary)
- **Feature engineering:**
  - Job title domain extraction
  - Experience interaction features

---

## 5. RESUME ANALYSIS SYSTEM

### 5.1 Overview

The resume analysis module extracts structured information from PDF resumes using NLP techniques.

---

### 5.2 Processing Pipeline

```
PDF Resume → Text Extraction → Cleaning → Feature Extraction → Prediction
```

---

### 5.3 Feature Extraction

The system extracts:

- Years of experience (regex-based detection)
- Education level (pattern matching)
- Skills (spaCy PhraseMatcher)
- Job title (alias mapping + NLP)
- Country (NER + alias matching)
- Seniority (derived feature)

---

### 5.4 Resume Scoring

The resume is scored out of 100 based on:

| Component  | Weight |
|------------|--------|
| Experience | 50     |
| Education  | 35     |
| Skills     | 30     |

**Levels:**

- Basic
- Moderate
- Strong

---

### 5.5 App 2 Resume System

- Experience mapped to categories (EN, MI, SE, EX)
- DS/ML skills weighted higher
- Job relevance scoring included

---

## 6. SYSTEM ARCHITECTURE

### 6.1 Architecture Overview

SalaryScope follows a modular and layered architecture consisting of:

- Presentation Layer (User Interface)
- Processing Layer (ML + NLP)
- Data Layer (Firestore + datasets)

---

### 6.2 Architectural Flow

```
User → Streamlit UI → Backend Processing → ML/NLP Models → Results
                                                         ↓
                                                Firebase Storage
```

---

### 6.3 Module Description

#### 1. Presentation Layer (UI)

- Built using Streamlit
- Provides tab-based navigation:
  - Manual Prediction
  - Resume Analysis
  - Batch Prediction
  - Scenario Analysis
  - Model Analytics
  - Data Insights
  - Profile
  - About

---

#### 2. Authentication Module

- Uses Firebase Authentication
- Supports:
  - Email/password login
  - Registration
- Session handled via Streamlit session state
- Session expiry: 24 hours

---

#### 3. Prediction Module

Handles salary estimation using:

- Random Forest Regressor
- XGBoost Regressor

**Outputs:**

- Salary estimate
- Salary level
- Career stage
- Insights and recommendations

---

#### 4. Resume NLP Module

- Extracts structured data from resumes
- Uses:
  - pdfplumber for text extraction
  - spaCy for NLP
  - Regex for pattern detection

---

#### 5. Database Module

Firebase Firestore used for:

- User storage
- Prediction history

**Structure:**

```
users/{username}
predictions/{username}/records/{id}
```

---

#### 6. Analytics Module

- Visualizations using Plotly and Matplotlib
- Includes:
  - Feature importance
  - Residual analysis
  - Clustering results
  - Association rules

---

#### 7. Feedback Module

- Implemented in `feedback.py`
- Provides a collapsible form in the Manual Prediction tab after each result
- Collects structured feedback: accuracy rating (Yes / Somewhat / No), direction (Too High / About Right / Too Low), star rating (1–5), and optional actual salary
- Stores prediction inputs alongside feedback in Firestore under a dedicated `feedback/` collection
- Available to both logged-in and anonymous users
- Isolated from the prediction and user modules — no shared state or collections

---

## 7. DATABASE DESIGN

### 7.1 Firestore Collections

#### Users Collection

```
users/
   └── username
        ├── email
        ├── display_name
        └── created_at
```

---

#### Predictions Collection

```
predictions/
   └── username
        └── records/
             ├── model_used
             ├── input_data
             ├── predicted_salary
             └── created_at
```

---

#### Feedback Collection

```
feedback/
   └── {auto-id}
        ├── username
        ├── model_used
        ├── input_data
        ├── predicted_salary
        ├── accuracy_rating
        ├── direction
        ├── star_rating
        ├── actual_salary
        └── created_at
```

---

### 7.2 Data Flow

```
User → Input → Prediction → Save to Firestore → Retrieve → Display in Profile
```

---

## 8. FEATURES AND FUNCTIONALITY

### 8.1 Manual Prediction

- User enters input manually
- System predicts salary
- Displays:
  - Salary value
  - Career stage
  - Recommendations
- Collapsible feedback form available after each result for users to rate prediction accuracy

---

### 8.7 Prediction Feedback

- Available in the Manual Prediction tab for both models
- Structured feedback fields: accuracy rating, direction of error, star rating (1–5), optional actual salary
- Prediction inputs and predicted salary stored alongside feedback for full traceability
- Accessible to logged-in and anonymous users
- Stored in Firestore under `feedback/` — separate from prediction history

---

### 8.2 Resume Analysis

- Upload PDF resume
- Automatic feature extraction
- Editable extracted fields
- Salary prediction with insights

---

### 8.3 Batch Prediction

- Upload dataset file
- Predict multiple entries
- Export results

---

### 8.4 Scenario Analysis

- Compare up to 5 scenarios
- Visual comparison charts
- Sensitivity analysis

---

### 8.5 Model Analytics

- Performance metrics
- Feature importance
- Error analysis

---

### 8.6 User Profile

- Prediction history
- Summary dashboard
- Export functionality

---

## 9. RESULTS AND OUTPUT

### 9.1 Output Types

The system generates:

- Predicted salary (numerical)
- Salary level classification
- Career stage classification
- Resume score
- Insights and recommendations

---

### 9.2 Visualization Outputs

- Scatter plots (prediction history)
- Bar charts (scenario comparison)
- Feature importance graphs
- Residual plots

---

### 9.3 Export Outputs

- CSV
- JSON
- XLSX
- PDF reports

---

## 10. ADVANTAGES

- Supports both manual and resume-based prediction
- Uses multiple ML models for better accuracy
- Provides insights beyond just salary
- Interactive and user-friendly interface
- Cloud-based storage for scalability
- Scenario comparison feature
- Structured feedback collection from all users enables ongoing prediction quality assessment

---

## 11. LIMITATIONS

- Model accuracy depends on dataset quality
- Resume parsing may fail for complex formats
- Does not include real-time market trends
- Limited dataset coverage for some roles

---

## 12. FUTURE SCOPE

- Integration with real-time job market APIs
- Improved NLP for better resume understanding
- Deep learning-based salary prediction
- Mobile application version
- More datasets for wider coverage
- Personalized career path recommendations
- Use collected feedback data to retrain or recalibrate models over time

---

## 13. CONCLUSION

SalaryScope demonstrates the effective use of machine learning and NLP techniques to build an intelligent salary prediction system. By combining structured data analysis with resume-based feature extraction, the system provides a comprehensive and user-friendly solution for salary estimation.

The integration of advanced features such as scenario analysis, batch processing, cloud-based storage, and structured prediction feedback enhances the practicality and scalability of the application. The feedback system provides a lightweight, non-intrusive mechanism for collecting user-reported accuracy data, laying the groundwork for future model improvement. Overall, SalaryScope serves as a valuable tool for individuals seeking data-driven insights into salary expectations and career planning.
