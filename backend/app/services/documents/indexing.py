"""Persist chunks for a document after extraction."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.documents.chunking import ChunkDraft


def index_document(db: Session, document: Document, drafts: list[ChunkDraft]) -> int:
    """Replace existing chunks with new drafts. Returns chunk count."""
    # Clear old chunks
    for ch in list(document.chunks):
        db.delete(ch)
    db.flush()
    for d in drafts:
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=d.chunk_index,
                content=d.content,
                location_type=d.location_type,
                location_label=d.location_label,
                heading=d.heading,
                token_estimate=d.token_estimate,
            )
        )
    db.flush()
    return len(drafts)
