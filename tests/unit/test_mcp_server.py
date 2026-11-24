"""Servidor MCP propio ``valeria-tools`` (spec 024, T049): solo lectura, esquemas y citas."""

from __future__ import annotations

import asyncio

from proyecto_modelos_lenguaje.agent.catalog import ToolContext, catalog
from proyecto_modelos_lenguaje.mcp_server import build_server, exposed_specs, main
from tests.agent_helpers import demo_retriever


def _context() -> ToolContext:
    return ToolContext(retriever=demo_retriever())


def test_only_read_tools_are_exposed() -> None:
    exposed = {spec.name for spec in exposed_specs()}
    reads = {spec.name for spec in catalog() if spec.kind == "read" and spec.mcp_allowed}
    writes = {spec.name for spec in catalog() if spec.kind == "write"}
    assert exposed == reads and not exposed & writes
    assert {"save_profile", "forget_memory"} <= writes
    # Spec 025 (R16): el modo degradado no planifica.
    assert {"get_plant_state", "get_commitments", "search_operating_procedures"} <= exposed
    assert not {"simulate_production_scenario", "optimize_production_plan"} & exposed
    assert "save_production_proposal" not in exposed


def test_schemas_and_call() -> None:
    server = build_server(_context)

    async def scenario():
        tools = await server.list_tools()
        result = await server.call_tool("search_documents", {"query": "azúcar y etanol"})
        return tools, result

    tools, result = asyncio.run(scenario())
    by_name = {tool.name: tool for tool in tools}
    assert set(by_name) == {spec.name for spec in exposed_specs()}
    schema = by_name["search_documents"].input_schema
    assert schema["properties"]["query"]["maxLength"] == 500 and "query" in schema["required"]
    text = result.content[0].text
    assert "<documento" in text or "Sin resultados" in text


def test_list_command(capsys) -> None:
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "search_documents" in out and "save_profile" not in out
