"""Servicio de conversación de la API y la CLI (spec 014, US1, ``contracts/chat-api.md``).

Valida la solicitud, gestiona hilos (creación, existencia y variante fija) y ejecuta el grafo de la
variante pedida con el checkpointer común. Los grafos se construyen una vez por variante y modo.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, Command

from ..rag.hybrid import HybridRetriever
from .actions import ActionArgsError, validate_args
from .config import AgentConfig
from .demo import DemoChatModel
from .graph import (
    ChatUnavailableError,
    GraphDeps,
    TurnMetricsHandler,
    build_agent_graph,
    build_chain_graph,
)
from .memory import UserMemory
from .models import Decision, PendingAction, RouteDecision, Turn
from .privacy import redact_pii
from .structured import StructuredError, StructuredStore

Variant = Literal["chain", "agent"]
Mode = Literal["real", "demo"]
MESSAGE_MAX_CHARS = 500
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


INTERRUPT_CHANNEL = "__interrupt__"
FORGET_MESSAGE = "Olvida mis preferencias guardadas"


def pending_from_interrupt(item: Any, timestamp: str | None) -> dict[str, Any]:
    """Convierte el ``interrupt`` de HITL (cadena o middleware) en ``PendingAction``."""
    value = getattr(item, "value", item) or {}
    request = (value.get("action_requests") or [{}])[0]
    extra = {"proposed_at": timestamp} if timestamp else {}
    action = PendingAction(
        action_id=str(getattr(item, "id", "") or "act"),
        tool=request.get("name"),
        args=dict(request.get("args") or {}),
        **extra,
    )
    return action.model_dump(mode="json")


class ChatError(Exception):
    """Error de contrato con código, mensaje y estado HTTP sugerido."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(slots=True)
class ChatOutcome:
    thread_id: str
    turn: Turn
    status: str
    pending_action: dict[str, Any] | None = None
    anomalies: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "turn": self.turn.model_dump(mode="json"),
            "status": self.status,
            "pending_action": self.pending_action,
            "anomalies": self.anomalies,
        }


def validate_message(message: str) -> str:
    text = (message or "").strip()
    if not text:
        raise ChatError("empty_question", "El mensaje no puede estar vacío.", 400)
    if len(text) > MESSAGE_MAX_CHARS:
        raise ChatError(
            "question_too_long", f"El mensaje supera {MESSAGE_MAX_CHARS} caracteres.", 400
        )
    if CONTROL_CHARS.search(text):
        raise ChatError("invalid_message", "El mensaje contiene caracteres de control.", 400)
    return text


def validate_user_id(user_id: str) -> str:
    if not USER_ID_PATTERN.match(user_id or ""):
        raise ChatError(
            "invalid_user_id", "user_id debe tener 1 a 64 caracteres [A-Za-z0-9-].", 400
        )
    return user_id


def turn_status(turn: Turn) -> str:
    if turn.route.route == "clarify":
        return "clarify"
    return "fallback" if turn.fallback else "answered"


def anomalies_of(turn: Turn) -> list[dict[str, Any]]:
    return [
        {
            "label": fragment.get("label"),
            "unit_id": fragment.get("unit_id"),
            "reasons": fragment.get("anomaly_reasons", []),
        }
        for fragment in turn.fragments
        if fragment.get("anomalous")
    ]


def open_store(config: AgentConfig) -> StructuredStore | None:
    """Tabla estructurada si existe y es válida; si no, el agente usa solo documentos."""
    try:
        return StructuredStore(config.structured_path)
    except StructuredError:
        return None


def build_deps(mode: Mode, config: AgentConfig, retriever: HybridRetriever | None) -> GraphDeps:
    """Dependencias por modo: demo determinista sin red, o DeepSeek con la configuración del LLM."""
    store = open_store(config)
    if mode == "demo":
        return GraphDeps(config, retriever, store, DemoChatModel())
    from ..llm import build_chat_model, load_llm_config

    model = build_chat_model(load_llm_config())
    return GraphDeps(config, retriever, store, model, router_model=model, summary_model=model)


