"""Unit tests for YouTube metadata handling (no network)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from proyecto_modelos_lenguaje.config import load_config
from proyecto_modelos_lenguaje.fetchers.youtube import (
    _flatten_entries,
    metadata_payload,
    subtitle_language,
)
from proyecto_modelos_lenguaje.sources.youtube import YoutubeSource


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


def test_flatten_channel_entries_handles_videos_and_shorts() -> None:
    info = {
        "entries": [
            {
                "title": "Videos",
                "entries": [
                    {"id": "vid1", "title": "Video 1", "_type": "url"},
                    {"id": "vid2", "title": "Video 2", "_type": "url"},
                ],
            },
            {
                "title": "Shorts",
                "entries": [
                    {"id": "short1", "title": "Short 1", "_type": "url"},
                ],
            },
        ]
    }
    entries = _flatten_entries(info)
    assert [entry["id"] for entry in entries] == ["vid1", "vid2", "short1"]


def test_direct_video_seeds_are_not_expanded() -> None:
    config = load_config("config/youtube_backfill.toml")
    source = config.sources[0]
    candidates = asyncio.run(YoutubeSource(source=source).discover(None))  # type: ignore[arg-type]
    assert [candidate.url for candidate in candidates] == [
        "https://www.youtube.com/watch?v=XpPz6nM0Hb8",
        "https://www.youtube.com/watch?v=o5HHOA6IWps",
        "https://www.youtube.com/watch?v=j7YQakSnK2g",
        "https://www.youtube.com/watch?v=asEruPVCaM4",
        "https://www.youtube.com/watch?v=PwjzJFavJ8U",
        "https://www.youtube.com/shorts/9TrHNkHD7qU",
    ]
