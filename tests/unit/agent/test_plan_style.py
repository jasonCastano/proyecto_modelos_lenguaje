"""Campos de estilo del plan y de la memoria del hilo (spec 036, ``data-model.md`` §3–§4)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent import care
from proyecto_modelos_lenguaje.agent.config import ConversationConfig
from proyecto_modelos_lenguaje.agent.plan import TurnPlan, build_plan

CONFIG = ConversationConfig()
DIRECT = {"route": "direct", "confidence": 0.9, "reason": "x", "decided_by": "demo"}
DECISION = {"route": "direct", "confidence": 0.9, "reason": "x"}


def plan_with(style: str, hints: tuple[str, ...]) -> TurnPlan:
    signals = {"act": "smalltalk", "act_ruled": True, "sentiment": "neutral", "guided": True}
    return build_plan(signals, DIRECT, {}, CONFIG, turn=2, style=style, style_hints=hints)


def test_plan_defaults_to_no_style() -> None:
    plan = plan_with("off", ("ve",))
    assert plan.style == "off" and plan.style_hints == ()


def test_plan_round_trip_keeps_the_style() -> None:
    plan = plan_with("neutral", ("listo pues", "a la orden"))
    again = TurnPlan.from_state(plan.to_state())
    assert again is not None
    assert (again.style, again.style_hints) == ("neutral", ("listo pues", "a la orden"))
    legacy = {k: v for k, v in plan.to_state().items() if not k.startswith("style")}
    old = TurnPlan.from_state(legacy)
    assert old is not None and old.style == "off" and old.style_hints == ()


def update(memory: care.ConversationMemory, turn: int, **kwargs) -> None:
    care.update_conversation(
        memory,
        message="mensaje",
        signals=None,
        decision=DECISION,
        act="smalltalk",
        turn=turn,
        bridged=None,
        **kwargs,
    )


def test_memory_keeps_the_last_three_expressions() -> None:
    memory = care.empty_conversation()
    assert memory["last_expressions"] == [] and memory["style_opt_out"] is False
    update(memory, 1, expressions=["ve"])
    update(memory, 2, expressions=["listo pues"])
    update(memory, 3, expressions=["a la orden"])
    update(memory, 4, expressions=["chévere"])
    assert memory["last_expressions"] == ["listo pues", "a la orden", "chévere"]
    update(memory, 5, expressions=["listo pues"])
    assert memory["last_expressions"] == ["a la orden", "chévere", "listo pues"]


def test_plain_request_sticks_for_the_thread() -> None:
    memory = care.empty_conversation()
    update(memory, 1, plain=True)
    update(memory, 2)
    assert memory["style_opt_out"] is True


def test_copy_conversation_brings_the_style_defaults() -> None:
    copied = care.copy_conversation(None)
    assert copied["style_opt_out"] is False and copied["last_expressions"] == []
    memory = care.empty_conversation()
    update(memory, 1, expressions=["ve"], plain=True)
    again = care.copy_conversation(memory)
    assert again["last_expressions"] == ["ve"] and again["style_opt_out"] is True
