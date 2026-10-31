"""FastAPI boundary for the Manuelita RAG web experience."""

from __future__ import annotations

import uuid
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api_models import (
    ApiError,
    AskRequest,
    CitedAnswer,
    FaqItem,
    FaqRequest,
    FaqResponse,
    HealthStatus,
    SummaryRequest,
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
WEB_DIST = PROJECT_ROOT / "web" / "dist"
APP_TITLE = "RAG Ingenio Manuelita"

app = FastAPI(title=APP_TITLE, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
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
        )
    if not probe:
        return HealthStatus(
            ok=True,
            provider=config.provider,
            model=config.model,
            configured=True,
            demo_available=True,
            detail="Proveedor configurado.",
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
        latency_ms=result.get("latency_ms"),
        detail=result.get("detail"),
    )


@app.get("/api/showcase")
def showcase():
    try:
        return build_showcase()
    except Exception as exc:
        return _exception_response(exc)


@app.post("/api/ask")
def ask(payload: AskRequest):
    try:
        result = answer_question(
            payload.question,
            model=_model("qa", payload.mode),
            units=_units(),
            entity_index=_entity_index(),
            gold_dir=GOLD_DIR,
            project_root=PROJECT_ROOT,
        )
    except Exception as exc:
        return _exception_response(exc)
    return _to_answer(result, str(uuid.uuid4()), payload.mode)


@app.post("/api/summary")
def summary(payload: SummaryRequest):
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
def faq(payload: FaqRequest):
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


if WEB_DIST.is_dir():
    assets = WEB_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
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
