"""Contrato HTTP del registro del contacto y de los campos de atención (spec 019, T038)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api
from proyecto_modelos_lenguaje.api_models import ChatResponse, ContactRecordModel, ThreadView


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def _chat(client: TestClient, message: str, thread: str | None = None) -> dict:
    body = {"message": message, "mode": "demo", "user_id": "anon-care", "thread_id": thread}
    response = client.post("/api/chat", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_chat_returns_the_contact_record_and_care_route_fields(client: TestClient) -> None:
    first = _chat(client, "¿Qué produce Manuelita?")
    second = _chat(client, "Dame una receta de postre", first["thread_id"])

    ChatResponse.model_validate(second)
    record = ContactRecordModel.model_validate(second["contact"])
    assert record.turns == 2
    assert [r.category for r in record.requests] == ["manuelita", "off_topic"]
    route = second["turn"]["route"]
    assert route["scope_reason"] == "off_topic" and route["topic"] == "cocina"
    assert route["kind"] is None and route["sentiment"] is None


def test_stream_done_event_carries_the_contact(client: TestClient) -> None:
    body = {"message": "Quiero hablar con una persona", "mode": "demo", "user_id": "anon-s"}
    response = client.post("/api/chat/stream", json=body)
    blocks = [b for b in response.text.strip().split("\n\n") if b]
    final = json.loads(
        next(line[6:] for line in blocks[-1].splitlines() if line.startswith("data: "))
    )
    done = final["response"]
    ChatResponse.model_validate(done)
    assert done["turn"]["route"]["kind"] == "human"
    assert done["contact"]["requests"][0]["category"] == "unattainable"


def test_thread_view_includes_the_contact(client: TestClient) -> None:
    first = _chat(client, "¿Va a llover mañana?")
    view = client.get(f"/api/threads/{first['thread_id']}").json()
    ThreadView.model_validate(view)
    assert view["contact"]["requests"][0]["topic"] == "clima"


def test_older_payloads_without_care_fields_still_validate() -> None:
    payload = {
        "thread_id": "8f6c1e0a-0000-4000-8000-000000000001",
        "turn": {
            "turn_id": 1,
            "question": "Hola",
            "route": {
                "route": "direct",
                "confidence": 1.0,
                "reason": "saludo",
                "decided_by": "rules",
            },
            "answer": "¡Hola!",
        },
        "status": "answered",
    }
    response = ChatResponse.model_validate(payload)
    assert response.contact is None and response.turn.route.topic is None