class ChatService:
    """Punto único para enviar mensajes, leer hilos y resolver acciones pendientes."""

    def __init__(
        self,
        config: AgentConfig,
        checkpointer: Checkpointer,
        deps_factory: Callable[[Mode], GraphDeps],
        store: BaseStore | None = None,
    ) -> None:
        self.config = config
        self.checkpointer = checkpointer
        self.store = store
        self._deps_factory = deps_factory
        self._graphs: dict[tuple[str, str], Any] = {}
        self._deps: dict[str, GraphDeps] = {}

    def deps(self, mode: Mode) -> GraphDeps:
        """Dependencias de un modo, cargadas una vez y compartidas por ambas variantes."""
        if mode not in self._deps:
            self._deps[mode] = self._deps_factory(mode)
        return self._deps[mode]

    def graph(self, variant: Variant, mode: Mode):
        key = (variant, mode)
        if key not in self._graphs:
            deps = self.deps(mode)
            builder = build_agent_graph if variant == "agent" else build_chain_graph
            self._graphs[key] = builder(deps, self.checkpointer, self.store)
        return self._graphs[key]

    @staticmethod
    def _config(thread_id: str, handler: TurnMetricsHandler | None = None) -> dict[str, Any]:
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        if handler is not None:
            config["callbacks"] = [handler]
        return config

    def _load(self, thread_id: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Estado del hilo y su acción pendiente (si el grafo quedó en ``interrupt``)."""
        saved = self.checkpointer.get_tuple(self._config(thread_id))
        if saved is None:
            raise ChatError("thread_not_found", "No existe ese hilo de conversación.", 404)
        values = dict(saved.checkpoint.get("channel_values") or {})
        interrupts = [
            item
            for _task, channel, value in (saved.pending_writes or [])
            if channel == INTERRUPT_CHANNEL
            for item in (value if isinstance(value, (list, tuple)) else [value])
        ]
        timestamp = saved.checkpoint.get("ts")
        pending = pending_from_interrupt(interrupts[0], timestamp) if interrupts else None
        return values, pending

    def _invoke(self, variant: Variant, mode: Mode, payload: Any, thread_id: str) -> Any:
        handler = TurnMetricsHandler()
        try:
            return self.graph(variant, mode).invoke(payload, self._config(thread_id, handler))
        except ChatUnavailableError as exc:
            raise ChatError("index_unavailable", str(exc), 503) from exc

    def _outcome(self, thread_id: str, result: dict[str, Any]) -> ChatOutcome:
        interrupts = result.get(INTERRUPT_CHANNEL) or []
        if interrupts:
            turns = result.get("turns") or []
            turn = Turn(
                turn_id=len(turns) + 1,
                question=result["question"],
                route=RouteDecision.model_validate(result["decision"]),
            )
            pending = pending_from_interrupt(interrupts[0], None)
            return ChatOutcome(thread_id, turn, "pending_approval", pending_action=pending)
        turn = Turn.model_validate(result["turns"][-1])
        return ChatOutcome(thread_id, turn, turn_status(turn), anomalies=anomalies_of(turn))

    def send(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        user_id: str = "anon",
        variant: Variant = "chain",
        mode: Mode = "demo",
    ) -> ChatOutcome:
        question = redact_pii(validate_message(message))
        validate_user_id(user_id)
        state: dict[str, Any] = {"question": question, "mode": mode}
        if thread_id is None:
            thread_id = str(uuid.uuid4())
            state.update(
                variant=variant, user_id=user_id, turns=[], summary="", summarized=0, actions=[]
            )
        else:
            values, pending = self._load(thread_id)
            if values.get("variant", variant) != variant:
                raise ChatError(
                    "variant_mismatch",
                    f"El hilo usa la variante «{values.get('variant')}»; abre uno nuevo.",
                    409,
                )
            if pending is not None:
                raise ChatError(
                    "thread_pending_approval", "El hilo tiene una acción por aprobar.", 409
                )
        result = self._invoke(variant, mode, state, thread_id)
        return self._outcome(thread_id, result)

    def resume(
        self,
        thread_id: str,
        *,
        action_id: str,
        decision: Decision,
        args: dict[str, Any] | None = None,
    ) -> ChatOutcome:
        """Registra la decisión humana y continúa el hilo (``Command(resume=...)``)."""
        values, pending = self._load(thread_id)
        if pending is None:
            raise ChatError("no_pending_action", "El hilo no tiene acciones por aprobar.", 409)
        if action_id != pending["action_id"]:
            raise ChatError("action_mismatch", "La acción no corresponde a la pendiente.", 409)
        final_args = pending["args"]
        payload: dict[str, Any] = {"type": decision}
        if decision == "edit":
            try:
                final_args = validate_args(pending["tool"], args or {})
            except ActionArgsError as exc:
                raise ChatError("invalid_args", str(exc), 400) from exc
            payload["edited_action"] = {"name": pending["tool"], "args": final_args}
        elif decision == "reject":
            payload["message"] = "La persona revisora rechazó la acción; no se ejecutó."
        variant = values.get("variant", "chain")
        mode = values.get("mode", "demo")
        result = self._invoke(variant, mode, Command(resume={"decisions": [payload]}), thread_id)
        record = {
            **pending,
            "args": final_args,
            "decision": decision,
            "decided_at": datetime.now(UTC).isoformat(),
        }
        if not result.get(INTERRUPT_CHANNEL):
            self.graph(variant, mode).update_state(
                self._config(thread_id),
                {"actions": [*(values.get("actions") or []), record]},
                as_node="finalize",
            )
        return self._outcome(thread_id, result)

    def preferences(self, user_id: str) -> dict[str, Any]:
        """``GET /api/memory/{user_id}``: preferencias vigentes (las expiradas se borran)."""
        validate_user_id(user_id)
        if self.store is None:
            return {"user_id": user_id, "items": []}
        memory = UserMemory(self.store, self.config.memory.preference_ttl_days)
        return {"user_id": user_id, "items": [item.to_dict() for item in memory.list(user_id)]}

    def request_forget(self, user_id: str, thread_id: str) -> ChatOutcome:
        """``DELETE /api/memory/{user_id}``: propone ``forget_memory`` en el hilo; no borra aún."""
        validate_user_id(user_id)
        values, _pending = self._load(thread_id)
        if values.get("user_id") != user_id:
            raise ChatError("thread_not_found", "No existe ese hilo para este usuario.", 404)
        return self.send(
            FORGET_MESSAGE,
            thread_id=thread_id,
            user_id=user_id,
            variant=values.get("variant", "chain"),
            mode=values.get("mode", "demo"),
        )

    def thread(self, thread_id: str) -> dict[str, Any]:
        values, pending = self._load(thread_id)
        return {
            "thread_id": thread_id,
            "variant": values.get("variant", "chain"),
            "turns": values.get("turns") or [],
            "summary": values.get("summary") or "",
            "status": "pending_approval" if pending else "idle",
            "pending_action": pending,
            "actions": values.get("actions") or [],
        }
