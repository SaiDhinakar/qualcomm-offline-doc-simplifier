"""Glossary Extractor module.

Scans all chunks to identify defined terms and their definitions, producing
a glossary table that later stages use for term resolution.
"""

from __future__ import annotations

import re

from src.models import Chunk, GlossaryEntry

# Common definition patterns in legal/financial documents
DEFINITION_PATTERNS = [
    # '"Term" means ...' or '"Term" shall mean ...'
    re.compile(
        r'"([A-Z][^"]{1,60})"\s+(?:means|shall mean|refers to|is defined as)\s+(.+?)(?:\.|$)',
        re.MULTILINE,
    ),
    # '(Term) means ...'
    re.compile(
        r'\(([A-Z][^)]{1,60})\)\s+(?:means|shall mean)\s+(.+?)(?:\.|$)',
        re.MULTILINE,
    ),
    # Term: definition (at start of line or after a number)
    re.compile(
        r'(?:^|\n)\s*(?:\d+[\.\)]\s*)?([A-Z][A-Za-z\s]{1,40}?)(?:\s*:\s*|\s+means\s+)(.+?)(?:\.|$)',
        re.MULTILINE,
    ),
    # 'defined as Term' or 'hereinafter referred to as "Term"'
    re.compile(
        r'(?:hereinafter|hereafter)\s+(?:referred\s+to\s+)?(?:as|called)\s+"([A-Z][^"]{1,60})"',
        re.IGNORECASE,
    ),
]

# Minimum term length to avoid noise
_MIN_TERM_LEN = 2
_MAX_TERM_LEN = 60


def _clean_term(term: str) -> str:
    """Normalize a extracted term."""
    return term.strip().strip('"').strip("'").strip()


def _clean_definition(defn: str) -> str:
    """Clean up an extracted definition."""
    defn = defn.strip()
    # Remove trailing period
    if defn.endswith("."):
        defn = defn[:-1]
    return defn.strip()


def _is_valid_term(term: str) -> bool:
    """Check if a term is likely a real defined term (not noise)."""
    if len(term) < _MIN_TERM_LEN or len(term) > _MAX_TERM_LEN:
        return False
    # Skip very common words that aren't defined terms
    skip_words = {
        "the", "this", "that", "these", "those", "here", "there", "where",
        "when", "which", "what", "who", "how", "all", "any", "each", "every",
        "some", "such", "other", "another", "both", "either", "neither",
        "not", "but", "and", "or", "if", "then", "else", "for", "nor",
        "with", "without", "under", "over", "above", "below", "between",
        "Section", "Article", "Chapter", "Clause", "Schedule", "Party",
        "Parties", "Agreement", "Contract", "Document", "System", "User",
    }
    if term in skip_words:
        return False
    return True


def extract_glossary(chunks: list[Chunk]) -> list[GlossaryEntry]:
    """Extract defined terms and their definitions from all chunks.

    Args:
        chunks: List of Chunk objects from the chunker.

    Returns:
        List of GlossaryEntry objects with deduplicated terms.
    """
    term_sources: dict[str, dict[str, str | list[str]]] = {}  # term -> {definition, chunk_ids}

    for chunk in chunks:
        text = chunk.raw_text

        for pattern in DEFINITION_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) == 2:
                    term = _clean_term(groups[0])
                    definition = _clean_definition(groups[1])
                elif len(groups) == 1:
                    term = _clean_term(groups[0])
                    definition = ""
                else:
                    continue

                if not _is_valid_term(term):
                    continue

                if definition and not definition:
                    continue  # Skip entries with no definition

                if term in term_sources:
                    existing = term_sources[term]
                    if definition and not existing["definition"]:
                        existing["definition"] = definition
                    existing["chunk_ids"].append(chunk.id)  # type: ignore[union-attr]
                else:
                    term_sources[term] = {
                        "definition": definition,
                        "chunk_ids": [chunk.id],
                    }

    entries: list[GlossaryEntry] = []
    for term, data in term_sources.items():
        definition = str(data.get("definition", ""))
        chunk_ids = data.get("chunk_ids", [])
        if not isinstance(chunk_ids, list):
            chunk_ids = [chunk_ids]
        entries.append(GlossaryEntry(
            term=term,
            definition=definition,
            source_chunk_ids=chunk_ids,
        ))

    return entries
