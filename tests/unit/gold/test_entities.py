"""Unit tests for entity consolidation."""

from __future__ import annotations

from proyecto_modelos_lenguaje.gold.entities import build_entities
from proyecto_modelos_lenguaje.gold.units import build_units
from tests.unit.gold.test_units import _setup


def test_builds_canonical_entities_and_aliases() -> None:
    config, taxonomy, document, chunk = _setup()
    units = build_units(document, [chunk], taxonomy, config.units)
    entities = build_entities(units, taxonomy)
    manuelita = next(entity for entity in entities if entity.canonical_name == "Manuelita")
    assert manuelita.entity_id.startswith("ent_")
    assert "Ingenio Manuelita" in manuelita.aliases
    assert manuelita.unit_ids
    assert any(unit.entity_ids for unit in units)
