"""Simple keyword retrieval over user-owned document chunks."""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


@dataclass
class RetrievedChunk:
    document_id: str
    document_name: str
    chunk_id: str
    content: str
    location_label: str | None
    heading: str | None
    score: float


def _tokenize(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{2,}", q.lower()) if t]


def search_user_chunks(
    db: Session,
    user_id: str,
    query: str,
    *,
    document_ids: list[str] | None = None,
    limit: int = 8,
) -> list[RetrievedChunk]:
    tokens = _tokenize(query)
    if not tokens:
        return []

    q = (
        select(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.user_id == user_id, Document.status == "ready")
    )
    if document_ids:
        q = q.where(Document.id.in_(document_ids))

    rows = db.execute(q).all()
    scored: list[RetrievedChunk] = []
    for chunk, doc in rows:
        text_l = (chunk.content or "").lower()
        score = sum(1.0 for t in tokens if t in text_l)
        if chunk.heading:
            score += sum(0.5 for t in tokens if t in chunk.heading.lower())
        if score <= 0:
            continue
        scored.append(
            RetrievedChunk(
                document_id=doc.id,
                document_name=doc.original_filename,
                chunk_id=chunk.id,
                content=chunk.content,
                location_label=chunk.location_label,
                heading=chunk.heading,
                score=score,
            )
        )
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:limit]


def get_document_context(
    db: Session,
    user_id: str,
    document_ids: list[str],
    *,
    max_chars: int = 12000,
) -> str:
    """Concatenate previews/chunks from selected user-owned documents for research context."""
    docs = db.scalars(
        select(Document).where(
            Document.user_id == user_id,
            Document.id.in_(document_ids),
            Document.status == "ready",
        )
    ).all()
    parts: list[str] = []
    total = 0
    for doc in docs:
        header = f"[Uploaded document: {doc.original_filename}]"
        parts.append(header)
        total += len(header)
        chunks = sorted(doc.chunks, key=lambda c: c.chunk_index)
        for ch in chunks:
            loc = f" ({ch.location_label})" if ch.location_label else ""
            piece = f"{loc}\n{ch.content}".strip()
            if total + len(piece) > max_chars:
                remaining = max_chars - total
                if remaining > 100:
                    parts.append(piece[:remaining] + "…")
                return "\n\n".join(parts)
            parts.append(piece)
            total += len(piece)
    return "\n\n".join(parts)
