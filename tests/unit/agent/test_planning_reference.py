"""Óptimo de referencia por malla frente al LP (spec 025, T017, R9, SC-001)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent import planning_reference
from proyecto_modelos_lenguaje.agent.planning import Scenario, load_plant, optimize
from proyecto_modelos_lenguaje.agent.planning_reference import reference_optimum
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

BATTERY = PROJECT_ROOT / "tests" / "fixtures" / "agent" / "planning_scenarios.jsonl"


@pytest.mark.parametrize(
    "args", [{"cane_delta_pct": -15}, {"cane_quality": 12.0}, {"steam_limit": 30000}]
)
def test_reference_matches_lp_within_grid_step(args: dict) -> None:
    # Arrange
    data = load_plant()
    scenario = Scenario(**args)

    # Act
    ref = reference_optimum(data, scenario, points=801)
    plan = optimize(scenario, data)

    # Assert: el LP nunca es peor que la malla y la malla queda a < 1 % del LP
    assert ref.feasible
    assert plan.margin >= ref.margin - 1.0
    assert ref.margin >= 0.99 * plan.margin


def test_reference_detects_infeasibility() -> None:
    ref = reference_optimum(load_plant(), Scenario(cane_delta_pct=-35), points=401)
    assert not ref.feasible and ref.margin is None


def test_reference_does_not_import_the_solver() -> None:
    tree = ast.parse(Path(planning_reference.__file__).read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "optimize" not in imported and not any("scipy" in m for m in modules | imported)


def test_battery_has_ten_feasible_and_two_infeasible_and_lp_meets_sc001() -> None:
    # Arrange
    data = load_plant()
    cases = [json.loads(line) for line in BATTERY.read_text(encoding="utf-8").splitlines()]

    # Act / Assert
    assert len(cases) == 12 and sum(not c["feasible"] for c in cases) == 2
    for case in cases:
        plan = optimize(Scenario(**case["scenario"]), data)
        if case["feasible"]:
            assert plan.status == "optimal", case["id"]
            assert plan.margin >= 0.99 * case["reference_margin"], case["id"]
        else:
            assert plan.status == "infeasible_relaxed" and plan.shortfalls, case["id"]
