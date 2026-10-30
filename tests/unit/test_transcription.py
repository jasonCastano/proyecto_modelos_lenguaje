"""Unit tests for WebVTT generation used by ASR transcripts."""

from __future__ import annotations

from proyecto_modelos_lenguaje.transcription import Segment, build_vtt, format_timestamp


def test_format_timestamp_pads_hours_minutes_and_millis() -> None:
    assert format_timestamp(0) == "00:00:00.000"
    assert format_timestamp(5.64) == "00:00:05.640"
    assert format_timestamp(3661.005) == "01:01:01.005"


def test_build_vtt_includes_note_and_cues() -> None:
    vtt = build_vtt(
        [Segment(1.0, 2.5, "Cada día empieza"), Segment(2.5, 4.0, "  con   esperanza ")],
        note="Transcripción automática",
    )
    assert vtt.startswith("WEBVTT\n\nNOTE Transcripción automática")
    assert "00:00:01.000 --> 00:00:02.500" in vtt
    assert "Cada día empieza" in vtt
    assert "con esperanza" in vtt
    assert vtt.endswith("\n")


def test_build_vtt_skips_empty_segments() -> None:
    vtt = build_vtt([Segment(0, 1, "   "), Segment(1, 2, "texto")])
    assert vtt.count("-->") == 1
