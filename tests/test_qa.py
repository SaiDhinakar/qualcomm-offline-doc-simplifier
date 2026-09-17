"""Tests for the Q&A engine."""

from src.embed_index.embedding import HashEmbeddingBackend
from src.embed_index.index import LocalVectorIndex
from src.models import Chunk
from src.qa.engine import QAEngine
from src.simplify.llm import StubLLM


def _build_test_index():
    """Build a small test index with known chunks."""
    embedder = HashEmbeddingBackend(dim=64)
    index = LocalVectorIndex()

    chunks = [
        Chunk(
            id="c1", document_id="d1", page_number=1,
            section_id="Section 1", order_index=0,
            raw_text="The policy premium is $500 per year.",
        ),
        Chunk(
            id="c2", document_id="d1", page_number=1,
            section_id="Section 2", order_index=1,
            raw_text="Coverage begins on the policy start date.",
        ),
        Chunk(
            id="c3", document_id="d1", page_number=2,
            section_id="Section 3", order_index=2,
            raw_text="Claims must be filed within 30 days of the incident.",
        ),
    ]

    embeddings = embedder.embed([c.raw_text for c in chunks])
    index.add_chunks(chunks, embeddings)

    return index, embedder


def test_qa_engine_answer():
    index, embedder = _build_test_index()
    llm = StubLLM()

    engine = QAEngine(index=index, embedding_backend=embedder, llm=llm)
    result = engine.answer("What is the premium amount?", target_language="en")

    assert result["status"] == "answered"
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0
    assert isinstance(result["source_sections"], list)


def test_qa_engine_empty_index():
    index = LocalVectorIndex()
    embedder = HashEmbeddingBackend(dim=64)
    llm = StubLLM()

    engine = QAEngine(index=index, embedding_backend=embedder, llm=llm)
    result = engine.answer("Any question?", target_language="en")

    assert result["status"] == "not_addressed"
    assert "does not appear to address" in result["answer"]


def test_qa_engine_source_sections():
    index, embedder = _build_test_index()
    llm = StubLLM()

    # Use a very low threshold since hash embeddings don't have semantic meaning
    engine = QAEngine(index=index, embedding_backend=embedder, llm=llm, similarity_threshold=-1.0)
    result = engine.answer("premium payment", target_language="en")

    assert result["status"] == "answered"
    assert isinstance(result["source_sections"], list)
