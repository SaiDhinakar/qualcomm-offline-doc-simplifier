"""Embedding & Local Vector Index module."""

from src.embed_index.embedding import (
    EmbeddingBackend,
    FastEmbedBackend,
    HashEmbeddingBackend,
    SentenceTransformerBackend,
    get_embedding_backend,
)
from src.embed_index.index import LocalVectorIndex
from src.embed_index.lifecycle import VectorStoreManager

__all__ = [
    "EmbeddingBackend",
    "FastEmbedBackend",
    "HashEmbeddingBackend",
    "SentenceTransformerBackend",
    "LocalVectorIndex",
    "VectorStoreManager",
    "get_embedding_backend",
]
