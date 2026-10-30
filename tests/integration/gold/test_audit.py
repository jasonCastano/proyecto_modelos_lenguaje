"""Integration test for User Story 5: lineage audit."""

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


def test_units_trace_to_silver_chunks(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    text = (
        "Manuelita es una organización agroindustrial diversificada. "
        "La compañía produce azúcar, etanol y biocombustibles."
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
    build_gold_pipeline(tmp_path, silver).build("2026-10-gold-07")
    units = [
        json.loads(line)
        for line in (tmp_path / "data" / "gold" / "knowledge_units.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    chunks = {chunk["chunk_id"]: chunk for chunk in [chunk]}
    for unit in units:
        evidence = unit["evidence"][0]
        source = chunks[evidence["chunk_id"]]
        assert unit["text"] in source["text"]
        assert unit["url"] == source["url"]
    after = hashlib.sha256((silver / "chunks.jsonl").read_bytes()).hexdigest()
    assert before == after
