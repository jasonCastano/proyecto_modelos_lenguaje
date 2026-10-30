"""Unit tests for FAQ seeds."""

from __future__ import annotations

from proyecto_modelos_lenguaje.gold.faq import build_faq_seeds
from proyecto_modelos_lenguaje.gold.models import CoverageEntry, Entity, Topic
from tests.unit.gold.test_conflicts import _unit


def test_generates_seed_from_coverage_and_topic() -> None:
    unit = _unit(1, "Manuelita produce azúcar y etanol.")
    coverage = [
        CoverageEntry(
            item_id="O-01",
            name="Productos y servicios",
            category="offer",
            status="covered",
            unit_ids=[unit.unit_id],
            authority_counts={"first_party": 1},
            conflict_ids=[],
            gap_reason=None,
            recommendation=None,
        )
    ]
    topic = Topic(
        topic_id="productos",
        title="Productos y servicios",
        description="Productos",
        coverage_item_ids=["O-01"],
        order=1,
        unit_count=1,
        status="partial",
    )
    entity = Entity(
        schema_version="1.0",
        entity_id="ent_0123456789abcdef",
        canonical_name="Manuelita",
        aliases=[],
        entity_type="company",
        description=None,
        unit_ids=[unit.unit_id],
        coverage_item_ids=["O-01"],
    )
    seeds = build_faq_seeds([unit], coverage, [topic], [entity])
    assert seeds
    assert any("productos" in seed.question.lower() for seed in seeds)
    assert all(seed.evidence_unit_ids for seed in seeds)
    assert len({seed.seed_id for seed in seeds}) == len(seeds)
