"""Series anuales curadas y herramienta de agregación determinista (rúbrica del Módulo 2, ítem 2.1).

``data/curated/series_anuales.csv`` es un CSV **versionado y curado a mano**: cada fila es una cifra
anual publicada en los informes de sostenibilidad de Manuelita (ventas, EBITDA, producción de
azúcar, bioetanol, biodiésel…), con su ``unit_id`` de oro, la URL del informe y la página. Una
prueba verifica que cada valor aparece literalmente en el texto de la unidad citada.

``aggregate`` calcula en código (``Decimal``, sin redondeos intermedios) la suma, el promedio, el
máximo, el mínimo o la variación de una métrica en un rango de años. El modelo nunca hace la
aritmética: recibe el resultado ya calculado como un hecho ``F#`` y solo lo redacta y lo cita.

Los informes publican cifras **anuales**; no hay series trimestrales ni mensuales. Si la pregunta
pide un trimestre, la herramienta lo declara en lugar de inventar el dato.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..config import PROJECT_ROOT
from .structured import Citation, StructuredFact, normalize

SERIES_PATH = PROJECT_ROOT / "data" / "curated" / "series_anuales.csv"
MIN_YEAR = 2014
MAX_YEAR = 2025

Operation = Literal["list", "sum", "avg", "max", "min", "change"]
OPERATION_LABELS: dict[str, str] = {
    "list": "valores",
    "sum": "suma",
    "avg": "promedio",
    "max": "máximo",
    "min": "mínimo",
    "change": "variación",
}

# Palabras clave (normalizadas, sin tildes) que identifican cada métrica en una pregunta.
METRIC_CUES: dict[str, re.Pattern[str]] = {
    "ventas_consolidadas": re.compile(r"\b(ventas|ingresos operacionales|facturacion|vendio)\b"),
    "ebitda": re.compile(r"\bebitda\b"),
    "utilidad_neta": re.compile(r"\b(utilidad(es)? neta|ganancia(s)?|utilidad(es)?)\b"),
    "patrimonio": re.compile(r"\bpatrimonio\b"),
    "cana_molida": re.compile(r"\b(cana (molida|procesada)|toneladas de cana|molienda)\b"),
    "azucar": re.compile(r"\bazucar\b"),
    "bioetanol_carburante": re.compile(r"\b(bioetanol|etanol|alcohol carburante)\b"),
    "biodiesel": re.compile(r"\bbiodiesel\b"),
    "aceite_palma": re.compile(r"\b(aceite de palma|toneladas de aceite|aceite crudo)\b"),
    "camaron": re.compile(r"\bcamar(o|on|ones)\b"),
    "mejillon": re.compile(r"\bmejillo(n|nes)\b"),
    "inversion_social": re.compile(r"\binversion social\b"),
}
OPERATION_CUES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("change", re.compile(r"\b(variacion|crecimiento|crecio|cambio|aumento|disminuyo|cayo)\b")),
    ("avg", re.compile(r"\b(promedio|media|en promedio)\b")),
    ("max", re.compile(r"\b(maximo|mayor|mas alto|record|mejor ano)\b")),
    ("min", re.compile(r"\b(minimo|menor|mas bajo|peor ano)\b")),
    ("sum", re.compile(r"\b(total|suma|sumad[oa]s?|acumulad[oa]s?|en conjunto)\b")),
)
YEAR = re.compile(r"\b(20[12]\d)\b")
QUARTER = re.compile(r"\b(trimestre|trimestral|semestre|mensual|mes de|q[1-4])\b")


class SeriesError(RuntimeError):
    """El CSV curado falta o no tiene el formato esperado."""


@dataclass(frozen=True, slots=True)
class SeriesRow:
    metric: str
    label: str
    business: str
    year: int
    value: Decimal
    unit: str
    scope: str
    unit_id: str
    source_title: str
    source_url: str
    page: str

    def citation(self) -> Citation:
        page = f", p. {self.page}" if self.page else ""
        return Citation(url=self.source_url, title=f"{self.source_title}{page}")


@dataclass(frozen=True, slots=True)
class SeriesTable:
    """Tabla en memoria con las series anuales; solo lectura."""

    rows: tuple[SeriesRow, ...]

    def metrics(self) -> dict[str, SeriesRow]:
        """Una fila de muestra por métrica (etiqueta, unidad y negocio)."""
        catalog: dict[str, SeriesRow] = {}
        for row in self.rows:
            catalog.setdefault(row.metric, row)
        return catalog

    def select(self, metric: str, year_from: int | None, year_to: int | None) -> list[SeriesRow]:
        low = year_from if year_from is not None else MIN_YEAR
        high = year_to if year_to is not None else MAX_YEAR
        return sorted(
            (r for r in self.rows if r.metric == metric and low <= r.year <= high),
            key=lambda r: r.year,
        )


def load_series(path: str | Path = SERIES_PATH) -> SeriesTable:
    """Lee el CSV curado; falla con ``SeriesError`` si falta o está mal formado."""
    source = Path(path)
    if not source.is_file():
        raise SeriesError(f"No existe el CSV de series: {source}")
    rows: list[SeriesRow] = []
    with source.open(encoding="utf-8", newline="") as handle:
        for line, record in enumerate(csv.DictReader(handle), start=2):
            try:
                rows.append(
                    SeriesRow(
                        metric=record["metric"],
                        label=record["label"],
                        business=record["business"],
                        year=int(record["year"]),
                        value=Decimal(record["value"]),
                        unit=record["unit"],
                        scope=record["scope"],
                        unit_id=record["unit_id"],
                        source_title=record["source_title"],
                        source_url=record["source_url"],
                        page=record.get("page") or "",
                    )
                )
            except (KeyError, ValueError, ArithmeticError) as exc:
                raise SeriesError(f"{source}:{line}: fila inválida ({exc})") from exc
    if not rows:
        raise SeriesError(f"El CSV de series está vacío: {source}")
    return SeriesTable(tuple(rows))


@lru_cache(maxsize=1)
def default_series() -> SeriesTable | None:
    """Tabla del repositorio (una carga por proceso); ``None`` si el CSV no está."""
    try:
        return load_series()
    except SeriesError:
        return None


class AggregateArgs(BaseModel):
    """Argumentos de ``aggregate_series``: agregación validada, nunca código ni SQL libre."""

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(
        min_length=2,
        max_length=40,
        description=(
            "Métrica: ventas_consolidadas, ebitda, utilidad_neta, patrimonio, cana_molida, "
            "azucar, bioetanol_carburante, biodiesel, aceite_palma, camaron, mejillon o "
            "inversion_social."
        ),
    )
    op: Operation = Field(
        default="list",
        description="list (valores), sum, avg (promedio), max, min o change (variación).",
    )
    year_from: int | None = Field(
        default=None, ge=MIN_YEAR, le=MAX_YEAR, description="Año inicial."
    )
    year_to: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR, description="Año final.")

    @model_validator(mode="after")
    def valid_range(self) -> AggregateArgs:
        if self.metric not in METRIC_CUES:
            raise ValueError(f"métrica desconocida: {self.metric}")
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("year_from no puede ser mayor que year_to")
        return self


@dataclass(frozen=True, slots=True)
class AggregateResult:
    args: AggregateArgs
    rows: tuple[SeriesRow, ...]
    value: Decimal | None
    text: str
    missing_years: tuple[int, ...] = ()


def _fmt(value: Decimal) -> str:
    """Formato colombiano: punto de miles y coma decimal (``1.133.242`` o ``12,5``)."""
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    integer, _, decimals = f"{quantized:,.2f}".partition(".")
    integer = integer.replace(",", ".")
    decimals = decimals.rstrip("0")
    return f"{integer},{decimals}" if decimals else integer


def aggregate(table: SeriesTable, args: AggregateArgs) -> AggregateResult:
    """Agrega una métrica en código; el texto resultante ya trae la cifra exacta."""
    rows = table.select(args.metric, args.year_from, args.year_to)
    sample = table.metrics().get(args.metric)
    label = sample.label if sample else args.metric
    unit = sample.unit if sample else ""
    requested = (
        range(args.year_from, args.year_to + 1) if args.year_from and args.year_to else range(0)
    )
    have = {row.year for row in rows}
    missing = tuple(year for year in requested if year not in have)
    if not rows:
        available = sorted({r.year for r in table.rows if r.metric == args.metric})
        listed = ", ".join(str(year) for year in available) or "ninguno"
        return AggregateResult(
            args,
            (),
            None,
            f"{label}: no hay cifras publicadas en ese período. Años disponibles: {listed}.",
            missing,
        )
    values = [row.value for row in rows]
    series = "; ".join(f"{row.year}: {_fmt(row.value)} {unit}" for row in rows)
    value: Decimal | None
    if args.op == "sum":
        value = sum(values, Decimal(0))
        summary = f"Suma {rows[0].year}–{rows[-1].year}: {_fmt(value)} {unit}"
    elif args.op == "avg":
        value = sum(values, Decimal(0)) / len(values)
        summary = f"Promedio de {len(values)} años: {_fmt(value)} {unit}"
    elif args.op == "max":
        best = max(rows, key=lambda r: r.value)
        value = best.value
        summary = f"Máximo: {_fmt(value)} {unit} en {best.year}"
    elif args.op == "min":
        worst = min(rows, key=lambda r: r.value)
        value = worst.value
        summary = f"Mínimo: {_fmt(value)} {unit} en {worst.year}"
    elif args.op == "change":
        first, last = rows[0], rows[-1]
        value = last.value - first.value
        pct = (value / first.value * 100) if first.value else Decimal(0)
        summary = (
            f"Variación {first.year}–{last.year}: {_fmt(value)} {unit} ({_fmt(pct)} %)"
            if len(rows) > 1
            else "Solo hay un año en el rango; no se puede calcular la variación"
        )
    else:
        value = rows[0].value if len(rows) == 1 else None
        summary = series
    scopes = "; ".join(sorted({row.scope for row in rows}))
    gaps = f" Sin dato publicado para: {', '.join(str(y) for y in missing)}." if missing else ""
    detail = "" if args.op == "list" else f" Serie: {series}."
    text = (
        f"{label}: {summary}.{detail} Alcance: {scopes}.{gaps} "
        "Cálculo hecho por la herramienta sobre el CSV curado."
    )
    return AggregateResult(args, tuple(rows), value, text, missing)


def series_intent(question: str) -> AggregateArgs | None:
    """Detecta una pregunta sobre una serie anual («¿Cuánto vendió Manuelita en 2022?»)."""
    text = normalize(question)
    metric = next((name for name, cue in METRIC_CUES.items() if cue.search(text)), None)
    if metric is None:
        return None
    op: str = next((name for name, cue in OPERATION_CUES if cue.search(text)), "list")
    years = sorted({int(year) for year in YEAR.findall(text)})
    year_from = years[0] if years else None
    year_to = years[-1] if years else None
    if len(years) == 1 and re.search(r"\b(desde|a partir de)\b", text):
        year_to = None
    if len(years) == 1 and re.search(r"\b(hasta|antes de)\b", text):
        year_from, year_to = None, years[0]
    return AggregateArgs(
        metric=metric,
        op=op,  # type: ignore[arg-type]
        year_from=year_from if year_from and MIN_YEAR <= year_from <= MAX_YEAR else None,
        year_to=year_to if year_to and MIN_YEAR <= year_to <= MAX_YEAR else None,
    )


def asks_for_quarter(question: str) -> bool:
    """La pregunta pide una granularidad que los informes no publican (trimestre, mes)."""
    return bool(QUARTER.search(normalize(question)))


def series_fact(result: AggregateResult, *, quarter_requested: bool = False) -> StructuredFact:
    """Hecho sintético ``F#`` con el resultado ya calculado y la fuente de cada cifra."""
    citations: list[Citation] = []
    for row in result.rows:
        citation = row.citation()
        if citation not in citations:
            citations.append(citation)
    label = OPERATION_LABELS[result.args.op]
    first = result.rows[0] if result.rows else None
    snippet = result.text
    if quarter_requested:
        # Lo primero que se lee es el límite: no hay cifras trimestrales; después, el dato anual.
        name, _, rest = result.text.partition(": ")
        snippet = (
            f"{name}: los informes no publican cifras trimestrales ni mensuales, solo anuales; "
            f"dato anual {rest}"
        )
    return StructuredFact(
        fact_id=f"series_{result.args.metric}_{result.args.op}",
        subject_id="manuelita",
        subject_label="Grupo Manuelita",
        attribute=f"{first.label.lower() if first else result.args.metric} ({label})",
        value="" if result.value is None else _fmt(result.value),
        year=result.rows[-1].year if result.rows else None,
        unit_id=first.unit_id if first else "",
        snippet=snippet,
        citations=tuple(citations),
    )


def describe_metrics(table: SeriesTable) -> str:
    """Catálogo legible de métricas y años (para la descripción de la herramienta y la UI)."""
    lines = []
    for metric, row in table.metrics().items():
        years = sorted({r.year for r in table.rows if r.metric == metric})
        lines.append(f"{metric}: {row.label} ({row.unit}), años {years[0]}–{years[-1]}")
    return "\n".join(lines)


def years_of(rows: Sequence[SeriesRow]) -> list[int]:
    return [row.year for row in rows]
