"""Professional multi-page research report PDF generator (ReportLab)."""
from __future__ import annotations

import io
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("prebrief.reports.pdf")

A4_W = 595.27
A4_H = 841.89
MARGIN = 48


def _safe(text: str) -> str:
    return (text or "").replace("\x00", "").replace("\r", "")


def render_research_report_pdf(
    payload: dict[str, Any],
    *,
    title: str | None = None,
    include_sources: bool = True,
    include_timeline: bool = True,
    include_intelligence: bool = True,
    meeting_context: str | None = None,
) -> bytes:
    """Generate a multi-page professional research report PDF from a research result dict."""
    try:
        from reportlab.lib.colors import HexColor, white
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit
    except ImportError as e:
        raise RuntimeError("reportlab is required: pip install reportlab") from e

    entity = payload.get("entity_name") or "Subject"
    entity_type = payload.get("entity_type") or "company"
    window_days = payload.get("window_days") or 30
    window_start = (payload.get("window_start") or "")[:10]
    window_end = (payload.get("window_end") or "")[:10]
    generated_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    findings = payload.get("findings") or []
    sources = payload.get("sources") or []
    open_questions = payload.get("open_questions") or []
    gaps = payload.get("gaps") or []
    contradictions = payload.get("contradictions") or []
    timeline = payload.get("timeline") or []
    evidence = payload.get("evidence") or []
    company_intel = payload.get("company_intelligence")
    person_intel = payload.get("person_intelligence")
    depth = payload.get("research_depth") or "standard"
    report_title = title or f"Research Report — {entity}"

    ink = HexColor("#111827")
    muted = HexColor("#4B5563")
    line = HexColor("#E5E7EB")
    accent = HexColor("#1D4ED8")
    soft = HexColor("#F8FAFC")
    header_bg = HexColor("#0F172A")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(A4_W, A4_H))
    page_num = 0

    def new_page() -> float:
        nonlocal page_num
        if page_num > 0:
            _footer(c, page_num, entity)
            c.showPage()
        page_num += 1
        return A4_H - MARGIN

    def _footer(cv, num: int, subject: str) -> None:
        cv.setStrokeColor(line)
        cv.setLineWidth(0.5)
        cv.line(MARGIN, 32, A4_W - MARGIN, 32)
        cv.setFont("Helvetica", 8)
        cv.setFillColor(muted)
        cv.drawString(MARGIN, 20, f"PreBrief · {subject[:40]}")
        cv.drawRightString(A4_W - MARGIN, 20, f"Page {num}")

    def heading(y: float, text: str, size: float = 14) -> float:
        c.setFont("Helvetica-Bold", size)
        c.setFillColor(ink)
        c.drawString(MARGIN, y, _safe(text))
        return y - size - 10

    def body(y: float, text: str, size: float = 9.5, leading: float = 13, max_w: float | None = None) -> float:
        max_w = max_w or (A4_W - 2 * MARGIN)
        c.setFont("Helvetica", size)
        c.setFillColor(ink)
        lines = simpleSplit(_safe(text), "Helvetica", size, max_w)
        for ln in lines:
            if y < MARGIN + 40:
                y = new_page()
                c.setFont("Helvetica", size)
                c.setFillColor(ink)
            c.drawString(MARGIN, y, ln)
            y -= leading
        return y

    def bullet(y: float, text: str, size: float = 9) -> float:
        if y < MARGIN + 40:
            y = new_page()
        c.setFont("Helvetica", size)
        c.setFillColor(ink)
        max_w = A4_W - 2 * MARGIN - 14
        lines = simpleSplit(_safe(text), "Helvetica", size, max_w)
        for i, ln in enumerate(lines):
            if y < MARGIN + 40:
                y = new_page()
                c.setFont("Helvetica", size)
            prefix = "•  " if i == 0 else "   "
            c.drawString(MARGIN, y, prefix + ln)
            y -= 12
        return y - 2

    # ---- Cover ----
    y = new_page()
    c.setFillColor(header_bg)
    c.rect(0, A4_H - 160, A4_W, 160, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGIN, A4_H - 70, _safe(report_title)[:70])
    c.setFont("Helvetica", 11)
    c.drawString(MARGIN, A4_H - 95, f"{entity_type.title()} research  ·  {depth.title()} depth  ·  {window_days}-day window")
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, A4_H - 115, f"Window: {window_start} → {window_end}")
    c.drawString(MARGIN, A4_H - 130, f"Generated: {str(generated_at)[:19].replace('T', ' ')} UTC")
    if meeting_context:
        c.drawString(MARGIN, A4_H - 145, f"Context: {_safe(meeting_context)[:90]}")

    y = A4_H - 190
    y = heading(y, "Executive summary", 13)
    n_findings = len(findings)
    n_sources = len(sources)
    summary = (
        f"This report covers public web research on {entity} over the {window_days}-day window "
        f"ending {window_end or 'the meeting date'}. "
        f"{n_findings} findings were retained from {n_sources} sources after date, entity, and "
        f"deduplication filters. Claims without evidence are excluded."
    )
    y = body(y, summary)
    y -= 8

    if gaps:
        y = heading(y, "Information gaps", 11)
        for g in gaps[:6]:
            y = bullet(y, str(g))
        y -= 6

    if contradictions:
        y = heading(y, "Conflicting reports", 11)
        for g in contradictions[:4]:
            y = bullet(y, str(g))
        y -= 6

    # ---- Findings by category ----
    y = heading(y, "Key findings", 13)
    by_cat: dict[str, list] = {}
    for f in findings:
        cat = (f.get("category") if isinstance(f, dict) else getattr(f, "category", None)) or "news"
        by_cat.setdefault(str(cat), []).append(f)

    for cat, items in by_cat.items():
        if y < MARGIN + 80:
            y = new_page()
        y = heading(y, cat.replace("_", " ").title(), 11)
        for f in items[:8]:
            statement = f.get("statement") if isinstance(f, dict) else getattr(f, "statement", "")
            conf = f.get("confidence") if isinstance(f, dict) else getattr(f, "confidence", "")
            date = f.get("event_date") if isinstance(f, dict) else getattr(f, "event_date", None)
            prefix = f"[{date}] " if date else ""
            y = bullet(y, f"{prefix}{statement}  (confidence: {conf})")
        y -= 4

    # ---- Intelligence profile ----
    intel = company_intel if entity_type == "company" else person_intel
    if include_intelligence and intel and isinstance(intel, dict):
        y = new_page() if y < MARGIN + 120 else y
        y = heading(y, "Intelligence profile", 13)
        for key, label in [
            ("overview", "Overview"),
            ("professional_bio", "Professional background"),
            ("current_role", "Current role"),
            ("business_model", "Business model"),
            ("industry", "Industry"),
        ]:
            val = intel.get(key)
            if val and isinstance(val, str):
                y = heading(y, label, 10)
                y = body(y, val)
                y -= 4
        for key, label in [
            ("leadership", "Leadership"),
            ("founders", "Founders"),
            ("products_services", "Products & services"),
            ("funding", "Funding"),
            ("partnerships", "Partnerships"),
            ("competitors", "Competitors"),
            ("risks", "Risks"),
            ("opportunities", "Opportunities"),
            ("career_timeline", "Career timeline"),
            ("recent_activities", "Recent activities"),
            ("achievements", "Achievements"),
            ("public_statements", "Public statements"),
        ]:
            val = intel.get(key) or []
            if isinstance(val, str):
                val = [val] if val else []
            if not val:
                continue
            y = heading(y, label, 10)
            for item in val[:6]:
                y = bullet(y, str(item))
            y -= 4

    # ---- Timeline ----
    if include_timeline and timeline:
        y = new_page() if y < MARGIN + 100 else y
        y = heading(y, "Timeline", 13)
        for ev in timeline[:25]:
            if not isinstance(ev, dict):
                continue
            date = ev.get("date") or ""
            title_ev = ev.get("title") or ""
            cat = ev.get("category") or ""
            ver = ev.get("verification_status") or ""
            y = bullet(y, f"{date[:10]}  ·  {title_ev}  [{cat}, {ver}]")

    # ---- Open questions ----
    if open_questions:
        y = new_page() if y < MARGIN + 80 else y
        y = heading(y, "Open questions", 13)
        for i, oq in enumerate(open_questions[:10], 1):
            q = oq.get("question") if isinstance(oq, dict) else getattr(oq, "question", "")
            why = oq.get("rationale") if isinstance(oq, dict) else getattr(oq, "rationale", "")
            y = bullet(y, f"{i}. {q}")
            if why:
                y = body(y, f"   Why: {why}", size=8, leading=11)
            y -= 2

    # ---- Sources ----
    if include_sources and sources:
        y = new_page()
        y = heading(y, "Sources", 13)
        y = body(y, "Every factual claim in this report is tied to at least one of the sources below.", size=9)
        y -= 6
        for i, s in enumerate(sources[:40], 1):
            if not isinstance(s, dict):
                continue
            headline = s.get("headline") or ""
            pub = s.get("publisher") or ""
            url = s.get("url") or ""
            published = (s.get("published_at") or "")[:10]
            cred = s.get("credibility") or ""
            y = bullet(y, f"[{i}] {headline}")
            y = body(y, f"    {pub} · {published} · credibility: {cred}", size=8, leading=10)
            if url:
                y = body(y, f"    {url}", size=7.5, leading=10)
            y -= 3

    # ---- Disclaimer ----
    y = new_page() if y < MARGIN + 60 else y - 10
    y = heading(y, "Methodology & limits", 11)
    notes = payload.get("grounding_notes") or []
    for n in notes[:6]:
        y = bullet(y, str(n))
    y = bullet(
        y,
        "This report uses only publicly available web sources collected in the configured window. "
        "It does not invent facts, statistics, or quotations. Private or sensitive personal data is excluded.",
    )

    _footer(c, page_num, entity)
    c.save()
    return buf.getvalue()
