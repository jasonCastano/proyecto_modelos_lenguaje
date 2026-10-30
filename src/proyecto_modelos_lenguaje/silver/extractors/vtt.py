"""WebVTT parsing for YouTube transcripts."""

from __future__ import annotations

import html
import re

from ..models import ExtractedBlock, ExtractedDocument

_TIMING = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
)
_TAG = re.compile(r"<[^>]+>")
_NOISE = (
    "amara.org",
    "subtítulos por la comunidad",
    "subtitulos por la comunidad",
    "gracias por ver",
    "thanks for watching",
)


def _seconds(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    minutes, seconds = parts
    return int(minutes) * 60 + float(seconds)


def _clean_text(text: str) -> str:
    text = html.unescape(_TAG.sub("", text))
    return " ".join(text.split())


def _is_noise(text: str) -> bool:
    lowered = text.lower()
    return not text or any(pattern in lowered for pattern in _NOISE)


def extract_vtt(data: bytes, *, title: str | None = None) -> ExtractedDocument:
    raw = data.decode("utf-8", errors="replace")
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\r?\n\s*\r?\n", raw):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0].upper().startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        match = _TIMING.search(lines[timing_index])
        if not match:
            continue
        text = _clean_text(" ".join(lines[timing_index + 1 :]))
        if _is_noise(text):
            continue
        cues.append((_seconds(match.group("start")), _seconds(match.group("end")), text))
    merged: list[tuple[float, float, str]] = []
    for start, end, text in cues:
        if merged and text == merged[-1][2]:
            continue
        if merged and start < merged[-1][1]:
            start = merged[-1][1]
        if end <= start:
            end = start + 0.1
        merged.append((start, end, text))
    blocks: list[ExtractedBlock] = []
    if title:
        blocks.append(ExtractedBlock(text=title, level=1))
    for start, end, text in merged:
        blocks.append(ExtractedBlock(text=text, time_start=start, time_end=end))
    return ExtractedDocument(
        title=title,
        blocks=blocks,
        metadata={"cues": len(merged)},
        skip_reason=None if merged else "no_text",
    )
