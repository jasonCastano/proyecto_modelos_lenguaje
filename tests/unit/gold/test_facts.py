"""Unit tests for deterministic fact extraction."""

from __future__ import annotations

from dataclasses import replace

from proyecto_modelos_lenguaje.gold.facts import extract_facts, normalize_value
from proyecto_modelos_lenguaje.gold.units import build_units
from tests.unit.gold.test_units import _setup


def test_extracts_number_unit_fact() -> None:
    config, taxonomy, document, chunk = _setup()
    chunk = replace(
        chunk,
        text="Manuelita tiene una capacidad de 125.000 toneladas de azúcar en su planta.",
    )
    units = build_units(document, [chunk], taxonomy, config.units)
    facts = extract_facts(units[0], taxonomy)
    assert facts
    fact = facts[0]
    assert fact.subject_label == "Manuelita"
    assert fact.attribute == "capacidad"
    assert fact.value_normalized == "125000"
    assert fact.unit == "toneladas"
    assert units[0].unit_type == "fact"
    assert units[0].fact_id == fact.fact_id


def test_no_fact_without_subject() -> None:
    config, taxonomy, document, chunk = _setup()
    chunk = replace(chunk, text="La capacidad de la planta es de 125.000 toneladas.")
    units = build_units(document, [chunk], taxonomy, config.units)
    assert extract_facts(units[0], taxonomy) == []


def test_normalizes_values() -> None:
    assert normalize_value("125.000") == "125000"
    assert normalize_value("3,5") == "3.5"
