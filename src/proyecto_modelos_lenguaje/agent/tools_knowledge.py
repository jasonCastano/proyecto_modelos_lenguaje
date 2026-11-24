"""Herramientas de conocimiento del catálogo (spec 024, herramientas 6 y 10 a 13).

Todas leen el oro ya cargado por el recuperador híbrido (``ctx.retriever``) y registran cada
unidad que entregan en la traza del turno como fragmento ``U#``, igual que ``search_documents``;
así el validador de citas del Módulo 2 funciona sin cambios. Son extractivas: devuelven el texto
de las unidades, nunca un resumen generado. Sin evidencia lo dicen («sin resultados»).

``sustainability_lookup`` aplica un **filtro por payload** en dos niveles (research, ítem 1.1):

1. ``MetadataFilter`` por ``topic_id`` (Qdrant lo aplica en el servidor; sin Qdrant, el
   recuperador sobremuestrea y filtra después). Los temas por eje salen de contar en el oro qué
   ``topic_id`` concentran las unidades con los términos del eje: la taxonomía del oro reparte la
   sostenibilidad entre ``sostenibilidad``, ``productos``, ``sedes`` e ``identidad``.
2. Un filtro de términos sobre el texto de cada unidad recuperada (``THEME_TERMS``), para que solo
   queden fragmentos que de verdad tratan el eje pedido.

La consulta se amplía con los términos del eje (``THEME_EXPANSION``) cuando el usuario no da una.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..config import PROJECT_ROOT
from ..rag.hybrid import HybridRetriever, MetadataFilter, RetrievedFragment
from ..retrieval import GoldUnit
from .catalog import ToolContext, ToolSpec
from .guard import GuardedDocument, render_documents
from .guard import neutralize as neutralize_text
from .structured import STOPWORDS, normalize
from .tools import mark_anomalies

NO_INDEX = "El índice de recuperación no está disponible en este servidor."
GOLD_DIR_ENV = "PML_GOLD_DIR"
SUMMARY_UNITS = 5
NEWS_TOPIC = "noticias"
NEWS_URL = "/manuelita-noticias/"

Theme = Literal["agua", "carbono", "energia", "residuos", "biodiversidad", "social"]
TopicId = Literal[
    "catalogos",
    "certificaciones",
    "clientes",
    "empleo",
    "finanzas",
    "fundacion",
    "general",
    "identidad",
    "noticias",
    "precios",
    "productos",
    "rankings",
    "redes",
    "sedes",
    "sostenibilidad",
    "youtube",
]

# Eje → temas del oro (``topic_id``) donde se concentran sus unidades (conteo sobre el oro de
# noviembre de 2026; ver docstring del módulo).
THEME_TOPICS: dict[str, tuple[str, ...]] = {
    "agua": ("sostenibilidad", "productos", "sedes"),
    "carbono": ("sostenibilidad", "productos", "identidad"),
    "energia": ("sostenibilidad", "productos", "sedes"),
    "residuos": ("sostenibilidad", "productos"),
    "biodiversidad": ("sostenibilidad", "general", "productos", "sedes"),
    "social": ("sostenibilidad", "fundacion", "identidad"),
}
THEME_EXPANSION: dict[str, str] = {
    "agua": "agua consumo hídrico vertimientos aguas residuales riego cuencas",
    "carbono": "emisiones de carbono gases de efecto invernadero huella de carbono CO2",
    "energia": "energía renovable cogeneración biogás eficiencia energética",
    "residuos": "residuos reciclaje compostaje economía circular aprovechamiento",
    "biodiversidad": "biodiversidad conservación bosques reforestación fauna flora",
    "social": "comunidades inversión social educación vivienda Fundación Manuelita",
}
# Términos (texto normalizado, sin tildes) que debe contener una unidad para contar en el eje.
THEME_TERMS: dict[str, re.Pattern[str]] = {
    "agua": re.compile(r"\b(agua|aguas|hidric\w*|vertimiento\w*|riego|fertirriego|cuenca\w*)\b"),
    "carbono": re.compile(
        r"\b(carbono|emision\w*|gei|co2|co2e|invernadero|huella|descarboniz\w*)\b"
    ),
    "energia": re.compile(
        r"\b(energia\w*|energetic\w*|cogenera\w*|biogas|electric\w*|renovable\w*|vapor)\b"
    ),
    "residuos": re.compile(
        r"\b(residuo\w*|reciclaj\w*|reciclad\w*|compost\w*|circular|desecho\w*|aprovecha\w*)\b"
    ),
    "biodiversidad": re.compile(
        r"\b(biodiversidad|conservacion|bosque\w*|reforesta\w*|fauna|flora|ecosistema\w*|"
        r"corredor\w*|deforestacion)\b"
    ),
    "social": re.compile(
        r"\b(comunidad\w*|social\w*|educacion|educativ\w*|fundacion|voluntariad\w*|vivienda|"
        r"salud|graduad\w*)\b"
    ),
}
FAQ_STOPWORDS = STOPWORDS | {"manuelita", "informacion", "hace", "sobre", "tienen", "cual"}


# ----------------------------------------------------------------------- utilidades comunes


def gold_dir() -> Path:
    configured = os.environ.get(GOLD_DIR_ENV, "").strip()
    return Path(configured) if configured else PROJECT_ROOT / "data" / "gold"


def unit_header(unit: GoldUnit) -> str:
    """Metadatos legibles de una unidad (título, fecha y páginas)."""
    parts = [unit.title or unit.topic_title]
    if unit.published_at:
        parts.append(f"publicado {unit.published_at[:10]}")
    if unit.page_start is not None:
        pages = (
            f"p. {unit.page_start}"
            if unit.page_end in (None, unit.page_start)
            else f"pp. {unit.page_start}–{unit.page_end}"
        )
        parts.append(pages)
    return " · ".join(part for part in parts if part)


def cite_units(
    ctx: ToolContext,
    units: Sequence[GoldUnit],
    *,
    fragments: Sequence[RetrievedFragment] | None = None,
    with_header: bool = False,
) -> str:
    """Registra las unidades en la traza (``U#`` consecutivas) y las devuelve aisladas.

    Con ``ctx.neutralize`` las oraciones con instrucciones embebidas se sustituyen antes de
    llegar al modelo (spec 015), y el fragmento queda marcado como anómalo.
    """
    documents: list[GuardedDocument] = []
    for index, unit in enumerate(units):
        fragment = (
            fragments[index]
            if fragments is not None
            else RetrievedFragment(
                unit_id=unit.unit_id,
                title=unit.title or unit.topic_title,
                url=unit.url,
                score=1.0,
                semantic_score=None,
                lexical_score=None,
                origin="lexical",
            )
        )
        cleaned = neutralize_text(unit.text) if ctx.neutralize else None
        removed = len(cleaned.removed) if cleaned else 0
        ctx.trace.fragments.append(mark_anomalies(fragment, unit.text, removed))
        text = cleaned.text if cleaned else unit.text
        if with_header:
            text = f"[{unit_header(unit)}]\n{text}"
        documents.append(GuardedDocument(f"U{len(ctx.trace.fragments)}", unit.url, text))
    return render_documents(documents)


def _retrieve(
    retriever: HybridRetriever, query: str, *, top_k: int, topics: Sequence[str]
) -> list[tuple[GoldUnit, RetrievedFragment]]:
    trace = retriever.retrieve(
        query, top_k=top_k, metadata_filter=MetadataFilter.of(topics=list(topics))
    )
    found: list[tuple[GoldUnit, RetrievedFragment]] = []
    for fragment in trace.fragments:
        unit = retriever.units_by_id.get(fragment.unit_id)
        if fragment.status == "used" and unit is not None:
            found.append((unit, fragment))
    return found


# ---------------------------------------------------------------- 6. sustainability_lookup


class SustainabilityLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: Theme = Field(
        description="Eje: agua, carbono, energia, residuos, biodiversidad o social."
    )
    query: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Pregunta concreta dentro del eje (opcional).",
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Máximo de fragmentos.")


def sustainability_lookup_impl(ctx: ToolContext, args: SustainabilityLookupArgs) -> str:
    ctx.trace.calls += 1
    if ctx.retriever is None:
        return NO_INDEX
    query = (
        f"{args.query} {THEME_EXPANSION[args.theme]}" if args.query else THEME_EXPANSION[args.theme]
    )
    terms = THEME_TERMS[args.theme]
    found = [
        (unit, fragment)
        for unit, fragment in _retrieve(
            ctx.retriever, query, top_k=max(args.top_k * 3, 10), topics=THEME_TOPICS[args.theme]
        )
        if terms.search(normalize(unit.text))
    ][: args.top_k]
    if not found:
        return f"Sin resultados de sostenibilidad para el eje «{args.theme}»."
    units = [unit for unit, _ in found]
    fragments = [fragment for _, fragment in found]
    return cite_units(ctx, units, fragments=fragments)


# ------------------------------------------------------------------------- 10. faq_lookup


class FaqLookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=300, description="Pregunta del usuario.")
    top_k: int = Field(default=3, ge=1, le=5, description="Máximo de preguntas frecuentes.")


@lru_cache(maxsize=4)
def _load_faq(path: str) -> tuple[dict[str, Any], ...]:
    source = Path(path)
    if not source.is_file():
        return ()
    return tuple(
        json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line
    )


def load_faq_seeds() -> tuple[dict[str, Any], ...]:
    """Semillas de FAQ del oro (``faq_seeds.jsonl``), una carga por ruta."""
    return _load_faq(str(gold_dir() / "faq_seeds.jsonl"))


def _faq_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize(text))
    return {token for token in tokens if len(token) > 2 and token not in FAQ_STOPWORDS}


def rank_faq(question: str, seeds: Sequence[dict[str, Any]]) -> list[tuple[float, dict]]:
    """Coincidencia léxica (coseno binario) entre la pregunta y cada semilla."""
    asked = _faq_tokens(question)
    ranked: list[tuple[float, dict[str, Any]]] = []
    for seed in seeds:
        tokens = _faq_tokens(f"{seed.get('question', '')} {seed.get('topic_id', '')}")
        common = asked & tokens
        if not common:
            continue
        score = len(common) / math.sqrt(len(asked) * len(tokens))
        ready = 1 if seed.get("status") == "ready" else 0
        ranked.append((score + 0.01 * ready, seed))
    ranked.sort(key=lambda item: (-item[0], str(item[1].get("seed_id", ""))))
    return ranked


def best_evidence(units: Sequence[GoldUnit], text: str, limit: int = 3) -> list[GoldUnit]:
    """Unidades de evidencia más afines a la pregunta (solapamiento léxico; español primero)."""
    wanted = _faq_tokens(text)

    def key(unit: GoldUnit) -> tuple[int, int, str]:
        overlap = len(wanted & _faq_tokens(unit.text))
        return (-overlap, 0 if unit.language == "es" else 1, unit.unit_id)

    return sorted(units, key=key)[:limit]


def faq_lookup_impl(ctx: ToolContext, args: FaqLookupArgs) -> str:
    ctx.trace.calls += 1
    seeds = load_faq_seeds()
    if not seeds:
        return "Las preguntas frecuentes del oro no están disponibles."
    ranked = rank_faq(args.question, seeds)[: args.top_k]
    if not ranked:
        return "Sin resultados en las preguntas frecuentes."
    units_by_id = ctx.retriever.units_by_id if ctx.retriever is not None else {}
    parts: list[str] = []
    for _score, seed in ranked:
        units = best_evidence(
            [units_by_id[u] for u in seed.get("evidence_unit_ids", []) if u in units_by_id],
            f"{args.question} {seed.get('question', '')}",
        )
        header = f"Pregunta frecuente ({seed.get('topic_id', '')}): {seed.get('question', '')}"
        if units:
            parts.append(f"{header}\n{cite_units(ctx, units)}")
        else:
            parts.append(f"{header}\n(Sin evidencia disponible en el índice para esta pregunta.)")
    return "\n\n".join(parts)


# --------------------------------------------------------------------- 11. summarize_topic


class SummarizeTopicArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: TopicId = Field(description="Tema del oro (data/gold/topics).")


def topic_info(topic_id: str) -> tuple[str, str]:
    """Título y descripción del tema desde la cabecera de ``gold/topics/<tema>.md``."""
    path = gold_dir() / "topics" / f"{topic_id}.md"
    title, description = topic_id, ""
    if not path.is_file():
        return title, description
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index and line.strip() == "---":
                break
            key, _, value = line.partition(":")
            if key == "title":
                title = value.strip()
            elif key == "description":
                description = value.strip()
    return title, description


def summarize_topic_impl(ctx: ToolContext, args: SummarizeTopicArgs) -> str:
    ctx.trace.calls += 1
    if ctx.retriever is None:
        return NO_INDEX
    title, description = topic_info(args.topic_id)
    found = _retrieve(
        ctx.retriever,
        f"{title}. {description}",
        top_k=SUMMARY_UNITS,
        topics=[args.topic_id],
    )[:SUMMARY_UNITS]
    if not found:
        return f"Sin resultados para el tema «{args.topic_id}»."
    rendered = cite_units(
        ctx, [unit for unit, _ in found], fragments=[fragment for _, fragment in found]
    )
    return (
        f"Tema: {title} — {description} Unidades representativas (extractivo, sin resumen "
        f"generado):\n{rendered}"
    )


# ------------------------------------------------------------------------- 12. latest_news


class LatestNewsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=3, ge=1, le=5, description="Número de noticias.")
    since_year: int | None = Field(
        default=None, ge=2000, le=2030, description="Solo noticias publicadas desde este año."
    )


def _lead_key(unit: GoldUnit) -> tuple[int, int, str]:
    """Prefiere la unidad que comparte más palabras con el título de la noticia."""
    title = _faq_tokens(unit.title)
    return (len(title & _faq_tokens(unit.text)), min(len(unit.text), 1200), unit.unit_id)


def news_units(units: Sequence[GoldUnit], *, since_year: int | None = None) -> list[GoldUnit]:
    """Una unidad por noticia (URL), las más recientes primero.

    Cuenta como noticia toda unidad con ``published_at`` del tema ``noticias`` o de la sección
    de noticias del sitio (``/manuelita-noticias/``). Por noticia se toma la unidad que más
    palabras comparte con el título (y, a igualdad, la más extensa).
    """
    best: dict[str, GoldUnit] = {}
    for unit in units:
        if not unit.published_at or not unit.published_at[:4].isdigit():
            continue
        if unit.topic_id != NEWS_TOPIC and NEWS_URL not in unit.url:
            continue
        if since_year is not None and int(unit.published_at[:4]) < since_year:
            continue
        key = unit.url or unit.unit_id
        current = best.get(key)
        if current is None or _lead_key(unit) > _lead_key(current):
            best[key] = unit
    return sorted(best.values(), key=lambda u: (u.published_at or "", u.unit_id), reverse=True)


def latest_news_impl(ctx: ToolContext, args: LatestNewsArgs) -> str:
    ctx.trace.calls += 1
    if ctx.retriever is None:
        return NO_INDEX
    news = news_units(ctx.retriever.units, since_year=args.since_year)[: args.limit]
    if not news:
        since = f" desde {args.since_year}" if args.since_year else ""
        return f"Sin resultados: no hay noticias fechadas{since}."
    return cite_units(ctx, news, with_header=True)


# ------------------------------------------------------------------------ 13. get_fragment


class GetFragmentArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(
        pattern=r"^unit_[0-9a-f]{16}$", description="Identificador de la unidad de oro."
    )


def get_fragment_impl(ctx: ToolContext, args: GetFragmentArgs) -> str:
    ctx.trace.calls += 1
    if ctx.retriever is None:
        return NO_INDEX
    unit = ctx.retriever.units_by_id.get(args.unit_id)
    if unit is None:
        return f"Sin resultados: no existe la unidad {args.unit_id}."
    return cite_units(ctx, [unit], with_header=True)


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        6,
        "sustainability_lookup",
        "Busca evidencia de sostenibilidad de Manuelita por eje (agua, carbono, energía, "
        "residuos, biodiversidad o social) con búsqueda híbrida filtrada por tema; cita [U#].",
        SustainabilityLookupArgs,
        "read",
        frozenset({"documental"}),
        "Qdrant híbrida con filtro por payload (topic_id + términos del eje)",
        sustainability_lookup_impl,
    ),
    ToolSpec(
        10,
        "faq_lookup",
        "Busca la pregunta frecuente del oro más parecida a la del usuario y devuelve sus "
        "unidades de evidencia citables [U#].",
        FaqLookupArgs,
        "read",
        frozenset({"documental"}),
        "gold/faq_seeds.jsonl + unidades de evidencia",
        faq_lookup_impl,
    ),
    ToolSpec(
        11,
        "summarize_topic",
        "Panorama extractivo de un tema del oro (identidad, productos, sedes, fundación…): "
        "devuelve las unidades más representativas con su cita [U#], sin resumen generado.",
        SummarizeTopicArgs,
        "read",
        frozenset({"documental"}),
        "gold/topics/*.md + unidades del tema",
        summarize_topic_impl,
    ),
    ToolSpec(
        12,
        "latest_news",
        "Noticias y comunicados de Manuelita más recientes según su fecha de publicación, "
        "opcionalmente desde un año; cada noticia se cita [U#].",
        LatestNewsArgs,
        "read",
        frozenset({"documental"}),
        "unidades fechadas del tema noticias (published_at)",
        latest_news_impl,
    ),
    ToolSpec(
        13,
        "get_fragment",
        "Devuelve el texto completo, la URL y las páginas de una unidad de oro por su unit_id "
        "(p. ej. para ampliar una cita) [U#].",
        GetFragmentArgs,
        "read",
        frozenset({"documental"}),
        "gold/knowledge_units.jsonl",
        get_fragment_impl,
    ),
)
