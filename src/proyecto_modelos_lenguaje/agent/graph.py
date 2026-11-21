"""Grafos conversacionales del agente (spec 014, US1, FR-001 a FR-008).

Dos variantes comparables sobre el mismo estado de hilo (``ChatState``) y el mismo checkpointer:

- **Cadena** (``build_chain_graph``): ``route → retrieve → answer → finalize``. Recupera según la
  ruta (documentos, tabla estructurada o ambas en la ruta ``mixed``) y responde con una sola
  llamada (más un reintento si faltan citas).
- **Agente** (``build_agent_graph``): ``route → agent → finalize``. El agente de
  ``langchain.agents.create_agent`` decide cuándo y cuántas veces buscar, con
  ``ToolCallLimitMiddleware`` y ``ModelCallLimitMiddleware``.

En ambas, la puerta de decisión resuelve saludos, preguntas ajenas y mensajes ambiguos sin buscar
(``reply``), y ``finalize`` registra el turno visible, sus métricas y el resumen de memoria.

Desviación del plan: el checkpointer vive en el grafo exterior y el agente se invoca como subgrafo
(hereda el checkpointer), para que ambas variantes compartan la forma del estado y del turno.
"""

from __future__ import annotations

import queue
import re
import threading
import time
import zlib
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextvars import copy_context
from dataclasses import dataclass
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    ModelCallLimitMiddleware,
    ModelRequest,
    ToolCallLimitMiddleware,
    dynamic_prompt,
)
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig, RunnablePassthrough
from langchain_core.runnables.config import merge_configs
from langgraph.config import get_store, get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, interrupt

from ..rag.hybrid import HybridRetriever, RetrievedFragment
from ..tasks import FALLBACK_ANSWER, STRICT_REMINDER, is_model_fallback
from . import bridges, care
from .actions import (
    TOOL_DESCRIPTIONS,
    WRITE_TOOLS,
    build_write_tools,
    detect_write_intent,
    execute_action,
    extract_profile,
    is_profile_question,
)
from .config import AgentConfig
from .guard import GuardedDocument, leaks_prompt, render_documents
from .identity import (
    MAX_THREAD_ATTEMPTS,
    IdentityRegistry,
    extract_name,
    looks_like_name,
    names_match,
)
from .memory import (
    PROFILE_KEYS,
    PROFILE_LABELS,
    UserMemory,
    UserProfile,
    build_summarization_middleware,
    compact_history,
    recent_within_budget,
    render_preferences,
    render_profile,
    render_turn,
    turns_to_keep,
)
from .models import RouteDecision, Turn, TurnMetrics
from .plan import TurnPlan, build_plan
from .privacy import build_pii_middleware
from .prompts import load_agent_prompt, load_care, load_conduct, load_converse
from .review import (
    LOCAL_CHECKS,
    RETRIEVAL_CHECKS,
    ReviewVerdict,
    correction_note,
    drop_flagged_sentences,
    evidence_text,
    missing_required,
    review,
    review_sentence,
    similarity,
    trim_sentences,
)
from .router import (
    AI_QUESTION,
    COMPANY,
    apply_structured_fallback,
    contextual_query,
    route_message,
)
from .sentences import SentenceGate, SentenceSplitter, split_all
from .series import SeriesTable, series_intent
from .structured import StructuredFact, StructuredStore, normalize
from .tools import (
    ToolTrace,
    aggregate_series_impl,
    build_read_tools,
    count_fact,
    count_intent,
    fact_document,
    query_structured_impl,
    search_documents_impl,
)

LABEL_PATTERN = re.compile(r"\[([UF]\d+)\]")
ROUTER_HISTORY_TURNS = 3
FAREWELL = re.compile(r"\b(gracias|adios|chao|hasta luego|hasta pronto|nos vemos|eso es todo)\b")
# Spec 018: respuestas deterministas de Valer-IA Caña, versionadas en prompts/conduct.md.
SENSITIVE_NOTICES = frozenset({"credit_card", "document", "phone"})
IDENTITY_STAGE_NONE: dict[str, Any] = {"stage": "none", "attempts": 0, "offered": False}


def conduct(key: str, **values: str) -> str:
    """Texto de ``prompts/conduct.md`` con ``{name}`` / ``{masked}`` reemplazados."""
    sections = load_conduct()
    text = sections.get(key) or sections["off_topic"]
    for name, value in values.items():
        text = text.replace("{" + name + "}", value)
    return text


NO_RETRIEVAL_ROUTES = frozenset({"direct", "out_of_scope", "clarify"})
REVIEW_DECISIONS = ["approve", "edit", "reject"]
REJECTED_ANSWER = "Entendido: no realicé la acción porque fue rechazada en la revisión."
PROFILE_UNKNOWN_ANSWER = (
    "Todavía no sé eso de ti: no me lo has contado en esta conversación ni está guardado en tu "
    "perfil. Si quieres, cuéntamelo; por ejemplo: «Me llamo Laura y soy docente»."
)


class ChatUnavailableError(RuntimeError):
    """El índice de recuperación no está disponible para responder."""


class ChatState(TypedDict, total=False):
    """Estado persistido de un hilo (``data-model.md`` §5) más los campos del turno en curso."""

    variant: str
    user_id: str
    mode: str
    turns: list[dict[str, Any]]
    summary: str
    summarized: int
    pending_action: dict[str, Any] | None
    question: str
    decision: dict[str, Any]
    fragments: list[dict[str, Any]]
    structured_rows: list[dict[str, Any]]
    evidence: dict[str, dict[str, Any]]
    context: str
    answer: str
    citations: list[dict[str, Any]]
    fallback: bool
    retrievals: int
    intent: dict[str, Any] | None
    actions: list[dict[str, Any]]
    profile_query: bool
    # spec 018: identidad conversacional, avisos de datos sensibles y cliente para la respuesta
    identity: dict[str, Any]
    identity_event: dict[str, Any] | None
    pii_notice: list[str]
    client: dict[str, Any] | None
    identity_next: str
    notices: list[str]
    # spec 019: atención (rachas y variantes del hilo), señales del turno y registro del contacto
    care: dict[str, Any]
    care_signals: dict[str, Any] | None
    contact: dict[str, Any]
    # spec 020: memoria del hilo, plan del turno y resultado de la revisión
    conversation: dict[str, Any]
    plan: dict[str, Any] | None
    reviewed: str
    bridged: dict[str, Any] | None
    turn_notices: list[str]
    # spec 021: frases previas, frases entregadas por el nodo que genera y frases descartadas
    lead: list[str]
    delivered: list[str]
    discarded: int


@dataclass(slots=True)
class GraphDeps:
    """Dependencias ya cargadas (una vez por variante y modo)."""

    config: AgentConfig
    retriever: HybridRetriever | None
    store: StructuredStore | None
    model: BaseChatModel
    router_model: BaseChatModel | None = None
    summary_model: BaseChatModel | None = None
    neutralize: bool = True  # spec 015: neutraliza instrucciones embebidas (False = línea base)
    series: SeriesTable | None = None


