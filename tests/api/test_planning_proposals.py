"""Propuesta en dos pasos desde la consola (spec 026, T025; R9)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from proyecto_modelos_lenguaje import api, api_planning

PHONE_NOTE = "Llamar a Ana al 3001234567 para revisar"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("MANUELITA_PLANNER_WEB", "1")
    api_planning.PENDING.clear()
    api_planning.PENDING.clock = lambda: datetime.now(UTC)
    yield TestClient(api.app)
    api_planning.PENDING.clock = lambda: datetime.now(UTC)


def _proposals(tmp_path: Path) -> list[dict]:
    path = tmp_path / "state" / "planning" / "proposals.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _create(client: TestClient, note: str | None = None) -> dict:
    body: dict = {"scenario": {"cane_delta_pct": -15}}
    if note is not None:
        body["note"] = note
    response = client.post("/api/v1/planning/proposals", json=body)
    assert response.status_code == 202
    return response.json()


def test_create_does_not_write(client: TestClient, tmp_path: Path) -> None:
    pending = _create(client)
    assert pending["plan_id"].startswith("p-")
    assert pending["question"].startswith("¿Guardar")
    assert pending["confirmation_id"] and pending["summary"]
    assert _proposals(tmp_path) == []


def test_yes_saves_with_redacted_note(client: TestClient, tmp_path: Path) -> None:
    pending = _create(client, PHONE_NOTE)
    response = client.post(
        f"/api/v1/planning/proposals/{pending['confirmation_id']}", json={"decision": "yes"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved" and body["message"].startswith("Propuesta guardada")
    rows = _proposals(tmp_path)
    assert len(rows) == 1
    assert rows[0]["plan_id"] == pending["plan_id"] and rows[0]["synthetic"] is True
    assert "3001234567" not in json.dumps(rows[0])


def test_no_discards_without_writing(client: TestClient, tmp_path: Path) -> None:
    pending = _create(client)
    response = client.post(
        f"/api/v1/planning/proposals/{pending['confirmation_id']}", json={"decision": "no"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "discarded"
    assert _proposals(tmp_path) == []


def test_repeated_confirmation_is_404(client: TestClient) -> None:
    pending = _create(client)
    url = f"/api/v1/planning/proposals/{pending['confirmation_id']}"
    assert client.post(url, json={"decision": "no"}).status_code == 200
    again = client.post(url, json={"decision": "yes"})
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "proposal_not_found"


def test_expired_proposal_is_410(client: TestClient, tmp_path: Path) -> None:
    pending = _create(client)
    later = datetime.now(UTC) + timedelta(minutes=6)
    api_planning.PENDING.clock = lambda: later
    response = client.post(
        f"/api/v1/planning/proposals/{pending['confirmation_id']}", json={"decision": "yes"}
    )
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "proposal_expired"
    assert _proposals(tmp_path) == []


def test_store_keeps_at_most_100(client: TestClient) -> None:
    first = _create(client)
    for _ in range(api_planning.MAX_PENDING):
        _create(client)
    assert len(api_planning.PENDING) == api_planning.MAX_PENDING
    response = client.post(
        f"/api/v1/planning/proposals/{first['confirmation_id']}", json={"decision": "yes"}
    )
    assert response.status_code == 404


def test_note_over_280_is_422(client: TestClient) -> None:
    response = client.post("/api/v1/planning/proposals", json={"scenario": {}, "note": "x" * 281})
    assert response.status_code == 422


def test_console_log_has_no_raw_note(client: TestClient, tmp_path: Path) -> None:
    pending = _create(client, PHONE_NOTE)
    client.post(f"/api/v1/planning/proposals/{pending['confirmation_id']}", json={"decision": "no"})
    log = (tmp_path / "state" / "planning" / "console.jsonl").read_text(encoding="utf-8")
    assert "3001234567" not in log and "Ana" not in log
    statuses = [json.loads(line)["status"] for line in log.splitlines()]
    assert "pending" in statuses and "discarded" in statuses
