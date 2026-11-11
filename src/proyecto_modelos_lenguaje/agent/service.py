"""Servicio de conversación de la API y la CLI (spec 014, US1, ``contracts/chat-api.md``).

Valida la solicitud, gestiona hilos (creación, existencia y variante fija) y ejecuta el grafo de la
variante pedida con el checkpointer común. Los grafos se construyen una vez por variante y modo.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from langgraph.types import Checkpointer

from ..rag.hybrid import HybridRetriever
from .config import AgentConfig
from .demo import DemoChatModel
from .graph import (
    ChatUnavailableError,
    GraphDeps,
    TurnMetricsHandler,
    build_agent_graph,
    build_chain_graph,
)
from .models import Turn
from .structured import StructuredError, StructuredStore

Variant = Literal["chain", "agent"]
Mode = Literal["real", "demo"]
MESSAGE_MAX_CHARS = 500
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


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
    """Punto único para enviar mensajes y leer hilos."""

    def __init__(
        self,
        config: AgentConfig,
        checkpointer: Checkpointer,
        deps_factory: Callable[[Mode], GraphDeps],
    ) -> None:
        self.config = config
        self.checkpointer = checkpointer
        self._deps_factory = deps_factory
        self._graphs: dict[tuple[str, str], Any] = {}

    def graph(self, variant: Variant, mode: Mode):
        key = (variant, mode)
        if key not in self._graphs:
            deps = self._deps_factory(mode)
            builder = build_agent_graph if variant == "agent" else build_chain_graph
            self._graphs[key] = builder(deps, self.checkpointer)
        return self._graphs[key]

    def _values(self, thread_id: str) -> dict[str, Any] | None:
        saved = self.checkpointer.get_tuple({"configurable": {"thread_id": thread_id}})
        if saved is None:
            return None
        return dict(saved.checkpoint.get("channel_values") or {})

    def send(
        self,
        message: str,
        *,
        thread_id: str | None = None,
        user_id: str = "anon",
        variant: Variant = "chain",
        mode: Mode = "demo",
    ) -> ChatOutcome:
        question = validate_message(message)
        validate_user_id(user_id)
        state: dict[str, Any] = {"question": question}
        if thread_id is None:
            thread_id = str(uuid.uuid4())
            state.update(
                {
                    "variant": variant,
                    "user_id": user_id,
                    "turns": [],
                    "summary": "",
                    "summarized": 0,
                }
            )
        else:
            values = self._values(thread_id)
            if values is None:
                raise ChatError("thread_not_found", "No existe ese hilo de conversación.", 404)
            if values.get("variant", variant) != variant:
                raise ChatError(
                    "variant_mismatch",
                    f"El hilo usa la variante «{values.get('variant')}»; abre uno nuevo.",
                    409,
                )
            if values.get("pending_action"):
                raise ChatError(
                    "thread_pending_approval", "El hilo tiene una acción por aprobar.", 409
                )
        handler = TurnMetricsHandler()
        try:
            result = self.graph(variant, mode).invoke(
                state, {"configurable": {"thread_id": thread_id}, "callbacks": [handler]}
            )
        except ChatUnavailableError as exc:
            raise ChatError("index_unavailable", str(exc), 503) from exc
        turn = Turn.model_validate(result["turns"][-1])
        return ChatOutcome(thread_id, turn, turn_status(turn), anomalies=anomalies_of(turn))

    def thread(self, thread_id: str) -> dict[str, Any]:
        values = self._values(thread_id)
        if values is None:
            raise ChatError("thread_not_found", "No existe ese hilo de conversación.", 404)
        pending = values.get("pending_action")
        return {
            "thread_id": thread_id,
            "variant": values.get("variant", "chain"),
            "turns": values.get("turns") or [],
            "summary": values.get("summary") or "",
            "status": "pending_approval" if pending else "idle",
            "pending_action": pending,
        }
