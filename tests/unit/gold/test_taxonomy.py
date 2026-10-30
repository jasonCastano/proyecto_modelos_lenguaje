"""Unit tests for the controlled taxonomy and entities."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.gold.taxonomy import load_taxonomy

ROOT = Path(__file__).resolve().parents[3]


def _taxonomy():
    return load_taxonomy(
        ROOT / "config" / "gold_taxonomy.toml",
        coverage_path=ROOT / "config" / "coverage-items.toml",
        min_score=2,
    )


def test_classifies_topics() -> None:
    taxonomy = _taxonomy()
    assert taxonomy.classify("La misión y visión de Manuelita").topic.topic_id == "identidad"
    assert (
        taxonomy.classify("Manuelita produce azúcar, etanol y biocombustibles").topic.topic_id
        == "productos"
    )
    assert (
        taxonomy.classify("La certificación ISO y BASC de la planta").topic.topic_id
        == "certificaciones"
    )


def test_unknown_text_falls_back_to_general() -> None:
    taxonomy = _taxonomy()
    match = taxonomy.classify("Texto sin palabras clave del negocio")
    assert match.topic.topic_id == "general"
    assert match.uncertain is True


def test_finds_entities_with_word_boundaries() -> None:
    taxonomy = _taxonomy()
    specs = taxonomy.find_entities("Fundación Manuelita y Manuelita Azúcar y Energía")
    names = {spec.canonical_name for spec in specs}
    assert "Manuelita" in names
    assert "Fundación Manuelita" in names
    assert "Manuelita Azúcar y Energía" in names
