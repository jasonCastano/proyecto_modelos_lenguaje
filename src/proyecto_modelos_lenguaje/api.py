"""FastAPI boundary for the Manuelita RAG web experience."""

from __future__ import annotations

import hmac
import json
import logging
import os
import uuid
from functools import lru_cache
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from . import api_evidence, api_planning, webbuild
from .agent.adversarial import adversarial_enabled, adversarial_retriever
from .agent.catalog import to_json_schema
from .agent.config import AgentConfigError, load_agent_config, resolve_state_dir
from .agent.memory import build_checkpointer, build_store
from .agent.observability import configure_tracing
from .agent.service import ChatError, ChatService, build_deps
from .agent.welcome import load_welcome
from .api_errors import ApiV1Error
from .api_models import (
    ApiError,
    AskRequest,
    ChannelMessageRequest,
    ChannelReplyModel,
    ChannelStatus,
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
    SttResult,
    SttStatus,
    SummaryRequest,
    ThreadView,
    TtsRequest,
    VoiceStatus,
    WelcomeResponse,
)
from .api_models import (
    Citation as CitationModel,
)
from .channels.bridge import ChannelBridge, InboundMessage
from .channels.identity import channel_salt, normalize_sender
from .channels.journal import recent_stats, workspace_dir
from .channels.store import ChannelStore
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
from .stt.audio import (
    AudioTooLargeError,
    EmptyAudioError,
    UnsupportedAudioError,
    parse_wav16k,
)
from .stt.engine import SttBusyError, SttUnavailableError, get_stt_service
from .stt.log import log_stt
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
from .voice.audio import to_wav_bytes
from .voice.engine import UnknownVoiceError, VoiceUnavailableError, get_voice_service
from .voice.log import log_voice
from .voice.text import clean_for_speech

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
DEMO_INDEX = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "index"
WEB_DIST = PROJECT_ROOT / "web" / "dist"
APP_TITLE = "RAG Ingenio Manuelita"

load_dotenv(PROJECT_ROOT / ".env", override=False)
configure_tracing()

app = FastAPI(title=APP_TITLE, version="0.1.0")


@app.on_event("startup")
def _voice_warmup() -> None:
    """Precarga el modelo de voz en un hilo (spec 016, R5); nunca bloquea ni rompe el arranque."""
    try:
        service = get_voice_service()
        if service.config.warmup and service.config.engine != "fake":
            service.warmup_async()
    except Exception:  # la voz es opcional
        pass


@app.on_event("startup")
def _stt_warmup() -> None:
    """Precarga el modelo de dictado en un hilo (spec 023, R13); nunca bloquea el arranque."""
    try:
        service = get_stt_service()
        if service.config.warmup and service.config.engine != "fake":
            service.warmup_async()
    except Exception:  # el dictado es opcional
        pass


def _stt_available() -> bool:
    try:
        return get_stt_service().status().available
    except Exception:
        return False


def _voice_available() -> bool:
    try:
        return get_voice_service().status().available
    except Exception:
        return False


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Thread-Id"],
    expose_headers=["X-Voice", "X-Synth-Ms", "X-Audio-Ms"],
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
    elif _request.url.path.startswith("/api/v1/planning"):  # spec 026
        code = "invalid_scenario"
        message = api_planning.scenario_error_message(exc.errors())
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
            voice_available=_voice_available(),
            stt_available=_stt_available(),
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
            voice_available=_voice_available(),
            stt_available=_stt_available(),
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
        voice_available=_voice_available(),
        stt_available=_stt_available(),
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
    try:
        voice = get_voice_service().status()
        voice_info = {"available": voice.available, "state": voice.state, "voice": voice.voice}
    except Exception:
        voice_info = {"available": False, "state": "unavailable", "voice": None}
    try:
        from .agent.jev import gate_status_info

        gatekeeper = gate_status_info(load_agent_config().jev, demo=mode == "demo")
    except Exception:
        gatekeeper = {"state": "disabled"}
    return ObservabilityStatus(
        langsmith=bool(status.get("langsmith")),
        project=status.get("project"),
        structured_log=log_path,
        vector_store=vector_store,
        adversarial_corpus=adversarial_enabled(),
        voice=voice_info,
        gatekeeper=gatekeeper,
    )


