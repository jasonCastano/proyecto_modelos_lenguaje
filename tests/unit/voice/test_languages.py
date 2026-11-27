"""Voz por idioma (spec 028, T021, research R4): español con Rebeca, inglés con phonon-31m-en."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.voice import __main__ as cli
from proyecto_modelos_lenguaje.voice.engine import (
    ENGLISH_VOICES,
    VoiceUnavailableError,
    get_voice_service,
    reset_voice_service,
)


@pytest.fixture(autouse=True)
def fresh_services(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MANUELITA_VOICE_ENGINE", "fake")
    reset_voice_service()
    yield
    reset_voice_service()


def test_spanish_is_the_default_service() -> None:
    service = get_voice_service()
    assert service is get_voice_service("es")
    assert service.config.language == "es" and service.config.voice == "Rebeca"


def test_english_has_its_own_model_and_voice() -> None:
    english = get_voice_service("en")
    assert english is get_voice_service("en")  # un servicio por idioma, reutilizado
    assert english.config.model == "hf://gradium/phonon-31m-en"
    result = english.synthesize("Hi, I'm Valeria.")
    assert result.voice == "Harper" and result.audio_ms > 0
    assert {info.name for info in english.voices()} == {info.name for info in ENGLISH_VOICES}


def test_unknown_language_is_unavailable() -> None:
    with pytest.raises(VoiceUnavailableError):
        get_voice_service("fr")


def test_cli_checks_the_english_voice(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--check", "--language", "en"]) == cli.EXIT_OK
    assert "voice: Harper" in capsys.readouterr().out
    assert cli.main(["--check", "--language", "fr"]) == cli.EXIT_ERROR
