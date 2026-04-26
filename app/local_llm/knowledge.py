"""
Compact app knowledge used to ground the local SalaryScope assistant.
"""

from __future__ import annotations


APP_HELP_TEXT = """
SalaryScope is a machine-learning salary analysis app with two built-in models.

Main areas:
- Manual Prediction: single-profile salary estimate
- Resume Analysis: PDF resume extraction and salary prediction
- AI Assistant: chat-style help, explanation, drafting, and export support
- Batch Prediction: CSV/XLSX/JSON/SQL for built-in models
- Scenario Analysis: compare named what-if profiles
- Model Analytics: performance, diagnostics, feature importance
- Data Insights: dataset visual exploration
- Model Hub: load uploaded model bundles
- Profile: logged-in users can view prediction history and exports
- Admin Panel: diagnostics and model-management tools for authorized users
- HR Tools: hiring budget, benchmarking, candidate comparison, offer checker, team audit
- About: project overview, usage guidance, and limitations

Additional helper areas:
- Financial planning tools below prediction results: currency conversion, tax estimation,
  cost-of-living adjustment, CTC breakdown, take-home estimation, savings, loan affordability,
  budget planning, investment growth, emergency fund planning, and lifestyle split
- Export support for prediction reports, analytics reports, scenario results, salary cards,
  and AI Assistant conversation or reply downloads

Model framing:
- Model 1 is a general salary model based on a public Kaggle-style dataset
- Model 2 is a data-science salary model based on a public Kaggle-style dataset
- Model Hub can expose additional uploaded bundles through schema-driven prediction tabs

Important constraints:
- Salary predictions come from the trained ML models, not from the local assistant
- The assistant must not contradict or replace the app's prediction output
- The datasets are academic Kaggle-style datasets, so percentile / market-truth claims are not appropriate
- Future salary growth, promotion forecasting, or strong causal career guidance are not supported
- Resume extraction works best on ATS-friendly text PDFs
- Currency, tax, cost-of-living, take-home, savings, loan, and FIRE tools are interpretive helpers

Built-in exports already exist for:
- manual prediction PDF
- resume prediction PDF
- batch prediction PDF
- scenario analysis PDF
- model analytics PDF

The local assistant is best used for:
- app help
- plain-English explanation of already produced outputs
- negotiation drafts grounded in the displayed estimate
- resume summary drafting from extracted resume content
- short report-ready narrative based on structured app results
- general negotiation tips, job-title clarification, and cautious career suggestions when clearly labeled as guidance rather than prediction
""".strip()


APP_OVERVIEW_TEXT = """
SalaryScope is a machine-learning salary prediction and analysis application. It combines manual
prediction, resume-based prediction, batch prediction, scenario analysis, model analytics,
data insights, HR tools, and a Model Hub for additional uploaded model bundles. The full app
also includes financial-planning helpers, downloadable reports, user history for logged-in users,
and an AI Assistant for explanation and drafting.
""".strip()


APP_DEVELOPER_TEXT = """
SalaryScope was developed by Yash Shah as a Final Year B.Tech academic project in Computer Engineering.
It was built to combine machine-learning salary prediction with an interactive Streamlit application so users
can explore salary estimates, resume-based prediction, analytics, scenario comparison, and related insights in one place.
""".strip()


APP_LIMITATIONS_TEXT = """
Key limitations:
- Predictions are based on patterns learned from public training datasets and may not fully match current real-world salary conditions.
- The app is designed for academic demonstration and interpretation, not as a source of live market truth.
- Resume analysis works best on ATS-friendly text PDFs and may be less reliable on highly styled or image-heavy documents.
- Predictions do not incorporate live market demand, employer-specific compensation rules, or real-time economic changes.
- Confidence intervals and related interpretive ranges are approximate, not guarantees.
- Financial helper outputs such as tax, cost-of-living, savings, and loan estimates are planning aids, not exact financial advice.
- Model Hub results are only as reliable as the uploaded bundle's training quality.
- The AI Assistant is a support layer for explanation and drafting. It can make mistakes and should be reviewed before use.
""".strip()


MODE_HELP = {
    "App Help": (
        "Answer questions about SalaryScope workflows, tabs, file formats, and limitations. "
        "Do not invent features that are not present."
    ),
    "Prediction Companion": (
        "Explain the current prediction in plain English without contradicting the estimate. "
        "You can also answer adjacent questions such as negotiation tips, role framing, or careful next-step suggestions."
    ),
    "Negotiation Assistant": (
        "Draft negotiation messages that reference the displayed prediction as a discussion aid."
    ),
    "Resume Assistant": (
        "Summarize resume content and extracted signals in recruiter-friendly language."
    ),
    "Report Writer": (
        "Convert structured SalaryScope outputs into concise report-ready narrative text."
    ),
}


__all__ = [
    "APP_DEVELOPER_TEXT",
    "APP_HELP_TEXT",
    "APP_LIMITATIONS_TEXT",
    "APP_OVERVIEW_TEXT",
    "MODE_HELP",
]
