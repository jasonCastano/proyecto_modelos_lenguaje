"""Entrega por frases revisadas (spec 021, ``contracts/streaming.md`` §3).

- ``SentenceSplitter``: segmentador incremental con la misma regla de oraciones que la voz
  (``voice/text.py``): abreviaturas, «No. 3», enumeradores al inicio de línea y citas al final.
- ``SentenceGate``: recibe el texto del modelo a medida que llega, revisa cada frase y decide qué
  se entrega (``deliver``), cuándo regenerar sin haber mostrado nada (``retry``) y cuándo cortar
  (``stop``). Lo entregado nunca se retira: el texto unido de ``delivered`` es siempre prefijo de la
  respuesta final.

Cada frase entregada conserva su separador inicial (espacio, salto de línea o párrafo), así que
``"".join(delivered)`` reproduce el formato del texto, incluidas las listas numeradas.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from ..voice.text import SENTENCE_END, _is_abbreviation

GateMode = Literal["conversation", "retrieval"]
DecisionKind = Literal["deliver", "retry", "stop"]

# Enumerador al inicio de línea: «1.», «2)», «**3)**»; su punto no cierra frase.
ENUMERATOR = re.compile(r"(?:^|\n)[ \t]*(?:\*\*)?\d{1,2}[.)](?:\*\*)?$")
# Etiqueta de cita que quedó después del cierre: «… azúcar. [U1]» → la etiqueta va con la frase.
LABEL_TAIL = re.compile(r"^[ \t]*(?:\[[UF]\d+\])+[.!?…]*")
LABEL = re.compile(r"\[[UF]\d+\]")
PARTIAL_LABEL = re.compile(r"^[ \t]*(?:\[[UF]\d+\])*\[(?:[UF]\d*)?$")


def separator_of(raw: str) -> str:
    """Separador que precede a una frase: párrafo, salto de línea o espacio."""
    leading = raw[: len(raw) - len(raw.lstrip())]
    if leading.count("\n") >= 2:
        return "\n\n"
    if "\n" in leading:
        return "\n"
    return " "


class SentenceSplitter:
    """Segmentador incremental de frases (FR-006: fragmentos largos sin cortar palabras)."""

    def __init__(self, max_chars: int = 220, first_chars: int = 160) -> None:
        self.max_chars = max_chars
        self.first_chars = min(first_chars, max_chars)
        self.buffer = ""
        self.emitted = 0

    def push(self, chunk: str) -> list[str]:
        """Acumula texto y devuelve las frases cerradas, cada una con su separador inicial."""
        self.buffer += chunk or ""
        return self._drain(final=False)

    def close(self) -> list[str]:
        """Devuelve todo lo pendiente al terminar el modelo."""
        out = self._drain(final=True)
        if self.buffer.strip():
            out.append(self._take(len(self.buffer)))
        self.buffer = ""
        return out

    def _take(self, end: int) -> str:
        raw = self.buffer[:end]
        self.buffer = self.buffer[end:]
        prefix = "" if self.emitted == 0 else separator_of(raw)
        self.emitted += 1
        return prefix + raw.strip()

    def _drain(self, *, final: bool) -> list[str]:
        out: list[str] = []
        while True:
            end = self._boundary(final=final)
            if end is None:
                limit = self.first_chars if self.emitted == 0 else self.max_chars
                body = self.buffer.strip()
                if len(body) <= limit or final:
                    break
                # Fragmento largo sin cierre: hasta el último espacio dentro del límite.
                start = len(self.buffer) - len(self.buffer.lstrip())
                window = self.buffer[: start + limit]
                cut = window.rfind(" ")
                if cut <= start:
                    cut = start + limit
                out.append(self._take(cut))
                continue
            if self.buffer[:end].strip():
                out.append(self._take(end))
            else:
                self.buffer = self.buffer[end:]
        return out

    def _boundary(self, *, final: bool) -> int | None:
        """Índice donde termina la primera frase completa del búfer, o ``None``."""
        source = self.buffer + (" " if final else "")
        for match in SENTENCE_END.finditer(source):
            end = match.end(1) if match.group(1) else match.end()
            candidate = source[:end]
            following = source[end:]
            if not candidate.strip():
                continue
            if match.group(1):
                if not final and not following.strip():
                    return None  # sin texto después no se sabe si es abreviatura: esperar
                if "." in match.group(1):
                    stripped = candidate.rstrip()
                    if _is_abbreviation(candidate, following) or ENUMERATOR.search(stripped):
                        continue
                if not final and PARTIAL_LABEL.match(following):
                    return None  # «[U» todavía incompleto: puede ser la cita de esta frase
                tail = LABEL_TAIL.match(following)
                if tail:
                    end += tail.end()
            return min(end, len(self.buffer))
        return None


@dataclass(slots=True)
class Decision:
    kind: DecisionKind
    text: str = ""
    index: int = -1
    issues: tuple[str, ...] = ()


CheckFn = Callable[[str, bool], Sequence[str]]


@dataclass(slots=True)
class SentenceGate:
    """Filtro de frases de un turno (``data-model.md`` §1)."""

    mode: GateMode
    check: CheckFn
    splitter: SentenceSplitter = field(default_factory=SentenceSplitter)
    max_sentences: int | None = None  # respuestas breves (FR-011)
    start_index: int = 0
    held: list[str] = field(default_factory=list)
    delivered: list[str] = field(default_factory=list)
    discarded: list[str] = field(default_factory=list)
    stopped: bool = False
    first_check_failed: bool = False
    no_evidence: bool = False

    @property
    def text(self) -> str:
        return "".join(self.delivered)

    def push(self, chunk: str) -> list[Decision]:
        decisions: list[Decision] = []
        for sentence in self.splitter.push(chunk):
            decisions.extend(self._handle(sentence))
            if self.stopped or self.first_check_failed:
                break
        return decisions

    def close(self) -> list[Decision]:
        decisions: list[Decision] = []
        if not (self.stopped or self.first_check_failed):
            for sentence in self.splitter.close():
                decisions.extend(self._handle(sentence))
                if self.stopped or self.first_check_failed:
                    break
        if self.mode == "retrieval" and self.held:
            if self.delivered:
                # Frases sin cita después de una citada: ya revisadas, cierran la respuesta.
                decisions.extend(self._deliver(self.held))
            else:
                self.no_evidence = True  # sin ninguna frase citada: evidencia insuficiente
            self.held = []
        return decisions

    def _deliver(self, sentences: Sequence[str]) -> list[Decision]:
        out: list[Decision] = []
        for sentence in sentences:
            text = sentence if self.delivered or self.start_index else sentence.lstrip()
            index = self.start_index + len(self.delivered)
            self.delivered.append(text)
            out.append(Decision("deliver", text, index))
        return out

    def _handle(self, sentence: str) -> list[Decision]:
        if self.stopped or self.first_check_failed:
            return []
        if self.max_sentences is not None and len(self.delivered) >= self.max_sentences:
            self.stopped = True
            return [Decision("stop")]
        nothing_shown = not self.delivered and not self.held
        issues = tuple(self.check(sentence.strip(), nothing_shown))
        if issues:
            self.discarded.append(issues[0])
            if self.mode == "conversation":
                if nothing_shown:
                    self.first_check_failed = True
                    return [Decision("retry", issues=issues)]
                self.stopped = True
                return [Decision("stop", issues=issues)]
            return []  # búsqueda: la frase se descarta y la respuesta sigue (FR-005)
        if self.mode == "retrieval" and not LABEL.search(sentence):
            self.held.append(sentence)
            return []
        pending = [*self.held, sentence]
        self.held = []
        return self._deliver(pending)


def split_all(text: str, max_chars: int = 220, first_chars: int = 160) -> list[str]:
    """Frases de un texto completo, con separadores (respuestas fijas y respaldo)."""
    splitter = SentenceSplitter(max_chars, first_chars)
    return [*splitter.push(text), *splitter.close()]
