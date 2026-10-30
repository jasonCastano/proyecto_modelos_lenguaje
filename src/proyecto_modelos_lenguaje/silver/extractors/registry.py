"""Format registry: dispatch a bronze artifact to the right extractor."""

from __future__ import annotations

from ..bronze import BronzeArtifact
from ..models import ExtractedBlock, ExtractedDocument
from .html import extract_html
from .pdf import extract_pdf
from .spreadsheet import extract_xlsx
from .structured import extract_json, extract_xml
from .vtt import extract_vtt

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def extract(
    artifact: BronzeArtifact,
    data: bytes,
    *,
    table_line_ratio: float = 0.30,
    repeated_line_ratio: float = 0.30,
) -> ExtractedDocument:
    media_type = artifact.media_type.split(";", 1)[0].strip().lower()
    if media_type == "text/html":
        document = extract_html(data, url=artifact.url_canonical)
    elif media_type == "application/pdf":
        document = extract_pdf(
            data,
            table_line_ratio=table_line_ratio,
            repeated_line_ratio=repeated_line_ratio,
        )
    elif media_type == "text/vtt":
        document = extract_vtt(data, title=artifact.title)
    elif media_type == "application/json":
        document = extract_json(data, title=artifact.title)
    elif media_type in {"application/xml", "text/xml"}:
        document = extract_xml(data, url=artifact.url_canonical)
    elif media_type == _XLSX:
        document = extract_xlsx(data, title=artifact.title)
    elif media_type in {"text/plain", "text/csv"}:
        text = data.decode("utf-8", errors="replace")
        blocks = [ExtractedBlock(text=text)] if text.strip() else []
        document = ExtractedDocument(
            title=artifact.title,
            blocks=blocks,
            skip_reason=None if blocks else "no_text",
        )
    else:
        return ExtractedDocument(
            title=artifact.title,
            blocks=[],
            metadata={"media_type": media_type},
            skip_reason="unsupported_media_type",
        )
    document.metadata["extractor"] = media_type
    if not document.title and artifact.title:
        document.title = artifact.title
    return document
