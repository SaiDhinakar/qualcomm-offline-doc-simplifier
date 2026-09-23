"""Tests for OCR confidence flagging (FR-4)."""

from src.models import Document, Page, Region, RegionType, SourceType
from src.ocr.confidence import analyze_ocr_quality


def test_high_confidence_no_flags():
    doc = Document(
        id="d1",
        source_type=SourceType.PDF,
        pages=[Page(page_number=1, raw_text="Clean text", ocr_confidence=0.95)],
    )
    report = analyze_ocr_quality(doc)
    assert report.has_issues is False
    assert len(report.flags) == 0
    assert report.overall_confidence > 0.9


def test_low_confidence_page_flagged():
    doc = Document(
        id="d1",
        source_type=SourceType.PDF,
        pages=[Page(page_number=1, raw_text="Blurry text", ocr_confidence=0.55)],
    )
    report = analyze_ocr_quality(doc)
    assert report.has_issues is True
    assert any(f.scope == "page" for f in report.flags)


def test_low_confidence_region_flagged():
    region = Region(
        region_type=RegionType.PARAGRAPH,
        bbox=(0, 0, 100, 50),
        text="garbled text",
        confidence=0.4,
    )
    doc = Document(
        id="d1",
        source_type=SourceType.PDF,
        pages=[Page(
            page_number=1,
            raw_text="OK text",
            ocr_confidence=0.9,
            layout_regions=[region],
        )],
    )
    report = analyze_ocr_quality(doc)
    assert report.has_issues is True
    assert any(f.scope == "region" for f in report.flags)


def test_multiple_pages_report():
    doc = Document(
        id="d1",
        source_type=SourceType.PDF,
        pages=[
            Page(page_number=1, raw_text="OK", ocr_confidence=0.95),
            Page(page_number=2, raw_text="Bad", ocr_confidence=0.4),
            Page(page_number=3, raw_text="OK", ocr_confidence=0.9),
        ],
    )
    report = analyze_ocr_quality(doc)
    assert report.page_confidences[2] == 0.4
    assert report.has_issues is True
    # overall confidence is average
    assert abs(report.overall_confidence - (0.95 + 0.4 + 0.9) / 3) < 0.01


def test_summary_string():
    doc = Document(
        id="d1",
        source_type=SourceType.PDF,
        pages=[Page(page_number=1, raw_text="Bad", ocr_confidence=0.3)],
    )
    report = analyze_ocr_quality(doc)
    summary = report.summary()
    assert "low-confidence" in summary.lower() or "LOW" in summary.upper()


def test_empty_document():
    doc = Document(id="d1", source_type=SourceType.PDF, pages=[])
    report = analyze_ocr_quality(doc)
    assert report.overall_confidence == 0.0
    assert report.has_issues is False
