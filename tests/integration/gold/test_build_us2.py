"""Integration test for User Story 2: entities, facts and conflicts."""

from __future__ import annotations

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


def test_builds_entities_facts_and_conflicts(tmp_path: Path) -> None:
    first = "doc_0123456789abcdef"
    second = "doc_1111111111111111"
    docs = [
        make_document(first, title="Manuelita", url="https://example.test/a", text_hash="b" * 64),
        make_document(
            second,
            title="Manuelita",
            url="https://third.test/a",
            text_hash="c" * 64,
            authority="third_party",
        ),
    ]
    chunks = [
        make_chunk(
            first,
            chunk_id=f"{first}-s000-c0000",
            text="Manuelita tiene una capacidad de 125.000 toneladas de azúcar en su planta.",
            title="Manuelita",
            url="https://example.test/a",
            section_title="Productos",
        ),
        make_chunk(
            second,
            chunk_id=f"{second}-s000-c0000",
            text="Manuelita reporta una capacidad de 120.000 toneladas de azúcar en su planta.",
            title="Manuelita",
            url="https://third.test/a",
            section_title="Productos",
            authority="third_party",
        ),
    ]
    silver = write_silver(tmp_path, docs, chunks)
    report = build_gold_pipeline(tmp_path, silver).build("2026-10-gold-02")
    assert report["entities"] >= 1
    assert report["facts"] >= 2
    assert report["conflicts"] >= 1

    entities = _jsonl(tmp_path / "data" / "gold" / "entities.jsonl")
    facts = _jsonl(tmp_path / "data" / "gold" / "facts.jsonl")
    conflicts = _jsonl(tmp_path / "data" / "gold" / "conflicts.jsonl")
    assert any(entity["canonical_name"] == "Manuelita" for entity in entities)
    assert any(fact["attribute"] == "capacidad" for fact in facts)
    assert conflicts[0]["status"] == "resolved"
    assert conflicts[0]["reason"] == "official_source"
    assert (tmp_path / "data" / "gold" / "glossary.md").is_file()
