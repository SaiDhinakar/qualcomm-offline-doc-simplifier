"""LLM interface for the simplification pipeline.

Provides an abstraction over different LLM backends (stub, llama.cpp, etc.)
with a common interface for generating text completions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        """Generate a text completion for the given prompt."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is ready to use."""
        ...


class StubLLM(LLMBackend):
    """Stub LLM for development/testing. Returns deterministic responses."""

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        return (
            "[Stub LLM - replace with real model]\n"
            "This is a placeholder explanation. The real model will provide "
            "a plain-language explanation of the document content."
        )

    def is_available(self) -> bool:
        return True


class LlamaCppLLM(LLMBackend):
    """LLM backend using llama-cpp-python for local inference."""

    def __init__(self, model_path: str, n_ctx: int = 4096, n_gpu_layers: int = 0):
        self._model_path = model_path
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._llama = None

    def _load(self) -> None:
        if self._llama is not None:
            return
        try:
            from llama_cpp import Llama
            self._llama = Llama(
                model_path=self._model_path,
                n_ctx=self._n_ctx,
                n_gpu_layers=self._n_gpu_layers,
                verbose=False,
            )
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Install it with: uv pip install llama-cpp-python"
            )

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> str:
        self._load()
        assert self._llama is not None
        output = self._llama(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>", "\n\n"],
        )
        return output["choices"][0]["text"].strip()

    def is_available(self) -> bool:
        try:
            import os

            from llama_cpp import Llama  # noqa: F401
            return os.path.exists(self._model_path)
        except ImportError:
            return False


def get_llm_backend(
    backend: str = "stub",
    model_path: str | None = None,
    **kwargs,
) -> LLMBackend:
    """Factory function to get an LLM backend.

    Args:
        backend: "stub" for development, "llamacpp" for llama.cpp.
        model_path: path to model file (required for llamacpp).
        **kwargs: additional arguments passed to the backend constructor.

    Returns:
        An LLMBackend instance.
    """
    if backend == "stub":
        return StubLLM()
    elif backend == "llamacpp":
        if not model_path:
            raise ValueError("model_path is required for llamacpp backend")
        return LlamaCppLLM(model_path=model_path, **kwargs)
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")
