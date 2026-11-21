"""Orden reglas → gatekeeper Jev → clasificador LLM en ``route_message`` (spec 022, US1)."""

from __future__ import annotations

import json

from proyecto_modelos_lenguaje.agent.jev import GateOutcome, fake_outcome
from proyecto_modelos_lenguaje.agent.router import is_smalltalk, route_message
from tests.agent_helpers import ScriptedModel

LLM_REPLY = json.dumps(
    {"route": "structured", "confidence": 0.9, "reason": "dato puntual", "alternative": None}
)
QUESTION = "¿Cuál fue la evolución de la producción de azúcar en la última década?"


def _llm() -> ScriptedModel:
    return ScriptedModel(reply=LLM_REPLY)


def test_confident_gate_decides_without_the_llm() -> None:
    model = _llm()
    result = route_message(
        QUESTION, model=model, gate=fake_outcome("documental", 0.9), gate_threshold=0.75
    )
    assert result.decision.route == "documental"
    assert result.decision.decided_by == "jev"
    assert result.decision.alternative is not None
    assert result.model_calls == 0 and model.seen == []


def test_threshold_is_inclusive() -> None:
    result = route_message(QUESTION, model=_llm(), gate=fake_outcome("mixed", 0.75))
    assert result.decision.decided_by == "jev" and result.decision.route == "mixed"


def test_low_confidence_delegates_to_the_llm_and_keeps_the_suggestion() -> None:
    gate = fake_outcome("documental", 0.6)
    result = route_message(QUESTION, model=_llm(), gate=gate, gate_threshold=0.75)
    assert result.decision.decided_by == "llm" and result.decision.route == "structured"
    assert result.model_calls == 1
    assert result.gate is gate and result.gate.decision.route == "documental"


def test_failed_gate_delegates_to_the_llm() -> None:
    result = route_message(
        QUESTION, model=_llm(), gate=GateOutcome(status="failed", reason="timeout")
    )
    assert result.decision.decided_by == "llm"


def test_rules_always_win_over_the_gate() -> None:
    result = route_message("Hola, buenas tardes", model=_llm(), gate=fake_outcome("mixed", 0.99))
    assert result.decision.decided_by == "rules" and result.decision.route == "direct"


def test_confident_clarify_from_the_gate_is_respected() -> None:
    result = route_message("¿Y eso cuánto cuesta?", model=_llm(), gate=fake_outcome("clarify", 0.9))
    assert result.decision.route == "clarify" and result.decision.decided_by == "jev"


def test_router_min_confidence_still_applies_to_the_final_decision() -> None:
    result = route_message(
        QUESTION, model=_llm(), gate=fake_outcome("documental", 0.8), min_confidence=0.85
    )
    assert result.decision.route == "clarify" and result.decision.alternative == "documental"


def test_scope_reason_only_with_out_of_scope() -> None:
    off = route_message(
        "¿Me recomiendas una inversión en finca raíz?",
        model=_llm(),
        gate=fake_outcome("out_of_scope", 0.9, scope_reason="advice"),
    )
    assert off.decision.route == "out_of_scope" and off.decision.scope_reason == "advice"
    doc = route_message(
        QUESTION, model=_llm(), gate=fake_outcome("documental", 0.9, scope_reason="advice")
    )
    assert doc.decision.scope_reason is None


def test_smalltalk_detection() -> None:
    assert is_smalltalk("¡Hola! Buenas tardes")
    assert is_smalltalk("Muchas gracias, hasta luego")
    assert not is_smalltalk("Hola, ¿qué produce Manuelita?")
    assert not is_smalltalk("")
