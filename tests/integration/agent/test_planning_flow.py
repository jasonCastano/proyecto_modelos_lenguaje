"""Flujo del planificador en el grafo del agente (spec 025, T021, US1).

Perfil planificador autorizado → ruta ``planning`` (reglas) → estado, compromisos y optimizador →
respuesta validada (o reemplazada por el ``plan_card``) → guardar con «SÍ».
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from proyecto_modelos_lenguaje.agent.memory import memory_store
from proyecto_modelos_lenguaje.agent.planning import DECISION_PHRASE, SYNTHETIC_LABEL
from tests.agent_helpers import make_service

QUESTION = "Tenemos 15 % menos caña esta semana. ¿Cómo cumplimos azúcar, etanol y energía?"
USER = "planner-1"


def _text(message: BaseMessage) -> str:
    return str(message.content)


class PlannerModel(BaseChatModel):
    """Agente guionizado: estado + compromisos → optimizar → responder (o guardar)."""

    mode: str = "good"

    @property
    def _llm_type(self) -> str:
        return "planner-test"

    def bind_tools(self, tools: Sequence[Any], **_kwargs: Any) -> PlannerModel:  # type: ignore[override]
        return self

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **_: Any
    ) -> ChatResult:
        last = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
        question = _text(messages[last])
        tools = [m for m in messages[last + 1 :] if isinstance(m, ToolMessage)]
        system = "\n".join(_text(m) for m in messages if isinstance(m, SystemMessage))
        if "guarda" in question.lower():
            if not tools:
                plan_id = re.search(r"p-[0-9a-f]{8}", system)
                assert plan_id, "la pista del agente debe traer el plan_id del hilo"
                return self._call("save_production_proposal", {"plan_id": plan_id.group(0)})
            return self._say(_text(tools[-1]))
        if not tools:
            return self._calls([("get_plant_state", {}), ("get_commitments", {})])
        if len(tools) == 2:
            return self._call("optimize_production_plan", {"cane_delta_pct": -15})
        card = _text(tools[-1])
        if self.mode == "good":
            margin = next(line for line in card.splitlines() if "Margen total" in line)
            return self._say(
                f"Recomiendo este programa. {margin} {SYNTHETIC_LABEL}. {DECISION_PHRASE}"
            )
        return self._say("El margen será de 987.654 millones; conviene producir solo azúcar.")

    @staticmethod
    def _say(text: str) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _call(self, name: str, args: dict[str, Any]) -> ChatResult:
        return self._calls([(name, args)])

    @staticmethod
    def _calls(calls: list[tuple[str, dict[str, Any]]]) -> ChatResult:
        message = AIMessage(
            content="",
            tool_calls=[{"name": name, "args": args, "id": f"call_{name}"} for name, args in calls],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.fixture
def planner_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    # Spec 027: en la web el planificador no exige autorización; ninguna variable hace falta.
    for var in ("MANUELITA_PLANNER_WEB", "MANUELITA_PLANNER_OPEN", "VALERIA_PLANNERS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path))
    return tmp_path


def _proposals(state_dir: Path) -> list[dict[str, Any]]:
    path = state_dir / "planning" / "proposals.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_planner_gets_validated_plan_and_saves_with_yes(planner_env: Path) -> None:
    # Arrange
    service = make_service(model=PlannerModel(), store=memory_store())

    # Act
    first = service.send(QUESTION, user_id=USER, variant="agent", profile="planificador")
    paused = service.send(
        "guarda esta propuesta", thread_id=first.thread_id, user_id=USER, variant="agent"
    )
    resumed = service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )

    # Assert: plan validado, perfil y traza
    turn = first.turn
    assert turn.route.route == "planning" and turn.route.decided_by == "rules"
    assert turn.profile == "planificador"
    names = [tool["name"] for tool in turn.tools]
    # Las dos consultas iniciales van en la misma llamada y corren en paralelo: su orden varía.
    assert set(names[:2]) == {"get_plant_state", "get_commitments"}
    assert names[2:] == ["optimize_production_plan"]
    assert SYNTHETIC_LABEL in turn.answer and DECISION_PHRASE in turn.answer
    assert turn.plan_steps[0] == "consultar estado de planta y compromisos"
    # Guardar: aprobación humana y plan tomado del hilo
    assert paused.status == "pending_approval"
    assert paused.pending_action["tool"] == "save_production_proposal"
    assert "Guardé la propuesta" in resumed.turn.answer
    saved = _proposals(planner_env)
    assert len(saved) == 1 and saved[0]["plan"]["status"] == "optimal"


def test_rejecting_the_proposal_writes_nothing(planner_env: Path) -> None:
    service = make_service(model=PlannerModel(), store=memory_store())
    first = service.send(QUESTION, user_id=USER, variant="agent", profile="planificador")
    paused = service.send(
        "guarda esta propuesta", thread_id=first.thread_id, user_id=USER, variant="agent"
    )
    service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="reject"
    )
    assert _proposals(planner_env) == []


def test_invented_numbers_are_replaced_by_the_plan_card(planner_env: Path) -> None:
    service = make_service(model=PlannerModel(mode="bad"), store=memory_store())
    outcome = service.send(QUESTION, user_id=USER, variant="agent", profile="planificador")
    answer = outcome.turn.answer
    assert "987.654" not in answer
    assert answer.startswith("Plan recomendado") and "plan_id: p-" in answer
    assert any("validación de cifras" in step for step in outcome.turn.plan_steps)


def test_any_web_user_plans_without_authorization(planner_env: Path) -> None:
    """Spec 027 (FR-003, FR-004): cualquier usuario web planifica con el perfil elegido."""
    service = make_service(model=PlannerModel(), store=memory_store())
    outcome = service.send(QUESTION, user_id="anon", variant="agent", profile="planificador")
    names = {tool["name"] for tool in outcome.turn.tools}
    assert outcome.turn.profile == "planificador" and outcome.turn.route.route == "planning"
    assert "optimize_production_plan" in names
    assert "autorizad" not in outcome.turn.answer


def test_self_introduced_planner_plans_on_the_web(planner_env: Path) -> None:
    service = make_service(model=PlannerModel(), store=memory_store())
    outcome = service.send(
        "Soy planificador de planta. " + QUESTION, user_id="anon", variant="agent"
    )
    assert outcome.turn.profile == "planificador" and outcome.turn.route.route == "planning"


def test_whatsapp_planner_is_open(planner_env: Path) -> None:
    """Spec 028 (D3, FR-021): en WhatsApp el planificador es libre, como en la web."""
    service = make_service(model=PlannerModel(), store=memory_store())
    outcome = service.send(
        QUESTION, user_id=USER, variant="agent", profile="planificador", channel="whatsapp"
    )
    assert outcome.turn.route.route == "planning"


def test_visitor_planning_question_activates_the_planner_for_that_turn(
    planner_env: Path,
) -> None:
    """Spec 028 (FR-022, FR-023): por contexto, sin cambiar de perfil; sigue en la repregunta."""
    service = make_service(model=PlannerModel(), store=memory_store())
    first = service.send(QUESTION, user_id="visitor", variant="agent", channel="whatsapp")
    names = {tool["name"] for tool in first.turn.tools}
    assert first.turn.route.route == "planning" and "optimize_production_plan" in names
    assert first.turn.profile == "planificador"  # perfil activo del turno
    assert SYNTHETIC_LABEL in first.turn.answer
    follow = service.send(
        "¿Y si baja 20 %?", thread_id=first.thread_id, user_id="visitor", variant="agent"
    )
    assert follow.turn.route.route == "planning"
    assert "repregunta" in follow.turn.route.reason


def test_informative_question_does_not_activate_the_planner(planner_env: Path) -> None:
    service = make_service(store=memory_store())
    outcome = service.send(
        "¿Qué programas sociales tiene Manuelita con los cultivadores de caña?",
        user_id="visitor",
        variant="agent",
    )
    assert outcome.turn.route.route != "planning" and outcome.turn.profile == "visitante"
