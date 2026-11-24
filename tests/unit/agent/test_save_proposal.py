"""Guardar la propuesta desde ``last_plan`` (spec 025, T019, R13)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.actions import (
    STALE_PROPOSAL,
    ActionArgsError,
    execute_action,
    save_proposal,
    validate_args,
)
from proyecto_modelos_lenguaje.agent.catalog import get_spec
from proyecto_modelos_lenguaje.agent.planning import Scenario, optimize


@pytest.fixture
def plan() -> dict:
    return optimize(Scenario(cane_delta_pct=-15)).to_dict()


def test_spec_is_write_number_26_without_mcp() -> None:
    spec = get_spec("save_production_proposal")
    assert spec.number == 26 and spec.kind == "write" and spec.requires_approval and not spec.mcp


@pytest.mark.parametrize(
    "args",
    [{"plan_id": "p-123"}, {"plan_id": "x-0aed9288"}, {"plan_id": "p-0aed9288", "note": "x" * 201}],
)
def test_schema_validation(args: dict) -> None:
    with pytest.raises(ActionArgsError):
        validate_args("save_production_proposal", args)


def test_writes_plan_from_thread_not_from_args(tmp_path: Path, plan: dict) -> None:
    # Act
    reply = save_proposal(
        {"plan_id": plan["plan_id"], "note": "revisar con campo"},
        user_id="wa-0123456789abcdef",
        last_plan=plan,
        state_dir=tmp_path,
    )

    # Assert
    lines = (tmp_path / "planning" / "proposals.jsonl").read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    assert plan["plan_id"] in reply and "el equipo de planta decide" in reply
    assert record["plan"]["margin"] == plan["margin"] and "plan_card" not in record["plan"]
    assert record["user_id"] == "wa-0123456789abcdef" and record["approved_by"] == "user"
    assert record["synthetic"] is True


def test_stale_plan_id_writes_nothing(tmp_path: Path, plan: dict) -> None:
    reply = save_proposal(
        {"plan_id": "p-00000000", "note": None}, user_id="u", last_plan=plan, state_dir=tmp_path
    )
    assert reply == STALE_PROPOSAL
    assert not (tmp_path / "planning").exists()


def test_execute_action_routes_to_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, plan: dict
) -> None:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path))
    reply = execute_action(
        "save_production_proposal",
        {"plan_id": plan["plan_id"]},
        store=None,
        user_id="u",
        turns=[],
        ttl_days=30,
        last_plan=plan,
    )
    assert "Guardé la propuesta" in reply
    assert (tmp_path / "planning" / "proposals.jsonl").is_file()
