"""Registros del canal (spec 024, data-model §8–9).

- ``logs/channels.jsonl``: una línea por mensaje con seudónimo, ruta, herramientas, latencia y
  estado. **Nunca** texto ni número de teléfono (el id del mensaje se guarda como hash).
- Bitácora diaria del workspace de OpenClaw ``memory/YYYY-MM-DD.md`` (ítem 3.3): mismo contenido
  en Markdown legible; solo se escribe si ``OPENCLAW_WORKSPACE_DIR`` está definido.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .store import message_hash

WORKSPACE_ENV = "OPENCLAW_WORKSPACE_DIR"
_LOCK = threading.Lock()


@dataclass(slots=True)
class ChannelLogRecord:
    channel: str
    user_id: str
    status: str
    kind: str = "text"
    thread_id: str | None = None
    message_id_hash: str | None = None
    route: str | None = None
    tools: list[str] = field(default_factory=list)
    latency_ms: int = 0
    model_calls: int = 0
    error_code: str | None = None
    event: str | None = None  # spec 025: p. ej. «planner_denied» (sin número ni texto)
    # Spec 028: modo de entrada, idioma, formato y tiempos de voz (nunca texto ni audio).
    input_mode: str = "text"
    language: str | None = None
    reply_format: str | None = None
    script_ms: int | None = None
    voice_ms: int | None = None
    voice_sent: bool = False
    # Spec 030: qué va por escrito con la voz: «full», «sources» o «none» (solo la etiqueta).
    written: str | None = None
    # Spec 032: sin texto ni números. Motivo de inicio («first_contact», «inactivity», «restart»)
    # y origen de la presentación («bridge» o «agent») en el turno que abre la conversación.
    conversation_start: str | None = None
    introduced: str | None = None
    sender_kind: str | None = None  # Spec 033: phone | lid | telegram, nunca el valor
    sticker: str | None = None  # Spec 034: nombre del sticker, nunca contenido
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    @classmethod
    def for_message(cls, message_id: str | None, **values: Any) -> ChannelLogRecord:
        return cls(message_id_hash=message_hash(message_id) if message_id else None, **values)


def log_channel(log_dir: Path | None, record: ChannelLogRecord) -> None:
    if log_dir is None:
        return
    log_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(record), ensure_ascii=False)
    with _LOCK, (log_dir / "channels.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def workspace_dir() -> Path | None:
    value = os.environ.get(WORKSPACE_ENV, "").strip()
    return Path(value) if value else None


def append_daily(record: ChannelLogRecord, root: Path | None = None) -> Path | None:
    """Añade una línea a ``memory/YYYY-MM-DD.md`` del workspace de ejecución."""
    base = root if root is not None else workspace_dir()
    if base is None:
        return None
    stamp = datetime.fromisoformat(record.ts)
    path = base / "memory" / f"{stamp.date().isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    tools = ", ".join(record.tools) if record.tools else "—"
    line = (
        f"- {stamp.strftime('%H:%M:%S')} UTC · {record.channel} · `{record.user_id}` · "
        f"{record.status} · ruta {record.route or '—'} · herramientas {tools} · "
        f"{record.latency_ms} ms" + (f" · error {record.error_code}" if record.error_code else "")
    )
    with _LOCK:
        new = not path.exists()
        with path.open("a", encoding="utf-8") as handle:
            if new:
                handle.write(
                    f"# Bitácora de Valer-IA Caña · {stamp.date().isoformat()}\n\n"
                    "Generada por el backend (spec 024). Sin texto de mensajes ni números de "
                    "teléfono: solo seudónimos, rutas, herramientas y tiempos.\n\n"
                )
            handle.write(line + "\n")
    return path


def recent_stats(log_dir: Path | None, *, now: datetime | None = None) -> dict[str, Any]:
    """Resumen para ``GET /api/channels/status``: última hora y, desde la spec 031, el día local.

    ``people_today`` cuenta seudónimos distintos atendidos hoy; ``limited_today`` los mensajes
    frenados por límite (ventana o tope diario) y ``blocked_today`` los de números bloqueados. Sin
    números ni texto.
    """
    stats: dict[str, dict[str, Any]] = {}
    if log_dir is None or not (log_dir / "channels.jsonl").is_file():
        return stats
    current = now or datetime.now(UTC)
    latencies: dict[str, list[int]] = {}
    today = current.astimezone().date()
    people: dict[str, set[str]] = {}
    for line in (log_dir / "channels.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(row["ts"])
        except ValueError, KeyError, json.JSONDecodeError:
            continue
        channel = str(row.get("channel", "?"))
        entry = stats.setdefault(
            channel,
            {
                "last_message_at": None,
                "messages_1h": 0,
                "errors_1h": 0,
                "p90_latency_ms": 0,
                "people_today": 0,
                "limited_today": 0,
                "blocked_today": 0,
            },
        )
        entry["last_message_at"] = row["ts"]
        if ts.astimezone().date() == today:
            event = row.get("event")
            if event in ("rate_limited", "daily_capped"):
                entry["limited_today"] += 1
            elif event == "blocked":
                entry["blocked_today"] += 1
            elif row.get("status") != "ignored" and row.get("user_id"):
                people.setdefault(channel, set()).add(str(row["user_id"]))
        if (current - ts).total_seconds() <= 3600:
            entry["messages_1h"] += 1
            if row.get("status") == "error":
                entry["errors_1h"] += 1
            if row.get("status") in ("answered", "approval_resolved"):
                latencies.setdefault(channel, []).append(int(row.get("latency_ms") or 0))
    for channel, users in people.items():
        stats[channel]["people_today"] = len(users)
    for channel, values in latencies.items():
        ordered = sorted(values)
        stats[channel]["p90_latency_ms"] = ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))]
    return stats
