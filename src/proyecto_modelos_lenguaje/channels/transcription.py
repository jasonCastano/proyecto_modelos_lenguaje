"""Transcripción de notas de voz del canal (spec 028, research R5, channel-api-v2 §2).

La usan el endpoint ``POST /api/channels/transcriptions`` (con el dictado de la spec 023 ya cargado)
y, como respaldo, el CLI que ejecuta OpenClaw. Todo en memoria: el audio nunca se escribe en disco.
"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..stt.audio import (
    SAMPLE_RATE,
    AudioTooLargeError,
    EmptyAudioError,
    UnsupportedAudioError,
    parse_wav16k,
)
from ..stt.config import AUTO_LANGUAGE

MAX_BYTES = 16 * 1024 * 1024
MAX_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class ChannelTranscription:
    text: str
    language: str
    audio_ms: int
    latency_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "audio_ms": self.audio_ms,
            "latency_ms": self.latency_ms,
        }


def decode_audio(data: bytes, *, max_seconds: float = MAX_SECONDS) -> tuple[np.ndarray, int]:
    """Ogg/Opus, MP3, M4A o WAV → ``float32`` mono a 16 kHz y su duración en ms."""
    if not data:
        raise EmptyAudioError("El audio está vacío.")
    if len(data) > MAX_BYTES:
        raise AudioTooLargeError("El audio supera el tamaño máximo.")
    try:
        return parse_wav16k(data, max_bytes=MAX_BYTES, max_seconds=max_seconds)
    except UnsupportedAudioError:
        pass  # no es WAV 16 kHz: se decodifica con PyAV (lo trae faster-whisper)
    try:
        samples = _decode_with_pyav(data)
    except Exception as exc:  # PyAV lanza errores propios según el contenedor
        raise UnsupportedAudioError("No se pudo leer el audio.") from exc
    if samples.size == 0:
        raise EmptyAudioError("El audio no tiene muestras.")
    audio_ms = round(samples.size * 1000 / SAMPLE_RATE)
    if audio_ms > max_seconds * 1000:
        raise AudioTooLargeError("El audio supera la duración máxima.")
    return samples, audio_ms


def _decode_with_pyav(data: bytes) -> np.ndarray:
    """Decodifica con PyAV y remuestrea a mono 16 kHz ``float32``.

    No se usa ``faster_whisper.decode_audio``: con PyAV 19 falla (``metadata_errors`` ya no existe).
    """
    import av

    resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
    chunks: list[np.ndarray] = []
    with av.open(io.BytesIO(data), mode="r") as container:
        stream = next(s for s in container.streams if s.type == "audio")
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)


def transcribe_bytes(data: bytes, service: Any | None = None) -> ChannelTranscription:
    """Transcribe con detección de idioma (es/en). Sin habla → ``text`` vacío."""
    if service is None:
        from ..stt.engine import get_stt_service

        service = get_stt_service()
    started = time.perf_counter()
    samples, audio_ms = decode_audio(data)
    result = service.transcribe(samples, audio_ms, language=AUTO_LANGUAGE)
    latency = round((time.perf_counter() - started) * 1000)
    return ChannelTranscription(result.text, result.language, audio_ms, latency)
