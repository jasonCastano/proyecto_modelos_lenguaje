"""PDF extraction with pypdf: page text, outline and repeated-line removal."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from pypdf import PdfReader

from ..models import ExtractedBlock, ExtractedDocument, QualityFlag

_OUTLINE_SUFFIX = re.compile(r"^\d+\s*[-_ ]*")
_TABLE_GAP = re.compile(r"\S\s{2,}\S")


def _clean_line(line: str) -> str:
    return " ".join(line.split())


def _outline_entries(reader: PdfReader) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    def walk(items: list[Any], level: int = 1) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, level + 1)
                continue
            title = getattr(item, "title", None)
            if not title:
                continue
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                page = None
            entries.append(
                {
                    "title": _OUTLINE_SUFFIX.sub("", str(title)).replace("_", " ").strip(),
                    "page": page,
                    "level": min(level, 6),
                }
            )

    try:
        walk(reader.outline)
    except Exception:
        return []
    return entries


def _remove_repeated_lines(pages: list[list[str]], ratio: float) -> list[str]:
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update({_clean_line(line).lower() for line in lines if _clean_line(line)})
    threshold = max(2, int(len(pages) * ratio))
    repeated = {line for line, count in counts.items() if count >= threshold and len(line) <= 80}
    page_number = re.compile(r"^(p[aá]gina|page)\s+\d+\s+(de|of)\s+\d+$", re.IGNORECASE)
    cleaned_pages: list[str] = []
    for lines in pages:
        kept = [
            line
            for line in lines
            if _clean_line(line).lower() not in repeated
            and not page_number.fullmatch(_clean_line(line))
        ]
        cleaned_pages.append("\n".join(kept).strip())
    return cleaned_pages


def _table_ratio(text: str) -> float:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    table_lines = sum(1 for line in lines if _TABLE_GAP.search(line) or " | " in line)
    return table_lines / len(lines)


def _multi_column_suspect(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 20:
        return False
    short = sum(1 for line in lines if len(line) < 45)
    return short / len(lines) > 0.45


def extract_pdf(
    data: bytes,
    *,
    repeated_line_ratio: float = 0.30,
    table_line_ratio: float = 0.30,
) -> ExtractedDocument:
    from io import BytesIO

    from pypdf.errors import FileNotDecryptedError

    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                return ExtractedDocument(
                    title=None,
                    blocks=[],
                    metadata={"pages": len(reader.pages)},
                    skip_reason="encrypted_pdf",
                    flags={QualityFlag.ENCRYPTED_PDF.value},
                )
        except Exception:
            return ExtractedDocument(
                title=None,
                blocks=[],
                metadata={"pages": 0},
                skip_reason="encrypted_pdf",
                flags={QualityFlag.ENCRYPTED_PDF.value},
            )
    page_lines: list[list[str]] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except FileNotDecryptedError:
            return ExtractedDocument(
                title=None,
                blocks=[],
                metadata={"pages": len(reader.pages)},
                skip_reason="encrypted_pdf",
                flags={QualityFlag.ENCRYPTED_PDF.value},
            )
        except Exception:
            text = ""
        page_lines.append(text.splitlines())
    cleaned_pages = _remove_repeated_lines(page_lines, repeated_line_ratio)
    blocks: list[ExtractedBlock] = []
    flags: set[str] = set()
    combined = "\n".join(cleaned_pages)
    if not combined.strip():
        flags.add(QualityFlag.SCANNED_PDF.value)
        return ExtractedDocument(
            title=None,
            blocks=[],
            metadata={"pages": len(reader.pages), "outline": _outline_entries(reader)},
            skip_reason="scanned_pdf",
            flags=flags,
        )
    for number, text in enumerate(cleaned_pages, start=1):
        text = text.strip()
        if text:
            blocks.append(ExtractedBlock(text=text, page=number))
            if _table_ratio(text) > table_line_ratio:
                flags.add(QualityFlag.TABLE_HEAVY.value)
            if _multi_column_suspect(text):
                flags.add(QualityFlag.MULTI_COLUMN_SUSPECT.value)
    title = None
    try:
        raw_title = reader.metadata.get("/Title") if reader.metadata else None
    except Exception:
        raw_title = None
    if raw_title:
        title = " ".join(str(raw_title).split())
    outline = _outline_entries(reader)
    if not title and outline:
        title = outline[0]["title"]
    return ExtractedDocument(
        title=title,
        blocks=blocks,
        metadata={"pages": len(reader.pages), "outline": outline},
        skip_reason=None,
        flags=flags,
    )
