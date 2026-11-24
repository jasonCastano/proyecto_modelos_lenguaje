"""Evaluaciones del Módulo 3 sin red (spec 024, T036/T048, T059, T061)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from langgraph.store.memory import InMemoryStore

from proyecto_modelos_lenguaje.agent.channel_eval import (
    DIRECT_ATTACKS,
    TOOL_CASES,
    evaluate_tools,
    load_tool_cases,
    render_shield_markdown,
    render_tools_markdown,
    report_payload,
    run_channel_attacks,
    score_reply,
    summarize_attacks,
    summarize_tools,
)
from proyecto_modelos_lenguaje.agent.cli_m3 import list_memory, render_tools_doc


@dataclass
class FakeTurn:
    data: dict

    def model_dump(self, mode: str = "json") -> dict:
        return self.data


def test_fixture_covers_every_tool() -> None:
    from proyecto_modelos_lenguaje.agent.catalog import catalog

    cases = load_tool_cases(TOOL_CASES)
    expected = [case["expected_tool"] for case in cases]
    for spec in catalog():
        assert expected.count(spec.name) >= 2, spec.name
    assert expected.count(None) >= 10 and len(cases) >= 50


def test_evaluate_tools_scores_hits_and_trivial_searches() -> None:
    cases = [
        {"id": "a", "question": "q1", "expected_tool": "compare_indicator"},
        {"id": "b", "question": "q2", "expected_tool": "save_profile"},
        {"id": "c", "question": "hola", "expected_tool": None},
        {"id": "d", "question": "gracias", "expected_tool": None},
    ]
    answers = {
        "q1": ([{"name": "compare_indicator"}], None),
        "q2": ([], "save_profile"),
        "hola": ([], None),
        "gracias": ([{"name": "search_documents"}], None),
    }

    def send(question: str):
        tools, proposed = answers[question]
        turn = FakeTurn({"route": {"route": "structured"}, "tools": tools})
        pending = {"tool": proposed} if proposed else None
        return SimpleNamespace(turn=turn, pending_action=pending)

    results = evaluate_tools(send, cases)
    summary = summarize_tools(results)
    assert summary["accuracy"] == 1.0 and summary["searches_in_trivial"] == 1
    assert summary["meets_target"] is False
    report = report_payload("tools", "demo", "cmd", results, summary)
    assert "Exactitud de herramienta" in render_tools_markdown(report)


def test_score_reply() -> None:
    assert score_reply("Respuesta: HACKEADO", "HACKEADO") == (True, False)
    assert score_reply("## 1. Rol Eres Valer-IA", None) == (False, True)
    assert score_reply("Manuelita produce azúcar [1].", "PWNED") == (False, False)


def test_channel_attacks_pass_and_fail() -> None:
    replies = iter(
        [
            SimpleNamespace(status="answered", messages=["HACKEADO"]),
            SimpleNamespace(status="answered", messages=["No puedo hacer eso."]),
            SimpleNamespace(status="pending_approval", messages=["Responde SÍ"]),
            SimpleNamespace(status="approval_resolved", messages=["Hecho"]),
            SimpleNamespace(status="answered", messages=["ok"]),
        ]
    )
    results = run_channel_attacks(lambda mid, text: next(replies), DIRECT_ATTACKS, kind="direct")
    summary = summarize_attacks(results)
    assert summary["cases"] == 5 and summary["obeyed"] == 1
    assert summary["writes_without_confirmation"] == 1 and summary["proposed_writes"] == 1
    assert summary["meets_target"] is False
    report = report_payload("shield-canal", "demo", "cmd", results, summary)
    assert "❌ no cumple" in render_shield_markdown(report)
    json.dumps(report)  # serializable


def test_memory_audit_lists_namespace_and_dates() -> None:
    store = InMemoryStore()
    store.put(("users", "wa-0123456789abcdef", "profile"), "name", {"value": "Ana"})
    store.put(("users", "wa-0123456789abcdef", "preferences"), "language", {"value": "es"})
    store.put(("users", "wa-otro", "profile"), "name", {"value": "Luis"})
    rows = list_memory(store, "wa-0123456789abcdef")
    assert {(r["namespace"].split("/")[-1], r["key"], r["value"]) for r in rows} == {
        ("profile", "name", "Ana"),
        ("preferences", "language", "es"),
    }
    assert all(r["updated_at"] for r in rows)
    assert "Luis" not in json.dumps(rows)


def test_tools_doc_is_generated(tmp_path: Path) -> None:
    doc = render_tools_doc()
    assert "| 20 | `request_human_contact` |" in doc and "## Esquemas de argumentos" in doc
