"""WAV del dictado (spec 023, research R5): PCM 16 bits, mono, 16 kHz, siempre en memoria.

Nada de este módulo escribe en disco: el cuerpo de la petición se lee con ``io.BytesIO`` y el
audio vive como arreglo de ``numpy`` hasta que termina el reconocimiento (FR-018).
"""

from __future__ import annotations

import io
import wave

import numpy as np

SAMPLE_RATE = 16_000
SAMPLE_WIDTH = 2


class EmptyAudioError(ValueError):
    """Cuerpo vacío o sin muestras."""


class UnsupportedAudioError(ValueError):
    """No es WAV PCM16 mono a 16 kHz (o está truncado)."""


class AudioTooLargeError(ValueError):
    """Supera el tamaño o la duración máxima."""


def parse_wav16k(data: bytes, *, max_bytes: int, max_seconds: float) -> tuple[np.ndarray, int]:
    """Decodifica el WAV a ``float32`` en [-1, 1] y devuelve ``(muestras, audio_ms)``."""
    if not data:
        raise EmptyAudioError("El audio está vacío.")
    if len(data) > max_bytes:
        raise AudioTooLargeError("El audio supera el tamaño máximo.")
    try:
        with wave.open(io.BytesIO(data), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
            compression = handle.getcomptype()
            raw = handle.readframes(frames)
    except (wave.Error, EOFError, ValueError) as exc:
        raise UnsupportedAudioError("El audio no es WAV PCM de 16 bits.") from exc
    if compression != "NONE" or channels != 1 or width != SAMPLE_WIDTH or rate != SAMPLE_RATE:
        raise UnsupportedAudioError("El audio debe ser WAV PCM16 mono a 16 kHz.")
    if frames == 0:
        raise EmptyAudioError("El audio no tiene muestras.")
    if len(raw) < frames * SAMPLE_WIDTH:
        raise UnsupportedAudioError("El audio está incompleto.")
    if frames / SAMPLE_RATE > max_seconds:
        raise AudioTooLargeError("El audio supera la duración máxima.")
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return samples, round(frames * 1000 / SAMPLE_RATE)


def encode_wav16k(samples: np.ndarray) -> bytes:
    """Codifica ``float32`` (16 kHz, mono) como WAV PCM16; satura en ±1."""
    clipped = np.clip(np.asarray(samples, dtype=np.float32).reshape(-1), -1.0, 1.0)
    pcm = np.round(clipped * 32767.0).astype("<i2")
    pcm[clipped <= -1.0] = -32768
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()


def resample(samples: np.ndarray, rate: int, target: int = SAMPLE_RATE) -> np.ndarray:
    """Remuestreo lineal (para la batería de evaluación, que sintetiza con Phonon a 24 kHz)."""
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if rate == target or samples.size == 0:
        return samples
    count = max(1, round(samples.size * target / rate))
    positions = np.linspace(0, samples.size - 1, count)
    return np.interp(positions, np.arange(samples.size), samples).astype(np.float32)
