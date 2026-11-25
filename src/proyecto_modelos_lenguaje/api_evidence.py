"""API v1 de evidencia técnica del Módulo 3 (spec 026; contracts/evidence-api.md).

Solo lectura y sin autorización: no expone datos de planta, claves, teléfonos ni datos personales.
Reutiliza lo que ya existe: el catálogo, los perfiles, el hilo del checkpointer y los estados de
salud. Las evaluaciones publicadas vienen de ``config/evaluations.toml`` (curado y versionado).
"""

from __future__ import annotations

import asyncio
import os
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from .agent.catalog import catalog, specs_for_route
from .agent.privacy import redact_pii
from .agent.profiles import load_profiles
from .api_errors import ApiV1Error
from .api_models import (
    PublishedEvaluationModel,
    ServicesEvidence,
    ServiceStatusModel,
    ToolCatalogEvidence,
    ToolEvidence,
    TurnTraceModel,
)
from .config import PROJECT_ROOT

router = APIRouter(prefix="/api/v1/evidence", tags=["evidencia v1"])

EVALUATIONS_FILE = PROJECT_ROOT / "config" / "evaluations.toml"
CHECK_TIMEOUT = 2.0
GATEWAY_WINDOW = timedelta(minutes=10)
SERVICE_LABELS = {
    "model": "Modelo DeepSeek",
    "qdrant": "Base vectorial Qdrant",
    "whatsapp": "Canal WhatsApp",
    "gateway": "Gateway OpenClaw",
    "voice": "Voz del agente",
    "stt": "Dictado",
}


# --------------------------------------------------------------------------- herramientas


def profiles_for(name: str) -> list[str]:
    """Perfiles que reciben la herramienta, con la misma regla de ``specs_for_route``: las lecturas
    según la lista blanca; las escrituras comunes en todos y guardar propuestas solo en el
    planificador."""
    return sorted(
        key
        for key in load_profiles()
        if name in {spec.name for spec in specs_for_route(None, profile=key)}
    )


@router.get("/tools", response_model=ToolCatalogEvidence)
def tools() -> ToolCatalogEvidence:
    rows = [
        ToolEvidence(
            name=spec.name,
            description=spec.description,
            kind=spec.kind,
            requires_approval=spec.requires_approval,
            routes=sorted(spec.routes),
            profiles=profiles_for(spec.name),
            mcp_allowed=spec.mcp,
        )
        for spec in catalog()
    ]
    return ToolCatalogEvidence(count=len(rows), tools=rows)


# --------------------------------------------------------------------------- trazas


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_pii(value)
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


@router.get("/traces/{thread_id}", response_model=TurnTraceModel)
def trace(thread_id: str, turn: int | None = None) -> TurnTraceModel:
    from .agent.service import ChatError
    from .api import _chat_service

    try:
        view = _chat_service().thread(thread_id)
    except ChatError as exc:
        if exc.code == "thread_not_found":
            raise ApiV1Error(
                "thread_not_found",
                "No existe esa conversación. Haz una pregunta en el agente y vuelve a abrir "
                "la traza.",
                status_code=404,
            ) from exc
        raise
    turns = view.get("turns") or []
    if not turns:
        raise ApiV1Error(
            "thread_not_found",
            "Esa conversación todavía no tiene turnos. Haz una pregunta en el agente.",
            status_code=404,
        )
    index = len(turns) if turn is None else turn
    if index < 1 or index > len(turns):
        raise ApiV1Error(
            "turn_not_found",
            f"Esa conversación tiene {len(turns)} turnos; elige uno entre 1 y {len(turns)}.",
            status_code=404,
        )
    data = turns[index - 1]
    route = data.get("route") or {}
    tools_used = [_redact(dict(tool)) for tool in data.get("tools") or []]
    for tool in tools_used:
        tool["summary"] = str(tool.get("summary") or "")[:200]
    return TurnTraceModel(
        thread_id=thread_id,
        turn=index,
        turns=len(turns),
        question=redact_pii(str(data.get("question") or "")),
        profile=str(data.get("profile") or "visitante"),
        route=str(route.get("route") or ""),
        decided_by=str(route.get("decided_by") or ""),
        plan_steps=[str(step) for step in data.get("plan_steps") or []],
        tools=tools_used,
        duration_ms=int((data.get("metrics") or {}).get("latency_ms") or 0),
    )


# --------------------------------------------------------------------------- servicios


def _status(status: str, reason: str, action: str = "") -> dict[str, str]:
    return {"status": status, "reason": reason, "action": action}


def check_model() -> dict[str, str]:
    from .llm import load_llm_config

    config = load_llm_config()
    if not config.api_key_present:
        return _status(
            "down",
            "Falta la clave del modelo; la plataforma funciona en modo demostración.",
            "Define DEEPSEEK_API_KEY en el .env del servidor.",
        )
    return _status("up", f"Clave configurada; modelo {config.model}.")


