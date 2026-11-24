"""Herramientas utilitarias: calculate, get_official_channels y get_my_profile (T032, spec 024)."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from proyecto_modelos_lenguaje.agent.catalog import ToolArgsError, ToolContext, get_spec, run_read
from proyecto_modelos_lenguaje.agent.memory import UserMemory, UserProfile, memory_store
from proyecto_modelos_lenguaje.agent.tools_utility import (
    OFFICIAL_CONTACTS,
    CalculationError,
    digital_channels,
    evaluate_expression,
    purpose_for,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.unit.agent.tools.gold import requires_gold

GOLD_UNITS = PROJECT_ROOT / "data" / "gold" / "knowledge_units.jsonl"


def _run(name: str, args: dict, **context) -> tuple[str, ToolContext]:
    ctx = ToolContext(**context)
    return run_read(get_spec(name), ctx, args), ctx


# ------------------------------------------------------------------------------ calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("2 + 3 * 4", Decimal("14")),
        ("(1.250,5 - 1000) / 2", Decimal("125.25")),
        ("0.1 + 0.2", Decimal("0.3")),
        ("15% * 200", Decimal("30")),
        ("-(4 - 10)", Decimal("6")),
        ("2 ** 10", Decimal("1024")),
        ("10 % 3", Decimal("1")),
    ],
)
def test_evaluate_expression_with_decimal(expression: str, expected: Decimal) -> None:
    assert evaluate_expression(expression) == expected


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("1 / 0", "división por cero"),
        ("2 ** 11", "exponente"),
        ("2 ** 0.5", "exponente"),
        ("9" * 25 + " * " + "9" * 25, "demasiado grande"),
        ("(1 + 2", "no es aritmética"),
        ("1..2 + 3", "ambiguo"),
    ],
)
def test_evaluate_expression_rejects_unsafe_or_impossible(expression: str, message: str) -> None:
    with pytest.raises(CalculationError, match=message):
        evaluate_expression(expression)


def test_calculate_expression_registers_a_fact() -> None:
    # Act
    output, ctx = _run("calculate", {"expression": "(120 - 100) / 100 * 100"})

    # Assert
    assert output.startswith('<documento id="F1"')
    assert ctx.trace.facts[0].value == "20"


@pytest.mark.parametrize(
    ("operation", "values", "expected"),
    [
        ("percent_change", ["100", "125"], "25 %"),
        ("ratio", ["3", "4"], "0,75"),
        ("sum", ["1.5", "2.25", "3"], "6,75"),
    ],
)
def test_calculate_operations(operation: str, values: list[str], expected: str) -> None:
    # Act
    _, ctx = _run("calculate", {"operation": operation, "values": values})

    # Assert
    assert ctx.trace.facts[0].value == expected


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"expression": "abs(-1)"},
        {"expression": "__import__('os')"},
        {"expression": "x + 1"},
        {"expression": "1" * 121},
        {"expression": "1 + 1", "operation": "sum", "values": ["1"]},
        {"operation": "sum"},
        {"operation": "ratio", "values": ["1"]},
        {"operation": "sum", "values": ["1"] * 13},
        {"operation": "media", "values": ["1", "2"]},
    ],
)
def test_calculate_rejects_invalid_args(args: dict) -> None:
    with pytest.raises(ToolArgsError, match="calculate"):
        _run("calculate", args)


@pytest.mark.parametrize(
    "args",
    [
        {"expression": "5 / (2 - 2)"},
        {"operation": "ratio", "values": ["1", "0"]},
        {"operation": "percent_change", "values": ["0", "3"]},
    ],
)
def test_calculate_division_by_zero_is_a_clear_error(args: dict) -> None:
    with pytest.raises(ToolArgsError, match="No se pudo calcular"):
        _run("calculate", args)


# ------------------------------------------------------------------ get_official_channels


@pytest.mark.parametrize("purpose", ["general", "empleo", "proveedores", "clientes", "prensa"])
def test_official_channels_by_purpose_are_cited(purpose: str) -> None:
    # Act
    output, ctx = _run("get_official_channels", {"purpose": purpose})

    # Assert
    urls = {contact.url for contact in OFFICIAL_CONTACTS[purpose]}
    assert urls <= {fact.value for fact in ctx.trace.facts}
    assert all(fact.citations for fact in ctx.trace.facts)
    assert output.count("<documento") == len(ctx.trace.facts)


def test_general_channels_include_the_digital_channels_of_the_config() -> None:
    # Arrange
    channels = digital_channels()

    # Act
    output, _ = _run("get_official_channels", {})

    # Assert
    assert {"https://www.youtube.com/@ManuelitaAgroindustria"} <= {url for _, url in channels}
    assert all(url in output for _, url in channels)


def test_official_channels_reject_unknown_purpose() -> None:
    with pytest.raises(ToolArgsError, match="get_official_channels"):
        _run("get_official_channels", {"purpose": "ventas"})


@requires_gold
def test_contact_units_exist_in_the_gold() -> None:
    # Arrange
    wanted = {c.unit_id for contacts in OFFICIAL_CONTACTS.values() for c in contacts}
    found: dict[str, str] = {}
    with GOLD_UNITS.open(encoding="utf-8") as handle:
        for line in handle:
            unit_id = line[line.find('"unit_id": "') + 12 :][:21]
            if unit_id in wanted:
                found[unit_id] = json.loads(line)["url"]

    # Assert
    assert set(found) == wanted
    for contacts in OFFICIAL_CONTACTS.values():
        for contact in contacts:
            assert found[contact.unit_id].rstrip("/") == contact.url.rstrip("/")


def test_purpose_for_contact_topics() -> None:
    assert purpose_for("Quiero enviar mi hoja de vida") == "empleo"
    assert purpose_for("Soy proveedor de caña") == "proveedores"
    assert purpose_for("Un reclamo por un pedido") == "clientes"
    assert purpose_for("Entrevista para un medio") == "prensa"
    assert purpose_for("Otra cosa") == "general"


# ------------------------------------------------------------------------- get_my_profile


def test_get_my_profile_reads_only_the_current_user() -> None:
    # Arrange
    store = memory_store()
    UserProfile(store).save("user-a", {"name": "Ana", "city": "Cali"})
    UserMemory(store, ttl_days=30).save("user-a", "response_format", "breve")
    UserProfile(store).save("user-b", {"name": "Beto"})

    # Act
    output, ctx = _run("get_my_profile", {}, memory_store=store, user_id="user-a")
    other, _ = _run("get_my_profile", {}, memory_store=store, user_id="user-c")

    # Assert
    assert "Ana" in output and "Cali" in output and "breve" in output
    assert "Beto" not in output
    assert ctx.trace.facts == [] and ctx.trace.fragments == []
    assert other.startswith("Sin resultados")


def test_get_my_profile_takes_no_arguments() -> None:
    # Act / Assert
    with pytest.raises(ToolArgsError, match="get_my_profile"):
        _run("get_my_profile", {"user_id": "otro"}, memory_store=memory_store())
    output, _ = _run("get_my_profile", {})
    assert "no está disponible" in output
