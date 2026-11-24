"""Catálogo completo: las 20 herramientas de la spec 024 (contracts/tools-catalog.md)."""

from __future__ import annotations

import json
from collections import Counter

from proyecto_modelos_lenguaje.agent.catalog import ROUTES, catalog
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

ROUTING = PROJECT_ROOT / "tests" / "fixtures" / "agent" / "tool_routing.jsonl"

EXPECTED = [
    "search_documents",
    "query_structured",
    "aggregate_series",
    "list_indicators",
    "compare_indicator",
    "sustainability_lookup",
    "list_business_units",
    "list_company_entities",
    "get_official_channels",
    "faq_lookup",
    "summarize_topic",
    "latest_news",
    "get_fragment",
    "calculate",
    "get_my_profile",
    "save_profile",
    "save_preference",
    "forget_memory",
    "export_conversation",
    "request_human_contact",
]


def test_catalog_has_exactly_the_20_contract_tools_in_order() -> None:
    # Act
    specs = catalog()

    # Assert
    assert [spec.name for spec in specs] == EXPECTED
    assert [spec.number for spec in specs] == list(range(1, 21))
    assert sum(spec.kind == "read" for spec in specs) == 15
    assert all(spec.impl is not None for spec in specs if 4 <= spec.number <= 15)
    assert all(spec.requires_approval == (spec.kind == "write") for spec in specs)


def test_tool_routing_fixture_covers_every_tool_and_trivial_messages() -> None:
    # Arrange
    rows = [
        json.loads(line)
        for line in ROUTING.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Act
    per_tool = Counter(row["expected_tool"] for row in rows if row["expected_tool"])
    trivial = [row for row in rows if row["expected_tool"] is None]

    # Assert
    assert all(set(row) == {"id", "question", "route", "expected_tool"} for row in rows)
    assert len({row["id"] for row in rows}) == len(rows)
    assert set(per_tool) == set(EXPECTED) and min(per_tool.values()) >= 2
    assert sum(per_tool.values()) >= 40 and len(trivial) >= 10
    assert all(row["route"] in ROUTES for row in rows)
