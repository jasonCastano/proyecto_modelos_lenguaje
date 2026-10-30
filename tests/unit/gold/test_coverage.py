"""Unit tests for the 24-item coverage matrix."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.gold.config import load_gold_config
from proyecto_modelos_lenguaje.gold.coverage import build_coverage, coverage_summary
from proyecto_modelos_lenguaje.gold.taxonomy import load_taxonomy
from tests.unit.gold.test_conflicts import _unit

ROOT = Path(__file__).resolve().parents[3]


def _taxonomy():
    return load_taxonomy(
        ROOT / "config" / "gold_taxonomy.toml",
        coverage_path=ROOT / "config" / "coverage-items.toml",
        min_score=2,
    )


def test_coverage_states_and_24_items() -> None:
    config = load_gold_config(
        ROOT / "config" / "gold.toml",
        ROOT / "config" / "gold_taxonomy.toml",
        project_root=ROOT,
    )
    taxonomy = _taxonomy()
    units = []
    for index in range(3):
        unit = _unit(index + 1, f"Manuelita es una empresa agroindustrial {index}.")
        unit.coverage_item_ids = ["I-01"]
        units.append(unit)
    third = _unit(4, "Manuelita produce azúcar.", "third_party")
    third.coverage_item_ids = ["O-01"]
    units.append(third)
    entries = build_coverage(units, [], taxonomy, config.coverage)
    assert len(entries) == 24
    by_id = {entry.item_id: entry for entry in entries}
    assert by_id["I-01"].status == "covered"
    assert by_id["O-01"].status == "partial"
    assert by_id["H-06"].status == "missing"
    assert by_id["H-06"].gap_reason
    assert coverage_summary(entries) == {"covered": 1, "partial": 1, "missing": 22}
