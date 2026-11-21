"""SSE con entrega por frases (spec 021, ``contracts/streaming.md`` §1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api
from proyecto_modelos_lenguaje.api_models import ChatResponse


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


@pytest.mark.parametrize("message", ["¡qué calor hace hoy!", "¿Qué produce Manuelita?"])
@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_stream_sends_reviewed_sentences_and_no_tokens(
    client: TestClient, message: str, variant: str
) -> None:
    body = {"message": message, "mode": "demo", "user_id": "anon-frases", "variant": variant}
    response = client.post("/api/chat/stream", json=body)
    events = _events(response.text)
    kinds = [event["event"] for event in events]
    assert kinds[0] == "start" and kinds[-1] == "done"
    assert "route" in kinds and "sentence" in kinds and "token" not in kinds
    assert kinds.index("route") < kinds.index("sentence")
    shown = "".join(str(e["text"]) for e in events if e["event"] == "sentence")
    final = ChatResponse.model_validate(events[-1]["response"])
    assert " ".join(shown.split()) == " ".join(final.turn.answer.split())
    assert final.contact is not None and final.contact.acts[-1].discarded == 0
