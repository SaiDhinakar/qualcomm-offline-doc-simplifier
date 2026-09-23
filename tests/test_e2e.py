"""True end-to-end test: file on disk → OCR → chunks → glossary → simplify → embed → Q&A.

Unlike test_integration.py (which bypasses OCR by building a Document from a string),
this test starts from a real file path and exercises every pipeline stage through
Pipeline.analyze_document / Pipeline.ask_question.

Uses stub/hash backends by default for CI speed. Set QDS_E2E_REAL=1 to run with
Ollama + fastembed (requires local Ollama server and fastembed installed).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.pipeline.run import Pipeline

# Golden sample content (mirrors tests/fixtures/golden_sample.txt facts)
E2E_SAMPLE_TEXT = """1. POLICY OVERVIEW

This insurance policy ("Policy") is issued by ABC Insurance Company ("Company")
to the Insured. The Insured means the person named in the Schedule of this Policy.
The Policy Period means the duration of coverage from January 1, 2025 to
December 31, 2025. The Sum Assured means the maximum amount payable under
this Policy.

2. PREMIUM PAYMENT

The Insured must pay the Premium of $1,200 per year. Payment is due on the
first day of each month. Late payment incurs a penalty of 5% per month.

3. COVERAGE

The Company shall cover losses arising from natural disasters, theft, and
accidental damage. Coverage is subject to a deductible of $500 per claim.

4. CLAIMS PROCESS

Claims must be filed within 30 days of the incident. The Insured must provide
documentation including photographs and a police report where applicable.

5. TERMINATION

Either party may terminate this Policy with 30 days written notice. Upon
termination, unused premium is refunded on a pro-rata basis.
"""


def _make_sample_pdf(path: Path) -> Path:
    """Write a one-page PDF containing E2E_SAMPLE_TEXT (real file for OCR)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # insert_textbox handles wrapping; small font keeps it on one page
    rect = fitz.Rect(50, 50, 562, 742)
    page.insert_textbox(rect, E2E_SAMPLE_TEXT, fontsize=9, fontname="helv")
    doc.save(str(path))
    doc.close()
    return path


def _has_real_backends() -> bool:
    if os.environ.get("QDS_E2E_REAL") != "1":
        return False
    try:
        from src.simplify.llm import OllamaLLM
        if not OllamaLLM().is_available():
            return False
    except Exception:
        return False
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a real PDF sample for OCR (module-scoped for speed)."""
    out_dir = tmp_path_factory.mktemp("e2e")
    return _make_sample_pdf(out_dir / "e2e_policy.pdf")


def test_e2e_file_to_answer_stub(sample_pdf: Path):
    """Full path: PDF file → OCR → chunk → glossary → simplify → embed → Q&A."""
    assert sample_pdf.exists() and sample_pdf.stat().st_size > 0

    pipe = Pipeline(
        llm_backend="stub",
        embedding_backend="hash",
        ocr_engine="tesseract",
        similarity_threshold=-1.0,  # hash embeddings aren't semantic; accept all hits
    )
    session = pipe.analyze_document(sample_pdf, target_language="en")

    # OCR produced real text from the file
    assert session.chunks, "expected chunks from OCR'd PDF"
    total_chars = sum(len(c.raw_text) for c in session.chunks)
    assert total_chars > 500, f"OCR extracted too little text: {total_chars} chars"

    # Glossary: unquoted "The Insured means..." pattern (FR-7)
    terms = [e.term for e in session.glossary]
    assert "Insured" in terms, f"glossary missing Insured: {terms}"
    assert "Premium" in terms or "Policy Period" in terms or "Sum Assured" in terms

    # Per-chunk explanations generated
    assert all(c.explanation for c in session.chunks)

    # Overview non-empty
    assert session.overview and len(session.overview) > 0

    # OCR confidence present (FR-4)
    assert session.ocr_report is not None
    assert session.ocr_report.overall_confidence > 0.5

    # Q&A: retrieval + generation against the indexed document
    result = pipe.ask_question(
        session,
        "What is the premium amount?",
        target_language="en",
    )
    assert result["status"] == "answered"
    assert result["answer"]
    # Source sections should point at real chunks
    assert result["source_sections"], "expected source section ids"


def test_e2e_file_to_answer_real_backends(sample_pdf: Path):
    """Same flow with Ollama + fastembed when QDS_E2E_REAL=1 and services up.

    Skipped by default so CI stays hermetic.
    """
    if not _has_real_backends():
        pytest.skip("set QDS_E2E_REAL=1 with Ollama + fastembed to run real e2e")

    pipe = Pipeline(
        llm_backend="ollama",
        embedding_backend="fastembed",
        ocr_engine="tesseract",
    )
    session = pipe.analyze_document(sample_pdf, target_language="en")

    assert session.chunks
    assert session.overview
    # Real embeddings: dimension should be 384 (bge-small), not hash default only
    assert session.index_handle is not None
    assert session.index_handle.size == len(session.chunks)

    result = pipe.ask_question(
        session,
        "What is the premium amount?",
        target_language="en",
    )
    assert result["status"] == "answered"
    # Grounded fact check — the answer must mention the number from the doc
    assert "$1,200" in result["answer"] or "1,200" in result["answer"], (
        f"answer missing premium figure: {result['answer'][:300]}"
    )


def test_e2e_image_path_ocr(tmp_path: Path):
    """Also cover the image (photo) input path, not just PDF."""
    # Render the sample PDF to PNG so we exercise extract_from_image
    import fitz
    from PIL import Image

    pdf = _make_sample_pdf(tmp_path / "img_src.pdf")
    doc = fitz.open(str(pdf))
    pix = doc[0].get_pixmap(dpi=150)
    png_path = tmp_path / "e2e_page.png"
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.save(str(png_path))
    doc.close()

    pipe = Pipeline(
        llm_backend="stub",
        embedding_backend="hash",
        ocr_engine="tesseract",
        similarity_threshold=-1.0,
    )
    session = pipe.analyze_document(png_path, target_language="en")

    assert session.chunks
    assert sum(len(c.raw_text) for c in session.chunks) > 300
    assert session.glossary, "expected glossary terms from image OCR"
