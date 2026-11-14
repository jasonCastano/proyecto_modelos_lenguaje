"""Contrato HTTP de Valer-IA Caña (spec 018): bienvenida, cliente y privacidad del correo."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api
from proyecto_modelos_lenguaje.agent import welcome as welcome_module

EMAIL = "ana@ejemplo.com"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def test_welcome_contract_without_llm(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_model(*_args, **_kwargs):
        raise AssertionError("la bienvenida no debe llamar al modelo")

    monkeypatch.setattr(api, "build_chat_model", no_model)
    response = client.get("/api/welcome")
    assert response.status_code == 200
    body = response.json()
    assert body["assistant"] == "Valer-IA Caña"
    assert body["version"] == "1.0"
    assert "Valer-IA Caña" in body["text"]
    assert {c["label"] for c in body["citations"]} == {"U1", "U2"}


def test_welcome_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken():
        raise RuntimeError("sin plantilla")

    monkeypatch.setattr(api, "load_welcome", broken)
    response = client.get("/api/welcome")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "welcome_unavailable"
    assert welcome_module.load_welcome()["assistant"] == "Valer-IA Caña"


def _chat(client: TestClient, message: str, user: str, thread: str | None = None) -> dict:
    body = {"message": message, "mode": "demo", "user_id": user, "thread_id": thread}
    response = client.post("/api/chat", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_email_never_persisted_and_client_contract(client: TestClient, tmp_path: Path) -> None:
    # Arrange / Act: registro con aprobación y reconocimiento en otra visita
    paused = _chat(client, f"Soy Ana y mi correo es {EMAIL}", "anon-ana")
    assert paused["status"] == "pending_approval"
    assert paused["client"]["user_id"] == "anon-ana"
    resumed = client.post(
        f"/api/threads/{paused['thread_id']}/resume",
        json={"action_id": paused["pending_action"]["action_id"], "decision": "approve"},
    )
    assert resumed.status_code == 200, resumed.text
    asked = _chat(client, f"Hola, soy {EMAIL.upper()}", "anon-otra")
    assert asked["client"]["masked_email"] == "a***@ejemplo.com"
    recognized = _chat(client, "Ana", "anon-otra", asked["thread_id"])
    assert recognized["client"]["user_id"] == "anon-ana"
    assert recognized["client"]["recognized"] is True
    stream = client.post(
        "/api/chat/stream",
        json={
            "message": "Hola",
            "mode": "demo",
            "user_id": "anon-otra",
            "thread_id": asked["thread_id"],
        },
    )
    assert '"client"' in stream.text

    # Assert: el correo en claro no está en ninguna respuesta ni en el directorio de estado
    responses = " ".join(
        str(item) for item in (paused, resumed.json(), asked, recognized, stream.text)
    )
    for variant in (EMAIL, EMAIL.upper()):
        assert variant not in responses
        for path in (tmp_path / "state").rglob("*"):
            if path.is_file():
                raw = path.read_bytes()
                assert variant.encode() not in raw, path
                assert variant.encode("utf-16-le") not in raw, path
    thread = client.get(f"/api/threads/{asked['thread_id']}").json()
    assert EMAIL not in str(thread).lower()
