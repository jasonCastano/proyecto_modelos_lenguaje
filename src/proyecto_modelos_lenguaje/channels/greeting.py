"""Presentación de Valer-IA al iniciar una conversación del canal (spec 038, contrato §2).

El bridge antepone la presentación en la primera respuesta atendida de cada hilo (research R1): no
depende del modelo. Hay tres variantes por idioma, elegidas de forma estable por el hilo (R2); cada
una tiene dos frases como máximo, menciona a Valer-IA, a Manuelita, las fuentes y las notas de voz,
y nunca sugiere comandos ni menús. Si la respuesta del modelo ya se presentó, no se agrega otra; si
solo abría con un saludo suelto («¡Hola!»), ese saludo se reemplaza por la presentación (R3).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from .intents import Language

# {name} queda vacío o es «, Ana». Dos frases por variante (FR-013).
INTRODUCTIONS: dict[str, tuple[str, ...]] = {
    "es": (
        "¡Hola{name}! Soy Valer-IA, la asistente virtual de Manuelita: te cuento de sus "
        "productos, negocios, sostenibilidad y cifras, siempre con fuentes, y también puedes "
        "mandarme notas de voz.",
        # Spec 036: una expresión caleña («ve»), como máximo, en la presentación.
        "¡Hola{name}, ve, qué gusto saludarte! Soy Valer-IA, la asistente virtual de Manuelita, y "
        "respondo tus dudas sobre la empresa con fuentes, por escrito o en notas de voz.",
        "¡Hola{name}! Te habla Valer-IA, la asistente virtual de Manuelita: resuelvo tus "
        "preguntas sobre la compañía con fuentes y, si prefieres, también me puedes mandar notas "
        "de voz.",
    ),
    "en": (
        "Hi{name}! I'm Valer-IA, Manuelita's virtual assistant: I can tell you about its "
        "products, businesses, sustainability and figures, always with sources, and you can also "
        "send me voice notes.",
        "Hi{name}, nice to meet you! I'm Valer-IA, Manuelita's virtual assistant, and I answer "
        "your questions about the company with sources, in writing or by voice note.",
        "Hello{name}! This is Valer-IA, Manuelita's virtual assistant: I answer your questions "
        "about the company with sources, and you can also send me voice notes.",
    ),
}

IDENTITY = {
    "es": "Soy Valer-IA, la asistente virtual de Manuelita.",
    "en": "I'm Valer-IA, Manuelita's virtual assistant.",
}

# Saludo suelto al inicio de la respuesta del modelo: «¡Hola!», «Hola, Ana.», «Hi!», «Buenas, 👋».
_EMOJI = "\U0001f300-\U0001faff☀-➿️"
LEADING_GREETING = re.compile(
    r"^\s*¡?\s*(?:hola|holi|buenas(?:\s+(?:tardes|noches))?|buenos\s+d[ií]as|buen\s+d[ií]a|"
    r"hi|hello|hey)\b[^.!?¿\n]{0,25}[.!,]+[\s" + _EMOJI + r"]*",
    re.IGNORECASE,
)
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
SELF_NAMES = ("valer-ia", "valeria", "valer ia")


def _variant(thread_id: str, count: int) -> int:
    """Índice estable por hilo (``hashlib``: ``hash()`` cambia entre procesos)."""
    digest = hashlib.sha256(thread_id.encode("utf-8")).digest()
    return digest[0] % count


def _clean_name(name: str | None) -> str | None:
    """Nombre corto y sin dígitos (nunca un número de teléfono); si no cumple, no se usa."""
    value = " ".join(str(name or "").split())
    if not value or len(value) > 40 or any(char.isdigit() for char in value):
        return None
    return value


def introduction(language: Language, thread_id: str, name: str | None = None) -> str:
    """Saludo y presentación de dos frases en el idioma del turno, con el nombre si se conoce."""
    options = INTRODUCTIONS.get(language, INTRODUCTIONS["es"])
    clean = _clean_name(name)
    return options[_variant(thread_id, len(options))].format(name=f", {clean}" if clean else "")


def identity_line(language: Language) -> str:
    """Una frase de identidad para los mensajes de error en un hilo aún sin presentar (R7)."""
    return IDENTITY.get(language, IDENTITY["es"])


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in folded if not unicodedata.combining(char))


def already_introduced(answer: str) -> bool:
    """``True`` si las dos primeras frases de la respuesta ya nombran a Valer-IA."""
    head = " ".join(SENTENCE_END.split(answer.strip())[:2])
    plain = _plain(head)
    return any(name in plain for name in SELF_NAMES)


def _capitalize_first_letter(text: str) -> str:
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + char.upper() + text[index + 1 :]
    return text


def merge(intro: str, answer: str) -> str:
    """Antepone la presentación; quita antes un saludo suelto del modelo (sin saludar dos veces)."""
    body = answer.strip()
    match = LEADING_GREETING.match(body)
    if match:
        body = _capitalize_first_letter(body[match.end() :].lstrip())
    return f"{intro} {body}".strip() if body else intro
