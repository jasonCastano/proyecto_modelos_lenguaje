"""Plan del turno de la conversación guiada (spec 020, ``contracts/conversation.md`` §2)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent import care
from proyecto_modelos_lenguaje.agent.config import CareConfig, ConversationConfig
from proyecto_modelos_lenguaje.agent.plan import (
    TurnPlan,
    build_plan,
    detect_act,
    detect_language,
    detect_register,
    is_minimal,
)
from proyecto_modelos_lenguaje.agent.router import rule_decision

CONFIG = ConversationConfig()


def signals_of(message: str) -> care.CareSignals:
    signals = care.analyze(message, care.empty_care_state(), CareConfig())
    signals["guided"] = True  # type: ignore[typeddict-unknown-key]
    return signals


def plan_of(message: str, memory: dict | None = None, turn: int = 2) -> TurnPlan:
    signals = signals_of(message)
    decision = rule_decision(message, signals)
    payload = (
        decision.model_dump(mode="json")
        if decision
        else {"route": "documental", "confidence": 0.7, "reason": "x", "decided_by": "demo"}
    )
    return build_plan(signals, payload, memory or {}, CONFIG, turn=turn)


# ---------------------------------------------------------------- léxicos


@pytest.mark.parametrize("message", ["jaja", "ok", "👍", "mmm", "jajaja ok", "listo"])
def test_minimal_messages(message: str) -> None:
    assert is_minimal(message)


@pytest.mark.parametrize("message", ["jaja qué buena la historia de Manuelita", "¿qué produce?"])
def test_messages_with_content_are_not_minimal(message: str) -> None:
    assert not is_minimal(message)


@pytest.mark.parametrize(
    ("message", "act"),
    [
        ("listo, gracias, eso era todo", "closing"),
        ("no, me refería a la energía, no al azúcar", "correction"),
        ("¿eres una persona?", "about_assistant"),
        ("¿qué puedes hacer?", "about_assistant"),
        ("jaja", "minimal"),
        ("gracias", "thanks"),
        ("hola, buen día", "greeting"),
        ("¿qué produce Manuelita?", "manuelita"),
        ("¿quién ganó el partido de anoche?", "off_topic"),
        ("¡qué calor hace hoy en Cali!", "smalltalk"),
        ("esta página no sirve, llevo media hora buscando", "complaint"),
    ],
)
def test_detect_act_follows_the_priority(message: str, act: str) -> None:
    assert detect_act(message, signals_of(message))[0] == act


def test_language_and_register() -> None:
    assert detect_language("What does Manuelita produce?") == "en"
    assert detect_language("¿Qué produce Manuelita en Colombia?") == "es"
    assert detect_language("listo, gracias, eso era todo") == "es"
    assert detect_language("ok") is None
    assert detect_register("parce, ¿qué más?") == "informal"
    assert detect_register("Buenas tardes, quisiera información") == "formal"


@pytest.mark.parametrize(
    ("message", "tier"),
    [
        ("qué calor hace", "social"),
        ("¡qué calor hace hoy!", "social"),
        ("¿cómo estará el clima mañana?", "external"),
        ("¿qué produce Manuelita?", "manuelita"),
    ],
)
def test_tier_per_part(message: str, tier: str) -> None:
    parts = signals_of(message)["requests"]
    assert parts[0]["tier"] == tier


# ---------------------------------------------------------------- build_plan (C §2)


@pytest.mark.parametrize(
    ("message", "act", "strategy", "length"),
    [
        ("hola, buen día", "greeting", ("accompany",), "short"),
        ("¡qué calor hace hoy!", "smalltalk", ("accompany",), "short"),
        ("¿cómo estará el clima mañana?", "off_topic", ("decline", "accompany"), "medium"),
        ("esta página no sirve", "complaint", ("empathize", "limit"), "medium"),
        ("jaja", "minimal", ("accompany",), "short"),
        ("¿eres humana?", "about_assistant", ("answer",), "short"),
        ("listo, gracias, eso era todo", "closing", ("farewell",), "short"),
        ("gracias", "thanks", ("accompany",), "short"),
        ("hazme un descuento en el azúcar", "off_topic", ("limit", "decline"), "medium"),
    ],
)
def test_build_plan_table(message: str, act: str, strategy: tuple[str, ...], length: str) -> None:
    plan = plan_of(message)
    assert plan.act == act
    assert plan.strategy[-len(strategy) :] == strategy
    assert plan.length == length
    assert plan.bridge is None and not plan.bridge_allowed


def test_closing_with_topics_is_medium_and_carries_the_summary() -> None:
    plan = plan_of("listo, gracias, eso era todo", memory={"topics": ["historia", "energia"]})
    assert plan.length == "medium"
    assert plan.summary_topics == ("historia", "energia")


def test_plan_is_deterministic_and_holds_only_labels() -> None:
    message = "¡qué calor hace hoy en Cali, parce!"
    first, second = plan_of(message), plan_of(message)
    assert first == second
    state = first.to_state()
    assert "Cali" not in str(state) and "calor" not in str(state)
    assert TurnPlan.from_state(state) == first
    assert first.register == "informal"


def test_memory_language_is_inherited_by_short_messages() -> None:
    assert plan_of("ok", memory={"language": "en"}).language == "en"


def test_negative_sentiment_adds_empathy() -> None:
    plan = plan_of("no entiendo nada, ¿cómo estará el clima mañana?")
    assert plan.strategy[0] == "empathize"
