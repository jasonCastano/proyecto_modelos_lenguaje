"""Unit tests for topic pages."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.gold.topics import build_topics, render_topic_page
from tests.unit.gold.test_units import _setup

ROOT = Path(__file__).resolve().parents[3]


def test_builds_topic_counts_and_page() -> None:
    config, taxonomy, document, chunk = _setup()
    from proyecto_modelos_lenguaje.gold.units import build_units

    units = build_units(document, [chunk], taxonomy, config.units)
    topics = build_topics(units, taxonomy)
    identity = next(topic for topic in topics if topic.topic_id == "identidad")
    assert identity.unit_count >= 1
    page = render_topic_page(identity, [unit for unit in units if unit.topic_id == "identidad"])
    assert "# Identidad y gobierno" in page
    assert "https://example.test/manuelita" in page
    assert "topic_id: identidad" in page
