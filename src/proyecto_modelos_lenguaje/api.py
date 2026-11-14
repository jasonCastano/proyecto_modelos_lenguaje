"""FastAPI boundary for the Manuelita RAG web experience."""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent.adversarial import adversarial_enabled, adversarial_retriever
from .agent.config import AgentConfigError, load_agent_config, resolve_state_dir
from .agent.memory import build_checkpointer, build_store
from .agent.observability import configure_tracing
from .agent.service import ChatError, ChatService, build_deps
from .api_models import (
    ApiError,
    AskRequest,
    ChatRequest,
    ChatResponse,
    CitedAnswer,
    FaqItem,
    FaqRequest,
    FaqResponse,
    HealthStatus,
    MemoryView,
    ObservabilityStatus,
    PendingForget,
    ResumeRequest,
    RetrievalTraceModel,
    ShowcaseResponse,
    SummaryRequest,
    ThreadView,
)
from .api_models import (
    Citation as CitationModel,
)
from .config import PROJECT_ROOT
from .llm import (
    LLMAuthError,
    LLMConfigError,
    LLMModelMissingError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
    build_chat_model,
    estimate_cost,
    health_check,
    load_llm_config,
)
from .rag.config import load_retrieval_config
from .rag.embeddings import EmbeddingProfile, build_embedder
from .rag.errors import IndexInvalidError, IndexUnavailableError
from .rag.hybrid import HybridRetriever
from .rag.index import load_index
from .rag.vectorstore import attach_vector_store
from .retrieval import (
    RetrievalError,
    load_entity_index,
    load_faq_seeds,
    load_gold_units,
)
from .showcase import build_showcase
from .tasks import (
    Citation,
    FAQItem,
    TaskError,
    TaskResult,
    answer_question,
    build_scripted_model,
    generate_faq,
    summarize_corpus,
)

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
DEMO_INDEX = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "index"
WEB_DIST = PROJECT_ROOT / "web" / "dist"
APP_TITLE = "RAG Ingenio Manuelita"

load_dotenv(PROJECT_ROOT / ".env", override=False)
configure_tracing()

app = FastAPI(title=APP_TITLE, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def _units():
    return load_gold_units(GOLD_DIR)


@lru_cache(maxsize=1)
def _entity_index():
    return load_entity_index(GOLD_DIR)


@lru_cache(maxsize=1)
def _seeds():
    return load_faq_seeds(GOLD_DIR)


def _model(task: str, mode: str):
    if mode == "demo":
        return build_scripted_model(task)
    return build_chat_model(load_llm_config())


@lru_cache(maxsize=2)
def _retriever(mode: str) -> HybridRetriever | None:
    """Build (once per mode) the hybrid retriever; never fail the request."""
    try:
        config = load_retrieval_config()
        if adversarial_enabled():
            # Caso 5 de la rúbrica en vivo, en modo demo **y real** (spec 015): corpus de prueba
            # con documentos que intentan dar órdenes; la interfaz los muestra como dato.
            return adversarial_retriever("real" if mode == "real" else "demo", config)
        profile = EmbeddingProfile.from_config(config.embedding)
        notes: list[str] = []
        index_dir = DEMO_INDEX if mode == "demo" else config.index_dir
        try:
            index = load_index(index_dir, profile)
        except (IndexUnavailableError, IndexInvalidError) as exc:
            index = None
            notes.append(f"Índice no utilizable: {exc}")
        kind = "hash" if mode == "demo" else "fastembed"
        units = _units()
        vector_store, note = attach_vector_store(index, config.source, units, demo=mode == "demo")
        if note:
            notes.append(note)
        return HybridRetriever(
            units,
            index=index,
            embedder=build_embedder(profile, kind=kind),
            entity_index=_entity_index(),
            config=config,
            notes=tuple(notes),
            vector_store=vector_store,
        )
    except Exception:
        return None


def _citation(citation: Citation) -> CitationModel:
    return CitationModel(
        label=citation.label,
        title=citation.title,
        url=citation.url,
        section_path=list(citation.section_path),
        page=citation.page_start,
        time_start=citation.time_start,
        authority=citation.authority,
        snippet=None,
    )


def _cost(result: TaskResult, mode: str) -> float | None:
    if mode == "demo":
        return None
    config = load_llm_config()
    if config.cost_per_1k_input <= 0 and config.cost_per_1k_output <= 0:
        return None
    return estimate_cost(result.input_tokens, result.output_tokens, config)


def _to_answer(result: TaskResult, query_id: str, mode: str) -> CitedAnswer:
    if result.status in {"ok", "fallback"}:
        status = result.status
        error = None
    else:
        status = "error"
        error = ApiError(
            code=result.error or "invalid_response",
            message=result.answer,
            retryable=True,
            action="reintentar",
        )
    return CitedAnswer(
        query_id=query_id,
        status=status,  # type: ignore[arg-type]
        answer=result.answer,
        citations=[_citation(citation) for citation in result.citations],
        model=result.model,
        provider="demo" if mode == "demo" else "deepseek",
        prompt_version=result.prompt_version,
        latency_ms=round(result.latency_seconds * 1000, 2),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=_cost(result, mode),
        review_required=result.review_required,
        error=error,
        retrieval=(
            None if result.retrieval is None else RetrievalTraceModel(**result.retrieval.to_dict())
        ),
    )


def _api_error(
    code: str,
    message: str,
    *,
    retryable: bool,
    action: str,
    status_code: int,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "action": action,
            }
        },
    )


