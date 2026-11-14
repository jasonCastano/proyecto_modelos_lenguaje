"""Blindaje contra inyección indirecta: aislamiento XML, detector y neutralización (FR-016).

El contenido recuperado es **dato no confiable** (Principio IV). Tres capas:

1. **Aislamiento**: cada fragmento entra al prompt dentro de ``<documento>`` con ``<`` y ``>``
   escapados, de modo que no pueda cerrar la etiqueta ni abrir otra.
2. **Detección**: patrones de instrucciones dirigidas al asistente (también en inglés y con
   mayúsculas, tildes o caracteres invisibles intercalados) marcan el fragmento como anómalo.
3. **Neutralización** (spec 015): las oraciones detectadas se sustituyen por
   ``[instrucción embebida omitida]`` antes de llegar al modelo. El resto del fragmento se conserva
   (no se oculta evidencia) y la fuente original sigue disponible en la traza.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

OMITTED_MARKER = "[instrucción embebida omitida]"
INVISIBLE_CHARS = dict.fromkeys(map(ord, "​‌‍⁠﻿"))
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")

INSTRUCTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignora_instrucciones",
        re.compile(
            r"\b(ignora|ignore|olvida|forget|omite|disregard)\b[^.\n]{0,40}"
            r"\b(instrucciones|instructions|reglas|rules|indicaciones|prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "revela_prompt",
        re.compile(
            r"\b(revela|muestra|imprime|reveal|show|print|repeat|repite)\b[^.\n]{0,40}"
            r"\b(prompt|instrucciones del sistema|system prompt|system message|tus instrucciones"
            r"|your instructions)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "rol_sistema",
        re.compile(r"(^|\n)\s*(system|sistema|assistant|asistente)\s*:", re.IGNORECASE),
    ),
    (
        "cambio_de_rol",
        re.compile(
            r"\b(a partir de ahora|desde ahora|from now on)\b[^.\n]{0,40}"
            r"\b(eres|actúa|actua|you are|act as)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "nuevas_instrucciones",
        re.compile(
            r"\b(nuevas instrucciones|new instructions|instrucción prioritaria|override)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "etiqueta_documento",
        re.compile(r"</?\s*(documento|context|system)\b", re.IGNORECASE),
    ),
    (
        # Spec 015: un documento que pide escribir en la memoria o exportar (FR-008).
        "accion_escritura",
        re.compile(
            r"\b(save_preference|save_profile|forget_memory|export_conversation)\b"
            r"|\b(guarda\w*|almacena\w*|olvida\w*|borra\w*|exporta\w*|save|store|forget|export)\b"
            r"[^.\n]{0,60}\b(preferencias?|memoria|perfil|conversaci[oó]n|preferences?|memory"
            r"|profile|conversation)\b",
            re.IGNORECASE,
        ),
    ),
)


def normalize_for_detection(text: str) -> str:
    """Texto sin tildes ni caracteres invisibles y con espacios colapsados (anti-evasión)."""
    visible = (text or "").translate(INVISIBLE_CHARS)
    decomposed = unicodedata.normalize("NFKD", visible)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(plain.split())


def detect_instructions(text: str) -> list[str]:
    """Devuelve los motivos (nombres de patrón) de instrucciones dirigidas al modelo."""
    raw = text or ""
    normalized = normalize_for_detection(raw)
    return [
        name
        for name, pattern in INSTRUCTION_PATTERNS
        if pattern.search(raw) or pattern.search(normalized)
    ]


@dataclass(frozen=True, slots=True)
class NeutralizedText:
    """Texto listo para el modelo y las oraciones que se sustituyeron (con sus motivos)."""

    text: str
    removed: tuple[tuple[str, tuple[str, ...]], ...] = ()


def neutralize(text: str) -> NeutralizedText:
    """Sustituye por ``OMITTED_MARKER`` las oraciones con instrucciones dirigidas al asistente.

    Opera por oración para conservar el contenido legítimo del mismo fragmento. Si no hay
    instrucciones, devuelve el texto idéntico.
    """
    if not text or not detect_instructions(text):
        return NeutralizedText(text or "")
    removed: list[tuple[str, tuple[str, ...]]] = []
    pieces: list[str] = []
    last = 0
    for match in SENTENCE_SPLIT.finditer(text):
        pieces.append(text[last : match.start()])
        pieces.append(match.group(0))
        last = match.end()
    pieces.append(text[last:])
    for index in range(0, len(pieces), 2):  # posiciones pares: oraciones; impares: separadores
        sentence = pieces[index]
        reasons = detect_instructions(sentence)
        if sentence.strip() and reasons:
            removed.append((sentence.strip(), tuple(reasons)))
            pieces[index] = OMITTED_MARKER
    if not removed:  # la instrucción cruza oraciones: se omite el fragmento entero
        return NeutralizedText(OMITTED_MARKER, ((text.strip(), tuple(detect_instructions(text))),))
    return NeutralizedText("".join(pieces), tuple(removed))


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _attribute(text: str) -> str:
    return _escape(text).replace('"', "&quot;").replace("\n", " ").strip()


@dataclass(frozen=True, slots=True)
class GuardedDocument:
    """Fragmento o fila listo para el prompt."""

    label: str
    source: str
    text: str


def render_documents(documents: Iterable[GuardedDocument]) -> str:
    """Envuelve cada documento como ``<documento id="U#" fuente="...">…</documento>``."""
    blocks = [
        f'<documento id="{_attribute(doc.label)}" fuente="{_attribute(doc.source)}">\n'
        f"{_escape(doc.text.strip())}\n"
        "</documento>"
        for doc in documents
    ]
    return "\n".join(blocks)


LEAK_MIN_CHARS = 40
LEAK_SPLIT = re.compile(r"(?<=[.:;!?])\s+|\n+")


def _squash(text: str) -> str:
    return " ".join(re.sub(r"[`*_>#\-]+", " ", text).lower().split())


def leaks_prompt(answer: str, prompt_text: str) -> bool:
    """True si la respuesta reproduce una frase del system prompt (fuga por inyección).

    Segunda línea de defensa: aunque un documento malicioso logre que el modelo «revele su
    prompt», la respuesta se descarta antes de mostrarse.
    """
    squashed = _squash(answer)
    if not squashed:
        return False
    sentences = (_squash(part) for part in LEAK_SPLIT.split(prompt_text))
    return any(len(s) >= LEAK_MIN_CHARS and s in squashed for s in sentences)
