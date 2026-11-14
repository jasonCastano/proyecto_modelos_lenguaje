"""Series anuales curadas y agregación determinista (rúbrica del Módulo 2, ítem 2.1)."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from proyecto_modelos_lenguaje.agent.series import (
    SERIES_PATH,
    AggregateArgs,
    SeriesError,
    aggregate,
    asks_for_quarter,
    load_series,
    series_fact,
    series_intent,
)
from proyecto_modelos_lenguaje.agent.tools import ToolTrace, build_read_tools
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.agent_helpers import demo_retriever

GOLD_UNITS = PROJECT_ROOT / "data" / "gold" / "knowledge_units.jsonl"


@pytest.fixture(scope="module")
def table():
    return load_series()


def test_curated_csv_is_versioned_with_a_source_for_every_row(table) -> None:
    # Arrange / Act
    rows = table.rows

    # Assert
    assert SERIES_PATH.is_file()
    assert len(rows) == 74
    assert len(table.metrics()) == 12
    assert all(row.source_url.startswith("https://www.manuelita.com/") for row in rows)
    assert all(row.unit_id.startswith("unit_") for row in rows)


def _gold_is_downloaded() -> bool:
    if not GOLD_UNITS.is_file():
        return False
    with GOLD_UNITS.open(encoding="utf-8") as handle:
        return not handle.read(200).startswith("version https://git-lfs")


@pytest.mark.skipif(not _gold_is_downloaded(), reason="Requiere la capa oro (Git LFS).")
def test_every_value_appears_literally_in_its_gold_unit(table) -> None:
    # Arrange
    wanted = {row.unit_id for row in table.rows}
    texts: dict[str, str] = {}
    with GOLD_UNITS.open(encoding="utf-8") as handle:
        for line in handle:
            unit = json.loads(line)
            if unit["unit_id"] in wanted:
                texts[unit["unit_id"]] = unit["text"]

    # Act
    missing = [
        (row.metric, row.year)
        for row in table.rows
        if f"{int(row.value):,}".replace(",", ".") not in texts.get(row.unit_id, "")
    ]

    # Assert
    assert not missing


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (
            AggregateArgs(metric="ventas_consolidadas", op="sum", year_from=2019, year_to=2022),
            Decimal(7476475),
        ),
        (AggregateArgs(metric="ebitda", op="max"), Decimal(720297)),
        (AggregateArgs(metric="utilidad_neta", op="min"), Decimal(2163)),
        (
            AggregateArgs(metric="biodiesel", op="change", year_from=2017, year_to=2022),
            Decimal(26725698),
        ),
        (AggregateArgs(metric="azucar", op="avg", year_from=2023, year_to=2024), Decimal(379139)),
    ],
)
def test_aggregate_computes_exact_values(table, args: AggregateArgs, expected: Decimal) -> None:
    # Act
    result = aggregate(table, args)

    # Assert
    assert result.value == expected


def test_change_reports_the_percentage_and_the_years(table) -> None:
    # Act
    result = aggregate(
        table, AggregateArgs(metric="biodiesel", op="change", year_from=2017, year_to=2022)
    )

    # Assert
    assert "Variación 2017–2022: 26.725.698 litros (25,85 %)" in result.text


def test_missing_years_are_declared_not_invented(table) -> None:
    # Act
    result = aggregate(
        table, AggregateArgs(metric="azucar", op="sum", year_from=2018, year_to=2021)
    )

    # Assert
    assert result.missing_years == (2019, 2020)
    assert "Sin dato publicado para: 2019, 2020" in result.text
    assert result.value == Decimal(508196 + 362216)


def test_empty_period_lists_the_available_years(table) -> None:
    # Act
    result = aggregate(
        table, AggregateArgs(metric="inversion_social", op="sum", year_from=2014, year_to=2016)
    )

    # Assert
    assert result.value is None
    assert "Años disponibles: 2023, 2024" in result.text


@pytest.mark.parametrize(
    "payload",
    [
        {"metric": "precio_del_dolar"},
        {"metric": "azucar", "op": "median"},
        {"metric": "azucar", "year_from": 2022, "year_to": 2019},
        {"metric": "azucar", "year_from": 1990},
        {"metric": "azucar", "sql": "DROP TABLE"},
    ],
)
def test_aggregate_args_reject_invalid_input(payload: dict[str, object]) -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        AggregateArgs.model_validate(payload)


@pytest.mark.parametrize(
    ("question", "metric", "op", "years"),
    [
        (
            "¿Cuánto vendió Manuelita en total entre 2019 y 2022?",
            "ventas_consolidadas",
            "sum",
            (2019, 2022),
        ),
        ("¿Cuál fue el año de mayor EBITDA?", "ebitda", "max", (None, None)),
        ("Promedio de producción de azúcar desde 2021", "azucar", "avg", (2021, None)),
        ("¿Cómo creció el biodiésel?", "biodiesel", "change", (None, None)),
        ("Producción de camarón en 2022", "camaron", "list", (2022, 2022)),
    ],
)
def test_series_intent_reads_metric_operation_and_years(
    question: str, metric: str, op: str, years: tuple[int | None, int | None]
) -> None:
    # Act
    args = series_intent(question)

    # Assert
    assert args is not None
    assert (args.metric, args.op, (args.year_from, args.year_to)) == (metric, op, years)


def test_series_intent_ignores_narrative_questions() -> None:
    assert series_intent("¿Qué hace Manuelita en sostenibilidad?") is None


def test_quarter_request_is_answered_with_the_annual_limit(table) -> None:
    # Arrange
    question = "¿Cuántas toneladas de azúcar se produjeron en el tercer trimestre de 2022?"
    args = series_intent(question)
    assert args is not None

    # Act
    fact = series_fact(aggregate(table, args), quarter_requested=asks_for_quarter(question))

    # Assert
    assert fact.snippet.startswith(
        "Producción de azúcar: los informes no publican cifras trimestrales"
    )
    assert "2022: 395.663 toneladas" in fact.snippet
    assert fact.citations


def test_aggregate_tool_returns_a_citable_fact(table) -> None:
    # Arrange
    trace = ToolTrace()
    tools = {t.name: t for t in build_read_tools(demo_retriever(), None, trace, series=table)}

    # Act
    output = tools["aggregate_series"].invoke(
        {"metric": "ventas_consolidadas", "op": "sum", "year_from": 2019, "year_to": 2022}
    )

    # Assert
    assert re.search(r'<documento id="F1"', output)
    assert "7.476.475 COP millones" in output
    assert trace.facts[0].fact_id == "series_ventas_consolidadas_sum"


def test_load_series_rejects_a_malformed_csv(tmp_path: Path) -> None:
    # Arrange
    broken = tmp_path / "series.csv"
    broken.write_text("metric,year\nazucar,dos mil\n", encoding="utf-8")

    # Act / Assert
    with pytest.raises(SeriesError):
        load_series(broken)
