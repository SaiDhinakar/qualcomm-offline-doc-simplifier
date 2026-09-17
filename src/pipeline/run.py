"""End-to-end pipeline orchestration.

Sequences the pipeline stages for two flows:
1. "Analyze a new document" — OCR through overview
2. "Ask a question about an already-analyzed document" — RAG Q&A
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.models import DocumentSession
from src.ocr.extract import extract_document
from src.chunking.chunker import chunk_document
from src.glossary.extractor import extract_glossary
from src.simplify.simplifier import simplify_chunk
from src.simplify.merge import merge_explanations
from src.simplify.llm import LLMBackend, get_llm_backend
from src.embed_index.embedding import EmbeddingBackend, get_embedding_backend
from src.embed_index.index import LocalVectorIndex
from src.embed_index.lifecycle import VectorStoreManager
from src.qa.engine import QAEngine


class Pipeline:
    """Full document analysis pipeline.

    Orchestrates: OCR → Chunking → Glossary → Simplify → Embed → Merge → Q&A
    """

    def __init__(
        self,
        llm_backend: str = "stub",
        llm_model_path: str | None = None,
        embedding_backend: str = "hash",
        embedding_model: str | None = None,
        session_timeout_minutes: int | None = None,
        **llm_kwargs,
    ):
        """Initialize the pipeline with configurable backends.

        Args:
            llm_backend: "stub" for development, "llamacpp" for llama.cpp.
            llm_model_path: path to LLM model file (required for llamacpp).
            embedding_backend: "hash" for development, "sentence-transformers" for real.
            embedding_model: model name for sentence-transformers backend.
            session_timeout_minutes: auto-expire sessions after this duration.
            **llm_kwargs: additional arguments for the LLM backend.
        """
        self._llm = get_llm_backend(llm_backend, model_path=llm_model_path, **llm_kwargs)
        self._embedder = get_embedding_backend(
            embedding_backend,
            **({"model_name": embedding_model} if embedding_model else {}),
        )
        self._session_manager = VectorStoreManager(
            session_timeout_minutes=session_timeout_minutes,
        )

    def analyze_document(
        self,
        document_path: Path,
        target_language: str = "hi",
    ) -> DocumentSession:
        """Run the full analysis pipeline on a document.

        Args:
            document_path: path to a scanned/photographed document (image or PDF).
            target_language: ISO code for the output language.

        Returns:
            DocumentSession with all analysis results.
        """
        # 1. OCR & Layout Extraction
        document = extract_document(document_path, language=target_language)

        # Create session
        session = self._session_manager.create_session(document.id)

        # 2. Structure-Aware Chunking
        chunks = chunk_document(document)
        session.chunks = chunks

        # 3. Glossary Extraction
        glossary = extract_glossary(chunks)
        session.glossary = glossary

        # 4. Per-Chunk Simplification
        for chunk in session.chunks:
            chunk.explanation = simplify_chunk(
                chunk,
                glossary,
                target_language,
                self._llm,
            )

        # 5. Embedding & Indexing
        index = LocalVectorIndex()
        if session.chunks:
            texts = [c.raw_text for c in session.chunks]
            embeddings = self._embedder.embed(texts)
            index.add_chunks(session.chunks, embeddings)
            # Update chunk embeddings
            for i, chunk in enumerate(session.chunks):
                chunk.embedding = embeddings[i].tolist()

        session.index_handle = index

        # 6. Hierarchical Merge
        overview = merge_explanations(
            session.chunks,
            target_language,
            self._llm,
        )
        session.overview = overview

        return session

    def ask_question(
        self,
        session: DocumentSession,
        question: str,
        target_language: str = "hi",
    ) -> dict[str, Any]:
        """Ask a question about an already-analyzed document.

        Args:
            session: the DocumentSession from analyze_document.
            question: free-text user question.
            target_language: ISO code for the answer language.

        Returns:
            Dict with "answer", "source_sections", and "status".
        """
        if session.index_handle is None:
            return {
                "answer": "Document has not been analyzed yet.",
                "source_sections": [],
                "status": "error",
            }

        qa_engine = QAEngine(
            index=session.index_handle,
            embedding_backend=self._embedder,
            llm=self._llm,
        )

        return qa_engine.answer(question, target_language)

    def get_session(self, document_id: str) -> DocumentSession | None:
        """Retrieve an active session by document ID."""
        return self._session_manager.get_session(document_id)

    def clear_session(self, document_id: str) -> bool:
        """Clear a session. Returns True if it existed."""
        return self._session_manager.clear_session(document_id)

    def clear_all_sessions(self) -> int:
        """Clear all sessions. Returns count cleared."""
        return self._session_manager.clear_all()


# Module-level convenience functions
_default_pipeline: Pipeline | None = None


def get_default_pipeline() -> Pipeline:
    """Get or create the default pipeline instance."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = Pipeline()
    return _default_pipeline


def run_pipeline(
    document_path: Path,
    target_language: str = "hi",
    **kwargs,
) -> DocumentSession:
    """Run the full simplification pipeline on a document.

    Convenience function using the default pipeline configuration.

    Args:
        document_path: path to a scanned/photographed document (image or PDF).
        target_language: ISO code for the output language.

    Returns:
        DocumentSession with all analysis results.
    """
    pipeline = get_default_pipeline()
    return pipeline.analyze_document(document_path, target_language)
