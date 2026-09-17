"""Integration test for the full pipeline (without OCR).

Tests the complete flow from Document → chunks → glossary → simplify → embed → merge → Q&A
using a pre-constructed Document object (skipping OCR).
"""

from src.chunking.chunker import chunk_document
from src.embed_index.embedding import HashEmbeddingBackend
from src.embed_index.index import LocalVectorIndex
from src.glossary.extractor import extract_glossary
from src.models import Document, Page, SourceType
from src.qa.engine import QAEngine
from src.simplify.llm import StubLLM
from src.simplify.merge import merge_explanations
from src.simplify.simplifier import simplify_chunk

SAMPLE_TEXT = """1. Policy Overview

This insurance policy ("Policy") is issued by ABC Insurance Company ("Company")
to the Insured. The Insured means the person named in the Schedule.
The Policy Period means the duration of coverage as specified in the Schedule.
The Sum Assured means the maximum amount payable under this Policy.

2. Premium Payment

The Insured must pay the Premium of $1,200 per year. Payment is due on the
first day of each month. Late payment incurs a penalty of 5% per month.

3. Coverage

The Company shall cover losses arising from natural disasters, theft, and
accidental damage. Coverage is subject to a deductible of $500 per claim.

4. Claims Process

Claims must be filed within 30 days of the incident. The Insured must provide
documentation including photographs and a police report where applicable.
"""


def _build_document() -> Document:
    """Build a Document from sample text."""
    return Document(
        id="sample_policy",
        source_type=SourceType.PDF,
        pages=[
            Page(page_number=1, raw_text=SAMPLE_TEXT[:1500]),
            Page(page_number=2, raw_text=SAMPLE_TEXT[1500:]),
        ],
        language="en",
    )


def test_full_pipeline_flow():
    """Test the complete pipeline flow without OCR."""
    # 1. Build document
    doc = _build_document()
    assert len(doc.pages) == 2

    # 2. Chunk
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert all(c.document_id == "sample_policy" for c in chunks)

    # 3. Glossary
    glossary = extract_glossary(chunks)
    assert len(glossary) >= 1
    terms = [e.term for e in glossary]
    # Should find defined terms like "Policy Period" or "Sum Assured"
    assert any("Policy Period" in t or "Sum Assured" in t for t in terms)

    # 4. Simplify each chunk
    llm = StubLLM()
    for chunk in chunks:
        chunk.explanation = simplify_chunk(chunk, glossary, "en", llm)
        assert chunk.explanation is not None
        assert len(chunk.explanation) > 0

    # 5. Embed and index
    embedder = HashEmbeddingBackend(dim=64)
    index = LocalVectorIndex()
    texts = [c.raw_text for c in chunks]
    embeddings = embedder.embed(texts)
    index.add_chunks(chunks, embeddings)
    assert index.size == len(chunks)

    # 6. Merge
    overview = merge_explanations(chunks, "en", llm)
    assert isinstance(overview, str)
    assert len(overview) > 0

    # 7. Q&A
    qa = QAEngine(index=index, embedding_backend=embedder, llm=llm, similarity_threshold=-1.0)
    result = qa.answer("What is the premium amount?", target_language="en")
    assert result["status"] == "answered"
    assert len(result["answer"]) > 0


def test_glossary_deduplication_across_chunks():
    """Test that glossary correctly deduplicates terms across chunks."""
    doc = _build_document()
    chunks = chunk_document(doc)
    glossary = extract_glossary(chunks)

    # Each term should appear only once
    terms = [e.term for e in glossary]
    assert len(terms) == len(set(terms))


def test_chunk_ordering_preserved():
    """Test that chunks maintain document order."""
    doc = _build_document()
    chunks = chunk_document(doc)
    indices = [c.order_index for c in chunks]
    assert indices == sorted(indices)
