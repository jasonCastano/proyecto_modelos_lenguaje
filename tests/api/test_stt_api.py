"""Contrato del dictado: ``GET/POST /api/stt`` y ``/api/health`` (spec 023, stt-api.md)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.stt.audio import encode_wav16k
from proyecto_modelos_lenguaje.stt.config import SttConfig
from proyecto_modelos_lenguaje.stt.engine import (
    FakeTranscriber,
    Segment,
    SttService,
    reset_stt_service,
)

client = TestClient(api.app)
FAKE = replace(SttConfig(), engine="fake", warmup=False)
SPOKEN = "hola valeria caña, ¿qué produce manuelita?"
SPEECH = encode_wav16k((0.3 * np.sin(np.linspace(0, 400 * np.pi, 16_000))).astype(np.float32))
SILENCE = encode_wav16k(np.zeros(16_000, dtype=np.float32))
WAV = {"Content-Type": "audio/wav"}


@pytest.fixture()
def state_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    target = tmp_path / "state"
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(target))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    return target


@pytest.fixture()
def fake(state_dir: Path):
    service = SttService(FAKE, transcriber=FakeTranscriber(SPOKEN))
    reset_stt_service(service)
    yield service
    reset_stt_service(None)


def _error(response) -> dict:
    return response.json()["error"]


def test_status_fields(fake: SttService) -> None:
    body = client.get("/api/stt").json()
    assert set(body) == {
        "available",
        "state",
        "engine",
        "model",
        "language",
        "detail",
        "max_seconds",
        "silence_ms",
        "min_speech_ms",
        "handsfree_idle_seconds",
        "privacy",
    }
    assert body["available"] and body["state"] == "ready" and body["engine"] == "fake"
    assert body["privacy"] and body["silence_ms"] == 1500 and body["max_seconds"] == 60


def test_transcribes_speech_with_corrections(fake: SttService, state_dir: Path) -> None:
    response = client.post("/api/stt", content=SPEECH, headers={**WAV, "X-Thread-Id": "t-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "hola Valer-IA Caña, ¿qué produce Manuelita?"
    assert body["empty"] is False and body["truncated"] is False
    assert body["audio_ms"] == 1000 and body["stt_ms"] >= 0 and body["model"] == "fake"
    log = (state_dir / "logs" / "stt.jsonl").read_text(encoding="utf-8")
    record = json.loads(log.splitlines()[-1])
    assert record["thread_id"] == "t-1" and record["status"] == "ok"
    assert record["chars"] == len(body["text"])
    assert "Manuelita" not in log and "Valer" not in log  # nunca el texto


def test_silence_is_empty_not_an_error(fake: SttService) -> None:
    response = client.post("/api/stt", content=SILENCE, headers=WAV)
    assert response.status_code == 200
    assert response.json()["empty"] is True and response.json()["text"] == ""


def test_empty_body(fake: SttService) -> None:
    response = client.post("/api/stt", content=b"", headers=WAV)
    assert response.status_code == 400 and _error(response)["code"] == "stt_empty_audio"


def test_too_large(fake: SttService) -> None:
    reset_stt_service(
        SttService(replace(FAKE, max_seconds=1, max_bytes=40_000), transcriber=FakeTranscriber())
    )
    big = encode_wav16k(np.zeros(16_000 * 2, dtype=np.float32))
    response = client.post("/api/stt", content=big, headers=WAV)
    assert response.status_code == 413 and _error(response)["code"] == "stt_too_large"


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"ID3\x04\x00" + b"\xff\xfb" * 500, "audio/mpeg"),
        (b"ID3\x04\x00" + b"\xff\xfb" * 500, "audio/wav"),
    ],
)
def test_unsupported_format(fake: SttService, content: bytes, content_type: str) -> None:
    response = client.post("/api/stt", content=content, headers={"Content-Type": content_type})
    assert response.status_code == 415
    assert _error(response)["code"] == "stt_unsupported_format"


def test_disabled_service_is_unavailable(state_dir: Path) -> None:
    reset_stt_service(SttService(replace(FAKE, enabled=False)))
    try:
        response = client.post("/api/stt", content=SPEECH, headers=WAV)
        assert response.status_code == 503
        error = _error(response)
        assert error["code"] == "stt_unavailable" and error["retryable"] is True
        assert client.get("/api/stt").json()["available"] is False
    finally:
        reset_stt_service(None)


def test_busy(fake: SttService, monkeypatch: pytest.MonkeyPatch) -> None:
    from proyecto_modelos_lenguaje.stt.engine import SttBusyError

    def busy(*_args, **_kwargs):
        raise SttBusyError("ocupado")

    monkeypatch.setattr(fake, "transcribe", busy)
    response = client.post("/api/stt", content=SPEECH, headers=WAV)
    assert response.status_code == 503 and _error(response)["code"] == "stt_busy"


def test_engine_failure_is_a_clean_500(state_dir: Path) -> None:
    class Broken:
        model_label = "roto"

        def transcribe(self, _samples) -> list[Segment]:
            raise RuntimeError("Traceback: detalle interno en C:\\ruta")

    reset_stt_service(SttService(FAKE, transcriber=Broken()))
    try:
        response = client.post("/api/stt", content=SPEECH, headers=WAV)
        assert response.status_code == 500
        error = _error(response)
        assert error["code"] == "stt_error" and error["retryable"] is True
        assert "Traceback" not in response.text and "ruta" not in response.text
    finally:
        reset_stt_service(None)


def test_health_reports_stt(fake: SttService) -> None:
    assert client.get("/api/health").json()["stt_available"] is True
    reset_stt_service(SttService(replace(FAKE, enabled=False)))
    assert client.get("/api/health").json()["stt_available"] is False


def _snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {str(path) for path in root.rglob("*") if path.is_file()}


def test_audio_never_touches_disk(
    fake: SttService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # SC-006: ni el directorio de trabajo, ni el temporal, ni data/ reciben archivos.
    work = tmp_path / "work"
    temp = tmp_path / "temp"
    work.mkdir()
    temp.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    for name in ("TMP", "TEMP", "TMPDIR"):
        monkeypatch.setenv(name, str(temp))
    data_before = _snapshot(PROJECT_ROOT / "data")
    for _ in range(5):
        assert client.post("/api/stt", content=SPEECH, headers=WAV).status_code == 200
    assert not any(work.iterdir()) and not any(temp.iterdir())
    assert _snapshot(PROJECT_ROOT / "data") == data_before
    assert os.getcwd() == str(work)
