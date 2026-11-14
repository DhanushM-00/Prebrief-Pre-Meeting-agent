"""AI document intelligence via Gemini (graceful stub when no API key)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import Settings

log = logging.getLogger("prebrief.documents")


def _stub_intelligence(text: str, filename: str) -> dict[str, Any]:
    """Deterministic offline intelligence so the pipeline works without Gemini."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9&.'-]{1,}", text)
    # Crude entity heuristics
    companies = sorted({w for w in words if w[:1].isupper() and len(w) > 3})[:12]
    dates = re.findall(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
        text,
        flags=re.I,
    )[:10]
    money = re.findall(r"\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|m|bn))?", text, flags=re.I)[:10]
    preview = text[:600].replace("\n", " ").strip()
    topics = []
    for kw in ("revenue", "product", "risk", "market", "customer", "growth", "regulation", "partnership"):
        if re.search(rf"\b{kw}\b", text, re.I):
            topics.append(kw.capitalize())
    return {
        "summary": {
            "executive_summary": preview + ("…" if len(text) > 600 else ""),
            "main_topics": topics or ["General content"],
            "important_facts": money[:3] or companies[:3],
            "key_findings": topics[:3],
            "important_dates": dates,
        },
        "entities": {
            "companies": companies[:8],
            "people": [],
            "financial_figures": money,
            "products": [],
            "events": dates[:5],
            "risks": [t for t in topics if t.lower() in ("risk", "regulation")],
            "opportunities": [t for t in topics if t.lower() in ("growth", "partnership", "market")],
        },
        "questions": [
            f"What is the primary purpose of {filename}?",
            "Which financial figures are most material?",
            "What risks or uncertainties are mentioned?",
            "What follow-up information is missing from this document?",
            "How does this document relate to the upcoming meeting objectives?",
        ],
        "provider": "stub",
    }


async def analyze_document(
    text: str,
    filename: str,
    settings: Settings,
) -> dict[str, Any]:
    """Return summary + entities + questions. Uses Gemini when configured."""
    # Cap input for cost/safety
    clipped = text[:24000]
    if not settings.gemini_api_key:
        return _stub_intelligence(clipped, filename)

    prompt = f"""You are a research analyst. Analyze the uploaded document "{filename}".
Return STRICT JSON with this shape (no markdown fences):
{{
  "summary": {{
    "executive_summary": "2-4 sentences",
    "main_topics": ["..."],
    "important_facts": ["..."],
    "key_findings": ["..."],
    "important_dates": ["..."]
  }},
  "entities": {{
    "companies": ["..."],
    "people": ["..."],
    "financial_figures": ["..."],
    "products": ["..."],
    "events": ["..."],
    "risks": ["..."],
    "opportunities": ["..."]
  }},
  "questions": ["5-8 insightful questions grounded in the document"]
}}

Document text:
{clipped}
"""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
        text_out = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        parsed = json.loads(text_out)
        parsed["provider"] = "gemini"
        return parsed
    except Exception as e:
        log.warning("Gemini intelligence failed, using stub: %s", e)
        out = _stub_intelligence(clipped, filename)
        out["provider_error"] = str(e)
        return out


async def answer_document_question(
    question: str,
    context_chunks: list[dict[str, str]],
    settings: Settings,
) -> dict[str, Any]:
    """Answer a question using retrieved chunks; always return citations."""
    citations = []
    context_parts = []
    for i, ch in enumerate(context_chunks):
        loc = ch.get("location_label") or "section"
        name = ch.get("document_name") or "document"
        citations.append(
            {
                "document_id": ch.get("document_id"),
                "document_name": name,
                "location": loc,
                "excerpt": (ch.get("content") or "")[:240],
            }
        )
        context_parts.append(f"[{i + 1}] ({name} — {loc})\n{ch.get('content', '')}")

    context = "\n\n".join(context_parts)[:18000]
    if not context.strip():
        return {
            "answer": "I could not find relevant content in your uploaded documents for that question.",
            "citations": [],
            "provider": "none",
        }

    if not settings.gemini_api_key:
        # Extractive stub: return the top chunk with a framing sentence
        top = context_chunks[0] if context_chunks else {}
        excerpt = (top.get("content") or "")[:500]
        answer = (
            f"Based on your uploaded documents, here is the most relevant passage:\n\n{excerpt}"
        )
        return {"answer": answer, "citations": citations[:5], "provider": "stub"}

    prompt = f"""Answer the user's question using ONLY the uploaded document excerpts below.
Cite sources as [n] matching the excerpt numbers. If the documents do not contain the answer, say so.
Do not invent facts not present in the excerpts.

Question: {question}

Excerpts:
{context}
"""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
        answer = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        return {"answer": answer, "citations": citations[:8], "provider": "gemini"}
    except Exception as e:
        log.warning("Gemini chat failed: %s", e)
        return {
            "answer": f"AI provider unavailable. Top matching excerpt:\n\n{(context_chunks[0].get('content') or '')[:500]}",
            "citations": citations[:5],
            "provider": "stub",
            "provider_error": str(e),
        }
