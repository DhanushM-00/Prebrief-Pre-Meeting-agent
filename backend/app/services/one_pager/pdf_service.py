"""A4 one-page PDF renderer for meeting briefs (ReportLab)."""
from __future__ import annotations

import io
import logging
import re
from typing import Any

from app.schemas.one_pager import OnePageBrief

log = logging.getLogger("prebrief.pdf")

# A4 points
A4_W = 595.27
A4_H = 841.89
MARGIN = 36  # 0.5 inch
CONTENT_TOP = A4_H - MARGIN
CONTENT_BOTTOM = MARGIN + 14  # leave room for footer line
MAX_CONTENT_HEIGHT = CONTENT_TOP - CONTENT_BOTTOM


def _safe(text: str) -> str:
    return (text or "").replace("\x00", "")


def render_one_page_pdf(brief: OnePageBrief) -> tuple[bytes, bool, str | None]:
    """Return (pdf_bytes, page_fits, overflow_note)."""
    try:
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as e:
        raise RuntimeError(
            "reportlab is required for PDF export. Install with: pip install reportlab"
        ) from e

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(A4_W, A4_H))
    width, height = A4_W, A4_H

    ink = HexColor("#111827")
    muted = HexColor("#4B5563")
    line = HexColor("#D1D5DB")
    accent = HexColor("#1D4ED8")
    soft = HexColor("#F3F4F6")

    y = height - MARGIN
    overflow = False
    dropped: list[str] = []

    def space(pts: float) -> None:
        nonlocal y
        y -= pts

    def ensure(pts: float) -> bool:
        """Return False if not enough room for pts of content."""
        return y - pts >= CONTENT_BOTTOM

    def hline() -> None:
        nonlocal y
        c.setStrokeColor(line)
        c.setLineWidth(0.6)
        c.line(MARGIN, y, width - MARGIN, y)
        y -= 8

    def draw_wrapped(text: str, font: str, size: float, color: Any, max_w: float, leading: float) -> None:
        nonlocal y, overflow
        c.setFont(font, size)
        c.setFillColor(color)
        words = _safe(text).split()
        line_parts: list[str] = []
        while words:
            trial = (" ".join(line_parts + [words[0]])).strip()
            if c.stringWidth(trial, font, size) <= max_w or not line_parts:
                line_parts.append(words.pop(0))
            else:
                if not ensure(leading):
                    overflow = True
                    return
                c.drawString(MARGIN, y - size, " ".join(line_parts))
                y -= leading
                line_parts = []
        if line_parts:
            if not ensure(leading):
                overflow = True
                return
            c.drawString(MARGIN, y - size, " ".join(line_parts))
            y -= leading

    def section_title(title: str) -> None:
        nonlocal y
        if not ensure(18):
            return
        c.setFillColor(accent)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN, y - 10, title.upper())
        y -= 14
        c.setStrokeColor(accent)
        c.setLineWidth(1)
        c.line(MARGIN, y, MARGIN + 48, y)
        y -= 8

    # ---- Header ----
    c.setFillColor(ink)
    name = _safe(brief.entity_name)
    if len(name) > 48:
        name = name[:45] + "…"
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, y - 14, name)
    y -= 18

    c.setFont("Helvetica", 8)
    c.setFillColor(muted)
    meta = (
        f"{brief.entity_type.capitalize()}  ·  Meeting {_safe(brief.meeting_at)[:16]}  ·  "
        f"Research {_safe(brief.research_window_start)[:10]} – {_safe(brief.research_window_end)[:10]}  ·  "
        f"Generated {_safe(brief.generated_at)[:10]}"
    )
    c.drawString(MARGIN, y - 8, meta)
    y -= 14
    hline()

    # ---- A Executive snapshot ----
    section_title("A · Executive snapshot")
    draw_wrapped(brief.executive_snapshot, "Helvetica", 9, ink, width - 2 * MARGIN, 12)
    space(4)

    # ---- B Last 30 days ----
    section_title("B · Last 30 days")

    def bullets(label: str, items: list, empty_msg: str) -> None:
        nonlocal y, overflow
        if not ensure(12):
            overflow = True
            dropped.append(label)
            return
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(ink)
        c.drawString(MARGIN, y - 8, label)
        y -= 11
        if not items:
            draw_wrapped(empty_msg, "Helvetica-Oblique", 8, muted, width - 2 * MARGIN, 10)
            return
        for b in items:
            prefix = "• "
            txt = prefix + _safe(b.text)
            draw_wrapped(txt, "Helvetica", 8, ink, width - 2 * MARGIN - 4, 10)
            if overflow:
                dropped.append(label)
                return
        space(2)

    bullets("News", brief.news, "No verified news items in the research window.")
    bullets(
        "Hires & leadership",
        brief.hires_and_leadership,
        "No verified hires or leadership changes in the research window.",
    )
    bullets(
        "Product & service launches",
        brief.product_and_service_launches,
        "No verified product or service launches in the research window.",
    )
    space(2)

    # ---- C What matters ----
    section_title("C · What matters for this meeting")
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(muted)
    if ensure(10):
        c.drawString(MARGIN, y - 7, "Analytical notes — not verified facts")
        y -= 10
    for b in brief.what_matters:
        draw_wrapped("• " + _safe(b.text), "Helvetica", 8, ink, width - 2 * MARGIN, 10)
        if overflow:
            dropped.append("what_matters")
            break
    space(2)

    # ---- D Open questions ----
    section_title("D · Open questions")
    for i, q in enumerate(brief.open_questions, 1):
        draw_wrapped(f"{i}. {_safe(q)}", "Helvetica", 8, ink, width - 2 * MARGIN, 10)
        if overflow:
            dropped.append("questions")
            break
    space(4)

    # ---- Footer: citations + limitations ----
    if ensure(20):
        hline()
        section_title("Sources")
        for cit in brief.citations[:12]:
            if not ensure(11):
                overflow = True
                break
            label = f"[{cit.index}] {_safe(cit.publisher)} — {_truncate_title(cit.title, 70)}"
            c.setFont("Helvetica", 7)
            c.setFillColor(accent)
            # Clickable link
            c.drawString(MARGIN, y - 7, label)
            try:
                c.linkURL(cit.url, (MARGIN, y - 9, width - MARGIN, y + 1), relative=0)
            except Exception:
                pass
            y -= 10

    if brief.limitations and ensure(16):
        space(2)
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(muted)
        c.drawString(MARGIN, y - 7, "Coverage limitations")
        y -= 10
        for lim in brief.limitations[:4]:
            draw_wrapped("• " + _safe(lim), "Helvetica", 7, muted, width - 2 * MARGIN, 9)
            if overflow:
                break

    # Page footer stamp
    c.setFont("Helvetica", 6)
    c.setFillColor(muted)
    c.drawString(MARGIN, 18, "PreBrief · One-page meeting brief · Citations link to original sources")
    c.drawRightString(width - MARGIN, 18, "Page 1 of 1")

    c.showPage()
    c.save()
    data = buf.getvalue()

    # Post-render page-count inspection (never claim one page if PDF has more)
    page_count = 1
    try:
        from pypdf import PdfReader

        page_count = len(PdfReader(io.BytesIO(data)).pages)
    except Exception:
        page_count = 1

    note = None
    fits = (not overflow) and page_count == 1 and not dropped
    if page_count != 1:
        note = (
            f"PDF has {page_count} pages; one-page requirement not met. "
            "Reduce meeting context or request a shorter configuration."
        )
        fits = False
    elif overflow or dropped:
        note = (
            "Content was reduced to attempt a single A4 page; some lower-priority lines were "
            "condensed or omitted. Citations for retained claims were preserved."
        )
        # Still one physical page — acceptable if sections remain
        fits = page_count == 1
    return data, fits, note


def _truncate_title(t: str, n: int) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"
