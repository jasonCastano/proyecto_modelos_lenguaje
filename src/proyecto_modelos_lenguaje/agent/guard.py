"""Blindaje contra inyección indirecta: aislamiento XML y detector de instrucciones (FR-016).

El contenido recuperado es **dato no confiable** (Principio IV). Cada fragmento entra al prompt
dentro de ``<documento>`` con ``<`` y ``>`` escapados, de modo que no pueda cerrar la etiqueta ni
abrir otra. El detector no descarta fragmentos (eso ocultaría evidencia); solo los marca como
anómalos para la traza.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

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
)


def detect_instructions(text: str) -> list[str]:
    """Devuelve los motivos (nombres de patrón) de instrucciones dirigidas al modelo."""
    return [name for name, pattern in INSTRUCTION_PATTERNS if pattern.search(text or "")]


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
