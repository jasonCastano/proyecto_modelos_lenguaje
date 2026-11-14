"""Contrato de la voz del agente: ``POST /api/tts`` y ``GET /api/voice`` (spec 016)."""

from __future__ import annotations

import builtins
import io
import json
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.agent.guard import OMITTED_MARKER
from proyecto_modelos_lenguaje.voice.config import VoiceConfig
from proyecto_modelos_lenguaje.voice.engine import (
    FakeSynthesizer,
    VoiceService,
    reset_voice_service,
)

client = TestClient(api.app)


@pytest.fixture()
def state_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    target = tmp_path / "state"
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(target))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return target


@pytest.fixture()
def fake() -> FakeSynthesizer:
    synth = FakeSynthesizer()
    reset_voice_service(VoiceService(VoiceConfig(engine="fake", warmup=False), synthesizer=synth))
    return synth


def _log_lines(state_dir: Path) -> list[dict]:
    path = state_dir / "logs" / "voice.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# -- US1: síntesis -----------------------------------------------------------------------------


def test_tts_returns_wav_with_headers(state_dir: Path, fake: FakeSynthesizer) -> None:
    # Act
    response = client.post(
        "/api/tts",
        json={"text": "Manuelita produce azúcar [U2].", "thread_id": "t-1", "segment": 0},
    )
    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-voice"] == "Rebeca"
    assert float(response.headers["x-synth-ms"]) >= 0
    assert float(response.headers["x-audio-ms"]) > 0
    with wave.open(io.BytesIO(response.content)) as handle:
        assert (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) == (
            1,
            2,
            24_000,
        )
        assert handle.getnframes() > 0


def test_text_is_cleaned_before_synthesis(state_dir: Path, fake: FakeSynthesizer) -> None:
    # Act
    client.post(
        "/api/tts",
        json={"text": f"**Etanol** [U1, U3] {OMITTED_MARKER} en https://manuelita.com hoy."},
    )
    # Assert
    spoken, voice = fake.calls[-1]
    assert spoken == "Etanol en hoy."
    assert voice == "Rebeca"


def test_only_citation_returns_204(state_dir: Path, fake: FakeSynthesizer) -> None:
    response = client.post("/api/tts", json={"text": "[U2]"})
    assert response.status_code == 204
    assert response.content == b""
    assert fake.calls == []


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"text": "a" * 601}, "text_too_long"),
        ({"text": "Hola.", "voice": "Inexistente"}, "unknown_voice"),
        ({"text": "Hola.", "extra": 1}, "invalid_request"),
        ({"text": ""}, "invalid_request"),
        ({"text": "Hola.", "segment": -1}, "invalid_request"),
    ],
)
def test_invalid_requests_return_422(state_dir: Path, fake: FakeSynthesizer, body, code) -> None:
    response = client.post("/api/tts", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_other_voice_from_catalog(state_dir: Path, fake: FakeSynthesizer) -> None:
    response = client.post("/api/tts", json={"text": "Hola.", "voice": "Regina"})
    assert response.status_code == 200
    assert response.headers["x-voice"] == "Regina"


def test_tts_logs_without_text(state_dir: Path, fake: FakeSynthesizer) -> None:
    # Act
    client.post(
        "/api/tts", json={"text": "Secreto comercial de prueba.", "thread_id": "t-9", "segment": 2}
    )
    client.post("/api/tts", json={"text": "[U1]", "thread_id": "t-9", "segment": 3})
    # Assert
    records = _log_lines(state_dir)
    assert [record["status"] for record in records] == ["ok", "empty"]
    first = records[0]
    assert (first["thread_id"], first["segment"], first["voice"]) == ("t-9", 2, "Rebeca")
    assert first["chars"] == len("Secreto comercial de prueba.")
    assert first["synth_ms"] >= 0 and first["audio_ms"] > 0
    raw = (state_dir / "logs" / "voice.jsonl").read_text(encoding="utf-8")
    assert "Secreto" not in raw


def test_tts_works_without_llm_key(state_dir: Path, fake: FakeSynthesizer) -> None:
    assert client.post("/api/tts", json={"text": "Funciona sin clave."}).status_code == 200


def test_synthesis_failure_returns_500_and_keeps_ready(state_dir: Path) -> None:
    class Broken(FakeSynthesizer):
        def synth(self, text: str, voice: str):
            raise RuntimeError("falla nativa")

    reset_voice_service(VoiceService(VoiceConfig(engine="fake"), synthesizer=Broken()))
    response = client.post("/api/tts", json={"text": "Hola."})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "voice_error"
    assert response.json()["error"]["retryable"] is True
    assert client.get("/api/voice").json()["state"] == "ready"


# -- US3: estado y degradación -----------------------------------------------------------------


def test_voice_status_ready(fake: FakeSynthesizer) -> None:
    client.post("/api/tts", json={"text": "Hola."})
    body = client.get("/api/voice").json()
    assert body["available"] is True
    assert body["state"] == "ready"
    assert body["engine"] == "fake"
    assert body["voice"] == "Rebeca"
    assert body["language"] == "es"
    assert body["sample_rate"] == 24_000
    assert "CC BY-NC 4.0" in body["license"]


def test_voice_disabled(monkeypatch: pytest.MonkeyPatch, state_dir: Path) -> None:
    # Arrange
    monkeypatch.setenv("MANUELITA_VOICE_ENABLED", "0")
    reset_voice_service()
    # Act
    status = client.get("/api/voice").json()
    response = client.post("/api/tts", json={"text": "Hola."})
    # Assert
    assert (status["available"], status["state"]) == (False, "disabled")
    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "voice_unavailable",
        "message": "Voz desactivada por configuración.",
        "retryable": False,
        "action": "continuar sin voz",
    }
    assert client.get("/api/health").json()["voice_available"] is False


