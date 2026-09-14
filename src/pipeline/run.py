"""
End-to-end pipeline orchestration (stub).

Stages (see docs/ARCHITECTURE.md):
  1. OCR              -> src/ocr
  2. Chunking          -> src/chunking
  3. Glossary pass     -> src/glossary
  4. Per-chunk simplify -> src/simplify
  5. Embed & index      -> src/embed_index
  6. Hierarchical merge -> src/simplify (or a dedicated merge module, TBD)
  7. Q&A                -> src/qa

Each stage is left as a TODO until we've chosen the underlying models. Wiring this file up
end-to-end (even with dummy/mocked stages) early is useful for testing the overall flow before
any real model is plugged in.
"""

from pathlib import Path


def run_pipeline(document_path: Path, target_language: str = "hi"):
    """
    Run the full simplification pipeline on a document.

    Args:
        document_path: path to a scanned/photographed document (image or PDF).
        target_language: ISO code for the output language (e.g. "hi", "ta", "kn").

    Returns:
        dict with: chunks, glossary, chunk_explanations, overview, and a queryable index handle.
    """
    # 1. OCR
    # text, layout = extract_text(document_path)          # TODO: src/ocr

    # 2. Structure-aware chunking
    # chunks = chunk_by_structure(text, layout)            # TODO: src/chunking

    # 3. Glossary pass
    # glossary = extract_glossary(chunks)                  # TODO: src/glossary

    # 4. Per-chunk simplification
    # explanations = [simplify_chunk(c, glossary, target_language) for c in chunks]  # TODO: src/simplify

    # 5. Embed & index
    # index = build_local_index(chunks)                    # TODO: src/embed_index

    # 6. Hierarchical merge
    # overview = merge_explanations(explanations)           # TODO: src/simplify

    raise NotImplementedError("Pipeline stages not yet implemented — see TODOs above.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline.run <path-to-document>")
        sys.exit(1)

    run_pipeline(Path(sys.argv[1]))
