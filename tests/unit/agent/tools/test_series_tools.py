"""Herramientas de series del catálogo: list_indicators y compare_indicator (T029, spec 024)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from proyecto_modelos_lenguaje.agent.catalog import ToolArgsError, ToolContext, get_spec, run_read
from proyecto_modelos_lenguaje.agent.series import load_series


@pytest.fixture(scope="module")
def table():
    return load_series()


def _run(name: str, args: dict, table) -> tuple[str, ToolContext]:
    ctx = ToolContext(series=table)
    return run_read(get_spec(name), ctx, args), ctx


def test_list_indicators_lists_every_metric_with_years_and_a_fact(table) -> None:
    # Act
    output, ctx = _run("list_indicators", {}, table)

    # Assert
    assert output.startswith('<documento id="F1"')
    for metric in table.metrics():
        assert metric in output
    assert "2014" in output
    assert len(ctx.trace.facts) == 1
    assert ctx.trace.facts[0].citations


def test_list_indicators_filters_by_business(table) -> None:
    # Act
    output, _ = _run("list_indicators", {"business": "palma"}, table)

    # Assert
    assert "biodiesel" in output and "aceite_palma" in output
    assert "ebitda" not in output


def test_list_indicators_unknown_business_is_declared(table) -> None:
    # Act
    output, ctx = _run("list_indicators", {"business": "minería"}, table)

    # Assert
    assert output.startswith("Sin resultados")
    assert ctx.trace.facts == []


def test_compare_indicator_computes_decimal_change_with_sources(table) -> None:
    # Arrange
    rows = {row.year: row.value for row in table.rows if row.metric == "ventas_consolidadas"}
    delta = rows[2022] - rows[2018]
    pct = (delta / rows[2018] * 100).quantize(Decimal("0.01"))

    # Act
    args = {"metric": "ventas_consolidadas", "year_a": 2018, "year_b": 2022}
    output, ctx = _run("compare_indicator", args, table)

    # Assert
    fact = ctx.trace.facts[0]
    assert output.startswith('<documento id="F1"')
    assert fact.fact_id == "series_ventas_consolidadas_compare"
    assert Decimal(fact.value.replace(".", "").replace(",", ".")) == delta
    assert str(pct).replace(".", ",") in output
    assert fact.citations


@pytest.mark.parametrize(
    "args",
    [
        {"metric": "ebitda", "year_a": 2019, "year_b": 2019},
        {"metric": "ebitda", "year_a": 1999, "year_b": 2019},
        {"metric": "ebitda", "year_a": 2019, "year_b": 2031},
        {"metric": "ebitda", "year_a": 2019, "year_b": 2020, "extra": 1},
        {"metric": "x", "year_a": 2019, "year_b": 2020},
    ],
)
def test_compare_indicator_rejects_invalid_args(table, args: dict) -> None:
    # Act / Assert
    with pytest.raises(ToolArgsError, match="compare_indicator"):
        _run("compare_indicator", args, table)


@pytest.mark.parametrize(
    "args",
    [
        {"metric": "ebitda", "year_a": 2019, "year_b": 2029},
        {"metric": "exportaciones", "year_a": 2019, "year_b": 2020},
    ],
)
def test_compare_indicator_missing_metric_or_year_is_sin_resultados(table, args: dict) -> None:
    # Act
    output, ctx = _run("compare_indicator", args, table)

    # Assert
    assert output.startswith("Sin resultados")
    assert ctx.trace.facts == []
