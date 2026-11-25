"""API v1 de evidencia técnica (spec 026, T055; contracts/evidence-api.md)."""

from __future__ import annotations

import json
import re
import time
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever

from proyecto_modelos_lenguaje import api, api_evidence
from proyecto_modelos_lenguaje.agent.catalog import catalog
from proyecto_modelos_lenguaje.agent.profiles import load_profiles

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    for var in ("VALERIA_PLANNERS", "MANUELITA_PLANNER_OPEN", "MANUELITA_PLANNER_WEB"):
        monkeypatch.delenv(var, raising=False)
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()


def test_tools_lists_the_whole_catalog_with_profiles(client: TestClient) -> None:
    body = client.get("/api/v1/evidence/tools").json()
    specs = catalog()
    assert body["count"] == len(specs) == 26
    profiles = load_profiles()
    by_name = {tool["name"]: tool for tool in body["tools"]}
    for spec in specs:
        tool = by_name[spec.name]
        if spec.kind == "read":
            expected = sorted(k for k, profile in profiles.items() if spec.name in profile.tools)
        elif spec.name == "save_production_proposal":
            expected = ["planificador"]
        else:
            expected = sorted(profiles)
        assert tool["profiles"] == expected, spec.name
        assert tool["requires_approval"] == (tool["kind"] == "write")
    assert by_name["simulate_production_scenario"]["mcp_allowed"] is False
    assert by_name["optimize_production_plan"]["mcp_allowed"] is False


def test_trace_of_a_demo_turn(client: TestClient) -> None:
    chat = client.post(
        "/api/chat",
        json={
            "message": "¿Qué certificaciones tiene Manuelita? Llámame al 3001234567",
            "mode": "demo",
            "user_id": "anon-evidence",
            "variant": "agent",
        },
    ).json()
    thread_id = chat["thread_id"]
    trace = client.get(f"/api/v1/evidence/traces/{thread_id}").json()
    assert trace["thread_id"] == thread_id
    assert trace["turn"] == trace["turns"] == 1
    assert trace["route"]
    assert isinstance(trace["plan_steps"], list)
    assert all("duration_ms" in tool for tool in trace["tools"])
    assert "3001234567" not in json.dumps(trace)


def test_trace_errors(client: TestClient) -> None:
    missing = client.get("/api/v1/evidence/traces/no-existe")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "thread_not_found"
    chat = client.post(
        "/api/chat",
        json={"message": "hola", "mode": "demo", "user_id": "anon-e2", "variant": "agent"},
    ).json()
    bad_turn = client.get(f"/api/v1/evidence/traces/{chat['thread_id']}?turn=9")
    assert bad_turn.status_code == 404
    assert bad_turn.json()["error"]["code"] == "turn_not_found"


def test_services_report_reason_and_action_without_secrets(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-secreto-de-prueba")

    def slow() -> dict:
        time.sleep(3)
        return {"status": "up", "reason": "tarde", "action": ""}

    monkeypatch.setitem(api_evidence.CHECKS, "qdrant", slow)
    monkeypatch.setattr(api_evidence, "CHECK_TIMEOUT", 0.2)
    body = client.get("/api/v1/evidence/services").json()
    ids = [service["id"] for service in body["services"]]
    assert ids == ["model", "qdrant", "whatsapp", "gateway", "voice", "stt"]
    qdrant = next(s for s in body["services"] if s["id"] == "qdrant")
    assert qdrant["status"] == "unknown" and "tiempo" in qdrant["reason"]
    for service in body["services"]:
        assert service["reason"]
        if service["status"] in ("down", "unknown"):
            assert service["action"]
    text = json.dumps(body)
    assert "sk-" not in text
    assert not re.search(r"\+?57\d{10}", text)


def test_evaluations_match_the_versioned_file(client: TestClient) -> None:
    body = client.get("/api/v1/evidence/evaluations").json()
    config = tomllib.loads((ROOT / "config" / "evaluations.toml").read_text(encoding="utf-8"))
    assert [row["id"] for row in body] == [row["id"] for row in config["evaluation"]]
    for row in body:
        assert (ROOT / row["report"]).is_file(), row["report"]
    ids = {row["id"] for row in body}
    assert {
        "herramientas",
        "triviales",
        "planificacion",
        "planificacion-directa",
        "perfiles",
        "rag",
        "blindaje",
    } <= ids
    partial = next(row for row in body if row["id"] == "herramientas")
    assert partial["meets"] == "partial" and partial["note"]
