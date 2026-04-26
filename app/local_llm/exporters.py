"""
PDF export helpers for assistant drafts and conversations.
"""

from __future__ import annotations

from io import BytesIO
import os
import re
import tempfile
from textwrap import wrap

try:
    from markdown_it import MarkdownIt
except Exception:  # pragma: no cover - fallback stays available if the parser is missing
    MarkdownIt = None

try:
    from md2pdf.core import md2pdf as md2pdf_convert
except Exception:  # pragma: no cover - optional preferred exporter
    md2pdf_convert = None

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

HEADING_MARKER = "__PDF_HEADING__::"


#
# PDF formatting layer for assistant content.
# Easy rollback: remove `_prepare_export_text` and `_format_export_timestamp`,
# then pass the original text directly to `_draw_wrapped_text`.
#
def _prepare_export_text_fallback(text: str) -> str:
    cleaned_lines: list[str] = []
    previous_blank = False

    for raw_line in (text or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue

        # Convert markdown-like headings to plain readable section titles.
        if stripped.startswith("#"):
            stripped = re.sub(r"^#+\s*", "", stripped).strip()
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            cleaned_lines.append(HEADING_MARKER + stripped)
            previous_blank = False
            continue

        # Remove light markdown styling while keeping the content readable.
        stripped = re.sub(r"\*\*(.*?)\*\*", r"\1", stripped)
        stripped = re.sub(r"\*(.*?)\*", r"\1", stripped)
        stripped = re.sub(r"`([^`]*)`", r"\1", stripped)

        cleaned_lines.append(stripped)
        previous_blank = False

    return "\n".join(cleaned_lines).strip()


def _render_inline_text(token) -> str:
    if token is None:
        return ""

    children = getattr(token, "children", None) or []
    if not children:
        return str(getattr(token, "content", "") or "")

    parts: list[str] = []
    for child in children:
        child_type = getattr(child, "type", "")
        if child_type in {"softbreak", "hardbreak"}:
            parts.append(" ")
            continue
        if child_type == "code_inline":
            parts.append(str(getattr(child, "content", "") or ""))
            continue
        parts.append(str(getattr(child, "content", "") or ""))
    return "".join(parts).strip()


def _prepare_export_text_markdown(text: str) -> str:
    if MarkdownIt is None:
        return _prepare_export_text_fallback(text)

    parser = MarkdownIt("commonmark")
    tokens = parser.parse(text or "")
    rendered_lines: list[str] = []
    bullet_stack: list[str] = []
    ordered_counters: list[int] = []

    for token in tokens:
        token_type = getattr(token, "type", "")
        tag = getattr(token, "tag", "")

        if token_type == "heading_open":
            if rendered_lines and rendered_lines[-1] != "":
                rendered_lines.append("")
            continue

        if token_type == "heading_close":
            if rendered_lines and rendered_lines[-1] != "":
                rendered_lines.append("")
            continue

        if token_type == "bullet_list_open":
            bullet_stack.append("-")
            continue

        if token_type == "bullet_list_close":
            if bullet_stack:
                bullet_stack.pop()
            if rendered_lines and rendered_lines[-1] != "":
                rendered_lines.append("")
            continue

        if token_type == "ordered_list_open":
            ordered_counters.append(1)
            bullet_stack.append("ordered")
            continue

        if token_type == "ordered_list_close":
            if ordered_counters:
                ordered_counters.pop()
            if bullet_stack:
                bullet_stack.pop()
            if rendered_lines and rendered_lines[-1] != "":
                rendered_lines.append("")
            continue

        if token_type == "inline":
            line = _render_inline_text(token)
            if not line:
                continue

            if tag and tag.startswith("h"):
                rendered_lines.append(HEADING_MARKER + line)
                continue

            if bullet_stack:
                if bullet_stack[-1] == "ordered":
                    prefix = f"{ordered_counters[-1]}. "
                    ordered_counters[-1] += 1
                else:
                    prefix = "- "
                rendered_lines.append(prefix + line)
            else:
                rendered_lines.append(line)
            continue

        if token_type in {"paragraph_close", "blockquote_close"}:
            if rendered_lines and rendered_lines[-1] != "":
                rendered_lines.append("")
            continue

        if token_type == "fence":
            content = str(getattr(token, "content", "") or "").strip()
            if content:
                if rendered_lines and rendered_lines[-1] != "":
                    rendered_lines.append("")
                for code_line in content.splitlines():
                    rendered_lines.append("    " + code_line)
                rendered_lines.append("")

    compact_lines: list[str] = []
    previous_blank = False
    for line in rendered_lines:
        normalized = line.rstrip()
        if not normalized:
            if not previous_blank:
                compact_lines.append("")
            previous_blank = True
            continue
        compact_lines.append(normalized)
        previous_blank = False

    result = "\n".join(compact_lines).strip()
    return result or _prepare_export_text_fallback(text)


def _prepare_export_text(text: str) -> str:
    return _prepare_export_text_markdown(text)


def _format_export_timestamp(value: str) -> str:
    return str(value or "").replace("T", " ").replace("Z", "").strip()


def _try_markdown_to_pdf(markdown_text: str, *, title: str) -> bytes | None:
    if md2pdf_convert is None:
        return None

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            temp_path = handle.name

        md2pdf_convert(
            pdf=temp_path,
            raw=markdown_text,
        )

        with open(temp_path, "rb") as exported:
            return exported.read()
    except Exception:
        return None
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _wrap_pdf_line(line: str, width_chars: int) -> list[tuple[str, str]]:
    stripped = str(line or "").rstrip()
    if not stripped:
        return [("", "normal")]

    if stripped.startswith(HEADING_MARKER):
        heading_text = stripped[len(HEADING_MARKER):].strip()
        wrapped = wrap(
            heading_text,
            width=max(20, width_chars - 2),
        ) or [heading_text or ""]
        return [(item + (":" if idx == len(wrapped) - 1 else ""), "heading") for idx, item in enumerate(wrapped)]

    bullet_match = re.match(r"^-\s+(.*)$", stripped)
    ordered_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
    code_match = re.match(r"^( {4,})(.*)$", line or "")

    if bullet_match:
        wrapped = wrap(
            bullet_match.group(1).strip(),
            width=max(20, width_chars - 4),
            initial_indent="• ",
            subsequent_indent="  ",
        ) or ["• "]
        return [(item, "normal") for item in wrapped]

    if ordered_match:
        marker = f"{ordered_match.group(1)}. "
        wrapped = wrap(
            ordered_match.group(2).strip(),
            width=max(20, width_chars - len(marker)),
            initial_indent=marker,
            subsequent_indent=" " * len(marker),
        ) or [marker.rstrip()]
        return [(item, "normal") for item in wrapped]

    if code_match:
        wrapped = wrap(
            code_match.group(2).rstrip(),
            width=max(20, width_chars - 4),
            initial_indent="    ",
            subsequent_indent="    ",
        ) or ["    "]
        return [(item, "code") for item in wrapped]

    wrapped = wrap(stripped, width=width_chars) or [""]
    return [(item, "normal") for item in wrapped]


def _draw_wrapped_text(pdf: Canvas, text: str, *, x: int, y: int, width_chars: int = 95, line_height: int = 14) -> int:
    lines: list[tuple[str, str]] = []
    for para in (text or "").splitlines() or [""]:
        wrapped = _wrap_pdf_line(para, width_chars)
        lines.extend(wrapped)
    for line, style in lines:
        if y < 72:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 750
        if style == "heading":
            pdf.setFont("Helvetica-Bold", 11)
        elif style == "code":
            pdf.setFont("Courier", 9)
        else:
            pdf.setFont("Helvetica", 10)
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def export_message_pdf(
    *,
    title: str,
    subtitle: str,
    content: str,
) -> bytes:
    markdown_bytes = export_message_markdown(
        title=title,
        subtitle=subtitle,
        content=content,
    )
    preferred_pdf = _try_markdown_to_pdf(markdown_bytes.decode("utf-8"), title=title)
    if preferred_pdf:
        return preferred_pdf

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
    y = _draw_wrapped_text(pdf, _prepare_export_text(content), x=48, y=y)
    pdf.save()
    return buffer.getvalue()


def export_conversation_pdf(
    *,
    title: str,
    subtitle: str,
    messages: list[dict],
) -> bytes:
    markdown_bytes = export_conversation_markdown(
        title=title,
        subtitle=subtitle,
        messages=messages,
    )
    preferred_pdf = _try_markdown_to_pdf(markdown_bytes.decode("utf-8"), title=title)
    if preferred_pdf:
        return preferred_pdf

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
        created = _format_export_timestamp(str(message.get("created_at", "")))
        content = _prepare_export_text(str(message.get("content", "")))

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


def export_message_markdown(
    *,
    title: str,
    subtitle: str,
    content: str,
) -> bytes:
    lines = [f"# {title}", "", subtitle.strip(), "", content.strip(), ""]
    return "\n".join(lines).encode("utf-8")


def export_conversation_markdown(
    *,
    title: str,
    subtitle: str,
    messages: list[dict],
) -> bytes:
    lines = [f"# {title}", "", subtitle.strip(), ""]

    for message in messages:
        role = str(message.get("role", "assistant")).capitalize()
        created = _format_export_timestamp(str(message.get("created_at", "")))
        content = str(message.get("content", "")).strip()
        lines.append(f"## {role}")
        if created:
            lines.append(f"*{created}*")
        lines.append("")
        if content:
            lines.append(content)
        lines.append("")

    return "\n".join(lines).encode("utf-8")