class TurnMetricsHandler(BaseCallbackHandler):
    """Callback común a ambos grafos: latencia, llamadas al modelo y tokens del turno (T044)."""

    raise_error = False

    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.model_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def on_chat_model_start(self, *_args: Any, **_kwargs: Any) -> None:
        self.model_calls += 1

    def on_llm_start(self, *_args: Any, **_kwargs: Any) -> None:
        self.model_calls += 1

    def on_llm_end(self, response: LLMResult, **_kwargs: Any) -> None:
        for generations in response.generations:
            for generation in generations:
                usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
                if usage:
                    self.input_tokens += int(usage.get("input_tokens", 0) or 0)
                    self.output_tokens += int(usage.get("output_tokens", 0) or 0)

    def snapshot(self, tool_calls: int) -> TurnMetrics:
        return TurnMetrics(
            latency_ms=round((time.perf_counter() - self.started) * 1000),
            model_calls=self.model_calls,
            tool_calls=tool_calls,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


def find_metrics_handler(config: RunnableConfig | None) -> TurnMetricsHandler | None:
    callbacks = (config or {}).get("callbacks")
    if isinstance(callbacks, list):
        candidates: Sequence[Any] = callbacks
    else:
        candidates = [
            *(getattr(callbacks, "handlers", None) or []),
            *(getattr(callbacks, "inheritable_handlers", None) or []),
        ]
    return next((h for h in candidates if isinstance(h, TurnMetricsHandler)), None)


# ---------------------------------------------------------------- evidencia y citas


def _fragment_payload(label: str, fragment: RetrievedFragment) -> dict[str, Any]:
    return {"label": label, **fragment.to_dict()}


def _row_payload(label: str, fact: StructuredFact) -> dict[str, Any]:
    payload = fact.to_dict()
    payload.pop("snippet", None)
    return {"label": label, **payload}


def collect_evidence(
    fragments: Sequence[RetrievedFragment], facts: Sequence[StructuredFact]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Etiqueta fragmentos (``U#``) y hechos (``F#``) y arma el mapa de citas válidas."""
    fragment_rows = [_fragment_payload(f"U{i}", f) for i, f in enumerate(fragments, start=1)]
    fact_rows = [_row_payload(f"F{i}", f) for i, f in enumerate(facts, start=1)]
    evidence: dict[str, dict[str, Any]] = {}
    for row in fragment_rows:
        evidence[row["label"]] = {
            "label": row["label"],
            "unit_id": row["unit_id"],
            "url": row["url"],
            "title": row["title"],
        }
    for row, fact in zip(fact_rows, facts, strict=True):
        first = fact.citations[0] if fact.citations else None
        evidence[row["label"]] = {
            "label": row["label"],
            "unit_id": fact.unit_id,
            "fact_id": fact.fact_id,
            "url": first.url if first else "",
            "title": first.title if first else fact.subject_label,
        }
    return fragment_rows, fact_rows, evidence


def validate_answer(
    text: str, evidence: dict[str, dict[str, Any]], prompt_text: str = ""
) -> tuple[str, list[dict[str, Any]], bool]:
    """Toda respuesta factual cita evidencia válida o pasa a fallo de evidencia (SC-003).

    Una respuesta que reproduce el system prompt también se descarta (FR-016).
    """
    if not text.strip() or is_model_fallback(text) or leaks_prompt(text, prompt_text):
        return FALLBACK_ANSWER, [], True
    labels = list(dict.fromkeys(LABEL_PATTERN.findall(text)))
    citations = [evidence[label] for label in labels if label in evidence]
    if not citations:
        return FALLBACK_ANSWER, [], True
    return text.strip(), citations, False


def message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content
        )
    return str(content)


# ---------------------------------------------------------------- nodos comunes


def _previous_question(state: ChatState) -> str | None:
    turns = state.get("turns") or []
    return turns[-1]["question"] if turns else None


def _recent_turns(state: ChatState, deps: GraphDeps) -> list[dict[str, Any]]:
    turns = state.get("turns") or []
    start = max(state.get("summarized", 0), len(turns) - turns_to_keep(deps.config.memory))
    return turns[start:]


def hitl_request(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Solicitud de revisión con la misma forma que la de ``HumanInTheLoopMiddleware``."""
    return {
        "action_requests": [
            {"name": tool, "args": dict(args), "description": TOOL_DESCRIPTIONS[tool]}
        ],
        "review_configs": [{"action_name": tool, "allowed_decisions": REVIEW_DECISIONS}],
    }


def _route_node(deps: GraphDeps):
    def route(state: ChatState) -> dict[str, Any]:
        care_config = deps.config.care
        care_state = care.copy_care_state(state.get("care"))
        signals: care.CareSignals | None = None
        guided = care_config.enabled and deps.config.conversation.guided
        if care_config.enabled:
            signals = care.analyze(state["question"], care_state, care_config)
            signals["guided"] = guided  # type: ignore[typeddict-unknown-key]
            care.update_counters(signals, care_state, care_config)
        intent = detect_write_intent(state["question"], deps.router_model)
        profile_query = intent is None and is_profile_question(state["question"])
        if intent is not None:
            decision = RouteDecision(
                route="direct",
                confidence=1.0,
                reason=f"pedido de escritura: {intent.tool} (requiere aprobación)",
                decided_by="rules",
            )
        elif profile_query:
            decision = RouteDecision(
                route="direct",
                confidence=0.95,
                reason="pregunta sobre el propio usuario: se responde con la memoria, sin buscar",
                decided_by="rules",
            )
        else:
            history = [t["question"] for t in (state.get("turns") or [])[-ROUTER_HISTORY_TURNS:]]
            decision = route_message(
                routed_text(state["question"], signals),
                history=history,
                model=deps.router_model,
                min_confidence=deps.config.router.min_confidence,
                temperature=deps.config.router.llm_temperature,
                signals=signals,
            ).decision
            decision = _apply_care(decision, signals, care_state)
        plan: dict[str, Any] | None = None
        if guided and intent is None:
            turn_plan = _turn_plan(deps, state, signals, decision, profile_query)
            if signals is not None and turn_plan.act and decision.act is None:
                decision = decision.model_copy(update={"act": turn_plan.act})
            plan = turn_plan.to_state()
            plan["node"] = (
                "converse" if _goes_to_converse(decision, profile_query) else decision.route
            )
        lead, lead_notices = _lead(deps, state, signals, decision, care_state, plan)
        return {
            "lead": lead,
            "delivered": [],
            "discarded": 0,
            "care": care_state,
            "care_signals": signals,
            "intent": intent.to_dict() if intent else None,
            "profile_query": profile_query,
            "plan": plan,
            "reviewed": "show",
            "bridged": None,
            "turn_notices": lead_notices,
            "decision": decision.model_dump(mode="json"),
            "fragments": [],
            "structured_rows": [],
            "evidence": {},
            "context": "",
            "answer": "",
            "citations": [],
            "fallback": False,
            "retrievals": 0,
        }

    return route


def _lead(
    deps: GraphDeps,
    state: ChatState,
    signals: care.CareSignals | None,
    decision: RouteDecision,
    care_state: care.CareState,
    plan: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    """Frases que van antes del texto del modelo en la entrega por frases (spec 021, R8).

    Solo en los turnos que genera el modelo (``converse`` o búsqueda); en los demás, ``finalize``
    arma la respuesta completa como antes.
    """
    generated = plan is not None and (
        plan.get("node") == "converse" or decision.route in RETRIEVAL_ROUTES
    )
    if not deps.config.conversation.sentences or not generated:
        return [], []
    texts, notices = care.prefixes(
        signals, decision.model_dump(mode="json"), load_care(), care_state, guided=True
    )
    lead = list(texts)
    if SENSITIVE_NOTICES & set(state.get("pii_notice") or []):
        lead.insert(0, conduct("sensitive_notice"))
        notices = [*notices, "sensitive_data"]
    return lead, list(notices)


def routed_text(question: str, signals: care.CareSignals | None) -> str:
    """Con varias solicitudes, el enrutador ve solo las partes de Manuelita (spec 019, R7)."""
    parts = care.manuelita_parts(signals)
    if signals and len(signals.get("requests") or []) > 1 and parts:
        return "; ".join(part["text"] for part in parts)
    return question


RETRIEVAL_ROUTES = ("documental", "structured", "mixed")


def _apply_care(
    decision: RouteDecision, signals: care.CareSignals | None, care_state: care.CareState
) -> RouteDecision:
    """Emoción propuesta por el LLM y una sola aclaración seguida (spec 019, R3 y R10)."""
    if signals is None:
        return decision
    if signals.get("sentiment") == "neutral" and decision.sentiment not in {None, "neutral"}:
        signals["sentiment"] = str(decision.sentiment)
    if decision.route != "clarify":
        care_state["clarify_streak"] = 0
        return decision
    if care_state["clarify_streak"] >= 1:
        # Ya se pidió una aclaración: se responde con la interpretación más probable.
        care_state["clarify_streak"] = 0
        signals["best_guess"] = True
        alternative = decision.alternative if decision.alternative in RETRIEVAL_ROUTES else None
        return decision.model_copy(
            update={
                "route": alternative or "documental",
                "reason": "ambigüedad repetida: se usa la interpretación más probable",
            }
        )
    care_state["clarify_streak"] += 1
    return decision


def _after_route(state: ChatState) -> str:
    if state.get("intent"):
        return "action"
    if state["decision"]["route"] not in NO_RETRIEVAL_ROUTES:
        return "work"
    return "converse" if (state.get("plan") or {}).get("node") == "converse" else "reply"


# ---------------------------------------------------------------- spec 020: conversación guiada

# Respuestas que siguen siendo fijas en el modo guiado (R2): seguridad, privacidad e identidad.
FIXED_REASONS = frozenset(
    {"crisis", "third_party", "prompt_extraction", "harmful", "abuse", "identity"}
)


def _goes_to_converse(decision: RouteDecision, profile_query: bool) -> bool:
    """Orden de decisión de C §1: lo que no es seguridad, perfil ni búsqueda va a ``converse``."""
    if profile_query or decision.route not in NO_RETRIEVAL_ROUTES:
        return False
    return decision.scope_reason not in FIXED_REASONS


def _turn_plan(
    deps: GraphDeps,
    state: ChatState,
    signals: care.CareSignals | None,
    decision: RouteDecision,
    profile_query: bool = False,
) -> TurnPlan:
    """Plan del turno (R4) y, si se permite, el puente elegido (R5)."""
    memory = care.copy_conversation(state.get("conversation"))
    payload = decision.model_dump(mode="json")
    topic = None
    if decision.scope_reason in {"off_topic", "advice"}:
        topic = care.topic_label(signals, payload)[0]
    elif decision.scope_reason == "unattainable":
        kind = decision.kind or care._first_unattainable(signals) or "commitment"
        topic = care.UNATTAINABLE_LABELS.get(str(kind))
    turn = len(state.get("turns") or []) + 1
    turn_plan = build_plan(
        signals,
        payload,
        memory,
        deps.config.conversation,
        turn=turn,
        has_evidence=decision.route not in NO_RETRIEVAL_ROUTES,
        topic=topic,
    )
    if not _goes_to_converse(decision, profile_query):
        return turn_plan
    allowed = bridges.eligible(
        turn_plan.act,
        turn_plan.sentiment,
        memory,
        deps.config.conversation,
        reason=decision.scope_reason,
    )
    choice = None
    if allowed:
        playbook = load_care()
        text, key = bridges.topic_of(signals)
        options = bridges.candidates(text, key, playbook, deps.retriever, deps.config.conversation)
        choice = bridges.select(options, memory)
    return turn_plan.with_bridge(choice, allowed and choice is not None)


def _bridge_evidence(plan: TurnPlan | None) -> dict[str, dict[str, Any]]:
    if plan is None or plan.bridge is None:
        return {}
    bridge = plan.bridge
    return {
        "U1": {"label": "U1", "unit_id": bridge.unit_id, "url": bridge.url, "title": bridge.title}
    }


def _recent_answers(state: ChatState, window: int) -> list[str]:
    return [str(t.get("answer") or "") for t in (state.get("turns") or [])[-window:]]


def _thread_seed(config: RunnableConfig | None, turn: int, attempt: int) -> int:
    thread = str(((config or {}).get("configurable") or {}).get("thread_id") or "")
    return zlib.crc32(f"{thread}:{turn}:{attempt}".encode())


_PENALTIES_SUPPORTED = {"value": True}


def _converse_model(deps: GraphDeps, length: str, act: str = "") -> Runnable:
    settings = deps.config.conversation
    max_tokens = 80 if length == "short" else settings.converse_max_tokens
    temperature = settings.temperature_social
    if act in {"minimal", "thanks"}:
        # Respuestas de una frase: más libertad para no converger en la misma fórmula (SC-002).
        temperature = min(1.0, temperature + 0.2)
    kwargs: dict[str, Any] = {"temperature": temperature, "max_tokens": max_tokens}
    if _PENALTIES_SUPPORTED["value"]:
        kwargs.update(
            presence_penalty=settings.presence_penalty,
            frequency_penalty=settings.frequency_penalty,
        )
    return deps.model.bind(**kwargs)


def _invoke_with_timeout(
    runnable: Runnable, messages: list[BaseMessage], config: RunnableConfig, seconds: float
) -> str:
    """Llamada al modelo con tiempo de espera; el error o el vencimiento llevan al respaldo."""
    context = copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(context.run, runnable.invoke, messages, config)
        try:
            return message_text(future.result(timeout=seconds))
        except FutureTimeout as exc:
            raise TimeoutError("el modelo no respondió a tiempo") from exc


OPENINGS = (
    "empieza reaccionando a lo que dijo con una expresión breve y espontánea",
    "empieza con la respuesta directa, sin preámbulo",
    "empieza con una frase cálida y personal dirigida al visitante",
    "empieza reconociendo la situación o el interés del visitante con tus palabras",
    "empieza con un comentario ligero y amable sobre lo que dijo",
    "empieza con una pregunta corta que muestre interés, y luego responde",
)


MINIMAL_OPENINGS = (
    "sigue el ritmo con una expresión breve y alegre, sin repetir la risa del visitante",
    "responde con una frase corta y cálida que invite a seguir",
    "responde con una palabra de asentimiento y una pregunta muy breve",
    "responde con un emoji amable y media frase",
    "responde con complicidad ligera, en pocas palabras",
    "responde con una frase corta que deje la puerta abierta sin ofrecer temas",
)


def opening_hint(plan: TurnPlan, seed: int) -> str:
    """Apertura sugerida por hilo y turno (spec 020, SC-002): rompe la fórmula repetida."""
    options = list(OPENINGS)
    if plan.sentiment in {"frustrated", "angry", "distressed"}:
        options = [options[3], options[2]]  # con molestia, primero la emoción
    elif plan.act in {"minimal", "thanks"}:
        options = list(MINIMAL_OPENINGS)
    elif plan.act == "closing":
        options = options[:3]
    return f"<variacion>\napertura sugerida: {options[seed % len(options)]}\n</variacion>"


def _converse_messages(
    state: ChatState,
    deps: GraphDeps,
    plan: TurnPlan,
    memory: care.ConversationMemory,
    seed: int = 0,
) -> list[BaseMessage]:
    blocks = [load_converse().render(), plan.render(), opening_hint(plan, seed)]
    memory_block = care.render_memory(memory)
    if memory_block:
        blocks.append(memory_block)
    if plan.bridge is not None:
        bridge = plan.bridge
        blocks.append(
            f'<puente id="U1" fuente="{bridge.title}" angulo="{bridge.angle}">\n'
            f"{bridge.text}\n</puente>"
        )
    messages: list[BaseMessage] = [SystemMessage(content="\n\n".join(blocks))]
    keep = max(1, deps.config.memory.keep_last_messages // 2)
    for turn in (state.get("turns") or [])[-keep:]:
        messages.append(HumanMessage(content=str(turn.get("question") or "")))
        messages.append(AIMessage(content=str(turn.get("answer") or "")))
    messages.append(HumanMessage(content=state["question"]))
    return messages


# ---------------------------------------------------------------- spec 021: entrega por frases

TERMINAL = re.compile(r"[.!?…»)\]]\s*$")


class Emitter:
    """Entrega frases al cliente (evento ``sentence``) y lleva el texto del turno.

    Cada frase conserva su separador; la primera del turno no lleva ninguno. Lo entregado nunca se
    retira: la respuesta final es ``"".join(pieces)``.
    """

    def __init__(self, writer: Any, pieces: Sequence[str] = ()) -> None:
        self.writer = writer
        self.pieces: list[str] = list(pieces)
        self.next_separator: str | None = None

    @property
    def text(self) -> str:
        return "".join(self.pieces)

    def emit(self, text: str, *, separator_after: str | None = None) -> None:
        if not text or not text.strip():
            return
        if not self.pieces:
            text = text.lstrip()
        elif not text[:1].isspace():
            text = (self.next_separator or " ") + text
        self.next_separator = separator_after
        self.pieces.append(text)
        self.writer({"sentence": text, "index": len(self.pieces) - 1})


def _writer() -> Any:
    """Escritor de eventos propios de LangGraph; fuera de un flujo es una función vacía."""
    try:
        return get_stream_writer()
    except Exception:
        return lambda _payload: None


def _emit_lead(out: Emitter, state: ChatState) -> None:
    """Frases previas calculadas en ``route`` (aviso de datos sensibles y límite por hostilidad)."""
    for item in state.get("lead") or []:
        notice = item == conduct("sensitive_notice")
        out.emit(item, separator_after="\n\n" if notice else None)


def _stream_chunks(
    runnable: Runnable,
    messages: Any,
    config: RunnableConfig,
    first_timeout: float,
    idle_timeout: float,
) -> Iterator[str]:
    """Texto del modelo a medida que llega, con tiempo máximo al inicio y entre fragmentos."""
    channel: queue.Queue[tuple[str, Any]] = queue.Queue()
    stop = threading.Event()
    context = copy_context()

    def worker() -> None:
        try:
            for chunk in runnable.stream(messages, config):
                if stop.is_set():
                    break
                channel.put(("chunk", message_text(chunk)))
            channel.put(("end", None))
        except Exception as exc:  # se reenvía al consumidor
            channel.put(("error", exc))

    threading.Thread(target=lambda: context.run(worker), daemon=True).start()
    waited_first = True
    try:
        while True:
            try:
                kind, value = channel.get(timeout=first_timeout if waited_first else idle_timeout)
            except queue.Empty as exc:
                raise TimeoutError("el modelo no respondió a tiempo") from exc
            if kind == "end":
                return
            if kind == "error":
                raise value
            if value:
                waited_first = False
                yield value
    finally:
        stop.set()


def _converse_node(deps: GraphDeps):
    from .demo import DemoChatModel, demo_converse

    def converse(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        """Redacción guiada con revisión y respaldo (C §4): nada llega sin revisar."""
        if deps.config.conversation.sentences:
            return _converse_by_sentences(deps, state, config, DemoChatModel, demo_converse)
        settings = deps.config.conversation
        plan = TurnPlan.from_state(state.get("plan"))
        assert plan is not None
        memory = care.copy_conversation(state.get("conversation"))
        playbook = load_care()
        evidence = _bridge_evidence(plan)
        bridge_text = f"{plan.bridge.text}\n{plan.bridge.title}" if plan.bridge else ""
        names = [memory["thread_name"]] if memory["thread_name"] else []
        stored = _registered_name(get_store(), state.get("user_id"))
        if stored:
            names.append(stored)
        recent = _recent_answers(state, settings.recent_window)
        demo = isinstance(deps.model, DemoChatModel)
        messages = (
            []
            if demo
            else _converse_messages(
                state, deps, plan, memory, seed=_thread_seed(config, plan.turn, 0)
            )
        )
        notices: list[str] = []
        text, verdict = "", None
        try:
            for attempt in range(settings.max_regenerations + 1):
                if demo:
                    text = demo_converse(
                        plan,
                        playbook=playbook,
                        seed=_thread_seed(config, plan.turn, attempt),
                        name=memory["thread_name"] or stored,
                    )
                else:
                    try:
                        model = _converse_model(deps, plan.length, plan.act)
                        text = _invoke_with_timeout(
                            model, messages, config, settings.converse_timeout_seconds
                        )
                    except Exception as exc:
                        if "penalty" not in str(exc).lower() or not _PENALTIES_SUPPORTED["value"]:
                            raise
                        _PENALTIES_SUPPORTED["value"] = False  # el proveedor no las acepta
                        model = _converse_model(deps, plan.length, plan.act)
                        text = _invoke_with_timeout(
                            model, messages, config, settings.converse_timeout_seconds
                        )
                text = text.strip()
                if plan.length == "short":
                    text = trim_sentences(text, 2)
                verdict = review(
                    text,
                    plan,
                    evidence=bridge_text,
                    labels=evidence.keys(),
                    recent_answers=recent,
                    names=names,
                    playbook=playbook,
                    threshold=settings.repetition_threshold,
                )
                if verdict.ok:
                    break
                if attempt < settings.max_regenerations:
                    notices.append("review_retry")
                    if not demo:
                        messages = [
                            *messages,
                            AIMessage(content=text),
                            HumanMessage(content=correction_note(verdict, plan)),
                        ]
        except Exception:
            verdict = None  # error o tiempo vencido: respaldo sin mostrar el error (FR-027)
        if verdict is not None and verdict.ok:
            citations = [evidence["U1"]] if evidence and "[U1]" in text else []
            reviewed = "retry" if notices else "show"
            bridged = plan.bridge.to_dict() if citations and plan.bridge else None
            return {
                "answer": text,
                "citations": citations,
                "fallback": False,
                "reviewed": reviewed,
                "bridged": bridged,
                "turn_notices": notices,
            }
        result = _scripted_reply(state, bridge=plan.bridge)
        bridged = None
        if plan.bridge is not None and any(
            c.get("unit_id") == plan.bridge.unit_id for c in result["citations"]
        ):
            bridged = plan.bridge.to_dict()
        return {
            **result,
            "reviewed": "fallback",
            "bridged": bridged,
            "turn_notices": [*notices, "review_fallback"],
        }

    return converse


def _converse_by_sentences(
    deps: GraphDeps,
    state: ChatState,
    config: RunnableConfig,
    demo_model: type,
    demo_converse: Any,
) -> dict[str, Any]:
    """Spec 021: la conversación se entrega frase por frase, cada una revisada (C §3).

    - Primera frase rechazada (nada mostrado): se regenera o se usa el respaldo.
    - Frase posterior rechazada: se corta y la respuesta cierra con lo aprobado.
    - Error o tiempo vencido después de mostrar algo: se conserva lo mostrado y se cierra.
    """
    settings = deps.config.conversation
    plan = TurnPlan.from_state(state.get("plan"))
    assert plan is not None
    memory = care.copy_conversation(state.get("conversation"))
    playbook = load_care()
    care_state = care.copy_care_state(state.get("care"))
    evidence = _bridge_evidence(plan)
    bridge_text = f"{plan.bridge.text}\n{plan.bridge.title}" if plan.bridge else ""
    names = [memory["thread_name"]] if memory["thread_name"] else []
    stored = _registered_name(get_store(), state.get("user_id"))
    if stored:
        names.append(stored)
    recent = _recent_answers(state, settings.recent_window)
    demo = isinstance(deps.model, demo_model)
    messages = (
        []
        if demo
        else _converse_messages(state, deps, plan, memory, seed=_thread_seed(config, plan.turn, 0))
    )
    out = Emitter(_writer())
    _emit_lead(out, state)
    lead_count = len(out.pieces)

    def check(sentence: str, is_first: bool) -> list[str]:
        return review_sentence(
            sentence,
            plan,
            is_first=is_first,
            evidence=bridge_text,
            labels=evidence.keys(),
            names=names,
            playbook=playbook,
            recent_answers=recent,
            threshold=settings.repetition_threshold,
        ).issues

    notices: list[str] = []
    discarded = 0
    error = False
    gate: SentenceGate | None = None
    for attempt in range(settings.max_regenerations + 1):
        gate = SentenceGate(
            "conversation",
            check,
            SentenceSplitter(settings.sentence_max_chars, settings.first_fragment_chars),
            max_sentences=2 if plan.length == "short" else None,
        )
        try:
            if demo:
                chunks: Any = [
                    demo_converse(
                        plan,
                        playbook=playbook,
                        seed=_thread_seed(config, plan.turn, attempt),
                        name=memory["thread_name"] or stored,
                    )
                ]
            else:
                chunks = _converse_stream(deps, plan, messages, config)
            for chunk in chunks:
                for decision in gate.push(chunk):
                    if decision.kind == "deliver":
                        out.emit(decision.text)
                if gate.stopped or gate.first_check_failed:
                    break
            else:
                for decision in gate.close():
                    if decision.kind == "deliver":
                        out.emit(decision.text)
        except Exception:
            error = True  # error o tiempo vencido: sin mensaje técnico (FR-009)
            # La última frase completa que esperaba texto siguiente también se revisa y entrega;
            # un fragmento cortado a mitad nunca se muestra.
            if gate.delivered and TERMINAL.search(gate.splitter.buffer.strip()):
                for decision in gate.close():
                    if decision.kind == "deliver":
                        out.emit(decision.text)
        discarded += len(gate.discarded)
        if gate.first_check_failed and not error and attempt < settings.max_regenerations:
            notices.append("review_retry")
            if not demo:
                verdict = ReviewVerdict(ok=False, issues=list(gate.discarded[-1:]))
                messages = [*messages, HumanMessage(content=correction_note(verdict, plan))]
            continue
        break
    assert gate is not None
    citations: list[dict[str, Any]] = []
    if not gate.delivered:
        # Nada del modelo llegó al visitante: respaldo de la spec 019, también por frases.
        result = _scripted_reply(state, bridge=plan.bridge)
        for sentence in split_all(
            str(result["answer"]), settings.sentence_max_chars, settings.first_fragment_chars
        ):
            out.emit(sentence)
        bridged = None
        if plan.bridge is not None and any(
            c.get("unit_id") == plan.bridge.unit_id for c in result["citations"]
        ):
            bridged = plan.bridge.to_dict()
        return {
            "answer": out.text.strip(),
            "citations": result["citations"],
            "fallback": False,
            "identity": result.get("identity"),
            "care": result.get("care", care_state),
            "reviewed": "fallback",
            "bridged": bridged,
            "delivered": out.pieces,
            "discarded": discarded,
            "turn_notices": [*(state.get("turn_notices") or []), *notices, "review_fallback"],
        }
    if gate.stopped and gate.discarded:
        notices.append("sentence_discarded")
    last = out.pieces[-1] if len(out.pieces) > lead_count else ""
    if error or (gate.stopped and gate.discarded and not TERMINAL.search(last)):
        out.emit(care.pick(playbook, "close.short", care_state))
    if evidence and "[U1]" in out.text:
        citations = [evidence["U1"]]
    return {
        "answer": out.text.strip(),
        "citations": citations,
        "fallback": False,
        "care": care_state,
        "reviewed": "retry" if "review_retry" in notices else "show",
        "bridged": plan.bridge.to_dict() if citations and plan.bridge else None,
        "delivered": out.pieces,
        "discarded": discarded,
        "turn_notices": [*(state.get("turn_notices") or []), *notices],
    }


def _converse_stream(
    deps: GraphDeps, plan: TurnPlan, messages: list[BaseMessage], config: RunnableConfig
) -> Iterator[str]:
    """Stream de ``converse``; si el proveedor rechaza las penalizaciones, sigue sin ellas."""
    settings = deps.config.conversation
    yielded = False
    try:
        for chunk in _stream_chunks(
            _converse_model(deps, plan.length, plan.act),
            messages,
            config,
            min(settings.stream_first_timeout_seconds, settings.converse_timeout_seconds),
            settings.stream_idle_timeout_seconds,
        ):
            yielded = True
            yield chunk
    except Exception as exc:
        if yielded or "penalty" not in str(exc).lower() or not _PENALTIES_SUPPORTED["value"]:
            raise
        _PENALTIES_SUPPORTED["value"] = False
        yield from _stream_chunks(
            _converse_model(deps, plan.length, plan.act),
            messages,
            config,
            min(settings.stream_first_timeout_seconds, settings.converse_timeout_seconds),
            settings.stream_idle_timeout_seconds,
        )


def system_with_preferences(system: str, deps: GraphDeps, state: ChatState) -> str:
    """System prompt más preferencias y perfil del usuario (memoria larga, Store)."""
    store = get_store()
    if store is None:
        return system
    user_id = state.get("user_id", "anon")
    items = UserMemory(store, deps.config.memory.preference_ttl_days).list(user_id)
    blocks = [render_preferences(items), render_profile(UserProfile(store).list(user_id))]
    extra = "\n\n".join(block for block in blocks if block)
    return f"{system}\n\n{extra}" if extra else system


def profile_from_turns(turns: Sequence[dict[str, Any]]) -> dict[str, str]:
    """Datos de perfil que el usuario dijo en este hilo (memoria de corto plazo)."""
    facts: dict[str, str] = {}
    for turn in turns:
        facts.update(extract_profile(str(turn.get("question", ""))))
    return facts


def profile_answer(stored: dict[str, str], in_thread: dict[str, str]) -> str:
    """Respuesta a «¿Dónde trabajo?» que dice de qué memoria sale cada dato."""
    if not stored and not in_thread:
        return PROFILE_UNKNOWN_ANSWER
    parts: list[str] = []
    if stored:
        listed = "; ".join(f"{PROFILE_LABELS[k]}: {stored[k]}" for k in PROFILE_KEYS if k in stored)
        parts.append(f"Según tu perfil guardado (memoria de largo plazo): {listed}.")
    extra = {k: v for k, v in in_thread.items() if stored.get(k) != v}
    if extra:
        listed = "; ".join(f"{PROFILE_LABELS[k]}: {extra[k]}" for k in PROFILE_KEYS if k in extra)
        parts.append(f"En esta conversación me dijiste (memoria de corto plazo): {listed}.")
    return " ".join(parts)


def _run_action(deps: GraphDeps, state: ChatState, tool: str, args: dict[str, Any]) -> str:
    return execute_action(
        tool,
        args,
        store=get_store(),
        user_id=state.get("user_id", "anon"),
        turns=state.get("turns") or [],
        ttl_days=deps.config.memory.preference_ttl_days,
    )


def _action_node(deps: GraphDeps):
    def action(state: ChatState) -> dict[str, Any]:
        """Cadena: ``interrupt()`` explícito antes de toda escritura (FR-017)."""
        intent = state.get("intent") or {}
        tool, args = intent["tool"], intent.get("args", {})
        response = interrupt(hitl_request(tool, args))
        decision = ((response or {}).get("decisions") or [{"type": "reject"}])[0]
        if decision.get("type") == "reject":
            answer = REJECTED_ANSWER
        else:
            if decision.get("type") == "edit":
                args = decision.get("edited_action", {}).get("args", args)
            answer = _run_action(deps, state, tool, args)
        return {"answer": answer, "citations": [], "fallback": False}

    return action


def reply_node(state: ChatState) -> dict[str, Any]:
    """Respuestas sin búsqueda de Valer-IA: perfil, saludo, despedida, conducta y aclaración.

    Con la atención activa (spec 019), los temas ajenos, los consejos, los pedidos no atendibles,
    las quejas sin consulta, la aclaración y las crisis se componen desde ``prompts/care.md``.
    """
    return _scripted_reply(state)


LIGHT_FALLBACK = {
    "smalltalk": "smalltalk.fallback",
    "minimal": "minimal.fallback",
    "about_assistant": "about.fallback",
}


def _scripted_reply(state: ChatState, bridge: Any = care.DEFAULT_BRIDGE) -> dict[str, Any]:
    """Composición determinista de la spec 019; en el modo guiado es el respaldo (R9).

    ``bridge`` es el puente elegido por ``bridges.py`` (o ``None`` si no se permite uno).
    """
    decision = state["decision"]
    act = str((state.get("plan") or {}).get("act") or "")
    route = decision["route"]
    store = get_store()
    stored = (
        {item.key: item.value for item in UserProfile(store).list(state.get("user_id", "anon"))}
        if store is not None
        else {}
    )
    identity = {**IDENTITY_STAGE_NONE, **(state.get("identity") or {})}
    question = normalize(state["question"])
    signals = state.get("care_signals")
    caring = bool(signals and signals.get("enabled"))
    care_state = care.copy_care_state(state.get("care"))
    playbook = load_care()
    reason = decision.get("scope_reason") or "off_topic"
    citations: list[dict[str, Any]] = []
    if state.get("profile_query"):
        answer = profile_answer(stored, profile_from_turns(state.get("turns") or []))
    elif caring and route == "direct" and signals.get("complaint_only"):
        answer, citations = care.compose_complaint(signals, playbook, care_state)
    elif caring and route == "direct" and signals.get("satisfied_only"):
        answer = care.pick(playbook, "satisfied", care_state)
    elif route == "direct" and LIGHT_FALLBACK.get(act) in playbook.variants:
        # Spec 020 (SC-001): la variante menos parecida a lo que ya se dijo en el hilo.
        recent = _recent_answers(state, 10)
        answer = min(
            playbook.variants[LIGHT_FALLBACK[act]],
            key=lambda text: max((similarity(text, before) for before in recent), default=0.0),
        )
    elif route == "direct":
        if FAREWELL.search(question):
            # Oferta de recordar: una vez por visita y solo a un visitante anónimo (FR-007).
            anonymous = not stored.get("name") and identity.get("stage") != "recognized"
            if anonymous and not identity.get("offered"):
                identity["offered"] = True
                answer = conduct("farewell_offer")
            else:
                answer = conduct("farewell")
        elif AI_QUESTION.search(question):
            answer = conduct("ai_disclosure")
        elif stored.get("name"):
            # Memoria de largo plazo: el saludo usa el nombre guardado en el Store.
            answer = conduct("greeting_named", name=stored["name"])
        else:
            answer = conduct("greeting")
    elif route == "out_of_scope" and caring and reason == "crisis":
        answer = care.crisis_reply(playbook, care_state)
    elif route == "out_of_scope" and caring and reason in CARE_REASONS:
        answer, citations = care.compose_out_of_scope(
            signals, decision, playbook, care_state, bridge=bridge
        )
    elif route == "out_of_scope" and caring and reason == "abuse":
        # Nivel 1: el texto de la spec 018; después, un límite más firme sin cortar la atención.
        level = int(signals.get("hostility_level") or 1)
        answer = (
            conduct("abuse")
            if level <= 1
            else care.pick(playbook, f"hostility.{level}", care_state)
        )
    elif route == "out_of_scope":
        answer = conduct(reason)
    elif caring:
        answer, citations = care.compose_clarify(signals, playbook, care_state)
    else:
        answer = conduct("clarify")
    return {
        "answer": answer,
        "citations": citations,
        "fallback": False,
        "identity": identity,
        "care": care_state,
        "care_signals": signals,
    }


CARE_REASONS = frozenset({"off_topic", "advice", "unattainable"})


# ---------------------------------------------------------------- identidad (spec 018)

TURN_RESET: dict[str, Any] = {
    "intent": None,
    "profile_query": False,
    "fragments": [],
    "structured_rows": [],
    "evidence": {},
    "context": "",
    "citations": [],
    "fallback": False,
    "retrievals": 0,
    "care_signals": None,
    "plan": None,
    "reviewed": "show",
    "bridged": None,
    "turn_notices": [],
    "lead": [],
    "delivered": [],
    "discarded": 0,
}


def _identity_decision(reason: str) -> dict[str, Any]:
    return RouteDecision(
        route="direct",
        confidence=1.0,
        reason=reason,
        decided_by="rules",
        scope_reason="identity",
    ).model_dump(mode="json")


def _registered_name(store: BaseStore | None, user_id: str | None) -> str | None:
    if store is None or not user_id:
        return None
    for item in UserProfile(store).list(user_id):
        if item.key == "name":
            return item.value
    return None


def identify_node(state: ChatState) -> dict[str, Any]:
    """Reconocimiento conversacional determinista (contracts/identity-flow.md).

    No llama al modelo de lenguaje y nunca ve el correo: solo su huella (``identity_event``).
    ``identity_next`` decide el camino: ``route`` (turno normal), ``reply`` (respuesta de
    identidad) o ``remember`` (acción ``remember_client`` con aprobación humana).
    """
    event = state.get("identity_event") or None
    identity = {**IDENTITY_STAGE_NONE, **(state.get("identity") or {})}
    stage = identity.get("stage", "none")
    user_id = state.get("user_id", "anon")
    store = get_store()
    registry = IdentityRegistry(store) if store is not None else None
    question = state["question"]

    def reply(text: str, reason: str, **extra: Any) -> dict[str, Any]:
        return {
            **TURN_RESET,
            "decision": _identity_decision(reason),
            "answer": text,
            "identity": identity,
            "identity_next": "reply",
            **extra,
        }

    def remember(name: str) -> dict[str, Any]:
        return {
            **TURN_RESET,
            "decision": _identity_decision("pide que lo recuerden (requiere aprobación)"),
            "answer": "",
            "identity": identity,
            "intent": {"tool": "remember_client", "args": {"name": name}},
            "identity_next": "remember",
        }

    if event and event.get("kind") == "reset":
        if event.get("explicit", True) or stage == "recognized":
            identity = dict(IDENTITY_STAGE_NONE)
            return reply(
                conduct("identity_reset"),
                "el visitante pide empezar de nuevo",
                client={"user_id": user_id, "reset": True},
            )
        return {"identity_next": "route", "identity": identity}

    if event and event.get("kind") == "email":
        masked = event.get("masked")
        if not event.get("valid", True):
            return reply(conduct("identity_invalid_email"), "correo con formato inválido")
        if identity.get("attempts", 0) >= MAX_THREAD_ATTEMPTS or registry is None:
            return reply(conduct("identity_neutral"), "reconocimiento no disponible en este hilo")
        fp = str(event.get("fingerprint"))
        owner = registry.lookup(fp)
        if owner == user_id:
            name = _registered_name(store, user_id)
            return reply(
                conduct("greeting_named", name=name) if name else conduct("identity_neutral"),
                "el visitante ya está identificado",
            )
        if owner and not registry.is_locked(fp):
            identity.update(stage="awaiting_name_confirm", fingerprint=fp)
            return reply(
                conduct("identity_confirm_name"),
                "correo registrado: se pide confirmar el nombre",
                client={"user_id": user_id, "masked_email": masked},
            )
        # Correo nuevo (o bloqueado, que se trata igual para no revelar nada).
        identity.update(stage="none", fingerprint=fp, masked=masked)
        name = extract_profile(question).get("name") or _registered_name(store, user_id)
        if name:
            return remember(name)
        identity["stage"] = "awaiting_name_new"
        return reply(
            conduct("identity_ask_name"),
            "correo nuevo: se pide el nombre para recordarlo",
            client={"user_id": user_id, "masked_email": masked},
        )

    if stage == "awaiting_name_confirm":
        fp = str(identity.get("fingerprint") or "")
        identity["stage"] = "none"
        if not looks_like_name(question):
            identity["attempts"] = identity.get("attempts", 0) + 1
            identity["fingerprint"] = None
            return {"identity_next": "route", "identity": identity}
        owner = registry.lookup(fp) if registry and fp else None
        registered = _registered_name(store, owner)
        if owner and registered and names_match(registered, extract_name(question)):
            identity.update(stage="recognized", fingerprint=None, recognized_name=registered)
            return reply(
                conduct("identity_recognized", name=registered),
                "cliente reconocido por correo y nombre",
                user_id=owner,
                client={"user_id": owner, "recognized": True, "name": registered},
            )
        if registry and fp:
            registry.record_failure(fp)
        identity["attempts"] = identity.get("attempts", 0) + 1
        identity["fingerprint"] = None
        return reply(conduct("identity_neutral"), "confirmación de identidad no válida")

    if stage == "awaiting_name_new":
        identity["stage"] = "none"
        if looks_like_name(question):
            return remember(extract_name(question))
        return {"identity_next": "route", "identity": identity}

    return {"identity_next": "route", "identity": identity}


def _after_identify(state: ChatState) -> str:
    return str(state.get("identity_next") or "route")


def remember_node(state: ChatState) -> dict[str, Any]:
    """Acción ``remember_client``: ``interrupt()`` y, si se aprueba, perfil + vínculo del correo."""
    intent = state.get("intent") or {}
    args = dict(intent.get("args") or {})
    identity = {**IDENTITY_STAGE_NONE, **(state.get("identity") or {})}
    response = interrupt(hitl_request("remember_client", args))
    decision = ((response or {}).get("decisions") or [{"type": "reject"}])[0]
    fp = identity.get("fingerprint")
    identity.update(fingerprint=None, masked=None)
    if decision.get("type") == "reject":
        return {"answer": conduct("identity_declined"), "identity": identity}
    if decision.get("type") == "edit":
        args = decision.get("edited_action", {}).get("args", args)
    name = str(args.get("name") or "").strip()[:80]
    store = get_store()
    user_id = state.get("user_id", "anon")
    if store is None or not fp or not name:
        return {"answer": conduct("identity_declined"), "identity": identity}
    UserProfile(store).save(user_id, {"name": name})
    IdentityRegistry(store).link(str(fp), user_id)
    identity.update(stage="recognized", recognized_name=name)
    return {
        "answer": conduct("identity_saved", name=name),
        "identity": identity,
        "client": {"user_id": user_id, "recognized": True, "name": name},
    }


def _finalize_node(deps: GraphDeps):
    def finalize(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        handler = find_metrics_handler(config)
        retrievals = state.get("retrievals", 0)
        metrics = handler.snapshot(retrievals) if handler else TurnMetrics(tool_calls=retrievals)
        turns = list(state.get("turns") or [])
        citations = state.get("citations") or []
        answer = state.get("answer", "")
        notices: list[str] = []
        decision = state["decision"]
        signals = state.get("care_signals")
        care_state = care.copy_care_state(state.get("care"))
        playbook = load_care()
        action = bool(state.get("intent"))
        retrieval = decision.get("route") not in NO_RETRIEVAL_ROUTES and not action
        fallback = bool(state.get("fallback", False))
        plan = TurnPlan.from_state(state.get("plan"))
        guided = plan is not None
        identity = {**IDENTITY_STAGE_NONE, **(state.get("identity") or {})}
        delivered = list(state.get("delivered") or [])
        settings = deps.config.conversation
        if delivered:
            # Spec 021 (R8): el nodo que generó ya entregó lead + frases revisadas; aquí solo se
            # entrega lo que va después (tail). Nada de lo mostrado se retira ni se reemplaza.
            answer, tail_notices = _deliver_tail(
                Emitter(_writer(), delivered),
                state,
                plan,
                signals,
                decision,
                playbook,
                care_state,
                identity,
                retrieval=retrieval,
            )
            notices.extend(tail_notices)
        else:
            answer, fallback, citations = _assemble_answer(
                deps,
                state,
                answer,
                citations,
                fallback,
                notices,
                plan,
                signals,
                decision,
                playbook,
                care_state,
                identity,
                retrieval=retrieval,
            )
            if settings.sentences and deps.config.care.enabled:
                # Respuestas fijas o sin generación: se entregan completas como frases (G4).
                out = Emitter(_writer())
                for sentence in split_all(
                    answer, settings.sentence_max_chars, settings.first_fragment_chars
                ):
                    out.emit(sentence)
        bridged = state.get("bridged") if guided else None
        conversation = state.get("conversation")
        act_entry = None
        if guided:
            memory = care.copy_conversation(conversation)
            conversation = care.update_conversation(
                memory,
                message=state["question"],
                signals=signals,
                decision=decision,
                act=plan.act,
                turn=len(turns) + 1,
                bridged=bridged,
                name=extract_profile(state["question"]).get("name"),
            )
            act_entry = {
                "act": plan.act,
                "bridged": bool(bridged),
                "reviewed": state.get("reviewed") or "show",
                "discarded": int(state.get("discarded") or 0),
            }
        elif deps.config.care.enabled and deps.config.conversation.guided:
            # Turnos sin plan (acciones con aprobación): solo el nombre dado en el hilo (FR-018).
            name = extract_profile(state["question"]).get("name")
            if name:
                memory = care.copy_conversation(conversation)
                memory["thread_name"] = name[:40]
                conversation = memory
        contact = care.update_contact(
            state.get("contact"),
            signals=signals,
            decision=decision,
            citations=citations,
            fallback=fallback,
            care_state=care_state,
            action=action,
            act=act_entry,
        )
        turn = Turn(
            turn_id=len(turns) + 1,
            question=state["question"],
            route=RouteDecision.model_validate(state["decision"]),
            fragments=state.get("fragments") or [],
            structured_rows=state.get("structured_rows") or [],
            answer=answer,
            citations=citations,
            sources=list(dict.fromkeys(c["url"] for c in citations if c.get("url"))),
            fallback=fallback,
            metrics=metrics,
        )
        turns.append(turn.model_dump(mode="json"))
        summary, summarized = compact_history(
            turns,
            state.get("summary", ""),
            state.get("summarized", 0),
            deps.config.memory,
            deps.summary_model,
        )
        return {
            "turns": turns,
            "summary": summary,
            "summarized": summarized,
            "notices": notices,
            "identity_event": None,
            "care": care_state,
            "care_signals": care.strip_texts(signals),
            "contact": contact,
            "conversation": conversation or care.empty_conversation(),
            "identity": identity,
        }

    return finalize


def _remember_offer(
    state: ChatState, plan: TurnPlan | None, identity: dict[str, Any]
) -> str | None:
    """Spec 018 (FR-007) en el modo guiado: la oferta de recordar va en el cierre, una vez por
    visita y solo a visitantes anónimos."""
    if plan is None or plan.act != "closing" or plan.reason is not None:
        return None
    anonymous = (
        not _registered_name(get_store(), state.get("user_id"))
        and identity.get("stage") != "recognized"
    )
    if anonymous and not identity.get("offered"):
        identity["offered"] = True
        return conduct("remember_offer")
    return None


def _assemble_answer(
    deps: GraphDeps,
    state: ChatState,
    answer: str,
    citations: list[dict[str, Any]],
    fallback: bool,
    notices: list[str],
    plan: TurnPlan | None,
    signals: care.CareSignals | None,
    decision: dict[str, Any],
    playbook: Any,
    care_state: care.CareState,
    identity: dict[str, Any],
    *,
    retrieval: bool,
) -> tuple[str, bool, list[dict[str, Any]]]:
    """Respuesta completa (specs 019 y 020): antepuestos, sufijos y avisos alrededor del texto."""
    guided = plan is not None
    if retrieval:
        # Spec 019 (FR-018): ningún teléfono ni correo fuera de los canales citados.
        invented = care.invented_contacts(answer, playbook, state.get("context") or "")
        if invented:
            answer = care.replace_contacts(answer, invented)
            notices.append("invented_contact")
        if guided and not fallback:
            # Spec 020 (R11): cifras, nombres, promesas u opiniones sin respaldo.
            answer, citations, fallback, reviewed = _review_retrieval(
                answer, citations, state, playbook
            )
            if reviewed:
                notices.append(reviewed)
    # Sin evidencia el modelo no redacta apertura: el guion la antepone (spec 019).
    before, before_notices = care.prefixes(
        signals, decision, playbook, care_state, guided=guided and not fallback
    )
    after, after_notices = care.suffixes(
        signals, decision, playbook, care_state, retrieval=retrieval, guided=guided
    )
    answer = " ".join(piece for piece in [*before, answer, *after] if piece).strip()
    notices.extend(before_notices + after_notices)
    notices.extend(state.get("turn_notices") or [])
    offer = _remember_offer(state, plan, identity)
    if offer:
        answer = f"{answer} {offer}".strip()
    if SENSITIVE_NOTICES & set(state.get("pii_notice") or []):
        # Spec 018 (FR-020): aviso determinista si el visitante compartió datos sensibles.
        notices.append("sensitive_data")
        answer = f"{conduct('sensitive_notice')}\n\n{answer}".strip()
    return answer, fallback, citations


def _deliver_tail(
    out: Emitter,
    state: ChatState,
    plan: TurnPlan | None,
    signals: care.CareSignals | None,
    decision: dict[str, Any],
    playbook: Any,
    care_state: care.CareState,
    identity: dict[str, Any],
    *,
    retrieval: bool,
) -> tuple[str, list[str]]:
    """Spec 021 (R8): frases que van después del texto del modelo (``tail``)."""
    after, notices = care.suffixes(
        signals, decision, playbook, care_state, retrieval=retrieval, guided=True
    )
    for text in after:
        out.emit(text)
    notices = [*notices, *(state.get("turn_notices") or [])]
    offer = _remember_offer(state, plan, identity)
    if offer:
        out.emit(offer)
    converse = (state.get("plan") or {}).get("node") == "converse"
    if plan is not None and converse and state.get("reviewed") != "fallback":
        # Frases que el plan exige y el modelo no dijo: se agregan al final (FR-008).
        for section in missing_required(out.text, plan):
            out.emit(care.pick(playbook, section, care_state))
    return out.text.strip(), notices


def _review_retrieval(
    answer: str,
    citations: list[dict[str, Any]],
    state: ChatState,
    playbook: Any,
) -> tuple[str, list[dict[str, Any]], bool, str | None]:
    """Revisión de las respuestas con búsqueda en el modo guiado (R11).

    Quita las frases con cifras, nombres, promesas u opiniones sin respaldo; si no queda ninguna
    afirmación citada, la respuesta pasa a fallo de evidencia.
    """
    verdict = review(
        answer,
        None,
        evidence=evidence_text(state.get("evidence"), state.get("context") or ""),
        playbook=playbook,
        checks=RETRIEVAL_CHECKS,
    )
    if verdict.ok:
        return answer, citations, False, None
    trimmed = drop_flagged_sentences(answer, verdict.spans)
    labels = set(LABEL_PATTERN.findall(trimmed))
    kept = [c for c in citations if c.get("label") in labels]
    if not trimmed or not kept:
        return FALLBACK_ANSWER, [], True, "review_fallback"
    return trimmed, kept, False, "review_trimmed"


# ---------------------------------------------------------------- cadena


def _retrieve_node(deps: GraphDeps):
    def retrieve(state: ChatState) -> dict[str, Any]:
        decision = RouteDecision.model_validate(state["decision"])
        query = contextual_query(state["question"], _previous_question(state))
        top_k = deps.config.agent.chain_top_k
        retrievals = 0
        facts: list[StructuredFact] = []
        fragments: list[RetrievedFragment] = []
        documents: list[GuardedDocument] = []
        if decision.route in {"structured", "mixed"}:
            asked = series_intent(state["question"])
            if asked is not None and deps.series is not None:
                # Cifra anual del CSV curado: la agregación ya viene calculada por la herramienta.
                facts.append(aggregate_series_impl(deps.series, asked, question=state["question"]))
            elif deps.store is not None:
                facts, _, _ = query_structured_impl(deps.store, query=query, limit=top_k)
                entity_type = count_intent(state["question"])
                counted = count_fact(deps.store, entity_type) if entity_type else None
                if counted is not None:
                    # El conteo exacto basta: el modelo lo cita, no lo calcula, y los hechos
                    # extraídos automáticamente (ruidosos) no lo acompañan.
                    facts = [counted]
            documents = [fact_document(f"F{i}", fact) for i, fact in enumerate(facts, start=1)]
            retrievals += 1
        if decision.route == "structured" and not facts:
            decision = apply_structured_fallback(decision, rows_found=0)
        if decision.route in {"documental", "mixed"}:
            if deps.retriever is None:
                raise ChatUnavailableError("El índice de recuperación no está disponible.")
            parts = care.manuelita_parts(state.get("care_signals"))
            if len(parts) >= 2:
                found, guarded, searches = _search_parts(deps, parts, top_k)
            else:
                found, guarded = search_documents_impl(
                    deps.retriever, query, top_k=top_k, neutralize=deps.neutralize
                )
                searches = 1
            fragments = found
            # Los hechos llevan F#; los fragmentos, U#: en la ruta mixta conviven ambos.
            documents = [*documents, *guarded]
            retrievals += searches
        fragment_rows, fact_rows, evidence = collect_evidence(fragments, facts)
        return {
            "decision": decision.model_dump(mode="json"),
            "fragments": fragment_rows,
            "structured_rows": fact_rows,
            "evidence": evidence,
            "context": render_documents(documents),
            "retrievals": retrievals,
        }

    return retrieve


def _search_parts(
    deps: GraphDeps, parts: Sequence[care.RequestPart], top_k: int
) -> tuple[list[RetrievedFragment], list[GuardedDocument], int]:
    """Una búsqueda por solicitud de Manuelita, sin duplicados y con etiquetas ``U#`` globales."""
    assert deps.retriever is not None
    per_part = max(2, top_k // len(parts))
    fragments: list[RetrievedFragment] = []
    documents: list[GuardedDocument] = []
    seen: set[str] = set()
    for part in parts:
        text = part["text"]
        query = text if COMPANY.search(normalize(text)) else f"Manuelita {text}"
        found, guarded = search_documents_impl(
            deps.retriever, query, top_k=per_part, neutralize=deps.neutralize
        )
        for fragment, document in zip(found, guarded, strict=True):
            if fragment.unit_id in seen:
                continue
            seen.add(fragment.unit_id)
            fragments.append(fragment)
            label = f"U{len(documents) + 1}"
            documents.append(GuardedDocument(label, document.source, document.text))
    return fragments, documents, len(parts)


def care_brief(state: ChatState) -> str:
    """Brief de atención del turno (spec 019, contracts/care-skills.md)."""
    turns = state.get("turns") or []
    previous: str | None = None
    if turns:
        last = turns[-1]
        route = (last.get("route") or {}).get("route")
        previous = "fallback" if last.get("fallback") else (str(route) if route else None)
    guided = bool(state.get("plan"))
    return care.brief(
        state.get("care_signals"),
        care.copy_care_state(state.get("care")),
        previous,
        guided=guided,
        memory=care.copy_conversation(state.get("conversation")) if guided else None,
    )


def facts_model(deps: GraphDeps, state: ChatState) -> BaseChatModel:
    """Modelo de las respuestas con evidencia: ``temperature_facts`` en el modo guiado (R7)."""
    if not state.get("plan") or not hasattr(deps.model, "temperature"):
        return deps.model
    temperature = deps.config.conversation.temperature_facts
    return deps.model.model_copy(update={"temperature": temperature})


def _chain_user_message(state: ChatState, deps: GraphDeps) -> str:
    parts: list[str] = []
    if state.get("summary"):
        parts.append(f"<resumen>\n{state['summary']}\n</resumen>")
    # Recorte por tokens también en la cadena (antes solo «resumen + últimos N turnos»).
    recent = recent_within_budget(
        _recent_turns(state, deps), deps.config.memory.summarize_after_tokens
    )
    if recent:
        parts.append(
            "<historial>\n" + "\n\n".join(render_turn(t) for t in recent) + "\n</historial>"
        )
    parts.append(f"<evidencia>\n{state.get('context', '')}\n</evidencia>")
    attention = care_brief(state)
    if attention:
        parts.append(f"<atencion>\n{attention}\n</atencion>")
    parts.append(f"<pregunta>{state['question']}</pregunta>")
    return "\n\n".join(parts)


# Plantilla de la cadena RAG (LCEL): el system prompt y el mensaje del turno entran como
# variables, así que las llaves del contenido recuperado nunca se interpretan como plantilla.
CHAIN_PROMPT = ChatPromptTemplate.from_messages([("system", "{system}"), ("human", "{user}")])


def build_answer_chain(deps: GraphDeps, model: BaseChatModel | None = None) -> Runnable:
    """``RunnablePassthrough.assign(user=…) | ChatPromptTemplate | modelo``.

    Recibe ``{"state": ChatState, "system": str}`` y arma el mensaje del turno (resumen, historial,
    evidencia delimitada y pregunta) antes de llamar al modelo.
    """
    return (
        RunnablePassthrough.assign(user=lambda data: _chain_user_message(data["state"], deps))
        | CHAIN_PROMPT
        | (model or deps.model)
    )


def _answer_node(deps: GraphDeps):
    system = load_agent_prompt("agent").render()
    chain = build_answer_chain(deps)

    def answer(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        evidence = state.get("evidence") or {}
        if deps.config.conversation.sentences and state.get("plan"):
            return _answer_by_sentences(deps, state, config, system)
        if not evidence:
            return {"answer": FALLBACK_ANSWER, "citations": [], "fallback": True}
        personalized = system_with_preferences(system, deps, state)
        text, citations, fallback = FALLBACK_ANSWER, [], True
        for attempt in range(2):
            instruction = personalized if attempt == 0 else f"{personalized}\n\n{STRICT_REMINDER}"
            runnable = (
                chain
                if not state.get("plan")
                else build_answer_chain(deps, facts_model(deps, state))
            )
            response = runnable.invoke({"state": state, "system": instruction}, config)
            raw = message_text(response)
            text, citations, fallback = validate_answer(raw, evidence, system)
            if not fallback or is_model_fallback(raw):
                break
        return {"answer": text, "citations": citations, "fallback": fallback}

    return answer


def _fallback_opener(state: ChatState, playbook: Any, care_state: care.CareState) -> str:
    """Apertura empática antes del mensaje de evidencia insuficiente (el modelo no la redactó)."""
    signals = state.get("care_signals") or {}
    sentiment = signals.get("sentiment")
    if sentiment in care.NEGATIVE and not signals.get("hostile"):
        return care.pick(playbook, f"opener.{sentiment}", care_state)
    if signals.get("concern"):
        return care.pick(playbook, "opener.concern", care_state)
    return ""


def retrieval_checker(
    state: ChatState, evidence: dict[str, dict[str, Any]], context: str, system: str
) -> Any:
    """Revisión por frase de las respuestas con búsqueda (spec 021, R3 y R6)."""
    plan = TurnPlan.from_state(state.get("plan"))
    playbook = load_care()
    text = evidence_text(evidence, context)

    def check(sentence: str, _is_first: bool) -> list[str]:
        if leaks_prompt(sentence, system) or is_model_fallback(sentence):
            return ["citation"]
        return review_sentence(
            sentence,
            plan,
            is_first=False,
            evidence=text,
            labels=evidence.keys(),
            playbook=playbook,
            checks=LOCAL_CHECKS,
        ).issues

    return check


def cited(text: str, evidence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    labels = list(dict.fromkeys(LABEL_PATTERN.findall(text)))
    return [evidence[label] for label in labels if label in evidence]


def _answer_by_sentences(
    deps: GraphDeps, state: ChatState, config: RunnableConfig, system: str
) -> dict[str, Any]:
    """Spec 021: respuesta con búsqueda entregada por frases citadas y revisadas (R6)."""
    settings = deps.config.conversation
    evidence = state.get("evidence") or {}
    playbook = load_care()
    care_state = care.copy_care_state(state.get("care"))
    out = Emitter(_writer())
    _emit_lead(out, state)
    discarded = 0
    gate: SentenceGate | None = None
    if evidence:
        personalized = system_with_preferences(system, deps, state)
        check = retrieval_checker(state, evidence, state.get("context") or "", system)
        runnable = build_answer_chain(deps, facts_model(deps, state))
        for attempt in range(2):
            instruction = personalized if attempt == 0 else f"{personalized}\n\n{STRICT_REMINDER}"
            gate = SentenceGate(
                "retrieval",
                check,
                SentenceSplitter(settings.sentence_max_chars, settings.first_fragment_chars),
            )
            raw = ""
            for chunk in runnable.stream({"state": state, "system": instruction}, config):
                piece = message_text(chunk)
                raw += piece
                for decision in gate.push(piece):
                    if decision.kind == "deliver":
                        out.emit(decision.text)
            for decision in gate.close():
                if decision.kind == "deliver":
                    out.emit(decision.text)
            discarded += len(gate.discarded)
            # Sin ninguna frase citada y sin nada mostrado: un reintento estricto, como antes.
            if gate.delivered or is_model_fallback(raw) or attempt == 1:
                break
    notices = ["sentence_discarded"] if discarded else []
    if gate is None or not gate.delivered:
        opener = _fallback_opener(state, playbook, care_state)
        if opener:
            out.emit(opener)
        out.emit(FALLBACK_ANSWER)
        return {
            "answer": out.text.strip(),
            "citations": [],
            "fallback": True,
            "care": care_state,
            "delivered": out.pieces,
            "discarded": discarded,
            "turn_notices": [*(state.get("turn_notices") or []), *notices],
        }
    return {
        "answer": out.text.strip(),
        "citations": cited(out.text, evidence),
        "fallback": False,
        "care": care_state,
        "delivered": out.pieces,
        "discarded": discarded,
        "turn_notices": [*(state.get("turn_notices") or []), *notices],
    }


def build_chain_graph(
    deps: GraphDeps, checkpointer: Checkpointer = None, store: BaseStore | None = None
) -> CompiledStateGraph:
    """Variante cadena: recuperación fija y una respuesta por turno."""
    graph = StateGraph(ChatState)
    graph.add_node("identify", identify_node)
    graph.add_node("remember", remember_node)
    graph.add_node("route", _route_node(deps))
    graph.add_node("reply", reply_node)
    graph.add_node("converse", _converse_node(deps))
    graph.add_node("retrieve", _retrieve_node(deps))
    graph.add_node("answer", _answer_node(deps))
    graph.add_node("action", _action_node(deps))
    graph.add_node("finalize", _finalize_node(deps))
    graph.add_edge(START, "identify")
    graph.add_conditional_edges(
        "identify", _after_identify, {"route": "route", "reply": "finalize", "remember": "remember"}
    )
    graph.add_edge("remember", "finalize")
    graph.add_conditional_edges(
        "route",
        _after_route,
        {"reply": "reply", "converse": "converse", "work": "retrieve", "action": "action"},
    )
    graph.add_edge("converse", "finalize")
    graph.add_edge("action", "finalize")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", "finalize")
    graph.add_edge("reply", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer, store=store)


# ---------------------------------------------------------------- agente


def _agent_messages(state: ChatState, deps: GraphDeps) -> list[BaseMessage]:
    history: list[BaseMessage] = []
    summary = state.get("summary", "")
    for turn in _recent_turns(state, deps):
        history.append(HumanMessage(content=turn["question"]))
        history.append(AIMessage(content=turn["answer"]))
    # Recorte por tokens: los turnos recientes nunca desbordan la ventana; lo anterior ya está
    # en el resumen (``compact_history``).
    messages: list[BaseMessage] = trim_messages(
        history,
        max_tokens=deps.config.memory.summarize_after_tokens,
        token_counter=count_tokens_approximately,
        strategy="last",
        start_on="human",
    )
    question = f"<pregunta>{state['question']}</pregunta>"
    if summary:
        question = f"<resumen>\n{summary}\n</resumen>\n\n{question}"
    messages.append(HumanMessage(content=question))
    return messages


def _last_tool_text(messages: Sequence[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            return message_text(message)
    return ""


def _final_answer(messages: Sequence[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return "" if message.tool_calls else message_text(message)
    return ""


ROUTE_HINTS = {
    "structured": (
        "usa aggregate_series para cifras anuales (ventas, producción, cálculos por año) o "
        "query_structured para datos puntuales y listas; no uses search_documents salvo que "
        "esas herramientas no traigan nada"
    ),
    "documental": "usa search_documents; las cifras anuales solo si la pregunta las pide",
    "mixed": (
        "usa las dos fuentes: aggregate_series o query_structured para la cifra y "
        "search_documents para el contexto; la respuesta debe citar al menos un F# y un U#"
    ),
}


def route_hint(state: ChatState) -> str:
    """Pista explícita para el agente: la ruta del enrutador restringe qué herramientas usar."""
    decision = state.get("decision") or {}
    hint = ROUTE_HINTS.get(str(decision.get("route", "")))
    return f"\n\nRuta decidida por el enrutador: {decision.get('route')}. {hint}." if hint else ""


def _agent_node(deps: GraphDeps):
    system = load_agent_prompt("agent").render()
    limits = deps.config.agent

    def agent(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        if deps.retriever is None:
            raise ChatUnavailableError("El índice de recuperación no está disponible.")
        trace = ToolTrace()
        executed: list[str] = []

        def run(tool: str, args: dict[str, Any]) -> str:
            executed.append(tool)
            return _run_action(deps, state, tool, args)

        tools = [
            *build_read_tools(
                deps.retriever,
                deps.store,
                trace,
                top_k=limits.chain_top_k,
                neutralize=deps.neutralize,
                series=deps.series,
                question=state["question"],
            ),
            *build_write_tools(run),
        ]

        hint = route_hint(state)
        attention = care_brief(state)
        if attention:
            hint = f"{hint}\n\n{attention}"

        @dynamic_prompt
        def personalized_prompt(_request: ModelRequest) -> str:
            """System prompt con preferencias, perfil del Store y la ruta decidida."""
            return system_with_preferences(system, deps, state) + hint

        runnable = create_agent(
            facts_model(deps, state),
            tools=tools,
            middleware=[
                personalized_prompt,
                *build_pii_middleware(),
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        tool: {
                            "allowed_decisions": REVIEW_DECISIONS,
                            "description": TOOL_DESCRIPTIONS[tool],
                        }
                        for tool in WRITE_TOOLS
                    }
                ),
                build_summarization_middleware(
                    deps.config.memory, deps.summary_model or deps.model
                ),
                ToolCallLimitMiddleware(run_limit=limits.tool_call_limit),
                ModelCallLimitMiddleware(run_limit=limits.model_call_limit),
            ],
        )
        sentences = deps.config.conversation.sentences and bool(state.get("plan"))
        handler: _AgentSentences | None = None
        run_config = config
        if sentences and not state.get("intent"):
            handler = _AgentSentences(deps, state, trace, system)
            run_config = merge_configs(config, {"callbacks": [handler]})
        result = runnable.invoke({"messages": _agent_messages(state, deps)}, run_config)
        fragment_rows, fact_rows, evidence = collect_evidence(trace.fragments, trace.facts)
        final = _final_answer(result["messages"])
        if handler is not None and not executed:
            tool_text = [message_text(m) for m in result["messages"] if isinstance(m, ToolMessage)]
            delivered = handler.finish(final, evidence)
            return {
                "fragments": fragment_rows,
                "structured_rows": fact_rows,
                "evidence": evidence,
                "context": "\n\n".join(tool_text),
                **delivered,
                "retrievals": trace.calls,
            }
        if state.get("intent") or executed:
            # Turno de escritura: responde con el resultado de la acción, sin exigir citas.
            text = final or _last_tool_text(result["messages"]) or REJECTED_ANSWER
            citations, fallback = [], False
        else:
            text, citations, fallback = validate_answer(final, evidence, system)
        tool_text = [message_text(m) for m in result["messages"] if isinstance(m, ToolMessage)]
        return {
            "fragments": fragment_rows,
            "structured_rows": fact_rows,
            "evidence": evidence,
            "context": "\n\n".join(tool_text),
            "answer": text,
            "citations": citations,
            "fallback": fallback,
            "retrievals": trace.calls,
        }

    return agent


class _AgentSentences(BaseCallbackHandler):
    """Spec 021 (R7): frases revisadas de la variante agente, por cada llamada al modelo.

    Si una llamada termina pidiendo herramientas, su texto se descarta sin mostrarse. La primera
    frase de cada llamada se retiene hasta la segunda o hasta que la llamada termine sin
    herramientas, para no mostrar texto de una llamada que después pide buscar.
    """

    raise_error = False

    def __init__(self, deps: GraphDeps, state: ChatState, trace: ToolTrace, system: str) -> None:
        self.deps = deps
        self.state = state
        self.trace = trace
        self.system = system
        settings = deps.config.conversation
        self.max_chars = settings.sentence_max_chars
        self.first_chars = settings.first_fragment_chars
        self.out = Emitter(_writer())
        _emit_lead(self.out, state)
        self.lead_count = len(self.out.pieces)
        self.gate: SentenceGate | None = None
        self.pending: list[str] = []
        self.released = False
        self.tool = False
        self.streamed = False
        self.discarded = 0
        self.retracted = False

    # -- evidencia disponible en el momento de revisar cada frase
    def _evidence(self) -> tuple[dict[str, dict[str, Any]], str]:
        _rows, _facts, evidence = collect_evidence(self.trace.fragments, self.trace.facts)
        texts: list[str] = []
        units = getattr(self.deps.retriever, "units_by_id", {}) or {}
        for fragment in self.trace.fragments:
            unit = units.get(fragment.unit_id)
            if unit is not None:
                texts.append(unit.text)
        for index, fact in enumerate(self.trace.facts, start=1):
            texts.append(fact_document(f"F{index}", fact).text)
        return evidence, "\n".join(texts)

    def _new_gate(self) -> SentenceGate:
        def check(sentence: str, is_first: bool) -> list[str]:
            evidence, context = self._evidence()
            return retrieval_checker(self.state, evidence, context, self.system)(sentence, is_first)

        return SentenceGate("retrieval", check, SentenceSplitter(self.max_chars, self.first_chars))

    def _reset(self) -> None:
        if self.gate is not None:
            self.discarded += len(self.gate.discarded)
        self.gate = self._new_gate()
        self.pending = []
        self.released = False
        self.tool = False

    def on_chat_model_start(self, *_args: Any, **_kwargs: Any) -> None:
        self._reset()

    def on_llm_start(self, *_args: Any, **_kwargs: Any) -> None:
        self._reset()

    def _queue(self, text: str) -> None:
        if self.released:
            self.out.emit(text)
            return
        self.pending.append(text)
        if len(self.pending) >= 2:
            self._release()

    def _release(self) -> None:
        self.released = True
        for text in self.pending:
            self.out.emit(text)
        self.pending = []

    def on_llm_new_token(self, token: str, *, chunk: Any = None, **_kwargs: Any) -> None:
        if self.gate is None or self.tool:
            return
        message = getattr(chunk, "message", None)
        if message is not None and getattr(message, "tool_call_chunks", None):
            self.tool = True
            self.pending = []
            return
        if not token:
            return
        self.streamed = True
        for decision in self.gate.push(token):
            if decision.kind == "deliver":
                self._queue(decision.text)

    def on_llm_end(self, response: LLMResult, **_kwargs: Any) -> None:
        if self.gate is None:
            return
        calls_tools = self.tool or any(
            getattr(getattr(generation, "message", None), "tool_calls", None)
            for generations in response.generations
            for generation in generations
        )
        if calls_tools:
            self.retracted = self.retracted or self.released
            self.pending = []
        else:
            for decision in self.gate.close():
                if decision.kind == "deliver":
                    self._queue(decision.text)
            self._release()
        self.discarded += len(self.gate.discarded)
        self.gate = None

    def finish(self, final: str, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Cierra el turno: sin streaming, revisa la respuesta final completa por frases."""
        if not self.streamed and final:
            self._reset()
            assert self.gate is not None
            for decision in [*self.gate.push(final), *self.gate.close()]:
                if decision.kind == "deliver":
                    self.out.emit(decision.text)
            self.discarded += len(self.gate.discarded)
            self.gate = None
        notices = ["sentence_discarded"] if self.discarded else []
        care_state = care.copy_care_state(self.state.get("care"))
        if len(self.out.pieces) == self.lead_count:
            opener = _fallback_opener(self.state, load_care(), care_state)
            if opener:
                self.out.emit(opener)
            self.out.emit(FALLBACK_ANSWER)
            return {
                "answer": self.out.text.strip(),
                "citations": [],
                "fallback": True,
                "care": care_state,
                "delivered": self.out.pieces,
                "discarded": self.discarded,
                "turn_notices": [*(self.state.get("turn_notices") or []), *notices],
            }
        return {
            "answer": self.out.text.strip(),
            "citations": cited(self.out.text, evidence),
            "fallback": False,
            "care": care_state,
            "delivered": self.out.pieces,
            "discarded": self.discarded,
            "turn_notices": [*(self.state.get("turn_notices") or []), *notices],
        }


def build_agent_graph(
    deps: GraphDeps, checkpointer: Checkpointer = None, store: BaseStore | None = None
) -> CompiledStateGraph:
    """Variante agente: la puerta de decisión y después ``create_agent`` con herramientas."""
    graph = StateGraph(ChatState)
    graph.add_node("identify", identify_node)
    graph.add_node("remember", remember_node)
    graph.add_node("route", _route_node(deps))
    graph.add_node("reply", reply_node)
    graph.add_node("converse", _converse_node(deps))
    graph.add_node("agent", _agent_node(deps))
    graph.add_node("finalize", _finalize_node(deps))
    graph.add_edge(START, "identify")
    graph.add_conditional_edges(
        "identify", _after_identify, {"route": "route", "reply": "finalize", "remember": "remember"}
    )
    graph.add_edge("remember", "finalize")
    graph.add_conditional_edges(
        "route",
        _after_route,
        {"reply": "reply", "converse": "converse", "work": "agent", "action": "agent"},
    )
    graph.add_edge("converse", "finalize")
    graph.add_edge("agent", "finalize")
    graph.add_edge("reply", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer, store=store)
