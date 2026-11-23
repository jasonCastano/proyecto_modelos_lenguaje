"""Texto del dictado (spec 023, research R4 y R6).

- ``initial_prompt``: el vocabulario propio como prompt inicial del reconocedor.
- ``apply_corrections``: grafías de la marca (``valeria caña`` → ``Valer-IA Caña``) en palabras
  completas, sin distinguir mayúsculas ni tildes, en una sola pasada.
- ``clip_message``: recorte al máximo de un mensaje del chat.
- ``is_hallucination``: textos que Whisper inventa sobre silencio o ruido.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence

from ..transcription import is_noise

MAX_PROMPT_CHARS = 600
MAX_MESSAGE_CHARS = 2000  # ``ChatRequest.message``

# Alucinaciones típicas de Whisper con audio corto y silencioso. Se comparan con el texto
# completo normalizado: «gracias» a secas es un mensaje legítimo y no se descarta.
STT_HALLUCINATIONS = frozenset(
    {
        "gracias por ver",
        "gracias por ver el video",
        "gracias por ver el video hasta el final",
        "suscribete",
        "suscribete al canal",
        "suscribete a mi canal",
        "musica",
        "aplausos",
        "risas",
        "silencio",
    }
)

_ACCENTS = {
    "a": "aáàä",
    "e": "eéèë",
    "i": "iíìï",
    "o": "oóòö",
    "u": "uúùü",
    "n": "nñ",
}


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def initial_prompt(vocabulary: Sequence[str]) -> str:
    """«Manuelita, Valer-IA Caña, …» con punto final, sin pasar de ``MAX_PROMPT_CHARS``."""
    terms: list[str] = []
    for term in (str(item).strip() for item in vocabulary):
        if not term:
            continue
        if len(", ".join([*terms, term])) + 1 > MAX_PROMPT_CHARS:
            break
        terms.append(term)
    return f"{', '.join(terms)}." if terms else ""


def _pattern(key: str) -> str:
    parts: list[str] = []
    for char in _fold(key):
        if char.isspace():
            parts.append(r"\s+")
        elif char in _ACCENTS:
            parts.append(f"[{_ACCENTS[char]}]")
        else:
            parts.append(re.escape(char))
    return "".join(parts)


def apply_corrections(text: str, corrections: Iterable[tuple[str, str]]) -> str:
    """Reemplaza palabras completas según ``corrections`` (clave en minúsculas → grafía)."""
    table = {_fold(key): value for key, value in corrections if key.strip()}
    if not table or not text:
        return text
    keys = sorted(table, key=len, reverse=True)  # «valeria caña» antes que «valeria»
    regex = re.compile(
        r"(?<![\w-])(?:" + "|".join(_pattern(key) for key in keys) + r")(?![\w-])",
        flags=re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        return table.get(" ".join(_fold(match.group(0)).split()), match.group(0))

    return regex.sub(replace, text)


def clip_message(text: str, limit: int = MAX_MESSAGE_CHARS) -> tuple[str, bool]:
    """Recorta a ``limit`` caracteres en un límite de palabra; indica si recortó."""
    text = text.strip()
    if len(text) <= limit:
        return text, False
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:"), True


def is_hallucination(text: str) -> bool:
    """Texto vacío, de relleno conocido o de subtítulos (no se envía como mensaje)."""
    folded = " ".join(re.findall(r"[a-z0-9]+", _fold(text)))
    if not folded:
        return True
    return folded in STT_HALLUCINATIONS or is_noise(text)
