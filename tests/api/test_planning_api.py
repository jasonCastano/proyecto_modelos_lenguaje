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

PROTECTED = [
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
def planner(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_PLANNER_WEB", "1")
    return client


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_unauthorized_gets_403_without_plant_data(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = getattr(client, method)(path, **({"json": body} if body is not None else {}))
    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "planner_forbidden"
    text = json.dumps(payload)
    assert "cane" not in text and "commitments" not in text


def test_access_answers_everyone(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    denied = client.get("/api/v1/planning/access").json()
    assert denied["authorized"] is False and "equipo de planta" in denied["reason"]
    monkeypatch.setenv("MANUELITA_PLANNER_WEB", "1")
    assert client.get("/api/v1/planning/access").json()["authorized"] is True


def test_named_planner_is_authorized_by_user_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VALERIA_PLANNERS", "planta-01")
    assert client.get("/api/v1/planning/state").status_code == 403
    response = client.get("/api/v1/planning/state", headers={"X-User-Id": "planta-01"})
    assert response.status_code == 200


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
