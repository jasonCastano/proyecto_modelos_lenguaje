"""Texto que se lee en voz alta (spec 016, data-model.md).

``clean_for_speech`` es la única autoridad de limpieza: el servidor la aplica a cada oración
antes de sintetizar, para que la voz nunca pronuncie citas, URLs, Markdown ni marcas internas.
"""

from __future__ import annotations

import re

from ..agent.guard import OMITTED_MARKER

CITATION = re.compile(r"\[\s*U\d+(?:\s*[,;]\s*U\d+)*\s*\]", re.IGNORECASE)
MD_LINK = re.compile(r"!?\[([^\]]*)\]\((?:[^)\s]+)(?:\s+\"[^\"]*\")?\)")
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
BULLET = re.compile(r"(?m)^\s*(?:[-*+•]|\d+[.)])\s+")
MD_SYMBOLS = re.compile(r"[*_#`>|~]+")
SPEAKABLE = re.compile(r"[^\W_]", re.UNICODE)
SPACES = re.compile(r"\s+")

ABBREVIATIONS = (
    "sr",
    "sra",
    "srta",
    "dr",
    "dra",
    "etc",
    "ej",
    "núm",
    "art",
    "av",
    "ing",
    "lic",
    "pág",
)
SENTENCE_END = re.compile(r"([.!?…;]+)(?=\s)|\n\s*\n")


def clean_for_speech(text: str) -> str:
    """Limpia en el orden de data-model.md; devuelve ``""`` si no queda nada pronunciable."""
    value = (text or "").replace(OMITTED_MARKER, " ")
    value = CITATION.sub(" ", value)
    value = MD_LINK.sub(lambda match: match.group(1), value)
    value = URL.sub(" ", value)
    value = BULLET.sub(" ", value)
    value = MD_SYMBOLS.sub(" ", value)
    value = value.replace("%", " por ciento ").replace("&", " y ")
    value = SPACES.sub(" ", value).strip()
    value = re.sub(r"\s+([,.;:!?…])", r"\1", value)
    return value if SPEAKABLE.search(value) else ""


def _is_abbreviation(chunk: str, following: str) -> bool:
    words = chunk.rstrip(".").split()
    if not words:
        return False
    word = words[-1]
    last = word.lower()
    if last in ABBREVIATIONS:
        return True
    # «No. 3»: solo con mayúscula y seguido de un número (no confundir con «no.» al final)
    if word == "No" and following.lstrip()[:1].isdigit():
        return True
    # «p. ej.»: letra suelta seguida de punto
    return len(last) == 1 and last.isalpha()


def _split_long(sentence: str, max_chars: int) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]
    parts: list[str] = []
    rest = sentence
    while len(rest) > max_chars:
        window = rest[:max_chars]
        cut = max(window.rfind(", "), window.rfind("; "))
        if cut <= 0:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = max_chars
        else:
            cut += 1
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    return parts


def split_sentences(
    text: str, max_chars: int = 600, first_max_chars: int | None = None
) -> list[str]:
    """Corta un texto completo en oraciones (misma regla que el segmentador del navegador).

    ``first_max_chars`` limita solo el primer segmento, como hace el navegador (120) para que el
    primer audio llegue pronto (SC-001).
    """
    sentences: list[str] = []
    buffer = ""
    position = 0
    source = (text or "") + " "
    for match in SENTENCE_END.finditer(source):
        end = match.end(1) if match.group(1) else match.end()
        candidate = buffer + source[position:end]
        position = end
        if match.group(1) == "." and _is_abbreviation(candidate, source[end:]):
            buffer = candidate
            continue
        buffer = ""
        if candidate.strip():
            sentences.append(candidate.strip())
    tail = (buffer + source[position:]).strip()
    if tail:
        sentences.append(tail)
    result: list[str] = []
    for sentence in sentences:
        clean = " ".join(sentence.split())
        if not result and first_max_chars and len(clean) > first_max_chars:
            head, *rest = _split_long(clean, first_max_chars)
            result.append(head)
            tail = " ".join(rest)
            result.extend(_split_long(tail, max_chars) if tail else [])
        else:
            result.extend(_split_long(clean, max_chars))
    return result
