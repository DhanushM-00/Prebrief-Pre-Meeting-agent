"""Persist research sessions, sources, findings, and claim links."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    entity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    meeting_at: Mapped[str] = mapped_column(String(40), nullable=False)
    window_start: Mapped[str] = mapped_column(String(40), nullable=False)
    window_end: Mapped[str] = mapped_column(String(40), nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, default=30)
    meeting_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    sources: Mapped[list[ResearchSourceRow]] = relationship(
        "ResearchSourceRow", back_populates="session", cascade="all, delete-orphan"
    )
    findings: Mapped[list[ResearchFindingRow]] = relationship(
        "ResearchFindingRow", back_populates="session", cascade="all, delete-orphan"
    )


class ResearchSourceRow(Base):
    __tablename__ = "research_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True
    )
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    publisher: Mapped[str] = mapped_column(String(256), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    published_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    retrieved_at: Mapped[str] = mapped_column(String(40), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="news")
    target_entity: Mapped[str] = mapped_column(String(200), default="")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    credibility: Mapped[str] = mapped_column(String(32), default="unknown")
    in_window: Mapped[bool] = mapped_column(Boolean, default=True)
    undated: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped[ResearchSession] = relationship("ResearchSession", back_populates="sources")


class ResearchFindingRow(Base):
    __tablename__ = "research_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), default="single_source")
    source_ids_csv: Mapped[str] = mapped_column(Text, default="")  # comma-separated

    session: Mapped[ResearchSession] = relationship("ResearchSession", back_populates="findings")
