"""Contrato de la API de conversación (T039, ``contracts/chat-api.md``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def _chat(client: TestClient, message: str, **extra: object):
    body = {"message": message, "mode": "demo", "user_id": "anon-test", **extra}
    return client.post("/api/chat", json=body)


def test_chat_creates_a_thread_and_returns_the_turn(client: TestClient) -> None:
    # Act
    response = _chat(client, "¿Qué produce Manuelita?", thread_id=None)

    # Assert
    assert response.status_code == 200
    payload = response.json()
    uuid.UUID(payload["thread_id"], version=4)
    turn = payload["turn"]
    assert payload["status"] == "answered"
    assert turn["turn_id"] == 1
    assert turn["route"]["route"] == "documental"
    assert turn["fragments"] and turn["citations"]
    assert set(turn["metrics"]) == {
        "latency_ms",
        "model_calls",
        "tool_calls",
        "input_tokens",
        "output_tokens",
    }
    assert payload["pending_action"] is None
    assert payload["anomalies"] == []


def test_thread_view_returns_the_turns(client: TestClient) -> None:
    # Arrange
    thread_id = _chat(client, "¿Qué produce Manuelita?").json()["thread_id"]
    _chat(client, "¿Y dónde lo produce?", thread_id=thread_id)

    # Act
    response = client.get(f"/api/threads/{thread_id}")

    # Assert
    assert response.status_code == 200
    view = response.json()
    assert view["variant"] == "chain"
    assert view["status"] == "idle"
    assert [turn["turn_id"] for turn in view["turns"]] == [1, 2]


def test_unknown_thread_is_404(client: TestClient) -> None:
    # Arrange
    unknown = str(uuid.uuid4())

    # Act
    chat = _chat(client, "Hola", thread_id=unknown)
    view = client.get(f"/api/threads/{unknown}")

    # Assert
    for response in (chat, view):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "thread_not_found"


def test_variant_mismatch_is_409(client: TestClient) -> None:
    # Arrange
    thread_id = _chat(client, "Hola", variant="agent").json()["thread_id"]

    # Act
    response = _chat(client, "¿Qué produce Manuelita?", thread_id=thread_id, variant="chain")

    # Assert
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "variant_mismatch"


@pytest.mark.parametrize(
    ("message", "code"), [("   ", "empty_question"), ("a" * 501, "question_too_long")]
)
def test_invalid_messages_are_400(client: TestClient, message: str, code: str) -> None:
    # Act
    response = _chat(client, message)

    # Assert
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code


def test_clarify_turn_has_no_citations(client: TestClient) -> None:
    # Act
    payload = _chat(client, "¿Y lo anterior?").json()

    # Assert
    assert payload["status"] == "clarify"
    assert payload["turn"]["citations"] == []


def test_resume_approves_a_pending_action(client: TestClient) -> None:
    # Arrange
    paused = _chat(client, "Prefiero respuestas en viñetas").json()
    thread_id = paused["thread_id"]

    # Act
    busy = _chat(client, "¿Qué produce Manuelita?", thread_id=thread_id)
    view = client.get(f"/api/threads/{thread_id}").json()
    resumed = client.post(
        f"/api/threads/{thread_id}/resume",
        json={"action_id": paused["pending_action"]["action_id"], "decision": "approve"},
    )

    # Assert
    assert paused["status"] == "pending_approval"
    assert paused["pending_action"]["tool"] == "save_preference"
    assert busy.status_code == 409
    assert busy.json()["error"]["code"] == "thread_pending_approval"
    assert view["status"] == "pending_approval"
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "answered"
    assert client.get(f"/api/threads/{thread_id}").json()["actions"][0]["decision"] == "approve"


def test_resume_errors(client: TestClient) -> None:
    # Arrange
    thread_id = _chat(client, "Hola").json()["thread_id"]
    paused = _chat(client, "Exporta la conversación", thread_id=thread_id).json()

    # Act
    unknown = client.post(
        f"/api/threads/{uuid.uuid4()}/resume", json={"action_id": "a", "decision": "approve"}
    )
    mismatch = client.post(
        f"/api/threads/{thread_id}/resume", json={"action_id": "otra", "decision": "approve"}
    )
    invalid = client.post(
        f"/api/threads/{thread_id}/resume",
        json={
            "action_id": paused["pending_action"]["action_id"],
            "decision": "edit",
            "args": {"format": "pdf"},
        },
    )

    # Assert
    assert unknown.status_code == 404
    assert (mismatch.status_code, mismatch.json()["error"]["code"]) == (409, "action_mismatch")
    assert (invalid.status_code, invalid.json()["error"]["code"]) == (400, "invalid_args")
