"""Dictado con el modelo real (spec 023, T042).

Requiere el modelo de faster-whisper (se descarga de Hugging Face la primera vez) y Phonon con
``HF_TOKEN`` para sintetizar la frase. Marcador ``voice``: excluido por defecto y en CI.

    uv run pytest -o addopts="" -m voice tests/integration/stt
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from dotenv import load_dotenv

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.stt.audio import resample
from proyecto_modelos_lenguaje.stt.config import CONFIG_PATH as STT_CONFIG
from proyecto_modelos_lenguaje.stt.config import load_stt_config
from proyecto_modelos_lenguaje.stt.engine import SttService
from proyecto_modelos_lenguaje.voice.config import CONFIG_PATH as VOICE_CONFIG
from proyecto_modelos_lenguaje.voice.config import load_voice_config
from proyecto_modelos_lenguaje.voice.engine import VoiceService

pytestmark = pytest.mark.voice


@pytest.fixture(scope="module")
def service() -> SttService:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    # La suite fuerza los motores "fake" por variable de entorno; aquí se usan los reales.
    stt = SttService(replace(load_stt_config(STT_CONFIG), engine="whisper", warmup=False))
    stt.ensure_loaded()
    stt.transcribe(np.zeros(16_000, dtype=np.float32), 1000)  # la primera llamada es más lenta
    return stt


def test_question_is_transcribed_with_the_brand_name(service: SttService) -> None:
    phonon = VoiceService(replace(load_voice_config(VOICE_CONFIG), engine="phonon", enabled=True))
    voice = phonon.synthesize("¿Qué produce Manuelita?")
    samples = resample(voice.samples, voice.sample_rate)
    result = service.transcribe(samples, round(samples.size / 16))
    assert "Manuelita" in result.text
    assert result.stt_ms < 2000


def test_silence_is_empty(service: SttService) -> None:
    rng = np.random.default_rng(7)
    silence = rng.normal(0, 0.001, 16_000 * 3).astype(np.float32)
    assert service.transcribe(silence, 3000).empty
