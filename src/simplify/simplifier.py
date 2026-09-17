"""Per-Chunk Simplifier module.

Explains each document chunk in plain language using the glossary for term resolution,
preserving numeric details exactly.
"""

from __future__ import annotations

import re

from src.models import Chunk, GlossaryEntry
from src.simplify.llm import LLMBackend

# Patterns for numeric details that must be preserved exactly
_NUMERIC_PATTERN = re.compile(
    r"(?:"
    r"\$[\d,]+(?:\.\d+)?"           # currency amounts
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?"  # large numbers with commas
    r"|\d+[\.\d]*%"                  # percentages
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"  # dates
    r"|\d{4}[/-]\d{1,2}[/-]\d{1,2}"    # dates (YYYY-MM-DD)
    r"|\d+\s*(?:days?|months?|years?|hours?|minutes?)"  # time periods
    r"|\b(?:Rs|INR|USD|EUR|GBP)\.?\s*[\d,]+"  # currency in words
    r"|\b\d{1,3}(?:\.\d+)?\s*(?:crore|lakh|million|billion|thousand)\b"  # Indian numbering
    r")",
    re.IGNORECASE,
)


def _extract_numeric_terms(text: str) -> dict[str, str]:
    """Extract numeric terms and their surrounding context for preservation."""
    terms = {}
    for match in _NUMERIC_PATTERN.finditer(text):
        terms[match.group()] = match.group()
    return terms


def _build_glossary_context(glossary: list[GlossaryEntry], chunk_text: str) -> str:
    """Build a glossary context string relevant to this chunk."""
    relevant = []
    chunk_lower = chunk_text.lower()
    for entry in glossary:
        if entry.term.lower() in chunk_lower or entry.definition:
            relevant.append(f'- "{entry.term}": {entry.definition}')

    if not relevant:
        return ""

    return "Defined terms in this document:\n" + "\n".join(relevant[:20])


def simplify_chunk(
    chunk: Chunk,
    glossary: list[GlossaryEntry],
    target_language: str,
    llm: LLMBackend,
    language_names: dict[str, str] | None = None,
) -> str:
    """Simplify a single chunk into plain language.

    Args:
        chunk: The chunk to simplify.
        glossary: Full document glossary for term resolution.
        target_language: ISO language code for output.
        llm: LLM backend to use for generation.
        language_names: optional mapping of ISO codes to full language names.

    Returns:
        Plain-language explanation of the chunk.
    """
    lang_names = language_names or {
        "hi": "Hindi",
        "ta": "Tamil",
        "kn": "Kannada",
        "te": "Telugu",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "ur": "Urdu",
        "en": "English",
    }
    target_name = lang_names.get(target_language, target_language)

    glossary_ctx = _build_glossary_context(glossary, chunk.raw_text)
    numeric_terms = _extract_numeric_terms(chunk.raw_text)
    numeric_ctx = ""
    if numeric_terms:
        numeric_ctx = (
            "\nIMPORTANT: You MUST preserve these exact numbers, dates, and amounts "
            "without changing them:\n"
            + "\n".join(f"  - {v}" for v in numeric_terms.values())
        )

    section_hint = f" (Section: {chunk.section_id})" if chunk.section_id else ""

    prompt = (
        f"You are a legal/financial document explainer. "
        f"Explain the following text in simple, clear {target_name}.\n\n"
        f"RULES:\n"
        f"1. Use simple, everyday language that anyone can understand\n"
        f"2. Preserve ALL numbers, amounts, dates, and percentages EXACTLY as written\n"
        f"3. If the text defines a term, use the definition from the glossary below\n"
        f"4. Do NOT add information that isn't in the original text\n"
        f"5. Do NOT give legal or financial advice — only explain what the text says\n"
        f"6. Keep the explanation concise but complete\n\n"
        f"{glossary_ctx}\n{numeric_ctx}\n\n"
        f"Original text{section_hint}:\n{chunk.raw_text}\n\n"
        f"Provide your explanation in {target_name}:"
    )

    return llm.generate(prompt, max_tokens=512, temperature=0.3)
