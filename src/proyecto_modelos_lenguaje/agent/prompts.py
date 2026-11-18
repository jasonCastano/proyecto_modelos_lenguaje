"""Prompts versionados del agente (``prompts/router.md``, ``agent.md``, ``memory_summary.md``).

Reutiliza el formato de los prompts del Módulo 1 (versión en comentario, título y seis secciones
obligatorias) sin ampliar ``tasks.VALID_TASKS``, que solo cubre Q&A, resumen y FAQ.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..config import PROJECT_ROOT
from ..tasks import (
    HEADING_PATTERN,
    PROMPT_VERSION_PATTERN,
    PromptTemplate,
    TaskError,
    _parse_sections,
)

AGENT_PROMPTS = ("router", "agent", "memory_summary", "judge", "profile_extract")


def load_agent_prompt(name: str, *, project_root: Path | None = None) -> PromptTemplate:
    """Carga y valida un prompt del agente."""
    if name not in AGENT_PROMPTS:
        raise TaskError("invalid_config", f"Prompt de agente desconocido: {name}.", task=name)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    path = root / "prompts" / f"{name}.md"
    if not path.is_file():
        raise TaskError("invalid_config", f"No existe prompts/{name}.md.", task=name)
    text = path.read_text(encoding="utf-8")
    version = PROMPT_VERSION_PATTERN.search(text)
    if version is None:
        raise TaskError(
            "invalid_config", f"prompts/{name}.md no declara prompt_version.", task=name
        )
    if HEADING_PATTERN.search(text) is None:
        raise TaskError("invalid_config", f"prompts/{name}.md no tiene título.", task=name)
    return PromptTemplate(
        task=name,
        version=version.group(1),
        path=f"prompts/{name}.md",
        text=text,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        sections=_parse_sections(text, task=name),
    )


# ---------------------------------------------------------------- spec 018: Valer-IA Caña

SECTION_HEADING = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)
CONDUCT_SECTIONS = (
    "greeting",
    "greeting_named",
    "farewell",
    "farewell_offer",
    "clarify",
    "ai_disclosure",
    "off_topic",
    "third_party",
    "prompt_extraction",
    "abuse",
    "harmful",
    "advice",
    "sensitive_notice",
    "identity_confirm_name",
    "identity_ask_name",
    "identity_offer_remember",
    "identity_recognized",
    "identity_neutral",
    "identity_saved",
    "identity_declined",
    "identity_reset",
    "identity_invalid_email",
)


def load_sections(name: str, *, project_root: Path | None = None) -> tuple[str, dict[str, str]]:
    """Lee ``prompts/<name>.md`` con secciones ``## clave`` y devuelve (versión, secciones)."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    path = root / "prompts" / f"{name}.md"
    if not path.is_file():
        raise TaskError("invalid_config", f"No existe prompts/{name}.md.", task=name)
    text = path.read_text(encoding="utf-8")
    version = PROMPT_VERSION_PATTERN.search(text)
    if version is None:
        raise TaskError(
            "invalid_config", f"prompts/{name}.md no declara prompt_version.", task=name
        )
    headings = list(SECTION_HEADING.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[match.group(1)] = text[match.end() : end].strip()
    return version.group(1), sections


@lru_cache(maxsize=4)
def load_conduct(project_root: Path | None = None) -> dict[str, str]:
    """Respuestas deterministas de Valer-IA (``prompts/conduct.md``); exige todas las secciones."""
    _version, sections = load_sections("conduct", project_root=project_root)
    missing = [key for key in CONDUCT_SECTIONS if not sections.get(key)]
    if missing:
        detail = ", ".join(missing)
        raise TaskError(
            "invalid_config", f"prompts/conduct.md sin secciones: {detail}.", task="conduct"
        )
    return sections


# ---------------------------------------------------------------- spec 019: guiones de atención

CARE_PLACEHOLDERS = frozenset({"topic", "bridge", "channel", "options"})
CARE_SINGLE_VARIANT = frozenset({"crisis", "best_guess.suffix", "language.other"})
CARE_REQUIRED = (
    "opener.frustrated",
    "opener.angry",
    "opener.confused",
    "opener.concern",
    "ack.off_topic",
    "ack.advice",
    "boundary.off_topic",
    "boundary.advice",
    "boundary.pricing",
    "boundary.commitment",
    "boundary.human",
    "offer.positive",
    "bridge.default",
    "channel.website",
    "channel.ethics_line",
    "channel.data_protection",
    "close",
    "hostility.1",
    "hostility.2",
    "hostility.3",
    "rejection.rephrase",
    "rejection.related_topics",
    "rejection.official_channel",
    "complaint.help",
    "complaint.escalation",
    "clarify.intro",
    "clarify.options.default",
    "best_guess.suffix",
    "crisis",
    "decline.part",
    "truncated",
    "satisfied",
    "language.other",
)
PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_]+)\}")


@dataclass(frozen=True, slots=True)
class CareCitation:
    unit_id: str
    url: str
    title: str


@dataclass(frozen=True, slots=True)
class CarePlaybook:
    """Guiones de atención (``prompts/care.md``): variantes por sección y citas al oro."""

    version: str
    sha256: str
    variants: dict[str, tuple[str, ...]]
    citations: dict[str, CareCitation]


def _parse_care_section(key: str, body: str) -> tuple[tuple[str, ...], CareCitation | None]:
    variants: list[str] = []
    citation: CareCitation | None = None
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("- "):
            variants.append(line[2:].strip())
        elif line.startswith("cite:"):
            parts = [part.strip() for part in line[len("cite:") :].split("|")]
            if len(parts) != 3 or not all(parts):
                raise ValueError(f"care.md [{key}]: la cita debe ser «unit_id | url | título».")
            citation = CareCitation(*parts)
    for variant in variants:
        unknown = set(PLACEHOLDER_PATTERN.findall(variant)) - CARE_PLACEHOLDERS
        if unknown:
            raise ValueError(f"care.md [{key}]: placeholder no permitido {sorted(unknown)}.")
    minimum = 1 if key in CARE_SINGLE_VARIANT else 2
    if not minimum <= len(variants) <= 4:
        raise ValueError(f"care.md [{key}]: debe tener entre {minimum} y 4 variantes.")
    if (key.startswith("bridge.") or key.startswith("channel.")) and citation is None:
        raise ValueError(f"care.md [{key}]: los puentes y canales deben declarar su cita.")
    return tuple(variants), citation


@lru_cache(maxsize=4)
def load_care(project_root: Path | None = None) -> CarePlaybook:
    """Lee y valida ``prompts/care.md`` (spec 019, FR-019)."""
    version, sections = load_sections("care", project_root=project_root)
    missing = [key for key in CARE_REQUIRED if key not in sections]
    if missing:
        raise ValueError(f"care.md sin secciones: {', '.join(missing)}.")
    variants: dict[str, tuple[str, ...]] = {}
    citations: dict[str, CareCitation] = {}
    for key, body in sections.items():
        parsed, citation = _parse_care_section(key, body)
        variants[key] = parsed
        if citation is not None:
            citations[key] = citation
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    text = (root / "prompts" / "care.md").read_text(encoding="utf-8")
    return CarePlaybook(
        version=version,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        variants=variants,
        citations=citations,
    )
