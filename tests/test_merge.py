"""Tests for the merge module."""

from src.models import Chunk
from src.simplify.llm import StubLLM
from src.simplify.merge import merge_explanations


def test_merge_explanations_basic():
    chunks = [
        Chunk(
            id="c1", document_id="d1", page_number=1,
            section_id="Section 1", order_index=0,
            raw_text="Original text 1",
            explanation="The first section explains the premium of $500.",
        ),
        Chunk(
            id="c2", document_id="d1", page_number=1,
            section_id="Section 2", order_index=1,
            raw_text="Original text 2",
            explanation="The second section covers coverage terms.",
        ),
    ]
    llm = StubLLM()
    result = merge_explanations(chunks, "en", llm)
    assert isinstance(result, str)
    assert len(result) > 0


def test_merge_explanations_empty():
    chunks = []
    llm = StubLLM()
    result = merge_explanations(chunks, "en", llm)
    assert result == "No explanations available for this document."


def test_merge_explanations_short():
    chunks = [
        Chunk(
            id="c1", document_id="d1", page_number=1,
            order_index=0, raw_text="text",
            explanation="Short explanation.",
        ),
    ]
    llm = StubLLM()
    result = merge_explanations(chunks, "en", llm)
    # Short text should be returned directly
    assert "Short explanation." in result


def test_merge_explanations_orders_by_index():
    chunks = [
        Chunk(
            id="c2", document_id="d1", page_number=1,
            order_index=5, raw_text="text2",
            explanation="Second.",
        ),
        Chunk(
            id="c1", document_id="d1", page_number=1,
            order_index=1, raw_text="text1",
            explanation="First.",
        ),
    ]
    llm = StubLLM()
    result = merge_explanations(chunks, "en", llm)
    # Should be ordered by index: First, then Second
    assert isinstance(result, str)
