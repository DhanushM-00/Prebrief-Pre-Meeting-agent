"""Document upload, library, intelligence, and chat endpoints (user-scoped)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select

from app.config import get_settings
from app.dependencies import AnonymousSessionId, DbSession
from app.models.document import Document
from app.schemas.documents import (
    DocumentChatRequest,
    DocumentChatResponse,
    DocumentDetailOut,
    DocumentListOut,
    DocumentOut,
    MessageResponse,
    ReprocessResponse,
)
from app.services.documents.intelligence import answer_document_question
from app.services.documents.pipeline import process_document, user_storage_usage
from app.services.documents.retrieval import get_document_context, search_user_chunks
from app.services.documents.upload import delete_document_files, resolve_storage_path, save_bytes
from app.services.documents.validation import validate_upload

router = APIRouter(tags=["documents"])


def _doc_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        extension=doc.extension,
        size_bytes=doc.size_bytes,
        status=doc.status,
        status_message=doc.status_message,
        category=doc.category,
        page_count=doc.page_count,
        word_count=doc.word_count,
        has_extracted_text=bool(doc.extracted_text_preview) or doc.status == "ready",
        has_intelligence=bool(doc.intelligence_json),
        created_at=doc.created_at.isoformat() if doc.created_at else "",
        processed_at=doc.processed_at.isoformat() if doc.processed_at else None,
    )


def _owned(db, user_id: str, doc_id: str) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == doc_id, Document.user_id == user_id)
    )


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    session_id: AnonymousSessionId,
    db: DbSession,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
):
    settings = get_settings()
    data = await file.read()
    head = data[:16]
    result = validate_upload(
        filename=file.filename or "upload",
        content_type=file.content_type,
        size=len(data),
        head_bytes=head,
        settings=settings,
    )
    if not result.ok:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "validation_error", "message": result.error}},
        )

    count, used = user_storage_usage(db, session_id)
    if count >= settings.max_files_per_user:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "quota_exceeded", "message": "File count quota exceeded."}},
        )
    if used + len(data) > settings.max_storage_bytes_per_user:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "quota_exceeded", "message": "Storage quota exceeded."}},
        )

    try:
        stored, rel, content_hash = save_bytes(
            settings, session_id, file.filename or "upload", result.extension, data
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "validation_error", "message": str(e)}},
        )

    doc = Document(
        user_id=session_id,
        original_filename=file.filename or stored,
        stored_filename=stored,
        storage_path=rel,
        content_type=result.content_type,
        extension=result.extension,
        size_bytes=len(data),
        status="pending",
        category=(category or "").strip()[:64] or None,
        content_hash=content_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process synchronously for prototype (background task can replace this)
    doc = await process_document(db, doc, settings)
    return _doc_out(doc)


@router.get("/documents", response_model=DocumentListOut)
def list_documents(
    session_id: AnonymousSessionId,
    db: DbSession,
    q: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = select(Document).where(Document.user_id == session_id)
    if status:
        query = query.where(Document.status == status)
    if category:
        query = query.where(Document.category == category)
    if q:
        like = f"%{q}%"
        query = query.where(Document.original_filename.ilike(like))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Document.created_at.desc()).offset(max(0, offset)).limit(min(limit, 100))
    ).all()
    return DocumentListOut(items=[_doc_out(d) for d in rows], total=int(total))


@router.get("/documents/{doc_id}", response_model=DocumentDetailOut)
def get_document(doc_id: str, session_id: AnonymousSessionId, db: DbSession):
    doc = _owned(db, session_id, doc_id)
    if not doc:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Document not found."}},
        )
    intel = None
    if doc.intelligence_json:
        try:
            intel = json.loads(doc.intelligence_json)
        except json.JSONDecodeError:
            intel = None
    base = _doc_out(doc)
    return DocumentDetailOut(
        **base.model_dump(),
        extracted_text_preview=doc.extracted_text_preview,
        intelligence=intel,
    )


@router.delete("/documents/{doc_id}", response_model=MessageResponse)
def delete_document(doc_id: str, session_id: AnonymousSessionId, db: DbSession):
    settings = get_settings()
    doc = _owned(db, session_id, doc_id)
    if not doc:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Document not found."}},
        )
    delete_document_files(settings, doc.storage_path)
    db.delete(doc)
    db.commit()
    return MessageResponse(message="Document deleted.")


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: str, session_id: AnonymousSessionId, db: DbSession):
    settings = get_settings()
    doc = _owned(db, session_id, doc_id)
    if not doc:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Document not found."}},
        )
    try:
        path = resolve_storage_path(settings, doc.storage_path)
    except ValueError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "File missing on disk."}},
        )
    if not path.is_file():
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "File missing on disk."}},
        )
    return FileResponse(
        path,
        media_type=doc.content_type,
        filename=doc.original_filename,
    )


@router.post("/documents/{doc_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_document(doc_id: str, session_id: AnonymousSessionId, db: DbSession):
    settings = get_settings()
    doc = _owned(db, session_id, doc_id)
    if not doc:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Document not found."}},
        )
    doc = await process_document(db, doc, settings)
    return ReprocessResponse(id=doc.id, status=doc.status, message=doc.status_message or "ok")


@router.post("/documents/chat", response_model=DocumentChatResponse)
async def document_chat(body: DocumentChatRequest, session_id: AnonymousSessionId, db: DbSession):
    settings = get_settings()
    hits = search_user_chunks(
        db,
        session_id,
        body.question,
        document_ids=body.document_ids,
        limit=8,
    )
    chunks = [
        {
            "document_id": h.document_id,
            "document_name": h.document_name,
            "content": h.content,
            "location_label": h.location_label,
        }
        for h in hits
    ]
    result = await answer_document_question(body.question, chunks, settings)
    return DocumentChatResponse(
        answer=result["answer"],
        citations=[
            {
                "document_id": c.get("document_id"),
                "document_name": c.get("document_name"),
                "location": c.get("location"),
                "excerpt": c.get("excerpt"),
            }
            for c in result.get("citations", [])
        ],
        provider=result.get("provider", "stub"),
    )


@router.get("/documents/context/preview")
def context_preview(
    session_id: AnonymousSessionId,
    db: DbSession,
    ids: str = "",
):
    """Return concatenated context for selected document IDs (for briefing form)."""
    id_list = [x.strip() for x in ids.split(",") if x.strip()]
    if not id_list:
        return {"context": "", "documents": []}
    ctx = get_document_context(db, session_id, id_list)
    docs = db.scalars(
        select(Document).where(Document.user_id == session_id, Document.id.in_(id_list))
    ).all()
    return {
        "context": ctx[:2000],
        "documents": [{"id": d.id, "name": d.original_filename, "status": d.status} for d in docs],
    }
