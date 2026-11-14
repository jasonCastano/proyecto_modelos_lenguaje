"""Streaming de la conversación por Server-Sent Events (rúbrica del Módulo 2, ítem 3.1)."""

from __future__ import annotations

import json
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


def _events(body: str) -> list[dict[str, object]]:
    events = []
    for block in body.strip().split("\n\n"):
        data = next(line[6:] for line in block.splitlines() if line.startswith("data: "))
        events.append(json.loads(data))
    return events


def _stream(client: TestClient, message: str, **extra: object):
    body = {"message": message, "mode": "demo", "user_id": "anon-stream", **extra}
    return client.post("/api/chat/stream", json=body)


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_stream_emits_route_retrieval_tokens_and_the_final_turn(
    client: TestClient, variant: str
) -> None:
    # Act
    response = _stream(client, "¿Qué produce Manuelita?", variant=variant)
    events = _events(response.text)
    kinds = [event["event"] for event in events]
    streamed = "".join(str(e["text"]) for e in events if e["event"] == "token")
    final = events[-1]["response"]

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert kinds[0] == "start" and kinds[-1] == "done"
    found = "tool" if variant == "agent" else "retrieval"
    assert kinds.index("route") < kinds.index(found) < kinds.index("token")
    assert kinds.count("token") > 1
    assert final["status"] == "answered" and final["turn"]["citations"]
    assert streamed.strip() == final["turn"]["answer"].strip()


def test_stream_keeps_the_thread_and_pauses_for_approval(client: TestClient) -> None:
    # Arrange
    first = _events(_stream(client, "¿Qué produce Manuelita?").text)
    thread_id = first[0]["thread_id"]

    # Act
    events = _events(_stream(client, "Me llamo Ana", thread_id=thread_id).text)

    # Assert
    assert events[-1]["response"]["thread_id"] == thread_id
    assert events[-1]["response"]["status"] == "pending_approval"
    assert events[-1]["response"]["pending_action"]["tool"] == "save_profile"
    assert not [event for event in events if event["event"] == "token"]


def test_stream_validation_errors_are_plain_http_errors(client: TestClient) -> None:
    # Act
    empty = _stream(client, "   ")
    unknown = _stream(client, "Hola", thread_id="00000000-0000-4000-8000-000000000000")

    # Assert
    assert empty.status_code == 400 and empty.json()["error"]["code"] == "empty_question"
    assert unknown.status_code == 404


def test_each_turn_is_logged_as_structured_json(client: TestClient, tmp_path: Path) -> None:
    # Act
    _stream(client, "Hola, buenas tardes")
    status = client.get("/api/observability").json()
    log = tmp_path / "state" / "logs" / "turns.jsonl"
    record = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])

    # Assert
    assert status["structured_log"].endswith("turns.jsonl")
    assert record["route"] == "direct" and record["tool_calls"] == 0
    assert "question" not in record and "user_id" not in record


def test_observability_reports_which_vector_search_is_in_use(client: TestClient) -> None:
    # Act
    status = client.get("/api/observability", params={"mode": "demo"}).json()

    # Assert: la UI muestra si busca en Qdrant o si cayó al respaldo numpy.
    assert "demo" in status["vector_store"]
    assert status["vector_store"]["demo"].startswith(("Búsqueda vectorial", "Respaldo numpy"))


def test_adversarial_demo_corpus_shows_the_injection_as_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange: el caso 5 de la rúbrica, en vivo desde la interfaz
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("MANUELITA_DEMO_CORPUS", "malicious")

    def no_gold():  # en CI el oro no se descarga (LFS): el corpus adversarial no lo necesita
        raise RuntimeError("sin oro")

    monkeypatch.setattr(api, "_entity_index", no_gold)
    monkeypatch.setattr(api, "_units", no_gold)
    api._retriever.cache_clear()
    api._chat_service.cache_clear()
    client = TestClient(api.app)

    # Act
    payload = client.post(
        "/api/chat",
        json={"message": "¿Qué produce Manuelita?", "mode": "demo", "user_id": "anon-mal"},
    ).json()

    # Assert
    assert "anomalies" in payload, payload
    reasons = {reason for anomaly in payload["anomalies"] for reason in anomaly["reasons"]}
    assert "ignora_instrucciones" in reasons
    assert "HACKEADO" not in payload["turn"]["answer"]
    api._retriever.cache_clear()
    api._chat_service.cache_clear()
