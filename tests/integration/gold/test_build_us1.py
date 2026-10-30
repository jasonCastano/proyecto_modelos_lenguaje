"""Integration test for User Story 1: units and topics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.gold_helpers import (
    build_gold_pipeline,
    make_chunk,
    make_document,
    write_silver,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_builds_units_and_topics(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    text = (
        "Manuelita es una organización agroindustrial diversificada. "
        "La compañía produce azúcar, etanol y biocombustibles. "
        "Su misión es generar progreso y bienestar en las comunidades."
    )
    document = make_document(
        doc_id, title="Manuelita", url="https://example.test/a", text_hash="b" * 64
    )
    chunk = make_chunk(
        doc_id,
        chunk_id=f"{doc_id}-s000-c0000",
        text=text,
        title="Manuelita",
        url="https://example.test/a",
        section_title="Manuelita",
    )
    silver = write_silver(tmp_path, [document], [chunk])
    before = hashlib.sha256((silver / "chunks.jsonl").read_bytes()).hexdigest()
    pipeline = build_gold_pipeline(tmp_path, silver)
    report = pipeline.build("2026-10-gold-01")
    after = hashlib.sha256((silver / "chunks.jsonl").read_bytes()).hexdigest()

    assert report["input_documents"] == 1
    assert report["units"] >= 3
    assert before == after
    units = _jsonl(tmp_path / "data" / "gold" / "knowledge_units.jsonl")
    assert units
    assert all(unit["evidence"] for unit in units)
    assert all(unit["url"] and unit["title"] and unit["section_path"] for unit in units)
    assert all(unit["text"] in text for unit in units)
    assert (tmp_path / "data" / "gold" / "topics").is_dir()
    assert list((tmp_path / "data" / "gold" / "topics").glob("*.md"))
