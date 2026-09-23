"""OCR & Layout Extraction module.

Converts photographed/scanned documents (images or PDFs) into structured text
with layout metadata (headings, paragraphs, tables) and per-region confidence scores.

Engines:
  - tesseract: default, fast, installed system-wide (eng/afr/osd packs available)
  - paddle: fallback for missing Tesseract language packs (e.g. Hindi) and
    when Tesseract fails — PaddleOCR ships multi-language PP-OCRv4 models
  - auto: try Tesseract, fall back to Paddle on any failure (default)
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

# PDF render DPI — 150 keeps ~91% conf at ~5x speed vs 300
_PDF_DPI = 150

# Tesseract uses 3-letter codes; map ISO-639-1 → tesseract where they differ
_TESSERACT_LANG_MAP = {
    "hi": "hin",
    "bn": "ben",
    "ta": "tam",
    "te": "tel",
    "kn": "kan",
    "ml": "mal",
    "mr": "mar",
    "gu": "guj",
    "pa": "pan",
    "ur": "urd",
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "es": "spa",
    "ar": "ara",
}

_paddle_instance = None  # lazy singleton — PaddleOCR model load is expensive


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


def _tesseract_lang(language: str) -> str:
    """Map an ISO language code to a Tesseract language string."""
    code = language.split("-")[0].lower()  # en-US → en
    return _TESSERACT_LANG_MAP.get(code, code)


def _tesseract_available(lang: str) -> bool:
    try:
        return lang in pytesseract.get_languages(config="")
    except Exception:
        return False


def _ocr_tesseract(image: Image.Image, language: str) -> tuple[str, float, list[Region]]:
    """Run Tesseract on a PIL image, return (full_text, avg_confidence, regions)."""
    tess_lang = _tesseract_lang(language)
    if not _tesseract_available(tess_lang):
        raise RuntimeError(
            f"Tesseract language pack {tess_lang!r} not installed "
            f"(available: {pytesseract.get_languages(config='')})"
        )

    data = pytesseract.image_to_data(
        image, lang=tess_lang, output_type=pytesseract.Output.DICT
    )

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

    return _regions_from_blocks(blocks, block_confs, block_bbox)


def _get_paddle(language: str = "en"):
    """Lazy-load a PaddleOCR instance (cached per language).

    PaddleOCR 3.x API: no show_log, use_textline_orientation replaces use_angle_cls.
    Disables oneDNN (mkldnn) which crashes with PIR attribute errors on some CPUs.
    """
    global _paddle_instance
    paddle_lang = _paddle_lang(language)
    # Cache key includes language — Hindi/ch models differ from English
    cache_key = f"paddle::{paddle_lang}"
    if getattr(_paddle_instance, "_qds_key", None) == cache_key:
        return _paddle_instance

    import os

    # Offline-friendly + work around oneDNN PIR crash on this host.
    # PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False is the flag that actually
    # disables mkldnn run_mode in PaddleOCR 3.x/paddlex (FLAGS_use_mkldnn alone
    # is insufficient — models still enter mkldnn and hit ConvertPirAttribute...).
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "False")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("GLOG_minloglevel", "2")  # silence paddle INFO logs

    from paddleocr import PaddleOCR

    try:
        ocr = PaddleOCR(
            lang=paddle_lang,
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
        )
    except TypeError:
        # Fallback for older paddleocr
        ocr = PaddleOCR(lang=paddle_lang)

    ocr._qds_key = cache_key  # type: ignore[attr-defined]
    _paddle_instance = ocr
    return ocr


def _paddle_lang(language: str) -> str:
    """Map an ISO language code to a PaddleOCR language code.

    PaddleOCR 3.x accepts ISO 639-1 codes directly (en, hi, mr, ur, fr, ...)
    and groups them into script packs internally (latin/devanagari/arabic/...).
    """
    code = language.split("-")[0].lower()
    # A few historical/3-letter aliases → ISO 639-1
    aliases = {
        "eng": "en", "hin": "hi", "mar": "mr", "urd": "ur",
        "fre": "fr", "fra": "fr", "ger": "de", "deu": "de",
        "spa": "es", "ara": "ar", "rus": "ru", "zho": "ch",
        "jpn": "japan", "kor": "korean",
    }
    return aliases.get(code, code)


def _ocr_paddle(image: Image.Image, language: str) -> tuple[str, float, list[Region]]:
    """Run PaddleOCR on a PIL image, return (full_text, avg_confidence, regions).

    Paddle's PP-OCRv handles scripts Tesseract packs lack (Devanagari etc.)
    and is the documented fallback when Tesseract fails.
    """
    import numpy as np

    ocr = _get_paddle(language)
    img_array = np.array(image)

    # PaddleOCR 3.x: predict(); older: ocr()
    if hasattr(ocr, "predict"):
        result = ocr.predict(img_array)
    else:
        try:
            result = ocr.ocr(img_array, cls=True)
        except TypeError:
            result = ocr.ocr(img_array)

    # Normalize result → list of (bbox, text, conf)
    # 3.x predict returns list of result dicts with 'rec_texts'/'rec_scores'/'dt_polys'
    # classic ocr() returns [ [ [bbox, (text, conf)], ... ] ]
    lines: list[tuple[tuple[int, int, int, int], str, float]] = []

    if result and isinstance(result[0], dict):
        r = result[0]
        polys = r.get("dt_polys") or r.get("rec_polys") or []
        texts = r.get("rec_texts") or []
        scores = r.get("rec_scores") or []
        for poly, text, score in zip(polys, texts, scores):
            if not text or not str(text).strip():
                continue
            pts = np.array(poly).reshape(-1, 2)
            box = (int(pts[:, 0].min()), int(pts[:, 1].min()),
                   int(pts[:, 0].max()), int(pts[:, 1].max()))
            lines.append((box, str(text).strip(), float(score)))
    elif result and result[0]:
        for item in result[0]:
            if not item or len(item) < 2:
                continue
            bbox, pair = item[0], item[1]
            text, conf = (pair if isinstance(pair, (list, tuple)) else (pair, 1.0))
            if not text or not str(text).strip():
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            box = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            lines.append((box, str(text).strip(), float(conf)))

    # Group Paddle lines into pseudo-blocks by vertical proximity (reading order)
    lines.sort(key=lambda x: (x[0][1], x[0][0]))
    blocks: dict[int, list[str]] = {}
    block_confs: dict[int, list[float]] = {}
    block_bbox: dict[int, tuple[int, int, int, int]] = {}
    current_block = 0
    prev_y1 = -1
    block_gap = 40  # pixels; lines closer than this belong to same paragraph

    for box, text, conf in lines:
        _, y0, _, y1 = box
        if prev_y1 >= 0 and (y0 - prev_y1) > block_gap:
            current_block += 1
        blocks.setdefault(current_block, []).append(text)
        # Normalize conf to 0–100 scale (paddle is 0–1, scale up)
        conf_pct = conf * 100.0 if conf <= 1.0 else conf
        block_confs.setdefault(current_block, []).append(conf_pct)
        bx0, by0, bx1, by1 = block_bbox.get(current_block, box)
        block_bbox[current_block] = (
            min(bx0, box[0]), min(by0, box[1]),
            max(bx1, box[2]), max(by1, box[3]),
        )
        prev_y1 = y1

    if not blocks:
        return "", 0.0, []

    return _regions_from_blocks(blocks, block_confs, block_bbox)


def _regions_from_blocks(
    blocks: dict[int, list[str]],
    block_confs: dict[int, list[float]],
    block_bbox: dict[int, tuple[int, int, int, int]],
) -> tuple[str, float, list[Region]]:
    """Shared block → Region assembly for both OCR engines.

    conf inputs are 0–100 (Tesseract native, Paddle scaled); output is 0–1.
    """
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
    return full_text, round(min(overall_conf, 1.0), 3), regions


def _ocr_image(
    image: Image.Image,
    language: str = "en",
    engine: str = "auto",
) -> tuple[str, float, list[Region]]:
    """OCR a PIL image with the selected engine.

    Args:
        image: source image.
        language: ISO-639-1 code (e.g. "en", "hi").
        engine: "tesseract" | "paddle" | "auto".

    Returns:
        (full_text, avg_confidence, regions)
    """
    errors: list[str] = []

    if engine in ("tesseract", "auto"):
        try:
            return _ocr_tesseract(image, language)
        except Exception as e:
            errors.append(f"tesseract: {e}")
            if engine == "tesseract":
                raise

    if engine in ("paddle", "auto"):
        try:
            return _ocr_paddle(image, language)
        except Exception as e:
            errors.append(f"paddle: {e}")
            if engine == "paddle":
                raise

    raise RuntimeError("All OCR engines failed: " + " | ".join(errors))


def extract_from_image(
    image_path: Path,
    language: str = "en",
    engine: str = "auto",
) -> Page:
    """Extract text and layout from a single image file."""
    img = Image.open(image_path)
    full_text, confidence, regions = _ocr_image(img, language=language, engine=engine)
    return Page(
        page_number=1,
        raw_text=full_text,
        layout_regions=regions,
        ocr_confidence=confidence,
    )


def extract_from_pdf(
    pdf_path: Path,
    language: str = "en",
    engine: str = "auto",
) -> list[Page]:
    """Extract text and layout from each page of a PDF."""
    doc = fitz.open(str(pdf_path))
    pages: list[Page] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Convert PDF page to image for OCR (150 DPI ≈ 5x faster, same conf)
        pix = page.get_pixmap(dpi=_PDF_DPI)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        full_text, confidence, regions = _ocr_image(
            img, language=language, engine=engine
        )
        pages.append(Page(
            page_number=page_num + 1,
            raw_text=full_text,
            layout_regions=regions,
            ocr_confidence=confidence,
        ))

    doc.close()
    return pages


def extract_document(
    document_path: Path,
    language: str = "en",
    engine: str = "auto",
) -> Document:
    """Main entry point: extract text and layout from a document (image or PDF).

    Args:
        document_path: path to an image or PDF file.
        language: ISO language code for OCR (also stored on the Document).
        engine: OCR engine — "tesseract", "paddle", or "auto" (default).

    Returns:
        Document with populated pages and layout metadata.
    """
    suffix = document_path.suffix.lower()

    if suffix == ".pdf":
        source_type = SourceType.PDF
        pages = extract_from_pdf(document_path, language=language, engine=engine)
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"):
        source_type = SourceType.PHOTO
        page = extract_from_image(document_path, language=language, engine=engine)
        pages = [page]
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return Document(
        id=document_path.stem,
        source_type=source_type,
        pages=pages,
        language=language,
    )
