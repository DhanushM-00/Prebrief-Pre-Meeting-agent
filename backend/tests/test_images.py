"""Image discovery parsing and person disambiguation tests."""
from __future__ import annotations

from app.services.images import collect_from_response, _person_matches, _company_matches


def test_person_disambiguation_requires_cues():
    assert not _person_matches("Jane Doe", "Jane Doe restaurant menu", None)
    assert _person_matches("Jane Doe", "Jane Doe appointed CEO of Acme", "executive portrait")
    assert _person_matches("Jane Doe", "Interview with Jane Doe at conference", "keynote")


def test_company_match():
    assert _company_matches("Acme Robotics", "Acme Robotics opens new HQ", None)
    assert not _company_matches("Acme Robotics", "Unrelated industry report", "markets rise")


def test_collect_from_response_parses_urls():
    data = {
        "images": [
            {"url": "https://cdn.example.com/a.jpg", "description": "Acme Robotics logo official"},
            "https://cdn.example.com/b.jpg",
        ],
        "results": [
            {
                "url": "https://news.example.com/story",
                "title": "Acme Robotics product launch",
                "images": ["https://cdn.example.com/product.jpg"],
            }
        ],
    }
    assets = collect_from_response(
        data,
        subject="Acme Robotics",
        subject_type="company",
        category="product",
        retrieved_at="2026-01-01T00:00:00Z",
    )
    urls = {a.url for a in assets}
    assert "https://cdn.example.com/product.jpg" in urls
    # Never invent URLs
    assert all(u.startswith("http") for u in urls)
