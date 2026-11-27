"""Motor de voz (spec 016, research R1 y R5).

- ``PhononSynthesizer`` envuelve el runtime local de Phonon (paquete ``ptts``, sin PyTorch).
- ``FakeSynthesizer`` es determinista y sin red: se usa en pruebas y en demos sin modelo.
- ``VoiceService`` guarda el estado (``disabled|loading|ready|unavailable``), carga el motor
  de forma perezosa con un ``Lock`` y serializa la síntesis.
  Una falla de voz nunca debe romper el chat.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np

from .audio import duration_ms
from .config import LICENSE, VoiceConfig, VoiceConfigError, load_voice_config

logger = logging.getLogger(__name__)

VoiceState = Literal["disabled", "loading", "ready", "unavailable"]
FAKE_SAMPLE_RATE = 24_000


@dataclass(frozen=True)
class VoiceInfo:
    name: str
    voice_id: str
    accent: str  # "ES" (España) | "MX" (México)
    gender: Literal["female", "male"]


# Catálogo en español de gradium/phonon-voices (research R4), verificado con
# ``ptts.catalog_voices()`` el 2026-11-14. El catálogo no trae el género; sale de las fichas.
SPANISH_VOICES: tuple[VoiceInfo, ...] = (
    VoiceInfo("Noa", "b6FvJAiokjdqIti4", "ES", "female"),
    VoiceInfo("Lucía-Sol", "3p0eIGbkmny71GlA", "ES", "female"),
    VoiceInfo("Candela", "c9wqBDmQiBie5q6Y", "ES", "female"),
    VoiceInfo("Celia", "rmLBOdHrfkFym9MM", "ES", "female"),
    VoiceInfo("Alba", "u2UscyAnHilpiwmf", "ES", "female"),
    VoiceInfo("Alicia", "4701YgRXjkBcg6sL", "ES", "female"),
    VoiceInfo("Nerea", "EQcQFGkYfMn5YJgx", "ES", "female"),
    VoiceInfo("Rebeca", "Sx8m6WdXBG06zwZT", "MX", "female"),
    VoiceInfo("Regina", "s58clrg2fe0MO7Y-", "MX", "female"),
    VoiceInfo("Danae", "evfxKSxpDIhmsNoq", "MX", "female"),
    VoiceInfo("Azucena", "KJpIQlbYrZPA4aLq", "MX", "female"),
    VoiceInfo("Jimena", "qG5BXOJYrKEnXLIX", "MX", "female"),
    VoiceInfo("Ximena", "VDwnGxAo68C8U8vC", "MX", "female"),
    VoiceInfo("Marcos", "jvPx8j8zLGQ3utZz", "ES", "male"),
    VoiceInfo("Borja", "tIjCgP8v3RY8UpgM", "ES", "male"),
    VoiceInfo("Iker", "t-_TS1e-0GzDAX02", "ES", "male"),
    VoiceInfo("Nuno", "fghJGlv90qu8OJ36", "ES", "male"),
    VoiceInfo("Izan", "Ejb29qHnSOK0cIHY", "ES", "male"),
    VoiceInfo("Guillermo", "FaLVVqpFQcDOtq45", "ES", "male"),
    VoiceInfo("Lalo", "F05gqkzX7WhKVpSL", "MX", "male"),
    VoiceInfo("Aldo", "ax7dW1XB0eiMfHgO", "MX", "male"),
    VoiceInfo("Yael", "ALczEazoF4n6PmGl", "MX", "male"),
    VoiceInfo("Ulises", "G5HLUsQd659UtRe7", "MX", "male"),
    VoiceInfo("Leonel", "BkuASiOJRrJEB5qA", "MX", "male"),
    VoiceInfo("Nico", "PwgPEaweQILZdGc4", "MX", "male"),
)
# Spec 028 (research R4): candidatas en inglés del catálogo de Phonon (modelo phonon-31m-en).
ENGLISH_VOICES = (
    VoiceInfo("Harper", "4SZHfMpw-p46Ywgs", "US", "female"),
    VoiceInfo("Everly", "vjFyp2BcCyTlUmYb", "US", "female"),
    VoiceInfo("Juniper", "NIWIOv5vTi5eRMj8", "US", "female"),
    VoiceInfo("Hadley", "bXwrkHhURL1VFJdG", "US", "female"),
)
VOICES_BY_LANGUAGE = {"es": SPANISH_VOICES, "en": ENGLISH_VOICES}


class VoiceUnavailableError(RuntimeError):
    """El motor no está disponible (deshabilitado, sin modelo o sin soporte de CPU)."""


class UnknownVoiceError(ValueError):
    """La voz pedida no está en el catálogo."""


class Synthesizer(Protocol):
    engine: str
    sample_rate: int

    def synth(self, text: str, voice: str) -> np.ndarray: ...

    def voices(self) -> list[VoiceInfo]: ...


def find_voice(voices: list[VoiceInfo], wanted: str) -> VoiceInfo | None:
    key = wanted.strip().casefold()
    for info in voices:
        if key in {info.name.casefold(), info.voice_id.casefold()} and key:
            return info
    return None


class FakeSynthesizer:
    """Sintetizador determinista: un tono suave de ~60 ms por carácter (sin red ni modelo)."""

    engine = "fake"

    def __init__(
        self,
        sample_rate: int = FAKE_SAMPLE_RATE,
        ms_per_char: float = 60.0,
        language: str = "es",
    ) -> None:
        self.sample_rate = sample_rate
        self.ms_per_char = ms_per_char
        self.language = language
        self.calls: list[tuple[str, str]] = []

    def synth(self, text: str, voice: str) -> np.ndarray:
        self.calls.append((text, voice))
        frames = max(1, int(self.sample_rate * self.ms_per_char * len(text) / 1000.0))
        t = np.arange(frames, dtype=np.float32) / self.sample_rate
        return (0.05 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)

    def voices(self) -> list[VoiceInfo]:
        return list(VOICES_BY_LANGUAGE.get(self.language, SPANISH_VOICES))


def _friendly_load_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if isinstance(exc, ImportError):
        return "El motor de voz Phonon (paquete ptts) no está instalado; ejecuta uv sync."
    if any(token in text for token in ("401", "403", "gated", "unauthorized", "token", "access")):
        return (
            "No se pudo descargar el modelo de voz: falta HF_TOKEN o no se aceptaron las "
            "condiciones de gradium/phonon-40m-es en Hugging Face."
        )
    if any(token in text for token in ("connection", "network", "resolve", "timeout", "offline")):
        return "No se pudo descargar el modelo de voz: sin conexión a Hugging Face."
    if any(token in text for token in ("illegal instruction", "avx", "cpu")):
        return "La CPU de este equipo no es compatible con el motor de voz (requiere AVX2)."
    return "No se pudo cargar el modelo de voz Phonon."


class PhononSynthesizer:
    """Adaptador del runtime de Phonon (``ptts``). Importa y carga el modelo al construirse."""

    engine = "phonon"

    def __init__(self, config: VoiceConfig) -> None:
        import ptts  # importación perezosa: el resto del proyecto no depende de ella

        self._language = config.language.lower()
        # Firma verificada en ptts 0.7.1: TTS(model, device, quant, voice, ..., *, lang, ...)
        self._tts = ptts.TTS(config.model, quant=config.quant, lang=config.language)
        self.sample_rate = int(self._tts.sample_rate)
        self._catalog = self._load_catalog()

    def _load_catalog(self) -> list[VoiceInfo]:
        """Voces en español del catálogo oficial; si no se puede leer, el catálogo documentado."""
        try:
            import ptts

            raw = ptts.catalog_voices()
        except Exception:
            return list(VOICES_BY_LANGUAGE.get(self._language, SPANISH_VOICES))
        documented = VOICES_BY_LANGUAGE.get(self._language, SPANISH_VOICES)
        known = {info.voice_id: info for info in documented}
        catalog: list[VoiceInfo] = []
        for item in raw:
            if not str(item.get("language") or "").lower().startswith(self._language):
                continue
            voice_id = str(item.get("voice_id") or "")
            info = known.get(voice_id)
            catalog.append(
                info or VoiceInfo(str(item.get("name") or voice_id), voice_id, "", "male")
            )
        return catalog or list(documented)

    def synth(self, text: str, voice: str) -> np.ndarray:
        samples = self._tts.synth(text, voice=voice)
        return np.asarray(samples, dtype=np.float32).reshape(-1)

    def voices(self) -> list[VoiceInfo]:
        return list(self._catalog)


@dataclass(frozen=True)
class VoiceStatusData:
    available: bool
    state: VoiceState
    engine: str
    model: str
    voice: str
    language: str
    sample_rate: int | None
    license: str
    detail: str | None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class SynthResult:
    samples: np.ndarray
    sample_rate: int
    voice: str
    synth_ms: float
    audio_ms: float


class VoiceService:
    """Estado y acceso serializado al motor de voz."""

    def __init__(
        self, config: VoiceConfig | None = None, *, synthesizer: Synthesizer | None = None
    ):
        self._lock = threading.Lock()
        self._synth: Synthesizer | None = synthesizer
        self._detail: str | None = None
        self._warmup: threading.Thread | None = None
        try:
            self.config = config or load_voice_config()
        except VoiceConfigError as exc:
            self.config = VoiceConfig()
            self._state: VoiceState = "unavailable"
            self._detail = str(exc)
            return
        if not self.config.enabled:
            self._state = "disabled"
            self._detail = "Voz desactivada por configuración."
        elif synthesizer is not None:
            self._state = "ready"
        else:
            self._state = "loading"

    # -- estado -------------------------------------------------------------------------------
    @property
    def state(self) -> VoiceState:
        return self._state

    def status(self) -> VoiceStatusData:
        ready = self._state == "ready" and self._synth is not None
        return VoiceStatusData(
            available=self._state in {"ready", "loading"},
            state=self._state,
            engine=self.config.engine,
            model=self.config.model if self.config.engine == "phonon" else "fake",
            voice=self.config.voice,
            language=self.config.language,
            sample_rate=self._synth.sample_rate if ready and self._synth else None,
            license=LICENSE,
            detail=self._detail,
        )

    # -- carga --------------------------------------------------------------------------------
    def _build(self) -> Synthesizer:
        if self.config.engine == "fake":
            return FakeSynthesizer(language=self.config.language)
        return PhononSynthesizer(self.config)

    def ensure_loaded(self) -> Synthesizer:
        """Carga el motor si hace falta; lanza ``VoiceUnavailableError`` si no se puede."""
        if self._state in {"disabled", "unavailable"}:
            raise VoiceUnavailableError(self._detail or "La voz no está disponible.")
        if self._synth is not None:
            return self._synth
        with self._lock:
            if self._synth is None and self._state == "loading":
                try:
                    self._synth = self._build()
                    self._state = "ready"
                    self._detail = None
                except BaseException as exc:  # incluye errores nativos del runtime
                    if isinstance(exc, KeyboardInterrupt | SystemExit):
                        raise
                    logger.warning("No se pudo cargar el motor de voz: %s", type(exc).__name__)
                    self._state = "unavailable"
                    self._detail = _friendly_load_error(exc)
        if self._synth is None:
            raise VoiceUnavailableError(self._detail or "La voz no está disponible.")
        return self._synth

    def warmup_async(self) -> None:
        """Precarga el modelo en un hilo para que la primera oración no pague la carga."""
        if self._state != "loading" or self._warmup is not None:
            return

        def run() -> None:
            # Carga y una síntesis corta: la primera llamada del motor es ~2× más lenta (R10).
            with contextlib.suppress(Exception):
                self.ensure_loaded()
                self.synthesize("Hola.")

        self._warmup = threading.Thread(target=run, name="voice-warmup", daemon=True)
        self._warmup.start()

    # -- síntesis -----------------------------------------------------------------------------
    def voices(self) -> list[VoiceInfo]:
        return self.ensure_loaded().voices()

    def resolve_voice(self, voice: str | None) -> str:
        wanted = (voice or self.config.voice).strip()
        info = find_voice(self.voices(), wanted)
        if info is None:
            raise UnknownVoiceError(f"La voz {wanted!r} no está en el catálogo.")
        return info.name

    def synthesize(self, text: str, voice: str | None = None) -> SynthResult:
        synth = self.ensure_loaded()
        name = self.resolve_voice(voice)
        started = time.perf_counter()
        with self._lock:
            samples = synth.synth(text, name)
        elapsed = (time.perf_counter() - started) * 1000.0
        return SynthResult(
            samples=samples,
            sample_rate=synth.sample_rate,
            voice=name,
            synth_ms=round(elapsed, 1),
            audio_ms=round(duration_ms(samples, synth.sample_rate), 1),
        )


_SERVICE: VoiceService | None = None
_SERVICES_BY_LANGUAGE: dict[str, VoiceService] = {}
_SERVICE_LOCK = threading.Lock()


def get_voice_service(language: str | None = None) -> VoiceService:
    """Servicio de voz del idioma principal o, con ``language`` (spec 028), de otro idioma."""
    global _SERVICE
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = VoiceService()
        if language is None or language == _SERVICE.config.language:
            return _SERVICE
        service = _SERVICES_BY_LANGUAGE.get(language)
        if service is None:
            try:
                config = _SERVICE.config.for_language(language)
            except VoiceConfigError as exc:
                raise VoiceUnavailableError(str(exc)) from exc
            service = VoiceService(config)
            _SERVICES_BY_LANGUAGE[language] = service
        return service


def reset_voice_service(service: VoiceService | None = None) -> None:
    """Para pruebas: descarta los singletons (o reemplaza el principal)."""
    global _SERVICE
    with _SERVICE_LOCK:
        _SERVICE = service
        _SERVICES_BY_LANGUAGE.clear()
