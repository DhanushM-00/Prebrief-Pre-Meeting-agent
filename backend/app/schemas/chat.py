"""Chat / agent conversation schemas grounded in research evidence."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import WireModel


class ChatMessageIn(WireModel):
    role: Literal["user", "agent"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(WireModel):
    """Ask the research agent a question about a research session or briefing payload."""

    question: str = Field(min_length=1, max_length=2000)
    research_session_id: str | None = Field(default=None, max_length=36)
    # Optional fallback: client can send a compact briefing snapshot when session id is absent
    entity_name: str | None = Field(default=None, max_length=200)
    history: list[ChatMessageIn] = Field(default_factory=list, max_length=20)


class ChatCitationOut(WireModel):
    id: str
    title: str
    url: str | None = None
    publisher: str | None = None


class ChatResponse(WireModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    citation_details: list[ChatCitationOut] = Field(default_factory=list)
    grounded: bool = True
    research_session_id: str | None = None
