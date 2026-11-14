"""Stage 6 reliability + citation integrity tests."""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.schemas.one_pager import BriefBullet, CitationRef, OnePageBrief
from app.schemas.research import ResearchFindingOut, ResearchResultOut, ResearchSourceOut
from app.services.one_pager.generator import generate_one_pager
from app.services.one_pager.pdf_service import render_one_page_pdf
from app.services.one_pager.validation import validate_one_pager
from app.services.research_pipeline.classification import classify_text
from app.services.research_pipeline.entity_resolution import (
    entity_mentioned,
    person_disambiguation_ok,
    resolve_entity_type,
)
from app.services.research_pipeline.window import compute_window, in_window, parse_meeting_at


def test_window_past_and_future_meetings():
    past = parse_meeting_at("2024-01-15")
    s, e, _ = compute_window(past, 30)
    assert s.date() == date(2023, 12, 16)
    assert e.date() == date(2024, 1, 15)

    future = parse_meeting_at("2027-06-01T14:30:00+05:30")
    s2, e2, _ = compute_window(future, 30)
    assert e2.date() == date(2027, 6, 1)
    assert s2.date() == date(2027, 5, 2)


def test_timezone_normalized_to_utc_window():
    meeting = parse_meeting_at("2026-11-12T18:30:00+05:30")
    assert meeting.tzinfo is not None
    s, e, _ = compute_window(meeting, 30)
    assert s.tzinfo is not None
    assert e.date() == date(2026, 11, 12)


def test_out_of_window_filtering():
    meeting = parse_meeting_at("2026-11-12")
    s, e, _ = compute_window(meeting, 30)
    assert in_window(datetime(2026, 10, 20, tzinfo=timezone.utc), s, e)
    assert not in_window(datetime(2026, 9, 1, tzinfo=timezone.utc), s, e)
    assert not in_window(None, s, e)


def test_entity_company_and_person():
    assert resolve_entity_type("Stripe Inc", "auto") == "company"
    assert resolve_entity_type("Satya Nadella", "person") == "person"
    assert entity_mentioned("Stripe", "Stripe raises funding", "")
    assert person_disambiguation_ok("Satya Nadella", "Satya Nadella CEO interview", "executive")
    assert not person_disambiguation_ok("Satya Nadella", "Nadella street cafe menu", "food")


def test_classification_buckets():
    assert classify_text("Company appoints new CEO", "") == "hires_and_leadership"
    assert classify_text("Firm launches new product", "") == "product_and_service_launches"
    assert classify_text("Startup raises Series B", "") == "business_developments"
    assert classify_text("Regulator opens investigation", "") == "risks_and_challenges"


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
        target_entity="TestCo",
        relevance_score=0.85,
        credibility="high",
        in_window=True,
    )


def _research(name: str, etype: str, findings, sources) -> ResearchResultOut:
    return ResearchResultOut(
        id="rs-s6",
        entity_name=name,
        entity_type=etype,  # type: ignore[arg-type]
        meeting_at="2026-11-12T10:00:00Z",
        window_start="2026-10-13T00:00:00Z",
        window_end="2026-11-12T23:59:59Z",
        window_days=30,
        window_convention="Inclusive window: 2026-10-13 through 2026-11-12",
        findings=findings,
        sources=sources,
        open_questions=[],
        gaps=[],
        contradictions=[],
        stats={"sources": len(sources)},
        grounding_notes=[],
        generated_at="2026-11-12T12:00:00Z",
        status="completed",
    )


def test_citation_integrity_strips_unsupported():
    s1 = _src(1, "TestCo appoints CTO", "https://reuters.com/testco-cto")
    findings = [
        ResearchFindingOut(
            id="f1",
            category="hires_and_leadership",
            statement="TestCo appointed a CTO",
            event_date="2026-10-20",
            confidence="supported",
            sources=[s1],
        )
    ]
    brief = generate_one_pager(_research("TestCo", "company", findings, [s1]))
    # Inject unsupported claim
    bad = brief.model_copy(
        update={
            "news": brief.news
            + [
                BriefBullet(
                    text="TestCo secretly bought a competitor without any source",
                    citation_indexes=[],
                    is_analysis=False,
                )
            ]
        }
    )
    result = validate_one_pager(bad)
    assert all("secretly bought" not in b.text for b in result.brief.news)
    assert result.omitted
    # Remaining hires still cited
    for b in result.brief.hires_and_leadership:
        assert b.citation_indexes
        assert all(
            any(c.index == i and c.url.startswith("http") for c in result.brief.citations)
            for i in b.citation_indexes
        )


def test_empty_research_no_fabrication():
    brief = generate_one_pager(_research("Obscure LLC", "company", [], []))
    validated = validate_one_pager(brief)
    assert validated.brief.news == []
    assert validated.brief.hires_and_leadership == []
    assert validated.brief.product_and_service_launches == []
    assert validated.brief.limitations
    pdf, fits, _ = render_one_page_pdf(validated.brief)
    assert pdf[:4] == b"%PDF"


def test_company_and_person_pdf_samples(tmp_path=None):
    s1 = _src(1, "Acme appoints CTO", "https://example.com/acme-cto")
    s2 = _src(2, "Acme launches X", "https://example.com/acme-x")
    company = _research(
        "Acme Robotics",
        "company",
        [
            ResearchFindingOut(
                id="f1",
                category="hires_and_leadership",
                statement="Acme appointed a CTO",
                event_date="2026-10-20",
                confidence="supported",
                sources=[s1],
            ),
            ResearchFindingOut(
                id="f2",
                category="product_and_service_launches",
                statement="Acme launched product X",
                event_date="2026-10-22",
                confidence="supported",
                sources=[s2],
            ),
        ],
        [s1, s2],
    )
    person_src = _src(3, "Jane Doe named CEO", "https://example.com/jane-ceo")
    person = _research(
        "Jane Doe",
        "person",
        [
            ResearchFindingOut(
                id="fp",
                category="hires_and_leadership",
                statement="Jane Doe was named CEO",
                event_date="2026-10-18",
                confidence="supported",
                sources=[person_src],
            )
        ],
        [person_src],
    )
    for label, research in (("company", company), ("person", person)):
        brief = validate_one_pager(generate_one_pager(research)).brief
        pdf, fits, note = render_one_page_pdf(brief)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500
        # write samples for delivery
        path = f"/home/workdir/artifacts/sample-{label}-brief.pdf"
        with open(path, "wb") as f:
            f.write(pdf)
