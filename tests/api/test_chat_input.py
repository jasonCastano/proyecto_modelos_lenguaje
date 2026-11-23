"""Mensajes dictados en el chat: ``input`` viaja como metadato (spec 023, FR-012 y FR-022)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

import proyecto_modelos_lenguaje.api as api

VOICE = {"source": "voice", "audio_ms": 2040, "stt_ms": 451, "edited": True, "handsfree": False}


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


def _stream_done(client: TestClient, message: str, **extra: object) -> dict:
    body = {"message": message, "mode": "demo", "user_id": "anon-test", **extra}
    with client.stream("POST", "/api/chat/stream", json=body) as response:
        assert response.status_code == 200
        events = [
            json.loads(line[len("data: ") :])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]
    done = [event for event in events if event.get("event") == "done"]
    assert done, events
    return done[-1]["response"]


def _comparable(body: dict) -> dict:
    turn = body["turn"]
    return {
        "route": turn["route"]["route"],
        "answer": turn["answer"],
        "citations": [c.get("label") for c in turn["citations"]],
        "fallback": turn["fallback"],
        "status": body["status"],
    }


def test_chat_echoes_input_without_changing_the_answer(client: TestClient) -> None:
    question = "¿Qué produce Manuelita?"
    typed = _chat(client, question)
    spoken = _chat(client, question, input=VOICE)
    assert typed.status_code == 200 and spoken.status_code == 200
    assert typed.json()["turn"]["input"] is None
    assert spoken.json()["turn"]["input"] == VOICE
    assert _comparable(spoken.json()) == _comparable(typed.json())
    typed_contact = typed.json()["contact"] or {}
    spoken_contact = spoken.json()["contact"] or {}
    assert json.dumps(spoken_contact, sort_keys=True).count("voice") == 0
    assert set(spoken_contact) == set(typed_contact)


def test_stream_echoes_input_and_the_thread_keeps_it(client: TestClient) -> None:
    done = _stream_done(client, "hola", input={**VOICE, "handsfree": True, "edited": False})
    assert done["turn"]["input"]["handsfree"] is True
    thread_id = done["thread_id"]
    follow = _chat(client, "¿Qué produce Manuelita?", thread_id=thread_id)
    assert follow.status_code == 200 and follow.json()["turn"]["input"] is None
    turns = client.get(f"/api/threads/{thread_id}").json()["turns"]
    assert turns[0]["input"]["source"] == "voice" and turns[0]["input"]["audio_ms"] == 2040
    assert turns[1]["input"] is None


@pytest.mark.parametrize(
    "bad",
    [
        {**VOICE, "source": "text"},
        {**VOICE, "audio_ms": -1},
        {**VOICE, "stt_ms": 60_001},
        {**VOICE, "extra": "no"},
    ],
)
def test_invalid_input_is_rejected(client: TestClient, bad: dict) -> None:
    assert _chat(client, "hola", input=bad).status_code == 422
