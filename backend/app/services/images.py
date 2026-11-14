"""Company and person image discovery via Tavily include_images.

Rules:
- Only use URLs returned by the provider (never invent).
- Person images require entity cues in title/description (role, company, event).
- Do not associate an image with a person solely because the name appears.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.schemas.briefing import ImageAsset
from app.services.tavily_client import TavilyClient

log = logging.getLogger("prebrief.images")

_IMAGE_CATS_COMPANY = (
    ("logo", '"{subject}" company logo official'),
    ("headquarters", '"{subject}" headquarters building office'),
    ("office", '"{subject}" office campus workplace'),
    ("product", '"{subject}" product product photo'),
    ("event", '"{subject}" conference event booth'),
    ("brand", '"{subject}" brand brand image'),
)

_IMAGE_CATS_PERSON = (
    ("profile", '"{subject}" professional portrait photo'),
    ("leadership", '"{subject}" CEO executive leadership photo'),
    ("event", '"{subject}" conference keynote speaking'),
    ("public", '"{subject}" interview public appearance'),
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
        return host or "unknown"
    except Exception:
        return "unknown"


def _normalize_image_entry(entry: Any) -> tuple[str | None, str | None]:
    """Accept str URL or {url, description} objects from Tavily."""
    if isinstance(entry, str):
        u = entry.strip()
        return (u if u.startswith("http") else None), None
    if isinstance(entry, dict):
        u = (entry.get("url") or entry.get("src") or "").strip()
        desc = entry.get("description") or entry.get("title")
        if u.startswith("http"):
            return u, (str(desc).strip() if desc else None)
    return None, None


def _person_matches(subject: str, title: str | None, description: str | None) -> bool:
    """Conservative disambiguation: require name token + a professional cue."""
    text = f"{title or ''} {description or ''}".lower()
    name = subject.lower().strip()
    if not name or name not in text:
        # Require all significant tokens
        tokens = [t for t in re.split(r"\W+", name) if len(t) > 2]
        if not tokens or not all(t in text for t in tokens):
            return False
    cues = (
        "ceo", "cfo", "cto", "founder", "executive", "director", "president",
        "interview", "keynote", "conference", "speaker", "portrait", "profile",
        "linkedin", "appointed", "joins", "leadership",
    )
    return any(c in text for c in cues)


def _company_matches(subject: str, title: str | None, description: str | None) -> bool:
    text = f"{title or ''} {description or ''}".lower()
    name = subject.lower().strip()
    if name and name in text:
        return True
    tokens = [t for t in re.split(r"\W+", name) if len(t) > 2]
    return bool(tokens) and all(t in text for t in tokens)


def collect_from_response(
    data: dict[str, Any],
    *,
    subject: str,
    subject_type: str,
    category: str,
    retrieved_at: str,
) -> list[ImageAsset]:
    """Parse top-level and per-result images from a Tavily search_full payload."""
    out: list[ImageAsset] = []
    seen: set[str] = set()

    def add(url: str, title: str | None, source_url: str | None, desc: str | None) -> None:
        if url in seen:
            return
        if subject_type == "person":
            if not _person_matches(subject, title, desc):
                return
        else:
            # Soft filter for company when we have text
            if (title or desc) and not _company_matches(subject, title, desc):
                return
        seen.add(url)
        out.append(
            ImageAsset(
                id=f"img-{len(seen):04d}",
                url=url,
                thumbnail_url=url,
                title=title,
                alt_text=desc or title or f"{subject} — {category}",
                category=category,  # type: ignore[arg-type]
                source_page_url=source_url,
                source_name=_domain(source_url or url),
                attribution=_domain(source_url or url),
                license_note="Retrieved via search provider; verify reuse rights before redistribution.",
                retrieved_at=retrieved_at,
                confidence="medium" if (title or desc) else "low",
            )
        )

    # Top-level images list
    for entry in data.get("images") or []:
        url, desc = _normalize_image_entry(entry)
        if url:
            add(url, desc, None, desc)

    # Per-result images (source-linked — preferred)
    for row in data.get("results") or []:
        if not isinstance(row, dict):
            continue
        page_url = row.get("url")
        page_title = row.get("title")
        for entry in row.get("images") or []:
            url, desc = _normalize_image_entry(entry)
            if url:
                add(url, page_title or desc, page_url, desc)

    return out


async def discover_images(
    client: TavilyClient,
    subject: str,
    subject_type: str,
    *,
    max_per_category: int = 3,
    max_total: int = 18,
) -> list[ImageAsset]:
    """Run category-specific image searches and return deduped ImageAssets."""
    cats = _IMAGE_CATS_PERSON if subject_type == "person" else _IMAGE_CATS_COMPANY
    retrieved_at = _utcnow()
    collected: list[ImageAsset] = []
    seen_urls: set[str] = set()

    for cat, template in cats:
        if len(collected) >= max_total:
            break
        query = template.format(subject=subject)
        try:
            data = await client.search_full(
                query,
                topic="general",
                max_results=5,
                search_depth="basic",
                include_images=True,
                include_image_descriptions=True,
            )
        except Exception as e:
            log.warning("image search failed cat=%s: %s", cat, e)
            continue
        assets = collect_from_response(
            data,
            subject=subject,
            subject_type=subject_type,
            category=cat,
            retrieved_at=retrieved_at,
        )
        n = 0
        for a in assets:
            if a.url in seen_urls:
                continue
            seen_urls.add(a.url)
            collected.append(a.model_copy(update={"id": f"img-{len(collected)+1:04d}", "category": cat}))
            n += 1
            if n >= max_per_category or len(collected) >= max_total:
                break

    return collected
