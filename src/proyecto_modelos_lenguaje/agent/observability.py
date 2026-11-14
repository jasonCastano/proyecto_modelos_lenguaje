"""Observabilidad del agente: trazas de LangSmith y log estructurado por turno.

LangSmith **observa, no orquesta**: con ``LANGSMITH_TRACING=true`` y ``LANGSMITH_API_KEY`` en
``.env``, LangChain y LangGraph envían cada ejecución (enrutador, recuperación, herramientas,
modelo) al proyecto ``LANGSMITH_PROJECT``. Cada turno lleva ``run_name``, etiquetas y metadatos
(hilo, variante, modo) para filtrarlo; nunca se envían claves ni el ``user_id``.

Sin LangSmith queda el equivalente local: una línea JSON por turno en
``$MANUELITA_STATE_DIR/logs/turns.jsonl`` (ruta, quién decidió, herramientas, latencia, tokens y
si hubo fallo de evidencia), además del logger ``manuelita.agent``.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_PROJECT = "manuelita-modulo2"
LOG_NAME = "turns.jsonl"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})

logger = logging.getLogger("manuelita.agent")


def tracing_enabled() -> bool:
    """LangSmith activo: bandera encendida y clave presente."""
    flag = os.environ.get("LANGSMITH_TRACING", os.environ.get("LANGCHAIN_TRACING_V2", ""))
    key = os.environ.get("LANGSMITH_API_KEY", os.environ.get("LANGCHAIN_API_KEY", ""))
    return flag.strip().lower() in TRUE_VALUES and bool(key.strip())


def configure_tracing() -> dict[str, Any]:
    """Fija el proyecto por defecto si hay trazas y devuelve el estado (sin secretos)."""
    enabled = tracing_enabled()
    if enabled:
        os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_PROJECT)
    return {
        "langsmith": enabled,
        "project": os.environ.get("LANGSMITH_PROJECT", DEFAULT_PROJECT) if enabled else None,
    }


def run_config(
    thread_id: str, variant: str, mode: str, *, corpus: str | None = None
) -> dict[str, Any]:
    """Nombre, etiquetas y metadatos de la traza de un turno.

    ``corpus`` (spec 015) marca las trazas del corpus de prueba adversarial con la etiqueta
    ``corpus:adversarial`` para filtrarlas en LangSmith; por defecto es el modo.
    """
    corpus = corpus or mode
    tags = ["modulo2", f"variante:{variant}", f"modo:{mode}"]
    if corpus == "adversarial":
        tags.append("corpus:adversarial")
    return {
        "run_name": f"turno-{variant}",
        "tags": tags,
        "metadata": {"thread_id": thread_id, "variant": variant, "mode": mode, "corpus": corpus},
    }


def turn_record(
    outcome: dict[str, Any], *, variant: str, mode: str, corpus: str | None = None
) -> dict[str, Any]:
    """Resumen auditable de un turno, sin el texto de la pregunta ni datos del usuario."""
    turn = outcome.get("turn") or {}
    route = turn.get("route") or {}
    metrics = turn.get("metrics") or {}
    return {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "thread_id": outcome.get("thread_id"),
        "turn_id": turn.get("turn_id"),
        "variant": variant,
        "mode": mode,
        "corpus": corpus or mode,
        "status": outcome.get("status"),
        "route": route.get("route"),
        "decided_by": route.get("decided_by"),
        "confidence": route.get("confidence"),
        "fragments": len(turn.get("fragments") or []),
        "structured_rows": len(turn.get("structured_rows") or []),
        "citations": len(turn.get("citations") or []),
        "fallback": turn.get("fallback"),
        "anomalies": len(outcome.get("anomalies") or []),
        "pending_tool": (outcome.get("pending_action") or {}).get("tool"),
        "latency_ms": metrics.get("latency_ms"),
        "model_calls": metrics.get("model_calls"),
        "tool_calls": metrics.get("tool_calls"),
        "input_tokens": metrics.get("input_tokens"),
        "output_tokens": metrics.get("output_tokens"),
        "langsmith": tracing_enabled(),
    }


def log_turn(
    outcome: dict[str, Any],
    *,
    variant: str,
    mode: str,
    log_dir: Path | None,
    corpus: str | None = None,
) -> dict[str, Any]:
    """Escribe el turno en el logger y, si hay directorio de estado, en ``turns.jsonl``."""
    record = turn_record(outcome, variant=variant, mode=mode, corpus=corpus)
    line = json.dumps(record, ensure_ascii=False)
    logger.info(line)
    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / LOG_NAME).open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            logger.warning("No se pudo escribir %s", log_dir / LOG_NAME)
    return record
