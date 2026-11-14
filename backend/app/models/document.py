"""Document upload, extraction, and chunk models — session-scoped (anonymous)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    # Owner is an anonymous session id (no login). Column kept as user_id for
    # schema compatibility with existing DBs; no FK to users table.
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    # Original client filename (display only)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    # Safe storage name under upload_dir/{session_id}/
    stored_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    # Relative path from upload_dir (never expose absolute paths to clients)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # pending | processing | ready | failed
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    status_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Optional user category/tag
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Extracted plain text (truncated if huge; full text lives in chunks)
    extracted_text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # JSON: summary, entities, questions from AI
    intelligence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SHA-256 of file bytes for dedup / integrity
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Text segments with location metadata for retrieval and citations."""
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # page | slide | sheet | section
    location_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "Page 3"
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    token_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")
