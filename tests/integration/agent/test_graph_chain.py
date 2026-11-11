"""Variante cadena en modo demo (T038, US1)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.tasks import FALLBACK_ANSWER
from tests.agent_helpers import ScriptedModel, make_service


def test_follow_up_uses_the_thread_and_cites() -> None:
    # Arrange
    service = make_service()
    first = service.send("¿Qué produce Manuelita?", variant="chain")

    # Act
    second = service.send("¿Y dónde lo produce?", thread_id=first.thread_id, variant="chain")

    # Assert
    assert second.status == "answered"
    assert second.turn.route.route == "documental"
    assert second.turn.citations and second.turn.fragments
    labels = {fragment["label"] for fragment in second.turn.fragments}
    assert {citation["label"] for citation in second.turn.citations} <= labels
    assert second.turn.metrics.model_calls == 1
    assert second.turn.metrics.tool_calls == 1


def test_elliptic_question_in_a_new_thread_asks_for_clarification() -> None:
    # Act
    outcome = make_service().send("¿Y lo anterior?", variant="chain")

    # Assert
    assert outcome.status == "clarify"
    assert outcome.turn.citations == []
    assert outcome.turn.metrics.tool_calls == 0


@pytest.mark.parametrize(
    "reply", [FALLBACK_ANSWER, "Manuelita produce azúcar.", "Manuelita produce azúcar [U99]."]
)
def test_answers_without_valid_citations_become_fallback(reply: str) -> None:
    # Arrange
    model = ScriptedModel(reply=reply, seen=[])

    # Act
    outcome = make_service(model=model).send("¿Qué produce Manuelita?", variant="chain")

    # Assert
    assert outcome.status == "fallback"
    assert outcome.turn.fallback is True
    assert outcome.turn.answer == FALLBACK_ANSWER
    assert outcome.turn.citations == []
    expected_calls = 1 if reply == FALLBACK_ANSWER else 2  # reintento con recordatorio de citas
    assert len(model.seen) == expected_calls


def test_greeting_and_out_of_scope_do_not_search() -> None:
    # Arrange
    service = make_service()

    # Act
    greeting = service.send("Hola, buenas tardes", variant="chain")
    weather = service.send("¿Va a llover mañana en Cali?", variant="chain")

    # Assert
    assert greeting.turn.route.route == "direct"
    assert weather.turn.route.route == "out_of_scope"
    for outcome in (greeting, weather):
        assert outcome.turn.fragments == []
        assert outcome.turn.metrics.tool_calls == 0
        assert outcome.turn.metrics.model_calls == 0
