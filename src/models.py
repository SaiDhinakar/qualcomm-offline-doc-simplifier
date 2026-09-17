"""Shared data models for the Qualcomm Doc Simplifier pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    PHOTO = "photo"
    SCAN = "scan"
    PDF = "pdf"


class RegionType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    FOOTER = "footer"


class Region(BaseModel):
    region_type: RegionType
    bbox: tuple[int, int, int, int]  # (x0, y0, x1, y1) in pixels
    text: str
    confidence: float = Field(ge=0.0, le=1.0)


class Page(BaseModel):
    page_number: int
    raw_text: str
    layout_regions: list[Region] = Field(default_factory=list)
    ocr_confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class Chunk(BaseModel):
    id: str
    document_id: str
    page_number: int
    section_id: str | None = None
    order_index: int
    raw_text: str
    embedding: list[float] = Field(default_factory=list)
    explanation: str | None = None


class GlossaryEntry(BaseModel):
    term: str
    definition: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class Document(BaseModel):
    id: str
    source_type: SourceType
    pages: list[Page] = Field(default_factory=list)
    language: str = "hi"


class DocumentSession(BaseModel):
    document_id: str
    chunks: list[Chunk] = Field(default_factory=list)
    glossary: list[GlossaryEntry] = Field(default_factory=list)
    overview: str = ""
    index_handle: Any = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def clear(self) -> None:
        self.chunks.clear()
        self.glossary.clear()
        self.overview = ""
        self.index_handle = None
