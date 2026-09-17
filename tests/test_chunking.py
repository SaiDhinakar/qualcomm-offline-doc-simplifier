"""Tests for the structure-aware chunker."""

from src.chunking.chunker import _SECTION_START, _extract_section_id, chunk_document
from src.models import Document, Page, SourceType


def test_heading_patterns():
    assert _SECTION_START.match("1. Introduction") is not None
    assert _SECTION_START.match("Section 3. Coverage") is not None
    assert _SECTION_START.match("Article 5") is not None
    assert _SECTION_START.match("Clause 4.2 Payment Terms") is not None
    assert _SECTION_START.match("This is just a regular paragraph with no special format") is None


def test_extract_section_id():
    assert _extract_section_id("Section 3. Coverage Details") == "Section 3."
    assert _extract_section_id("1. Introduction to the Agreement") == "1."
    assert _extract_section_id("IV. Payment Terms") == "IV."
    assert _extract_section_id("Regular paragraph text") is None


def test_chunk_single_page():
    doc = Document(
        id="test",
        source_type=SourceType.PDF,
        pages=[
            Page(
                page_number=1,
                raw_text=(
                    "1. First Section\nThis is the first section content.\n\n"
                    "2. Second Section\nThis is the second section content."
                ),
            )
        ],
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert chunks[0].document_id == "test"
    assert chunks[0].page_number == 1
    assert chunks[0].order_index == 0


def test_chunk_multiple_pages():
    doc = Document(
        id="test",
        source_type=SourceType.PDF,
        pages=[
            Page(page_number=1, raw_text="Page 1 content with Section 1."),
            Page(page_number=2, raw_text="Page 2 content with Section 2."),
        ],
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    # Find chunk from page 2
    page2_chunks = [c for c in chunks if c.page_number == 2]
    assert len(page2_chunks) >= 1


def test_chunk_preserves_section_id():
    doc = Document(
        id="test",
        source_type=SourceType.PDF,
        pages=[
            Page(
                page_number=1,
                raw_text="Section 5. Premium Payment\nYou must pay the premium monthly.",
            )
        ],
    )
    chunks = chunk_document(doc)
    # At least one chunk should have section_id
    sections = [c.section_id for c in chunks if c.section_id]
    assert len(sections) >= 1


def test_chunk_order_indices_are_sequential():
    doc = Document(
        id="test",
        source_type=SourceType.PDF,
        pages=[
            Page(page_number=1, raw_text="A\n\nB\n\nC"),
            Page(page_number=2, raw_text="D\n\nE"),
        ],
    )
    chunks = chunk_document(doc)
    indices = [c.order_index for c in chunks]
    assert indices == list(range(len(chunks)))
