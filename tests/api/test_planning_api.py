"""API v1 de planificación (spec 026, T024; contracts/planning-api.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from proyecto_modelos_lenguaje import api, api_planning
from proyecto_modelos_lenguaje.agent.planning import (
    DECISION_PHRASE,
    SYNTHETIC_LABEL,
    PlanningError,
    Scenario,
    optimize,
)

OPEN_ROUTES = [
    ("get", "/api/v1/planning/state", None),
    ("post", "/api/v1/planning/plan", {}),
    ("post", "/api/v1/planning/compare", {}),
    ("post", "/api/v1/planning/proposals", {"scenario": {}}),
]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    for var in ("VALERIA_PLANNERS", "MANUELITA_PLANNER_OPEN", "MANUELITA_PLANNER_WEB"):
        monkeypatch.delenv(var, raising=False)
    api_planning.PENDING.clear()
    return TestClient(api.app)


@pytest.fixture()
def planner(client: TestClient) -> TestClient:
    """Spec 027: en la web no hace falta ninguna autorización."""
    return client


@pytest.mark.parametrize(("method", "path", "body"), OPEN_ROUTES)
def test_any_visitor_reaches_planning_without_authorization(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    """Spec 027 (FR-002, SC-002): sin envs ni X-User-Id, nunca 403."""
    response = getattr(client, method)(path, **({"json": body} if body is not None else {}))
    assert response.status_code in (200, 202)
    assert "planner_forbidden" not in response.text


def test_access_is_always_open(client: TestClient) -> None:
    body = client.get("/api/v1/planning/access").json()
    assert body["authorized"] is True and "sintéticos" in body["reason"]


def test_old_web_flag_is_ignored(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec 027 (FR-005): la variable vieja no cambia nada ni da error."""
    monkeypatch.setenv("MANUELITA_PLANNER_WEB", "0")
    assert client.get("/api/v1/planning/state").status_code == 200


def test_invalid_user_header_is_logged_as_anon(client: TestClient, tmp_path: Path) -> None:
    client.get("/api/v1/planning/state", headers={"X-User-Id": "no valido / x"})
    log = tmp_path / "state" / "planning" / "console.jsonl"
    event = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert event["endpoint"] == "state" and event["user"] == "anon"


def test_state_is_a_synthetic_snapshot(planner: TestClient) -> None:
    body = planner.get("/api/v1/planning/state").json()
    assert body["synthetic"] is True and body["label"] == SYNTHETIC_LABEL
    assert body["ranges"]["cane_delta_pct"] == {"min": -50, "max": 50}
    assert len(body["capacities"]) == 4


@pytest.mark.parametrize(
    "scenario",
    [{"cane_delta_pct": -80}, {"price_ethanol_pct": 60}, {"cane_quality": 3}, {"color": "rojo"}],
)
def test_invalid_scenario_is_422(planner: TestClient, scenario: dict) -> None:
    response = planner.post("/api/v1/planning/plan", json=scenario)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_scenario"
    assert error["message"]


def test_plan_matches_the_optimizer(planner: TestClient) -> None:
    body = planner.post("/api/v1/planning/plan", json={"cane_delta_pct": -15}).json()
    expected = optimize(Scenario(cane_delta_pct=-15)).to_dict(card=True)
    for key, value in expected.items():
        assert body[key] == value, key
    assert body["label"] == SYNTHETIC_LABEL
    assert body["decision_phrase"] == DECISION_PHRASE


def test_infeasible_scenario_reports_shortfalls(planner: TestClient) -> None:
    body = planner.post(
        "/api/v1/planning/plan", json={"cane_delta_pct": -50, "steam_limit": 0}
    ).json()
    assert body["status"] == "infeasible_relaxed"
    assert body["shortfalls"]


def test_compare_returns_base_and_scenario(planner: TestClient) -> None:
    body = planner.post("/api/v1/planning/compare", json={"cane_delta_pct": -15}).json()
    assert body["base"]["scenario"] == {"plant_id": "cana", "prioritize": "margin"}
    assert body["scenario"]["scenario"]["cane_delta_pct"] == -15
    assert body["synthetic"] is True
    assert body["margin_delta"] < 0


def test_missing_plant_data_is_503(planner: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*_args: object, **_kwargs: object):
        raise PlanningError("No hay datos de planificación en x.")

    monkeypatch.setattr(api_planning, "load_plant", missing)
    response = planner.get("/api/v1/planning/state")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "plant_data_missing"
    assert "generate_planning_data.py" in error["message"]


def test_console_events_are_logged_without_personal_data(
    planner: TestClient, tmp_path: Path
) -> None:
    planner.post("/api/v1/planning/plan", json={"cane_delta_pct": -15})
    log = tmp_path / "state" / "planning" / "console.jsonl"
    event = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert set(event) == {
        "ts",
        "endpoint",
        "user",
        "scenario",
        "plan_id",
        "status",
        "duration_ms",
        "synthetic",
    }
    assert event["endpoint"] == "plan" and event["user"] == "anon"
    assert "testclient" not in log.read_text(encoding="utf-8")
