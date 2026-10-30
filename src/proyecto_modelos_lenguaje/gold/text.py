"""Text normalization and sentence segmentation for the gold layer."""

from __future__ import annotations

import re
import unicodedata
import zlib

_ABBREVIATIONS = (
    "s.a.",
    "s.a.s.",
    "ltda.",
    "no.",
    "nro.",
    "p.",
    "pp.",
    "vs.",
    "dr.",
    "dra.",
    "ing.",
    "sr.",
    "sra.",
    "etc.",
    "aprox.",
    "fig.",
    "num.",
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-z0-9áéíóúüñ]+", re.IGNORECASE)


def fold_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def normalize_for_match(text: str) -> str:
    return fold_accents(normalize_text(text).lower())


def normalize_for_hash(text: str) -> str:
    return " ".join(_WORD.findall(normalize_for_match(text)))


def _ends_with_abbreviation(text: str) -> bool:
    lowered = text.strip().lower()
    if any(lowered.endswith(item) for item in _ABBREVIATIONS):
        return True
    return bool(re.search(r"\b[a-z]\.$", lowered))


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts = re.split(r"(?<=;)\s+", text)
    if len(parts) > 1:
        result: list[str] = []
        for part in parts:
            result.extend(_split_long(part, max_chars))
        return result
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > max_chars:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    return chunks or [text]


def split_sentences(text: str, *, min_chars: int = 40, max_chars: int = 700) -> list[str]:
    """Split a cleaned passage into usable sentences without breaking abbreviations."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    raw = [part.strip() for part in _SENTENCE.split(normalized) if part.strip()]
    merged: list[str] = []
    for sentence in raw:
        if merged and _ends_with_abbreviation(merged[-1]):
            merged[-1] = f"{merged[-1]} {sentence}"
        else:
            merged.append(sentence)

    grouped: list[str] = []
    for sentence in merged:
        if grouped and len(sentence) < min_chars:
            grouped[-1] = f"{grouped[-1]} {sentence}"
        else:
            grouped.append(sentence)
    if len(grouped) > 1 and len(grouped[0]) < min_chars:
        grouped[1] = f"{grouped[0]} {grouped[1]}"
        grouped.pop(0)

    result: list[str] = []
    for sentence in grouped:
        result.extend(_split_long(sentence, max_chars))
    return [item.strip() for item in result if item.strip()]


def shingles(text: str, size: int = 5) -> set[int]:
    words = _WORD.findall(normalize_for_match(text))
    if len(words) < size:
        return {zlib.crc32(" ".join(words).encode())} if words else set()
    return {
        zlib.crc32(" ".join(words[index : index + size]).encode())
        for index in range(len(words) - size + 1)
    }


def jaccard(left: set[int], right: set[int]) -> float:
    if not left or not right:
        return 0.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0
