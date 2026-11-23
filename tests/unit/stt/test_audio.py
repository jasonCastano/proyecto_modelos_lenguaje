"""WAV del dictado (spec 023, research R5 y contracts/stt-api.md §2)."""

from __future__ import annotations

import io
import wave

import numpy as np
import pytest

from proyecto_modelos_lenguaje.stt.audio import (
    SAMPLE_RATE,
    AudioTooLargeError,
    EmptyAudioError,
    UnsupportedAudioError,
    encode_wav16k,
    parse_wav16k,
)

LIMITS = {"max_bytes": 2_097_152, "max_seconds": 60.0}


def _wav(
    *, channels: int = 1, width: int = 2, rate: int = SAMPLE_RATE, frames: int = 1600
) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(
            b"\x01\x00" * channels * frames if width == 2 else b"\x01" * width * channels * frames
        )
    return buffer.getvalue()


def test_round_trip_returns_float32_in_range_and_duration() -> None:
    tone = 0.5 * np.sin(np.linspace(0, 2 * np.pi * 440, SAMPLE_RATE, dtype=np.float32))
    samples, audio_ms = parse_wav16k(encode_wav16k(tone), **LIMITS)
    assert samples.dtype == np.float32 and samples.shape == (SAMPLE_RATE,)
    assert float(np.max(np.abs(samples))) <= 1.0
    assert np.allclose(samples, tone, atol=1e-3)
    assert audio_ms == 1000


def test_encoder_clips_to_unit_range() -> None:
    samples, _ = parse_wav16k(encode_wav16k(np.array([2.0, -3.0, 0.0], np.float32)), **LIMITS)
    assert samples[0] == pytest.approx(32767 / 32768, abs=1e-4)
    assert samples[1] == pytest.approx(-1.0)


@pytest.mark.parametrize(
    "data",
    [
        _wav(channels=2),
        _wav(rate=44_100),
        _wav(width=1),
        _wav(width=3),
        b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb" * 400,  # MP3
        b"basura que no es audio" * 10,
    ],
)
def test_unsupported_formats(data: bytes) -> None:
    with pytest.raises(UnsupportedAudioError):
        parse_wav16k(data, **LIMITS)


def test_float_wav_is_unsupported() -> None:
    data = bytearray(_wav())
    data[20:22] = (3).to_bytes(2, "little")  # WAVE_FORMAT_IEEE_FLOAT
    with pytest.raises(UnsupportedAudioError):
        parse_wav16k(bytes(data), **LIMITS)


def test_truncated_data_is_unsupported() -> None:
    data = _wav(frames=16_000)
    with pytest.raises(UnsupportedAudioError):
        parse_wav16k(data[: len(data) // 2], **LIMITS)


@pytest.mark.parametrize("data", [b"", _wav(frames=0)])
def test_empty_audio(data: bytes) -> None:
    with pytest.raises(EmptyAudioError):
        parse_wav16k(data, **LIMITS)


def test_too_many_bytes() -> None:
    with pytest.raises(AudioTooLargeError):
        parse_wav16k(_wav(frames=16_000), max_bytes=1000, max_seconds=60)


def test_too_long() -> None:
    with pytest.raises(AudioTooLargeError):
        parse_wav16k(_wav(frames=SAMPLE_RATE * 3), max_bytes=10_000_000, max_seconds=2)
