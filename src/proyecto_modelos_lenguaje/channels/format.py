"""Respuesta de Valer-IA en el formato de WhatsApp (spec 024 R13, spec 029 US2/US4, channel-format).

- Markdown → WhatsApp: ``**x**`` → ``*x*``, títulos → negrita, tablas → líneas con «•».
- Citas ``[U3]``/``[F1]`` → ``[1]``/``[2]`` por orden de aparición; la misma fuente (URL + página)
  recibe un solo número y las citas repetidas contiguas se colapsan.
- Bloque de fuentes al final, en el idioma del turno, una línea fija por fuente:
  ``[n] Título, p. X — URL`` con títulos limpios de una línea (≤ 80 caracteres).
- Corte por frases a ``max_chars`` y como mucho ``max_messages`` mensajes; conserva los saltos de
  párrafo, nunca parte una cita ni el bloque de fuentes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

# Spec 025: [S#] son procedimientos SINTÉTICOS; se listan aparte de las fuentes públicas.
LABEL = re.compile(r"\[(?P<labels>[UFS]\d+(?:\s*,\s*[UFS]\d+)*)\]")
BOLD = re.compile(r"\*\*(.+?)\*\*")
UNDERSCORE_BOLD = re.compile(r"__(.+?)__")
HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
BULLET = re.compile(r"^[ \t]*[-*+][ \t]+", re.MULTILINE)
TABLE_RULE = re.compile(r"^[ \t]*\|?[ \t]*:?-{2,}.*$", re.MULTILINE)
# Separadores entre piezas: fin de frase o párrafo (el separador se conserva al volver a unir).
PIECE_SPLIT = re.compile(r"((?<=[.!?…])\s+|[ \t]*\n[ \t]*\n\s*)")
REPEATED_CITATION = re.compile(r"\[(\d+)\](?:\s*\[\1\])+")
TITLE_CHARS = 80

TEXTS: dict[str, dict[str, str]] = {
    "es": {
        "sources": "Fuentes:",
        "synthetic": "Fuentes sintéticas (demostración):",
        "abbreviated": "(respuesta abreviada; pídeme más detalle)",
        "source": "Fuente",
    },
    "en": {
        "sources": "Sources:",
        "synthetic": "Synthetic sources (demo):",
        "abbreviated": "(shortened answer; ask me for more detail)",
        "source": "Source",
    },
}
ABBREVIATED = TEXTS["es"]["abbreviated"]
SYNTHETIC_TITLE = TEXTS["es"]["synthetic"]

# Títulos sucios: encabezados de índice y numeraciones o viñetas sueltas (spec 029, R4).
INDEX_HEADING = re.compile(
    r"(?i)^(?:índice|indice|contenidos?|tabla de contenidos?|table of contents)\W*$"
)
LOOSE_NUMBERING = re.compile(r"^[\s\d.,;:()•·*#\-–—]*$")
FILE_EXTENSION = re.compile(r"\.(?:pdf|docx?|xlsx?|pptx?|html?)$", re.IGNORECASE)
NOISE_TOKENS = {
    "digital", "digitala", "alta", "baja", "f", "final", "web", "dig", "v", "def", "vf", "vfbaja",
}  # fmt: skip
YEAR = re.compile(r"^(?:19|20)\d{2}$")
CAMEL = re.compile(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])|(?<=[A-Za-záéíóúñ])(?=\d)")
# Títulos de metadatos de archivo («Informe_Sostenibilidad-2021», «Portada-acercade-carta», «01 …»).
WEAK_TITLE = re.compile(r"_|[A-Za-záéíóúñ]-[A-Za-záéíóúñ]|^\d")
TITLE_PAGE = re.compile(r",\s*p\.\s*(?P<page>[\w-]+)\s*$")


def _texts(language: str) -> dict[str, str]:
    return TEXTS.get(language, TEXTS["es"])


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


# --- títulos de las fuentes --------------------------------------------------------------------


def _humanize(slug: str) -> str:
    """``Informe-de-Sostenibilidad-Manuelita-2013-2014_digitalA`` → ``Informe de … 2013-2014``."""
    raw = [t for t in re.split(r"[_\-\s.+]+", slug) if t and t.lower() not in NOISE_TOKENS]
    tokens = [t for token in raw for t in CAMEL.sub(" ", token).split()]
    words: list[str] = []
    for token in tokens:
        if words and YEAR.match(token) and YEAR.match(words[-1].split("-")[-1]):
            words[-1] = f"{words[-1]}-{token}"
        else:
            words.append(token)
    return " ".join(words)


def _document_name(url: str) -> str:
    """Nombre legible del archivo del enlace (``""`` si el enlace no es un archivo)."""
    name = PurePosixPath(unquote(urlparse(url).path)).name
    if not FILE_EXTENSION.search(name):
        return ""
    return _humanize(FILE_EXTENSION.sub("", name))


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _shorten(title: str) -> str:
    return title if len(title) <= TITLE_CHARS else title[: TITLE_CHARS - 1].rstrip() + "…"


def clean_title(title: str | None, url: str | None = None) -> str:
    """Título de una línea, sin «Índice» ni numeraciones sueltas; respaldo: archivo y dominio."""
    url = (url or "").strip()
    dirty = False
    kept: list[str] = []
    for raw in (title or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if INDEX_HEADING.match(line) or LOOSE_NUMBERING.match(line):
            dirty = True
            continue
        kept.append(line)
    text = re.sub(r"\s+", " ", " ".join(kept)).strip()
    slug_like = bool(text) and (" " not in text or bool(WEAK_TITLE.search(text)))
    if dirty or not text or slug_like:
        document = _document_name(url) if url else ""
        if document:
            return _shorten(document)
        if slug_like:
            return _shorten(_humanize(text))
        if not text:
            return _shorten(_domain(url)) if url else ""
    return _shorten(text)


# --- citas y bloque de fuentes ---------------------------------------------------------------


def _source_key(citation: Mapping[str, Any], label: str) -> tuple[str, str]:
    url = str(citation.get("url") or "").strip().lower().rstrip("/")
    page = citation.get("page") or citation.get("page_start") or ""
    if not page:
        found = TITLE_PAGE.search(str(citation.get("title") or ""))
        page = found.group("page") if found else ""
    return (url, str(page)) if url else (f"label:{label}", "")


def number_citations(
    text: str, citations: Sequence[Mapping[str, Any]]
) -> tuple[str, list[tuple[int, Mapping[str, Any]]]]:
    """Renumera por orden de aparición; la misma fuente (URL + página) comparte número."""
    by_label = {str(c.get("label")): c for c in citations if c.get("label")}
    by_key: dict[tuple[str, str], int] = {}
    used: list[tuple[int, Mapping[str, Any]]] = []

    def number_of(label: str) -> int:
        citation = by_label.get(label, {"label": label})
        key = _source_key(citation, label)
        if key not in by_key:
            by_key[key] = len(by_key) + 1
            used.append((by_key[key], citation))
        return by_key[key]

    def replace(match: re.Match[str]) -> str:
        numbers: list[int] = []
        for label in re.split(r"\s*,\s*", match.group("labels")):
            number = number_of(label)
            if number not in numbers:
                numbers.append(number)
        return "".join(f"[{n}]" for n in numbers)

    renumbered = REPEATED_CITATION.sub(r"[\1]", LABEL.sub(replace, text))
    return renumbered, used


def _sources_lines(
    title_line: str, used: Sequence[tuple[int, Mapping[str, Any]]], fallback: str
) -> str:
    lines = []
    entries = []
    for number, citation in used:
        url = str(citation.get("url") or "").strip()
        raw = str(citation.get("title") or "")
        page = citation.get("page") or citation.get("page_start")
        found = TITLE_PAGE.search(raw)
        if found:  # algunas fuentes ya traen «, p. N» en el título
            raw = raw[: found.start()]
            page = page or found.group("page")
        entries.append((number, url, clean_title(raw, url) or fallback, page))
    repeated = _repeated_titles(entries)
    for number, url, title, page in entries:
        if title in repeated:
            title = _page_name(url) or title
        if page:
            title = f"{title}, p. {page}"
        lines.append(f"[{number}] {title}" + (f" — {url}" if url else ""))
    return f"{title_line}\n" + "\n".join(lines) if lines else ""


def _repeated_titles(entries: Sequence[tuple[int, str, str, Any]]) -> set[str]:
    """Títulos genéricos («Conoce las últimas noticias…») que comparten enlaces distintos."""
    urls: dict[str, set[str]] = {}
    for _number, url, title, _page in entries:
        urls.setdefault(title, set()).add(url)
    return {title for title, links in urls.items() if len(links) > 1}


def _page_name(url: str) -> str:
    """Nombre legible del final del enlace (``manuelita-mas-azucar`` → «Manuelita mas azucar»)."""
    last = PurePosixPath(unquote(urlparse(url).path)).name
    name = _humanize(FILE_EXTENSION.sub("", last)) if last else ""
    return _shorten(name[:1].upper() + name[1:]) if name else ""


def sources_block(used: Sequence[tuple[int, Mapping[str, Any]]], language: str = "es") -> str:
    texts = _texts(language)
    public = [item for item in used if item[1].get("kind") != "synthetic"]
    synthetic = [item for item in used if item[1].get("kind") == "synthetic"]
    blocks = [
        _sources_lines(texts["sources"], public, texts["source"]),
        _sources_lines(texts["synthetic"], synthetic, texts["source"]),
    ]
    return "\n\n".join(block for block in blocks if block)


# --- división en mensajes --------------------------------------------------------------------


def _separator(whitespace: str) -> str:
    newlines = whitespace.count("\n")
    return "\n\n" if newlines >= 2 else "\n" if newlines == 1 else " "


def _pieces(text: str, max_chars: int) -> list[tuple[str, str]]:
    """Piezas ``(separador previo, texto)`` que caben en un mensaje; las largas van por palabras."""
    parts = PIECE_SPLIT.split(text)
    pieces: list[tuple[str, str]] = []
    separator = " "
    for index, part in enumerate(parts):
        if index % 2:
            separator = _separator(part)
            continue
        chunk = part.strip()
        while len(chunk) > max_chars:
            cut = chunk.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            pieces.append((separator, chunk[:cut].strip()))
            separator = " "
            chunk = chunk[cut:].strip()
        if chunk:
            pieces.append((separator, chunk))
    return pieces


def split_messages(text: str, max_chars: int, max_messages: int, language: str = "es") -> list[str]:
    messages: list[str] = []
    current = ""
    for separator, piece in _pieces(text, max_chars):
        candidate = f"{current}{separator}{piece}" if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue
        messages.append(current)
        current = piece
    if current:
        messages.append(current)
    if len(messages) > max_messages:
        abbreviated = _texts(language)["abbreviated"]
        kept = messages[:max_messages]
        last = kept[-1]
        room = max_chars - len(abbreviated) - 2
        kept[-1] = (last if len(last) <= room else last[:room].rstrip()) + "\n\n" + abbreviated
        return kept
    return messages


def _fit_sources(sources: str, max_chars: int) -> str:
    """El bloque de fuentes nunca se parte a mitad de línea: entra una línea entera o nada."""
    if len(sources) <= max_chars:
        return sources
    out = ""
    for line in sources.splitlines():
        candidate = f"{out}\n{line}" if out else line
        if len(candidate) > max_chars:
            break
        out = candidate
    return out


def sources_only(
    answer: str,
    citations: Sequence[Mapping[str, Any]] = (),
    *,
    language: str = "es",
    max_chars: int = 1500,
) -> list[str]:
    """Spec 030: solo el bloque de fuentes, para acompañar una nota de voz sin repetir la respuesta.

    Usa la misma numeración y deduplicación que ``to_whatsapp``. Si no cabe en un mensaje, sigue
    en el siguiente con líneas completas y sin repetir el encabezado. Sin fuentes devuelve ``[]``.
    """
    _body, used = number_citations(markdown_to_whatsapp(answer or ""), citations)
    block = sources_block(used, language)
    if not block:
        return []
    messages: list[str] = []
    current = ""
    for line in block.split("\n"):
        line = line if len(line) <= max_chars else line[: max_chars - 1] + "…"
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_chars:
            current = candidate
            continue
        messages.append(current.strip())
        current = line
    if current.strip():
        messages.append(current.strip())
    return messages


def to_whatsapp(
    answer: str,
    citations: Sequence[Mapping[str, Any]] = (),
    *,
    max_chars: int = 1500,
    max_messages: int = 4,
    language: str = "es",
) -> list[str]:
    """Mensajes listos para WhatsApp: cuerpo formateado y fuentes en el último mensaje."""
    body, used = number_citations(markdown_to_whatsapp(answer or ""), citations)
    sources = _fit_sources(sources_block(used, language), max_chars)
    if not body and not sources:
        return []
    messages = split_messages(body, max_chars, max_messages, language) if body else []
    if sources:
        if messages and len(messages[-1]) + len(sources) + 2 <= max_chars:
            messages[-1] = f"{messages[-1]}\n\n{sources}"
        elif len(messages) < max_messages:
            messages.append(sources)
        else:
            # Sin espacio: el cuerpo cede un mensaje y las fuentes van solas al final.
            messages = split_messages(body, max_chars, max(1, max_messages - 1), language)
            messages.append(sources)
    return messages
