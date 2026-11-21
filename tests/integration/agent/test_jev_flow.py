"""Gatekeeper Jev en los dos grafos, en modo demo y sin red (spec 021, US1–US3)."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.agent.config import JevConfig
from proyecto_modelos_lenguaje.agent.jev import FakeJevGate, GateOutcome, fake_outcome
from proyecto_modelos_lenguaje.agent.observability import turn_record
from proyecto_modelos_lenguaje.agent.service import ChatOutcome
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.agent_helpers import agent_config, make_service

VARIANTS = ["chain", "agent"]
QUERIES = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "module2_queries.jsonl"
CARE_CASES = PROJECT_ROOT / "tests" / "fixtures" / "care" / "care_cases.jsonl"


def _config(enabled: bool = True):
    config = agent_config()
    return replace(config, jev=replace(config.jev, enabled=enabled))


def talk(variant: str, *messages: str, gate=None) -> list[ChatOutcome]:
    service = make_service(config=_config(), gate=gate)
    outcomes: list[ChatOutcome] = []
    thread_id = None
    for message in messages:
        outcome = service.send(message, thread_id=thread_id, user_id="anon-jev", variant=variant)
        thread_id = outcome.thread_id
        outcomes.append(outcome)
    return outcomes


# ---------------------------------------------------------------- US1


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_gate_is_consulted_once_with_history(variant: str) -> None:
    gate = FakeJevGate(JevConfig(enabled=True))
    _first, second = talk(variant, "¿Qué produce Manuelita?", "¿Y en qué año se fundó?", gate=gate)
    assert len(gate.calls) == 2
    assert gate.calls[1][1] == ("¿Qué produce Manuelita?",)
    turn = second.turn
    assert turn.route.decided_by in {"jev", "rules"}
    assert turn.metrics.gate_calls == 1
    assert turn.jev is not None and turn.jev["status"] == "ok"


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_gate_decision_is_traced_without_text(variant: str) -> None:
    question = "Cuéntame la historia del ingenio y su fundador"
    gate = FakeJevGate(
        JevConfig(enabled=True), outcomes={question: fake_outcome("documental", 0.92)}
    )
    (outcome,) = talk(variant, question, gate=gate)
    assert outcome.turn.route.decided_by == "jev"
    record = turn_record(outcome.to_dict(), variant=variant, mode="demo")
    assert record["decided_by"] == "jev" and record["gate_calls"] == 1
    assert record["jev"]["accepted"] is True and record["jev"]["confidence"] == 0.92
    assert question not in json.dumps(record, ensure_ascii=False)


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_smalltalk_is_not_sent_to_the_gate(variant: str) -> None:
    gate = FakeJevGate(JevConfig(enabled=True))
    (outcome,) = talk(variant, "Hola, buenas tardes", gate=gate)
    assert gate.calls == []
    assert outcome.turn.jev == outcome.turn.jev | {"status": "skipped", "reason": "smalltalk"}
    assert outcome.turn.metrics.gate_calls == 0


# ---------------------------------------------------------------- US2


def _routes(gate) -> list[str]:
    service = make_service(config=_config(enabled=gate is not None), gate=gate)
    routes = []
    for line in QUERIES.read_text(encoding="utf-8").splitlines()[:24]:
        row = json.loads(line)
        if row.get("type") == "follow_up":
            continue
        outcome = service.send(row["question"], user_id="anon-jev", variant="chain")
        routes.append(outcome.turn.route.route)
    return routes


def test_us2_without_gate_routes_match_the_baseline() -> None:
    baseline = _routes(None)
    failing = FakeJevGate(
        JevConfig(enabled=True), default=GateOutcome(status="failed", reason="timeout")
    )
    assert _routes(failing) == baseline


@pytest.mark.parametrize(
    "reason",
    ["timeout", "network", "http_401", "http_402", "http_429", "refusal", "invalid_response"],
)
def test_us2_every_failure_still_answers(reason: str) -> None:
    gate = FakeJevGate(JevConfig(enabled=True), default=GateOutcome(status="failed", reason=reason))
    (outcome,) = talk("chain", "¿Qué certificaciones tiene Manuelita?", gate=gate)
    assert outcome.turn.answer
    assert outcome.turn.route.decided_by != "jev"
    assert outcome.turn.jev["status"] == "failed" and outcome.turn.jev["reason"] == reason


# ---------------------------------------------------------------- US3


def _crisis_cases() -> list[dict]:
    rows = [json.loads(line) for line in CARE_CASES.read_text(encoding="utf-8").splitlines()]
    return [row for row in rows if row["skill"] == "crisis"]


@pytest.mark.parametrize("case", _crisis_cases(), ids=lambda case: case["id"])
def test_us3_gate_never_removes_a_crisis(case: dict) -> None:
    calm = fake_outcome("documental", 0.95, crisis=0.0, annoyance=0.0)
    gate = FakeJevGate(JevConfig(enabled=True), default=calm)
    (outcome,) = talk("chain", *case["turns"], gate=gate)
    assert outcome.turn.route.scope_reason == "crisis"
    assert "106" in outcome.turn.answer and "123" in outcome.turn.answer


def test_us3_gate_adds_an_indirect_crisis() -> None:
    message = "Siento que ya no puedo más con todo esto"
    calm = fake_outcome("direct", 0.9, crisis=0.0)
    (control,) = talk("chain", message, gate=FakeJevGate(JevConfig(enabled=True), default=calm))
    assert control.turn.route.scope_reason != "crisis"  # el léxico solo no la detecta
    risky = fake_outcome("direct", 0.9, crisis=0.8)
    (outcome,) = talk("chain", message, gate=FakeJevGate(JevConfig(enabled=True), default=risky))
    assert outcome.turn.route.scope_reason == "crisis"
    assert "106" in outcome.turn.answer and "123" in outcome.turn.answer
