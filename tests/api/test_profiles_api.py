"""API de perfiles (spec 025, T036, contracts/profiles.md)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    for var in ("VALERIA_PLANNERS", "MANUELITA_PLANNER_OPEN", "MANUELITA_PLANNER_WEB"):
        monkeypatch.delenv(var, raising=False)
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def _chat(client: TestClient, message: str, **extra: object):
    body = {"message": message, "mode": "demo", "user_id": "anon-test", "variant": "agent", **extra}
    return client.post("/api/chat", json=body)


def test_list_profiles(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = client.get("/api/profiles").json()
    assert [row["key"] for row in rows] == [
        "visitante",
        "cliente",
        "proveedor",
        "colaborador",
        "planificador",
    ]
    assert set(rows[0]) == {"key", "label", "requires_authorization", "authorized"}
    assert rows[-1]["requires_authorization"] and not rows[-1]["authorized"]
    monkeypatch.setenv("MANUELITA_PLANNER_WEB", "1")
    assert client.get("/api/profiles").json()[-1]["authorized"] is True


def test_chat_with_profile_returns_it_in_the_turn(client: TestClient) -> None:
    response = _chat(client, "¿Qué certificaciones tiene Manuelita?", profile="cliente")
    assert response.status_code == 200
    assert response.json()["turn"]["profile"] == "cliente"


def test_invalid_profile_is_400(client: TestClient) -> None:
    response = _chat(client, "hola", profile="gerente")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_profile"


def test_unauthorized_planner_is_403(client: TestClient) -> None:
    response = _chat(client, "Planifica la producción", profile="planificador")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "planner_not_authorized"


def test_default_profile_is_visitante(client: TestClient) -> None:
    assert _chat(client, "¿Qué produce Manuelita?").json()["turn"]["profile"] == "visitante"
