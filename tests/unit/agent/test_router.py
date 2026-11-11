"""Pruebas de la puerta de decisión (T028, FR-011, FR-015, SC-004)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.demo import build_demo_model
from proyecto_modelos_lenguaje.agent.models import RouteDecision
from proyecto_modelos_lenguaje.agent.router import (
    apply_structured_fallback,
    route_message,
    rule_decision,
)


class CountingModel:
    """Envuelve un modelo guionado y cuenta las llamadas."""

    def __init__(self, responses: list[str]) -> None:
        self.inner = build_demo_model(responses)
        self.calls = 0

    def invoke(self, messages):  # interfaz mínima de BaseChatModel
        self.calls += 1
        return self.inner.invoke(messages)


GREETINGS = [
    "Hola, buenas tardes",
    "Buenos días",
    "Gracias por la información",
    "Hasta luego",
    "¿Qué tal?",
    "Muchas gracias, eso es todo",
]
OUT_OF_SCOPE = [
    "¿Cuál es el precio del dólar hoy?",
    "¿Quién ganó el último mundial de fútbol?",
    "¿Qué clima hará mañana en Cali?",
    "Escríbeme una función en Python que ordene una lista",
]


@pytest.mark.parametrize("message", GREETINGS)
def test_smalltalk_is_direct_without_model_calls(message: str) -> None:
    # Arrange
    model = CountingModel(['{"route": "documental", "confidence": 0.9, "reason": "x"}'])

    # Act
    result = route_message(message, model=model)

    # Assert
    assert result.decision.route == "direct"
    assert result.decision.decided_by == "rules"
    assert result.model_calls == 0
    assert model.calls == 0


@pytest.mark.parametrize("message", OUT_OF_SCOPE)
def test_out_of_scope_is_ruled_without_model_calls(message: str) -> None:
    # Arrange
    model = CountingModel(['{"route": "documental", "confidence": 0.9, "reason": "x"}'])

    # Act
    result = route_message(message, model=model)

    # Assert
    assert result.decision.route == "out_of_scope"
    assert model.calls == 0


def test_greeting_with_a_real_question_is_not_direct() -> None:
    # Act / Assert
    assert rule_decision("Hola, ¿qué produce Manuelita en Perú?") is None
    assert rule_decision("¿Quién es el presidente de Manuelita?") is None


@pytest.mark.parametrize(
    ("raw", "route"),
    [
        ('{"route": "documental", "confidence": 0.88, "reason": "narrativa"}', "documental"),
        (
            'Claro: {"route": "structured", "confidence": 0.8, "reason": "dato", '
            '"alternative": "documental"}',
            "structured",
        ),
    ],
)
def test_llm_stage_parses_json_and_counts_one_call(raw: str, route: str) -> None:
    # Arrange
    model = CountingModel([raw])

    # Act
    result = route_message("¿Qué hace Manuelita en sostenibilidad?", model=model)

    # Assert
    assert result.decision.route == route
    assert result.decision.decided_by == "llm"
    assert result.model_calls == 1
    assert model.calls == 1


def test_low_confidence_becomes_clarify() -> None:
    # Arrange
    model = CountingModel(['{"route": "structured", "confidence": 0.45, "reason": "duda"}'])

    # Act
    result = route_message("¿Y la otra planta?", model=model, min_confidence=0.6)

    # Assert
    assert result.decision.route == "clarify"
    assert result.decision.alternative == "structured"


def test_invalid_llm_output_falls_back_to_heuristic() -> None:
    # Arrange
    model = CountingModel(["no sé qué responder"])

    # Act
    result = route_message("¿Qué cultiva Manuelita en Perú?", model=model)

    # Assert
    assert result.decision.route == "documental"
    assert "inválida" in result.decision.reason
    assert result.model_calls == 1


@pytest.mark.parametrize(
    ("message", "route"),
    [
        ("¿En qué año inició operaciones Manuelita en Colombia?", "structured"),
        ("¿Qué porcentaje accionario tiene Manuelita en Vale do Paraná?", "structured"),
        ("¿Qué cultiva Manuelita en Perú?", "documental"),
        ("¿Y eso cuánto es?", "clarify"),
        ("¿Cuál es mejor?", "clarify"),
    ],
)
def test_demo_heuristic_without_model(message: str, route: str) -> None:
    # Act
    result = route_message(message)

    # Assert
    assert result.decision.route == route
    assert result.model_calls == 0


def test_deictic_with_history_is_documental() -> None:
    # Act
    result = route_message(
        "¿Y a qué cliente le exporta esa uva?", history=["¿Qué cultiva en Perú?"]
    )

    # Assert
    assert result.decision.route == "documental"


def test_structured_without_rows_falls_back_to_documental() -> None:
    # Arrange
    decision = RouteDecision(route="structured", confidence=0.8, reason="dato", decided_by="llm")

    # Act
    empty = apply_structured_fallback(decision, rows_found=0)
    found = apply_structured_fallback(decision, rows_found=2)

    # Assert
    assert empty.route == "documental"
    assert empty.fallback_route == "documental"
    assert found.route == "structured"
