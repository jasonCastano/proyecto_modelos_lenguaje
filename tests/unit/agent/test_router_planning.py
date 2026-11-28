"""Ruta ``planning``: solo reglas y solo para el planificador autorizado (spec 025, T020, R3)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from proyecto_modelos_lenguaje.agent.router import (
    is_planning_request,
    llm_decision,
    planning_decision,
    route_message,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

BATTERY = PROJECT_ROOT / "tests" / "fixtures" / "agent" / "planning_scenarios.jsonl"
PUBLIC = [
    "¿Qué produce Manuelita?",
    "¿Cuánto creció la producción de bioetanol entre 2017 y 2021?",
    "Hola",
    "¿Qué programas sociales tiene la fundación?",
    "¿Cuál es la producción de azúcar de Manuelita?",
    # Spec 028: preguntas informativas sobre plantas reales (t04 de la batería de herramientas).
    "¿Cuál es la capacidad de la planta de biodiésel de Manuelita Aceites y Energía?",
    "¿Cuál es la capacidad de la planta de etanol de Manuelita?",
]


class PlanningLLM(BaseChatModel):
    """Clasificador que (mal) devuelve la ruta planning."""

    @property
    def _llm_type(self) -> str:
        return "planning-llm"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **_: Any
    ) -> ChatResult:
        payload = {"route": "planning", "confidence": 0.99, "reason": "x"}
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=json.dumps(payload)))]
        )


def test_battery_questions_are_planning_requests() -> None:
    for line in BATTERY.read_text(encoding="utf-8").splitlines():
        assert is_planning_request(json.loads(line)["question"])


@pytest.mark.parametrize("question", PUBLIC)
def test_public_questions_are_not_planning(question: str) -> None:
    assert not is_planning_request(question)


def test_planning_is_decided_by_context_for_anyone() -> None:
    """Spec 028 (R9): sin perfil ni autorización; solo reglas, por turno."""
    question = "Tenemos 15 % menos caña esta semana, ¿cómo cumplimos los contratos?"
    decision = planning_decision(question)
    assert decision is not None and decision.route == "planning" and decision.decided_by == "rules"
    assert planning_decision("¿Qué produce Manuelita?") is None


def test_follow_up_continues_only_after_a_planning_turn() -> None:
    assert planning_decision("¿Y si baja 20 %?") is None
    follow = planning_decision("¿Y si baja 20 %?", previous_route="planning")
    assert follow is not None and "repregunta" in follow.reason
    assert planning_decision("¿Qué produce Manuelita?", previous_route="planning") is None
    assert planning_decision("¿Y en 2022?", previous_route="planning") is None


def test_llm_classifier_never_returns_planning() -> None:
    with pytest.raises(ValueError):
        llm_decision("plan de producción", [], PlanningLLM())
    result = route_message("Planifica la producción de la semana", model=PlanningLLM())
    assert result.decision.route != "planning"
