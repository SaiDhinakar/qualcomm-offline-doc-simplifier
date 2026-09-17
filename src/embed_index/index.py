"""Local vector index for similarity search.

Provides an in-memory vector store with brute-force cosine similarity search.
Suitable for small-scale use (~30-50 vectors per document).
"""

from __future__ import annotations

import numpy as np

from src.models import Chunk


class LocalVectorIndex:
    """In-memory vector index backed by numpy arrays.

    Uses brute-force cosine similarity — appropriate for the small scale
    of individual documents (30-50 chunks).
    """

    def __init__(self):
        self._embeddings: np.ndarray = np.array([], dtype=np.float32)
        self._chunks: list[Chunk] = []
        self._chunk_ids: list[str] = []

    @property
    def size(self) -> int:
        return len(self._chunks)

    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks with their pre-computed embeddings to the index."""
        if len(chunks) == 0:
            return

        if self._embeddings.size == 0:
            self._embeddings = embeddings
        else:
            self._embeddings = np.vstack([self._embeddings, embeddings])

        self._chunks.extend(chunks)
        self._chunk_ids.extend(c.id for c in chunks)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[tuple[Chunk, float]]:
        """Search the index for the most similar chunks.

        Args:
            query_embedding: 1D numpy array for the query.
            top_k: number of results to return.
            threshold: minimum similarity score to include.

        Returns:
            List of (Chunk, similarity_score) tuples, sorted by descending similarity.
        """
        if self._embeddings.size == 0 or self.size == 0:
            return []

        # Compute cosine similarity
        # Normalize query
        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0:
            return []
        query_normalized = query_embedding / query_norm

        # Normalize all index embeddings
        norms = np.linalg.norm(self._embeddings, axis=1)
        # Avoid division by zero
        norms = np.where(norms == 0, 1, norms)
        embeddings_normalized = self._embeddings / norms[:, np.newaxis]

        # Cosine similarity = dot product of normalized vectors
        similarities = embeddings_normalized @ query_normalized

        # Filter by threshold
        mask = similarities >= threshold
        valid_indices = np.where(mask)[0]

        if len(valid_indices) == 0:
            return []

        # Sort by similarity (descending)
        sorted_indices = valid_indices[np.argsort(similarities[valid_indices])[::-1]]

        # Return top_k results
        results: list[tuple[Chunk, float]] = []
        for idx in sorted_indices[:top_k]:
            results.append((self._chunks[idx], float(similarities[idx])))

        return results

    def get_chunk_by_id(self, chunk_id: str) -> Chunk | None:
        """Retrieve a chunk by its ID."""
        for chunk in self._chunks:
            if chunk.id == chunk_id:
                return chunk
        return None

    def clear(self) -> None:
        """Remove all chunks and embeddings from the index."""
        self._embeddings = np.array([], dtype=np.float32)
        self._chunks.clear()
        self._chunk_ids.clear()