def _exception_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, TaskError):
        if exc.code in {"empty_question", "question_too_long"}:
            status_code = 422
            action = "revisar"
        elif exc.code == "model_timeout":
            status_code = 504
            action = "reintentar"
        else:
            status_code = 502
            action = "reintentar"
        return _api_error(
            exc.code,
            exc.message,
            retryable=exc.code not in {"empty_question", "question_too_long"},
            action=action,
            status_code=status_code,
        )
    if isinstance(exc, LLMConfigError):
        return _api_error(
            exc.code,
            "Falta la clave del proveedor. Define DEEPSEEK_API_KEY o usa el modo demostración.",
            retryable=False,
            action="configurar clave",
            status_code=503,
        )
    if isinstance(exc, LLMAuthError):
        return _api_error(
            exc.code,
            "La clave del proveedor no es válida o fue revocada.",
            retryable=False,
            action="configurar clave",
            status_code=502,
        )
    if isinstance(exc, LLMRateLimitError):
        return _api_error(
            exc.code,
            "El proveedor limitó temporalmente la solicitud. Espera y reintenta.",
            retryable=True,
            action="reintentar",
            status_code=429,
        )
    if isinstance(exc, LLMTimeoutError):
        return _api_error(
            exc.code,
            "El proveedor tardó demasiado. Reintenta o usa el modo demostración.",
            retryable=True,
            action="reintentar",
            status_code=504,
        )
    if isinstance(exc, LLMModelMissingError):
        return _api_error(
            exc.code,
            "El modelo configurado no está disponible en la cuenta.",
            retryable=False,
            action="revisar configuración",
            status_code=503,
        )
    if isinstance(exc, (LLMUnavailableError, LLMResponseError, RetrievalError)):
        return _api_error(
            getattr(exc, "code", "provider_unavailable"),
            "El servicio de conocimiento no está disponible en este momento.",
            retryable=True,
            action="reintentar",
            status_code=502,
        )
    return _api_error(
        "unexpected_error",
        "Ocurrió un error controlado. Revisa el estado y vuelve a intentar.",
        retryable=True,
        action="reintentar",
        status_code=500,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first.get("loc", []))
    if "question" in location:
        message_text = str(first.get("msg", "")).lower()
        code = (
            "empty_question"
            if any(token in message_text for token in ("blank", "empty", "vacía"))
            else "question_too_long"
        )
        message = (
            "La pregunta no puede estar vacía."
            if code == "empty_question"
            else "La pregunta supera 500 caracteres."
        )
    else:
        code = "invalid_request"
        message = "La solicitud no cumple el contrato de la API."
    return _api_error(
        code,
        message,
        retryable=False,
        action="revisar",
        status_code=422,
    )


