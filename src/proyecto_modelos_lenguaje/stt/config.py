"""Configuración del dictado (spec 023, data-model §1).

Se lee de ``config/stt.toml``; las variables ``MANUELITA_STT_*`` tienen prioridad. Una configuración
inválida no detiene la API: el servicio queda ``unavailable`` con el motivo (igual que la voz).
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

from ..config import PROJECT_ROOT
from .text import MAX_PROMPT_CHARS

CONFIG_PATH = PROJECT_ROOT / "config" / "stt.toml"
ENGINES = ("whisper", "fake")
COMPUTE_TYPES = ("int8", "int8_float32", "float32")
LICENSE = "MIT (faster-whisper, pesos de Whisper y Silero VAD)"
PRIVACY = "Tu voz se convierte en texto en el servidor del proyecto y el audio no se guarda."
FALSE_VALUES = {"0", "false", "no", "off"}
TRUE_VALUES = {"1", "true", "yes", "on"}
WAV_HEADER_BYTES = 44
# Spec 028 (R5): «auto» detecta el idioma; el canal solo acepta español e inglés.
AUTO_LANGUAGE = "auto"
SUPPORTED_LANGUAGES = ("es", "en")

DEFAULT_VOCABULARY = (
    "Manuelita",
    "Valer-IA Caña",
    "Palmira",
    "Valle del Cauca",
    "Fundación Manuelita",
    "Océanos",
    "Mejillones América",
    "Laredo",
    "Aceites Manuelita",
    "Ingenio Manuelita",
    "Educar Uno a Uno",
    "Línea Ética",
)
DEFAULT_CORRECTIONS = (
    ("valeria caña", "Valer-IA Caña"),
    ("valeria cana", "Valer-IA Caña"),
    ("valeria", "Valer-IA"),
    ("manuelita", "Manuelita"),
    ("oceanos", "Océanos"),
)


class SttConfigError(ValueError):
    """Configuración del dictado inválida; el servicio queda no disponible con este motivo."""


def _between(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise SttConfigError(f"{name} debe estar entre {low:g} y {high:g} (recibido {value!r}).")


@dataclass(frozen=True)
class SttConfig:
    enabled: bool = True
    engine: str = "whisper"
    model: str = "base"
    compute_type: str = "int8"
    cpu_threads: int = 0
    language: str = "es"
    beam_size: int = 1
    vocabulary: tuple[str, ...] = DEFAULT_VOCABULARY
    corrections: tuple[tuple[str, str], ...] = DEFAULT_CORRECTIONS
    no_speech_threshold: float = 0.6
    max_seconds: float = 60
    max_bytes: int = 2_097_152
    silence_ms: int = 1500
    min_speech_ms: int = 300
    handsfree_idle_seconds: int = 60
    max_concurrent: int = 2
    queue_timeout_seconds: float = 10
    warmup: bool = True

    def validate(self) -> SttConfig:
        if self.engine not in ENGINES:
            raise SttConfigError(
                f"Motor de dictado desconocido: {self.engine!r} (usa whisper o fake)."
            )
        if self.compute_type not in COMPUTE_TYPES:
            allowed = ", ".join(COMPUTE_TYPES)
            raise SttConfigError(f"compute_type inválido: {self.compute_type!r} (usa {allowed}).")
        if not str(self.model).strip():
            raise SttConfigError("El modelo de dictado no puede estar vacío.")
        if self.language != AUTO_LANGUAGE and not re.fullmatch(r"[a-z]{2}", str(self.language)):
            raise SttConfigError(
                "language debe ser un código ISO de dos letras (p. ej. «es») o «auto»."
            )
        _between("cpu_threads", self.cpu_threads, 0, 32)
        _between("beam_size", self.beam_size, 1, 5)
        _between("no_speech_threshold", self.no_speech_threshold, 0, 1)
        _between("max_seconds", self.max_seconds, 1, 120)
        minimum = WAV_HEADER_BYTES + 16_000 * 2 * self.max_seconds
        if self.max_bytes < minimum:
            raise SttConfigError(
                f"max_bytes debe ser al menos {int(minimum)} para {self.max_seconds:g} s de audio."
            )
        _between("silence_ms", self.silence_ms, 300, 5000)
        _between("min_speech_ms", self.min_speech_ms, 100, 2000)
        _between("handsfree_idle_seconds", self.handsfree_idle_seconds, 10, 600)
        _between("max_concurrent", self.max_concurrent, 1, 8)
        _between("queue_timeout_seconds", self.queue_timeout_seconds, 1, 60)
        if len(self.vocabulary) > 60:
            raise SttConfigError("El vocabulario admite como máximo 60 términos.")
        for term in self.vocabulary:
            if not 1 <= len(str(term).strip()) <= 40:
                raise SttConfigError(
                    f"Término de vocabulario inválido (1–40 caracteres): {term!r}."
                )
        if len(", ".join(self.vocabulary)) + 1 > MAX_PROMPT_CHARS:
            raise SttConfigError(
                f"El vocabulario unido supera {MAX_PROMPT_CHARS} caracteres de prompt inicial."
            )
        for key, value in self.corrections:
            if key != key.lower() or not key.strip():
                raise SttConfigError(f"Las claves de corrección van en minúsculas: {key!r}.")
            if not str(value).strip():
                raise SttConfigError(f"La corrección de {key!r} no puede estar vacía.")
        return self

    @property
    def model_label(self) -> str:
        return "fake" if self.engine == "fake" else f"{self.model}-{self.compute_type}"


def _flag(name: str, current: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in FALSE_VALUES:
        return False
    if raw in TRUE_VALUES:
        return True
    return current


def load_stt_config(path: Path | None = None) -> SttConfig:
    """Lee el TOML (si existe), aplica las variables de entorno y valida."""
    source = Path(path) if path is not None else CONFIG_PATH
    data: dict = {}
    if source.exists():
        with source.open("rb") as handle:
            data = dict(tomllib.load(handle).get("stt", {}))
    allowed = set(SttConfig.__dataclass_fields__)
    values = {key: value for key, value in data.items() if key in allowed}
    if "vocabulary" in values:
        values["vocabulary"] = tuple(str(term) for term in values["vocabulary"])
    if "corrections" in values:
        values["corrections"] = tuple(
            (str(key), str(value)) for key, value in dict(values["corrections"]).items()
        )
    try:
        config = SttConfig(**values)
    except TypeError as exc:
        raise SttConfigError(f"config/stt.toml inválido: {exc}") from exc
    engine = os.environ.get("MANUELITA_STT_ENGINE", "").strip().lower()
    model = os.environ.get("MANUELITA_STT_MODEL", "").strip()
    config = replace(
        config,
        enabled=_flag("MANUELITA_STT_ENABLED", config.enabled),
        warmup=_flag("MANUELITA_STT_WARMUP", config.warmup),
        engine=engine or config.engine,
        model=model or config.model,
    )
    return config.validate()
