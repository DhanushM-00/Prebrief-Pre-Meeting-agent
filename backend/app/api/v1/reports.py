"""Professional report generation, multi-format export, and saved reports."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import AnonymousSessionId
from app.models.report import SavedReport
from app.models.research import ResearchSession
from app.schemas.base import WireModel
from app.services.reports import (
    render_research_report_pdf,
    research_to_csv_rows,
    research_to_markdown,
    research_to_print_html,
)

router = APIRouter(tags=["reports"])

ExportFormat = Literal["pdf", "json", "csv", "markdown", "html"]


class ReportGenerateRequest(WireModel):
    research_session_id: str = Field(min_length=1, max_length=36)
    title: str | None = Field(default=None, max_length=300)
    include_sources: bool = True
    include_timeline: bool = True
    include_intelligence: bool = True
    meeting_context: str | None = Field(default=None, max_length=2000)
    format: ExportFormat = "pdf"
    save: bool = False


class SavedReportOut(WireModel):
    id: str
    title: str
    report_type: str
    format: str
    entity_name: str
    research_session_id: str | None = None
    created_at: str
    updated_at: str


class SavedReportListOut(WireModel):
    reports: list[SavedReportOut]
    total: int


def _load_research(db: Session, research_id: str, owner: str) -> dict[str, Any]:
    row = db.get(ResearchSession, research_id)
    if row is None or (row.user_id and row.user_id != owner):
        raise HTTPException(status_code=404, detail="Research session not found")
    if not row.result_json:
        raise HTTPException(status_code=404, detail="Research session has no result")
    try:
        return json.loads(row.result_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid research payload: {e}") from e


def _filename(entity: str, fmt: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (entity or "report"))[:40]
    return f"prebrief_{safe}.{fmt if fmt != 'markdown' else 'md'}"


@router.post("/reports/generate")
async def generate_report(
    req: ReportGenerateRequest,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
) -> Response:
    """Generate a professional report in the requested format from a research session."""
    payload = _load_research(db, req.research_session_id, session_id)
    entity = payload.get("entity_name") or "report"
    title = req.title or f"Research Report — {entity}"

    if req.format == "pdf":
        pdf_bytes = render_research_report_pdf(
            payload,
            title=title,
            include_sources=req.include_sources,
            include_timeline=req.include_timeline,
            include_intelligence=req.include_intelligence,
            meeting_context=req.meeting_context,
        )
        if req.save:
            _save_report(db, session_id, req.research_session_id, title, "research", "pdf", entity, payload)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "pdf")}"'},
        )

    if req.format == "json":
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        if req.save:
            _save_report(db, session_id, req.research_session_id, title, "research", "json", entity, payload)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "json")}"'},
        )

    if req.format == "csv":
        csv_text = research_to_csv_rows(payload)
        if req.save:
            _save_report(db, session_id, req.research_session_id, title, "research", "csv", entity, payload)
        return Response(
            content=csv_text.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "csv")}"'},
        )

    if req.format == "markdown":
        md = research_to_markdown(payload)
        if req.save:
            _save_report(db, session_id, req.research_session_id, title, "research", "markdown", entity, payload)
        return Response(
            content=md.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "md")}"'},
        )

    if req.format == "html":
        html = research_to_print_html(payload)
        if req.save:
            _save_report(db, session_id, req.research_session_id, title, "research", "html", entity, payload)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'inline; filename="{_filename(entity, "html")}"'},
        )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {req.format}")


def _save_report(
    db: Session,
    owner: str,
    research_id: str | None,
    title: str,
    report_type: str,
    fmt: str,
    entity: str,
    payload: dict,
) -> SavedReport:
    row = SavedReport(
        user_id=owner,
        research_session_id=research_id,
        title=title[:300],
        report_type=report_type,
        format=fmt,
        entity_name=entity[:200],
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/reports", response_model=SavedReportListOut)
async def list_reports(
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
) -> SavedReportListOut:
    rows = list(
        db.scalars(
            select(SavedReport)
            .where(SavedReport.user_id == session_id)
            .order_by(desc(SavedReport.created_at))
            .limit(limit)
        )
    )
    out = [
        SavedReportOut(
            id=r.id,
            title=r.title,
            report_type=r.report_type,
            format=r.format,
            entity_name=r.entity_name,
            research_session_id=r.research_session_id,
            created_at=r.created_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            if r.created_at
            else "",
            updated_at=r.updated_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            if r.updated_at
            else "",
        )
        for r in rows
    ]
    return SavedReportListOut(reports=out, total=len(out))


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
    format: ExportFormat | None = Query(default=None),
) -> Response:
    row = db.get(SavedReport, report_id)
    if row is None or (row.user_id and row.user_id != session_id):
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        payload = json.loads(row.payload_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    fmt = format or row.format or "json"
    entity = row.entity_name or "report"
    title = row.title

    if fmt == "pdf":
        pdf_bytes = render_research_report_pdf(payload, title=title)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "pdf")}"'},
        )
    if fmt == "markdown":
        return Response(
            content=research_to_markdown(payload).encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "md")}"'},
        )
    if fmt == "csv":
        return Response(
            content=research_to_csv_rows(payload).encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "csv")}"'},
        )
    if fmt == "html":
        return Response(
            content=research_to_print_html(payload).encode("utf-8"),
            media_type="text/html; charset=utf-8",
        )
    body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{_filename(entity, "json")}"'},
    )


@router.patch("/reports/{report_id}", response_model=SavedReportOut)
async def rename_report(
    report_id: str,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
    title: str = Query(..., min_length=1, max_length=300),
) -> SavedReportOut:
    row = db.get(SavedReport, report_id)
    if row is None or (row.user_id and row.user_id != session_id):
        raise HTTPException(status_code=404, detail="Report not found")
    row.title = title
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return SavedReportOut(
        id=row.id,
        title=row.title,
        report_type=row.report_type,
        format=row.format,
        entity_name=row.entity_name,
        research_session_id=row.research_session_id,
        created_at=row.created_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        if row.created_at
        else "",
        updated_at=row.updated_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        if row.updated_at
        else "",
    )


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    row = db.get(SavedReport, report_id)
    if row is None or (row.user_id and row.user_id != session_id):
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": report_id}
