"""Source credibility, date verification, and relevance scoring."""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlsplit

# Well-known news domains → higher credibility (non-exhaustive)
_HIGH = {
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "nytimes.com",
    "washingtonpost.com", "apnews.com", "bbc.com", "bbc.co.uk", "cnbc.com",
    "forbes.com", "techcrunch.com", "theverge.com", "wired.com", "economist.com",
    "businesswire.com", "prnewswire.com", "sec.gov",
}
_MEDIUM = {
    "cnn.com", "theguardian.com", "axios.com", "insider.com", "businessinsider.com",
    "yahoo.com", "marketwatch.com", "seekingalpha.com", "venturebeat.com",
    "sifted.eu", "pitchbook.com", "crunchbase.com",
}


def publisher_from_url(url: str) -> str:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return host or "unknown"


def assess_credibility(url: str) -> str:
    host = publisher_from_url(url)
    if host in _HIGH or any(host.endswith("." + h) for h in _HIGH):
        return "high"
    if host in _MEDIUM or any(host.endswith("." + h) for h in _MEDIUM):
        return "medium"
    if host.endswith(".gov") or host.endswith(".edu"):
        return "high"
    return "unknown"


def relevance_score(entity: str, title: str, content: str, base: float = 0.0) -> float:
    text = f"{title} {content}".lower()
    score = max(0.0, min(1.0, base))
    name = entity.lower().strip()
    if name in title.lower():
        score += 0.25
    elif name in text:
        score += 0.12
    tokens = [t for t in re.split(r"\W+", name) if len(t) > 2]
    if tokens:
        hits = sum(1 for t in tokens if t in text)
        score += 0.05 * hits
    return round(min(1.0, score), 3)


def excerpt(content: str, title: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", (content or "").strip())
    if not text:
        return title[:limit]
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "…"
