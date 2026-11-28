"""Plan de enfoque en Manuelita (spec 035, ``contracts/focus-rules.md`` §1)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.config import ConversationConfig
from proyecto_modelos_lenguaje.agent.plan import (
    FOCUS_SHORT_STREAK,
    TurnPlan,
    build_plan,
    needs_redirect,
)

CONFIG = ConversationConfig()
DIRECT = {"route": "direct", "confidence": 0.9, "reason": "x", "decided_by": "demo"}
OUT = {
    "route": "out_of_scope",
    "confidence": 0.9,
    "reason": "x",
    "decided_by": "demo",
    "scope_reason": "off_topic",
}


def plan_for(
    act: str,
    *,
    memory: dict | None = None,
    turn: int = 2,
    sentiment: str = "neutral",
    topics: tuple[str, ...] = ("historia", "energia", "fundacion"),
) -> TurnPlan:
    signals = {"act": act, "act_ruled": True, "sentiment": sentiment, "guided": True}
    decision = OUT if act == "off_topic" else DIRECT
    return build_plan(signals, decision, memory or {}, CONFIG, turn=turn, focus_topics=topics)


@pytest.mark.parametrize("act", ["smalltalk", "off_topic", "minimal"])
def test_social_and_offtopic_acts_need_redirect(act: str) -> None:
    assert needs_redirect(act, 2)


def test_greeting_needs_redirect_only_after_the_first_turn() -> None:
    assert not needs_redirect("greeting", 1)
    assert needs_redirect("greeting", 2)


def test_minimal_that_assents_to_an_offer_is_exempt() -> None:
    assert not needs_redirect("minimal", 3, assent_to_offer=True)


@pytest.mark.parametrize(
    "act", ["thanks", "closing", "about_assistant", "complaint", "clarify", "manuelita"]
)
def test_other_acts_do_not_need_redirect(act: str) -> None:
    assert not needs_redirect(act, 2)


def test_build_plan_sets_redirect_streak_and_topics() -> None:
    plan = plan_for("smalltalk", memory={"offtopic_streak": 1})
    assert plan.redirect and plan.streak == 2
    assert plan.topics == ("historia", "energia", "fundacion")
    plain = plan_for("manuelita", memory={"offtopic_streak": 4})
    assert not plain.redirect and plain.streak == 0 and plain.topics == ()


def test_distress_keeps_the_care_of_spec_019() -> None:
    plan = plan_for("smalltalk", sentiment="distressed")
    assert not plan.redirect and plan.streak == 0


def test_from_the_third_offtopic_turn_the_plan_is_short() -> None:
    plan = plan_for("off_topic", memory={"offtopic_streak": FOCUS_SHORT_STREAK - 1})
    assert plan.streak == FOCUS_SHORT_STREAK and plan.length == "short"
    assert "máximo dos frases" in plan.render()
    assert "máximo dos frases" not in plan_for("off_topic").render()


def test_render_requires_the_return_to_manuelita() -> None:
    text = plan_for("smalltalk").render({"historia": "la historia de Manuelita"})
    assert "regreso a Manuelita: obligatorio" in text
    assert "preguntas: solo sobre Manuelita" in text
    assert "temas sugeridos: la historia de Manuelita; energia; fundacion" in text
    assert "regreso a Manuelita" not in plan_for("manuelita").render()


def test_plan_state_round_trip_keeps_the_focus_fields() -> None:
    plan = plan_for("smalltalk", memory={"offtopic_streak": 2})
    again = TurnPlan.from_state(plan.to_state())
    assert again is not None
    assert (again.redirect, again.streak, again.topics) == (True, 3, plan.topics)
