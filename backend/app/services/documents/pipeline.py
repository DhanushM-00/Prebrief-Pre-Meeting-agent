"""End-to-end process: extract → chunk → index → optional AI intelligence."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.document import Document
from app.services.documents.chunking import chunk_extracted
from app.services.documents.extraction import extract_document
from app.services.documents.indexing import index_document
from app.services.documents.intelligence import analyze_document
from app.services.documents.upload import resolve_storage_path

log = logging.getLogger("prebrief.documents")


def user_storage_usage(db: Session, user_id: str) -> tuple[int, int]:
    """Return (file_count, total_bytes) for active documents."""
    count = db.scalar(
        select(func.count()).select_from(Document).where(Document.user_id == user_id)
    ) or 0
    total = db.scalar(
        select(func.coalesce(func.sum(Document.size_bytes), 0)).where(Document.user_id == user_id)
    ) or 0
    return int(count), int(total)


async def process_document(db: Session, doc: Document, settings: Settings) -> Document:
    doc.status = "processing"
    doc.status_message = "Extracting text…"
    db.commit()

    try:
        path = resolve_storage_path(settings, doc.storage_path)
        result = extract_document(path, doc.extension, enable_ocr=settings.enable_ocr)
        if result.error and not result.blocks:
            doc.status = "failed"
            doc.status_message = result.error[:500]
            db.commit()
            return doc

        drafts = chunk_extracted(result)
        index_document(db, doc, drafts)

        full_text = result.full_text
        preview = full_text[:4000] if full_text else None
        doc.extracted_text_preview = preview
        doc.page_count = result.page_count
        doc.word_count = len(full_text.split()) if full_text else 0

        doc.status_message = "Running document intelligence…"
        db.commit()

        intel = await analyze_document(full_text or "", doc.original_filename, settings)
        doc.intelligence_json = json.dumps(intel)

        doc.status = "ready"
        doc.status_message = None
        doc.processed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        log.exception("process_document failed id=%s", doc.id)
        doc.status = "failed"
        doc.status_message = str(e)[:500]
        db.commit()
        return doc
