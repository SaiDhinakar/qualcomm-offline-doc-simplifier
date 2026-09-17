"""Per-Chunk Simplifier & Hierarchical Merge module."""

from src.simplify.llm import LLMBackend, StubLLM, get_llm_backend
from src.simplify.merge import merge_explanations
from src.simplify.simplifier import simplify_chunk

__all__ = [
    "LLMBackend",
    "StubLLM",
    "get_llm_backend",
    "merge_explanations",
    "simplify_chunk",
]
