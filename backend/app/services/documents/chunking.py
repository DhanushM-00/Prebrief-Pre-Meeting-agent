"""Split extracted blocks into retrieval-sized chunks."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.documents.extraction import ExtractedBlock, ExtractionResult

# Rough target size (~500-800 tokens ≈ 2000-3200 chars)
_TARGET_CHARS = 2400
_OVERLAP = 200


@dataclass
class ChunkDraft:
    chunk_index: int
    content: str
    location_type: str | None
    location_label: str | None
    heading: str | None
    token_estimate: int


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def chunk_extracted(result: ExtractionResult) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    idx = 0
    for block in result.blocks:
        text = (block.text or "").strip()
        if not text:
            continue
        if len(text) <= _TARGET_CHARS:
            drafts.append(
                ChunkDraft(
                    chunk_index=idx,
                    content=text,
                    location_type=block.location_type,
                    location_label=block.location_label,
                    heading=block.heading,
                    token_estimate=_estimate_tokens(text),
                )
            )
            idx += 1
            continue
        # Sliding window split on paragraph boundaries when possible
        parts = text.split("\n\n")
        buf = ""
        for part in parts:
            candidate = f"{buf}\n\n{part}".strip() if buf else part
            if len(candidate) <= _TARGET_CHARS:
                buf = candidate
            else:
                if buf:
                    drafts.append(
                        ChunkDraft(
                            chunk_index=idx,
                            content=buf,
                            location_type=block.location_type,
                            location_label=block.location_label,
                            heading=block.heading,
                            token_estimate=_estimate_tokens(buf),
                        )
                    )
                    idx += 1
                    # overlap tail
                    buf = buf[-_OVERLAP:] + "\n\n" + part if len(buf) > _OVERLAP else part
                else:
                    # Hard split long paragraph
                    for start in range(0, len(part), _TARGET_CHARS - _OVERLAP):
                        piece = part[start : start + _TARGET_CHARS]
                        drafts.append(
                            ChunkDraft(
                                chunk_index=idx,
                                content=piece,
                                location_type=block.location_type,
                                location_label=block.location_label,
                                heading=block.heading,
                                token_estimate=_estimate_tokens(piece),
                            )
                        )
                        idx += 1
                    buf = ""
        if buf:
            drafts.append(
                ChunkDraft(
                    chunk_index=idx,
                    content=buf,
                    location_type=block.location_type,
                    location_label=block.location_label,
                    heading=block.heading,
                    token_estimate=_estimate_tokens(buf),
                )
            )
            idx += 1
    return drafts
