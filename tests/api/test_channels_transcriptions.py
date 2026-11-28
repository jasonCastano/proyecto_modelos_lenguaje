"""``POST /api/channels/transcriptions`` (spec 028, T010, channel-api-v2 §2).

Dictado simulado (``MANUELITA_STT_ENGINE=fake`` en conftest): sin red ni modelo.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.stt.audio import encode_wav16k

TOKEN = "token-de-prueba-0123456789abcdef"
HEADERS = {"X-Channel-Token": TOKEN, "Content-Type": "application/octet-stream"}
URL = "/api/channels/transcriptions"


def ogg_opus(seconds: float, amplitude: float = 0.3) -> bytes:
    """Nota de voz sintética en Ogg/Opus (el formato de WhatsApp)."""
    import av

    buffer = io.BytesIO()
    container = av.open(buffer, mode="w", format="ogg")
    stream = container.add_stream("libopus", rate=48_000)
    stream.layout = "mono"
    count = int(48_000 * seconds)
    pcm = (amplitude * np.sin(2 * np.pi * 220 * np.arange(count) / 48_000)).astype(np.float32)
    frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format="flt", layout="mono")
    frame.sample_rate = 48_000
    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode(None):
        container.mux(packet)
    container.close()
    return buffer.getvalue()


@pytest.fixture()
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", TOKEN)
    return TestClient(api.app)


def test_transcribes_a_whatsapp_voice_note(client: TestClient) -> None:
    response = client.post(URL, content=ogg_opus(2.0), headers=HEADERS)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"text", "language", "audio_ms", "latency_ms"}
    assert body["text"] == "¿Qué produce Manuelita?" and body["language"] == "es"
    assert 1900 <= body["audio_ms"] <= 2100


def test_accepts_wav_and_returns_empty_text_for_silence(client: TestClient) -> None:
    silence = encode_wav16k(np.zeros(16_000, dtype=np.float32))
    response = client.post(URL, content=silence, headers=HEADERS)
    assert response.status_code == 200 and response.json()["text"] == ""


@pytest.mark.parametrize(
    ("data", "status", "code"),
    [(b"", 400, "audio_invalid"), (b"esto no es audio", 400, "audio_invalid")],
)
def test_invalid_audio(client: TestClient, data: bytes, status: int, code: str) -> None:
    response = client.post(URL, content=data, headers=HEADERS)
    assert response.status_code == status and response.json()["error"]["code"] == code


def test_too_long(client: TestClient) -> None:
    response = client.post(URL, content=ogg_opus(121.0, 0.1), headers=HEADERS)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "audio_too_long"


def test_requires_token_and_loopback(client: TestClient) -> None:
    assert client.post(URL, content=ogg_opus(1.0)).status_code == 403
    remote = TestClient(api.app, client=("10.0.0.5", 50000))
    assert remote.post(URL, content=ogg_opus(1.0), headers=HEADERS).status_code == 403
