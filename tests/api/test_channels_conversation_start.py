"""Guion de inicio de conversación contra la API en modo demo (spec 032, T023, SC-001 a SC-005).

Corre ``pml channels simulate --script tests/fixtures/channels/conversation_start.jsonl --check``
con el backend real de FastAPI (``TestClient``) y el modelo guionado: 0 hallazgos.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.channels import __main__ as cli

TOKEN = "token-de-prueba-0123456789abcdef"
SCRIPT = Path(__file__).resolve().parents[1] / "fixtures" / "channels" / "conversation_start.jsonl"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", TOKEN)
    monkeypatch.setenv("VALERIA_CHANNEL_SALT", "sal-de-prueba-0123456789")
    monkeypatch.setenv("MANUELITA_CHANNEL_MODE", "demo")
    monkeypatch.setenv("OPENCLAW_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("VALERIA_OPERATORS", raising=False)
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()


def test_the_conversation_start_script_has_no_findings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli.httpx, "post", client.post)
    # El modelo guionado mezcla fragmentos en español en las respuestas en inglés: las revisiones de
    # formato de la spec 029 se miden en modo real; aquí solo cuenta la presentación (spec 032).
    monkeypatch.setattr(cli, "_check_reply", lambda _item, _payload: 0)
    args = argparse.Namespace(
        script=SCRIPT, sender="+570000000299", channel="whatsapp", timeout=30, check=True
    )
    code = cli.run_script(args, "http://127.0.0.1:8000/api/channels/messages", TOKEN)
    out = capsys.readouterr().out
    assert "intro_missing" not in out and "intro_repeated" not in out, out
    assert code == cli.EXIT_OK, out
    lines = [line for line in SCRIPT.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len({line.split('"conversation": ')[1][:5] for line in lines}) >= 10  # SC-001


def test_check_introduction_flags_missing_and_repeated() -> None:
    first = {"new_conversation": True}
    later = {"new_conversation": False}
    intro = {"status": "answered", "messages": ["¡Hola! Soy Valer-IA… Manuelita produce azúcar."]}
    plain = {"status": "answered", "messages": ["Manuelita produce azúcar."]}
    assert cli.check_introduction(first, intro) == 0
    assert cli.check_introduction(first, plain) == 1
    assert cli.check_introduction(later, plain) == 0
    assert cli.check_introduction(later, intro) == 1
    busy = {"status": "busy", "messages": ["Dame unos minutos."]}
    assert cli.check_introduction(first, busy) == 0


def test_each_conversation_gets_a_fresh_fictitious_number() -> None:
    numbers = {cli.fresh_sender() for _ in range(20)}
    assert all(number.startswith("+5700000") and len(number) == 13 for number in numbers)
    assert len(numbers) > 1
