"""Pruebas del origen estructurado de solo lectura (T027, FR-012, FR-013)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.structured import (
    DATABASE_NAME,
    StructuredExistsError,
    StructuredGoldError,
    StructuredInvalidError,
    StructuredStore,
    build_structured_store,
)

ENTITIES = [
    {
        "entity_id": "ent_a",
        "canonical_name": "Manuelita",
        "aliases": ["Ingenio Manuelita", "Grupo Manuelita"],
        "entity_type": "company",
    },
    {
        "entity_id": "ent_b",
        "canonical_name": "Palmar de Altamira",
        "aliases": [],
        "entity_type": "subsidiary",
    },
    {
        "entity_id": "ent_c",
        "canonical_name": "Océanos",
        "aliases": ["Oceanos"],
        "entity_type": "subsidiary",
    },
]


def _fact(fact_id: str, subject: str, label: str, attribute: str, value: str, unit: str) -> dict:
    return {
        "fact_id": fact_id,
        "subject_id": subject,
        "subject_label": label,
        "attribute": attribute,
        "value": value,
        "year": None,
        "unit_id": unit,
        "status": "current",
        "evidence": [
            {
                "url": f"https://www.manuelita.com/{fact_id}",
                "title": "Fuente",
                "authority": "first_party",
            }
        ],
    }


FACTS = [
    _fact("fact_1", "ent_a", "Manuelita", "Colombia", "1864", "unit_1"),
    _fact("fact_2", "ent_a", "Manuelita", "colombiana tiene", "25", "unit_2"),
    _fact("fact_3", "ent_b", "Palmar de Altamira", "procesar", "35.000", "unit_3"),
    _fact("fact_4", "ent_b", "Palmar de Altamira", "produjo a partir", "41.000", "unit_4"),
    _fact("fact_5", "ent_c", "Océanos", "exportacion", "2018", "unit_5"),
    {**_fact("fact_6", "ent_c", "Océanos", "obsoleto", "1", "unit_6"), "status": "superseded"},
]

UNITS = [
    {"unit_id": "unit_1", "text": "Manuelita inició operaciones en Colombia en 1864 en Palmira."},
    {"unit_id": "unit_2", "text": "En Vale do Paraná la colombiana tiene el 25 por ciento."},
    {"unit_id": "unit_3", "text": "Capacidad instalada para procesar 35.000 toneladas al año."},
    {"unit_id": "unit_4", "text": "La energía se produjo a partir de 41.000 toneladas de biomasa."},
    {"unit_id": "unit_5", "text": "Océanos exporta camarón desde 2018."},
]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), "utf-8")


@pytest.fixture()
def gold(tmp_path: Path) -> Path:
    directory = tmp_path / "gold"
    directory.mkdir()
    _write_jsonl(directory / "entities.jsonl", ENTITIES)
    _write_jsonl(directory / "facts.jsonl", FACTS)
    _write_jsonl(directory / "knowledge_units.jsonl", UNITS)
    (directory / "manifest.json").write_text('{"run_id": "test"}', encoding="utf-8")
    return directory


@pytest.fixture()
def store(gold: Path, tmp_path: Path) -> StructuredStore:
    target = tmp_path / "structured"
    build_structured_store(gold, target)
    with StructuredStore(target, gold_dir=gold) as opened:
        yield opened


def test_build_loads_only_accepted_facts_with_citations(gold: Path, tmp_path: Path) -> None:
    # Act
    manifest = build_structured_store(gold, tmp_path / "structured")

    # Assert
    assert manifest.entity_count == 3
    assert manifest.fact_count == 5
    assert manifest.citation_count == 5
    connection = sqlite3.connect(tmp_path / "structured" / DATABASE_NAME)
    orphans = connection.execute(
        "SELECT COUNT(*) FROM facts WHERE fact_id NOT IN (SELECT fact_id FROM citations)"
    ).fetchone()[0]
    connection.close()
    assert orphans == 0


def test_gold_is_read_only(gold: Path, tmp_path: Path) -> None:
    # Arrange
    before = {path.name: path.read_bytes() for path in gold.iterdir()}

    # Act
    build_structured_store(gold, tmp_path / "structured")

    # Assert
    assert {path.name: path.read_bytes() for path in gold.iterdir()} == before


def test_existing_store_requires_force(gold: Path, tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "structured"
    build_structured_store(gold, target)

    # Act / Assert
    with pytest.raises(StructuredExistsError):
        build_structured_store(gold, target)
    assert build_structured_store(gold, target, force=True).fact_count == 5


def test_missing_or_empty_gold_is_rejected(tmp_path: Path) -> None:
    # Arrange
    empty = tmp_path / "gold"
    empty.mkdir()
    (empty / "manifest.json").write_text("{}", encoding="utf-8")
    (empty / "entities.jsonl").write_text("", encoding="utf-8")

    # Act / Assert
    with pytest.raises(StructuredGoldError):
        build_structured_store(tmp_path / "missing", tmp_path / "out")
    with pytest.raises(StructuredGoldError):
        build_structured_store(empty, tmp_path / "out")


def test_store_rejects_outdated_gold(gold: Path, tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "structured"
    build_structured_store(gold, target)
    (gold / "manifest.json").write_text('{"run_id": "otro"}', encoding="utf-8")

    # Act / Assert
    with pytest.raises(StructuredInvalidError, match="no corresponde al oro"):
        StructuredStore(target, gold_dir=gold)


def test_readonly_connection_cannot_write(store: StructuredStore) -> None:
    # Act / Assert
    with pytest.raises(sqlite3.OperationalError):
        store._connection.execute("DELETE FROM facts")


def test_list_entities_filters_by_type(store: StructuredStore) -> None:
    # Act
    subsidiaries = store.list_entities("subsidiary")

    # Assert
    assert [entity.canonical_name for entity in subsidiaries] == ["Océanos", "Palmar de Altamira"]
    assert len(store.list_entities()) == 3


def test_get_facts_by_alias_and_attribute(store: StructuredStore) -> None:
    # Act
    by_alias = store.get_facts(subject="Ingenio Manuelita")
    by_accentless = store.get_facts(subject="oceanos")
    by_attribute = store.get_facts(subject="Palmar de Altamira", attribute="procesar")

    # Assert
    assert {fact.fact_id for fact in by_alias} == {"fact_1", "fact_2"}
    assert [fact.fact_id for fact in by_accentless] == ["fact_5"]
    assert [fact.value for fact in by_attribute] == ["35.000"]
    assert by_attribute[0].citations[0].url.endswith("fact_3")
    assert "35.000 toneladas" in by_attribute[0].snippet
    assert store.get_facts(subject="Empresa inexistente") == []


def test_search_facts_ranks_by_term_overlap(store: StructuredStore) -> None:
    # Act
    results = store.search_facts("¿Cuántas toneladas de biomasa usó Palmar de Altamira?")

    # Assert
    assert results[0].fact_id == "fact_4"
    assert results[0].score > results[-1].score or len(results) == 1
    assert store.search_facts("¿?") == []
