"""Registro de la voz (spec 016, research R8): ``MANUELITA_STATE_DIR/logs/voice.jsonl``.

Nunca guarda el texto ni el audio; si no se puede escribir, se ignora (la respuesta no falla).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Literal

from ..agent.config import resolve_state_dir

logger = logging.getLogger(__name__)

VoiceLogStatus = Literal["ok", "empty", "error", "unavailable"]


def log_voice(
    *,
    thread_id: str | None,
    segment: int | None,
    voice: str,
    chars: int,
    synth_ms: float = 0.0,
    audio_ms: float = 0.0,
    status: VoiceLogStatus = "ok",
    error: str | None = None,
) -> None:
    record = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "thread_id": thread_id,
        "segment": segment,
        "voice": voice,
        "chars": int(chars),
        "synth_ms": float(synth_ms),
        "audio_ms": float(audio_ms),
        "status": status,
        "error": error,
    }
    try:
        path = resolve_state_dir() / "logs" / "voice.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # el registro es best-effort
        logger.debug("No se pudo registrar la voz: %s", type(exc).__name__)
