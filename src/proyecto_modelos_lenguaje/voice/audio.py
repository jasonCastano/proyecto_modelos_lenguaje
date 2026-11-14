"""Codificación WAV (PCM 16 bits mono) con la librería estándar (spec 016, research R6)."""

from __future__ import annotations

import io
import wave

import numpy as np


def duration_ms(samples: np.ndarray, sample_rate: int) -> float:
    return 1000.0 * len(samples) / float(sample_rate) if sample_rate else 0.0


def to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    """Convierte float32 en [-1, 1] (se recorta lo que exceda) a un WAV mono de 16 bits."""
    data = np.asarray(samples, dtype=np.float32).reshape(-1)
    pcm = (np.clip(data, -1.0, 1.0) * 32767.0).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()
