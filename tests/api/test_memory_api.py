"""Contrato de la API de memoria larga (T061, ``contracts/chat-api.md``)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api

USER = "anon-test"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def _chat(client: TestClient, message: str, **extra: object) -> dict:
    body = {"message": message, "mode": "demo", "user_id": USER, **extra}
    return client.post("/api/chat", json=body).json()


def _approve(client: TestClient, thread_id: str, action_id: str) -> None:
    client.post(
        f"/api/threads/{thread_id}/resume", json={"action_id": action_id, "decision": "approve"}
    )


def test_memory_lists_items_and_forgets_only_after_approval(client: TestClient) -> None:
    # Arrange
    paused = _chat(client, "Prefiero respuestas en viñetas")
    thread_id = paused["thread_id"]
    _approve(client, thread_id, paused["pending_action"]["action_id"])

    # Act
    listed = client.get(f"/api/memory/{USER}").json()
    deletion = client.delete(f"/api/memory/{USER}?thread_id={thread_id}")
    still_there = client.get(f"/api/memory/{USER}").json()
    _approve(client, thread_id, deletion.json()["pending_action"]["action_id"])
    after = client.get(f"/api/memory/{USER}").json()

    # Assert
    item = listed["items"][0]
    assert (item["key"], item["value"]) == ("response_format", "viñetas")
    assert item["created_at"] < item["expires_at"]
    assert deletion.status_code == 202
    assert deletion.json()["status"] == "pending_approval"
    assert deletion.json()["pending_action"]["tool"] == "forget_memory"
    assert len(still_there["items"]) == 1
    assert after["items"] == []


def test_memory_delete_requires_the_owners_thread(client: TestClient) -> None:
    # Arrange
    thread_id = _chat(client, "Hola")["thread_id"]

    # Act
    other = client.delete(f"/api/memory/otro-usuario?thread_id={thread_id}")
    missing_thread = client.delete(f"/api/memory/{USER}")
    invalid_user = client.get("/api/memory/usuario con espacios")

    # Assert
    assert other.status_code == 404
    assert missing_thread.status_code == 422
    assert invalid_user.status_code == 400
