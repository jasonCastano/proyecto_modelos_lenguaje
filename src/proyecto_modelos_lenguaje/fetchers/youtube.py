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


def _flatten_entries(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten yt-dlp channel tabs (Videos/Shorts) into video entries."""
    flattened: list[dict[str, Any]] = []
    for entry in info.get("entries") or []:
        if not entry:
            continue
        if entry.get("entries"):
            flattened.extend(_flatten_entries(entry))
        elif entry.get("id"):
            flattened.append(entry)
    return flattened


class YoutubeAdapter:
    """Downloads subtitles and metadata only; video/audio files are never written."""

    def __init__(self, *, timeout: float = 60.0, max_videos: int = 50) -> None:
        self._timeout = timeout
        self._max_videos = max_videos

    def _base_options(
        self, output_dir: Path | None = None, *, languages: tuple[str, ...] = ("es.*",)
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": int(self._timeout),
            "sleep_interval_subtitles": 1,
        }
        if output_dir is not None:
            options.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": list(languages),
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
        videos: list[tuple[str, str]] = []
        seen: set[str] = set()
        for entry in _flatten_entries(info):
            video_id = str(entry.get("id") or "")
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            url = entry.get("url") or entry.get("webpage_url")
            if not url or not str(url).startswith("http"):
                url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append((str(url), entry.get("title") or ""))
            if limit and len(videos) >= limit:
                break
        return videos

    def fetch_channel(self, channel_url: str) -> YoutubeResult:
        try:
            import yt_dlp
        except Exception as exc:
            return YoutubeResult(error=f"yt-dlp unavailable: {exc}")
        options = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlistend": 1,
            "socket_timeout": int(self._timeout),
        }
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(channel_url, download=False)
        except Exception as exc:
            return YoutubeResult(error=f"{type(exc).__name__}: {exc}")
        if not info:
            return YoutubeResult(error="empty channel response")
        payload = {
            "schema_version": "1.0",
            "source": "youtube",
            "type": "channel",
            "channel_id": info.get("channel_id") or info.get("id"),
            "title": info.get("channel") or info.get("title"),
            "handle": info.get("uploader_id"),
            "url": info.get("uploader_url") or channel_url,
            "description": info.get("description"),
            "followers": info.get("channel_follower_count"),
            "tags": info.get("tags") or [],
            "thumbnail": (info.get("thumbnails") or [{}])[-1].get("url"),
            "playlists": info.get("playlist_count"),
        }
        return YoutubeResult(
            parts=[
                YoutubePart(
                    url=channel_url,
                    media_type="application/json",
                    data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                    role="channel_metadata",
                    title=payload["title"],
                    published_at=None,
                    language="es",
                )
            ]
        )

    def fetch_video(self, url: str) -> YoutubeResult:
        try:
            import yt_dlp
        except Exception as exc:
            return YoutubeResult(error=f"yt-dlp unavailable: {exc}")
        with tempfile.TemporaryDirectory(prefix="bronze-yt-") as tmp:
            output_dir = Path(tmp)
            info: dict[str, Any] | None = None
            try:
                with yt_dlp.YoutubeDL(self._base_options(output_dir)) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception as exc:
                # Subtitles can fail (e.g. 429) while metadata is still available.
                try:
                    with yt_dlp.YoutubeDL(self._base_options(None)) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception:
                    return YoutubeResult(error=f"{type(exc).__name__}: {exc}")
            if info is None:
                return YoutubeResult(error="empty yt-dlp response")
            if info.get("entries"):
                entries = [entry for entry in info["entries"] if entry]
                if not entries:
                    return YoutubeResult(error="video unavailable")
                info = entries[0]
            if not list(output_dir.glob("*.vtt")):
                available = {
                    key.split("-", 1)[0]
                    for key in list(info.get("subtitles") or {})
                    + list(info.get("automatic_captions") or {})
                }
                if "es" not in available and "en" in available:
                    try:
                        with yt_dlp.YoutubeDL(
                            self._base_options(output_dir, languages=("en.*",))
                        ) as ydl:
                            ydl.extract_info(url, download=True)
                    except Exception:
                        pass
            video_url = info.get("webpage_url") or url
            published = _published(info.get("upload_date"))
            subtitle_files: dict[str, Path] = {}
            for subtitle in sorted(output_dir.glob("*.vtt")):
                language = subtitle_language(subtitle)
                current = subtitle_files.get(language)
                if current is None or "-orig" in current.stem:
                    subtitle_files[language] = subtitle
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
                "transcript_available": bool(subtitle_files),
                "subtitle_languages": sorted(subtitle_files),
                "metadata": metadata,
            }
            language = "es" if str(info.get("language") or "").startswith("es") else "und"
            if language == "und" and "es" in subtitle_files:
                language = "es"
            parts = [
                YoutubePart(
                    url=video_url,
                    media_type="application/json",
                    data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
                    role="metadata",
                    title=info.get("title"),
                    published_at=published,
                    language=language,
                )
            ]
            for language, subtitle in subtitle_files.items():
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
