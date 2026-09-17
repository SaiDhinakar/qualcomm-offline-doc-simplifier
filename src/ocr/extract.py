"""OCR & Layout Extraction module.

Converts photographed/scanned documents (images or PDFs) into structured text
with layout metadata (headings, paragraphs, tables) and per-region confidence scores.
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from src.models import Document, Page, Region, RegionType, SourceType

# Heading detection patterns (numbered clauses, ALL CAPS lines, etc.)
_HEADING_PATTERNS = [
    re.compile(r"^\d+[\.\)]\s+\S"),          # "1. Something" or "1) Something"
    re.compile(r"^[IVX]+[\.\)]\s+\S"),       # "IV. Something"
    re.compile(r"^[A-Z][A-Z\s]{3,}$"),        # ALL CAPS lines (likely section headers)
    re.compile(r"^Section\s+\d+", re.I),       # "Section 3"
    re.compile(r"^Article\s+\d+", re.I),       # "Article 5"
    re.compile(r"^Chapter\s+\d+", re.I),       # "Chapter 2"
    re.compile(r"^Clause\s+\d+", re.I),        # "Clause 4.2"
    re.compile(r"^Schedule\s+\d+", re.I),      # "Schedule 1"
    re.compile(r"^Annexure\s+[A-Z\d]+", re.I), # "Annexure A"
]

_TABLE_LINE = re.compile(
    r"\t.*\t|^\|.*\|$",  # tab-separated or pipe-delimited
)


def _is_heading(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 120:
        return False
    return any(p.match(stripped) for p in _HEADING_PATTERNS)


def _is_table_line(text: str) -> bool:
    return bool(_TABLE_LINE.match(text.strip()))


def _classify_region(text: str, bbox: tuple[int, int, int, int]) -> RegionType:
    if _is_heading(text):
        return RegionType.HEADING
    if _is_table_line(text):
        return RegionType.TABLE
    return RegionType.PARAGRAPH


def _ocr_image(image: Image.Image) -> tuple[str, float, list[Region]]:
    """Run Tesseract on a PIL image, return (full_text, avg_confidence, regions)."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    # Build per-block text and confidence
    blocks: dict[int, list[str]] = {}
    block_confs: dict[int, list[float]] = {}
    block_bbox: dict[int, tuple[int, int, int, int]] = {}

    n = len(data["text"])
    for i in range(n):
        block_num = data["block_num"][i]
        txt = data["text"][i].strip()
        conf = float(data["conf"][i])
        if not txt or conf < 0:
            continue
        blocks.setdefault(block_num, []).append(txt)
        block_confs.setdefault(block_num, []).append(conf)

        x0 = data["left"][i]
        y0 = data["top"][i]
        x1 = x0 + data["width"][i]
        y1 = y0 + data["height"][i]
        if block_num not in block_bbox:
            block_bbox[block_num] = (x0, y0, x1, y1)
        else:
            bx0, by0, bx1, by1 = block_bbox[block_num]
            block_bbox[block_num] = (min(bx0, x0), min(by0, y0), max(bx1, x1), max(by1, y1))

    regions: list[Region] = []
    all_confs: list[float] = []
    for block_num in sorted(blocks.keys()):
        block_text = " ".join(blocks[block_num])
        confs = block_confs[block_num]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        bbox = block_bbox.get(block_num, (0, 0, 0, 0))
        region_type = _classify_region(block_text, bbox)
        regions.append(Region(
            region_type=region_type,
            bbox=bbox,
            text=block_text,
            confidence=round(avg_conf / 100.0, 3),
        ))
        all_confs.extend(confs)

    full_text = "\n".join(r.text for r in regions)
    overall_conf = sum(all_confs) / len(all_confs) / 100.0 if all_confs else 0.0
    return full_text, round(overall_conf, 3), regions


def extract_from_image(image_path: Path) -> Page:
    """Extract text and layout from a single image file."""
    img = Image.open(image_path)
    full_text, confidence, regions = _ocr_image(img)
    return Page(
        page_number=1,
        raw_text=full_text,
        layout_regions=regions,
        ocr_confidence=confidence,
    )


def extract_from_pdf(pdf_path: Path) -> list[Page]:
    """Extract text and layout from each page of a PDF."""
    doc = fitz.open(str(pdf_path))
    pages: list[Page] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Convert PDF page to image for OCR
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        full_text, confidence, regions = _ocr_image(img)
        pages.append(Page(
            page_number=page_num + 1,
            raw_text=full_text,
            layout_regions=regions,
            ocr_confidence=confidence,
        ))

    doc.close()
    return pages


def extract_document(document_path: Path, language: str = "hi") -> Document:
    """Main entry point: extract text and layout from a document (image or PDF).

    Args:
        document_path: path to an image or PDF file.
        language: target language code (used for Tesseract language hint).

    Returns:
        Document with populated pages and layout metadata.
    """
    suffix = document_path.suffix.lower()

    if suffix == ".pdf":
        source_type = SourceType.PDF
        pages = extract_from_pdf(document_path)
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"):
        source_type = SourceType.PHOTO
        page = extract_from_image(document_path)
        pages = [page]
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return Document(
        id=document_path.stem,
        source_type=source_type,
        pages=pages,
        language=language,
    )
