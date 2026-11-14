"""Classify articles and findings into Stage 4 categories."""
from __future__ import annotations

from typing import Literal

FindingCategory = Literal[
    "news",
    "hires_and_leadership",
    "product_and_service_launches",
    "business_developments",
    "risks_and_challenges",
]

_RULES: list[tuple[FindingCategory, tuple[str, ...]]] = [
    (
        "hires_and_leadership",
        (
            "appoints", "appointed", "hires", "hired", "joins as", "named ceo",
            "named cfo", "steps down", "resigns", "resignation", "promoted",
            "new ceo", "chief executive", "board director", "leadership change",
        ),
    ),
    (
        "product_and_service_launches",
        (
            "launches", "launched", "unveils", "unveiled", "releases", "released",
            "introduces", "rollout", "new product", "new service", "announces product",
        ),
    ),
    (
        "business_developments",
        (
            "funding", "raises", "series a", "series b", "series c", "acquisition",
            "acquires", "merger", "partnership", "partners with", "invests",
            "expansion", "ipo", "valuation", "joint venture", "strategic",
        ),
    ),
    (
        "risks_and_challenges",
        (
            "lawsuit", "sues", "sued", "investigation", "probe", "fine", "fined",
            "recall", "breach", "layoff", "layoffs", "bankruptcy", "fraud",
            "controversy", "scandal", "regulatory", "antitrust", "complaint",
        ),
    ),
]


def classify_text(title: str, content: str) -> FindingCategory:
    t = f"{title} {content}".lower()
    best: FindingCategory = "news"
    best_n = 0
    for cat, words in _RULES:
        n = sum(1 for w in words if w in t)
        if n > best_n:
            best, best_n = cat, n
    return best


def is_likely_interpretation(statement: str) -> bool:
    s = statement.lower()
    markers = ("may ", "might ", "could ", "suggests", "appears", "reportedly", "sources say")
    return any(m in s for m in markers)
