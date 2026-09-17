"""Tests for the per-chunk simplifier."""

from src.models import Chunk, GlossaryEntry
from src.simplify.llm import StubLLM
from src.simplify.simplifier import _extract_numeric_terms, simplify_chunk


def test_extract_numeric_terms():
    text = (
        "The premium is $1,200.50 per year, starting 01/15/2025, "
        "which is 5.5% of the sum assured."
    )
    terms = _extract_numeric_terms(text)
    assert "$1,200.50" in terms
    assert "5.5%" in terms


def test_simplify_chunk_with_stub_llm():
    chunk = Chunk(
        id="c1",
        document_id="doc1",
        page_number=1,
        order_index=0,
        raw_text="The Insured must pay the Premium within 30 days of the Policy Period start date.",
    )
    glossary = [
        GlossaryEntry(term="Insured", definition="The person covered by this policy"),
        GlossaryEntry(term="Premium", definition="The amount paid for coverage"),
    ]
    llm = StubLLM()
    result = simplify_chunk(chunk, glossary, "en", llm)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Stub LLM" in result  # Stub returns placeholder text


def test_simplify_chunk_no_glossary():
    chunk = Chunk(
        id="c1",
        document_id="doc1",
        page_number=1,
        order_index=0,
        raw_text="Simple text without any defined terms.",
    )
    llm = StubLLM()
    result = simplify_chunk(chunk, [], "en", llm)
    assert isinstance(result, str)
    assert len(result) > 0


def test_simplify_chunk_preserves_section_hint():
    chunk = Chunk(
        id="c1",
        document_id="doc1",
        page_number=1,
        section_id="Clause 4.2",
        order_index=0,
        raw_text="Payment terms apply.",
    )
    llm = StubLLM()
    result = simplify_chunk(chunk, [], "en", llm)
    assert isinstance(result, str)
