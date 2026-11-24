"""Estado del canal en ``$MANUELITA_STATE_DIR/channels.sqlite3`` (spec 024, data-model §1–5).

Tablas: ``channel_users`` (seudónimo, canal, máscara e hilo activo), ``channel_threads``,
``channel_seen`` (deduplicación de ``message_id``) y ``channel_pending`` (confirmaciones SÍ/NO).
Nunca guarda números de teléfono ni el texto de los mensajes: el texto vive en el checkpointer.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_users (
    user_id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    masked TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    active_thread_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_threads (
    thread_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    started INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS channel_seen (
    message_hash TEXT PRIMARY KEY,
    seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_pending (
    thread_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    state TEXT NOT NULL
);
"""
PENDING_STATES = ("pending", "approved", "rejected", "expired")


def message_hash(message_id: str) -> str:
    return hashlib.sha256(message_id.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True, slots=True)
class PendingApproval:
    thread_id: str
    action_id: str
    tool: str
    summary: str
    created_at: datetime
    expires_at: datetime
    state: str

    def expired(self, now: datetime) -> bool:
        return self.state == "pending" and now >= self.expires_at


class ChannelStore:
    """Acceso con candado a la base del canal (un proceso backend; modo WAL)."""

    def __init__(self, path: Path, *, clock: Callable[[], datetime] | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)
        self._db.commit()

    def now(self) -> datetime:
        return self._clock()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- usuarios e hilos -------------------------------------------------------------------
    def ensure_user(self, user_id: str, channel: str, masked: str) -> str:
        """Devuelve el hilo activo del usuario; lo crea en el primer mensaje."""
        now = self.now().isoformat()
        with self._lock:
            row = self._db.execute(
                "SELECT active_thread_id FROM channel_users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is not None:
                self._db.execute(
                    "UPDATE channel_users SET last_seen = ?, masked = ? WHERE user_id = ?",
                    (now, masked, user_id),
                )
                self._db.commit()
                return str(row[0])
            thread_id = str(uuid.uuid4())
            self._db.execute(
                "INSERT INTO channel_users VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, channel, masked, now, now, thread_id),
            )
            self._db.execute(
                "INSERT INTO channel_threads VALUES (?, ?, ?, NULL, 0)", (thread_id, user_id, now)
            )
            self._db.commit()
            return thread_id

    def new_thread(self, user_id: str) -> str:
        """Cierra el hilo activo y abre otro (comando ``/nuevo``); el perfil se conserva."""
        now = self.now().isoformat()
        thread_id = str(uuid.uuid4())
        with self._lock:
            row = self._db.execute(
                "SELECT active_thread_id FROM channel_users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row is None:
                raise KeyError(user_id)
            self._db.execute(
                "UPDATE channel_threads SET closed_at = ? WHERE thread_id = ?", (now, row[0])
            )
            self._db.execute(
                "INSERT INTO channel_threads VALUES (?, ?, ?, NULL, 0)", (thread_id, user_id, now)
            )
            self._db.execute(
                "UPDATE channel_users SET active_thread_id = ? WHERE user_id = ?",
                (thread_id, user_id),
            )
            self._db.commit()
        return thread_id

    def is_started(self, thread_id: str) -> bool:
        """``True`` si el hilo ya tuvo un turno en el checkpointer (columna ``started``)."""
        with self._lock:
            row = self._db.execute(
                "SELECT started FROM channel_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return bool(row and row[0])

    def adopt_thread(self, user_id: str, placeholder: str, thread_id: str) -> None:
        """Sustituye el id provisional por el que creó el servicio y lo marca como iniciado."""
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET thread_id = ?, started = 1 WHERE thread_id = ?",
                (thread_id, placeholder),
            )
            self._db.execute(
                "UPDATE channel_users SET active_thread_id = ? "
                "WHERE user_id = ? AND active_thread_id = ?",
                (thread_id, user_id, placeholder),
            )
            self._db.commit()

    def threads(self, user_id: str) -> list[tuple[str, str | None]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT thread_id, closed_at FROM channel_threads WHERE user_id = ? "
                "ORDER BY created_at",
                (user_id,),
            ).fetchall()
        return [(str(r[0]), r[1]) for r in rows]

    # -- deduplicación ----------------------------------------------------------------------
    def seen(self, message_id: str, *, retention_hours: int = 48) -> bool:
        """``True`` si el mensaje ya se atendió; si no, lo marca. Purga lo más antiguo."""
        now = self.now()
        key = message_hash(message_id)
        with self._lock:
            self._db.execute(
                "DELETE FROM channel_seen WHERE seen_at < ?",
                ((now - timedelta(hours=retention_hours)).isoformat(),),
            )
            exists = self._db.execute(
                "SELECT 1 FROM channel_seen WHERE message_hash = ?", (key,)
            ).fetchone()
            if exists is None:
                self._db.execute("INSERT INTO channel_seen VALUES (?, ?)", (key, now.isoformat()))
            self._db.commit()
        return exists is not None

    # -- confirmaciones pendientes ------------------------------------------------------------
    def set_pending(
        self, thread_id: str, action_id: str, tool: str, summary: str, *, ttl_minutes: int
    ) -> PendingApproval:
        now = self.now()
        expires = now + timedelta(minutes=ttl_minutes)
        pending = PendingApproval(thread_id, action_id, tool, summary, now, expires, "pending")
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO channel_pending VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    thread_id,
                    action_id,
                    tool,
                    summary,
                    now.isoformat(),
                    pending.expires_at.isoformat(),
                    "pending",
                ),
            )
            self._db.commit()
        return pending

    def get_pending(self, thread_id: str) -> PendingApproval | None:
        with self._lock:
            row = self._db.execute(
                "SELECT thread_id, action_id, tool, summary, created_at, expires_at, state "
                "FROM channel_pending WHERE thread_id = ? AND state = 'pending'",
                (thread_id,),
            ).fetchone()
        if row is None:
            return None
        return PendingApproval(
            row[0],
            row[1],
            row[2],
            row[3],
            datetime.fromisoformat(row[4]),
            datetime.fromisoformat(row[5]),
            row[6],
        )

    def resolve_pending(self, thread_id: str, state: str) -> None:
        if state not in PENDING_STATES[1:]:
            raise ValueError(f"estado inválido: {state}")
        with self._lock:
            self._db.execute(
                "UPDATE channel_pending SET state = ? WHERE thread_id = ? AND state = 'pending'",
                (state, thread_id),
            )
            self._db.commit()

    def pending_count(self) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) FROM channel_pending WHERE state = 'pending'"
            ).fetchone()
        return int(row[0]) if row else 0
