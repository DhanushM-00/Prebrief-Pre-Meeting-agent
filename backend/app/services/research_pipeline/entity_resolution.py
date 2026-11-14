"""Entity type resolution and name-matching filters."""
from __future__ import annotations

import re

_CORPORATE = re.compile(
    r"\b(inc|ltd|llc|plc|gmbh|corp|corporation|co|company|group|holdings|labs|"
    r"systems|technologies|ventures|partners|bank|airlines|motors)\b\.?",
    re.I,
)
_HONORIFIC = re.compile(r"^(dr|mr|mrs|ms|prof)\.?\s+", re.I)


def resolve_entity_type(name: str, requested: str) -> str:
    if requested in ("company", "person"):
        return requested
    n = name.strip()
    if _HONORIFIC.match(n) and not _CORPORATE.search(n):
        return "person"
    # Heuristic: multi-token Title Case without corporate suffix → person candidate
    tokens = n.split()
    if len(tokens) in (2, 3) and all(t[:1].isupper() for t in tokens if t) and not _CORPORATE.search(n):
        return "person"
    return "company"


def entity_mentioned(name: str, title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    n = name.lower().strip()
    if n in text:
        return True
    tokens = [t for t in re.split(r"\W+", n) if len(t) > 2]
    if not tokens:
        return False
    # Require all significant tokens for multi-word names (reduces false positives)
    return all(t in text for t in tokens)


def person_disambiguation_ok(name: str, title: str, content: str) -> bool:
    """Extra guard for people: require professional context, not just a name hit."""
    if not entity_mentioned(name, title, content):
        return False
    text = f"{title} {content}".lower()
    cues = (
        "ceo", "cfo", "cto", "coo", "founder", "executive", "director", "president",
        "appointed", "joins", "joined", "resigns", "steps down", "interview",
        "keynote", "conference", "board", "chief",
    )
    return any(c in text for c in cues)
