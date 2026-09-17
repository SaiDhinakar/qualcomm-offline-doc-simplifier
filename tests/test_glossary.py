"""Tests for the glossary extractor."""

from src.glossary.extractor import _is_valid_term, extract_glossary
from src.models import Chunk


def test_is_valid_term():
    assert _is_valid_term("Insured") is True
    assert _is_valid_term("Policy Period") is True
    assert _is_valid_term("X") is False  # too short
    assert _is_valid_term("the") is False  # skip word
    assert _is_valid_term("Section") is False  # skip word


def test_extract_glossary_basic():
    chunks = [
        Chunk(
            id="c1",
            document_id="doc1",
            page_number=1,
            order_index=0,
            raw_text='"Insured" means the person covered by this policy.',
        ),
    ]
    glossary = extract_glossary(chunks)
    assert len(glossary) >= 1
    terms = [e.term for e in glossary]
    assert "Insured" in terms


def test_extract_glossary_multiple_definitions():
    chunks = [
        Chunk(
            id="c1",
            document_id="doc1",
            page_number=1,
            order_index=0,
            raw_text='"Insured" means the person covered. "Premium" means the amount you pay.',
        ),
    ]
    glossary = extract_glossary(chunks)
    terms = [e.term for e in glossary]
    assert "Insured" in terms
    assert "Premium" in terms


def test_extract_glossary_shall_mean():
    chunks = [
        Chunk(
            id="c1",
            document_id="doc1",
            page_number=1,
            order_index=0,
            raw_text='"Policy Period" shall mean the duration of coverage.',
        ),
    ]
    glossary = extract_glossary(chunks)
    terms = [e.term for e in glossary]
    assert "Policy Period" in terms


def test_extract_glossary_deduplication():
    chunks = [
        Chunk(
            id="c1",
            document_id="doc1",
            page_number=1,
            order_index=0,
            raw_text='"Insured" means the person covered.',
        ),
        Chunk(
            id="c2",
            document_id="doc1",
            page_number=2,
            order_index=1,
            raw_text='"Insured" refers to the policyholder.',
        ),
    ]
    glossary = extract_glossary(chunks)
    insured_entries = [e for e in glossary if e.term == "Insured"]
    assert len(insured_entries) == 1
    # Should reference both chunks
    assert len(insured_entries[0].source_chunk_ids) == 2


def test_extract_glossary_empty():
    chunks = [
        Chunk(
            id="c1",
            document_id="doc1",
            page_number=1,
            order_index=0,
            raw_text="This is just regular text with no defined terms.",
        ),
    ]
    glossary = extract_glossary(chunks)
    assert len(glossary) == 0


def test_extract_glossary_cross_reference():
    chunks = [
        Chunk(
            id="c1",
            document_id="doc1",
            page_number=1,
            order_index=0,
            raw_text="The Insured (hereinafter referred to as \"Policyholder\") must comply.",
        ),
    ]
    glossary = extract_glossary(chunks)
    terms = [e.term for e in glossary]
    assert "Policyholder" in terms
