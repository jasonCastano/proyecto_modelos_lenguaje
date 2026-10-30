"""Local speech-to-text for YouTube videos without captions.

Audio is transcribed with faster-whisper and discarded; only the WebVTT
transcript and a provenance JSON are stored in the bronze layer.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Segment:
    start: float
    end: float
    text: str


def format_timestamp(seconds: float) -> str:
    """Format seconds as a WebVTT timestamp (HH:MM:SS.mmm)."""
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def build_vtt(segments: Iterable[Segment], *, note: str | None = None) -> str:
    lines = ["WEBVTT"]
    if note:
        lines.extend(["", f"NOTE {note}"])
    for segment in segments:
        text = " ".join(segment.text.split())
        if not text:
            continue
        lines.extend(
            [
                "",
                f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}",
                text,
            ]
        )
    return "\n".join(lines) + "\n"


_NOISE_PATTERNS = (
    "amara.org",
    "subtítulos por la comunidad",
    "subtitulos por la comunidad",
    "subtítulos realizados por",
    "subtitulos realizados por",
    "gracias por ver el video",
    "thanks for watching",
    "subscribe to my channel",
)


def is_noise(text: str) -> bool:
    """Detect Whisper boilerplate/hallucinations that carry no company information."""
    normalized = " ".join(text.lower().split())
    if not normalized:
        return True
    return any(pattern in normalized for pattern in _NOISE_PATTERNS)


def transcribe_audio(
    audio_path: Path,
    *,
    model: str = "small",
    language: str = "es",
    device: str = "cpu",
    compute_type: str = "int8",
    beam_size: int = 5,
    vad_filter: bool = True,
) -> tuple[list[Segment], dict[str, Any]]:
    """Transcribe an audio file, returning timestamped segments and model info."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "faster-whisper is required: uv run --extra asr python scripts/transcribe_youtube.py"
        ) from exc
    whisper = WhisperModel(model, device=device, compute_type=compute_type)
    raw_segments, info = whisper.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=vad_filter,
        condition_on_previous_text=False,
    )
    segments = [
        Segment(start=float(item.start), end=float(item.end), text=item.text)
        for item in raw_segments
        if not is_noise(item.text)
    ]
    if not segments:
        raise RuntimeError("no speech detected (only silence or boilerplate)")
    details = {
        "model": model,
        "language": getattr(info, "language", language),
        "language_probability": (
            round(float(info.language_probability), 4)
            if getattr(info, "language_probability", None) is not None
            else None
        ),
        "duration_seconds": (
            round(float(info.duration), 3) if getattr(info, "duration", None) else None
        ),
        "device": device,
        "compute_type": compute_type,
    }
    return segments, details


def provenance_payload(
    *,
    video_url: str,
    title: str | None,
    published_at: str | None,
    details: dict[str, Any],
    segments: int,
) -> str:
    payload = {
        "schema_version": "1.0",
        "source": "youtube",
        "type": "transcript_provenance",
        "video_url": video_url,
        "title": title,
        "published_at": published_at,
        "method": "automatic_speech_recognition",
        "generator": "faster-whisper",
        "segments": segments,
        **details,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
