"""Respuesta de Valer-IA en el formato de WhatsApp (spec 024, research R13, channel-api §5).

- Markdown → WhatsApp: ``**x**`` → ``*x*``, títulos → negrita, tablas → líneas con «•».
- Citas ``[U3]``/``[F1]`` → ``[1]``/``[2]`` por orden de aparición y bloque «Fuentes:» al final.
- Corte por frases a ``max_chars`` y como mucho ``max_messages`` mensajes; nunca parte una cita.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

LABEL = re.compile(r"\[(?P<labels>[UF]\d+(?:\s*,\s*[UF]\d+)*)\]")
BOLD = re.compile(r"\*\*(.+?)\*\*")
UNDERSCORE_BOLD = re.compile(r"__(.+?)__")
HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
BULLET = re.compile(r"^[ \t]*[-*+][ \t]+", re.MULTILINE)
TABLE_RULE = re.compile(r"^[ \t]*\|?[ \t]*:?-{2,}.*$", re.MULTILINE)
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n{2,}")
TITLE_CHARS = 80
ABBREVIATED = "(respuesta abreviada; pídeme más detalle)"


def _table_rows(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if TABLE_RULE.fullmatch(line):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            lines.append("• " + " · ".join(cell for cell in cells if cell))
        else:
            lines.append(line)
    return "\n".join(lines)


def markdown_to_whatsapp(text: str) -> str:
    out = _table_rows(text)
    out = HEADING.sub(lambda m: f"*{m.group(1).strip()}*", out)
    out = BOLD.sub(r"*\1*", out)
    out = UNDERSCORE_BOLD.sub(r"*\1*", out)
    out = BULLET.sub("• ", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def number_citations(
    text: str, citations: Sequence[Mapping[str, Any]]
) -> tuple[str, list[tuple[int, Mapping[str, Any]]]]:
    """Renumera las etiquetas por orden de aparición y devuelve las fuentes usadas."""
    by_label = {str(c.get("label")): c for c in citations if c.get("label")}
    order: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        numbers = []
        for label in re.split(r"\s*,\s*", match.group("labels")):
            if label not in order:
                order[label] = len(order) + 1
            numbers.append(str(order[label]))
        return "[" + "][".join(numbers) + "]"

    renumbered = LABEL.sub(replace, text)
    used = [(number, by_label.get(label, {"label": label})) for label, number in order.items()]
    return renumbered, used


def sources_block(used: Sequence[tuple[int, Mapping[str, Any]]]) -> str:
    lines = []
    for number, citation in used:
        title = str(citation.get("title") or citation.get("label") or "Fuente").strip()
        if len(title) > TITLE_CHARS:
            title = title[: TITLE_CHARS - 1] + "…"
        page = citation.get("page") or citation.get("page_start")
        if page:
            title = f"{title}, p. {page}"
        url = str(citation.get("url") or "").strip()
        lines.append(f"[{number}] {title}" + (f" — {url}" if url else ""))
    return "Fuentes:\n" + "\n".join(lines) if lines else ""


def _pieces(text: str, max_chars: int) -> list[str]:
    """Frases (o bloques) que caben en un mensaje; una frase larga se parte por palabras."""
    pieces: list[str] = []
    for chunk in SENTENCE_END.split(text):
        chunk = chunk.strip()
        while len(chunk) > max_chars:
            cut = chunk.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            pieces.append(chunk[:cut].strip())
            chunk = chunk[cut:].strip()
        if chunk:
            pieces.append(chunk)
    return pieces


def split_messages(text: str, max_chars: int, max_messages: int) -> list[str]:
    messages: list[str] = []
    current = ""
    for piece in _pieces(text, max_chars):
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue
        messages.append(current)
        current = piece
    if current:
        messages.append(current)
    if len(messages) > max_messages:
        kept = messages[:max_messages]
        last = kept[-1]
        room = max_chars - len(ABBREVIATED) - 2
        kept[-1] = (last if len(last) <= room else last[:room].rstrip()) + "\n\n" + ABBREVIATED
        return kept
    return messages


def to_whatsapp(
    answer: str,
    citations: Sequence[Mapping[str, Any]] = (),
    *,
    max_chars: int = 1500,
    max_messages: int = 4,
) -> list[str]:
    """Mensajes listos para WhatsApp: cuerpo formateado y «Fuentes:» en el último mensaje."""
    body, used = number_citations(markdown_to_whatsapp(answer or ""), citations)
    sources = sources_block(used)
    if not body and not sources:
        return []
    messages = split_messages(body, max_chars, max_messages) if body else []
    if sources:
        if messages and len(messages[-1]) + len(sources) + 2 <= max_chars:
            messages[-1] = f"{messages[-1]}\n\n{sources}"
        elif len(messages) < max_messages:
            messages.append(sources[:max_chars])
        else:
            # Sin espacio: el cuerpo cede un mensaje y las fuentes van solas al final.
            messages = split_messages(body, max_chars, max(1, max_messages - 1))
            messages.append(sources[:max_chars])
    return messages
