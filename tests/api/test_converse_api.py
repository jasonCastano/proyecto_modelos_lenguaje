"""Contrato de la API en la conversación guiada (spec 020, ``contracts/api-changes.md``)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import ValidationError
from tests.agent_helpers import agent_config, demo_retriever, make_service

from proyecto_modelos_lenguaje import api
from proyecto_modelos_lenguaje.api_models import ChatResponse, ContactRecordModel, ContactTurnModel


class StreamingModel(BaseChatModel):
    """Modelo que transmite su respuesta palabra por palabra (como DeepSeek)."""

    reply: str = "¡Uf, qué calor! Ojalá tengas sombra cerca."

    @property
    def _llm_type(self) -> str:
        return "streaming-test"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, **_: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])

    def _stream(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **_: Any
    ):
        for word in self.reply.split(" "):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=word + " "))
            if run_manager is not None:
                run_manager.on_llm_new_token(word + " ", chunk=chunk)
            yield chunk


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def _events(body: str) -> list[dict[str, Any]]:
    events = []
    for block in body.strip().split("\n\n"):
        data = next(line[6:] for line in block.splitlines() if line.startswith("data: "))
        events.append(json.loads(data))
    return events


def test_chat_response_carries_the_act_and_the_turn_labels(client: TestClient) -> None:
    body = {"message": "¡qué calor hace hoy!", "mode": "demo", "user_id": "anon-api"}
    payload = client.post("/api/chat", json=body).json()
    ChatResponse.model_validate(payload)
    assert payload["turn"]["route"]["act"] == "smalltalk"
    acts = payload["contact"]["acts"]
    assert acts == [
        {"act": "smalltalk", "bridged": acts[0]["bridged"], "reviewed": "show", "discarded": 0}
    ]
    thread = client.get(f"/api/threads/{payload['thread_id']}").json()
    assert thread["contact"]["acts"] == acts


def test_converse_turn_streams_route_and_done_without_tokens() -> None:
    config = agent_config("guided")
    config = replace(config, conversation=replace(config.conversation, delivery="complete"))
    service = make_service(model=StreamingModel(), config=config)
    _thread, events = service.open_stream("¡qué calor hace hoy!", variant="chain")
    kinds = [event["event"] for event in events]
    assert kinds[0] == "start" and kinds[-1] == "done"
    assert "route" in kinds and "token" not in kinds


def test_retrieval_turns_keep_streaming_tokens_in_complete_delivery() -> None:
    """Spec 021: con ``delivery = "complete"`` las respuestas con búsqueda transmiten tokens."""
    config = agent_config("guided")
    config = replace(config, conversation=replace(config.conversation, delivery="complete"))
    service = make_service(config=config)
    _thread, events = service.open_stream("¿Qué produce Manuelita?", variant="chain")
    assert "token" in [event["event"] for event in events]


def test_review_notices_reach_the_response() -> None:
    config = agent_config("guided")
    config = replace(config, conversation=replace(config.conversation, max_regenerations=0))
    service = make_service(model=StreamingModel(reply="Mañana hará 32 grados."), config=config)
    outcome = service.send("¿cómo estará el clima mañana?")
    payload = ChatResponse.model_validate(outcome.to_dict())
    assert payload.notices == ["review_fallback"]
    assert payload.contact is not None and payload.contact.acts[-1].reviewed == "fallback"
    assert "32" not in payload.turn.answer


def test_contact_turns_are_controlled_labels_capped_at_fifty() -> None:
    with pytest.raises(ValidationError):
        ContactTurnModel.model_validate({"act": "smalltalk", "text": "hola"})
    with pytest.raises(ValidationError):
        ContactTurnModel.model_validate({"act": "poema"})
    record = {
        "opened_at": "x",
        "updated_at": "x",
        "turns": 51,
        "acts": [{"act": "minimal"}] * 51,
    }
    with pytest.raises(ValidationError):
        ContactRecordModel.model_validate(record)
    record["acts"] = [{"act": "minimal"}] * 50
    assert len(ContactRecordModel.model_validate(record).acts) == 50
