"""Herramientas de entidades del catálogo (spec 024, herramientas 7 y 8).

Leen ``data/gold/entities.jsonl`` (filiales, empresa, marcas y certificaciones). Cada entidad se
entrega como hecho ``F#`` cuya evidencia es una unidad de oro que la menciona (``unit_id``), con
la URL de esa unidad como cita; el texto de la unidad va en el hecho para que el modelo y la
revisión por frase vean la evidencia.

El oro no trae el país de cada filial. ``BUSINESS_LOCATIONS`` lo fija a mano, con una unidad de
oro que lo afirma literalmente (una prueba lo verifica sobre ``knowledge_units.jsonl``); así el
filtro por país nunca depende de un dato inventado.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .catalog import ToolContext, ToolSpec
from .series import default_series
from .structured import Citation, StructuredFact, normalize
from .tools_knowledge import gold_dir
from .tools_series import cite_facts

EVIDENCE_RADIUS = 220
BUSINESS_TYPES = ("company", "subsidiary")
KIND_LABELS = {"certification": "certificación", "brand": "marca"}


@dataclass(frozen=True, slots=True)
class Location:
    country: str
    place: str
    unit_id: str  # unidad de oro que afirma la ubicación


# Nombre canónico (entities.jsonl) → ubicación con su evidencia en el oro.
BUSINESS_LOCATIONS: dict[str, Location] = {
    "Manuelita": Location(
        "Colombia", "Cali, Valle del Cauca (sede corporativa)", "unit_e86a6fb077449b90"
    ),
    "Manuelita Azúcar y Energía": Location(
        "Colombia", "Palmira, Valle del Cauca", "unit_27c34db39788d197"
    ),
    "Manuelita Aceites y Energía": Location(
        "Colombia", "San Carlos de Guaroa, Meta", "unit_9db6a73445595cbe"
    ),
    "Palmar de Altamira": Location("Colombia", "Orocué, Casanare", "unit_0259bdce79a2e521"),
    "Océanos": Location("Colombia", "Cartagena, Bolívar", "unit_401abdc1d567d126"),
    "Agroindustrial Laredo": Location("Perú", "Trujillo", "unit_0259bdce79a2e521"),
    "Mejillones América": Location("Chile", "", "unit_63a63973d2222f5f"),
}
_LOCATIONS = {normalize(name): location for name, location in BUSINESS_LOCATIONS.items()}


@lru_cache(maxsize=4)
def _load_entities(path: str) -> tuple[dict[str, Any], ...]:
    source = Path(path)
    if not source.is_file():
        return ()
    return tuple(
        json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line
    )


def load_entities() -> tuple[dict[str, Any], ...]:
    """Entidades del oro (``entities.jsonl``), una carga por ruta."""
    return _load_entities(str(gold_dir() / "entities.jsonl"))


def _snippet(text: str, names: Sequence[str]) -> str:
    """Ventana del texto alrededor de la primera mención de la entidad."""
    flat = " ".join(text.split())
    lowered = normalize(flat)
    for name in names:
        position = lowered.find(normalize(name))
        if position >= 0:
            start = max(0, position - EVIDENCE_RADIUS // 2)
            return flat[start : position + EVIDENCE_RADIUS].strip()
    return flat[:EVIDENCE_RADIUS]


def _evidence(
    ctx: ToolContext, entity: dict[str, Any], preferred: str | None = None
) -> tuple[str, str, tuple[Citation, ...]]:
    """(unit_id, texto de evidencia, citas) de una unidad que menciona la entidad."""
    names = [entity["canonical_name"], *entity.get("aliases", [])]
    units = ctx.retriever.units_by_id if ctx.retriever is not None else {}
    candidates = [preferred] if preferred else []
    candidates += list(entity.get("unit_ids", []))
    for unit_id in candidates:
        unit = units.get(unit_id)
        if unit is None:
            continue
        text = normalize(unit.text)
        if unit_id == preferred or any(normalize(name) in text for name in names):
            title = unit.title or unit.topic_title
            return unit_id, _snippet(unit.text, names), (Citation(url=unit.url, title=title),)
    fallback = preferred or next(iter(entity.get("unit_ids", [])), "")
    return fallback, "", ()


def _platforms(name: str) -> list[str]:
    """Negocios de las series anuales cuyo alcance menciona la filial."""
    table = default_series()
    if table is None:
        return []
    wanted = normalize(name)
    found: list[str] = []
    for row in table.rows:
        if wanted in normalize(row.scope) and row.business not in found:
            found.append(row.business)
    return found


def _entity_fact(
    entity: dict[str, Any], attribute: str, value: str, detail: str, evidence: tuple
) -> StructuredFact:
    unit_id, text, citations = evidence
    aliases = ", ".join(entity.get("aliases", []))
    snippet = f"{entity['canonical_name']}: {detail}" + (f" (alias: {aliases})" if aliases else "")
    if text:
        snippet += f". Evidencia: «{text}»"
    return StructuredFact(
        fact_id=f"entity_{entity['entity_id']}",
        subject_id=entity["entity_id"],
        subject_label=entity["canonical_name"],
        attribute=attribute,
        value=value,
        year=None,
        unit_id=unit_id,
        snippet=snippet,
        citations=citations,
    )


# ---------------------------------------------------------------- 7. list_business_units


class ListBusinessUnitsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str | None = Field(
        default=None,
        min_length=3,
        max_length=40,
        description="País para filtrar (Colombia, Perú, Chile…). Vacío: todas.",
    )


def list_business_units_impl(ctx: ToolContext, args: ListBusinessUnitsArgs) -> str:
    ctx.trace.calls += 1
    entities = [e for e in load_entities() if e.get("entity_type") in BUSINESS_TYPES]
    if not entities:
        return "Las entidades del oro no están disponibles."
    wanted = normalize(args.country) if args.country else ""
    facts: list[StructuredFact] = []
    for entity in sorted(entities, key=lambda e: (e["entity_type"], e["canonical_name"])):
        location = _LOCATIONS.get(normalize(entity["canonical_name"]))
        if wanted and (location is None or wanted not in normalize(location.country)):
            continue
        kind = "empresa matriz" if entity["entity_type"] == "company" else "filial"
        detail = kind
        if location is not None:
            place = f"{location.place}, " if location.place else ""
            detail += f" en {place}{location.country}"
        platforms = _platforms(entity["canonical_name"])
        if platforms:
            detail += f"; plataforma en las series anuales: {', '.join(platforms)}"
        evidence = _evidence(ctx, entity, location.unit_id if location else None)
        country = location.country if location else "sin dato"
        facts.append(_entity_fact(entity, "unidad de negocio (país)", country, detail, evidence))
    if not facts:
        return f"Sin resultados: no hay unidades de negocio registradas en «{args.country}»."
    header = f"Unidades de negocio en el oro: {len(facts)}."
    return f"{header}\n{cite_facts(ctx, facts)}"


# ------------------------------------------------------------- 8. list_company_entities


class ListCompanyEntitiesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["certification", "brand"] = Field(
        description="certification (certificaciones) o brand (marcas)."
    )


def list_company_entities_impl(ctx: ToolContext, args: ListCompanyEntitiesArgs) -> str:
    ctx.trace.calls += 1
    entities = sorted(
        (e for e in load_entities() if e.get("entity_type") == args.kind),
        key=lambda e: e["canonical_name"],
    )
    label = KIND_LABELS[args.kind]
    if not entities:
        return f"Sin resultados: no hay entidades de tipo {label} en el oro."
    facts = [
        _entity_fact(entity, label, entity["canonical_name"], label, _evidence(ctx, entity))
        for entity in entities
    ]
    names = ", ".join(entity["canonical_name"] for entity in entities)
    header = f"{len(facts)} entidades de tipo {label} en el oro: {names}."
    return f"{header}\n{cite_facts(ctx, facts)}"


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        7,
        "list_business_units",
        "Lista la empresa y las filiales o unidades de negocio de Manuelita con su país y "
        "plataforma, opcionalmente filtradas por país; cada una con su evidencia [F#].",
        ListBusinessUnitsArgs,
        "read",
        frozenset({"structured"}),
        "gold/entities.jsonl (subsidiary, company) + series anuales",
        list_business_units_impl,
    ),
    ToolSpec(
        8,
        "list_company_entities",
        "Lista las certificaciones o las marcas de Manuelita registradas en el oro, cada una "
        "con un fragmento que la menciona como evidencia [F#].",
        ListCompanyEntitiesArgs,
        "read",
        frozenset({"structured"}),
        "gold/entities.jsonl",
        list_company_entities_impl,
    ),
)
