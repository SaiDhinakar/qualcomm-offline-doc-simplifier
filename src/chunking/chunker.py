"""Structure-Aware Chunker module.

Splits extracted document text into chunks aligned to clause/section boundaries
rather than fixed token windows. Each chunk retains page number, section ID, and
position metadata.
"""

from __future__ import annotations

import hashlib
import re

from src.models import Chunk, Document

# Heuristic: target ~500 tokens per chunk (~2000 chars). Tune once LLM is chosen.
_TARGET_CHUNK_CHARS = 2000
_MAX_CHUNK_CHARS = 3000

# Patterns that signal the start of a new structural section
_SECTION_START = re.compile(
    r"^\s*(?:"
    r"\d+[\.\)]\s+\S"           # "1. Something"
    r"|[IVX]+[\.\)]\s+\S"      # "IV. Something"
    r"|Section\s+\d+"           # "Section 3"
    r"|Article\s+\d+"           # "Article 5"
    r"|Chapter\s+\d+"           # "Chapter 2"
    r"|Clause\s+\d+"            # "Clause 4.2"
    r"|Schedule\s+\d+"          # "Schedule 1"
    r"|Annexure\s+[A-Z\d]+"     # "Annexure A"
    r"|Paragraph\s+\d+"         # "Paragraph 3"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# Sub-clause patterns for secondary splitting within an oversized chunk
_SUBCLAUSE_START = re.compile(
    r"^\s*(?:\d+\.\d+[\.\)]\s+\S|[a-z][\.\)]\s+\S)",
    re.MULTILINE,
)


def _make_chunk_id(document_id: str, order_index: int) -> str:
    raw = f"{document_id}:{order_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _extract_section_id(text: str) -> str | None:
    """Try to extract a clause/section identifier from the beginning of text."""
    match = re.match(
        r"^\s*((?:Section|Article|Chapter|Clause|Schedule|Annexure|Paragraph)"
        r"\s+[\d\.A-Z]+)",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    match = re.match(r"^\s*(\d+[\.\)])", text)
    if match:
        return match.group(1).strip()

    match = re.match(r"^\s*([IVX]+[\.\)])", text)
    if match:
        return match.group(1).strip()

    return None


def _split_at_section_boundaries(text: str) -> list[str]:
    """Split text into segments at structural section boundaries."""
    segments: list[str] = []
    current: list[str] = []

    for line in text.split("\n"):
        if _SECTION_START.match(line) and current:
            segments.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        segments.append("\n".join(current).strip())

    return [s for s in segments if s]


def _split_oversized_chunk(text: str) -> list[str]:
    """Secondary split at sentence boundaries for chunks exceeding max size."""
    if len(text) <= _MAX_CHUNK_CHARS:
        return [text]

    # Try sub-clause boundaries first
    if _SUBCLAUSE_START.search(text):
        parts = _SUBCLAUSE_START.split(text)
        result: list[str] = []
        current = ""
        for part in parts:
            if len(current) + len(part) > _TARGET_CHUNK_CHARS and current:
                result.append(current.strip())
                current = part
            else:
                current += part
        if current.strip():
            result.append(current.strip())
        if all(len(r) <= _MAX_CHUNK_CHARS for r in result):
            return result

    # Fall back to sentence boundary splitting
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > _TARGET_CHUNK_CHARS and current:
            result.append(current.strip())
            current = sentence
        else:
            current += " " + sentence if current else sentence
    if current.strip():
        result.append(current.strip())

    return result if result else [text]


def chunk_document(document: Document) -> list[Chunk]:
    """Split a document into structure-aware chunks.

    Args:
        document: Document with populated pages.

    Returns:
        Ordered list of Chunk objects with metadata.
    """
    chunks: list[Chunk] = []
    order_index = 0

    for page in document.pages:
        # Split page text at section boundaries
        segments = _split_at_section_boundaries(page.raw_text)

        for segment in segments:
            # Further split oversized segments
            sub_segments = _split_oversized_chunk(segment)

            for sub_seg in sub_segments:
                section_id = _extract_section_id(sub_seg)
                chunk_id = _make_chunk_id(document.id, order_index)

                chunks.append(Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    page_number=page.page_number,
                    section_id=section_id,
                    order_index=order_index,
                    raw_text=sub_seg,
                ))
                order_index += 1

    return chunks
