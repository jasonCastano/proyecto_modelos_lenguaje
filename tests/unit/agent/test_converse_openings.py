"""Aperturas sugeridas sin preguntas en los turnos ajenos (spec 035, US1)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.agent.graph import opening_hint
from proyecto_modelos_lenguaje.agent.plan import TurnPlan

BASE = TurnPlan(
    act="smalltalk",
    tiers=(),
    sentiment="neutral",
    strategy=("acknowledge",),
    length="short",
    language="es",
    register="informal",
    turn=3,
)


@pytest.mark.parametrize("act", ["smalltalk", "off_topic", "minimal", "greeting"])
def test_redirect_never_suggests_question_openings(act: str) -> None:
    plan = replace(BASE, act=act, redirect=True, streak=1)
    for seed in range(31):
        hint = opening_hint(plan, seed)
        assert "pregunta" not in hint and "sin ofrecer temas" not in hint


def test_question_opening_stays_available_without_redirect() -> None:
    hints = {opening_hint(BASE, seed) for seed in range(31)}
    assert any("pregunta" in hint for hint in hints)
