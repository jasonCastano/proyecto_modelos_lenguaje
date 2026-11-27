"""Motor del dictado (spec 023, research R1, R2, R6, R7 y R13).

- ``WhisperTranscriber`` envuelve faster-whisper (CTranslate2, CPU) con Silero VAD y el vocabulario
  propio como prompt inicial.
- ``FakeTranscriber`` es determinista y sin red: vacío con silencio, una frase fija con voz.
- ``SttService`` guarda el estado (``disabled|loading|ready|unavailable``), carga el modelo una vez
  con un ``Lock`` y limita las transcripciones simultáneas con un semáforo. El dictado es opcional:
  una falla nunca rompe el chat ni la voz de salida.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import numpy as np

from .config import (
    AUTO_LANGUAGE,
    LICENSE,
    PRIVACY,
    SUPPORTED_LANGUAGES,
    SttConfig,
    SttConfigError,
    load_stt_config,
)
from .text import apply_corrections, clip_message, initial_prompt, is_hallucination

logger = logging.getLogger(__name__)

SttState = Literal["disabled", "loading", "ready", "unavailable"]
SILENCE_RMS = 0.01


class SttUnavailableError(RuntimeError):
    """El dictado no está disponible (deshabilitado, sin modelo o con error de carga)."""


class SttBusyError(RuntimeError):
    """Se agotó la espera por un turno de transcripción."""


@dataclass(frozen=True)
class Segment:
    text: str
    no_speech_prob: float = 0.0


class Transcriber(Protocol):
    model_label: str

    def transcribe(self, samples: np.ndarray) -> list[Segment]: ...


class FakeTranscriber:
    """Sin red ni modelo: vacío si el audio es silencio; si no, ``text``."""

    model_label = "fake"

    def __init__(self, text: str = "¿Qué produce Manuelita?") -> None:
        self.text = text

    def transcribe(self, samples: np.ndarray) -> list[Segment]:
        if samples.size == 0 or float(np.sqrt(np.mean(np.square(samples)))) < SILENCE_RMS:
            return []
        return [Segment(self.text)]

    def transcribe_with_language(
        self, samples: np.ndarray, language: str | None
    ) -> tuple[list[Segment], str]:
        """Spec 028: con ``language=None`` «detecta» inglés si el texto fijo parece inglés."""
        detected = language or ("en" if _looks_english(self.text) else "es")
        return self.transcribe(samples), detected


def _looks_english(text: str) -> bool:
    words = set(text.lower().replace("?", " ").replace("¿", " ").split())
    return bool(words & {"what", "does", "the", "how", "is", "are", "who", "where", "when"})


def _friendly_load_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if isinstance(exc, ImportError):
        return "El dictado (faster-whisper) no está instalado; ejecuta uv sync."
    if any(token in text for token in ("connection", "network", "resolve", "timeout", "offline")):
        return "No se pudo descargar el modelo de dictado: sin conexión a Hugging Face."
    if any(token in text for token in ("illegal instruction", "avx", "cpu")):
        return "La CPU de este equipo no es compatible con el modelo de dictado."
    if any(token in text for token in ("memory", "alloc")):
        return "No hay memoria suficiente para cargar el modelo de dictado."
    return "No se pudo cargar el modelo de dictado."


class WhisperTranscriber:
    """Adaptador de faster-whisper. Importa y carga el modelo al construirse."""

    def __init__(self, config: SttConfig, *, model_factory: Callable[..., Any] | None = None):
        if model_factory is None:
            from faster_whisper import WhisperModel  # importación perezosa

            model_factory = WhisperModel
        self._config = config
        self._prompt = initial_prompt(config.vocabulary) or None
        self._model = model_factory(
            config.model,
            device="cpu",
            compute_type=config.compute_type,
            cpu_threads=config.cpu_threads,
        )
        self.model_label = config.model_label

    def transcribe(self, samples: np.ndarray) -> list[Segment]:
        language = None if self._config.language == AUTO_LANGUAGE else self._config.language
        return self.transcribe_with_language(samples, language)[0]

    def transcribe_with_language(
        self, samples: np.ndarray, language: str | None
    ) -> tuple[list[Segment], str]:
        """``language=None`` deja que Whisper detecte el idioma (spec 028, research R5)."""
        segments, info = self._model.transcribe(
            samples,
            language=language,
            beam_size=self._config.beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=self._prompt,
        )
        kept = [
            Segment(str(item.text).strip(), float(getattr(item, "no_speech_prob", 0.0) or 0.0))
            for item in segments
        ]
        return kept, str(getattr(info, "language", None) or language or "es")


@dataclass(frozen=True)
class SttStatusData:
    available: bool
    state: SttState
    engine: str
    model: str
    language: str
    detail: str | None
    max_seconds: float
    silence_ms: int
    min_speech_ms: int
    handsfree_idle_seconds: int
    privacy: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class Transcription:
    text: str
    empty: bool
    truncated: bool
    language: str
    audio_ms: int
    stt_ms: int
    model: str
    language_fallback: bool = False  # spec 028: idioma distinto de es/en → se trata como «es»

    def to_dict(self) -> dict[str, Any]:
        """Contrato de ``/api/stt`` (spec 023): sin el campo interno del canal."""
        data = dict(self.__dict__)
        data.pop("language_fallback", None)
        return data


class SttService:
    """Estado, carga perezosa y acceso acotado al reconocedor."""

    def __init__(self, config: SttConfig | None = None, *, transcriber: Transcriber | None = None):
        self._load_lock = threading.Lock()
        self._transcriber: Transcriber | None = transcriber
        self._detail: str | None = None
        self._warmup: threading.Thread | None = None
        try:
            self.config = config.validate() if config is not None else load_stt_config()
        except SttConfigError as exc:
            self.config = SttConfig()
            self._state: SttState = "unavailable"
            self._detail = str(exc)
            self._slots = threading.BoundedSemaphore(1)
            return
        self._slots = threading.BoundedSemaphore(self.config.max_concurrent)
        if not self.config.enabled:
            self._state = "disabled"
            self._detail = "Dictado desactivado por configuración."
        elif transcriber is not None:
            self._state = "ready"
        else:
            self._state = "loading"

    # -- estado -------------------------------------------------------------------------------
    @property
    def state(self) -> SttState:
        return self._state

    def status(self) -> SttStatusData:
        return SttStatusData(
            available=self._state in {"ready", "loading"},
            state=self._state,
            engine=self.config.engine,
            model=self.config.model_label,
            language=self.config.language,
            detail=self._detail,
            max_seconds=self.config.max_seconds,
            silence_ms=self.config.silence_ms,
            min_speech_ms=self.config.min_speech_ms,
            handsfree_idle_seconds=self.config.handsfree_idle_seconds,
            privacy=PRIVACY,
        )

    @property
    def license(self) -> str:
        return LICENSE

    # -- carga --------------------------------------------------------------------------------
    def _build(self) -> Transcriber:
        if self.config.engine == "fake":
            return FakeTranscriber()
        return WhisperTranscriber(self.config)

    def ensure_loaded(self) -> Transcriber:
        """Carga el modelo si hace falta; lanza ``SttUnavailableError`` si no se puede."""
        if self._state in {"disabled", "unavailable"}:
            raise SttUnavailableError(self._detail or "El dictado no está disponible.")
        if self._transcriber is not None:
            return self._transcriber
        with self._load_lock:
            if self._transcriber is None and self._state == "loading":
                try:
                    self._transcriber = self._build()
                    self._state = "ready"
                    self._detail = None
                except BaseException as exc:  # incluye errores nativos de CTranslate2
                    if isinstance(exc, KeyboardInterrupt | SystemExit):
                        raise
                    logger.warning("No se pudo cargar el dictado: %s", type(exc).__name__)
                    self._state = "unavailable"
                    self._detail = _friendly_load_error(exc)
        if self._transcriber is None:
            raise SttUnavailableError(self._detail or "El dictado no está disponible.")
        return self._transcriber

    def warmup_async(self) -> None:
        """Carga el modelo en un hilo y transcribe un silencio corto (la primera vez es lenta)."""
        if self._state != "loading" or self._warmup is not None:
            return

        def run() -> None:
            with contextlib.suppress(Exception):
                self.ensure_loaded().transcribe(np.zeros(16_000, dtype=np.float32))

        self._warmup = threading.Thread(target=run, name="stt-warmup", daemon=True)
        self._warmup.start()

    def join_warmup(self, timeout: float | None = None) -> None:
        if self._warmup is not None:
            self._warmup.join(timeout)

    # -- reconocimiento -----------------------------------------------------------------------
    def transcribe(
        self, samples: np.ndarray, audio_ms: int, *, language: str | None = None
    ) -> Transcription:
        """``language`` (spec 028) reemplaza el de la configuración; «auto» detecta es/en."""
        transcriber = self.ensure_loaded()
        requested = language or self.config.language
        if not self._slots.acquire(timeout=self.config.queue_timeout_seconds):
            raise SttBusyError("El dictado está ocupado.")
        try:
            started = time.perf_counter()
            detect = getattr(transcriber, "transcribe_with_language", None)
            if detect is not None:
                whisper_language = None if requested == AUTO_LANGUAGE else requested
                segments, detected = detect(samples, whisper_language)
            else:
                segments, detected = transcriber.transcribe(samples), requested
            elapsed = round((time.perf_counter() - started) * 1000)
        finally:
            self._slots.release()
        fallback = False
        if requested == AUTO_LANGUAGE:
            if detected not in SUPPORTED_LANGUAGES:
                detected, fallback = SUPPORTED_LANGUAGES[0], True
        else:
            detected = requested
        kept = [
            segment.text.strip()
            for segment in segments
            if segment.no_speech_prob <= self.config.no_speech_threshold
            and not is_hallucination(segment.text)
        ]
        text = apply_corrections(" ".join(part for part in kept if part), self.config.corrections)
        text, truncated = clip_message(text)
        return Transcription(
            text=text,
            empty=not text,
            truncated=truncated,
            language=detected,
            audio_ms=int(audio_ms),
            stt_ms=int(elapsed),
            model=getattr(transcriber, "model_label", self.config.model_label),
            language_fallback=fallback,
        )


_SERVICE: SttService | None = None
_SERVICE_LOCK = threading.Lock()


def get_stt_service() -> SttService:
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = SttService()
        return _SERVICE


def reset_stt_service(service: SttService | None = None) -> None:
    """Para pruebas: descarta el singleton (o lo reemplaza)."""
    global _SERVICE
    with _SERVICE_LOCK:
        _SERVICE = service
