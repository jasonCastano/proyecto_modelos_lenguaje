"""Estilo caleño de Valer-IA (spec 036, ``contracts/style-rules.md``).

Léxico versionado en ``config/caleno.toml``: expresiones aprobadas de Santiago de Cali, con su
significado y los niveles en que se permiten, y expresiones vetadas (groserías, modismos de otras
regiones y voseo). Este módulo es puro y sin red:

- ``level_for`` fija el nivel del turno (``off``, ``formal``, ``neutral`` o ``informal``);
- ``suggest`` elige las expresiones sugeridas sin repetir las recientes;
- ``render_block`` arma el bloque ``<estilo>`` de los prompts;
- ``find_expressions`` y ``find_banned`` revisan una respuesta (los usa ``review.py``).
"""

from __future__ import annotations

import hashlib
import logging
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from ..config import PROJECT_ROOT
from .structured import normalize

LOGGER = logging.getLogger(__name__)
CALENO_FILE = PROJECT_ROOT / "config" / "caleno.toml"
StyleLevel = Literal["off", "formal", "neutral", "informal"]
LEVELS = frozenset({"informal", "neutral", "formal"})
MatchKind = Literal["phrase", "interjection", "closing", "voseo"]
OFF_SENTIMENTS = frozenset({"frustrated", "angry", "distressed"})
OFF_ACTS = frozenset({"complaint"})
OFF_REASONS = frozenset({"crisis", "harmful", "abuse", "third_party", "prompt_extraction"})
# Malestar que el sentimiento puede dejar en «neutral»: sin estilo (FR-005, conservador).
LOW_MOOD = re.compile(
    r"\b(me siento (muy )?(mal|triste|fatal|horrible|solo|sola)|estoy (muy )?(triste|mal|"
    r"deprimid[oa]|angustiad[oa]|preocupad[oa])|dia (terrible|horrible|fatal|pesimo)|"
    r"(me|estoy) (duele|enferm[oa])|perdi (a|mi)|fallecio|murio|lloro|llorando|"
    r"(estoy|me tiene|me siento) (muy )?(molest[oa]|furios[oa]|indignad[oa]|hart[oa])|"
    r"(esto|esta pagina|eso) no (me )?sirve|pesimo (servicio|servicio al cliente))\b"
)
MIN_APPROVED = 8
MIN_FORMAL = 3


@dataclass(frozen=True)
class Expression:
    """Expresión caleña aprobada (``data-model.md`` §1)."""

    text: str
    meaning: str
    levels: frozenset[str]
    spoken: bool
    example: str
    match: MatchKind = "phrase"
    suggested: bool = True  # False: se permite, pero no se sugiere

    @property
    def key(self) -> str:
        return normalize(self.text)


@dataclass(frozen=True)
class Lexicon:
    approved: tuple[Expression, ...]
    banned: tuple[tuple[str, str, str], ...]  # (texto, motivo, tipo de coincidencia)
    max_written: int = 1
    max_spoken: int = 2
    suggestions: int = 3
    memory: int = 3
    opt_out: tuple[str, ...] = ()
    formal_markers: tuple[str, ...] = ()
    enabled: bool = True
    sha256: str = ""

    def by_key(self) -> dict[str, Expression]:
        return {expression.key: expression for expression in self.approved}


DISABLED = Lexicon(approved=(), banned=(), enabled=False)


# ---------------------------------------------------------------- carga y validación


