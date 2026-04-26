"""
Compact app knowledge used to ground the local SalaryScope assistant.
"""

from __future__ import annotations


APP_HELP_TEXT = """
SalaryScope is a machine-learning salary analysis app with two built-in models.

Main areas:
- Manual Prediction: single-profile salary estimate
- Resume Analysis: PDF resume extraction and salary prediction
- Batch Prediction: CSV/XLSX/JSON/SQL for built-in models
- Scenario Analysis: compare named what-if profiles
- Model Analytics: performance, diagnostics, feature importance
- Data Insights: dataset visual exploration
- Model Hub: load uploaded model bundles
- HR Tools: hiring budget, benchmarking, candidate comparison, offer checker, team audit

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
""".strip()


MODE_HELP = {
    "App Help": (
        "Answer questions about SalaryScope workflows, tabs, file formats, and limitations. "
        "Do not invent features that are not present."
    ),
    "Prediction Companion": (
        "Explain the current prediction in plain English without contradicting the estimate."
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
