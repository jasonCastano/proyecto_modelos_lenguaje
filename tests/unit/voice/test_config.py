"""Configuración de la voz (spec 016, contracts/voice-config.md)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.voice.config import (
    CONFIG_PATH,
    VoiceConfig,
    VoiceConfigError,
    load_voice_config,
)

ENV_VARS = (
    "MANUELITA_VOICE_ENABLED",
    "MANUELITA_VOICE_ENGINE",
    "MANUELITA_VOICE",
    "MANUELITA_VOICE_WARMUP",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_versioned_toml_uses_phonon_spanish_female_voice() -> None:
    # Act
    config = load_voice_config(CONFIG_PATH)
    # Assert
    assert config.enabled is True
    assert config.engine == "phonon"
    assert config.model == "hf://gradium/phonon-40m-es"
    assert config.language == "es"
    assert config.quant == "q8_0"
    assert config.voice == "Rebeca"  # voz oficial del agente (T037)
    assert config.voice_gender == "female"
    assert config.max_chars == 600


def test_environment_overrides_toml(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("MANUELITA_VOICE_ENABLED", "0")
    monkeypatch.setenv("MANUELITA_VOICE_ENGINE", "fake")
    monkeypatch.setenv("MANUELITA_VOICE", "Regina")
    monkeypatch.setenv("MANUELITA_VOICE_WARMUP", "false")
    # Act
    config = load_voice_config(CONFIG_PATH)
    # Assert
    assert (config.enabled, config.engine, config.voice, config.warmup) == (
        False,
        "fake",
        "Regina",
        False,
    )


def test_missing_file_uses_defaults(tmp_path: Path) -> None:
    assert load_voice_config(tmp_path / "no-existe.toml") == VoiceConfig()


@pytest.mark.parametrize(
    "body",
    [
        'engine = "otro"',
        'quant = "q4"',
        'quant = "q8"',
        "max_chars = 0",
        "max_chars = 1001",
        'voice = "  "',
    ],
)
def test_invalid_values_are_rejected(tmp_path: Path, body: str) -> None:
    # Arrange
    path = tmp_path / "voice.toml"
    path.write_text(f"[voice]\n{body}\n", encoding="utf-8")
    # Act / Assert
    with pytest.raises(VoiceConfigError):
        load_voice_config(path)


def test_unknown_engine_from_env_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANUELITA_VOICE_ENGINE", "espeak")
    with pytest.raises(VoiceConfigError):
        load_voice_config(CONFIG_PATH)