def _validate(data: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    approved = list(data.get("approved") or [])
    banned = list(data.get("banned") or [])
    keys = [normalize(str(row.get("text") or "")) for row in [*approved, *banned]]
    if any(not key for key in keys):
        errors.append("hay expresiones sin texto")
    if len(set(keys)) != len(keys):
        errors.append("hay textos repetidos entre aprobadas y vetadas")
    if len(approved) < MIN_APPROVED:
        errors.append(f"se necesitan al menos {MIN_APPROVED} expresiones aprobadas")
    for row in approved:
        levels = set(row.get("levels") or [])
        if not levels or not levels <= LEVELS:
            errors.append(f"niveles inválidos en «{row.get('text')}»")
        if str(row.get("match") or "phrase") not in {"phrase", "interjection", "closing"}:
            errors.append(f"tipo de coincidencia inválido en «{row.get('text')}»")
    if sum("formal" in (row.get("levels") or []) for row in approved) < MIN_FORMAL:
        errors.append(f"se necesitan al menos {MIN_FORMAL} expresiones de nivel formal")
    return errors


def parse_lexicon(raw: bytes) -> Lexicon:
    """Léxico desde el TOML; un archivo inválido deja el estilo apagado (nunca lanza error)."""
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        LOGGER.warning("caleno.toml inválido: %s; estilo caleño apagado", exc)
        return DISABLED
    errors = _validate(data)
    if errors:
        LOGGER.warning("caleno.toml inválido: %s; estilo caleño apagado", "; ".join(errors))
        return DISABLED
    settings = data.get("style") or {}
    approved = tuple(
        Expression(
            text=str(row["text"]),
            meaning=str(row.get("meaning") or ""),
            levels=frozenset(row["levels"]),
            spoken=bool(row.get("spoken", True)),
            example=str(row.get("example") or ""),
            match=str(row.get("match") or "phrase"),  # type: ignore[arg-type]
            suggested=bool(row.get("suggest", True)),
        )
        for row in data["approved"]
    )
    banned = tuple(
        (str(row["text"]), str(row.get("reason") or ""), str(row.get("match") or "phrase"))
        for row in data.get("banned") or []
    )
    return Lexicon(
        approved=approved,
        banned=banned,
        max_written=int(settings.get("max_written", 1)),
        max_spoken=int(settings.get("max_spoken", 2)),
        suggestions=int(settings.get("suggestions", 3)),
        memory=int(settings.get("memory", 3)),
        opt_out=tuple(normalize(str(p)) for p in settings.get("opt_out") or []),
        formal_markers=tuple(normalize(str(p)) for p in settings.get("formal_markers") or []),
        enabled=bool(settings.get("enabled", True)),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


@lru_cache(maxsize=4)
def load_lexicon(path: Path = CALENO_FILE) -> Lexicon:
    """``config/caleno.toml`` validado; si falta o es inválido, el estilo queda apagado."""
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        LOGGER.warning("no se pudo leer %s: %s; estilo caleño apagado", path, exc)
        return DISABLED
    return parse_lexicon(raw)


# ---------------------------------------------------------------- coincidencias

SEPARATOR = r"[\s,;:¡!¿?.…]+"
END = r"[.!?…]"


def _phrase(key: str) -> str:
    words = [re.escape(word) for word in re.findall(r"[a-z0-9]+", key)]
    return r"(?<![a-z0-9])" + SEPARATOR.join(words) + r"(?![a-z0-9])"


@lru_cache(maxsize=64)
def _pattern(key: str, kind: str) -> re.Pattern[str]:
    if kind == "interjection":
        # «¡Ve, …», «Ve! …» al inicio de una frase, o entre comas: «…, ve.», «hola, ve, qué…».
        word = re.escape(key)
        return re.compile(
            rf"(?:(?:^|{END}\s*|[¡¿]\s*){word}\s*[,!]|,\s*{word}\s*(?:[,!]|{END}|$))", re.M
        )
    if kind == "closing":
        return re.compile(rf"(?<![a-z0-9]){re.escape(key)}\s*(?:{END}|$)", re.M)
    if kind == "voseo":
        return re.compile(rf"(?<![\wáéíóúñ]){re.escape(key)}(?![\wáéíóúñ])")
    return re.compile(_phrase(key))


def _spans(text: str, expression: Expression) -> list[tuple[int, int]]:
    pattern = _pattern(expression.key, expression.match)
    return [match.span() for match in pattern.finditer(text)]


def _original(text: str, normalized: str, span: tuple[int, int], fallback: str) -> str:
    """Fragmento de ``text`` del tramo normalizado (la normalización conserva el largo
    en el español habitual; si no, se devuelve ``fallback``)."""
    if len(text) != len(normalized):
        return fallback
    return text[span[0] : span[1]].strip(" ,;:¡!¿?.…")


def expression_hits(text: str, lexicon: Lexicon | None = None) -> list[tuple[str, str]]:
    """``(expresión aprobada, fragmento original)`` en orden de aparición (sin tildes al comparar).

    Las más largas se reconocen primero y ocupan su tramo: en «qué bueno, ve» no se cuenta además
    «ve», ni «pues» dentro de «listo pues».
    """
    lexicon = lexicon or load_lexicon()
    if not lexicon.enabled or not text:
        return []
    normalized = normalize(text)
    taken: list[tuple[int, int]] = []
    found: list[tuple[int, str, str]] = []
    for expression in sorted(lexicon.approved, key=lambda e: -len(e.key)):
        for start, end in _spans(normalized, expression):
            if any(start < right and left < end for left, right in taken):
                continue
            taken.append((start, end))
            fragment = _original(text, normalized, (start, end), expression.text)
            found.append((start, expression.text, fragment))
    return [(name, fragment) for _start, name, fragment in sorted(found)]


def find_expressions(text: str, lexicon: Lexicon | None = None) -> list[str]:
    """Expresiones aprobadas presentes en ``text``, en orden de aparición."""
    return [name for name, _fragment in expression_hits(text, lexicon)]


def banned_hits(text: str, lexicon: Lexicon | None = None) -> list[tuple[str, str]]:
    """``(expresión vetada, fragmento original)``; el voseo exige la tilde («mirá», no «mira»)."""
    lexicon = lexicon or load_lexicon()
    if not text or not lexicon.banned:
        return []
    normalized = normalize(text)
    lowered = text.lower()
    found: list[tuple[str, str]] = []
    for word, _reason, kind in lexicon.banned:
        if kind == "voseo":
            hit = _pattern(word.lower(), "voseo").search(lowered)
            if hit and len(lowered) == len(text):
                found.append((word, text[hit.start() : hit.end()]))
            elif hit:
                found.append((word, word))
        else:
            hit = _pattern(normalize(word), "phrase").search(normalized)
            if hit:
                found.append((word, _original(text, normalized, hit.span(), word)))
    return found


def find_banned(text: str, lexicon: Lexicon | None = None) -> list[str]:
    """Expresiones vetadas en ``text``."""
    return [word for word, _fragment in banned_hits(text, lexicon)]


def wants_plain(message: str, lexicon: Lexicon | None = None) -> bool:
    """¿La persona pidió hablar sin acento ni modismos? (FR-009)."""
    lexicon = lexicon or load_lexicon()
    normalized = normalize(message)
    return any(re.search(_phrase(phrase), normalized) for phrase in lexicon.opt_out if phrase)


def named_expressions(message: str, lexicon: Lexicon | None = None) -> list[str]:
    """Expresiones que el mensaje nombra («¿qué significa "ve"?»), sin exigir la forma de uso."""
    lexicon = lexicon or load_lexicon()
    normalized = normalize(message)
    return [e.text for e in lexicon.approved if re.search(_phrase(e.key), normalized)]


# ---------------------------------------------------------------- nivel y sugerencias


def _formal(message: str, lexicon: Lexicon) -> bool:
    normalized = normalize(message)
    return any(re.search(_phrase(marker), normalized) for marker in lexicon.formal_markers)


def level_for(
    plan: Any,
    memory: Mapping[str, Any] | None,
    message: str,
    lexicon: Lexicon | None = None,
) -> StyleLevel:
    """Nivel de estilo del turno (``research.md`` R3, ``data-model.md`` §2)."""
    lexicon = lexicon or load_lexicon()
    memory = memory or {}
    if not lexicon.enabled or plan is None:
        return "off"
    if getattr(plan, "language", "es") != "es":
        return "off"
    if memory.get("style_opt_out") or wants_plain(message, lexicon):
        return "off"
    if getattr(plan, "sentiment", "neutral") in OFF_SENTIMENTS:
        return "off"
    if LOW_MOOD.search(normalize(message)):
        return "off"
    if getattr(plan, "act", "") in OFF_ACTS or getattr(plan, "reason", None) in OFF_REASONS:
        return "off"
    if _formal(message, lexicon):
        return "formal"
    if getattr(plan, "register", "formal") == "informal":
        return "informal"
    return "neutral"


def suggest(
    level: str,
    recent: Sequence[str] = (),
    seed: int = 0,
    *,
    spoken: bool = False,
    lexicon: Lexicon | None = None,
) -> tuple[str, ...]:
    """Expresiones permitidas en el nivel, sin las recientes, rotando con la semilla (R4)."""
    lexicon = lexicon or load_lexicon()
    if level == "off" or not lexicon.enabled:
        return ()
    used = {normalize(item) for item in recent}
    options = [
        e.text
        for e in lexicon.approved
        if e.suggested and level in e.levels and (e.spoken or not spoken) and e.key not in used
    ]
    if not options:
        return ()
    start = seed % len(options)
    rotated = options[start:] + options[:start]
    return tuple(rotated[: lexicon.suggestions])


def glossary(names: Sequence[str], lexicon: Lexicon | None = None) -> list[str]:
    """«expresión = significado» para las expresiones dadas (FR-010)."""
    lexicon = lexicon or load_lexicon()
    by_key = lexicon.by_key()
    lines: list[str] = []
    for name in names:
        expression = by_key.get(normalize(name))
        if expression and expression.meaning:
            line = f"«{expression.text}» = {expression.meaning}"
            if line not in lines:
                lines.append(line)
    return lines


def render_block(
    level: str,
    hints: Sequence[str] = (),
    *,
    spoken: bool = False,
    glossary_lines: Sequence[str] = (),
    plain_request: bool = False,
    lexicon: Lexicon | None = None,
) -> str:
    """Bloque ``<estilo>`` para los prompts (``contracts/style-rules.md`` §3); vacío con ``off``.

    Con ``plain_request`` (la persona acaba de pedir hablar normal) el bloque solo pide confirmarlo.
    """
    lexicon = lexicon or load_lexicon()
    if plain_request:
        return (
            "<estilo>\nnivel: off\nla persona pidió hablar sin modismos: confírmalo en media "
            "frase y responde en español neutro, sin expresiones caleñas\n</estilo>"
        )
    if level == "off" or not lexicon.enabled:
        return ""
    limit = lexicon.max_spoken if spoken else lexicon.max_written
    amount = "como máximo dos" if limit == 2 else "como máximo una"
    lines = [
        f"nivel: {level}",
        "acento: caleño (Santiago de Cali), profesional y cordial; tuteo, nunca voseo",
    ]
    if hints:
        listed = ", ".join(f"«{hint}»" for hint in hints)
        lines.append(f"expresiones sugeridas ({amount}, solo si encaja): {listed}")
    else:
        lines.append(f"expresiones caleñas: {amount}, solo si encaja")
    lines.append("dónde: al inicio o al cierre; nunca dentro de una cifra, una cita o un nombre")
    lines.append(
        "prohibido: groserías, modismos de otras regiones («parce»), voseo («vos», «mirá»)"
    )
    if level == "formal":
        lines.append(
            "registro formal: solo cortesías suaves, como «con mucho gusto» o «a la orden»"
        )
    if spoken:
        lines.append("ritmo: frases cortas y cálidas, como se habla en Cali")
    if glossary_lines:
        lines.append("glosario: " + "; ".join(glossary_lines))
    return "<estilo>\n" + "\n".join(lines) + "\n</estilo>"