@app.get("/api/welcome", response_model=WelcomeResponse)
def welcome():
    """Bienvenida de Valer-IA Caña (spec 018): plantilla con citas al oro, sin LLM."""
    try:
        return WelcomeResponse(**load_welcome())
    except Exception:
        return _api_error(
            "welcome_unavailable",
            "La bienvenida no está disponible.",
            retryable=True,
            action="continuar",
            status_code=503,
        )


@app.get("/api/voice", response_model=VoiceStatus)
def voice_status() -> VoiceStatus:
    """Estado del motor de voz (spec 016). Siempre 200; la indisponibilidad va en el cuerpo."""
    return VoiceStatus(**get_voice_service().status().to_dict())


def _voice_unavailable(detail: str | None) -> JSONResponse:
    return _api_error(
        "voice_unavailable",
        detail or "La voz no está disponible.",
        retryable=False,
        action="continuar sin voz",
        status_code=503,
    )


@app.post("/api/tts")
def tts(payload: TtsRequest):
    """Sintetiza una oración de la respuesta como WAV (spec 016, contracts/tts-api.md)."""
    service = get_voice_service()
    voice_name = payload.voice or service.config.voice
    log = {"thread_id": payload.thread_id, "segment": payload.segment, "voice": voice_name}
    if len(payload.text) > service.config.max_chars:
        return _api_error(
            "text_too_long",
            f"El texto supera {service.config.max_chars} caracteres.",
            retryable=False,
            action="revisar",
            status_code=422,
        )
    if service.state in {"disabled", "unavailable"}:
        log_voice(**log, chars=0, status="unavailable", error="voice_unavailable")
        return _voice_unavailable(service.status().detail)
    text = clean_for_speech(payload.text)
    try:
        if payload.voice:
            service.resolve_voice(payload.voice)
        if not text:
            log_voice(**log, chars=0, status="empty")
            return Response(status_code=204, headers={"Cache-Control": "no-store"})
        result = service.synthesize(text, payload.voice)
    except UnknownVoiceError as exc:
        return _api_error(
            "unknown_voice", str(exc), retryable=False, action="revisar", status_code=422
        )
    except VoiceUnavailableError as exc:
        log_voice(**log, chars=len(text), status="unavailable", error="voice_unavailable")
        return _voice_unavailable(str(exc))
    except Exception as exc:
        log_voice(**log, chars=len(text), status="error", error=type(exc).__name__)
        return _api_error(
            "voice_error",
            "No se pudo sintetizar la voz de esta oración.",
            retryable=True,
            action="reintentar",
            status_code=500,
        )
    log_voice(
        **{**log, "voice": result.voice},
        chars=len(text),
        synth_ms=result.synth_ms,
        audio_ms=result.audio_ms,
    )
    return Response(
        content=to_wav_bytes(result.samples, result.sample_rate),
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "X-Voice": result.voice,
            "X-Synth-Ms": str(result.synth_ms),
            "X-Audio-Ms": str(result.audio_ms),
        },
    )


WAV_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"}


@app.get("/api/stt", response_model=SttStatus)
def stt_status() -> SttStatus:
    """Estado del dictado (spec 023). Siempre 200; la indisponibilidad va en el cuerpo."""
    return SttStatus(**get_stt_service().status().to_dict())


