"""Paridad de cifras: consola, herramienta del agente y CLI (spec 026, SC-003, T026)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from proyecto_modelos_lenguaje import api
from proyecto_modelos_lenguaje.agent.catalog import ToolContext
from proyecto_modelos_lenguaje.agent.tools_planning import OptimizePlanArgs, optimize_impl

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    json.loads(line)
    for line in (ROOT / "tests" / "fixtures" / "agent" / "planning_scenarios.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]
FIELDS = ("plan_id", "status", "mix", "products", "margin", "binding", "shortfalls", "alternatives")


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    mp = pytest.MonkeyPatch()
    mp.setenv("MANUELITA_STATE_DIR", str(tmp_path_factory.mktemp("state")))
    for var in ("MANUELITA_PLANNER_WEB", "MANUELITA_PLANNER_OPEN", "VALERIA_PLANNERS"):
        mp.delenv(var, raising=False)  # spec 027 (SC-005): paridad sin ninguna autorización
    yield TestClient(api.app)
    mp.undo()


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_console_tool_and_cli_give_the_same_plan(client: TestClient, case: dict) -> None:
    scenario = case["scenario"]
    console = client.post("/api/v1/planning/plan", json=scenario).json()

    ctx = ToolContext()
    optimize_impl(ctx, OptimizePlanArgs(**scenario))
    tool = json.loads(json.dumps(ctx.trace.plans[-1]))

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "proyecto_modelos_lenguaje.agent",
            "planning",
            "--scenario",
            json.dumps(scenario),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        env=env,
        check=True,
    )
    cli = json.loads(completed.stdout)

    for field in FIELDS:
        assert console[field] == tool[field] == cli[field], (case["id"], field)
