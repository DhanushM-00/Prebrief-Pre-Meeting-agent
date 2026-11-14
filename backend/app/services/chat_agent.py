"""Evidence-grounded research agent.

Answers questions using only findings, sources, and open questions stored for a
research session. Never invents facts. Explicitly states when information is
missing or outside the research window.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.research import ResearchSession
from app.schemas.chat import ChatCitationOut, ChatResponse

log = logging.getLogger("prebrief.chat_agent")

_STOP = {
    "the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "is", "was", "are",
    "were", "what", "who", "how", "why", "when", "where", "did", "does", "do", "has",
    "have", "had", "me", "about", "their", "they", "them", "his", "her", "its", "our",
    "your", "we", "you", "that", "this", "these", "those", "be", "been", "it", "as",
    "at", "by", "with", "from", "tell", "give", "know", "want", "need", "can", "could",
    "would", "should", "will",
}


def _tokenize(s: str) -> list[str]:
    return [
        w
        for w in re.sub(r"[^a-z0-9\s-]", " ", s.lower()).split()
        if len(w) > 2 and w not in _STOP
    ]


def _score(tokens: list[str], text: str) -> int:
    t = text.lower()
    return sum(1 for tok in tokens if tok in t)


def _load_session_payload(db: Session, session_id: str, owner_id: str) -> dict[str, Any] | None:
    row = db.get(ResearchSession, session_id)
    if row is None:
        return None
    # Ownership: user_id stores the anonymous session id
    if row.user_id and row.user_id != owner_id:
        return None
    if not row.result_json:
        return None
    try:
        return json.loads(row.result_json)
    except json.JSONDecodeError:
        log.warning("Invalid result_json for research session %s", session_id)
        return None


def answer_from_payload(
    payload: dict[str, Any],
    question: str,
    *,
    research_session_id: str | None = None,
) -> ChatResponse:
    """Produce a grounded answer from a ResearchResultOut-like dict."""
    q = question.strip()
    qt = _tokenize(q)
    lower = q.lower()

    entity = payload.get("entity_name") or payload.get("entityName") or "the subject"
    entity_type = payload.get("entity_type") or payload.get("entityType") or "company"
    findings = payload.get("findings") or []
    sources = payload.get("sources") or []
    open_questions = payload.get("open_questions") or payload.get("openQuestions") or []
    gaps = payload.get("gaps") or []
    contradictions = payload.get("contradictions") or []
    stats = payload.get("stats") or {}
    window_days = payload.get("window_days") or payload.get("windowDays") or 30
    grounding_notes = payload.get("grounding_notes") or payload.get("groundingNotes") or []

    # Index sources by id
    src_by_id: dict[str, dict] = {}
    for s in sources:
        sid = s.get("id")
        if sid:
            src_by_id[sid] = s

    cites: list[str] = []
    cite_details: list[ChatCitationOut] = []

    def add_cite(sid: str | None) -> None:
        if not sid or sid in cites:
            return
        cites.append(sid)
        s = src_by_id.get(sid) or {}
        cite_details.append(
            ChatCitationOut(
                id=sid,
                title=s.get("headline") or s.get("title") or sid,
                url=s.get("url"),
                publisher=s.get("publisher") or s.get("source"),
            )
        )

    # Score findings
    scored: list[tuple[int, dict]] = []
    for f in findings:
        statement = f.get("statement") or ""
        cat = f.get("category") or ""
        score = _score(qt, statement) * 3 + _score(qt, cat) * 2
        # Boost risk / opportunity keywords
        if any(k in lower for k in ("risk", "challenge", "lawsuit", "problem", "concern")):
            if "risk" in cat or "challenge" in cat:
                score += 3
        if any(k in lower for k in ("product", "launch", "announce")):
            if "product" in cat or "launch" in cat:
                score += 2
        if any(k in lower for k in ("hire", "leadership", "appoint", "ceo", "executive")):
            if "hire" in cat or "leadership" in cat:
                score += 2
        if score > 0:
            scored.append((score, f))
    scored.sort(key=lambda x: -x[0])

    # Greeting / identity
    if re.match(r"^(hi|hey|hello|yo)\b", lower) or re.search(
        r"who are you|what are you|what is this", lower
    ):
        n_findings = len(findings)
        n_sources = len(sources)
        return ChatResponse(
            answer=(
                f"I'm the PreBrief research agent. I investigated **{entity}** "
                f"across the last {window_days} days and found {n_findings} findings "
                f"from {n_sources} sources.\n\n"
                "Ask me about recent developments, leadership, risks, competitors, "
                "or what you should prepare before a meeting. I only answer from "
                "evidence collected in this research session."
            ),
            citations=[],
            citation_details=[],
            grounded=True,
            research_session_id=research_session_id,
        )

    # Overview / who is
    if re.search(
        r"\b(who is|what is|tell me about|summar(y|ise|ize)|overview|profile|background)\b",
        lower,
    ):
        top = findings[:6]
        lines = [f"**{entity}** ({entity_type}) — research window: last {window_days} days.\n"]
        if top:
            lines.append("Key findings:")
            for f in top:
                conf = f.get("confidence") or "single_source"
                lines.append(f"- [{conf}] {f.get('statement')}")
                for sid in (f.get("source_ids") or f.get("sourceIds") or [])[:2]:
                    add_cite(sid)
                # also from nested sources list
                for src in f.get("sources") or []:
                    add_cite(src.get("id"))
        else:
            lines.append(
                "No verified findings were collected in this window. "
                "Try a longer window or check that the subject name is correct."
            )
        if gaps:
            lines.append("\n**Information gaps:**")
            for g in gaps[:5]:
                lines.append(f"- {g}")
        return ChatResponse(
            answer="\n".join(lines),
            citations=cites,
            citation_details=cite_details,
            grounded=True,
            research_session_id=research_session_id,
        )

    # Risks
    if re.search(r"\b(risk|challenge|lawsuit|investigation|controversy|problem|concern|threat)\b", lower):
        risk_findings = [
            f
            for f in findings
            if "risk" in (f.get("category") or "")
            or "challenge" in (f.get("category") or "")
            or any(
                k in (f.get("statement") or "").lower()
                for k in ("lawsuit", "investigation", "fine", "controversy", "risk")
            )
        ][:5]
        if not risk_findings:
            risk_findings = [f for _, f in scored[:3]]
        lines = []
        if risk_findings:
            lines.append(f"**Risks and challenges for {entity}:**\n")
            for f in risk_findings:
                lines.append(f"- {f.get('statement')} _(confidence: {f.get('confidence')})_")
                for sid in (f.get("source_ids") or [])[:2]:
                    add_cite(sid)
                for src in f.get("sources") or []:
                    add_cite(src.get("id"))
        else:
            lines.append(
                f"No explicit risk or challenge findings were recorded for **{entity}** "
                f"in the {window_days}-day window. That does not mean risks are absent — "
                "only that none were surfaced by the research pipeline."
            )
        return ChatResponse(
            answer="\n".join(lines),
            citations=cites,
            citation_details=cite_details,
            grounded=True,
            research_session_id=research_session_id,
        )

    # Leadership / people
    if re.search(r"\b(leader|executive|ceo|founder|hire|appoint|management|board|team)\b", lower):
        lead = [
            f
            for f in findings
            if "hire" in (f.get("category") or "")
            or "leadership" in (f.get("category") or "")
        ][:6]
        lines = [f"**Leadership and people signals for {entity}:**\n"]
        if lead:
            for f in lead:
                lines.append(f"- {f.get('statement')}")
                for sid in (f.get("source_ids") or [])[:2]:
                    add_cite(sid)
        else:
            lines.append(
                "No leadership or hiring findings were collected in this research window."
            )
        return ChatResponse(
            answer="\n".join(lines),
            citations=cites,
            citation_details=cite_details,
            grounded=True,
            research_session_id=research_session_id,
        )

    # Open questions / what to ask
    if re.search(r"\b(question|ask|prepare|meeting|what should i)\b", lower):
        lines = [f"**Questions worth asking about {entity}:**\n"]
        if open_questions:
            for i, oq in enumerate(open_questions[:7], 1):
                qtext = oq.get("question") or ""
                why = oq.get("rationale") or oq.get("why") or ""
                lines.append(f"{i}. **{qtext}**")
                if why:
                    lines.append(f"   *Why:* {why}")
                for rid in oq.get("related_finding_ids") or []:
                    # try map finding -> sources
                    for f in findings:
                        if f.get("id") == rid:
                            for sid in (f.get("source_ids") or [])[:1]:
                                add_cite(sid)
        else:
            lines.append(
                "The research pipeline did not generate open questions for this session. "
                "Review the findings above and form your own based on gaps."
            )
        if gaps:
            lines.append("\n**Known gaps:**")
            for g in gaps[:4]:
                lines.append(f"- {g}")
        return ChatResponse(
            answer="\n".join(lines),
            citations=cites,
            citation_details=cite_details,
            grounded=True,
            research_session_id=research_session_id,
        )

    # Recent / news / what happened
    if re.search(r"\b(recent|latest|news|happened|development|announce|update)\b", lower):
        top = [f for _, f in scored[:5]] if scored else findings[:5]
        lines = [f"**Recent developments for {entity}:**\n"]
        if top:
            for f in top:
                date = f.get("event_date") or ""
                prefix = f"*{date}* — " if date else ""
                lines.append(f"- {prefix}{f.get('statement')}")
                for sid in (f.get("source_ids") or [])[:2]:
                    add_cite(sid)
                for src in f.get("sources") or []:
                    add_cite(src.get("id"))
        else:
            lines.append("No findings available in this research session.")
        return ChatResponse(
            answer="\n".join(lines),
            citations=cites,
            citation_details=cite_details,
            grounded=True,
            research_session_id=research_session_id,
        )

    # Default: best-matching findings
    if scored:
        lines = [f"Based on evidence collected for **{entity}**:\n"]
        for score, f in scored[:5]:
            lines.append(f"- {f.get('statement')} _(confidence: {f.get('confidence')})_")
            for sid in (f.get("source_ids") or [])[:2]:
                add_cite(sid)
            for src in f.get("sources") or []:
                add_cite(src.get("id"))
        if contradictions:
            lines.append("\n**Conflicting reports noted:**")
            for c in contradictions[:3]:
                lines.append(f"- {c}")
        return ChatResponse(
            answer="\n".join(lines),
            citations=cites,
            citation_details=cite_details,
            grounded=True,
            research_session_id=research_session_id,
        )

    # Nothing matched
    gap_text = ""
    if gaps:
        gap_text = "\n\nKnown gaps from the research:\n" + "\n".join(f"- {g}" for g in gaps[:4])
    notes = ""
    if grounding_notes:
        notes = "\n\n" + "\n".join(grounding_notes[:3])

    return ChatResponse(
        answer=(
            f"I don't have a specific finding that answers that question about **{entity}** "
            f"within the {window_days}-day research window. "
            "I only report what the research pipeline collected; I do not invent information."
            f"{gap_text}{notes}"
        ),
        citations=[],
        citation_details=[],
        grounded=True,
        research_session_id=research_session_id,
    )


def answer_question(
    db: Session,
    owner_session_id: str,
    question: str,
    research_session_id: str | None = None,
    entity_name: str | None = None,
) -> ChatResponse:
    """Resolve research session and answer, or return a clear unavailable message."""
    if research_session_id:
        payload = _load_session_payload(db, research_session_id, owner_session_id)
        if payload is None:
            return ChatResponse(
                answer=(
                    "I could not load that research session. It may have expired, "
                    "belong to another session, or never completed successfully. "
                    "Please run a new research query first."
                ),
                citations=[],
                citation_details=[],
                grounded=False,
                research_session_id=research_session_id,
            )
        return answer_from_payload(payload, question, research_session_id=research_session_id)

    # No session id — try most recent for this owner + entity if given
    from sqlalchemy import select, desc

    q = (
        select(ResearchSession)
        .where(ResearchSession.user_id == owner_session_id)
        .order_by(desc(ResearchSession.created_at))
        .limit(5)
    )
    rows = list(db.scalars(q))
    if entity_name:
        en = entity_name.lower().strip()
        rows = [r for r in rows if (r.entity_name or "").lower().strip() == en] or rows

    for row in rows:
        if row.result_json:
            try:
                payload = json.loads(row.result_json)
                return answer_from_payload(payload, question, research_session_id=row.id)
            except json.JSONDecodeError:
                continue

    return ChatResponse(
        answer=(
            "No research session is available for me to answer from. "
            "Please run a company or person research first, then ask follow-up questions "
            "in the same browser session."
        ),
        citations=[],
        citation_details=[],
        grounded=False,
        research_session_id=None,
    )