def test_voice_unavailable_without_engine(monkeypatch: pytest.MonkeyPatch, state_dir: Path) -> None:
    # Arrange: Phonon configurado pero el paquete no importa
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ptts":
            raise ImportError("No module named 'ptts'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setenv("MANUELITA_VOICE_ENGINE", "phonon")
    reset_voice_service()
    # Act
    first = client.post("/api/tts", json={"text": "Hola."})
    status = client.get("/api/voice").json()
    # Assert
    assert first.status_code == 503
    assert first.json()["error"]["code"] == "voice_unavailable"
    assert (status["available"], status["state"]) == (False, "unavailable")
    assert "Traceback" not in status["detail"] and "\\" not in status["detail"]
    assert client.post("/api/tts", json={"text": "Otra."}).status_code == 503


def test_health_reports_voice_in_all_branches(monkeypatch: pytest.MonkeyPatch, fake) -> None:
    # Sin clave
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert client.get("/api/health").json()["voice_available"] is True
    # Con clave, sin sondeo
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-prueba")
    assert client.get("/api/health").json()["voice_available"] is True


def test_observability_includes_voice(fake: FakeSynthesizer) -> None:
    voice = client.get("/api/observability").json()["voice"]
    assert voice["available"] is True and voice["voice"] == "Rebeca"


def test_chat_is_unchanged_when_voice_is_disabled(
    monkeypatch: pytest.MonkeyPatch, state_dir
) -> None:
    # Arrange: voz desactivada y recuperador de demo (sin red)
    monkeypatch.setenv("MANUELITA_VOICE_ENABLED", "0")
    reset_voice_service()
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    body = {"message": "¿Qué produce Manuelita?", "mode": "demo", "user_id": "anon-voz"}
    try:
        # Act
        chat = client.post("/api/chat", json=body)
        stream = client.post("/api/chat/stream", json=body)
    finally:
        api._chat_service.cache_clear()
    # Assert
    assert chat.status_code == 200
    assert chat.json()["status"] == "answered"
    assert stream.status_code == 200
    assert '"event": "done"' in stream.text