def check_qdrant() -> dict[str, str]:
    from .api import _retriever_ok

    url = os.environ.get("QDRANT_URL", "").strip()
    if _retriever_ok():
        where = "servidor" if url else "embebido"
        return _status("up", f"Índice vectorial disponible (modo {where}).")
    return _status(
        "down",
        "El índice vectorial no responde; la búsqueda usa el respaldo léxico.",
        "Ejecuta make qdrant-up o revisa QDRANT_URL.",
    )


def _channel_stats() -> dict[str, dict[str, Any]]:
    from .agent.config import load_agent_config, resolve_state_dir
    from .channels.journal import recent_stats

    config = load_agent_config()
    return recent_stats(resolve_state_dir(config.state_env_var) / "logs")


def check_whatsapp() -> dict[str, str]:
    stats = _channel_stats().get("whatsapp")
    if not stats:
        return _status(
            "unknown",
            "No hay mensajes de WhatsApp registrados en este servidor.",
            "Escribe al número del proyecto y vuelve a revisar.",
        )
    errors = int(stats.get("errors_1h") or 0)
    messages = int(stats.get("messages_1h") or 0)
    if errors and errors >= messages:
        return _status(
            "degraded",
            f"{errors} errores en {messages} mensajes de la última hora.",
            "Revisa logs/channels.jsonl en el directorio de estado.",
        )
    return _status(
        "up",
        f"{messages} mensajes en la última hora; p90 {stats.get('p90_latency_ms', 0)} ms.",
    )


def check_gateway() -> dict[str, str]:
    last = None
    for stats in _channel_stats().values():
        stamp = stats.get("last_message_at")
        if stamp and (last is None or stamp > last):
            last = stamp
    if last is None:
        return _status(
            "unknown",
            "El puente no ha entregado turnos en este servidor.",
            "Ejecuta openclaw gateway status en el PC servidor.",
        )
    age = datetime.now(UTC) - datetime.fromisoformat(last)
    if age <= GATEWAY_WINDOW:
        return _status("up", "El puente entregó turnos en los últimos 10 minutos.")
    return _status(
        "down",
        "Sin turnos del puente en 10 minutos.",
        "Ejecuta openclaw gateway status en el PC servidor.",
    )


def check_voice() -> dict[str, str]:
    from .api import _voice_available

    if _voice_available():
        return _status("up", "La voz en español está lista.")
    return _status(
        "down",
        "La voz no está disponible; el chat sigue por texto.",
        "Ejecuta uv run python -m proyecto_modelos_lenguaje.voice --check.",
    )


def check_stt() -> dict[str, str]:
    from .api import _stt_available

    if _stt_available():
        return _status("up", "El dictado está listo.")
    return _status(
        "down",
        "El dictado no está disponible; se puede escribir.",
        "Revisa el modelo de dictado local (spec 023).",
    )


CHECKS: dict[str, Callable[[], dict[str, str]]] = {
    "model": check_model,
    "qdrant": check_qdrant,
    "whatsapp": check_whatsapp,
    "gateway": check_gateway,
    "voice": check_voice,
    "stt": check_stt,
}


async def _run_check(service_id: str) -> ServiceStatusModel:
    check = CHECKS[service_id]
    try:
        result = await asyncio.wait_for(run_in_threadpool(check), timeout=CHECK_TIMEOUT)
    except TimeoutError:
        result = _status(
            "unknown",
            f"No respondió a tiempo ({CHECK_TIMEOUT:g} s).",
            "Vuelve a revisar en un momento.",
        )
    except Exception:
        result = _status("unknown", "No se pudo comprobar.", "Revisa los logs del servidor.")
    return ServiceStatusModel(
        id=service_id,  # type: ignore[arg-type]
        label=SERVICE_LABELS[service_id],
        status=result["status"],  # type: ignore[arg-type]
        reason=redact_pii(result["reason"]),
        action=result.get("action", ""),
    )


@router.get("/services", response_model=ServicesEvidence)
async def services() -> ServicesEvidence:
    rows = await asyncio.gather(*(_run_check(service_id) for service_id in CHECKS))
    return ServicesEvidence(checked_at=datetime.now(UTC).isoformat(), services=list(rows))


# --------------------------------------------------------------------------- evaluaciones


@router.get("/evaluations", response_model=list[PublishedEvaluationModel])
def evaluations() -> list[PublishedEvaluationModel]:
    try:
        payload = tomllib.loads(EVALUATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ApiV1Error(
            "evaluations_unavailable",
            "No se pudo leer config/evaluations.toml.",
            status_code=503,
        ) from exc
    return [PublishedEvaluationModel(**row) for row in payload.get("evaluation", [])]
