"""Herramientas de series anuales del catálogo (spec 024, herramientas 4 y 5).

``list_indicators`` y ``compare_indicator`` leen el mismo CSV curado que ``aggregate_series``
(``data/curated/series_anuales.csv``, lector de ``agent/series.py``). La aritmética se hace en
código con ``Decimal``; el modelo recibe el resultado ya calculado como un hecho ``F#`` con la
fuente de cada cifra y solo lo redacta y lo cita.

También expone :func:`cite_facts`, que registra hechos en la traza del turno con etiquetas ``F#``
consecutivas (las mismas que valida el mecanismo de citas del Módulo 2).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .catalog import ToolContext, ToolSpec
from .guard import render_documents
from .series import SeriesRow, SeriesTable, _fmt, default_series
from .structured import Citation, StructuredFact, normalize
from .tools import fact_document

NO_SERIES = "Las series anuales no están disponibles en este servidor."


def cite_facts(ctx: ToolContext, facts: Sequence[StructuredFact]) -> str:
    """Registra los hechos en la traza y los devuelve como documentos ``F#`` aislados."""
    documents = []
    for fact in facts:
        ctx.trace.facts.append(fact)
        documents.append(fact_document(f"F{len(ctx.trace.facts)}", fact))
    return render_documents(documents)


def _series(ctx: ToolContext) -> SeriesTable | None:
    return ctx.series if ctx.series is not None else default_series()


def _citations(rows: Sequence[SeriesRow]) -> tuple[Citation, ...]:
    citations: list[Citation] = []
    for row in rows:
        citation = row.citation()
        if citation not in citations:
            citations.append(citation)
    return tuple(citations)


# --------------------------------------------------------------------- 4. list_indicators


class ListIndicatorsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        description=(
            "Negocio o plataforma para filtrar (p. ej. «caña», «palma», «acuicultura», "
            "«Grupo Manuelita»). Vacío: todas las métricas."
        ),
    )


def list_indicators_impl(ctx: ToolContext, args: ListIndicatorsArgs) -> str:
    ctx.trace.calls += 1
    table = _series(ctx)
    if table is None:
        return NO_SERIES
    wanted = normalize(args.business) if args.business else ""
    rows = [
        row
        for row in table.rows
        if not wanted or wanted in normalize(row.business) or wanted in normalize(row.scope)
    ]
    if not rows:
        return f"Sin resultados: no hay series anuales para «{args.business}»."
    by_metric: dict[str, list[SeriesRow]] = {}
    for row in rows:
        by_metric.setdefault(row.metric, []).append(row)
    lines = []
    for metric, metric_rows in by_metric.items():
        sample = metric_rows[0]
        years = sorted({row.year for row in metric_rows})
        lines.append(
            f"- {metric}: {sample.label} ({sample.unit}; {sample.business}), "
            f"años publicados: {', '.join(str(year) for year in years)}"
        )
    snippet = (
        f"Indicadores anuales disponibles en el CSV curado ({len(by_metric)} métricas):\n"
        + "\n".join(lines)
    )
    fact = StructuredFact(
        fact_id="series_catalog",
        subject_id="manuelita",
        subject_label="Grupo Manuelita",
        attribute="indicadores anuales disponibles",
        value=str(len(by_metric)),
        year=None,
        unit_id=rows[0].unit_id,
        snippet=snippet,
        citations=_citations(rows),
    )
    return cite_facts(ctx, [fact])


# --------------------------------------------------------------------- 5. compare_indicator


class CompareIndicatorArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(
        min_length=2,
        max_length=40,
        description="Métrica del CSV (p. ej. ventas_consolidadas, ebitda, azucar, cana_molida).",
    )
    year_a: int = Field(ge=2000, le=2030, description="Año base de la comparación.")
    year_b: int = Field(ge=2000, le=2030, description="Año a comparar con el año base.")

    @model_validator(mode="after")
    def distinct_years(self) -> CompareIndicatorArgs:
        if self.year_a == self.year_b:
            raise ValueError("year_a y year_b deben ser distintos")
        return self


def compare_indicator_impl(ctx: ToolContext, args: CompareIndicatorArgs) -> str:
    ctx.trace.calls += 1
    table = _series(ctx)
    if table is None:
        return NO_SERIES
    metric = args.metric.strip().lower()
    available = sorted({row.year for row in table.rows if row.metric == metric})
    if not available:
        known = ", ".join(table.metrics())
        return f"Sin resultados: no existe la métrica «{args.metric}». Métricas: {known}."
    rows = {row.year: row for row in table.rows if row.metric == metric}
    first, second = rows.get(args.year_a), rows.get(args.year_b)
    if first is None or second is None:
        label = table.metrics()[metric].label
        missing = ", ".join(str(year) for year in (args.year_a, args.year_b) if year not in rows)
        listed = ", ".join(str(year) for year in available)
        return (
            f"Sin resultados: {label} no tiene cifra publicada para {missing}. "
            f"Años disponibles: {listed}."
        )
    delta: Decimal = second.value - first.value
    pct = (delta / first.value * 100) if first.value else None
    pct_text = f"{_fmt(pct)} %" if pct is not None else "no calculable (valor base 0)"
    unit = first.unit
    snippet = (
        f"{first.label}: {args.year_a} = {_fmt(first.value)} {unit}; "
        f"{args.year_b} = {_fmt(second.value)} {unit}. "
        f"Variación absoluta {args.year_a}→{args.year_b}: {_fmt(delta)} {unit}; "
        f"variación porcentual: {pct_text}. Alcance: {first.scope}. "
        "Cálculo hecho por la herramienta con Decimal sobre el CSV curado."
    )
    fact = StructuredFact(
        fact_id=f"series_{metric}_compare",
        subject_id="manuelita",
        subject_label="Grupo Manuelita",
        attribute=f"{first.label.lower()} (comparación {args.year_a}–{args.year_b})",
        value=_fmt(delta),
        year=args.year_b,
        unit_id=second.unit_id,
        snippet=snippet,
        citations=_citations([first, second]),
    )
    return cite_facts(ctx, [fact])


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        4,
        "list_indicators",
        "Lista los indicadores anuales curados de Manuelita (ventas, EBITDA, azúcar, bioetanol…) "
        "con su unidad y los años publicados; úsala antes de pedir una cifra o comparación [F#].",
        ListIndicatorsArgs,
        "read",
        frozenset({"structured"}),
        "data/curated/series_anuales.csv",
        list_indicators_impl,
    ),
    ToolSpec(
        5,
        "compare_indicator",
        "Compara un indicador anual entre dos años distintos: variación absoluta y porcentual "
        "calculadas en código con Decimal, con la fuente de cada cifra [F#].",
        CompareIndicatorArgs,
        "read",
        frozenset({"structured", "mixed"}),
        "data/curated/series_anuales.csv (Decimal)",
        compare_indicator_impl,
    ),
)
