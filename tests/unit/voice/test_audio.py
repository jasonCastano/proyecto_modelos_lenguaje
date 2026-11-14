"""WAV PCM 16 bits mono (spec 016, research R6)."""

from __future__ import annotations

import io
import wave

import numpy as np

from proyecto_modelos_lenguaje.voice.audio import duration_ms, to_wav_bytes


def test_wav_header_and_format() -> None:
    # Arrange
    samples = np.linspace(-0.5, 0.5, 2400, dtype=np.float32)
    # Act
    data = to_wav_bytes(samples, 24_000)
    # Assert
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    with wave.open(io.BytesIO(data)) as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 24_000
        assert handle.getnframes() == 2400


def test_out_of_range_samples_are_clipped() -> None:
    data = to_wav_bytes(np.array([2.0, -3.0, 0.0], dtype=np.float32), 16_000)
    with wave.open(io.BytesIO(data)) as handle:
        frames = np.frombuffer(handle.readframes(3), dtype="<i2")
    assert frames.tolist() == [32767, -32767, 0]


def test_duration_ms() -> None:
    assert duration_ms(np.zeros(12_000, dtype=np.float32), 24_000) == 500.0
    assert duration_ms(np.zeros(10, dtype=np.float32), 0) == 0.0
