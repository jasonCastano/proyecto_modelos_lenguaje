"""Unit tests for YouTube metadata handling (no network)."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.fetchers.youtube import metadata_payload, subtitle_language


def test_metadata_payload_keeps_relevant_fields() -> None:
    info = {
        "id": "abc123",
        "title": "Manuelita Corporativo 2024",
        "channel": "Manuelita",
        "upload_date": "20240102",
        "duration": 90,
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
        "language": "es",
        "formats": [{"url": "https://media.example/video.mp4"}],
        "requested_downloads": [{"filepath": "video.mp4"}],
    }
    payload = metadata_payload(info)
    assert payload["id"] == "abc123"
    assert payload["upload_date"] == "20240102"
    assert "formats" not in payload
    assert "requested_downloads" not in payload


def test_subtitle_language_parsing() -> None:
    assert subtitle_language(Path("abc123.es.vtt")) == "es"
    assert subtitle_language(Path("abc123.en-US.vtt")) == "en"
    assert subtitle_language(Path("abc123.vtt")) == "und"
