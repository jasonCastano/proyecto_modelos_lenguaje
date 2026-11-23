"""Registro del dictado (spec 023, research R8): ``MANUELITA_STATE_DIR/logs/stt.jsonl``.

Solo tiempos, tamaños y estado: nunca el texto reconocido ni el audio. Si no se puede escribir,
se ignora (la transcripción no falla).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Literal

from ..agent.config import resolve_state_dir

logger = logging.getLogger(__name__)

SttLogStatus = Literal["ok", "empty", "error", "unavailable", "busy", "rejected"]


def log_stt(
    *,
    thread_id: str | None,
    audio_ms: int = 0,
    stt_ms: int = 0,
    size: int = 0,
    model: str = "",
    status: SttLogStatus = "ok",
    chars: int = 0,
    error: str | None = None,
) -> None:
    record = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "thread_id": (thread_id or None) and str(thread_id)[:64],
        "audio_ms": int(audio_ms),
        "stt_ms": int(stt_ms),
        "bytes": int(size),
        "model": model,
        "status": status,
        "chars": int(chars),
        "error": error,
    }
    try:
        path = resolve_state_dir() / "logs" / "stt.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # el registro es best-effort
        logger.debug("No se pudo registrar el dictado: %s", type(exc).__name__)
