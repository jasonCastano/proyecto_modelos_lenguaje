"""Revisión automática del formato de las respuestas del canal (spec 029, FR-015).

``review_reply`` revisa lo que la persona recibe por WhatsApp:

- **idioma único**: encabezados y frases fijas del idioma correcto y ninguna oración en el
  otro idioma;
- **bloque de fuentes**: una línea por fuente ``[n] Título[, p. X] — URL``, numeración 1..N sin
  huecos, sin fuentes repetidas (URL + página) y títulos limpios de una línea y ≤ 80 caracteres;
- **aviso de seguridad**: solo si la persona compartió datos sensibles;
- **turno con voz** (spec 030, ``voice=True``): el texto lleva solo bloques de fuentes; cualquier
  otra oración repite lo dicho en la nota de voz (``voice_text_duplicate``).

Se usa en las pruebas, en ``pml channels simulate --check`` y sobre las respuestas reales de
regresión.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

TITLE_CHARS = 80
HEADERS = {
    "es": ("Fuentes:", "Fuentes sintéticas (demostración):"),
    "en": ("Sources:", "Synthetic sources (demo):"),
}
ALL_HEADERS = {header for pair in HEADERS.values() for header in pair}
SOURCE_LINE = re.compile(r"^\[(?P<n>\d+)\] (?P<title>.+?)(?: — (?P<url>\S+))?$")
PAGE = re.compile(r", p\. (?P<page>[\w-]+)$")
DIRTY_TITLE = re.compile(r"(?i)^(?:índice|indice|contenido|tabla de contenido)\b|^[\d.\s]+$|_")
NOTICE_MARKERS = {
    "es": ("por tu seguridad", "no hace falta que compartas", "no compartas números de tarjeta"),
    "en": ("just so you know", "no need to share", "for your safety"),
}
FIXED_MARKERS = {
    "es": ("respuesta abreviada", "Fuentes:", "Fuentes sintéticas"),
    "en": ("shortened answer", "Sources:", "Synthetic sources"),
}
SPANISH_WORDS = {
    "el",
    "la",
    "los",
    "las",
    "de",
    "del",
    "que",
    "en",
    "y",
    "por",
    "para",
    "con",
    "una",
    "es",
    "son",
    "su",
    "sus",
    "también",
    "desde",
    "como",
    "más",
    "año",
    "cifras",
    "si",
    "quieres",
    "te",
    "puedo",
}
ENGLISH_WORDS = {
    "the",
    "and",
    "of",
    "to",
    "in",
    "is",
    "are",
    "for",
    "with",
    "its",
    "from",
    "that",
    "this",
    "was",
    "were",
    "by",
    "an",
    "if",
    "you",
    "can",
    "would",
    "like",
    "year",
    "figures",
    "i",
    "my",
}
WORD = re.compile(r"[a-záéíóúñü']+", re.IGNORECASE)
SENTENCE = re.compile(r"(?<=[.!?…])\s+")


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message_index: int
    detail: str


def _sentence_language(sentence: str) -> str | None:
    words = [w.lower() for w in WORD.findall(sentence)]
    if len(words) < 5:
        return None
    spanish = sum(w in SPANISH_WORDS for w in words)
    english = sum(w in ENGLISH_WORDS for w in words)
    if spanish >= 2 and spanish > english * 2:
        return "es"
    if english >= 2 and english > spanish * 2:
        return "en"
    return None


def _split_sources(message: str) -> tuple[str, list[tuple[str, list[str]]]]:
    """Cuerpo del mensaje y bloques de fuentes ``(encabezado, líneas)``."""
    lines = message.splitlines()
    body: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped in ALL_HEADERS:
            current = []
            blocks.append((stripped, current))
            continue
        if current is not None:
            if stripped:
                current.append(stripped)
            elif current:
                current = None  # una línea vacía cierra el bloque
            continue
        if SOURCE_LINE.match(stripped) and not any(item.strip() for item in body):
            # Spec 030: continuación de un bloque de fuentes que no cupo en el mensaje anterior.
            current = [stripped]
            blocks.append(("", current))
            continue
        body.append(line)
    return "\n".join(body), blocks


def review_reply(
    messages: Sequence[str],
    language: str,
    *,
    sensitive_input: bool = False,
    voice: bool = False,
) -> list[Issue]:
    """Hallazgos de formato de una respuesta completa (lista vacía = conforme).

    Con ``voice=True`` se revisa el texto que acompaña a una nota de voz: solo fuentes (o nada). El
    aviso de datos sensibles va en la voz, así que no se exige por escrito.
    """
    issues: list[Issue] = []
    other = "en" if language == "es" else "es"
    numbers: list[int] = []
    seen: set[tuple[str, str]] = set()
    notice_found = False
    for index, message in enumerate(messages):
        body, blocks = _split_sources(message)
        lowered = message.lower()
        if voice and body.strip():
            first = " ".join(body.split())[:40]
            issues.append(Issue("voice_text_duplicate", index, f"texto además de la voz: {first}"))
        if any(marker in lowered for markers in NOTICE_MARKERS.values() for marker in markers):
            notice_found = True
        for marker in FIXED_MARKERS[other]:
            if marker.lower() in lowered:
                issues.append(
                    Issue("mixed_language", index, f"texto fijo en otro idioma: {marker}")
                )
        for marker in NOTICE_MARKERS[other]:
            if marker in lowered:
                issues.append(Issue("mixed_language", index, "aviso en otro idioma"))
        for sentence in SENTENCE.split(re.sub(r"https?://\S+", " ", body)):
            if _sentence_language(sentence) == other:
                issues.append(Issue("mixed_language", index, f"oración en {other}"))
                break
        for header, lines in blocks:
            if header and header not in HEADERS.get(language, ()):
                issues.append(Issue("wrong_sources_header", index, header))
            for line in lines:
                match = SOURCE_LINE.match(line)
                if match is None:
                    issues.append(Issue("sources_line_format", index, line[:40]))
                    continue
                numbers.append(int(match.group("n")))
                title = match.group("title")
                page_match = PAGE.search(title)
                page = page_match.group("page") if page_match else ""
                clean = PAGE.sub("", title).strip()
                if len(clean) > TITLE_CHARS or DIRTY_TITLE.search(clean) or not clean:
                    issues.append(Issue("dirty_title", index, clean[:40]))
                key = ((match.group("url") or clean).lower(), page)
                if key in seen:
                    issues.append(Issue("duplicate_source", index, f"[{match.group('n')}]"))
                seen.add(key)
    if numbers and sorted(numbers) != list(range(1, len(numbers) + 1)):
        issues.append(Issue("sources_numbering", len(messages) - 1, str(numbers)))
    if notice_found and not sensitive_input:
        issues.append(Issue("unexpected_notice", 0, "aviso de seguridad sin datos sensibles"))
    if sensitive_input and not notice_found and not voice:  # con voz, el aviso va en el audio
        issues.append(Issue("missing_notice", 0, "faltó el aviso de seguridad"))
    return issues


def codes(issues: Sequence[Issue]) -> set[str]:
    return {issue.code for issue in issues}
