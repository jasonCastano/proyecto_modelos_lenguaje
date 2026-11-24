"""Núcleo de planificación: simulador, LP, LP elástico, plan_card y validador (spec 025, T016)."""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from proyecto_modelos_lenguaje.agent.planning import (
    DECISION_PHRASE,
    SYNTHETIC_LABEL,
    Scenario,
    check_answer,
    fmt,
    load_plant,
    numbers_in,
    optimize,
    simulate,
)


@pytest.fixture(scope="module")
def data():
    return load_plant()


def test_simulation_balances_follow_the_model(data) -> None:
    # Arrange
    m = data.model
    scenario = Scenario(cane_delta_pct=-15)
    cane = data.state.cane_available * 0.85
    k = data.state.cane_quality / m.quality_ref

    # Act
    result = simulate(data, scenario, 0.9)

    # Assert
    assert result.x_s == pytest.approx(0.9 * cane)
    assert result.sugar == pytest.approx(m.sugar_yield * k * 0.9 * cane)
    expected_ethanol = (
        m.ethanol_from_molasses * m.molasses_yield * 0.9 * cane
        + m.ethanol_from_juice * k * 0.1 * cane
    )
    assert result.ethanol == pytest.approx(expected_ethanol)
    assert result.bagasse == pytest.approx(m.bagasse_yield * cane)


def test_simulation_reports_violations_without_raising(data) -> None:
    result = simulate(data, Scenario(cane_delta_pct=-15), 0.9)
    assert [v["constraint"] for v in result.violations] == ["compromiso de etanol"]
    assert result.violations[0]["excess"] > 0 and result.violations[0]["unit"] == "L"


def test_optimal_plan_with_binding_and_sensitivity(data) -> None:
    plan = optimize(Scenario(cane_delta_pct=-15), data)
    assert plan.status == "optimal"
    assert plan.binding is not None and plan.binding["constraint"] == "compromiso de etanol"
    assert all(item["unit"] and item["dual"] > 0 for item in plan.sensitivity)
    for product in ("sugar", "ethanol", "power"):
        assert plan.products[product] >= data.required(product) - 1e-6
    assert plan.mix["x_s"] + plan.mix["x_e"] <= data.state.cane_available * 0.85 + 1e-6


def test_infeasible_reports_shortfalls_and_keeps_capacities(data) -> None:
    plan = optimize(Scenario(cane_delta_pct=-35), data)
    assert plan.status == "infeasible_relaxed"
    assert plan.shortfalls and all(item["missing"] > 0 for item in plan.shortfalls)
    assert plan.mix["x_s"] + plan.mix["x_e"] <= data.state.cane_available * 0.65 + 1e-6
    assert "No se supuso capacidad adicional" in plan.plan_card


def test_plan_id_is_stable_and_well_formed(data) -> None:
    first = optimize(Scenario(cane_delta_pct=-15), data)
    second = optimize(Scenario(cane_delta_pct=-15), data)
    other = optimize(Scenario(cane_delta_pct=-10), data)
    assert re.fullmatch(r"p-[0-9a-f]{8}", first.plan_id)
    assert first.plan_id == second.plan_id != other.plan_id


def test_plan_card_has_label_decision_and_alternative(data) -> None:
    card = optimize(Scenario(cane_delta_pct=-15), data).plan_card
    assert SYNTHETIC_LABEL in card and DECISION_PHRASE in card
    assert "Alternativa «mezcla actual»" in card and "plan_id: p-" in card


def test_scenario_rejects_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        Scenario(cane_delta_pct=-80)
    with pytest.raises(ValidationError):
        Scenario(cane_quality=20)
    with pytest.raises(ValidationError):
        Scenario(steam_limit=-1)
    with pytest.raises(ValidationError):
        Scenario(unknown=1)  # type: ignore[call-arg]


def test_fmt_uses_es_co_separators() -> None:
    assert fmt(46750.4) == "46.750"
    assert fmt(13.25, 1) == "13,2" or fmt(13.25, 1) == "13,3"
    assert fmt(1_234_567.891, 2) == "1.234.567,89"


def test_numbers_in_ignores_plan_id_and_week() -> None:
    assert numbers_in("plan_id: p-0aed9288 · semana 2026-W48 · 46.750 t") == ["46.750"]


def test_check_answer_accepts_grounded_numbers(data) -> None:
    card = optimize(Scenario(cane_delta_pct=-15), data).plan_card
    sugar_line = next(line for line in card.splitlines() if line.startswith("• Azúcar"))
    answer = (
        f"Recomiendo este plan. {sugar_line} {SYNTHETIC_LABEL}. Usa la mezcla 1 y la 2. "
        f"{DECISION_PHRASE}"
    )
    assert check_answer(answer, [card]).ok


def test_check_answer_rejects_invented_numbers_and_missing_label(data) -> None:
    card = optimize(Scenario(cane_delta_pct=-15), data).plan_card
    invented = check_answer(
        f"El margen será 987.654 millones. {SYNTHETIC_LABEL}. {DECISION_PHRASE}", [card]
    )
    assert not invented.ok and invented.ungrounded == ("987.654",)
    unlabeled = check_answer("Recomiendo producir más azúcar.", [card])
    assert not unlabeled.ok and unlabeled.missing_label and unlabeled.missing_decision


def test_check_answer_accepts_rounded_and_english_forms() -> None:
    source = "Margen total: COP 6.253,63 millones · etanol 910.000 L"
    assert check_answer(
        f"6.253,6 millones y 910,000 L. {SYNTHETIC_LABEL}. {DECISION_PHRASE}", [source]
    ).ok
