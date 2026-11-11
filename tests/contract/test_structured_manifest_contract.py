"""Contrato del manifiesto de la tabla estructurada (T029)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from proyecto_modelos_lenguaje.agent.structured import MANIFEST_NAME, build_structured_store
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.unit.agent.test_structured import ENTITIES, FACTS, UNITS, _write_jsonl

CONTRACTS = PROJECT_ROOT / "specs" / "014-rag-agent-memory-router" / "contracts"
SCHEMA = json.loads((CONTRACTS / "structured-manifest.schema.json").read_text(encoding="utf-8"))


def test_generated_manifest_satisfies_schema(tmp_path: Path) -> None:
    # Arrange
    gold = tmp_path / "gold"
    gold.mkdir()
    _write_jsonl(gold / "entities.jsonl", ENTITIES)
    _write_jsonl(gold / "facts.jsonl", FACTS)
    _write_jsonl(gold / "knowledge_units.jsonl", UNITS)
    (gold / "manifest.json").write_text("{}", encoding="utf-8")

    # Act
    build_structured_store(gold, tmp_path / "structured")
    payload = json.loads((tmp_path / "structured" / MANIFEST_NAME).read_text(encoding="utf-8"))

    # Assert
    jsonschema.validate(payload, SCHEMA)
