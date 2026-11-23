"""Motor y servicio del dictado (spec 023, research R1, R2, R6, R7 y R13)."""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from typing import Any, ClassVar

import numpy as np
import pytest

from proyecto_modelos_lenguaje.stt.config import SttConfig
from proyecto_modelos_lenguaje.stt.engine import (
    FakeTranscriber,
    Segment,
    SttBusyError,
    SttService,
    SttUnavailableError,
    WhisperTranscriber,
)

FAKE = replace(SttConfig(), engine="fake", warmup=False)
SPEECH = (0.3 * np.sin(np.linspace(0, 400 * np.pi, 16_000))).astype(np.float32)
SILENCE = np.zeros(16_000, dtype=np.float32)


class _Slow:
    model_label = "lento"

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds

    def transcribe(self, samples: np.ndarray) -> list[Segment]:
        time.sleep(self.seconds)
        return [Segment("hola")]


def test_fake_transcriber_is_empty_on_silence_and_fixed_on_speech() -> None:
    fake = FakeTranscriber("¿Qué produce Manuelita?")
    assert fake.transcribe(SILENCE) == []
    assert [s.text for s in fake.transcribe(SPEECH)] == ["¿Qué produce Manuelita?"]


def test_service_applies_corrections_and_reports_times() -> None:
    service = SttService(
        FAKE, transcriber=FakeTranscriber("hola valeria caña, ¿qué produce manuelita?")
    )
    result = service.transcribe(SPEECH, audio_ms=1000)
    assert result.text == "hola Valer-IA Caña, ¿qué produce Manuelita?"
    assert not result.empty and not result.truncated
    assert result.language == "es" and result.audio_ms == 1000 and result.stt_ms >= 0
    assert result.model == "fake"


def test_service_returns_empty_without_inventing_words() -> None:
    service = SttService(FAKE, transcriber=FakeTranscriber("algo"))
    result = service.transcribe(SILENCE, audio_ms=1000)
    assert result.empty and result.text == ""


class _Scripted:
    model_label = "guion"

    def __init__(self, segments: list[Segment]) -> None:
        self.segments = segments

    def transcribe(self, samples: np.ndarray) -> list[Segment]:
        return list(self.segments)


def test_service_discards_no_speech_segments_and_hallucinations() -> None:
    segments = [
        Segment("¿Qué produce Manuelita?", no_speech_prob=0.1),
        Segment(" murmullo", no_speech_prob=0.9),
        Segment(" ¡Gracias por ver!", no_speech_prob=0.2),
    ]
    service = SttService(FAKE, transcriber=_Scripted(segments))
    assert service.transcribe(SPEECH, audio_ms=1000).text == "¿Qué produce Manuelita?"
    only_noise = SttService(FAKE, transcriber=_Scripted(segments[1:]))
    assert only_noise.transcribe(SPEECH, audio_ms=1000).empty


def test_service_clips_long_text() -> None:
    service = SttService(FAKE, transcriber=_Scripted([Segment("palabra " * 400)]))
    result = service.transcribe(SPEECH, audio_ms=60_000)
    assert result.truncated and len(result.text) <= 2000


def test_states_and_status_without_paths() -> None:
    disabled = SttService(replace(FAKE, enabled=False))
    assert disabled.status().state == "disabled" and not disabled.status().available
    with pytest.raises(SttUnavailableError):
        disabled.transcribe(SPEECH, audio_ms=1000)

    lazy = SttService(FAKE)
    assert lazy.status().state == "loading" and lazy.status().available
    lazy.ensure_loaded()
    first = lazy.ensure_loaded()
    assert lazy.ensure_loaded() is first and lazy.status().state == "ready"

    status = lazy.status().to_dict()
    assert status["privacy"] and status["silence_ms"] == 1500 and status["max_seconds"] == 60


def test_load_failure_is_unavailable_with_a_friendly_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SttService(replace(FAKE, engine="whisper"))

    def boom(_config: SttConfig) -> Any:
        raise OSError(r"C:\Users\secreto\cache: connection refused")

    monkeypatch.setattr("proyecto_modelos_lenguaje.stt.engine.WhisperTranscriber", boom)
    with pytest.raises(SttUnavailableError):
        service.ensure_loaded()
    status = service.status()
    assert status.state == "unavailable" and not status.available
    assert status.detail and "secreto" not in status.detail and "C:" not in status.detail


def test_invalid_config_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUELITA_STT_ENGINE", "nube")
    service = SttService()
    assert service.status().state == "unavailable"
    assert "nube" in (service.status().detail or "")


def test_warmup_does_not_block() -> None:
    service = SttService(FAKE, transcriber=None)
    started = time.perf_counter()
    service.warmup_async()
    assert time.perf_counter() - started < 0.5
    service.join_warmup(5)
    assert service.status().state == "ready"


def test_busy_after_queue_timeout() -> None:
    config = replace(FAKE, max_concurrent=1, queue_timeout_seconds=1)
    service = SttService(config, transcriber=_Slow(1.5))
    thread = threading.Thread(target=service.transcribe, args=(SPEECH, 1000))
    thread.start()
    time.sleep(0.1)
    with pytest.raises(SttBusyError):
        service.transcribe(SPEECH, audio_ms=1000)
    thread.join()


def test_second_call_waits_when_a_slot_frees_up() -> None:
    config = replace(FAKE, max_concurrent=1, queue_timeout_seconds=5)
    service = SttService(config, transcriber=_Slow(0.2))
    results: list[str] = []
    threads = [
        threading.Thread(target=lambda: results.append(service.transcribe(SPEECH, 1000).text))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == ["hola", "hola"]


class _Info:
    language = "es"


class _FakeWhisperModel:
    calls: ClassVar[list[dict[str, Any]]] = []
    init: ClassVar[dict[str, Any]] = {}

    def __init__(self, model: str, **kwargs: Any) -> None:
        type(self).init = {"model": model, **kwargs}

    def transcribe(self, audio: np.ndarray, **kwargs: Any):
        type(self).calls.append(kwargs)

        class _Seg:
            text = " ¿Qué produce Manuelita?"
            no_speech_prob = 0.05

        return iter([_Seg()]), _Info()


def test_whisper_transcriber_passes_the_configured_parameters() -> None:
    config = replace(SttConfig(), cpu_threads=4, beam_size=2)
    transcriber = WhisperTranscriber(config, model_factory=_FakeWhisperModel)
    segments = transcriber.transcribe(SPEECH)
    assert [s.text for s in segments] == ["¿Qué produce Manuelita?"]
    assert segments[0].no_speech_prob == pytest.approx(0.05)
    assert _FakeWhisperModel.init == {
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "cpu_threads": 4,
    }
    call = _FakeWhisperModel.calls[-1]
    assert call["language"] == "es" and call["beam_size"] == 2
    assert call["vad_filter"] is True and call["condition_on_previous_text"] is False
    assert call["initial_prompt"].startswith("Manuelita, Valer-IA Caña")
    assert transcriber.model_label == "base-int8"
