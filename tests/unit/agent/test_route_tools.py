"""Herramientas por ruta, plan visible y traza de invocaciones (spec 024, T034, ítem 1.2)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.agent.catalog import (
    ToolContext,
    build_catalog_tools,
    instrument,
    plan_steps,
    specs_for_route,
)
from tests.agent_helpers import demo_retriever

SEARCHES = {"search_documents", "sustainability_lookup", "faq_lookup", "latest_news"}


def _names(route: str) -> set[str]:
    return {spec.name for spec in specs_for_route(route, include_write=False)}


def test_direct_route_has_no_search() -> None:
    assert not _names("direct") & SEARCHES
    assert "search_documents" not in _names("direct")


def test_subsets_by_route() -> None:
    assert {"search_documents", "sustainability_lookup", "faq_lookup"} <= _names("documental")
    assert {"aggregate_series", "compare_indicator", "calculate"} <= _names("structured")
    assert "sustainability_lookup" not in _names("structured")
    assert {"search_documents", "aggregate_series"} <= _names("mixed")


def test_write_tools_only_with_runner() -> None:
    context = ToolContext(retriever=demo_retriever())
    without = {tool.name for tool in build_catalog_tools(context, route="documental")}
    assert "save_profile" not in without
    with_run = build_catalog_tools(context, route="documental", write_run=lambda t, a: "ok")
    assert {"save_profile", "request_human_contact"} <= {tool.name for tool in with_run}


def test_instrument_records_invocations() -> None:
    log: list[dict] = []
    context = ToolContext(retriever=demo_retriever())
    tools = {t.name: t for t in instrument(build_catalog_tools(context, route="structured"), log)}
    tools["calculate"].invoke({"expression": "2+3*4"})
    tools["calculate"].invoke({"expression": "1/0"})
    first, second = log
    assert first["step"] == 1 and first["name"] == "calculate" and first["ok"] is True
    assert first["args"] == {"expression": "2+3*4"} and first["duration_ms"] >= 0
    assert len(first["summary"]) <= 200 and "14" in first["summary"]
    assert second["step"] == 2 and second["ok"] is False and second["error"]


def test_plan_steps() -> None:
    assert plan_steps("direct") == ["responder directo, sin herramientas de búsqueda"]
    steps = plan_steps("structured", [{"name": "compare_indicator", "args": {"metric": "azucar"}}])
    assert steps[0].startswith("consultar") and steps[-1] == "→ compare_indicator(metric=azucar)"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def test_turn_exposes_plan_and_tools(client: TestClient) -> None:
    body = {
        "message": "¿Qué produce Manuelita?",
        "mode": "demo",
        "variant": "agent",
        "user_id": "anon-test",
    }
    turn = client.post("/api/chat", json=body).json()["turn"]
    assert "plan_steps" in turn and "tools" in turn
    if turn["route"]["route"] in {"documental", "structured", "mixed"}:
        assert turn["plan_steps"]
        for call in turn["tools"]:
            assert {"step", "name", "args", "ok", "duration_ms", "summary"} <= set(call)


@pytest.mark.parametrize(
    ("question", "route"),
    [
        ("Compara el EBITDA de 2019 con el de 2022", "structured"),
        ("Muéstrame el texto de la unidad unit_27c34db39788d197", "documental"),
        ("¿Cuánto es 1.250 por 3,5?", "structured"),
        ("Calcula la variación porcentual de 120 a 150", "structured"),
        ("¿Cómo contacto al servicio al cliente de Manuelita?", "documental"),
    ],
)
def test_tool_cues_reach_the_agent(question: str, route: str) -> None:
    from proyecto_modelos_lenguaje.agent.router import rule_decision

    decision = rule_decision(question)
    assert decision is not None and decision.route == route and decision.decided_by == "rules"


@pytest.mark.parametrize("question", ["hola", "¿Qué produce Manuelita?", "gracias, muy amable"])
def test_tool_cues_do_not_capture_other_messages(question: str) -> None:
    from proyecto_modelos_lenguaje.agent.router import rule_decision

    decision = rule_decision(question)
    assert decision is None or decision.route == "direct"
