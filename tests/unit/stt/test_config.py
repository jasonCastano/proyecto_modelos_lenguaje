"""Configuración del dictado (spec 023, data-model §1)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.stt.config import (
    CONFIG_PATH,
    SttConfig,
    SttConfigError,
    load_stt_config,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "MANUELITA_STT_ENABLED",
        "MANUELITA_STT_ENGINE",
        "MANUELITA_STT_MODEL",
        "MANUELITA_STT_WARMUP",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_match_the_data_model() -> None:
    config = SttConfig().validate()
    assert config.enabled and config.engine == "whisper" and config.model == "base"
    assert config.compute_type == "int8" and config.cpu_threads == 0
    assert config.language == "es" and config.beam_size == 1
    assert config.no_speech_threshold == 0.6
    assert config.max_seconds == 60 and config.max_bytes == 2_097_152
    assert config.silence_ms == 1500 and config.min_speech_ms == 300
    assert config.handsfree_idle_seconds == 60
    assert config.max_concurrent == 2 and config.queue_timeout_seconds == 10
    assert config.warmup
    assert "Manuelita" in config.vocabulary and "Valer-IA Caña" in config.vocabulary


def test_repository_file_loads_and_has_the_brand_corrections() -> None:
    config = load_stt_config(CONFIG_PATH)
    assert config.engine == "whisper" and config.model == "base"
    assert dict(config.corrections)["valeria caña"] == "Valer-IA Caña"
    assert "Mejillones América" in config.vocabulary


def test_toml_overrides_and_environment_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "stt.toml"
    path.write_text(
        '[stt]\nmodel = "small"\nbeam_size = 2\nwarmup = true\nenabled = true\n'
        '[stt.corrections]\n"oceanos" = "Océanos"\n',
        encoding="utf-8",
    )
    config = load_stt_config(path)
    assert config.model == "small" and config.beam_size == 2
    assert dict(config.corrections) == {"oceanos": "Océanos"}

    monkeypatch.setenv("MANUELITA_STT_ENABLED", "0")
    monkeypatch.setenv("MANUELITA_STT_ENGINE", "fake")
    monkeypatch.setenv("MANUELITA_STT_MODEL", "tiny")
    monkeypatch.setenv("MANUELITA_STT_WARMUP", "off")
    config = load_stt_config(path)
    assert not config.enabled and config.engine == "fake" and config.model == "tiny"
    assert not config.warmup


@pytest.mark.parametrize(
    "changes",
    [
        {"engine": "vosk"},
        {"compute_type": "float16"},
        {"beam_size": 0},
        {"beam_size": 6},
        {"max_seconds": 0.5},
        {"max_seconds": 121},
        {"max_seconds": 60, "max_bytes": 44 + 16000 * 2 * 60 - 1},
        {"silence_ms": 200},
        {"silence_ms": 5001},
        {"min_speech_ms": 50},
        {"min_speech_ms": 2001},
        {"handsfree_idle_seconds": 9},
        {"handsfree_idle_seconds": 601},
        {"max_concurrent": 0},
        {"max_concurrent": 9},
        {"queue_timeout_seconds": 0.5},
        {"queue_timeout_seconds": 61},
        {"cpu_threads": 33},
        {"no_speech_threshold": 1.5},
        {"vocabulary": tuple(f"término {i}" for i in range(61))},
        {"vocabulary": ("x" * 41,)},
        {"vocabulary": tuple(f"palabra larga número {i:02d}" for i in range(30))},
        {"corrections": (("valeria", ""),)},
        {"corrections": (("Valeria", "Valer-IA"),)},
        {"language": "español"},
    ],
)
def test_invalid_values_raise(changes: dict) -> None:
    with pytest.raises(SttConfigError):
        replace(SttConfig(), **changes).validate()


def test_invalid_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "stt.toml"
    path.write_text('[stt]\nengine = "cloud"\n', encoding="utf-8")
    with pytest.raises(SttConfigError):
        load_stt_config(path)
