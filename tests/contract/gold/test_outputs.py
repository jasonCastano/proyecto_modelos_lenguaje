"""Contract tests for generated gold outputs."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tests.contract.gold.conftest import load_schema
from tests.gold_helpers import (
    build_gold_pipeline,
    make_chunk,
    make_document,
    write_silver,
)


def _jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_generated_outputs_match_schemas(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    text = (
        "Manuelita es una organización agroindustrial. "
        "La compañía produce azúcar, etanol y biocombustibles. "
        "La capacidad de la planta es de 125.000 toneladas. "
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
    build_gold_pipeline(tmp_path, silver).build("2026-10-gold-08")
    gold = tmp_path / "data" / "gold"

    validators = {
        "knowledge-unit.schema.json": Draft202012Validator(
            load_schema("knowledge-unit.schema.json")
        ),
        "fact.schema.json": Draft202012Validator(load_schema("fact.schema.json")),
        "entity.schema.json": Draft202012Validator(load_schema("entity.schema.json")),
        "conflict.schema.json": Draft202012Validator(load_schema("conflict.schema.json")),
        "coverage.schema.json": Draft202012Validator(load_schema("coverage.schema.json")),
        "context-pack.schema.json": Draft202012Validator(load_schema("context-pack.schema.json")),
        "faq-seed.schema.json": Draft202012Validator(load_schema("faq-seed.schema.json")),
        "run-report.schema.json": Draft202012Validator(load_schema("run-report.schema.json")),
    }
    for unit in _jsonl(gold / "knowledge_units.jsonl"):
        validators["knowledge-unit.schema.json"].validate(unit)
    for fact in _jsonl(gold / "facts.jsonl"):
        validators["fact.schema.json"].validate(fact)
    for entity in _jsonl(gold / "entities.jsonl"):
        validators["entity.schema.json"].validate(entity)
    for conflict in _jsonl(gold / "conflicts.jsonl"):
        validators["conflict.schema.json"].validate(conflict)
    for seed in _jsonl(gold / "faq_seeds.jsonl"):
        validators["faq-seed.schema.json"].validate(seed)
    validators["coverage.schema.json"].validate(
        json.loads((gold / "coverage.json").read_text(encoding="utf-8"))
    )
    validators["context-pack.schema.json"].validate(
        json.loads((gold / "context_8000.json").read_text(encoding="utf-8"))
    )
    validators["run-report.schema.json"].validate(
        json.loads(
            (gold / "reports" / "2026-10-gold-08" / "quality.json").read_text(encoding="utf-8")
        )
    )
