"""Tests for the embedding backends and local vector index."""

import numpy as np

from src.embed_index.embedding import HashEmbeddingBackend, get_embedding_backend
from src.embed_index.index import LocalVectorIndex
from src.models import Chunk


def test_hash_embedding_dimension():
    embedder = HashEmbeddingBackend(dim=128)
    assert embedder.dimension() == 128


def test_hash_embedding_single():
    embedder = HashEmbeddingBackend(dim=64)
    vec = embedder.embed_single("hello world")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (64,)
    # Should be normalized
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-6


def test_hash_embedding_batch():
    embedder = HashEmbeddingBackend(dim=64)
    vecs = embedder.embed(["hello", "world", "test"])
    assert vecs.shape == (3, 64)


def test_hash_embedding_deterministic():
    embedder = HashEmbeddingBackend(dim=64)
    v1 = embedder.embed_single("same text")
    v2 = embedder.embed_single("same text")
    np.testing.assert_array_equal(v1, v2)


def test_hash_embedding_different_texts():
    embedder = HashEmbeddingBackend(dim=64)
    v1 = embedder.embed_single("text one")
    v2 = embedder.embed_single("text two")
    assert not np.allclose(v1, v2)


def test_get_embedding_backend_hash():
    backend = get_embedding_backend("hash", dim=128)
    assert isinstance(backend, HashEmbeddingBackend)
    assert backend.dimension() == 128


def test_local_vector_index_add_and_search():
    index = LocalVectorIndex()
    embedder = HashEmbeddingBackend(dim=64)

    chunks = [
        Chunk(id="c1", document_id="d1", page_number=1, order_index=0, raw_text="insurance policy"),
        Chunk(id="c2", document_id="d1", page_number=1, order_index=1, raw_text="payment terms"),
        Chunk(id="c3", document_id="d1", page_number=2, order_index=2, raw_text="coverage details"),
    ]
    embeddings = embedder.embed([c.raw_text for c in chunks])

    index.add_chunks(chunks, embeddings)
    assert index.size == 3

    # Search - hash embeddings don't have semantic similarity, just check it returns results
    query_emb = embedder.embed_single("insurance")
    results = index.search(query_emb, top_k=3, threshold=-1.0)
    assert len(results) == 3
    assert all(isinstance(score, float) for _, score in results)


def test_local_vector_index_empty():
    index = LocalVectorIndex()
    embedder = HashEmbeddingBackend(dim=64)
    query = embedder.embed_single("test")
    results = index.search(query, top_k=5)
    assert results == []


def test_local_vector_index_threshold():
    index = LocalVectorIndex()
    embedder = HashEmbeddingBackend(dim=64)

    chunk = Chunk(id="c1", document_id="d1", page_number=1, order_index=0, raw_text="hello")
    embeddings = embedder.embed([chunk.raw_text])
    index.add_chunks([chunk], embeddings)

    # Search with very high threshold should return nothing for different text
    results = index.search(embedder.embed_single("different text"), top_k=5, threshold=0.99)
    assert len(results) == 0  # Different text, low similarity

    # Same text should have similarity = 1.0
    results = index.search(embedder.embed_single("hello"), top_k=5, threshold=0.99)
    assert len(results) == 1


def test_local_vector_index_get_by_id():
    index = LocalVectorIndex()
    embedder = HashEmbeddingBackend(dim=64)

    chunk = Chunk(id="unique_id", document_id="d1", page_number=1, order_index=0, raw_text="test")
    embeddings = embedder.embed([chunk.raw_text])
    index.add_chunks([chunk], embeddings)

    found = index.get_chunk_by_id("unique_id")
    assert found is not None
    assert found.id == "unique_id"

    not_found = index.get_chunk_by_id("nonexistent")
    assert not_found is None


def test_local_vector_index_clear():
    index = LocalVectorIndex()
    embedder = HashEmbeddingBackend(dim=64)

    chunks = [
        Chunk(id="c1", document_id="d1", page_number=1, order_index=0, raw_text="test"),
    ]
    embeddings = embedder.embed([c.raw_text for c in chunks])
    index.add_chunks(chunks, embeddings)
    assert index.size == 1

    index.clear()
    assert index.size == 0
