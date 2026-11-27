"""Ningún texto dirigido a las personas sugiere comandos (spec 028, T027, FR-009, SC-004).

Recorre los textos del canal y ejecuta el guion ``natural_conversation.jsonl`` en modo demo (mismo
``ChatService`` de la web, sin red ni clave) a través de ``POST /api/channels/messages``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.channels.bridge import ACTIONS, GENERIC_ACTION, TEXTS
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.agent_helpers import demo_retriever

COMMAND = re.compile(r"(?<![\w/:.])/[a-záéíóúñ]+", re.IGNORECASE)
SCRIPT = PROJECT_ROOT / "tests" / "fixtures" / "channels" / "natural_conversation.jsonl"
TOKEN = "token-de-prueba-0123456789abcdef"


def _all_channel_texts() -> list[str]:
    texts = [text for language in TEXTS.values() for text in language.values()]
    texts += [text for phrases in ACTIONS.values() for text in phrases.values()]
    return texts + list(GENERIC_ACTION.values())


@pytest.mark.parametrize("text", _all_channel_texts())
def test_channel_texts_never_mention_commands(text: str) -> None:
    assert not COMMAND.search(text), text
    assert "SÍ" not in text and "*NO*" not in text  # tampoco «Responde SÍ o NO»


def test_both_languages_have_the_same_texts() -> None:
    assert set(TEXTS["es"]) == set(TEXTS["en"])
    for phrases in ACTIONS.values():
        assert set(phrases) == {"es", "en"}


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", TOKEN)
    monkeypatch.setenv("VALERIA_CHANNEL_SALT", "sal-de-prueba-0123456789")
    monkeypatch.setenv("MANUELITA_CHANNEL_MODE", "demo")
    monkeypatch.setenv("OPENCLAW_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()


def test_natural_conversation_script_never_mentions_commands(client: TestClient) -> None:
    items = [json.loads(line) for line in SCRIPT.read_text(encoding="utf-8").splitlines() if line]
    assert len(items) >= 15
    channel_level = {
        "restart": ("restart",),
        "format_text": ("format_text",),
        "format_voice": ("format_voice",),
    }
    for index, item in enumerate(items):
        body = {
            "channel": "whatsapp",
            "message_id": f"guion-{index}",
            "sender": "+573001234567",
            "text": item["text"],
        }
        response = client.post(
            "/api/channels/messages", json=body, headers={"X-Channel-Token": TOKEN}
        )
        assert response.status_code == 200, response.text
        reply = response.json()
        text = "\n".join(reply["messages"])
        assert reply["status"] != "error", item
        assert not COMMAND.search(text), (item["id"], text)
        if item["expect"] in channel_level:
            keys = channel_level[item["expect"]]
            expected = {TEXTS[item["lang"]][key] for key in keys}
            assert reply["messages"][0] in expected, (item["id"], reply["messages"])
