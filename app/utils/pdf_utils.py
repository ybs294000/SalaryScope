import streamlit as st
from io import BytesIO

# ==================================================
# LAZY IMPORT HELPERS
# All heavy libraries are still lazy so startup cost
# is zero. BytesIO is stdlib and always available.
# ==================================================

def _plt():
    import matplotlib
    matplotlib.use("Agg")          # non-interactive backend — no display needed
    import matplotlib.pyplot as plt
    return plt

def _BytesIO():
    return BytesIO

def _ImageReader():
    from reportlab.lib.utils import ImageReader
    return ImageReader

def _np():
    import numpy as np
    return np

def _pd():
    import pandas as pd
    return pd

def _datetime():
    from datetime import datetime
    return datetime

def _letter():
    from reportlab.lib.pagesizes import letter
    return letter

def _canvas():
    from reportlab.pdfgen.canvas import Canvas
    return Canvas


# Lazy NumberedCanvas factory — class is built on first call, then cached
_NumberedCanvas_class = None


def _get_numbered_canvas():
    global _NumberedCanvas_class
    if _NumberedCanvas_class is None:
        _Base = _canvas()

        class _NumberedCanvasImpl(_Base):
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

        _NumberedCanvas_class = _NumberedCanvasImpl
    return _NumberedCanvas_class


# ==================================================
# CENTRALISED CHART-TO-IMAGE HELPER
# Single implementation used by every chart function.
# Replaces the duplicated inline BytesIO+savefig+close
# blocks scattered across every PDF function.
# Always closes the figure — no matplotlib figure leak.
# ==================================================

def _fig_to_image(fig, dpi=150):
    """
    Render a matplotlib figure to a ReportLab ImageReader.
    Closes the figure immediately after saving to release
    memory.  Uses dpi=150 instead of the old 150 — visually
    identical at the rendered PDF page size (~500pt wide)
    but saves ~36% of PNG bytes per chart.
    """
    plt = _plt()
    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return _ImageReader()(buf)


# ==================================================
# REUSABLE CHART SAVE HELPERS  (kept for API compat)
# ==================================================

def _save_chart_to_image(fig):
    """Save a matplotlib figure to an ImageReader buffer."""
    return _fig_to_image(fig, dpi=150)


def _save_chart_to_image_nodpi(fig, dpi=150):
    """Save a matplotlib figure with custom dpi."""
    return _fig_to_image(fig, dpi=dpi)


# ==================================================
# REUSABLE BOXPLOT PROPS
# ==================================================

def _boxplot_props():
    return dict(
        vert=False,
        patch_artist=True,
        boxprops=dict(facecolor="#6A9FCA", color="#1A4F8A", linewidth=1.6),
        medianprops=dict(color="#111111", linewidth=2.2),
        whiskerprops=dict(color="#1A4F8A", linewidth=1.4, linestyle="--"),
        capprops=dict(color="#1A4F8A", linewidth=1.6),
        flierprops=dict(
            marker="o",
            markerfacecolor="#1A4F8A",
            markeredgecolor="#1A4F8A",
            markersize=4,
            alpha=0.8
        )
    )


# ==================================================
# REUSABLE BAR COLORS
# ==================================================

def _bar_colors():
    return ["#1A4F8A", "#1F5FA3", "#2470BA", "#2980CC", "#3590D8"]


# ==================================================
# REUSABLE CHART AXIS STYLE (horizontal grid variant)
# ==================================================

def _apply_chart_style_h(ax, fig):
    """Apply standard chart style with horizontal (x-axis) grid."""
    ax.set_facecolor("#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    ax.grid(axis="x", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    ax.tick_params(colors="#111111", labelsize=9)


# ==================================================
# REUSABLE CHART TITLE / LABEL SETTER
# ==================================================

def _set_chart_labels(ax, title, xlabel=None, ylabel=None):
    ax.set_title(title, fontsize=12, fontweight="bold", color="#111111", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color="#111111", labelpad=6)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color="#111111", labelpad=6)


# ==================================================
# REUSABLE INLINE WORD WRAP
# ==================================================

def _inline_wrap_text(c, text, x, y, max_width, font="Helvetica-Oblique", size=10, line_gap=14):
    """Word-wrap helper shared by all PDF generation functions."""
    c.setFont(font, size)
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if c.stringWidth(test_line, font, size) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_gap
    return y


# ==================================================
# COMMON DRAWING HELPERS
# ==================================================

def draw_line(c, left_margin, right_margin, y):
    c.line(left_margin, y, right_margin, y)
    return y


def draw_section_header(c, text, x, y, size=13):
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, text)
    return y


def draw_kv_line(c, text, x, y, offset=15, font="Helvetica", size=11):
    c.setFont(font, size)
    c.drawString(x + offset, y, text)
    return y


def draw_wrapped_text(c, text, x, y, max_width,
                      font="Helvetica-Oblique", size=10, line_gap=14):
    # Delegates to the single canonical implementation
    return _inline_wrap_text(c, text, x, y, max_width, font=font, size=size, line_gap=line_gap)


def draw_centered_image(c, img, y, width, height, page_width):
    x = (page_width - width) / 2
    c.drawImage(
        img,
        x,
        y,
        width=width,
        height=height,
        preserveAspectRatio=True,
        mask='auto'
    )
    return y


