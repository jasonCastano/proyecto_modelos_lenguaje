"""Spec 026 (R8): comparación pura entre dos planes."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent.planning import Scenario, compare, optimize


def test_compare_reports_deltas_by_destination_product_commitment_and_margin() -> None:
    base = optimize(Scenario())
    scenario = optimize(Scenario(cane_delta_pct=-15))
    result = compare(base, scenario)
    assert result["synthetic"] is True
    assert set(result["mix_delta"]) == {"sugar", "ethanol"}
    sugar = result["mix_delta"]["sugar"]
    assert sugar["tonnes"] == scenario.mix["x_s"] - base.mix["x_s"]
    assert "points" in sugar
    assert {p["product"] for p in result["products_delta"]} == {"sugar", "ethanol", "power"}
    assert all(p["unit"] for p in result["products_delta"])
    assert result["margin_delta"] == scenario.margin - base.margin
    for row in result["commitments"]:
        assert {"id", "product", "met_base", "met_scenario", "gap_base", "gap_scenario"} <= set(row)


def test_compare_plan_with_itself_is_all_zero() -> None:
    plan = optimize(Scenario(cane_delta_pct=-10))
    result = compare(plan, plan)
    assert result["margin_delta"] == 0
    assert all(v["tonnes"] == 0 and v["points"] == 0 for v in result["mix_delta"].values())
    assert all(p["delta"] == 0 for p in result["products_delta"])


def test_compare_reports_gaps_when_scenario_is_infeasible() -> None:
    base = optimize(Scenario())
    infeasible = optimize(Scenario(cane_delta_pct=-50, steam_limit=0))
    assert infeasible.status == "infeasible_relaxed"
    result = compare(base, infeasible)
    assert any(row["gap_scenario"] > 0 for row in result["commitments"])
    assert any(not row["met_scenario"] for row in result["commitments"])
