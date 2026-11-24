"""Datos sintéticos de planificación (spec 025, T015, R10, contracts/planning-tools.md)."""

from __future__ import annotations

import json
import sys

import pytest

from proyecto_modelos_lenguaje.agent.planning import DATA_ROOT, Scenario, load_plant, optimize
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import generate_planning_data

V1 = DATA_ROOT / "v1"


def test_check_is_idempotent() -> None:
    # Act
    code = generate_planning_data.main(["--seed", "2026", "--version", "v1", "--check"])

    # Assert
    assert code == 0


def test_build_is_deterministic() -> None:
    assert generate_planning_data.build(2026, "v1") == generate_planning_data.build(2026, "v1")
    assert generate_planning_data.build(2026, "v1") != generate_planning_data.build(7, "v1")


@pytest.mark.parametrize("name", ["plant_cana.json", "state.json", "commitments.json"])
def test_files_are_marked_synthetic(name: str) -> None:
    payload = json.loads((V1 / name).read_text(encoding="utf-8"))
    assert payload["synthetic"] is True
    assert payload["seed"] == 2026 and payload["version"] == "v1"


def test_ranges_and_generic_counterparties() -> None:
    data = load_plant()
    assert 9 <= data.state.cane_quality <= 16
    assert all(0 <= item.capacity_factor <= 1 for item in data.state.equipment)
    assert all(c.priority in (1, 2, 3) for c in data.commitments)
    assert all(
        c.counterparty.startswith(("Cliente", "Mayorista", "Comercializador"))
        for c in data.commitments
    )
    assert "manuelita" not in " ".join(c.counterparty.lower() for c in data.commitments)
    assert len(data.procedures) == 10


def test_procedures_and_card_are_synthetic() -> None:
    card = (V1 / "DATA_CARD.md").read_text(encoding="utf-8")
    assert "sintéticos" in card and "Sostenibilidad 2023-2024" in card
    for path in (V1 / "procedures").glob("*.md"):
        assert "synthetic: true" in path.read_text(encoding="utf-8")


def test_calibration_base_slack_and_minus_15_active() -> None:
    # Arrange
    data = load_plant()
    base = generate_planning_data._production(
        json.loads((V1 / "plant_cana.json").read_text(encoding="utf-8")),
        data.state.cane_available,
        data.state.cane_quality,
        generate_planning_data.REFERENCE_SHARE,
    )

    # Act
    minus15 = optimize(Scenario(cane_delta_pct=-15), data)

    # Assert: holgura ≥ 10 % en la semana base y −15 % factible con algo activo
    for product in ("sugar", "ethanol", "power"):
        assert base[product] >= 1.1 * data.required(product), product
    assert optimize(Scenario(), data).status == "optimal"
    assert minus15.status == "optimal" and minus15.sensitivity
