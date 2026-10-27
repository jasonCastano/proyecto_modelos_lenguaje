"""YouTube metadata and subtitle acquisition through yt-dlp (no media download)."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..extractors.metadata import detect_media_type


@dataclass(frozen=True, slots=True)
class YoutubePart:
    url: str
    media_type: str
    data: bytes
    role: str
    title: str | None
    published_at: str | None
    language: str


@dataclass(slots=True)
class YoutubeResult:
    parts: list[YoutubePart] = field(default_factory=list)
    error: str | None = None


def _published(upload_date: str | None) -> str | None:
    if not upload_date or not re.fullmatch(r"\d{8}", upload_date):
        return None
    parsed = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
    return parsed.isoformat().replace("+00:00", "Z")


def metadata_payload(info: dict[str, Any]) -> dict[str, Any]:
    """Reduce a yt-dlp info dict to the stable bronze metadata contract."""
    keys = (
        "id",
        "title",
        "description",
        "uploader",
        "uploader_id",
        "channel",
        "channel_id",
        "upload_date",
        "duration",
        "webpage_url",
        "view_count",
        "like_count",
        "tags",
        "categories",
        "language",
    )
    return {key: info.get(key) for key in keys if info.get(key) is not None}


def subtitle_language(path: Path) -> str:
    parts = path.stem.split(".")
    for part in reversed(parts):
        if part in {"es", "en"} or part.startswith(("es-", "en-")):
            return part.split("-", 1)[0]
    return "und"


class YoutubeAdapter:
    """Downloads subtitles and metadata only; video/audio files are never written."""

    def __init__(self, *, timeout: float = 60.0, max_videos: int = 50) -> None:
        self._timeout = timeout
        self._max_videos = max_videos

    def _base_options(self, output_dir: Path | None = None) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": int(self._timeout),
        }
        if output_dir is not None:
            options.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["es.*", "en.*"],
                    "subtitlesformat": "vtt",
                    "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
                }
            )
        return options

    def list_videos(self, channel_url: str, *, limit: int | None = None) -> list[tuple[str, str]]:
        try:
            import yt_dlp
        except Exception as exc:
            raise RuntimeError(f"yt-dlp unavailable: {exc}") from exc
        options = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlistend": limit or self._max_videos,
            "socket_timeout": int(self._timeout),
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(channel_url, download=False)
        entries = info.get("entries") or []
        videos: list[tuple[str, str]] = []
        for entry in entries:
            url = entry.get("url") or entry.get("webpage_url")
            if not url:
                continue
            if not url.startswith("http"):
                url = f"https://www.youtube.com/watch?v={entry.get('id', url)}"
            videos.append((url, entry.get("title") or ""))
        return videos

    def fetch_video(self, url: str) -> YoutubeResult:
        try:
            import yt_dlp
        except Exception as exc:
            return YoutubeResult(error=f"yt-dlp unavailable: {exc}")
        with tempfile.TemporaryDirectory(prefix="bronze-yt-") as tmp:
            output_dir = Path(tmp)
            try:
                with yt_dlp.YoutubeDL(self._base_options(output_dir)) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception as exc:
                return YoutubeResult(error=f"{type(exc).__name__}: {exc}")
            if info is None:
                return YoutubeResult(error="empty yt-dlp response")
            if info.get("entries"):
                entries = [entry for entry in info["entries"] if entry]
                if not entries:
                    return YoutubeResult(error="video unavailable")
                info = entries[0]
            video_url = info.get("webpage_url") or url
            published = _published(info.get("upload_date"))
            metadata = metadata_payload(info)
            payload = {
                "schema_version": "1.0",
                "source": "youtube",
                "video_id": info.get("id"),
                "title": info.get("title"),
                "channel": info.get("channel") or info.get("uploader"),
                "published_at": published,
                "duration_seconds": info.get("duration"),
                "webpage_url": video_url,
                "metadata": metadata,
            }
            parts = [
                YoutubePart(
                    url=video_url,
                    media_type="application/json",
                    data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                    role="metadata",
                    title=info.get("title"),
                    published_at=published,
                    language="es" if info.get("language", "").startswith("es") else "und",
                )
            ]
            for subtitle in sorted(output_dir.glob("*.vtt")):
                language = subtitle_language(subtitle)
                data = subtitle.read_bytes()
                parts.append(
                    YoutubePart(
                        url=f"{video_url}?sub={language}",
                        media_type=detect_media_type("text/vtt", data),
                        data=data,
                        role=f"subtitle_{language}",
                        title=info.get("title"),
                        published_at=published,
                        language=language if language in {"es", "en"} else "und",
                    )
                )
            return YoutubeResult(parts=parts)
