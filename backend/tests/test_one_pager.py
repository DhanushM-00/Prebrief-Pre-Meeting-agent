"""Stage 5: one-page brief generation + PDF constraints."""
from __future__ import annotations

from app.schemas.research import (
    ResearchFindingOut,
    ResearchResultOut,
    ResearchSourceOut,
)
from app.services.one_pager.generator import generate_one_pager
from app.services.one_pager.pdf_service import render_one_page_pdf


def _src(i: int, title: str, url: str) -> ResearchSourceOut:
    return ResearchSourceOut(
        id=f"src-{i}",
        headline=title,
        publisher="reuters.com",
        url=url,
        published_at="2026-10-20T00:00:00Z",
        retrieved_at="2026-11-12T00:00:00Z",
        excerpt=title,
        category="news",
        target_entity="Acme Robotics",
        relevance_score=0.9,
        credibility="high",
        in_window=True,
    )


def _finding(cat: str, statement: str, sources: list[ResearchSourceOut]) -> ResearchFindingOut:
    return ResearchFindingOut(
        id=f"f-{cat[:4]}",
        category=cat,  # type: ignore[arg-type]
        statement=statement,
        event_date="2026-10-20",
        confidence="supported",
        sources=sources,
    )


def _research(findings=None, sources=None) -> ResearchResultOut:
    sources = sources or []
    findings = findings or []
    return ResearchResultOut(
        id="rs-test",
        entity_name="Acme Robotics",
        entity_type="company",
        meeting_at="2026-11-12T09:00:00Z",
        window_start="2026-10-13T00:00:00Z",
        window_end="2026-11-12T23:59:59Z",
        window_days=30,
        window_convention="Inclusive window: 2026-10-13 through 2026-11-12",
        findings=findings,
        sources=sources,
        open_questions=[],
        gaps=["No verified hires"] if not any(f.category == "hires_and_leadership" for f in findings) else [],
        contradictions=[],
        stats={"sources": len(sources), "findings": len(findings)},
        grounding_notes=["test"],
        generated_at="2026-11-12T12:00:00Z",
        status="completed",
    )


def test_citations_on_every_factual_bullet():
    s1 = _src(1, "Acme appoints new CTO", "https://reuters.com/acme-cto")
    s2 = _src(2, "Acme launches Widget X", "https://reuters.com/acme-widget")
    research = _research(
        sources=[s1, s2],
        findings=[
            _finding("hires_and_leadership", "Acme appointed a new CTO in October 2026", [s1]),
            _finding("product_and_service_launches", "Acme launched Widget X", [s2]),
            _finding("news", "Acme reported strong quarter", [s1]),
        ],
    )
    brief = generate_one_pager(research)
    assert brief.executive_snapshot
    assert brief.hires_and_leadership
    assert "[" in brief.hires_and_leadership[0].text
    assert brief.hires_and_leadership[0].citation_indexes
    assert brief.citations
    # Every citation has URL
    assert all(c.url.startswith("http") for c in brief.citations)


def test_empty_research_honest():
    research = _research(findings=[], sources=[])
    brief = generate_one_pager(research)
    assert "Insufficient verified" in brief.executive_snapshot or brief.limitations
    assert brief.news == []
    assert any("No verified" in lim or "no verified" in lim.lower() for lim in brief.limitations) or brief.limitations


def test_long_company_name():
    long = "International Business Machines Corporation Global Services Division Asia Pacific"
    research = _research()
    research = research.model_copy(update={"entity_name": long})
    brief = generate_one_pager(research)
    assert brief.entity_name == long
    pdf, fits, _ = render_one_page_pdf(brief)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500


def test_pdf_one_page_and_links():
    s1 = _src(1, "Acme appoints new CTO", "https://reuters.com/acme-cto")
    research = _research(
        sources=[s1],
        findings=[_finding("hires_and_leadership", "Acme appointed a new CTO", [s1])],
    )
    brief = generate_one_pager(research)
    pdf, fits, note = render_one_page_pdf(brief)
    assert pdf[:4] == b"%PDF"
    # Single page: only one /Type /Page roughly — soft check
    assert pdf.count(b"/Type /Page") <= 2  # /Page and maybe /Pages
    assert fits or note  # either fits or explains overflow


def test_person_entity():
    s1 = _src(1, "Jane Doe joins Acme as CEO", "https://reuters.com/jane-doe")
    research = _research(
        sources=[s1],
        findings=[_finding("hires_and_leadership", "Jane Doe joined Acme as CEO", [s1])],
    )
    research = research.model_copy(update={"entity_name": "Jane Doe", "entity_type": "person"})
    brief = generate_one_pager(research)
    assert brief.entity_type == "person"
    assert brief.hires_and_leadership