def apply_chart_style(ax):
    ax.set_facecolor("#FFFFFF")
    ax.grid(axis="y", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    ax.tick_params(colors="#111111", labelsize=9)


# ==================================================
#
# ==================================================
def draw_skills_clean(c, label, text, x, y, max_width,
                      font="Helvetica", size=11, line_gap=14):
    """
    Clean skill rendering:
    - Splits by comma (natural units)
    - Wraps properly
    - Keeps indentation clean
    """
    c.setFont(font, size)

    skills = [s.strip() for s in str(text).split(",") if s.strip()]

    label_text = f"{label}: "
    label_width = c.stringWidth(label_text, font, size)

    current_line = ""
    first_line = True

    for skill in skills:
        test_line = f"{current_line}, {skill}" if current_line else skill

        if c.stringWidth(test_line, font, size) <= (max_width - label_width):
            current_line = test_line
        else:
            # draw current line
            if first_line:
                c.drawString(x + 15, y, label_text + current_line)
                first_line = False
            else:
                c.drawString(x + 15 + label_width, y, current_line)

            y -= line_gap
            current_line = skill

    # draw last line
    if current_line:
        if first_line:
            c.drawString(x + 15, y, label_text + current_line)
        else:
            c.drawString(x + 15 + label_width, y, current_line)

    return y
# ==================================================
# CHART HELPERS — common internal builder
# All chart functions now go through _fig_to_image
# so figures are always closed and buffers released.
# ==================================================

def _apply_full_chart_style(ax, fig, grid_axis="y"):
    """Apply the standard white-background chart style."""
    ax.set_facecolor("#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    ax.grid(axis=grid_axis, linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    ax.tick_params(colors="#111111", labelsize=9)


def _make_histogram(data, title, xlabel, ylabel, figsize=(7.5, 4.5)):
    """Shared histogram builder used by both A1 and A2."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=figsize)
    # Cap bins: large datasets don't need more than 25 bins at this page size
    n_bins = min(25, max(5, len(data) // max(1, len(data) // 12)))
    ax.hist(data, bins=n_bins, color="#1A4F8A", edgecolor="#FFFFFF", linewidth=0.7, alpha=1.0)
    apply_chart_style(ax)
    ax.set_title(title, fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax.set_xlabel(xlabel, fontsize=10, color="#111111", labelpad=6)
    ax.set_ylabel(ylabel, fontsize=10, color="#111111", labelpad=6)
    return _fig_to_image(fig)


def _make_boxplot(data, title, xlabel, figsize=(7.5, 3.5)):
    """Shared boxplot builder."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=figsize)
    ax.boxplot(data, **_boxplot_props())
    ax.set_facecolor("#FFFFFF")
    fig.patch.set_facecolor("#FFFFFF")
    ax.grid(axis="x", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#444444")
    ax.spines["bottom"].set_color("#444444")
    ax.tick_params(colors="#111111", labelsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax.set_xlabel(xlabel, fontsize=10, color="#111111", labelpad=6)
    return _fig_to_image(fig)


def _make_country_bar(countries, salaries, title, figsize=(7.5, 4.5)):
    """Shared country bar chart builder."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=figsize)
    n_bars = len(countries)
    colors_to_use = _bar_colors()[:n_bars]
    ax.bar(countries, salaries, color=colors_to_use, edgecolor="#FFFFFF", linewidth=0.7)
    _apply_full_chart_style(ax, fig, grid_axis="y")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#111111", pad=10)
    ax.set_xlabel("Country", fontsize=10, color="#111111", labelpad=6)
    ax.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    plt.xticks(rotation=20)
    return _fig_to_image(fig)


# ==================================================
# APP 1 PDF CHART HELPERS  (public API unchanged)
# ==================================================

def create_histogram_a1(data):
    return _make_histogram(
        data,
        title="Distribution of Predicted Salaries",
        xlabel="Predicted Salary (USD)",
        ylabel="Count"
    )


def create_boxplot_a1(data):
    return _make_boxplot(
        data,
        title="Predicted Salary Spread",
        xlabel="Predicted Salary (USD)"
    )


def create_country_bar_chart_a1(country_group_chart):
    return _make_country_bar(
        country_group_chart["Country"].tolist(),
        country_group_chart["Predicted Annual Salary"].tolist(),
        title="Average Predicted Salary by Country"
    )


# ==================================================
# APP 2 PDF CHART HELPERS  (public API unchanged)
# ==================================================

def create_histogram_a2(data):
    return _make_histogram(
        data,
        title="Distribution of Predicted Salaries",
        xlabel="Predicted Salary (USD)",
        ylabel="Count"
    )


def create_boxplot_a2(data):
    return _make_boxplot(
        data,
        title="Predicted Salary Spread",
        xlabel="Predicted Salary (USD)"
    )


def create_country_bar_chart_a2(country_group_chart):
    return _make_country_bar(
        country_group_chart["Country"].tolist(),
        country_group_chart["Predicted Annual Salary (USD)"].tolist(),
        title="Average Predicted Salary by Country"
    )


# ==================================================
# PDF METADATA HELPER
# ==================================================

def apply_pdf_metadata(c, title, subject):
    c.setTitle(title)
    c.setAuthor("SalaryScope")
    c.setSubject(subject)
    c.setCreator("SalaryScope - Salary Prediction System")
    c.setKeywords("salary prediction, machine learning, salaryscope")


# ==================================================
# APP 1 — PDF: Manual Prediction
# ==================================================

def app1_generate_manual_pdf(
    data_dict, prediction, lower_bound, upper_bound,
    salary_band_label, metadata, classifier_metadata,
    career_stage_label, cluster_metadata
):
    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()
    apply_pdf_metadata(
        c,
        "SalaryScope Salary Prediction Report",
        "Manual Salary Prediction Report generated by SalaryScope"
    )
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
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    y -= 25
    y = draw_section_header(c, "Input Details", left_margin, y)
    c.setFont("Helvetica", 11)
    for key, value in data_dict.items():
        y -= 18
        y = draw_kv_line(c, f"{key}: {value}", left_margin, y)
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    y -= 25
    y = draw_section_header(c, "Prediction Results", left_margin, y)
    c.setFont("Helvetica", 11)
    monthly = prediction / 12
    weekly = prediction / 52
    hourly = prediction / (52 * 40)
    y -= 18
    y = draw_kv_line(c, f"Predicted Annual Salary: ${prediction:,.2f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Estimated Salary Level: {salary_band_label}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Predicted Career Stage: {career_stage_label}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Monthly (Approx): ${monthly:,.2f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Weekly (Approx): ${weekly:,.2f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Hourly (Approx, 40hr/week): ${hourly:,.2f}", left_margin, y)
    y -= 18
    y = draw_kv_line(
        c,
        f"Likely Salary Range (95% CI): ${lower_bound:,.2f} - ${upper_bound:,.2f}",
        left_margin,
        y
    )
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    y -= 25
    y = draw_section_header(c, "Model Information", left_margin, y)
    c.setFont("Helvetica", 11)
    y -= 18
    y = draw_kv_line(c, "Salary Prediction Model: Random Forest Regressor", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Test R\u00b2: {metadata['test_r2']:.4f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Cross-Validation R\u00b2: {metadata['cv_mean_r2']:.4f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"MAE: ${metadata['mae']:,.2f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"RMSE: ${metadata['rmse']:,.2f}", left_margin, y)
    y -= 20
    y = draw_kv_line(
        c,
        f"Salary Level Classifier: {classifier_metadata.get('model_type', 'Classifier')}",
        left_margin,
        y
    )

    if "accuracy" in classifier_metadata:
        y -= 18
        y = draw_kv_line(c, f"Accuracy: {classifier_metadata['accuracy']:.4f}", left_margin, y)

    if "precision_macro" in classifier_metadata:
        y -= 18
        y = draw_kv_line(
            c,
            f"Precision (Macro): {classifier_metadata['precision_macro']:.4f}",
            left_margin,
            y
        )

    if "recall_macro" in classifier_metadata:
        y -= 18
        y = draw_kv_line(
            c,
            f"Recall (Macro): {classifier_metadata['recall_macro']:.4f}",
            left_margin,
            y
        )

    if "f1_macro" in classifier_metadata:
        y -= 18
        y = draw_kv_line(c, f"F1 Score (Macro): {classifier_metadata['f1_macro']:.4f}", left_margin, y)

    y -= 20
    y = draw_kv_line(
        c,
        f"Career Stage Clustering Model: {cluster_metadata.get('model_type', 'KMeans')}",
        left_margin,
        y
    )

    silhouette = cluster_metadata.get("silhouette_score", 0)
    db_score = cluster_metadata.get("davies_bouldin_score", 0)

    y -= 18
    y = draw_kv_line(c, f"Silhouette Score: {silhouette:.4f}", left_margin, y)
    y -= 18
    y = draw_kv_line(c, f"Davies-Bouldin Score: {db_score:.4f}", left_margin, y)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP1: Resume Analysis PDF
# ==================================================
def app1_generate_resume_pdf(result_data):
    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()

    apply_pdf_metadata(
        c,
        "SalaryScope Resume Analysis Report",
        "Resume-based salary prediction generated by SalaryScope"
    )

    left_margin = 50
    right_margin = width - 50
    y = height - 50

    # HEADER
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 20

    c.setFont("Helvetica", 12)
    c.drawString(left_margin, y, "Resume Analysis Report")
    y -= 20

    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= INPUT DETAILS =================
    y -= 25
    y = draw_section_header(c, "Input Details", left_margin, y)

    c.setFont("Helvetica", 11)
    for key, value in result_data["input_details"].items():
        y -= 18

        if key == "Detected Skills" and value:
            y = draw_skills_clean(
                c,
                label=key,
                text=value,
                x=left_margin,
                y=y,
                max_width=right_margin - left_margin
            )
        else:
            y = draw_kv_line(c, f"{key}: {value}", left_margin, y)

    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= SCORE =================
    score = result_data["resume_score_data"]

    y -= 25
    y = draw_section_header(c, "Resume Score Breakdown", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Total Score: {score['total_score']}/100 ({score['level']})", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Experience Score: {score['experience_score']}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Education Score: {score['education_score']}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Skills Score: {score['skills_score']}", left_margin, y)

    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= PREDICTION =================
    pred = result_data["prediction"]
    lower = result_data["lower_bound"]
    upper = result_data["upper_bound"]

    monthly = pred / 12
    weekly = pred / 52
    hourly = pred / (52 * 40)

    y -= 25
    y = draw_section_header(c, "Prediction Results", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Predicted Annual Salary: ${pred:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Salary Level: {result_data['salary_band_label']}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Career Stage: {result_data['career_stage_label']}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Monthly: ${monthly:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Weekly: ${weekly:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Hourly: ${hourly:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(
        c,
        f"95% Confidence Interval: ${lower:,.2f} - ${upper:,.2f}",
        left_margin,
        y
    )

    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= INSIGHT =================
    y -= 25
    y = draw_section_header(c, "Pattern Insight", left_margin, y)

    insight = result_data["assoc_text_a1_improved"]
    y -= 18
    y = draw_wrapped_text(c, insight, left_margin, y, right_margin - left_margin)

    # FOOTER
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer
# ==================================================
# APP 1 — PDF: Batch Prediction
# ==================================================

def app1_generate_bulk_pdf(analytics_df):
    pd = _pd()
    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()

    apply_pdf_metadata(
        c,
        "SalaryScope Batch Salary Prediction Report",
        "Batch salary analytics generated by SalaryScope"
    )

    left_margin = 50
    right_margin = width - 50
    max_width = right_margin - left_margin
    y = height - 55

    # Pre-compute all stats once — avoids repeated passes over the Series
    sal = analytics_df["Predicted Annual Salary"]
    avg_salary    = float(sal.mean())
    min_salary    = float(sal.min())
    max_salary    = float(sal.max())
    std_salary    = float(sal.std())
    std_salary    = 0.0 if pd.isna(std_salary) else std_salary
    total_records = int(analytics_df.shape[0])
    median_salary = float(sal.median())
    q1_salary     = float(sal.quantile(0.25))
    q3_salary     = float(sal.quantile(0.75))
    iqr_salary    = q3_salary - q1_salary
    spread        = max_salary - min_salary

    # ================= PAGE 1 =================

    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Batch Salary Prediction Report")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    y -= 30
    y = draw_section_header(c, "Summary Statistics", left_margin, y, size=14)
    y -= 22
    c.setFont("Helvetica", 11)
    spacing = 17
    y = draw_kv_line(c, f"Total Records Processed: {total_records}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"Average Predicted Salary: ${avg_salary:,.2f}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"Median Predicted Salary: ${median_salary:,.2f}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"Minimum Predicted Salary: ${min_salary:,.2f}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"Maximum Predicted Salary: ${max_salary:,.2f}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"Salary Standard Deviation: ${std_salary:,.2f}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"Interquartile Range (IQR): ${iqr_salary:,.2f}", left_margin, y, offset=10)
    y -= spacing
    y = draw_kv_line(c, f"(Q1: ${q1_salary:,.2f}  |  Q3: ${q3_salary:,.2f})", left_margin, y, offset=20)

    y -= 30
    insight_text = (
        f"Insight: The predicted salary spread is ${spread:,.2f}. "
        "This reflects variation associated with experience, education level, and seniority."
    )
    y = draw_wrapped_text(c, insight_text, left_margin, y, max_width)

    y -= 20
    y = draw_section_header(c, "Salary Distribution", left_margin, y, size=13)

    # Build chart — figure is closed inside _fig_to_image immediately
    img = create_histogram_a1(sal)

    image_width = 500
    image_height = 290
    x_position = (width - image_width) / 2
    y -= image_height + 12
    c.drawImage(img, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 20
    difference = abs(avg_salary - median_salary)
    if difference < 1000:
        shape_comment = "approximately symmetric"
    elif avg_salary > median_salary:
        shape_comment = "slightly right-skewed"
    else:
        shape_comment = "slightly left-skewed"

    hist_text = (
        f"Interpretation: The salary distribution appears {shape_comment}. "
        f"The mean salary is ${avg_salary:,.2f} and the median salary is "
        f"${median_salary:,.2f}, indicating the overall central tendency "
        f"of the predicted salaries."
    )
    y = draw_wrapped_text(c, hist_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 2 =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Analytical Breakdown", left_margin, y, size=16)

    y -= 25
    y = draw_section_header(c, "Average Salary by Education Level", left_margin, y, size=12)

    edu_group = (
        analytics_df.groupby("Education Level")["Predicted Annual Salary"]
        .mean()
        .reset_index()
    )
    edu_map = {0: "High School", 1: "Bachelor's", 2: "Master's", 3: "PhD"}
    edu_group["Education Level"] = edu_group["Education Level"].map(edu_map)

    y -= 18
    for _, row in edu_group.iterrows():
        y = draw_kv_line(
            c,
            f"{row['Education Level']}: ${row['Predicted Annual Salary']:,.2f}",
            left_margin, y, offset=10
        )
        y -= 16

    y -= 15
    y = draw_section_header(c, "Average Salary by Seniority", left_margin, y, size=12)

    senior_group = (
        analytics_df.groupby("Senior")["Predicted Annual Salary"]
        .mean()
        .reset_index()
    )
    senior_map = {0: "Non-Senior", 1: "Senior"}
    senior_group["Senior"] = senior_group["Senior"].map(senior_map)

    y -= 18
    for _, row in senior_group.iterrows():
        y = draw_kv_line(
            c,
            f"{row['Senior']}: ${row['Predicted Annual Salary']:,.2f}",
            left_margin, y, offset=10
        )
        y -= 16

    y -= 15
    y = draw_section_header(c, "Average Predicted Salary by Country", left_margin, y, size=12)

    country_group = (
        analytics_df.groupby("Country")["Predicted Annual Salary"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary", ascending=False)
    )

    y -= 18
    for _, row in country_group.iterrows():
        y = draw_kv_line(
            c,
            f"{row['Country']}: ${row['Predicted Annual Salary']:,.2f}",
            left_margin, y, offset=10
        )
        y -= 16

    y -= 25
    y = draw_section_header(c, "Salary Distribution (Box Plot)", left_margin, y, size=12)

    img_box = create_boxplot_a1(sal)
    image_width = 480
    image_height = 200
    x_position = (width - image_width) / 2
    y -= image_height + 10
    c.drawImage(img_box, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 30
    analysis_text = (
        "Interpretation: This section presents a breakdown of predicted "
        "salaries across education levels and seniority, along with an "
        "overview of the overall salary distribution within the uploaded dataset."
    )
    y = draw_wrapped_text(c, analysis_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 3 =================
    c.showPage()
    y = height - 55

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Average Predicted Salary by Country")

    country_group_chart = (
        analytics_df.groupby("Country")["Predicted Annual Salary"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary", ascending=False)
        .head(5)
    )

    img_country = create_country_bar_chart_a1(country_group_chart)
    image_width = 500
    image_height = 300
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_country, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 25
    if len(country_group_chart) > 0:
        top_country    = country_group_chart.iloc[0]["Country"]
        top_salary     = country_group_chart.iloc[0]["Predicted Annual Salary"]
        bottom_country = country_group_chart.iloc[-1]["Country"]
        bottom_salary  = country_group_chart.iloc[-1]["Predicted Annual Salary"]
    else:
        top_country = bottom_country = "N/A"
        top_salary = bottom_salary = 0.0

    country_spread = top_salary - bottom_salary
    interpretation_text = (
        f"Interpretation: Among the selected countries, {top_country} "
        f"shows the highest average predicted salary (${top_salary:,.2f}), "
        f"while {bottom_country} shows the lowest (${bottom_salary:,.2f}). "
        f"The difference of ${country_spread:,.2f} highlights regional "
        f"variations in predicted compensation."
    )
    y = draw_wrapped_text(c, interpretation_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer

# ==================================================
# APP1: Scenario Analysis PDF
# ==================================================

# ==================================================
# APP 1 — PDF: Model Analytics
# ==================================================

def app1_generate_model_analytics_pdf(metadata, model, model_comparison,
                                       classifier_metadata, salary_band_model, analytics, cluster_metadata, assoc_rules_df):
    plt = _plt()
    pd = _pd()
    np = _np()
    ImageReader = _ImageReader()

    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()
    apply_pdf_metadata(
        c,
        "SalaryScope Model Analytics Report",
        "Machine learning model diagnostics generated by SalaryScope"
    )
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
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    y -= 30
    y = draw_section_header(c, "Regression Model: Random Forest", left_margin, y, size=14)
    y -= 22
    c.setFont("Helvetica", 11)
    spacing = 17
    c.drawString(left_margin + 10, y, f"Test R\u00b2: {metadata['test_r2']:.4f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"Cross-Validation R\u00b2 (Mean): {metadata['cv_mean_r2']:.4f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"MAE: ${metadata['mae']:,.2f}")
    y -= spacing
    c.drawString(left_margin + 10, y, f"RMSE: ${metadata['rmse']:,.2f}")

    y -= 25
    y = draw_section_header(c, "Model Comparison (Regression)", left_margin, y, size=12)
    y -= 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_margin + 5, y, "Model")
    c.drawString(left_margin + 260, y, "R\u00b2")
    c.drawString(left_margin + 320, y, "MAE")
    c.drawString(left_margin + 400, y, "RMSE")
    y -= 10
    y = draw_line(c, left_margin, right_margin, y)
    y -= 15
    c.setFont("Helvetica", 10)
    sorted_models = sorted(model_comparison, key=lambda x: x["Test R2"], reverse=True)
    for row in sorted_models:
        c.drawString(left_margin + 5, y, row["Model"][:34])
        c.drawString(left_margin + 260, y, f"{row['Test R2']:.4f}")
        c.drawString(left_margin + 320, y, f"${row['MAE']:,.0f}")
        c.drawString(left_margin + 400, y, f"${row['RMSE']:,.0f}")
        y -= 15

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 2 — FEATURE IMPORTANCE (Regression)
    c.showPage()
    y = height - 55
    y = draw_section_header(c, "Feature Importance \u2014 Regression Model", left_margin, y, size=16)

    rf_model    = model.named_steps["model"]
    preprocessor = model.named_steps["preprocessor"]
    feature_names = preprocessor.get_feature_names_out()
    importances   = rf_model.feature_importances_

    importance_df = pd.DataFrame({"Feature": feature_names, "Importance": importances})
    importance_df["Feature"] = (
        importance_df["Feature"]
        .str.replace("num__", "", regex=False)
        .str.replace("cat__", "", regex=False)
    )
    importance_df["Original_Feature"] = importance_df["Feature"].apply(lambda x: x.split("_")[0])
    grouped_importance_df = (
        importance_df
        .groupby("Original_Feature")["Importance"]
        .sum()
        .reset_index()
        .sort_values(by="Importance", ascending=False)
    )

    fig_imp, ax_imp = plt.subplots(figsize=(7.5, 4.5))
    ax_imp.barh(
        grouped_importance_df["Original_Feature"][::-1],
        grouped_importance_df["Importance"][::-1],
        color="#1A4F8A", edgecolor="#FFFFFF", linewidth=0.7
    )
    apply_chart_style(ax_imp)
    ax_imp.set_title("Feature Importances (Regression)", fontsize=12, fontweight="bold",
                     color="#111111", pad=10)
    img_imp = _fig_to_image(fig_imp)

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
    y = draw_section_header(c, "Predicted vs Actual Analysis", left_margin, y, size=16)

    y_test_rf = analytics["y_test"]
    y_pred_rf  = analytics["y_pred"]

    fig1, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax1.scatter(y_test_rf, y_pred_rf, alpha=0.5, color="#1A4F8A", s=8, edgecolors="none")
    min_val = min(float(y_test_rf.min()), float(y_pred_rf.min()))
    max_val = max(float(y_test_rf.max()), float(y_pred_rf.max()))
    ax1.plot([min_val, max_val], [min_val, max_val], color="red", linewidth=1.5)
    ax1.set_title("Predicted vs Actual Salary")
    ax1.set_xlabel("Actual Salary")
    ax1.set_ylabel("Predicted Salary")
    ax1.grid(True)
    img1 = _fig_to_image(fig1)

    y -= 260
    c.drawImage(img1, left_margin, y, width=500, height=250)

    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    text2 = ("Interpretation: Points closer to the diagonal line represent "
             "accurate predictions. Greater dispersion indicates prediction error.")
    y = draw_wrapped_text(c, text2, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 4 — RESIDUAL ANALYSIS
    c.showPage()
    y = height - 55
    y = draw_section_header(c, "Residual Analysis", left_margin, y, size=16)

    residuals = analytics["residuals"]

    fig2, ax2 = plt.subplots(figsize=(7.5, 3.5))
    ax2.scatter(y_pred_rf, residuals, alpha=0.6, color="#1A4F8A", s=8, edgecolors="none")
    ax2.axhline(0, color="red", linestyle="--")
    ax2.set_title("Residuals vs Predicted Values")
    ax2.set_xlabel("Predicted Salary")
    ax2.set_ylabel("Residual")
    ax2.grid(True)
    img2 = _fig_to_image(fig2)

    y -= 230
    c.drawImage(img2, left_margin, y, width=500, height=200)

    fig3, ax3 = plt.subplots(figsize=(7.5, 3))
    ax3.hist(residuals, bins=30, color="#1A4F8A", edgecolor="white")
    ax3.set_title("Residual Distribution")
    ax3.set_xlabel("Residual")
    ax3.set_ylabel("Count")
    ax3.grid(axis="y", linestyle="--", color="#888888", alpha=0.6, linewidth=0.7)
    img3 = _fig_to_image(fig3)

    y -= 220
    c.drawImage(img3, left_margin, y, width=500, height=180)

    y -= 20
    c.setFont("Helvetica-Oblique", 10)
    text3 = ("Interpretation: Residuals centered around zero indicate balanced "
             "model errors. A symmetric distribution suggests stable predictive behavior.")
    y = draw_wrapped_text(c, text3, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 5 — CLASSIFICATION MODEL
    c.showPage()
    y = height - 55
    y = draw_section_header(c, "Salary Level Classification Model", left_margin, y, size=16)

    y -= 25
    y = draw_section_header(c, "Performance Metrics", left_margin, y, size=12)
    c.setFont("Helvetica", 11)
    y -= 18
    c.drawString(left_margin + 10, y, f"Accuracy: {classifier_metadata.get('accuracy', 0):.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Precision (Macro): {classifier_metadata.get('precision_macro', 0):.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Recall (Macro): {classifier_metadata.get('recall_macro', 0):.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"F1 Score (Macro): {classifier_metadata.get('f1_macro', 0):.4f}")

    y -= 25
    y = draw_section_header(c, "Confusion Matrix", left_margin, y, size=12)

    cm_raw = classifier_metadata.get("confusion_matrix")
    cm = np.array(cm_raw) if cm_raw is not None else np.zeros((3, 3), dtype=int)

    fig_cm, ax_cm = plt.subplots(figsize=(7.5, 4.5))
    norm = plt.Normalize(vmin=cm.min(), vmax=max(cm.max(), 1))
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
    img_cm = _fig_to_image(fig_cm)

    image_width = 420
    image_height = 250
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_cm, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 30
    y = draw_section_header(c, "Feature Importance (Classifier)", left_margin, y, size=12)

    importance_dict = classifier_metadata.get("feature_importance", {})
    importance_cls_df = (
        pd.DataFrame(list(importance_dict.items()), columns=["Feature", "Importance"])
        .sort_values(by="Importance", ascending=False)
    )

    fig_imp_cls, ax_imp_cls = plt.subplots(figsize=(7, 4))
    ax_imp_cls.barh(
        importance_cls_df["Feature"][::-1],
        importance_cls_df["Importance"][::-1],
        color="#1A4F8A", edgecolor="white", linewidth=0.6
    )
    ax_imp_cls.set_title("Feature Importances (Classifier)")
    ax_imp_cls.grid(axis="x", linestyle="--", alpha=0.6)
    img_imp_cls = _fig_to_image(fig_imp_cls)

    image_width = 480
    image_height = 260
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_imp_cls, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 6 — CLUSTERING MODEL ANALYTICS
    c.showPage()
    y = height - 55
    y = draw_section_header(c, "Career Stage Clustering Model", left_margin, y, size=16)

    y -= 20
    desc_text = (
        "This model segments individuals into career stages using KMeans clustering "
        "based on Years of Experience and Education Level. A derived Career Score "
        "feature enhances separation between progression levels."
    )
    y = draw_wrapped_text(c, desc_text, left_margin, y, max_width)

    y -= 25
    y = draw_section_header(c, "Clustering Quality Metrics", left_margin, y, size=12)
    c.setFont("Helvetica", 11)
    silhouette = cluster_metadata.get("silhouette_score", 0)
    db_score   = cluster_metadata.get("davies_bouldin_score", 0)
    y -= 18
    c.drawString(left_margin + 10, y, f"Silhouette Score: {silhouette:.4f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Davies-Bouldin Score: {db_score:.4f}")

    y -= 25
    y = draw_section_header(c, "Model Configuration", left_margin, y, size=12)
    config_items = [
        ("Model Type",        cluster_metadata.get("model_type")),
        ("Training Dataset",  cluster_metadata.get("training_dataset")),
        ("Dataset Shape",     cluster_metadata.get("dataset_shape")),
        ("Features Used",     ", ".join(map(str, cluster_metadata.get("features_used", [])))),
        ("Engineered Feature", cluster_metadata.get("engineered_feature")),
        ("Number of Clusters", cluster_metadata.get("cluster_count")),
    ]
    c.setFont("Helvetica", 11)
    for key, value in config_items:
        y -= 16
        c.drawString(left_margin + 10, y, f"{key}: {value}")

    y -= 25
    y = draw_section_header(c, "Cluster Visualization (PCA Projection)", left_margin, y, size=12)

    X_pca_vis       = analytics["X_pca"]
    cluster_labels_vis = analytics["cluster_labels"]
    centroids_pca   = analytics["centroids_pca"]
    stage_map       = cluster_metadata.get("cluster_stage_mapping", {})
    stage_labels_vis = [stage_map.get(int(cl), "Unknown") for cl in cluster_labels_vis]

    plot_df = pd.DataFrame({
        "PCA1": X_pca_vis[:, 0],
        "PCA2": X_pca_vis[:, 1],
        "Career Stage": stage_labels_vis
    })

    fig_pca, ax_pca = plt.subplots(figsize=(6.5, 3.8))
    colors = {
        "Entry Stage":      "#5DADE2",
        "Growth Stage":     "#2E86C1",
        "Leadership Stage": "#8E44AD"
    }
    for stage in plot_df["Career Stage"].unique():
        subset = plot_df[plot_df["Career Stage"] == stage]
        ax_pca.scatter(
            subset["PCA1"], subset["PCA2"],
            label=stage, alpha=0.6, s=18,
            color=colors.get(stage, "#999999")
        )
    for i, (x_c, y_c) in enumerate(centroids_pca):
        label = stage_map.get(i, f"Cluster {i}")
        ax_pca.scatter(x_c, y_c, marker="x", s=100, color="#EF4444")
        ax_pca.text(x_c, y_c, label, fontsize=7)
    ax_pca.set_title("PCA Projection of Career Clusters", fontsize=10)
    ax_pca.set_xlabel("PCA1")
    ax_pca.set_ylabel("PCA2")
    ax_pca.legend(fontsize=7)
    ax_pca.grid(True)
    img_pca = _fig_to_image(fig_pca, dpi=150)

    image_width = 460
    image_height = 230
    x_position = (width - image_width) / 2
    y -= image_height + 15
    c.drawImage(img_pca, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    y -= 18
    c.setFont("Helvetica-Oblique", 9)
    note_text = (
        "Note: The structured patterns in this PCA visualization reflect the linear relationships "
        "between experience, education, and the derived career score used for clustering."
    )
    y = draw_wrapped_text(c, note_text, left_margin, y, max_width)

    y -= 15
    interpretation_text = (
        "Interpretation: The clustering model groups individuals into career stages based on "
        "experience and education. The PCA visualization shows separation between clusters, "
        "while the derived career score enhances progression-based segmentation."
    )
    y = draw_wrapped_text(c, interpretation_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 7 — ASSOCIATION RULE MINING =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Association Rule Mining (Apriori)", left_margin, y, size=16)

    # -----------------------------
    # PREP DATA
    # -----------------------------
    rules_df = assoc_rules_df.copy()
    rules_df = rules_df[rules_df["lift"] > 1]

    def clean_text(x):
        return (
            str(x)
            .replace("Education_Category_", "")
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

    rules_df["rule"] = rules_df["antecedents"] + " \u2192 " + rules_df["consequents"]

    rules_df["support"] = rules_df["support"].round(3)
    rules_df["confidence"] = rules_df["confidence"].round(3)
    rules_df["lift"] = rules_df["lift"].round(3)

    rules_df = rules_df.sort_values(by="lift", ascending=False)

    # -----------------------------
    # SUMMARY METRICS
    # -----------------------------
    y -= 25
    y = draw_section_header(c, "Rule Metrics Summary", left_margin, y, size=12)

    total_rules = len(rules_df)
    max_conf = rules_df["confidence"].max() if len(rules_df) else 0
    max_lift = rules_df["lift"].max() if len(rules_df) else 0

    c.setFont("Helvetica", 11)
    y -= 18
    c.drawString(left_margin + 10, y, f"Total Rules: {total_rules}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Max Confidence: {max_conf:.3f}")
    y -= 16
    c.drawString(left_margin + 10, y, f"Max Lift: {max_lift:.3f}")

    # -----------------------------
    # TOP RULES TABLE
    # -----------------------------
    y -= 25
    y = draw_section_header(c, "Top Rules (by Lift)", left_margin, y, size=12)

    top_rules = rules_df.head(8)

    # Header
    y -= 18
    c.setFont("Helvetica-Bold", 10)

    c.drawString(left_margin + 5, y, "Rule")
    c.drawString(left_margin + 360, y, "Conf")
    c.drawString(left_margin + 420, y, "Lift")

    y -= 8
    y = draw_line(c, left_margin, right_margin, y)

    # Rows
    y -= 15
    c.setFont("Helvetica", 9)

    for _, row in top_rules.iterrows():
        # Wrap rule text manually (important for long rules)
        rule_text = row["rule"]

        # Split rule into multiple lines if too long
        max_rule_width = 340
        lines = []
        words = rule_text.split()
        current = ""

        for w in words:
            test = current + " " + w if current else w
            if c.stringWidth(test, "Helvetica", 9) <= max_rule_width:
                current = test
            else:
                lines.append(current)
                current = w
        if current:
            lines.append(current)

        # Draw rule (possibly multiple lines)
        for i, line in enumerate(lines):
            c.drawString(left_margin + 5, y, line)

            # Only draw metrics on FIRST line
            if i == 0:
                c.drawString(left_margin + 360, y, f"{row['confidence']:.2f}")
                c.drawString(left_margin + 420, y, f"{row['lift']:.2f}")

            y -= 12

        y -= 4  # spacing between rules

    # -----------------------------
    # INTERPRETATION TEXT
    # -----------------------------
    y -= 20

    interpretation_text = (
        "Interpretation: Rules with lift greater than 1 indicate meaningful associations "
        "between career attributes and salary outcomes. Higher confidence reflects rule reliability, "
        "while lift captures the strength of the relationship beyond random chance."
    )

    y = draw_wrapped_text(c, interpretation_text, left_margin, y, max_width)
    # -----------------------------
    # LIFT BAR CHART
    # -----------------------------
#    y -= 20

#    plt = _plt()
#    fig, ax = plt.subplots(figsize=(7.5, 4))

#    plot_df = top_rules[::-1]
#    ax.barh(
#        plot_df["rule"],
#        plot_df["lift"],
#        color="#1A4F8A",
#        edgecolor="#FFFFFF",
#        linewidth=0.7
#    )

#    _apply_full_chart_style(ax, fig, grid_axis="x")

#    ax.set_title("Top Association Rules by Lift", fontsize=12, fontweight="bold")
#    ax.set_xlabel("Lift")

#   img_rules = _fig_to_image(fig)

#    image_width = 500
#    image_height = 260
#    x_position = (width - image_width) / 2

    #y -= image_height + 10

    #c.drawImage(
    #    img_rules,
    #    x_position,
    #    y,
    #    width=image_width,
    #    height=image_height,
    #    preserveAspectRatio=True,
    #    mask="auto"
    #)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 8 — RESUME NLP MODULE =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Resume NLP Module (Feature Extraction System)", left_margin, y, size=16)

    # -----------------------------
    # DESCRIPTION
    # -----------------------------
    y -= 20
    desc_text = (
        "This module processes unstructured resume text and converts it into structured features "
        "used by the machine learning model. Unlike predictive models, this is a rule-based NLP "
        "system designed for efficient and interpretable feature extraction."
    )
    y = draw_wrapped_text(c, desc_text, left_margin, y, max_width)

    # -----------------------------
    # COMPONENTS
    # -----------------------------
    y -= 25
    y = draw_section_header(c, "System Components", left_margin, y, size=12)

    components = [
        "Text Extraction: pdfplumber (PDF parsing)",
        "Text Cleaning: Regex preprocessing",
        "Experience Extraction: Regex-based pattern detection",
        "Education Detection: Rule-based keyword matching",
        "Skill Detection: spaCy PhraseMatcher",
        "Job Title Detection: Phrase matching with alias mapping",
        "Country Detection: spaCy Named Entity Recognition",
        "Seniority Detection: Derived from experience and job title"
    ]

    c.setFont("Helvetica", 11)
    for comp in components:
        y -= 16
        c.drawString(left_margin + 10, y, f"\u2022 {comp}")

    # -----------------------------
    # PIPELINE
    # -----------------------------
    y -= 25
    y = draw_section_header(c, "Processing Pipeline", left_margin, y, size=12)

    pipeline_text = (
        "PDF Resume \u2192 Text Extraction \u2192 Cleaning \u2192 NLP Processing \u2192 Feature Extraction "
        "\u2192 Structured Input \u2192 Machine Learning Model"
    )
    y -= 18
    y = draw_wrapped_text(c, pipeline_text, left_margin + 10, y, max_width - 10)

    # -----------------------------
    # DESIGN RATIONALE
    # -----------------------------
    y -= 25
    y = draw_section_header(c, "Design Rationale", left_margin, y, size=12)

    rationale_points = [
        "No labeled resume dataset available for supervised NLP training",
        "Rule-based NLP ensures deterministic and interpretable outputs",
        "Faster processing compared to deep learning models",
        "Suitable for structured feature extraction (skills, experience, etc.)"
    ]

    c.setFont("Helvetica", 11)
    for point in rationale_points:
        y -= 16
        c.drawString(left_margin + 10, y, f"\u2022 {point}")

    # -----------------------------
    # LIMITATIONS
    # -----------------------------
    y -= 25
    y = draw_section_header(c, "Limitations", left_margin, y, size=12)

    limitations = [
        "Performance depends on resume formatting and keyword presence",
        "May miss implicit or uncommon skill expressions",
        "Does not perform deep semantic understanding"
    ]

    c.setFont("Helvetica", 11)
    for lim in limitations:
        y -= 16
        c.drawString(left_margin + 10, y, f"\u2022 {lim}")

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer


@st.cache_data(show_spinner=False)
def cached_app1_model_analytics_pdf(
    metadata,
    model_comparison,
    classifier_metadata,
    analytics,
    cluster_metadata,
    assoc_rules_df,
    _model,
    _salary_band_model
):
    return app1_generate_model_analytics_pdf(
        metadata,
        _model,
        model_comparison,
        classifier_metadata,
        _salary_band_model,
        analytics,
        cluster_metadata,
        assoc_rules_df
    )


# ==================================================
# APP 2 — PDF: Manual Prediction
# ==================================================

def app2_generate_manual_pdf(data_dict, prediction, lower_bound, upper_bound, metadata):
    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()
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
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    weekly  = prediction / 52
    hourly  = prediction / (52 * 40)
    y -= 18
    c.drawString(left_margin + 15, y, f"Predicted Annual Salary: ${prediction:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Monthly (Approx): ${monthly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Weekly (Approx): ${weekly:,.2f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"Hourly (Approx, 40hr/week): ${hourly:,.2f}")
    #y -= 18
    #c.drawString(left_margin + 15, y,
    #             f"Likely Salary Range (95% CI): ${lower_bound:,.2f} - ${upper_bound:,.2f}")
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
    c.drawString(left_margin + 15, y, f"R\u00b2 (log scale): {metadata['test_r2_log_scale']:.4f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"MAE: ${metadata['mae_usd']:,.0f}")
    y -= 18
    c.drawString(left_margin + 15, y, f"RMSE: ${metadata['rmse_usd']:,.0f}")
    #y -= 18
    #c.drawString(left_margin + 15, y,
    #             "Confidence interval estimated from variance across boosted trees.")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")
    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 2 — PDF: Resume Analysis
# ==================================================

def app2_generate_resume_pdf(result_data):
    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()

    apply_pdf_metadata(
        c,
        "SalaryScope Resume Analysis Report",
        "Resume-based salary prediction generated by SalaryScope"
    )

    left_margin = 50
    right_margin = width - 50
    y = height - 50

    # ================= HEADER =================
    c.setFont("Helvetica-Bold", 18)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 20

    c.setFont("Helvetica", 12)
    c.drawString(left_margin, y, "Resume Analysis Report")
    y -= 20

    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= INPUT DETAILS =================
    y -= 25
    y = draw_section_header(c, "Input Details", left_margin, y)

    c.setFont("Helvetica", 11)
    for key, value in result_data["input_details_a2"].items():
        y -= 18

        if key == "Detected Skills" and value:
            y = draw_skills_clean(
                c,
                label=key,
                text=value,
                x=left_margin,
                y=y,
                max_width=right_margin - left_margin
            )
        else:
            y = draw_kv_line(c, f"{key}: {value}", left_margin, y)

    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= RESUME SCORE =================
    score = result_data["resume_score_data_a2"]

    y -= 25
    y = draw_section_header(c, "Resume Score Breakdown", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Total Score: {score['total_score_a2']}/100 ({score['level_a2']})", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Experience Score: {score['experience_score_a2']}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Skills Score: {score['skills_score_a2']}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Role Relevance: {score['title_score_a2']}", left_margin, y)

    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= PREDICTION =================
    pred = result_data["prediction_a2"]

    monthly = pred / 12
    weekly = pred / 52
    hourly = pred / (52 * 40)

    y -= 25
    y = draw_section_header(c, "Prediction Results", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Predicted Annual Salary: ${pred:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Monthly: ${monthly:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Weekly: ${weekly:,.2f}", left_margin, y)

    y -= 18
    y = draw_kv_line(c, f"Hourly (40hr/week): ${hourly:,.2f}", left_margin, y)

    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # ================= OPTIONAL NOTES =================
    y -= 25
    y = draw_section_header(c, "Profile Summary", left_margin, y)

    summary_text = (
        f"This resume is classified as a {score['level_a2']} profile with a total score "
        f"of {score['total_score_a2']}/100. The predicted salary reflects the combined "
        f"impact of experience level, job role, and detected skills."
    )

    y -= 18
    y = draw_wrapped_text(c, summary_text, left_margin, y, right_margin - left_margin)

    # ================= FOOTER =================
    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer
# ==================================================
# APP 2 — PDF: Batch Prediction
# ==================================================

def app2_generate_bulk_pdf(analytics_df, country_map):
    plt = _plt()
    pd = _pd()
    ImageReader = _ImageReader()

    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()
    apply_pdf_metadata(c, "SalaryScope Batch Salary Prediction Report",
                       "Batch salary analytics generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 55
    max_width = right_margin - left_margin

    # Pre-compute stats once
    sal = analytics_df["Predicted Annual Salary (USD)"]
    avg_salary    = float(sal.mean())
    min_salary    = float(sal.min())
    max_salary    = float(sal.max())
    std_salary    = float(sal.std())
    std_salary    = 0.0 if pd.isna(std_salary) else std_salary
    total_records = int(analytics_df.shape[0])
    median_salary = float(sal.median())
    q1_salary     = float(sal.quantile(0.25))
    q3_salary     = float(sal.quantile(0.75))
    iqr_salary    = q3_salary - q1_salary
    spread        = max_salary - min_salary

    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Batch Salary Prediction Report")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

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
    insight_text = (
        f"Insight: The predicted salary spread is ${spread:,.2f}. "
        "This variation reflects differences in experience level, company size, "
        "work arrangement, and geographic location among the uploaded records."
    )
    y = draw_wrapped_text(c, insight_text, left_margin, y, max_width)

    y -= 20
    c.setFont("Helvetica-Bold", 13)
    c.drawString(left_margin, y, "Salary Distribution")

    img = create_histogram_a2(sal)
    image_width = 500
    image_height = 290
    x_position = (width - image_width) / 2
    y -= image_height + 12
    c.drawImage(img, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask='auto')

    y -= 20
    difference = abs(avg_salary - median_salary)
    if difference < 1000:
        shape_comment = "approximately symmetric"
    elif avg_salary > median_salary:
        shape_comment = "slightly right-skewed"
    else:
        shape_comment = "slightly left-skewed"

    hist_text = (
        f"Interpretation: The salary distribution appears {shape_comment}. "
        f"The mean salary is ${avg_salary:,.2f} and the median salary is "
        f"${median_salary:,.2f}, indicating the overall central tendency of the predicted salaries."
    )
    y = draw_wrapped_text(c, hist_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 2 — ANALYTICAL BREAKDOWN
    EXPERIENCE_MAP_PDF  = {"EN": "Entry Level", "MI": "Mid Level", "SE": "Senior Level", "EX": "Executive Level"}
    COMPANY_SIZE_MAP_PDF = {"S": "Small Company", "M": "Medium Company", "L": "Large Company"}
    REMOTE_MAP_PDF      = {0: "On-site", 50: "Hybrid", 100: "Fully Remote"}

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
        lambda x: country_map.get(x, x))
    y -= 18
    c.setFont("Helvetica", 11)
    for _, row in country_group.iterrows():
        c.drawString(left_margin + 10, y,
                     f"{row['company_location']}: ${row['Predicted Annual Salary (USD)']:,.2f}")
        y -= 16

    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, y, "Salary Distribution (Box Plot)")
    img_box = create_boxplot_a2(sal)
    image_width = 480
    image_height = 200
    x_position = (width - image_width) / 2
    y -= image_height + 10
    c.drawImage(img_box, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # PAGE 3 — COUNTRY SALARY VISUALIZATION
    c.showPage()
    y = height - 55
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left_margin, y, "Average Predicted Salary by Country")

    country_group_chart = (
        analytics_df
        .groupby("company_location")["Predicted Annual Salary (USD)"]
        .mean()
        .reset_index()
        .sort_values(by="Predicted Annual Salary (USD)", ascending=False)
        .head(5)
    )
    country_group_chart["Country"] = country_group_chart["company_location"].map(
        lambda x: country_map.get(x, x)
    )

    img_country = create_country_bar_chart_a2(country_group_chart)
    image_width = 500
    image_height = 300
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_country, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    y -= 25
    if len(country_group_chart) > 0:
        top_country    = country_group_chart.iloc[0]["Country"]
        top_salary     = float(country_group_chart.iloc[0]["Predicted Annual Salary (USD)"])
        bottom_country = country_group_chart.iloc[-1]["Country"]
        bottom_salary  = float(country_group_chart.iloc[-1]["Predicted Annual Salary (USD)"])
    else:
        top_country = bottom_country = "N/A"
        top_salary = bottom_salary = 0.0

    country_spread = top_salary - bottom_salary
    interpretation_text = (
        f"Interpretation: Among the selected countries, {top_country} "
        f"shows the highest average predicted salary (${top_salary:,.2f}), "
        f"while {bottom_country} shows the lowest (${bottom_salary:,.2f}). "
        f"The difference of ${country_spread:,.2f} highlights regional "
        f"variations in predicted compensation."
    )
    y = draw_wrapped_text(c, interpretation_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer

# ==================================================
# APP2: PDF: Scenario Analysis
# ==================================================

# ==================================================
# APP 2 — PDF: Model Analytics
# ==================================================

def app2_generate_model_analytics_pdf(metadata, model, model_comparison, analytics):
    plt = _plt()
    pd = _pd()
    ImageReader = _ImageReader()

    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()
    apply_pdf_metadata(c, "SalaryScope Model Analytics Report",
                       "Machine learning model diagnostics generated by SalaryScope")
    left_margin = 50
    right_margin = width - 50
    y = height - 55
    max_width = right_margin - left_margin

    # draw_wrapped_text is now the shared module-level function;
    # the original had a local redefinition here — removed (same behaviour).

    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24
    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Model Analytics Report")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.line(left_margin, y, right_margin, y)

    y -= 30
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left_margin, y, "Performance Metrics")
    y -= 22
    c.setFont("Helvetica", 11)
    spacing = 17
    r2  = metadata["test_r2_log_scale"]
    mae = metadata["mae_usd"]
    rmse = metadata["rmse_usd"]
    c.drawString(left_margin + 10, y, f"Test R\u00b2 (log scale): {r2:.4f}")
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
    c.drawString(left_margin + 260, y, "R\u00b2")
    c.drawString(left_margin + 320, y, "MAE")
    c.drawString(left_margin + 400, y, "RMSE")
    y -= 10
    c.line(left_margin, y, right_margin, y)
    y -= 15
    c.setFont("Helvetica", 10)
    sorted_models = sorted(model_comparison, key=lambda x: x["Test R2"], reverse=True)
    for row in sorted_models:
        c.drawString(left_margin + 5, y, row["Model"][:34])
        c.drawString(left_margin + 260, y, f"{row['Test R2']:.4f}")
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

    xgb_model_inner  = model.named_steps["model"]
    preprocessor_a2  = model.named_steps["preprocessor"]
    feature_names_a2 = preprocessor_a2.get_feature_names_out()
    importances_a2   = xgb_model_inner.feature_importances_
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
    ax_imp.set_title("Top 15 Feature Importances", fontsize=12, fontweight="bold",
                     color="#111111", pad=10)
    img_imp = _fig_to_image(fig_imp)

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

    y_test_a2 = analytics["y_actual"]
    preds_a2  = analytics["y_pred"]

    fig_pred, ax_pred = plt.subplots(figsize=(7.5, 4.5))
    ax_pred.scatter(y_test_a2, preds_a2, alpha=0.6, color="#1A4F8A", s=8, edgecolors="none")
    min_val = min(float(y_test_a2.min()), float(preds_a2.min()))
    max_val = max(float(y_test_a2.max()), float(preds_a2.max()))
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
    img_pred = _fig_to_image(fig_pred)

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

    residuals_a2 = analytics["residuals"]

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
    img_res = _fig_to_image(fig_res)

    image_width = 500
    image_height = 280
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_res, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")
    y -= 20
    mean_residual = float(residuals_a2.mean())
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


@st.cache_data(show_spinner=False)
def cached_app2_model_analytics_pdf(
    metadata,
    model_comparison,
    analytics,
    _model
):
    return app2_generate_model_analytics_pdf(
        metadata,
        _model,
        model_comparison,
        analytics
    )

# ==================================================
# APP 1 — PDF: Scenario Analysis
# ==================================================
def app1_generate_scenario_pdf(scenarios_df):
    pd = _pd()
    plt = _plt()

    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()

    apply_pdf_metadata(
        c,
        "SalaryScope Scenario Analysis Report",
        "Scenario-based salary comparison generated by SalaryScope"
    )

    left_margin = 50
    right_margin = width - 50
    max_width = right_margin - left_margin
    y = height - 55

    # ================= PAGE 1: HEADER + SUMMARY + SCENARIO LIST =================
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24

    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Scenario Analysis Report")
    y -= 15

    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # --- Summary Statistics ---
    sal = scenarios_df["Predicted Salary (USD)"]
    avg_salary = float(sal.mean())
    min_salary = float(sal.min())
    max_salary = float(sal.max())

    y -= 30
    y = draw_section_header(c, "Summary Statistics", left_margin, y, size=14)

    c.setFont("Helvetica", 11)
    y -= 22
    y = draw_kv_line(c, f"Total Scenarios: {len(scenarios_df)}", left_margin, y, offset=10)
    y -= 17
    y = draw_kv_line(c, f"Average Predicted Salary: ${avg_salary:,.2f}", left_margin, y, offset=10)
    y -= 17
    y = draw_kv_line(c, f"Minimum Predicted Salary: ${min_salary:,.2f}", left_margin, y, offset=10)
    y -= 17
    y = draw_kv_line(c, f"Maximum Predicted Salary: ${max_salary:,.2f}", left_margin, y, offset=10)

    # --- Scenario Detail List ---
    y -= 25
    y = draw_section_header(c, "Scenario Details", left_margin, y, size=12)

    c.setFont("Helvetica", 10)
    for _, row in scenarios_df.iterrows():
        y -= 18
        if y < 120:
            c.showPage()
            y = height - 55

        line1 = (
            f"{row['Scenario']} \u2014 {row['Job Title']} | "
            f"{row['Education']} | {row['Experience (yrs)']} yrs exp | "
            f"Senior: {row['Senior']} | {row['Country']}"
        )
        y = draw_wrapped_text(c, line1, left_margin + 10, y, max_width - 10)

        y -= 14
        line2 = (
            f"   Predicted: ${row['Predicted Salary (USD)']:,.0f}  "
            f"(95% CI: ${row['Lower Bound']:,.0f} \u2013 ${row['Upper Bound']:,.0f})  "
            f"| Level: {row['Salary Level']}  | Stage: {row['Career Stage']}"
        )
        y = draw_wrapped_text(c, line2, left_margin + 10, y, max_width - 10)
        y -= 6

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 2: PREDICTED SALARY BAR CHART =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Predicted Salary Comparison", left_margin, y, size=14)

    fig_bar, ax_bar = plt.subplots(figsize=(7.5, 4.5))
    ax_bar.bar(
        scenarios_df["Scenario"],
        scenarios_df["Predicted Salary (USD)"],
        color="#1A4F8A",
        edgecolor="white",
        linewidth=0.7
    )
    apply_chart_style(ax_bar)
    ax_bar.set_title("Predicted Annual Salary by Scenario", fontsize=12,
                     fontweight="bold", color="#111111", pad=10)
    ax_bar.set_xlabel("Scenario", fontsize=10, color="#111111", labelpad=6)
    ax_bar.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    plt.xticks(rotation=20)
    img_bar = _fig_to_image(fig_bar)

    image_width = 500
    image_height = 280
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_bar, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    best_row = scenarios_df.loc[scenarios_df["Predicted Salary (USD)"].idxmax()]
    y -= 20
    bar_text = (
        f"Interpretation: '{best_row['Scenario']}' yields the highest predicted salary "
        f"at ${best_row['Predicted Salary (USD)']:,.0f}. Differences across scenarios "
        "reflect the combined effect of job title, experience, education, seniority, and country."
    )
    y = draw_wrapped_text(c, bar_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 3: CONFIDENCE INTERVAL CHART =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Salary Confidence Intervals (95%)", left_margin, y, size=14)

    fig_ci, ax_ci = plt.subplots(figsize=(7.5, 4.5))
    ax_ci.errorbar(
        scenarios_df["Scenario"],
        scenarios_df["Predicted Salary (USD)"],
        yerr=[
            scenarios_df["Predicted Salary (USD)"] - scenarios_df["Lower Bound"],
            scenarios_df["Upper Bound"] - scenarios_df["Predicted Salary (USD)"]
        ],
        fmt="o",
        color="#1A4F8A",
        ecolor="#444444",
        capsize=5,
        linewidth=1.4,
        markersize=7
    )
    apply_chart_style(ax_ci)
    ax_ci.set_title("95% Confidence Intervals by Scenario", fontsize=12,
                    fontweight="bold", color="#111111", pad=10)
    ax_ci.set_xlabel("Scenario", fontsize=10, color="#111111", labelpad=6)
    ax_ci.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    plt.xticks(rotation=20)
    img_ci = _fig_to_image(fig_ci)

    y -= image_height + 20
    c.drawImage(img_ci, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    y -= 20
    ci_text = (
        "Interpretation: Error bars represent the 95% confidence interval around each "
        "point estimate. Wider intervals indicate greater uncertainty in the prediction "
        "for that scenario's input configuration."
    )
    y = draw_wrapped_text(c, ci_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 4: SALARY LEVEL + CAREER STAGE BREAKDOWN =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Salary Level & Career Stage Breakdown", left_margin, y, size=14)

    # Salary Level table
    y -= 25
    y = draw_section_header(c, "Salary Level per Scenario", left_margin, y, size=12)

    level_colors = {
        "Early Career Range": "#38BDF8",
        "Professional Range": "#4F8EF7",
        "Executive Range":    "#A78BFA"
    }

    c.setFont("Helvetica", 11)
    for _, row in scenarios_df.iterrows():
        y -= 17
        y = draw_kv_line(
            c,
            f"{row['Scenario']}: {row['Salary Level']}  "
            f"(${row['Predicted Salary (USD)']:,.0f})",
            left_margin, y, offset=10
        )

    # Career Stage table
    y -= 25
    y = draw_section_header(c, "Career Stage per Scenario", left_margin, y, size=12)

    c.setFont("Helvetica", 11)
    for _, row in scenarios_df.iterrows():
        y -= 17
        y = draw_kv_line(
            c,
            f"{row['Scenario']}: {row['Career Stage']}  "
            f"(Exp: {row['Experience (yrs)']} yrs | {row['Education']})",
            left_margin, y, offset=10
        )

    # Salary Level bar chart
    y -= 30
    y = draw_section_header(c, "Predicted Salary Colored by Salary Level", left_margin, y, size=12)

    level_palette = ["#38BDF8", "#4F8EF7", "#A78BFA", "#34D399", "#F59E0B"]
    unique_levels = scenarios_df["Salary Level"].unique().tolist()
    level_color_map = {lvl: level_palette[i % len(level_palette)]
                       for i, lvl in enumerate(unique_levels)}
    bar_colors_level = [level_color_map[lvl] for lvl in scenarios_df["Salary Level"]]

    fig_level, ax_level = plt.subplots(figsize=(7.5, 3.8))
    ax_level.bar(
        scenarios_df["Scenario"],
        scenarios_df["Predicted Salary (USD)"],
        color=bar_colors_level,
        edgecolor="white",
        linewidth=0.7
    )
    apply_chart_style(ax_level)
    ax_level.set_title("Salary by Scenario (Salary Level)", fontsize=12,
                       fontweight="bold", color="#111111", pad=10)
    ax_level.set_xlabel("Scenario", fontsize=10, color="#111111", labelpad=6)
    ax_level.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)

    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=level_color_map[lvl], label=lvl)
                      for lvl in unique_levels]
    ax_level.legend(handles=legend_handles, fontsize=8, loc="upper left")
    plt.xticks(rotation=20)
    img_level = _fig_to_image(fig_level)

    img_h = 240
    y -= img_h + 15
    if y < 60:
        c.showPage()
        y = height - 55
    c.drawImage(img_level, x_position, y, width=image_width, height=img_h,
                preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 5: INSIGHTS =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Insights", left_margin, y, size=14)

    best  = scenarios_df.loc[scenarios_df["Predicted Salary (USD)"].idxmax()]
    worst = scenarios_df.loc[scenarios_df["Predicted Salary (USD)"].idxmin()]
    spread = float(best["Predicted Salary (USD)"] - worst["Predicted Salary (USD)"])

    insight_text = (
        f"The highest predicted salary belongs to '{best['Scenario']}' at "
        f"${best['Predicted Salary (USD)']:,.0f} (Level: {best['Salary Level']}, "
        f"Stage: {best['Career Stage']}), while the lowest belongs to "
        f"'{worst['Scenario']}' at ${worst['Predicted Salary (USD)']:,.0f} "
        f"(Level: {worst['Salary Level']}, Stage: {worst['Career Stage']}). "
        f"The salary spread of ${spread:,.0f} highlights how changes in experience, "
        "education, seniority, job title, and country can significantly shift "
        "predicted compensation outcomes."
    )

    y -= 20
    y = draw_wrapped_text(c, insight_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer


# ==================================================
# APP 2 — PDF: Scenario Analysis
# ==================================================
def app2_generate_scenario_pdf(scenarios_df):
    pd = _pd()
    plt = _plt()

    buffer = BytesIO()
    c = _get_numbered_canvas()(buffer, pagesize=_letter())
    width, height = _letter()

    apply_pdf_metadata(
        c,
        "SalaryScope Scenario Analysis Report",
        "Scenario-based salary comparison generated by SalaryScope"
    )

    left_margin = 50
    right_margin = width - 50
    max_width = right_margin - left_margin
    y = height - 55

    # ================= PAGE 1: HEADER + SUMMARY + SCENARIO LIST =================
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left_margin, y, "SalaryScope")
    y -= 24

    c.setFont("Helvetica", 13)
    c.drawString(left_margin, y, "Scenario Analysis Report")
    y -= 15

    c.setFont("Helvetica", 9)
    c.drawString(left_margin, y, f"Generated on: {_datetime().now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    y = draw_line(c, left_margin, right_margin, y)

    # --- Summary Statistics ---
    sal = scenarios_df["Predicted Salary (USD)"]
    avg_salary = float(sal.mean())
    min_salary = float(sal.min())
    max_salary = float(sal.max())

    y -= 30
    y = draw_section_header(c, "Summary Statistics", left_margin, y, size=14)

    c.setFont("Helvetica", 11)
    y -= 22
    y = draw_kv_line(c, f"Total Scenarios: {len(scenarios_df)}", left_margin, y, offset=10)
    y -= 17
    y = draw_kv_line(c, f"Average Predicted Salary: ${avg_salary:,.2f}", left_margin, y, offset=10)
    y -= 17
    y = draw_kv_line(c, f"Minimum Predicted Salary: ${min_salary:,.2f}", left_margin, y, offset=10)
    y -= 17
    y = draw_kv_line(c, f"Maximum Predicted Salary: ${max_salary:,.2f}", left_margin, y, offset=10)

    # --- Scenario Detail List ---
    y -= 25
    y = draw_section_header(c, "Scenario Details", left_margin, y, size=12)

    c.setFont("Helvetica", 10)
    for _, row in scenarios_df.iterrows():
        y -= 18
        if y < 120:
            c.showPage()
            y = height - 55

        line1 = (
            f"{row['Scenario']} \u2014 {row['Job Title']} | "
            f"{row['Experience Level']} | {row['Employment']} | "
            f"{row['Work Mode']} | {row['Company Size']}"
        )
        y = draw_wrapped_text(c, line1, left_margin + 10, y, max_width - 10)

        y -= 14
        line2 = (
            f"   Residence: {row['Residence']}  |  "
            f"Company Location: {row['Company Location']}  |  "
            f"Predicted: ${row['Predicted Salary (USD)']:,.0f}"
        )
        y = draw_wrapped_text(c, line2, left_margin + 10, y, max_width - 10)
        y -= 6

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 2: PREDICTED SALARY BAR CHART =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Predicted Salary Comparison", left_margin, y, size=14)

    fig_bar, ax_bar = plt.subplots(figsize=(7.5, 4.5))
    ax_bar.bar(
        scenarios_df["Scenario"],
        scenarios_df["Predicted Salary (USD)"],
        color="#1A4F8A",
        edgecolor="white",
        linewidth=0.7
    )
    apply_chart_style(ax_bar)
    ax_bar.set_title("Predicted Annual Salary by Scenario", fontsize=12,
                     fontweight="bold", color="#111111", pad=10)
    ax_bar.set_xlabel("Scenario", fontsize=10, color="#111111", labelpad=6)
    ax_bar.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    plt.xticks(rotation=20)
    img_bar = _fig_to_image(fig_bar)

    image_width = 500
    image_height = 280
    x_position = (width - image_width) / 2
    y -= image_height + 20
    c.drawImage(img_bar, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    best_row = scenarios_df.loc[scenarios_df["Predicted Salary (USD)"].idxmax()]
    y -= 20
    bar_text = (
        f"Interpretation: '{best_row['Scenario']}' yields the highest predicted salary "
        f"at ${best_row['Predicted Salary (USD)']:,.0f}. Differences across scenarios "
        "reflect the combined effect of job title, experience level, employment type, "
        "work mode, company size, and location."
    )
    y = draw_wrapped_text(c, bar_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 3: EXPERIENCE LEVEL BREAKDOWN =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Salary by Experience Level", left_margin, y, size=14)

    exp_order = ["Entry Level", "Mid Level", "Senior Level", "Executive Level"]
    exp_group = (
        scenarios_df.groupby("Experience Level")["Predicted Salary (USD)"]
        .mean()
        .reset_index()
    )
    exp_group["Experience Level"] = pd.Categorical(
        exp_group["Experience Level"],
        categories=exp_order,
        ordered=True
    )
    exp_group = exp_group.sort_values("Experience Level")

    # Text table first
    y -= 22
    c.setFont("Helvetica", 11)
    for _, row in exp_group.iterrows():
        y -= 17
        y = draw_kv_line(
            c,
            f"{row['Experience Level']}: ${row['Predicted Salary (USD)']:,.2f}",
            left_margin, y, offset=10
        )

    # Bar chart
    y -= 25
    fig_exp, ax_exp = plt.subplots(figsize=(7.5, 4.5))
    bar_colors_exp = ["#38BDF8", "#4F8EF7", "#A78BFA", "#F59E0B"]
    ax_exp.bar(
        exp_group["Experience Level"].astype(str),
        exp_group["Predicted Salary (USD)"],
        color=bar_colors_exp[:len(exp_group)],
        edgecolor="white",
        linewidth=0.7
    )
    apply_chart_style(ax_exp)
    ax_exp.set_title("Average Predicted Salary by Experience Level", fontsize=12,
                     fontweight="bold", color="#111111", pad=10)
    ax_exp.set_xlabel("Experience Level", fontsize=10, color="#111111", labelpad=6)
    ax_exp.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    plt.xticks(rotation=20)
    img_exp = _fig_to_image(fig_exp)

    y -= image_height + 20
    if y < 60:
        c.showPage()
        y = height - 55
    c.drawImage(img_exp, x_position, y, width=image_width, height=image_height,
                preserveAspectRatio=True, mask="auto")

    y -= 20
    exp_text = (
        "Interpretation: This chart shows how predicted salary varies across experience "
        "levels for the scenarios defined. Higher seniority levels are generally associated "
        "with greater predicted compensation."
    )
    y = draw_wrapped_text(c, exp_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 4: COMPANY SIZE + WORK MODE BREAKDOWN =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Salary by Company Size & Work Mode", left_margin, y, size=14)

    # Company Size
    y -= 25
    y = draw_section_header(c, "Average Predicted Salary by Company Size", left_margin, y, size=12)

    size_order = ["Small Company", "Medium Company", "Large Company"]
    size_group = (
        scenarios_df.groupby("Company Size")["Predicted Salary (USD)"]
        .mean()
        .reset_index()
    )
    size_group["Company Size"] = pd.Categorical(
        size_group["Company Size"],
        categories=size_order,
        ordered=True
    )
    size_group = size_group.sort_values("Company Size")

    c.setFont("Helvetica", 11)
    for _, row in size_group.iterrows():
        y -= 17
        y = draw_kv_line(
            c,
            f"{row['Company Size']}: ${row['Predicted Salary (USD)']:,.2f}",
            left_margin, y, offset=10
        )

    # Work Mode
    y -= 25
    y = draw_section_header(c, "Average Predicted Salary by Work Mode", left_margin, y, size=12)

    remote_group = (
        scenarios_df.groupby("Work Mode")["Predicted Salary (USD)"]
        .mean()
        .reset_index()
        .sort_values("Predicted Salary (USD)", ascending=False)
    )

    c.setFont("Helvetica", 11)
    for _, row in remote_group.iterrows():
        y -= 17
        y = draw_kv_line(
            c,
            f"{row['Work Mode']}: ${row['Predicted Salary (USD)']:,.2f}",
            left_margin, y, offset=10
        )

    # Company Size bar chart
    y -= 30
    fig_size, ax_size = plt.subplots(figsize=(7.5, 4.0))
    ax_size.bar(
        size_group["Company Size"].astype(str),
        size_group["Predicted Salary (USD)"],
        color=["#38BDF8", "#4F8EF7", "#A78BFA"],
        edgecolor="white",
        linewidth=0.7
    )
    apply_chart_style(ax_size)
    ax_size.set_title("Average Predicted Salary by Company Size", fontsize=12,
                      fontweight="bold", color="#111111", pad=10)
    ax_size.set_xlabel("Company Size", fontsize=10, color="#111111", labelpad=6)
    ax_size.set_ylabel("Predicted Salary (USD)", fontsize=10, color="#111111", labelpad=6)
    plt.xticks(rotation=0)
    img_size = _fig_to_image(fig_size)

    img_h = 240
    y -= img_h + 15
    if y < 60:
        c.showPage()
        y = height - 55
    c.drawImage(img_size, x_position, y, width=image_width, height=img_h,
                preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    # ================= PAGE 5: INSIGHTS =================
    c.showPage()
    y = height - 55

    y = draw_section_header(c, "Insights", left_margin, y, size=14)

    best  = scenarios_df.loc[scenarios_df["Predicted Salary (USD)"].idxmax()]
    worst = scenarios_df.loc[scenarios_df["Predicted Salary (USD)"].idxmin()]
    spread = float(best["Predicted Salary (USD)"] - worst["Predicted Salary (USD)"])

    insight_text = (
        f"The highest predicted salary belongs to '{best['Scenario']}' at "
        f"${best['Predicted Salary (USD)']:,.0f} "
        f"({best['Experience Level']}, {best['Company Size']}, {best['Work Mode']}), "
        f"while the lowest belongs to '{worst['Scenario']}' at "
        f"${worst['Predicted Salary (USD)']:,.0f} "
        f"({worst['Experience Level']}, {worst['Company Size']}, {worst['Work Mode']}). "
        f"The salary spread of ${spread:,.0f} highlights how role, experience level, "
        "company size, and work arrangement can meaningfully influence compensation outcomes."
    )

    y -= 20
    y = draw_wrapped_text(c, insight_text, left_margin, y, max_width)

    c.setFont("Helvetica-Oblique", 9)
    c.drawRightString(right_margin, 30, "Generated by SalaryScope")

    c.save()
    buffer.seek(0)
    return buffer