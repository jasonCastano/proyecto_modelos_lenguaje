"""Catálogo completo: las 20 herramientas de la spec 024 y las 6 de planificación de la
spec 025 (contracts/tools-catalog.md, specs/025-…/contracts/planning-tools.md)."""

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
PLANNING = [
    "get_plant_state",
    "get_commitments",
    "search_operating_procedures",
    "simulate_production_scenario",
    "optimize_production_plan",
    "save_production_proposal",
]


def test_catalog_has_exactly_the_26_contract_tools_in_order() -> None:
    # Act
    specs = catalog()

    # Assert
    assert [spec.name for spec in specs] == EXPECTED + PLANNING
    assert [spec.number for spec in specs] == list(range(1, 27))
    assert sum(spec.kind == "read" for spec in specs) == 20
    assert all(spec.impl is not None for spec in specs if 4 <= spec.number <= 15)
    assert all(spec.impl is not None for spec in specs if 21 <= spec.number <= 25)
    # Spec 028 (D1): ninguna lectura de planificación va al MCP; quedan las 15 de atención.
    assert [s.name for s in specs if s.kind == "read" and not s.mcp] == PLANNING[:5]
    assert sum(spec.kind == "read" and spec.mcp for spec in specs) == 15
    assert all(spec.requires_approval == (spec.kind == "write") for spec in specs)


def test_tool_routing_fixture_covers_every_tool_and_trivial_messages() -> None:
    # Arrange
    rows = [
        json.loads(line)
        for line in ROUTING.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    baseline = [row for row in rows if "profile" not in row]
    planner = [row for row in rows if "profile" in row]

    # Act
    per_tool = Counter(row["expected_tool"] for row in baseline if row["expected_tool"])
    trivial = [row for row in baseline if row["expected_tool"] is None]
    planner_tools = {row["expected_tool"] for row in planner}

    # Assert
    assert all(set(row) == {"id", "question", "route", "expected_tool"} for row in baseline)
    assert all(row["profile"] == "planificador" for row in planner)
    assert planner_tools == set(PLANNING) - {"save_production_proposal"}
    assert len({row["id"] for row in rows}) == len(rows)
    assert set(per_tool) == set(EXPECTED) and min(per_tool.values()) >= 2
    assert sum(per_tool.values()) >= 40 and len(trivial) >= 10
    assert all(row["route"] in ROUTES for row in rows)
