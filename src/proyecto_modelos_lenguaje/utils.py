"""Small shared helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime

_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def utcnow() -> str:
    """Return the current UTC time as an ISO 8601 string with a trailing Z."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def human_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def slugify(value: str, *, maximum: int = 63) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:maximum].strip("-") or "campaign"
