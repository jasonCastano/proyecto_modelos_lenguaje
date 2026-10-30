"""Deterministic Spanish/English language detection for bronze metadata."""

from __future__ import annotations

import re
import unicodedata

from ..models import Language, LanguageMethod

_SPANISH = frozenset(
    [
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "de",
        "del",
        "al",
        "y",
        "o",
        "que",
        "en",
        "por",
        "para",
        "con",
        "sin",
        "sobre",
        "entre",
        "como",
        "mas",
        "pero",
        "sus",
        "su",
        "este",
        "esta",
        "estos",
        "estas",
        "es",
        "son",
        "fue",
        "ser",
        "esta",
        "estan",
        "empresa",
        "nosotros",
        "nuestro",
        "nuestra",
        "colombia",
        "colombiano",
        "ingenio",
        "azucar",
        "caña",
        "desarrollo",
        "sostenible",
        "comunidad",
        "trabajo",
        "año",
        "desde",
        "hasta",
        "donde",
        "cuando",
    ]
)

_ENGLISH = frozenset(
    [
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "on",
        "with",
        "without",
        "about",
        "between",
        "as",
        "but",
        "its",
        "this",
        "these",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "company",
        "our",
        "we",
        "colombia",
        "colombian",
        "sugar",
        "cane",
        "sustainable",
        "development",
        "community",
        "work",
        "year",
        "from",
        "until",
        "where",
        "when",
        "which",
    ]
)

_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
_ACCENTS = str.maketrans("áéíóúüñ", "aeiouun")


def _normalize(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _WORD_RE.findall(stripped.translate(_ACCENTS))[:4000]


def detect_language(html_lang: str | None, text: str) -> tuple[str, str]:
    """Return ``(language, method)`` using the declared language or a stopword heuristic."""
    if html_lang:
        primary = html_lang.strip().lower().split("-", 1)[0]
        if primary == "es":
            return Language.ES.value, LanguageMethod.HTML_LANG.value
        if primary == "en":
            return Language.EN.value, LanguageMethod.HTML_LANG.value
    tokens = _normalize(text)
    if len(tokens) < 10:
        return Language.UND.value, LanguageMethod.UNKNOWN.value
    spanish = sum(1 for token in tokens if token in _SPANISH)
    english = sum(1 for token in tokens if token in _ENGLISH)
    if max(spanish, english) < 3:
        return Language.UND.value, LanguageMethod.UNKNOWN.value
    if spanish >= english * 1.2:
        return Language.ES.value, LanguageMethod.HEURISTIC.value
    if english >= spanish * 1.2:
        return Language.EN.value, LanguageMethod.HEURISTIC.value
    return Language.UND.value, LanguageMethod.UNKNOWN.value
