"""Herramientas de planificación 21–25 (spec 025, T018, contracts/planning-tools.md)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.catalog import ToolArgsError, ToolContext, get_spec, run_read

PREFIX = "[Datos sintéticos de demostración · v1]"
NAMES = (
    "get_plant_state",
    "get_commitments",
    "search_operating_procedures",
    "simulate_production_scenario",
    "optimize_production_plan",
)


@pytest.mark.parametrize("number,name", list(enumerate(NAMES, start=21)))
def test_specs(number: int, name: str) -> None:
    spec = get_spec(name)
    assert spec.number == number and spec.kind == "read"
    assert spec.routes == frozenset({"planning"})
    assert spec.args_schema.model_config.get("extra") == "forbid"
    assert spec.mcp is False  # spec 028 (D1): la planificación nunca va al MCP


def test_state_and_commitments_are_labeled() -> None:
    ctx = ToolContext()
    state = run_read(get_spec("get_plant_state"), ctx, {})
    commitments = run_read(get_spec("get_commitments"), ctx, {"product": "ethanol"})
    assert state.startswith(PREFIX) and "Caña disponible" in state
    assert commitments.startswith(PREFIX) and "c-etanol-1" in commitments
    assert "c-azucar-1" not in commitments


def test_procedures_are_cited_as_s_and_neutralized() -> None:
    ctx = ToolContext()
    text = run_read(
        get_spec("search_operating_procedures"), ctx, {"query": "prioridad de compromisos"}
    )
    assert text.startswith(PREFIX) and "[S1] PO-01" in text
    assert ctx.trace.procedures[0]["label"] == "S1"


def test_optimize_records_plan_in_trace() -> None:
    ctx = ToolContext()
    text = run_read(get_spec("optimize_production_plan"), ctx, {"cane_delta_pct": -15})
    assert text.startswith(PREFIX) and "plan_id: p-" in text
    assert ctx.trace.plans and ctx.trace.plans[0]["status"] == "optimal"


def test_simulate_requires_share() -> None:
    ctx = ToolContext()
    text = run_read(
        get_spec("simulate_production_scenario"), ctx, {"cane_delta_pct": -15, "sugar_share": 0.9}
    )
    assert "Incumple: compromiso de etanol" in text
    with pytest.raises(ToolArgsError, match="Argumentos inválidos"):
        run_read(get_spec("simulate_production_scenario"), ctx, {"cane_delta_pct": -15})


@pytest.mark.parametrize(
    "args",
    [
        {"cane_delta_pct": -51},
        {"cane_delta_pct": 51},
        {"cane_quality": 8.5},
        {"steam_limit": -10},
        {"plant_id": "palma"},
        {"extra": 1},
    ],
)
def test_out_of_range_arguments_are_rejected(args: dict) -> None:
    with pytest.raises(ToolArgsError, match="Argumentos inválidos"):
        run_read(get_spec("optimize_production_plan"), ToolContext(), args)
