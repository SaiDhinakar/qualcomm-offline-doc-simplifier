"""OCR confidence flagging (FR-4).

Surfaces low-confidence OCR pages/regions so explanations don't silently
misrepresent unclear text.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.models import Document, Page

# Confidence thresholds
LOW_CONFIDENCE_THRESHOLD = 0.7
VERY_LOW_CONFIDENCE_THRESHOLD = 0.5


@dataclass
class LowConfidenceFlag:
    page_number: int
    scope: str  # "page" or "region"
    text: str
    confidence: float
    bbox: tuple[int, int, int, int] | None = None
    message: str = ""

    def __str__(self) -> str:
        loc = f"Page {self.page_number}"
        if self.bbox:
            loc += f" @ {self.bbox}"
        return (
            f"[LOW OCR CONFIDENCE {self.confidence:.0%}] {loc} ({self.scope}): "
            f"{self.message} — \"{self.text[:80]}...\""
        )


@dataclass
class OCRQualityReport:
    flags: list[LowConfidenceFlag] = field(default_factory=list)
    page_confidences: dict[int, float] = field(default_factory=dict)
    overall_confidence: float = 1.0

    @property
    def has_issues(self) -> bool:
        return len(self.flags) > 0

    @property
    def worst_pages(self) -> list[int]:
        return sorted(
            self.page_confidences.items(),
            key=lambda x: x[1],
        )[:3]

    def summary(self) -> str:
        if not self.has_issues:
            return f"OCR quality OK (overall confidence: {self.overall_confidence:.0%})"
        lines = [f"OCR quality: {len(self.flags)} low-confidence area(s) found"]
        for flag in self.flags[:10]:
            lines.append(f"  - {flag}")
        if len(self.flags) > 10:
            lines.append(f"  ... and {len(self.flags) - 10} more")
        return "\n".join(lines)


def _flag_page(page: Page, report: OCRQualityReport) -> None:
    if page.ocr_confidence < VERY_LOW_CONFIDENCE_THRESHOLD:
        msg = "Very low OCR confidence — text may be garbled"
    elif page.ocr_confidence < LOW_CONFIDENCE_THRESHOLD:
        msg = "Low OCR confidence — text may contain errors"
    else:
        return

    report.flags.append(LowConfidenceFlag(
        page_number=page.page_number,
        scope="page",
        text=page.raw_text[:200],
        confidence=page.ocr_confidence,
        message=msg,
    ))


def _flag_regions(page: Page, report: OCRQualityReport) -> None:
    for region in page.layout_regions:
        if region.confidence < LOW_CONFIDENCE_THRESHOLD:
            msg = (
                "Very low confidence region — possibly blurred or skewed"
                if region.confidence < VERY_LOW_CONFIDENCE_THRESHOLD
                else "Low confidence region"
            )
            report.flags.append(LowConfidenceFlag(
                page_number=page.page_number,
                scope="region",
                text=region.text,
                confidence=region.confidence,
                bbox=region.bbox,
                message=msg,
            ))


def analyze_ocr_quality(document: Document) -> OCRQualityReport:
    """Analyze OCR quality across a document and flag low-confidence areas.

    Args:
        document: Document with populated pages.

    Returns:
        OCRQualityReport with flags for low-confidence pages/regions.
    """
    report = OCRQualityReport()

    if not document.pages:
        report.overall_confidence = 0.0
        return report

    confidences: list[float] = []
    for page in document.pages:
        report.page_confidences[page.page_number] = page.ocr_confidence
        confidences.append(page.ocr_confidence)
        _flag_page(page, report)
        _flag_regions(page, report)

    report.overall_confidence = sum(confidences) / len(confidences)
    return report
