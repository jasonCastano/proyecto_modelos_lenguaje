"""Configuración de la voz del agente (spec 016, contracts/voice-config.md).

Se lee de ``config/voice.toml``; las variables ``MANUELITA_VOICE_*`` tienen prioridad.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

from ..config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config" / "voice.toml"
ENGINES = ("phonon", "fake")
# Formatos que acepta ptts 0.7.1 (``ptts.available_quants()``).
QUANTS = ("f32", "q8_0", "q8_1", "q8k", "q6k", "q5_0", "q5_1", "q5k", "q4_0", "q4_1", "q4k")
LICENSE = "CC BY-NC 4.0 (modelo y voces); MIT/Apache-2.0 (motor)"
FALSE_VALUES = {"0", "false", "no", "off"}
TRUE_VALUES = {"1", "true", "yes", "on"}


class VoiceConfigError(ValueError):
    """Configuración de voz inválida; el servicio queda no disponible con este motivo."""


@dataclass(frozen=True)
class VoiceConfig:
    enabled: bool = True
    engine: str = "phonon"
    model: str = "hf://gradium/phonon-40m-es"
    language: str = "es"
    quant: str = "q8_0"
    voice: str = "Rebeca"
    voice_gender: str = "female"
    max_chars: int = 600
    warmup: bool = True

    def validate(self) -> VoiceConfig:
        if self.engine not in ENGINES:
            raise VoiceConfigError(
                f"Motor de voz desconocido: {self.engine!r} (usa phonon o fake)."
            )
        if self.quant not in QUANTS:
            allowed = ", ".join(QUANTS)
            raise VoiceConfigError(f"Cuantización inválida: {self.quant!r} (usa uno de {allowed}).")
        if not 1 <= int(self.max_chars) <= 1000:
            raise VoiceConfigError("max_chars debe estar entre 1 y 1000.")
        if not str(self.voice).strip():
            raise VoiceConfigError("La voz configurada no puede estar vacía.")
        return self


def _flag(name: str, current: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in FALSE_VALUES:
        return False
    if raw in TRUE_VALUES:
        return True
    return current


def load_voice_config(path: Path | None = None) -> VoiceConfig:
    """Lee el TOML (si existe), aplica las variables de entorno y valida."""
    source = Path(path) if path is not None else CONFIG_PATH
    data: dict = {}
    if source.exists():
        with source.open("rb") as handle:
            data = dict(tomllib.load(handle).get("voice", {}))
    allowed = set(VoiceConfig.__dataclass_fields__)
    config = VoiceConfig(**{key: value for key, value in data.items() if key in allowed})
    engine = os.environ.get("MANUELITA_VOICE_ENGINE", "").strip().lower()
    voice = os.environ.get("MANUELITA_VOICE", "").strip()
    config = replace(
        config,
        enabled=_flag("MANUELITA_VOICE_ENABLED", config.enabled),
        warmup=_flag("MANUELITA_VOICE_WARMUP", config.warmup),
        engine=engine or config.engine,
        voice=voice or config.voice,
    )
    return config.validate()
