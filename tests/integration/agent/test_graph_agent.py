"""Variante agente en modo demo (T038, US1)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.service import ChatError
from proyecto_modelos_lenguaje.tasks import FALLBACK_ANSWER
from tests.agent_helpers import AlwaysSearchModel, make_service


def test_agent_follow_up_uses_the_thread_and_cites() -> None:
    # Arrange
    service = make_service()
    first = service.send("¿Qué produce Manuelita?", variant="agent")

    # Act
    second = service.send("¿Y dónde lo produce?", thread_id=first.thread_id, variant="agent")

    # Assert
    assert second.status == "answered"
    assert second.turn.citations
    assert second.turn.metrics.tool_calls == 1
    assert second.turn.metrics.model_calls == 2  # pide la búsqueda y luego responde


def test_agent_new_thread_with_elliptic_question_clarifies() -> None:
    # Act
    outcome = make_service().send("¿Y lo anterior?", variant="agent")

    # Assert
    assert outcome.status == "clarify"
    assert outcome.turn.metrics.model_calls == 0


def test_agent_respects_the_tool_call_limit() -> None:
    # Arrange: el modelo pediría buscar sin parar
    service = make_service(model=AlwaysSearchModel())

    # Act
    outcome = service.send("¿Qué produce Manuelita?", variant="agent")

    # Assert
    assert outcome.turn.metrics.tool_calls <= 3
    assert outcome.turn.metrics.model_calls <= 5
    assert outcome.turn.fallback is True
    assert outcome.turn.answer == FALLBACK_ANSWER


def test_variant_is_fixed_per_thread() -> None:
    # Arrange
    service = make_service()
    thread_id = service.send("Hola", variant="agent").thread_id

    # Act / Assert
    with pytest.raises(ChatError) as error:
        service.send("¿Qué produce Manuelita?", thread_id=thread_id, variant="chain")
    assert error.value.code == "variant_mismatch"
    assert error.value.status_code == 409
