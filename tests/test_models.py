"""Tests for the data models."""

from datetime import datetime, timedelta

from src.models import (
    Chunk,
    Document,
    DocumentSession,
    GlossaryEntry,
    Page,
    Region,
    RegionType,
    SourceType,
)


def test_page_model():
    page = Page(page_number=1, raw_text="Hello world")
    assert page.page_number == 1
    assert page.raw_text == "Hello world"
    assert page.layout_regions == []
    assert page.ocr_confidence == 1.0


def test_page_with_regions():
    region = Region(
        region_type=RegionType.HEADING,
        bbox=(0, 0, 100, 50),
        text="Section 1",
        confidence=0.95,
    )
    page = Page(page_number=1, raw_text="Section 1\nContent", layout_regions=[region])
    assert len(page.layout_regions) == 1
    assert page.layout_regions[0].region_type == RegionType.HEADING


def test_chunk_model():
    chunk = Chunk(
        id="abc123",
        document_id="doc1",
        page_number=1,
        section_id="Clause 1",
        order_index=0,
        raw_text="Some text",
    )
    assert chunk.id == "abc123"
    assert chunk.explanation is None
    assert chunk.embedding == []


def test_glossary_entry():
    entry = GlossaryEntry(
        term="Insured",
        definition="The person covered by this policy",
        source_chunk_ids=["chunk1", "chunk2"],
    )
    assert entry.term == "Insured"
    assert len(entry.source_chunk_ids) == 2


def test_document_session():
    session = DocumentSession(document_id="doc1")
    assert session.document_id == "doc1"
    assert session.is_expired() is False
    assert session.overview == ""


def test_document_session_expiry():
    session = DocumentSession(
        document_id="doc1",
        expires_at=datetime.now() - timedelta(minutes=1),
    )
    assert session.is_expired() is True


def test_document_session_clear():
    session = DocumentSession(document_id="doc1")
    chunk = Chunk(id="c1", document_id="doc1", page_number=1, order_index=0, raw_text="x")
    session.chunks = [chunk]
    session.overview = "Some overview"
    session.clear()
    assert len(session.chunks) == 0
    assert session.overview == ""


def test_document_model():
    doc = Document(
        id="test_doc",
        source_type=SourceType.PDF,
        pages=[Page(page_number=1, raw_text="content")],
        language="hi",
    )
    assert doc.id == "test_doc"
    assert len(doc.pages) == 1
    assert doc.language == "hi"
