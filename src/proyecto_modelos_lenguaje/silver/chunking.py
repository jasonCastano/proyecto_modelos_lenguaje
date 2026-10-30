"""Section-aware chunking with deterministic identifiers."""

from __future__ import annotations

import re

from .cleaning import estimate_tokens
from .config import ChunkingConfig
from .models import (
    Chunk,
    ExtractedBlock,
    QualityFlag,
    SilverDocument,
    make_chunk_id,
)

_SENTENCE_END = re.compile(r"[.!?](?=\s)")


def _best_boundary(text: str, start: int, end: int, minimum: int) -> int:
    window = text[start:end]
    paragraph = window.rfind("\n\n")
    if paragraph >= 0 and start + paragraph >= minimum:
        return start + paragraph + 2
    sentence = None
    for match in _SENTENCE_END.finditer(window):
        if start + match.end() >= minimum:
            sentence = start + match.end()
    if sentence is not None:
        return sentence
    newline = window.rfind("\n")
    if newline >= 0 and start + newline >= minimum:
        return start + newline + 1
    space = window.rfind(" ")
    if space >= 0 and start + space >= minimum:
        return start + space + 1
    return end


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    raw = text[start:end]
    left = len(raw) - len(raw.lstrip())
    trimmed = raw.strip()
    return start + left, start + left + len(trimmed)


def _spans(
    blocks: list[ExtractedBlock], start: int, end: int
) -> tuple[int | None, int | None, float | None, float | None]:
    pages = [
        block.page
        for block in blocks
        if block.page is not None and block.char_start < end and block.char_end > start
    ]
    starts = [
        block.time_start
        for block in blocks
        if block.time_start is not None and block.char_start < end and block.char_end > start
    ]
    ends = [
        block.time_end
        for block in blocks
        if block.time_end is not None and block.char_start < end and block.char_end > start
    ]
    return (
        min(pages) if pages else None,
        max(pages) if pages else None,
        min(starts) if starts else None,
        max(ends) if ends else None,
    )


def _chunk_ranges(
    text: str,
    *,
    start: int,
    end: int,
    config: ChunkingConfig,
) -> list[tuple[int, int]]:
    max_chars = max(1, int(config.max_tokens * config.chars_per_token) - 2)
    target_chars = max(1, int(config.target_tokens * config.chars_per_token))
    overlap_chars = max(0, int(config.overlap_tokens * config.chars_per_token))
    section_length = end - start
    if section_length <= max_chars:
        return [_trim(text, start, end)] if section_length else []
    ranges: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        limit = min(cursor + target_chars, cursor + max_chars, end)
        if limit < end:
            limit = _best_boundary(text, cursor, limit, cursor + max(1, target_chars // 2))
        left, right = _trim(text, cursor, limit)
        if right > left:
            ranges.append((left, right))
        if right >= end:
            break
        next_cursor = max(left + 1, right - overlap_chars)
        while next_cursor < right and text[next_cursor] not in " \n\t":
            next_cursor += 1
        cursor = next_cursor if next_cursor > left else right
    return ranges


def chunk_document(
    document: SilverDocument,
    *,
    config: ChunkingConfig,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in document.sections:
        ranges = _chunk_ranges(
            document.text,
            start=section.char_start,
            end=section.char_end,
            config=config,
        )
        for order, (start, end) in enumerate(ranges):
            text = document.text[start:end]
            if not text.strip():
                continue
            page_start, page_end, time_start, time_end = _spans(document.blocks, start, end)
            flags = list(document.quality_flags)
            if section.title == "sin sección" and QualityFlag.NO_SECTION.value not in flags:
                flags.append(QualityFlag.NO_SECTION.value)
            if (
                estimate_tokens(text, config.chars_per_token) < config.min_tokens
                and QualityFlag.SHORT_SECTION.value not in flags
            ):
                flags.append(QualityFlag.SHORT_SECTION.value)
            chunks.append(
                Chunk(
                    schema_version="1.0",
                    chunk_id=make_chunk_id(document.doc_id, section.order, order),
                    doc_id=document.doc_id,
                    artifact_id=document.artifact_id,
                    content_hash=document.content_hash,
                    source_id=document.source_id,
                    authority=document.authority,
                    url=document.url,
                    title=document.title,
                    section_id=section.section_id,
                    section_title=section.title,
                    section_path=list(section.path),
                    section_level=section.level,
                    chunk_order=order,
                    text=text,
                    char_start=start,
                    char_end=end,
                    token_count=estimate_tokens(text, config.chars_per_token),
                    page_start=page_start,
                    page_end=page_end,
                    time_start=time_start,
                    time_end=time_end,
                    language=document.language,
                    media_type=document.media_type,
                    quality_flags=flags,
                    duplicate_of=None,
                    retrieved_at=document.retrieved_at,
                    license_note=document.license_note,
                )
            )
    return chunks
