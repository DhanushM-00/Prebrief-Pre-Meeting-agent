"""Wire models for document upload and intelligence."""
from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.base import WireModel


class DocumentOut(WireModel):
    id: str
    original_filename: str
    content_type: str
    extension: str
    size_bytes: int
    status: str
    status_message: str | None = None
    category: str | None = None
    page_count: int | None = None
    word_count: int | None = None
    has_extracted_text: bool = False
    has_intelligence: bool = False
    created_at: str
    processed_at: str | None = None


class DocumentDetailOut(DocumentOut):
    extracted_text_preview: str | None = None
    intelligence: dict[str, Any] | None = None


class DocumentListOut(WireModel):
    items: list[DocumentOut]
    total: int


class DocumentChatRequest(WireModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] | None = None


class CitationOut(WireModel):
    document_id: str | None = None
    document_name: str | None = None
    location: str | None = None
    excerpt: str | None = None


class DocumentChatResponse(WireModel):
    answer: str
    citations: list[CitationOut] = Field(default_factory=list)
    provider: str = "stub"


class ReprocessResponse(WireModel):
    id: str
    status: str
    message: str


class MessageResponse(WireModel):
    message: str
