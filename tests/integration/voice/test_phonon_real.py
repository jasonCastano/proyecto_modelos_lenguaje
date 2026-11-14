"""Voz con el modelo Phonon real (spec 016, T025).

Requiere ``ptts``, ``HF_TOKEN`` y haber aceptado las condiciones de ``gradium/phonon-40m-es``.
Marcada ``voice``: excluida por defecto y en la CI. Ejecutar con:

    uv run pytest -o addopts="" -m voice tests/integration/voice
"""

from __future__ import annotations

import io
import time
import wave
from dataclasses import replace

import pytest
from dotenv import load_dotenv

from proyecto_modelos_lenguaje.voice.audio import to_wav_bytes
from proyecto_modelos_lenguaje.voice.config import CONFIG_PATH, load_voice_config
from proyecto_modelos_lenguaje.voice.engine import VoiceService, find_voice

pytestmark = pytest.mark.voice

SENTENCE = "Manuelita produce azúcar, etanol y energía renovable en el Valle del Cauca desde 1864."


@pytest.fixture(scope="module")
def service() -> VoiceService:
    load_dotenv()
    # La suite fuerza el motor "fake" por variable de entorno; aquí se usa el configurado.
    config = replace(load_voice_config(CONFIG_PATH), engine="phonon", enabled=True)
    voice = VoiceService(config)
    voice.ensure_loaded()
    return voice


def test_phonon_is_ready_with_configured_female_voice(service: VoiceService) -> None:
    status = service.status()
    assert (status.available, status.state, status.engine) == (True, "ready", "phonon")
    info = find_voice(service.voices(), service.config.voice)
    assert info is not None
    assert info.gender == "female"


def test_spanish_sentence_produces_24khz_wav_quickly(service: VoiceService) -> None:
    # Arrange: una primera síntesis calienta el motor
    service.synthesize("Hola.")
    started = time.perf_counter()
    # Act
    result = service.synthesize(SENTENCE)
    elapsed = time.perf_counter() - started
    data = to_wav_bytes(result.samples, result.sample_rate)
    # Assert
    with wave.open(io.BytesIO(data)) as handle:
        assert handle.getframerate() == 24_000
        assert handle.getnframes() > 0
    assert result.audio_ms > 1000
    # SC-001: la oración debe estar lista en < 1,5 s y sintetizarse más rápido que el tiempo real.
    assert elapsed < 1.5, f"síntesis de {len(SENTENCE)} caracteres tardó {elapsed:.2f} s"
    assert elapsed < 0.5 * result.audio_ms / 1000
