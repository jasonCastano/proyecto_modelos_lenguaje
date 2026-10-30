"""Text normalization, cleaning and quality helpers for the silver layer."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

from ..extractors.language import detect_language
from .models import ExtractedBlock, ExtractedDocument, QualityFlag

CLEANING_VERSION = "1.0.0"

_WHITESPACE = re.compile(r"[ \t\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "Ãƒ", "Â¡", "Â¿")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """Return a deterministic, offline token estimate."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / chars_per_token))


def normalize_whitespace(text: str) -> str:
    """Normalize line endings, spaces and blank lines without changing words."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text)
    text = _WHITESPACE.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def repair_mojibake(text: str) -> tuple[str, bool]:
    """Repair reversible UTF-8/latin-1 mojibake; return the text and whether it changed."""
    if not text or not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text, False
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except UnicodeEncodeError, UnicodeDecodeError:
        return text, False
    before = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    after = sum(repaired.count(marker) for marker in _MOJIBAKE_MARKERS)
    if after < before:
        return repaired, True
    return text, False


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def alpha_ratio(text: str) -> float:
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return 0.0
    return sum(1 for char in visible if char.isalpha()) / len(visible)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def detect_text_language(
    text: str,
    *,
    declared: str | None = None,
    min_tokens: int = 10,
) -> tuple[str, str]:
    """Detect the language while respecting a declared HTML language."""
    if len(text.split()) < min_tokens and declared not in {"es", "en"}:
        return "und", "unknown"
    return detect_language(declared, text)


def clean_document(
    document: ExtractedDocument,
    *,
    declared_language: str | None,
    min_text_chars: int,
    min_alpha_ratio: float,
    min_tokens: int,
) -> ExtractedDocument:
    """Normalize blocks in place and attach language/quality information."""
    cleaned_blocks: list[ExtractedBlock] = []
    repaired = False
    for block in document.blocks:
        text, changed = repair_mojibake(block.text)
        repaired = repaired or changed
        text = normalize_whitespace(text)
        if not text:
            continue
        block.text = text
        cleaned_blocks.append(block)
    document.blocks = cleaned_blocks
    if repaired:
        document.flags.add(QualityFlag.ENCODING_REPAIRED.value)

    text = document.text
    title = normalize_whitespace(repair_mojibake(document.title or "")[0])
    if not title:
        heading = next((block.text for block in document.blocks if block.text), None)
        title = heading or "Documento sin título"
    document.title = title

    language, method = detect_text_language(text, declared=declared_language, min_tokens=min_tokens)
    document.metadata["language"] = language
    document.metadata["language_method"] = method
    if language == "und":
        document.flags.add(QualityFlag.LANGUAGE_UNKNOWN.value)
    if len(text) < min_text_chars:
        document.flags.add(QualityFlag.NO_TEXT.value)
    elif alpha_ratio(text) < min_alpha_ratio:
        document.flags.add(QualityFlag.LOW_TEXT_DENSITY.value)
    return document
