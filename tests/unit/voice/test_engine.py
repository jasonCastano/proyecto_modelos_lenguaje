"""Motor de voz con estado (spec 016, research R5): sin red ni modelo."""

from __future__ import annotations

import builtins
import threading
import time

import numpy as np
import pytest

from proyecto_modelos_lenguaje.voice import engine as engine_module
from proyecto_modelos_lenguaje.voice.config import VoiceConfig
from proyecto_modelos_lenguaje.voice.engine import (
    SPANISH_VOICES,
    FakeSynthesizer,
    UnknownVoiceError,
    VoiceService,
    VoiceUnavailableError,
)

FAKE = VoiceConfig(engine="fake", voice="Ximena", warmup=False)


def test_fake_synthesizer_is_deterministic_and_proportional() -> None:
    synth = FakeSynthesizer()
    short = synth.synth("Hola.", "Ximena")
    longer = synth.synth("Hola, bienvenidos a Manuelita.", "Ximena")
    assert short.dtype == np.float32
    assert np.array_equal(short, synth.synth("Hola.", "Ximena"))
    assert len(longer) > len(short)


def test_catalog_has_thirteen_spanish_female_voices() -> None:
    females = [voice for voice in SPANISH_VOICES if voice.gender == "female"]
    assert len(females) == 13
    assert {voice.accent for voice in females} == {"ES", "MX"}


def test_service_starts_loading_then_ready() -> None:
    # Arrange
    service = VoiceService(FAKE)
    assert service.state == "loading"
    assert service.status().available is True
    # Act
    result = service.synthesize("Manuelita produce azúcar.")
    # Assert
    assert service.state == "ready"
    assert result.voice == "Ximena"
    assert result.sample_rate == 24_000
    assert result.audio_ms > 0
    assert service.status().sample_rate == 24_000


def test_disabled_service() -> None:
    service = VoiceService(VoiceConfig(enabled=False, engine="fake"))
    status = service.status()
    assert (status.available, status.state) == (False, "disabled")
    assert status.detail == "Voz desactivada por configuración."
    with pytest.raises(VoiceUnavailableError):
        service.synthesize("Hola.")


def test_import_failure_marks_unavailable_with_friendly_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: simular que ptts no está instalado
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "ptts":
            raise ImportError("No module named 'ptts'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    service = VoiceService(VoiceConfig(engine="phonon", warmup=False))
    # Act
    with pytest.raises(VoiceUnavailableError):
        service.synthesize("Hola.")
    # Assert
    status = service.status()
    assert (status.available, status.state) == (False, "unavailable")
    assert "ptts" in status.detail and "Traceback" not in status.detail
    assert ":\\" not in status.detail and "/" not in status.detail.replace("gradium/", "")


def test_gated_model_error_mentions_hf_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(self, config):
        raise RuntimeError("401 Client Error: gated repo C:\\Users\\x\\cache")

    monkeypatch.setattr(engine_module.PhononSynthesizer, "__init__", boom)
    service = VoiceService(VoiceConfig(engine="phonon", warmup=False))
    with pytest.raises(VoiceUnavailableError):
        service.ensure_loaded()
    assert "HF_TOKEN" in service.status().detail
    assert "Users" not in service.status().detail


def test_synthesis_error_keeps_service_ready() -> None:
    class Flaky(FakeSynthesizer):
        def synth(self, text: str, voice: str) -> np.ndarray:
            if "falla" in text:
                raise RuntimeError("boom")
            return super().synth(text, voice)

    service = VoiceService(FAKE, synthesizer=Flaky())
    with pytest.raises(RuntimeError):
        service.synthesize("esto falla")
    assert service.state == "ready"
    assert service.synthesize("esto sí").audio_ms > 0


def test_unknown_voice_is_rejected_and_ids_are_accepted() -> None:
    service = VoiceService(FAKE)
    with pytest.raises(UnknownVoiceError):
        service.synthesize("Hola.", voice="Inexistente")
    assert service.synthesize("Hola.", voice="VDwnGxAo68C8U8vC").voice == "Ximena"
    assert service.synthesize("Hola.", voice="regina").voice == "Regina"


def test_concurrent_synthesis_is_serialized() -> None:
    # Arrange: un sintetizador que detecta llamadas solapadas
    class Slow(FakeSynthesizer):
        def __init__(self) -> None:
            super().__init__()
            self.active = 0
            self.max_active = 0

        def synth(self, text: str, voice: str) -> np.ndarray:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            time.sleep(0.02)
            self.active -= 1
            return super().synth(text, voice)

    slow = Slow()
    service = VoiceService(FAKE, synthesizer=slow)
    threads = [threading.Thread(target=service.synthesize, args=("Hola.",)) for _ in range(5)]
    # Act
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # Assert
    assert slow.max_active == 1


def test_warmup_loads_in_background() -> None:
    service = VoiceService(FAKE)
    service.warmup_async()
    service._warmup.join(timeout=5)
    assert service.state == "ready"
