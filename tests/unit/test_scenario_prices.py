"""Spec 026 (R7): precios opcionales en el escenario sin cambiar los planes vigentes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from proyecto_modelos_lenguaje.agent.planning import Scenario, load_plant, optimize, plan_id_for

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agent"
SCENARIOS = [
    json.loads(line)
    for line in (FIXTURES / "planning_scenarios.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
BASELINE = json.loads((FIXTURES / "planning_baseline_026.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("field", ["price_sugar_pct", "price_ethanol_pct", "price_power_pct"])
def test_price_range_is_minus_50_to_50(field: str) -> None:
    assert getattr(Scenario(**{field: -50}), field) == -50
    assert getattr(Scenario(**{field: 50}), field) == 50
    for bad in (-51, 51):
        with pytest.raises(ValidationError):
            Scenario(**{field: bad})


def test_scenario_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Scenario(price_coffee_pct=10)  # type: ignore[call-arg]


@pytest.mark.parametrize("case", SCENARIOS, ids=[c["id"] for c in SCENARIOS])
def test_plans_without_prices_are_identical_to_spec_025(case: dict) -> None:
    plan = optimize(Scenario(**case["scenario"])).to_dict(card=False)
    assert json.loads(json.dumps(plan, sort_keys=True)) == BASELINE[case["id"]]


def test_higher_ethanol_price_does_not_reduce_ethanol_cane() -> None:
    base = optimize(Scenario(cane_delta_pct=-15))
    pricier = optimize(Scenario(cane_delta_pct=-15, price_ethanol_pct=30))
    assert pricier.mix["x_e"] >= base.mix["x_e"] - 1e-6
    assert pricier.margin > base.margin


def test_plan_id_changes_only_with_a_price() -> None:
    data = load_plant()
    plain = Scenario(cane_delta_pct=-15)
    assert plan_id_for(data, plain) == BASELINE["p02"]["plan_id"]
    assert plan_id_for(data, Scenario(cane_delta_pct=-15, price_power_pct=10)) != plan_id_for(
        data, plain
    )