@app.get("/api/health", response_model=HealthStatus)
def health(probe: bool = False) -> HealthStatus | JSONResponse:
    config = load_llm_config()
    if not config.api_key_present:
        return HealthStatus(
            ok=False,
            provider=config.provider,
            model=config.model,
            configured=False,
            demo_available=True,
            detail="Falta DEEPSEEK_API_KEY. El modo demostración está disponible.",
            adversarial_corpus=adversarial_enabled(),
        )
    if not probe:
        return HealthStatus(
            ok=True,
            provider=config.provider,
            model=config.model,
            configured=True,
            demo_available=True,
            detail="Proveedor configurado.",
            adversarial_corpus=adversarial_enabled(),
        )
    try:
        result = health_check(config)
    except Exception as exc:
        return _exception_response(exc)
    return HealthStatus(
        ok=True,
        provider=config.provider,
        model=config.model,
        configured=True,
        demo_available=True,
        adversarial_corpus=adversarial_enabled(),
        latency_ms=result.get("latency_ms"),
        detail=result.get("detail"),
    )


@app.get("/api/showcase", response_model=ShowcaseResponse)
def showcase() -> ShowcaseResponse | JSONResponse:
    """Recorrido de los Módulos 1 y 2 con métricas reales del repositorio."""
    try:
        return build_showcase()
    except Exception as exc:
        return _exception_response(exc)


@app.post("/api/ask", response_model=CitedAnswer)
def ask(payload: AskRequest) -> CitedAnswer | JSONResponse:
    """Q&A del Módulo 1 con citas ``[U#]`` y recuperación híbrida."""
    try:
        result = answer_question(
            payload.question,
            model=_model("qa", payload.mode),
            units=_units(),
            entity_index=_entity_index(),
            gold_dir=GOLD_DIR,
            project_root=PROJECT_ROOT,
            retrieval=_retriever(payload.mode),
        )
    except Exception as exc:
        return _exception_response(exc)
    return _to_answer(result, str(uuid.uuid4()), payload.mode)


@app.post("/api/summary", response_model=CitedAnswer)
def summary(payload: SummaryRequest) -> CitedAnswer | JSONResponse:
    """Resumen del corpus con citas."""
    try:
        result = summarize_corpus(
            pack=payload.pack,
            model=_model("summary", payload.mode),
            units=_units(),
            gold_dir=GOLD_DIR,
            project_root=PROJECT_ROOT,
        )
    except Exception as exc:
        return _exception_response(exc)
    return _to_answer(result, str(uuid.uuid4()), payload.mode)


@app.post("/api/faq", response_model=FaqResponse)
def faq(payload: FaqRequest) -> FaqResponse | JSONResponse:
    """Preguntas frecuentes con evidencia."""
    try:
        items = generate_faq(
            limit=payload.limit,
            model=_model("faq", payload.mode),
            units=_units(),
            seeds=_seeds(),
            gold_dir=GOLD_DIR,
            project_root=PROJECT_ROOT,
        )
    except Exception as exc:
        return _exception_response(exc)
    return FaqResponse(items=[_faq_item(item) for item in items])


def _faq_item(item: FAQItem) -> FaqItem:
    return FaqItem(
        question=item.question,
        answer=item.answer,
        citations=[_citation(citation) for citation in item.citations],
        status=item.status,  # type: ignore[arg-type]
        model=item.model,
        prompt_version=item.prompt_version,
    )


@lru_cache(maxsize=1)
def _chat_service() -> ChatService:
    """Servicio de conversación: checkpointer en ``MANUELITA_STATE_DIR`` y grafos perezosos."""
    config = load_agent_config()
    state_dir = resolve_state_dir(config.state_env_var)
    return ChatService(
        config,
        build_checkpointer(state_dir),
        lambda mode: build_deps(mode, config, _retriever(mode)),
        store=build_store(state_dir),
        log_dir=state_dir / "logs",
    )


@app.get("/api/observability", response_model=ObservabilityStatus)
def observability(mode: Literal["demo", "real"] | None = None) -> ObservabilityStatus:
    """Estado de las trazas (LangSmith), del log estructurado y de la búsqueda vectorial."""
    status = configure_tracing()
    vector_store: dict[str, str] = {}
    if mode is not None:
        retriever = _retriever(mode)
        vector_store[mode] = (
            retriever.vector_search_status()
            if retriever is not None
            else "Recuperación no disponible."
        )
    try:
        state_dir = resolve_state_dir(load_agent_config().state_env_var)
        log_path: str | None = str(state_dir / "logs" / "turns.jsonl")
    except Exception:
        log_path = None
    return ObservabilityStatus(
        langsmith=bool(status.get("langsmith")),
        project=status.get("project"),
        structured_log=log_path,
        vector_store=vector_store,
        adversarial_corpus=adversarial_enabled(),
    )


