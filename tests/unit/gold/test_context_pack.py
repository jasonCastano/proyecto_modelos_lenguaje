"""Unit tests for context packs."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.gold.config import load_gold_config
from proyecto_modelos_lenguaje.gold.context_pack import build_context_packs
from proyecto_modelos_lenguaje.gold.models import CoverageEntry
from tests.unit.gold.test_conflicts import _unit

ROOT = Path(__file__).resolve().parents[3]


def test_context_packs_respect_budget_and_citations() -> None:
    config = load_gold_config(
        ROOT / "config" / "gold.toml",
        ROOT / "config" / "gold_taxonomy.toml",
        project_root=ROOT,
    )
    units = [
        _unit(index + 1, "Manuelita transforma recursos naturales " * 20) for index in range(5)
    ]
    coverage = [
        CoverageEntry(
            item_id="O-01",
            name="Productos y servicios",
            category="offer",
            status="covered",
            unit_ids=[unit.unit_id for unit in units],
            authority_counts={"first_party": 5},
            conflict_ids=[],
            gap_reason=None,
            recommendation=None,
        )
    ]
    packs = build_context_packs(units, coverage, config.context)
    assert len(packs) == 2
    for pack in packs:
        assert pack.tokens <= pack.budget_tokens
        assert len(set(pack.unit_ids)) == len(pack.unit_ids)
        assert all(block.citation for block in pack.blocks)
    small = set(packs[0].unit_ids)
    large = set(packs[1].unit_ids)
    assert small <= large
