"""Embedding interface for the vector index.

Provides an abstraction over different embedding backends (stub, sentence-transformers, etc.)
with a common interface for generating text embeddings.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingBackend(ABC):
    """Abstract base class for embedding backends."""

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Returns:
            2D numpy array of shape (len(texts), embedding_dim).
        """
        ...

    @abstractmethod
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Returns:
            1D numpy array of shape (embedding_dim,).
        """
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...


class HashEmbeddingBackend(EmbeddingBackend):
    """Deterministic hash-based embeddings for development/testing.

    Produces fixed-size vectors from text using a hash function.
    Not semantically meaningful — only for pipeline testing.
    """

    def __init__(self, dim: int = 384):
        self._dim = dim

    def _text_to_vector(self, text: str) -> np.ndarray:
        import hashlib
        # Use multiple hashes to fill the vector
        vec = np.zeros(self._dim, dtype=np.float32)
        for i in range(self._dim):
            h = hashlib.sha256(f"{text}:{i}".encode()).hexdigest()
            # Convert first 8 hex chars to float in [-1, 1]
            val = int(h[:8], 16) / 0xFFFFFFFF
            vec[i] = val * 2 - 1
        # Normalize to unit vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array([self._text_to_vector(t) for t in texts])

    def embed_single(self, text: str) -> np.ndarray:
        return self._text_to_vector(text)

    def dimension(self) -> int:
        return self._dim


class SentenceTransformerBackend(EmbeddingBackend):
    """Embedding backend using sentence-transformers (requires torch)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install with: uv pip install sentence-transformers torch"
            )

    def embed(self, texts: list[str]) -> np.ndarray:
        self._load()
        assert self._model is not None
        return self._model.encode(texts, convert_to_numpy=True)

    def embed_single(self, text: str) -> np.ndarray:
        self._load()
        assert self._model is not None
        return self._model.encode(text, convert_to_numpy=True)

    def dimension(self) -> int:
        self._load()
        assert self._model is not None
        return self._model.get_sentence_embedding_dimension()


def get_embedding_backend(backend: str = "hash", **kwargs) -> EmbeddingBackend:
    """Factory function to get an embedding backend.

    Args:
        backend: "hash" for development, "sentence-transformers" for real embeddings.
        **kwargs: additional arguments passed to the backend constructor.

    Returns:
        An EmbeddingBackend instance.
    """
    if backend == "hash":
        return HashEmbeddingBackend(**kwargs)
    elif backend == "sentence-transformers":
        return SentenceTransformerBackend(**kwargs)
    else:
        raise ValueError(f"Unknown embedding backend: {backend}")
