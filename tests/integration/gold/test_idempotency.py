"""Integration tests for User Story 5: idempotency and audit."""

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


def test_idempotent_and_auditable(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    text = (
        "Manuelita produce azúcar, etanol y biocombustibles. "
        "La compañía tiene una capacidad de 125.000 toneladas de azúcar. "
        "Su misión es generar progreso y bienestar."
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
    silver_hash = hashlib.sha256((silver / "chunks.jsonl").read_bytes()).hexdigest()
    pipeline = build_gold_pipeline(tmp_path, silver)
    first = pipeline.build("2026-10-gold-05")
    units_path = tmp_path / "data" / "gold" / "knowledge_units.jsonl"
    facts_path = tmp_path / "data" / "gold" / "facts.jsonl"
    units_bytes = units_path.read_bytes()
    facts_bytes = facts_path.read_bytes()
    second = pipeline.build("2026-10-gold-06")
    assert first["units"] == second["units"]
    assert first["facts"] == second["facts"]
    assert units_path.read_bytes() == units_bytes
    assert facts_path.read_bytes() == facts_bytes
    verified = pipeline.verify_run("2026-10-gold-06", sample=50, seed=1)
    assert verified["passed"] is True
    assert verified["coverage_items"] == 24
    assert silver_hash == hashlib.sha256((silver / "chunks.jsonl").read_bytes()).hexdigest()
    units = [
        json.loads(line) for line in units_path.read_text(encoding="utf-8").splitlines() if line
    ]
    for unit in units[:50]:
        evidence = unit["evidence"][0]
        assert evidence["chunk_id"]
        assert evidence["url"]
