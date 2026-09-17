"""On-Device Q&A / RAG module.

Answers free-text user questions using only retrieved, relevant document content.
Uses embedding-based retrieval followed by LLM-based answer generation.
"""

from __future__ import annotations

from src.embed_index.embedding import EmbeddingBackend
from src.embed_index.index import LocalVectorIndex
from src.simplify.llm import LLMBackend


class QAEngine:
    """Retrieval-Augmented Generation engine for document Q&A.

    Flow:
    1. Embed the question using the same model as indexing.
    2. Retrieve top-k relevant chunks from the local index.
    3. If best similarity < threshold, respond that the document doesn't address the question.
    4. Otherwise, pass question + retrieved chunks to LLM for grounded answer.
    """

    def __init__(
        self,
        index: LocalVectorIndex,
        embedding_backend: EmbeddingBackend,
        llm: LLMBackend,
        similarity_threshold: float = 0.15,
        top_k: int = 5,
    ):
        self._index = index
        self._embedder = embedding_backend
        self._llm = llm
        self._similarity_threshold = similarity_threshold
        self._top_k = top_k

    def answer(
        self,
        question: str,
        target_language: str = "hi",
        language_names: dict[str, str] | None = None,
    ) -> dict[str, str | list[str]]:
        """Answer a question about the analyzed document.

        Args:
            question: free-text user question.
            target_language: ISO language code for the answer.
            language_names: optional mapping of ISO codes to full language names.

        Returns:
            Dict with:
                - "answer": the generated answer string
                - "source_sections": list of section IDs the answer was derived from
                - "status": "answered" or "not_addressed"
        """
        lang_names = language_names or {
            "hi": "Hindi", "ta": "Tamil", "kn": "Kannada", "te": "Telugu",
            "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "ml": "Malayalam",
            "pa": "Punjabi", "ur": "Urdu", "en": "English",
        }
        target_name = lang_names.get(target_language, target_language)

        # 1. Embed the question
        question_embedding = self._embedder.embed_single(question)

        # 2. Retrieve top-k relevant chunks
        results = self._index.search(
            question_embedding,
            top_k=self._top_k,
            threshold=self._similarity_threshold,
        )

        # 3. Check if any result is relevant
        if not results:
            return {
                "answer": (
                    "This document does not appear to address your question. "
                    "Please try asking about a different aspect of the document."
                ),
                "source_sections": [],
                "status": "not_addressed",
            }

        # 4. Build context from retrieved chunks
        context_parts: list[str] = []
        source_sections: list[str] = []
        for chunk, score in results:
            section_hint = f"[Section: {chunk.section_id}] " if chunk.section_id else ""
            context_parts.append(f"{section_hint}{chunk.raw_text}")
            if chunk.section_id and chunk.section_id not in source_sections:
                source_sections.append(chunk.section_id)

        context = "\n\n---\n\n".join(context_parts)

        prompt = (
            f"You are a document question-answering assistant. "
            f"Answer the user's question based ONLY on the provided document content.\n\n"
            f"RULES:\n"
            f"1. Answer ONLY based on the document content below — do NOT use general knowledge\n"
            f"2. Preserve ALL numbers, dates, amounts, and percentages exactly as they appear\n"
            f"3. If the document content doesn't fully answer the question, say so\n"
            f"4. Be concise and direct\n"
            f"5. Do NOT provide legal or financial advice\n"
            f"6. Answer in {target_name}\n\n"
            f"Document content:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer in {target_name}:"
        )

        answer_text = self._llm.generate(prompt, max_tokens=512, temperature=0.3)

        return {
            "answer": answer_text,
            "source_sections": source_sections,
            "status": "answered",
        }
