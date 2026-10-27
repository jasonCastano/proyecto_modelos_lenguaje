"""Coverage evidence inference and the 24-item matrix."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from .catalog import Catalog
from .models import Confidence, CoverageItem, CoverageRow


@dataclass(frozen=True, slots=True)
class Evidence:
    item_id: str
    confidence: str
    note: str


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents)


def _matches(keyword: str, haystack: str) -> bool:
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, haystack) is not None


def infer_evidence(
    text: str,
    *,
    title: str | None,
    url: str,
    items: Iterable[CoverageItem],
) -> tuple[Evidence, ...]:
    """Infer which of the 24 items an artifact supports."""
    body = normalize_text(text or "")
    headline = normalize_text(f"{title or ''} {url.replace('-', ' ').replace('_', ' ')}")
    evidence: list[Evidence] = []
    for item in items:
        keywords = [normalize_text(keyword) for keyword in item.keywords if keyword.strip()]
        body_hits = [keyword for keyword in keywords if _matches(keyword, body)]
        headline_hits = [keyword for keyword in keywords if _matches(keyword, headline)]
        hits = sorted(set(body_hits + headline_hits))
        if not hits:
            continue
        direct = len(hits) >= 3 or bool(headline_hits)
        confidence = Confidence.DIRECT.value if direct else Confidence.SUPPORTING.value
        evidence.append(
            Evidence(
                item_id=item.item_id,
                confidence=confidence,
                note=f"keywords: {', '.join(hits[:5])}",
            )
        )
    return tuple(evidence)


def build_matrix(catalog: Catalog, campaign_id: str) -> tuple[CoverageRow, ...]:
    return catalog.coverage_matrix(campaign_id)


def summarize(rows: Iterable[CoverageRow]) -> dict[str, int]:
    summary = {"covered": 0, "partial": 0, "missing": 0, "total": 0}
    for row in rows:
        summary[row.status] += 1
        summary["total"] += 1
    return summary


def gaps(rows: Iterable[CoverageRow]) -> list[dict[str, str]]:
    return [
        {"item_id": row.item_id, "reason": row.gap_reason or "Sin justificación registrada."}
        for row in rows
        if row.status == "missing"
    ]
