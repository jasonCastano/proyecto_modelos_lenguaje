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

import re
import time
from collections.abc import Sequence
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
    ToolMessage,
)
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig, RunnablePassthrough
from langgraph.config import get_store
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer, interrupt

from ..rag.hybrid import HybridRetriever, RetrievedFragment
from ..tasks import FALLBACK_ANSWER, STRICT_REMINDER, is_model_fallback
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
from .privacy import build_pii_middleware
from .prompts import load_agent_prompt
from .router import apply_structured_fallback, contextual_query, route_message
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
GREETING_ANSWER = (
    "¡Hola! Soy el asistente de información pública del Grupo Manuelita. Pregúntame por su "
    "historia, productos, sostenibilidad, programas o filiales."
)
FAREWELL_ANSWER = "Con gusto. Si tienes otra pregunta sobre Manuelita, aquí estoy."
OUT_OF_SCOPE_ANSWER = (
    "Solo puedo responder sobre el Grupo Manuelita con su información pública; esa pregunta queda "
    "fuera de ese alcance."
)
CLARIFY_ANSWER = (
    "No estoy seguro de a qué te refieres. ¿Puedes precisar la pregunta, por ejemplo qué empresa, "
    "producto o tema de Manuelita te interesa?"
)
NO_RETRIEVAL_ROUTES = frozenset({"direct", "out_of_scope", "clarify"})
REVIEW_DECISIONS = ["approve", "edit", "reject"]
REJECTED_ANSWER = "Entendido: no realicé la acción porque fue rechazada en la revisión."
PROFILE_UNKNOWN_ANSWER = (
    "Todavía no sé eso de ti: no me lo has contado en esta conversación ni está guardado en tu "
    "perfil. Puedes decírmelo, por ejemplo «Me llamo Ana y trabajo en Carvajal»."
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
                state["question"],
                history=history,
                model=deps.router_model,
                min_confidence=deps.config.router.min_confidence,
                temperature=deps.config.router.llm_temperature,
            ).decision
        return {
            "intent": intent.to_dict() if intent else None,
            "profile_query": profile_query,
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


def _after_route(state: ChatState) -> str:
    if state.get("intent"):
        return "action"
    return "reply" if state["decision"]["route"] in NO_RETRIEVAL_ROUTES else "work"


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
    """Respuestas sin búsqueda: perfil, saludo o despedida, fuera de alcance y aclaración."""
    route = state["decision"]["route"]
    store = get_store()
    stored = (
        {item.key: item.value for item in UserProfile(store).list(state.get("user_id", "anon"))}
        if store is not None
        else {}
    )
    if state.get("profile_query"):
        answer = profile_answer(stored, profile_from_turns(state.get("turns") or []))
    elif route == "direct":
        farewell = FAREWELL.search(normalize(state["question"]))
        answer = FAREWELL_ANSWER if farewell else GREETING_ANSWER
        if not farewell and stored.get("name"):
            # Memoria de largo plazo: el saludo usa el nombre guardado en el Store.
            answer = answer.replace("¡Hola!", f"¡Hola, {stored['name']}!", 1)
    elif route == "out_of_scope":
        answer = OUT_OF_SCOPE_ANSWER
    else:
        answer = CLARIFY_ANSWER
    return {"answer": answer, "citations": [], "fallback": False}


def _finalize_node(deps: GraphDeps):
    def finalize(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        handler = find_metrics_handler(config)
        retrievals = state.get("retrievals", 0)
        metrics = handler.snapshot(retrievals) if handler else TurnMetrics(tool_calls=retrievals)
        turns = list(state.get("turns") or [])
        citations = state.get("citations") or []
        turn = Turn(
            turn_id=len(turns) + 1,
            question=state["question"],
            route=RouteDecision.model_validate(state["decision"]),
            fragments=state.get("fragments") or [],
            structured_rows=state.get("structured_rows") or [],
            answer=state.get("answer", ""),
            citations=citations,
            sources=list(dict.fromkeys(c["url"] for c in citations if c.get("url"))),
            fallback=state.get("fallback", False),
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
        return {"turns": turns, "summary": summary, "summarized": summarized}

    return finalize


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
            found, guarded = search_documents_impl(
                deps.retriever, query, top_k=top_k, neutralize=deps.neutralize
            )
            fragments = found
            # Los hechos llevan F#; los fragmentos, U#: en la ruta mixta conviven ambos.
            documents = [*documents, *guarded]
            retrievals += 1
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
    parts.append(f"<pregunta>{state['question']}</pregunta>")
    return "\n\n".join(parts)


# Plantilla de la cadena RAG (LCEL): el system prompt y el mensaje del turno entran como
# variables, así que las llaves del contenido recuperado nunca se interpretan como plantilla.
CHAIN_PROMPT = ChatPromptTemplate.from_messages([("system", "{system}"), ("human", "{user}")])


def build_answer_chain(deps: GraphDeps) -> Runnable:
    """``RunnablePassthrough.assign(user=…) | ChatPromptTemplate | modelo``.

    Recibe ``{"state": ChatState, "system": str}`` y arma el mensaje del turno (resumen, historial,
    evidencia delimitada y pregunta) antes de llamar al modelo.
    """
    return (
        RunnablePassthrough.assign(user=lambda data: _chain_user_message(data["state"], deps))
        | CHAIN_PROMPT
        | deps.model
    )


def _answer_node(deps: GraphDeps):
    system = load_agent_prompt("agent").render()
    chain = build_answer_chain(deps)

    def answer(state: ChatState, config: RunnableConfig) -> dict[str, Any]:
        evidence = state.get("evidence") or {}
        if not evidence:
            return {"answer": FALLBACK_ANSWER, "citations": [], "fallback": True}
        personalized = system_with_preferences(system, deps, state)
        text, citations, fallback = FALLBACK_ANSWER, [], True
        for attempt in range(2):
            instruction = personalized if attempt == 0 else f"{personalized}\n\n{STRICT_REMINDER}"
            response = chain.invoke({"state": state, "system": instruction}, config)
            raw = message_text(response)
            text, citations, fallback = validate_answer(raw, evidence, system)
            if not fallback or is_model_fallback(raw):
                break
        return {"answer": text, "citations": citations, "fallback": fallback}

    return answer


def build_chain_graph(
    deps: GraphDeps, checkpointer: Checkpointer = None, store: BaseStore | None = None
) -> CompiledStateGraph:
    """Variante cadena: recuperación fija y una respuesta por turno."""
    graph = StateGraph(ChatState)
    graph.add_node("route", _route_node(deps))
    graph.add_node("reply", reply_node)
    graph.add_node("retrieve", _retrieve_node(deps))
    graph.add_node("answer", _answer_node(deps))
    graph.add_node("action", _action_node(deps))
    graph.add_node("finalize", _finalize_node(deps))
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route", _after_route, {"reply": "reply", "work": "retrieve", "action": "action"}
    )
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

        @dynamic_prompt
        def personalized_prompt(_request: ModelRequest) -> str:
            """System prompt con preferencias, perfil del Store y la ruta decidida."""
            return system_with_preferences(system, deps, state) + hint

        runnable = create_agent(
            deps.model,
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
        result = runnable.invoke({"messages": _agent_messages(state, deps)}, config)
        fragment_rows, fact_rows, evidence = collect_evidence(trace.fragments, trace.facts)
        final = _final_answer(result["messages"])
        if state.get("intent") or executed:
            # Turno de escritura: responde con el resultado de la acción, sin exigir citas.
            text = final or _last_tool_text(result["messages"]) or REJECTED_ANSWER
            citations, fallback = [], False
        else:
            text, citations, fallback = validate_answer(final, evidence, system)
        return {
            "fragments": fragment_rows,
            "structured_rows": fact_rows,
            "evidence": evidence,
            "answer": text,
            "citations": citations,
            "fallback": fallback,
            "retrievals": trace.calls,
        }

    return agent


def build_agent_graph(
    deps: GraphDeps, checkpointer: Checkpointer = None, store: BaseStore | None = None
) -> CompiledStateGraph:
    """Variante agente: la puerta de decisión y después ``create_agent`` con herramientas."""
    graph = StateGraph(ChatState)
    graph.add_node("route", _route_node(deps))
    graph.add_node("reply", reply_node)
    graph.add_node("agent", _agent_node(deps))
    graph.add_node("finalize", _finalize_node(deps))
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route", _after_route, {"reply": "reply", "work": "agent", "action": "agent"}
    )
    graph.add_edge("agent", "finalize")
    graph.add_edge("reply", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer, store=store)
