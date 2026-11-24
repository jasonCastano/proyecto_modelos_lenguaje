"""Contrato del canal: ``POST /api/channels/messages`` y ``GET /api/channels/status`` (spec 024).

Modo demo (sin red ni clave): mismo ``ChatService`` que la web, variante agente.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

import proyecto_modelos_lenguaje.api as api

TOKEN = "token-de-prueba-0123456789abcdef"
HEADERS = {"X-Channel-Token": TOKEN}
PHONE = "+573001234567"


@pytest.fixture()
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "state"
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(target))
    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", TOKEN)
    monkeypatch.setenv("VALERIA_CHANNEL_SALT", "sal-de-prueba-0123456789")
    monkeypatch.setenv("MANUELITA_CHANNEL_MODE", "demo")
    monkeypatch.setenv("OPENCLAW_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()
    yield target
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()


@pytest.fixture()
def client(state: Path) -> TestClient:
    return TestClient(api.app)


def _body(text: str = "¿Qué produce Manuelita?", message_id: str = "m1", **extra: object):
    return {"channel": "whatsapp", "message_id": message_id, "sender": PHONE, "text": text, **extra}


def test_requires_token(client: TestClient) -> None:
    response = client.post("/api/channels/messages", json=_body())
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "channel_forbidden"
    wrong = client.post("/api/channels/messages", json=_body(), headers={"X-Channel-Token": "x"})
    assert wrong.status_code == 403


def test_rejects_non_loopback(state: Path) -> None:
    remote = TestClient(api.app, client=("10.0.0.5", 50000))
    response = remote.post("/api/channels/messages", json=_body(), headers=HEADERS)
    assert response.status_code == 403


def test_disabled_without_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALERIA_CHANNEL_TOKEN")
    response = client.post("/api/channels/messages", json=_body(), headers=HEADERS)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "channel_disabled"


@pytest.mark.parametrize(
    "body",
    [
        _body(sender="3001234567x"),
        _body(text="x" * 4001),
        _body(text=""),
        {**_body(), "channel": "discord"},
        {**_body(), "extra": 1},
    ],
)
def test_invalid_body(client: TestClient, body: dict) -> None:
    response = client.post("/api/channels/messages", json=body, headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "channel_invalid"


def test_answers_and_keeps_the_thread(client: TestClient, state: Path) -> None:
    first = client.post("/api/channels/messages", json=_body(), headers=HEADERS)
    assert first.status_code == 200, first.text
    body = first.json()
    assert set(body) == {"status", "messages", "thread_id", "route", "tools", "latency_ms"}
    assert body["status"] == "answered" and body["messages"]
    second = client.post("/api/channels/messages", json=_body("¿y en Perú?", "m2"), headers=HEADERS)
    assert second.json()["thread_id"] == body["thread_id"]
    duplicate = client.post("/api/channels/messages", json=_body(), headers=HEADERS)
    assert duplicate.json()["status"] == "ignored"
    log = (state / "logs" / "channels.jsonl").read_text(encoding="utf-8")
    assert "Manuelita" not in log and "3001234567" not in log


def test_jid_sender_is_accepted(client: TestClient) -> None:
    body = _body(sender="573001234567@s.whatsapp.net", message_id="j1")
    response = client.post("/api/channels/messages", json=body, headers=HEADERS)
    assert response.status_code == 200


def test_media_is_unsupported(client: TestClient) -> None:
    body = {"channel": "whatsapp", "message_id": "i1", "sender": PHONE, "kind": "image"}
    response = client.post("/api/channels/messages", json=body, headers=HEADERS)
    assert response.json()["status"] == "unsupported"


def test_status(client: TestClient) -> None:
    client.post("/api/channels/messages", json=_body(), headers=HEADERS)
    response = client.get("/api/channels/status", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"enabled", "channels", "model", "qdrant", "pending_approvals"}
    assert body["channels"]["whatsapp"]["messages_1h"] >= 1
    assert body["model"]["provider"] == "deepseek" and "ok" in body["model"]
    assert client.get("/api/channels/status").status_code == 403


def test_tools_catalog(client: TestClient) -> None:
    from proyecto_modelos_lenguaje.agent.catalog import catalog

    tools = client.get("/api/tools").json()
    assert [tool["name"] for tool in tools] == [spec.name for spec in catalog()]
    first = tools[0]
    assert {"number", "name", "description", "kind", "requires_approval", "routes", "mcp"} <= set(
        first
    )
    assert first["schema"]["type"] == "object"
    assert all(tool["requires_approval"] == (tool["kind"] == "write") for tool in tools)
