"""Catálogo único de herramientas (spec 024, T008, contracts/tools-catalog.md)."""

from __future__ import annotations

import re

import pytest

from proyecto_modelos_lenguaje.agent.catalog import (
    PLAN_BY_ROUTE,
    ROUTES,
    ToolArgsError,
    ToolContext,
    catalog,
    get_spec,
    run_read,
    specs_for_route,
    to_json_schema,
)

NAME = re.compile(r"^[a-z][a-z0-9_]{2,40}$")


def test_at_least_twenty_unique_tools() -> None:
    specs = catalog()
    names = [spec.name for spec in specs]
    assert len(specs) >= 20
    assert len(set(names)) == len(names)
    assert [spec.number for spec in specs] == sorted(spec.number for spec in specs)


@pytest.mark.parametrize("spec", catalog(), ids=lambda spec: spec.name)
def test_spec_invariants(spec) -> None:
    assert NAME.match(spec.name)
    assert 20 <= len(spec.description) <= 300
    assert spec.requires_approval == (spec.kind == "write")
    assert spec.mcp == (spec.kind == "read" and spec.mcp_allowed)
    assert spec.args_schema.model_config.get("extra") == "forbid"
    assert spec.routes and spec.routes <= ROUTES
    assert spec.data_source


def test_write_tools_need_approval() -> None:
    writes = {spec.name for spec in catalog() if spec.kind == "write"}
    assert {"save_profile", "save_preference", "forget_memory", "export_conversation"} <= writes


def test_direct_route_offers_no_search() -> None:
    names = {spec.name for spec in specs_for_route("direct", include_write=False)}
    assert "search_documents" not in names and "aggregate_series" not in names
    documental = {spec.name for spec in specs_for_route("documental", include_write=False)}
    assert "search_documents" in documental


def test_run_read_validates_and_refuses_writes() -> None:
    with pytest.raises(ToolArgsError, match="Argumentos inválidos"):
        run_read(get_spec("search_documents"), ToolContext(), {"query": ""})
    with pytest.raises(ToolArgsError, match="aprobación"):
        run_read(get_spec("save_profile"), ToolContext(), {"name": "Ana"})


def test_json_schema_export() -> None:
    exported = to_json_schema()
    assert len(exported) == len(catalog())
    assert all(item["schema"]["type"] == "object" for item in exported)


# --- Spec 025 (T007): ruta planning, mcp_allowed y filtro por perfil ----------------------------


def test_planning_route_exists() -> None:
    assert "planning" in ROUTES
    assert len(PLAN_BY_ROUTE["planning"]) >= 3


def test_mcp_allowed_hides_read_tool_from_mcp() -> None:
    from dataclasses import replace

    spec = replace(get_spec("calculate"), mcp_allowed=False)
    assert spec.kind == "read" and not spec.mcp
    assert spec.to_dict()["mcp"] is False


def test_profile_filters_reads_and_keeps_common_writes() -> None:
    cliente = {spec.name for spec in specs_for_route("documental", profile="cliente")}
    assert "search_documents" in cliente
    assert "aggregate_series" not in cliente  # no está en la lista del perfil
    assert {"save_profile", "request_human_contact"} <= cliente
    assert "save_production_proposal" not in cliente


def test_visitante_profile_matches_no_profile() -> None:
    for route in ROUTES - {"planning"}:
        plain = {spec.name for spec in specs_for_route(route)}
        visitor = {spec.name for spec in specs_for_route(route, profile="visitante")}
        assert visitor == plain - {"save_production_proposal"}


def test_planning_tools_only_for_planner() -> None:
    planner = {spec.name for spec in specs_for_route("planning", profile="planificador")}
    assert {"get_plant_state", "optimize_production_plan", "save_production_proposal"} <= planner
    visitor = {spec.name for spec in specs_for_route("planning", profile="visitante")}
    assert "optimize_production_plan" not in visitor
