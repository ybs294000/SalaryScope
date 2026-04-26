"""
PDF export helpers for assistant drafts and conversations.
"""

from __future__ import annotations

from io import BytesIO
from textwrap import wrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas


def _draw_wrapped_text(pdf: Canvas, text: str, *, x: int, y: int, width_chars: int = 95, line_height: int = 14) -> int:
    lines = []
    for para in (text or "").splitlines() or [""]:
        wrapped = wrap(para, width=width_chars) or [""]
        lines.extend(wrapped)
    for line in lines:
        if y < 72:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 750
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def export_message_pdf(
    *,
    title: str,
    subtitle: str,
    content: str,
) -> bytes:
    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=letter)
    pdf.setTitle(title)

    y = 760
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(48, y, title)
    y -= 24

    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, y, subtitle)
    y -= 28

    pdf.setFont("Helvetica", 10)
    y = _draw_wrapped_text(pdf, content, x=48, y=y)
    pdf.save()
    return buffer.getvalue()


def export_conversation_pdf(
    *,
    title: str,
    subtitle: str,
    messages: list[dict],
) -> bytes:
    buffer = BytesIO()
    pdf = Canvas(buffer, pagesize=letter)
    pdf.setTitle(title)

    y = 760
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(48, y, title)
    y -= 24

    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, y, subtitle)
    y -= 28

    for message in messages:
        role = str(message.get("role", "assistant")).capitalize()
        created = str(message.get("created_at", ""))
        content = str(message.get("content", ""))

        if y < 96:
            pdf.showPage()
            y = 760

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(48, y, f"{role}  {created}")
        y -= 18

        pdf.setFont("Helvetica", 10)
        y = _draw_wrapped_text(pdf, content, x=56, y=y)
        y -= 12

    pdf.save()
    return buffer.getvalue()
