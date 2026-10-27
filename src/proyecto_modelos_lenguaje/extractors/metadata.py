"""MIME detection and publication-date parsing."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

_EXTENSIONS = {
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "application/pdf": ".pdf",
    "application/xml": ".xml",
    "text/xml": ".xml",
    "application/json": ".json",
    "text/plain": ".txt",
    "text/vtt": ".vtt",
    "text/csv": ".csv",
    "application/gzip": ".gz",
    "application/zip": ".zip",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def normalize_content_type(value: str | None) -> str:
    if not value:
        return ""
    return value.split(";", 1)[0].strip().lower()


def detect_media_type(content_type: str | None, data: bytes) -> str:
    declared = normalize_content_type(content_type)
    head = data[:2048].lstrip()
    if head.startswith(b"%PDF-") or declared == "application/pdf":
        return "application/pdf"
    if head.startswith(b"\x1f\x8b"):
        return "application/gzip"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if declared in {"text/html", "application/xhtml+xml"}:
        return "text/html"
    lowered = head[:512].lower()
    if lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html"):
        return "text/html"
    if lowered.startswith(b"<?xml"):
        return "application/xml"
    if head.startswith(b"WEBVTT"):
        return "text/vtt"
    if declared in {"application/xml", "text/xml", "application/rss+xml", "application/atom+xml"}:
        return "application/xml"
    if declared in {"application/json", "application/ld+json"}:
        return "application/json"
    if declared.startswith("text/"):
        return declared
    if declared:
        return declared
    if lowered.startswith(b"{") or lowered.startswith(b"["):
        return "application/json"
    return "application/octet-stream"


def extension_for(media_type: str) -> str:
    normalized = normalize_content_type(media_type)
    if normalized in _EXTENSIONS:
        return _EXTENSIONS[normalized]
    if normalized.startswith("text/"):
        return ".txt"
    if normalized.startswith("image/"):
        return ".bin"
    return ".bin"


def parse_published_at(value: str | None) -> str | None:
    """Normalize common publication-date formats to ISO 8601 UTC."""
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(cleaned)
        except TypeError, ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_allowed_media_type(media_type: str, allowed: tuple[str, ...] | list[str]) -> bool:
    normalized = normalize_content_type(media_type)
    return any(normalized == normalize_content_type(item) for item in allowed)