async def _read_capped(request: Request, limit: int) -> bytes:
    """Lee el cuerpo en memoria sin pasar de ``limit + 1`` bytes (nunca a disco)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        return b"0" * (limit + 1)  # se rechaza sin leerlo
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            break
    return b"".join(chunks)


def _stt_error(code: str, message: str, status_code: int, *, retryable: bool) -> JSONResponse:
    return _api_error(
        code,
        message,
        retryable=retryable,
        action="reintentar" if retryable else "escribir",
        status_code=status_code,
    )


@app.post("/api/stt", response_model=SttResult)
async def stt(request: Request):
    """Convierte la voz del visitante en texto (spec 023, contracts/stt-api.md §2).

    El audio se procesa en memoria y se descarta; el registro guarda tiempos y tamaños, no texto.
    """
    service = get_stt_service()
    config = service.config
    thread_id = request.headers.get("x-thread-id")
    log = {"thread_id": thread_id, "model": config.model_label}
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    data = await _read_capped(request, config.max_bytes)
    if content_type and content_type not in WAV_TYPES:
        log_stt(**log, size=len(data), status="rejected", error="stt_unsupported_format")
        return _stt_error(
            "stt_unsupported_format",
            "El audio debe ser WAV PCM16 mono a 16 kHz.",
            415,
            retryable=False,
        )
    if service.state in {"disabled", "unavailable"}:
        log_stt(**log, size=len(data), status="unavailable", error="stt_unavailable")
        return _stt_error(
            "stt_unavailable",
            service.status().detail or "El dictado no está disponible.",
            503,
            retryable=True,
        )
    try:
        samples, audio_ms = parse_wav16k(
            data, max_bytes=config.max_bytes, max_seconds=config.max_seconds
        )
    except EmptyAudioError:
        log_stt(**log, size=len(data), status="rejected", error="stt_empty_audio")
        return _stt_error("stt_empty_audio", "No llegó audio.", 400, retryable=False)
    except AudioTooLargeError:
        log_stt(**log, size=len(data), status="rejected", error="stt_too_large")
        return _stt_error(
            "stt_too_large",
            f"El audio supera el máximo de {config.max_seconds:g} segundos.",
            413,
            retryable=False,
        )
    except UnsupportedAudioError:
        log_stt(**log, size=len(data), status="rejected", error="stt_unsupported_format")
        return _stt_error(
            "stt_unsupported_format",
            "El audio debe ser WAV PCM16 mono a 16 kHz.",
            415,
            retryable=False,
        )
    try:
        result = await run_in_threadpool(service.transcribe, samples, audio_ms)
    except SttUnavailableError as exc:
        log_stt(**log, audio_ms=audio_ms, size=len(data), status="unavailable")
        return _stt_error("stt_unavailable", str(exc), 503, retryable=True)
    except SttBusyError:
        log_stt(**log, audio_ms=audio_ms, size=len(data), status="busy", error="stt_busy")
        return _stt_error(
            "stt_busy", "El dictado está ocupado; intenta de nuevo.", 503, retryable=True
        )
    except Exception as exc:
        log_stt(**log, audio_ms=audio_ms, size=len(data), status="error", error=type(exc).__name__)
        return _stt_error("stt_error", "No se pudo convertir la voz en texto.", 500, retryable=True)
    finally:
        del samples  # el audio no sobrevive a la petición
    log_stt(
        **{**log, "model": result.model},
        audio_ms=result.audio_ms,
        stt_ms=result.stt_ms,
        size=len(data),
        status="empty" if result.empty else "ok",
        chars=len(result.text),
    )
    return SttResult(**result.to_dict())


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
            input_meta=payload.input.model_dump() if payload.input else None,
            profile=payload.profile,
        )
    except Exception as exc:
        return _chat_error(exc)
    return outcome.to_dict()


@app.get("/api/profiles")
def list_profiles(user_id: str = "anon") -> list[dict[str, Any]]:
    """Spec 025: perfiles de la plataforma y si el usuario puede usar cada uno (web)."""
    from .agent.profiles import describe

    return describe(user_id, "web")


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
            input_meta=payload.input.model_dump() if payload.input else None,
            profile=payload.profile,
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


# --- Spec 024: canal de mensajería (puente OpenClaw → Valer-IA) y catálogo -------------------

CHANNEL_TOKEN_ENV = "VALERIA_CHANNEL_TOKEN"
CHANNEL_MODE_ENV = "MANUELITA_CHANNEL_MODE"
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


@lru_cache(maxsize=1)
def _channel_bridge() -> ChannelBridge:
    """Puente del canal sobre el mismo ``ChatService`` que la web (un solo agente)."""
    config = load_agent_config()
    state_dir = resolve_state_dir(config.state_env_var)
    mode = os.environ.get(CHANNEL_MODE_ENV, "real").strip() or "real"
    return ChannelBridge(
        _chat_service(),
        ChannelStore(state_dir / "channels.sqlite3"),
        config.channels,
        salt=channel_salt(),
        mode="demo" if mode == "demo" else "real",
        log_dir=state_dir / "logs",
        workspace=workspace_dir(),
    )


def _channel_guard(request: Request) -> JSONResponse | None:
    """Solo loopback y con ``X-Channel-Token`` (comparación en tiempo constante)."""
    expected = os.environ.get(CHANNEL_TOKEN_ENV, "").strip()
    if not expected or not load_agent_config().channels.enabled:
        return _api_error(
            "channel_disabled",
            "El canal de mensajería no está configurado en este servidor.",
            retryable=False,
            action="configurar VALERIA_CHANNEL_TOKEN",
            status_code=503,
        )
    host = request.client.host if request.client else ""
    supplied = request.headers.get("X-Channel-Token", "")
    if host not in LOOPBACK_HOSTS or not hmac.compare_digest(supplied, expected):
        return _api_error(
            "channel_forbidden",
            "Acceso denegado al canal.",
            retryable=False,
            action="revisar",
            status_code=403,
        )
    return None


@app.post("/api/channels/messages", response_model=ChannelReplyModel)
async def channel_message(request: Request) -> dict[str, Any] | JSONResponse:
    """Un mensaje entrante de WhatsApp (o Telegram) ya admitido por el gateway OpenClaw."""
    denied = _channel_guard(request)
    if denied is not None:
        return denied
    try:
        payload = ChannelMessageRequest.model_validate(await request.json())
        sender = normalize_sender(payload.sender, payload.channel)
    except (ValueError, json.JSONDecodeError) as exc:
        detail = str(exc).splitlines()[0][:200] if str(exc) else "cuerpo inválido"
        return _api_error(
            "channel_invalid",
            f"El mensaje no cumple el contrato del canal: {detail}",
            retryable=False,
            action="revisar",
            status_code=400,
        )
    message = InboundMessage(
        payload.channel, payload.message_id, sender, payload.kind, payload.text
    )
    try:
        reply = await run_in_threadpool(_channel_bridge().handle, message)
    except Exception:
        return _api_error(
            "channel_error",
            "No se pudo atender el mensaje.",
            retryable=True,
            action="reintentar",
            status_code=500,
        )
    return reply.to_dict()


@app.get("/api/channels/status", response_model=ChannelStatus)
def channel_status(request: Request) -> dict[str, Any] | JSONResponse:
    """Salud del canal: mensajes y errores de la última hora, p90, modelo y Qdrant."""
    denied = _channel_guard(request)
    if denied is not None:
        return denied
    config = load_agent_config()
    state_dir = resolve_state_dir(config.state_env_var)
    try:
        pending = _channel_bridge().store.pending_count()
    except Exception:
        pending = 0
    try:
        llm = load_llm_config()
        model = {"provider": llm.provider, "model": llm.model, "ok": llm.api_key_present}
    except Exception:
        model = {"ok": False}
    qdrant_url = os.environ.get("QDRANT_URL", "").strip()
    return {
        "enabled": config.channels.enabled,
        "channels": recent_stats(state_dir / "logs"),
        "model": model,
        "qdrant": {"mode": "server" if qdrant_url else "embedded", "ok": _retriever_ok()},
        "pending_approvals": pending,
    }


def _retriever_ok() -> bool:
    try:
        return _retriever("real") is not None
    except Exception:
        return False


@app.get("/api/tools")
def tools_catalog() -> list[dict[str, Any]]:
    """Catálogo de herramientas del agente (ítem 1.1): nombre, tipo, rutas y JSON Schema."""
    return to_json_schema()


# --- Spec 026: API v1 de la plataforma web (planificación y evidencia) ----------------------

app.add_exception_handler(ApiV1Error, api_planning.error_handler)  # type: ignore[arg-type]
app.include_router(api_planning.router)
app.include_router(api_evidence.router)


WEB_BUILD_STATUS = webbuild.status(WEB_DIST.parent)
if WEB_BUILD_STATUS != "ok":
    # Tras un clon o un `git pull`, web/dist puede faltar o ser de una versión anterior.
    logging.getLogger("uvicorn.error").warning(
        "%s %s", webbuild.MESSAGES[WEB_BUILD_STATUS], webbuild.FIX
    )

APP_COMMIT = webbuild.source_commit()


@app.get("/api/version")
def version() -> dict[str, Any]:
    """Qué versión sirve este proceso: commit con el que arrancó y compilación web en disco.

    ``make app`` lo consulta para no confundir un servidor viejo con la versión actual.
    """
    return webbuild.version_info(WEB_DIST.parent, commit=APP_COMMIT)


@app.middleware("http")
async def cache_policy(request: Request, call_next: Any) -> Response:
    """``index.html`` sin caché (siempre la versión actual); recursos con hash, inmutables."""
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif not path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


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
            "message": f"{webbuild.MESSAGES['missing']} {webbuild.FIX}",
        }
