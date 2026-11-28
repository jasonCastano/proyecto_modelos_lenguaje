"""Spec 028 (T006, research R5): idioma automático del dictado para las notas de voz."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from proyecto_modelos_lenguaje.stt.config import SttConfig, SttConfigError
from proyecto_modelos_lenguaje.stt.engine import Segment, SttService

VOICE = np.full(16_000, 0.2, dtype=np.float32)


@dataclass
class DetectingTranscriber:
    """Transcriptor simulado que «detecta» un idioma fijo y registra lo que le pidieron."""

    detected: str
    text: str = "What does Manuelita produce?"
    model_label: str = "fake-detect"
    requested: str | None = "unset"

    def transcribe(self, samples: np.ndarray) -> list[Segment]:
        return [Segment(self.text)]

    def transcribe_with_language(
        self, samples: np.ndarray, language: str | None
    ) -> tuple[list[Segment], str]:
        self.requested = language
        return [Segment(self.text)], language or self.detected


def test_config_accepts_auto_and_rejects_other_words() -> None:
    assert SttConfig(language="auto").validate().language == "auto"
    with pytest.raises(SttConfigError):
        SttConfig(language="spanish").validate()


def test_auto_lets_whisper_detect_english() -> None:
    transcriber = DetectingTranscriber(detected="en")
    service = SttService(SttConfig(engine="fake"), transcriber=transcriber)

    result = service.transcribe(VOICE, 1000, language="auto")

    assert transcriber.requested is None  # Whisper recibe language=None y detecta
    assert result.language == "en" and not result.language_fallback


def test_unsupported_language_falls_back_to_spanish() -> None:
    service = SttService(SttConfig(engine="fake"), transcriber=DetectingTranscriber(detected="fr"))

    result = service.transcribe(VOICE, 1000, language="auto")

    assert result.language == "es" and result.language_fallback is True
    assert "language_fallback" not in result.to_dict()  # el contrato de /api/stt no cambia


def test_web_dictation_keeps_the_configured_language() -> None:
    transcriber = DetectingTranscriber(detected="en")
    service = SttService(SttConfig(engine="fake", language="es"), transcriber=transcriber)

    result = service.transcribe(VOICE, 1000)

    assert transcriber.requested == "es" and result.language == "es"


def test_fake_transcriber_detects_by_its_text() -> None:
    from proyecto_modelos_lenguaje.stt.engine import FakeTranscriber

    _, language = FakeTranscriber("What does Manuelita produce?").transcribe_with_language(
        VOICE, None
    )
    assert language == "en"
    _, language = FakeTranscriber().transcribe_with_language(VOICE, None)
    assert language == "es"
