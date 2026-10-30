"""Integration test for User Story 3: coverage matrix."""

from __future__ import annotations

import json
from pathlib import Path

from tests.gold_helpers import (
    build_gold_pipeline,
    make_chunk,
    make_document,
    write_silver,
)


def test_builds_24_item_coverage(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    text = (
        "La misión de Manuelita es generar progreso y bienestar. "
        "Su visión es ser una organización agroindustrial sostenible. "
        "La misión y la visión guían el trabajo de Manuelita en las comunidades."
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
        section_title="Identidad",
    )
    silver = write_silver(tmp_path, [document], [chunk])
    report = build_gold_pipeline(tmp_path, silver).build("2026-10-gold-03")
    assert report["coverage"]["covered"] >= 1
    assert report["coverage"]["missing"] >= 1
    coverage = json.loads(
        (tmp_path / "data" / "gold" / "coverage.json").read_text(encoding="utf-8")
    )
    assert len(coverage["items"]) == 24
    by_id = {item["item_id"]: item for item in coverage["items"]}
    assert by_id["I-01"]["status"] == "covered"
    assert by_id["H-06"]["status"] == "missing"
    assert by_id["H-06"]["gap_reason"]
    assert (tmp_path / "data" / "gold" / "coverage.md").is_file()