def _chat_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, ChatError):
        return _api_error(
            exc.code,
            exc.message,
            retryable=exc.status_code >= 500,
            action="reconstruir" if exc.code == "index_unavailable" else "revisar",
            status_code=exc.status_code,
        )
    if isinstance(exc, AgentConfigError):
        return _api_error(
            "invalid_config",
            str(exc),
            retryable=False,
            action="revisar configuración",
            status_code=503,
        )
    return _exception_response(exc)


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> dict[str, Any] | JSONResponse:
    """Un turno de la conversación (cadena o agente) con memoria por ``thread_id``."""
    try:
        outcome = _chat_service().send(
            payload.message,
            thread_id=payload.thread_id,
            user_id=payload.user_id,
            variant=payload.variant,
            mode=payload.mode,
        )
    except Exception as exc:
        return _chat_error(exc)
    return outcome.to_dict()


def _sse(event: dict[str, object]) -> str:
    """Un evento Server-Sent Events: ``event: <tipo>`` y ``data: <json>``."""
    kind = str(event.get("event", "message"))
    return f"event: {kind}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.post("/api/chat/stream", response_model=None)
def chat_stream(payload: ChatRequest) -> StreamingResponse | JSONResponse:
    """Misma conversación que ``/api/chat`` pero en streaming (SSE): ruta, recuperación,
    tokens de la respuesta y, al final, el turno validado con sus citas."""
    try:
        _thread_id, events = _chat_service().open_stream(
            payload.message,
            thread_id=payload.thread_id,
            user_id=payload.user_id,
            variant=payload.variant,
            mode=payload.mode,
        )
    except Exception as exc:
        return _chat_error(exc)
    return StreamingResponse(
        (_sse(event) for event in events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/threads/{thread_id}/resume", response_model=ChatResponse)
def resume(thread_id: str, payload: ResumeRequest) -> dict[str, Any] | JSONResponse:
    """Aprueba, edita o rechaza la acción de escritura pendiente (Human-in-the-Loop)."""
    try:
        outcome = _chat_service().resume(
            thread_id, action_id=payload.action_id, decision=payload.decision, args=payload.args
        )
    except Exception as exc:
        return _chat_error(exc)
    return outcome.to_dict()


@app.get("/api/memory/{user_id}", response_model=MemoryView)
def memory(user_id: str) -> dict[str, Any] | JSONResponse:
    """Perfil y preferencias guardados del usuario (memoria de largo plazo)."""
    try:
        return _chat_service().preferences(user_id)
    except Exception as exc:
        return _chat_error(exc)


@app.delete("/api/memory/{user_id}", status_code=202, response_model=PendingForget)
def forget_memory(user_id: str, thread_id: str) -> JSONResponse:
    """Pide olvidar la memoria del usuario; la acción espera aprobación humana."""
    try:
        outcome = _chat_service().request_forget(user_id, thread_id)
    except Exception as exc:
        return _chat_error(exc)
    return JSONResponse(
        status_code=202,
        content={
            "status": outcome.status,
            "thread_id": outcome.thread_id,
            "pending_action": outcome.pending_action,
        },
    )


@app.get("/api/threads/{thread_id}", response_model=ThreadView)
def thread(thread_id: str) -> dict[str, Any] | JSONResponse:
    """Turnos y acción pendiente de un hilo guardado en el checkpointer."""
    try:
        return _chat_service().thread(thread_id)
    except Exception as exc:
        return _chat_error(exc)


if WEB_DIST.is_dir():
    assets = WEB_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        root = WEB_DIST.resolve()
        candidate = (WEB_DIST / path).resolve()
        if candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(root / "index.html")
else:

    @app.get("/")
    def not_built():
        return {
            "app": APP_TITLE,
            "message": "El frontend no está compilado. Ejecuta `cd web && npm run build`.",
        }
