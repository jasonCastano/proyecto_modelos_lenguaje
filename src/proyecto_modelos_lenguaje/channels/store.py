"""Estado del canal en ``$MANUELITA_STATE_DIR/channels.sqlite3`` (spec 024, data-model §1–5).

Tablas: ``channel_users`` (seudónimo, canal, máscara e hilo activo), ``channel_threads``,
``channel_seen`` (deduplicación de ``message_id``), ``channel_pending`` (confirmaciones SÍ/NO) y,
desde la spec 031, ``channel_usage`` (límites por seudónimo) y ``channel_blocked`` (bloqueados).
Spec 032: ``channel_threads.introduced`` marca si el hilo ya recibió la presentación de Valer-IA.
Spec 034: ``channel_stickers`` guarda qué stickers recibió cada hilo (solo el nombre) y
``channel_threads.answered_turns`` numera las respuestas atendidas, para moderar su uso.
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
from typing import Literal

from .limits import Usage
from .stickers import ThreadUsage

ConversationStart = Literal["first_contact", "inactivity"]

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
    started INTEGER NOT NULL DEFAULT 0,
    reply_format TEXT NOT NULL DEFAULT 'auto',
    last_route TEXT,
    introduced INTEGER NOT NULL DEFAULT 1,
    answered_turns INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS channel_stickers (
    thread_id TEXT NOT NULL,
    sticker TEXT NOT NULL,
    turn_no INTEGER NOT NULL,
    sent_at TEXT NOT NULL
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
CREATE TABLE IF NOT EXISTS channel_usage (
    user_id TEXT PRIMARY KEY,
    window_start TEXT NOT NULL,
    window_count INTEGER NOT NULL,
    window_notified INTEGER NOT NULL,
    day TEXT NOT NULL,
    day_count INTEGER NOT NULL,
    day_notified INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS channel_blocked (
    user_id TEXT PRIMARY KEY,
    blocked_at TEXT NOT NULL
);
"""
PENDING_STATES = ("pending", "approved", "rejected", "expired", "superseded")
# Spec 028 (data-model «ChannelThread»): formato de respuesta por conversación.
REPLY_FORMATS = ("auto", "text", "voice")
# Columnas añadidas después de la spec 024: se agregan a bases existentes sin perder datos.
MIGRATIONS = (
    ("channel_threads", "reply_format", "TEXT NOT NULL DEFAULT 'auto'"),
    ("channel_threads", "last_route", "TEXT"),
    # Spec 032 (research R5): los hilos anteriores quedan presentados; los nuevos se crean en 0.
    ("channel_threads", "introduced", "INTEGER NOT NULL DEFAULT 1"),
    ("channel_threads", "answered_turns", "INTEGER NOT NULL DEFAULT 0"),  # spec 034
    ("channel_threads", "stickers_off", "INTEGER NOT NULL DEFAULT 0"),  # spec 037
    ("channel_stickers", "situation", "TEXT"),  # spec 037: situación de cada sticker
)


def _older_than(last_seen: str | None, now: datetime, hours: int) -> bool:
    """``True`` si ``last_seen`` (ISO) es más viejo que ``hours``; sin fecha válida, no."""
    try:
        seen = datetime.fromisoformat(str(last_seen))
    except ValueError:
        return False
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now - seen > timedelta(hours=hours)


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
        self._migrate()
        self._db.commit()

    def _migrate(self) -> None:
        for table, column, ddl in MIGRATIONS:
            columns = {row[1] for row in self._db.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                self._db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def now(self) -> datetime:
        return self._clock()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- usuarios e hilos -------------------------------------------------------------------
    def ensure_user(self, user_id: str, channel: str, masked: str) -> str:
        """Devuelve el hilo activo del usuario; lo crea en el primer mensaje (sin inactividad)."""
        thread_id, _ = self.open_conversation(user_id, channel, masked, idle_hours=None)
        return thread_id

    def open_conversation(
        self, user_id: str, channel: str, masked: str, *, idle_hours: int | None
    ) -> tuple[str, ConversationStart | None]:
        """Hilo activo y motivo si la conversación empieza ahora (spec 032, contrato §1).

        ``first_contact``: el seudónimo nunca había escrito. ``inactivity``: el último mensaje es
        más viejo que ``idle_hours``; el hilo anterior se cierra y se abre otro (el perfil aprobado
        vive aparte y se conserva). ``last_seen`` se lee antes de actualizarlo.
        """
        current = self.now()
        now = current.isoformat()
        with self._lock:
            row = self._db.execute(
                "SELECT active_thread_id, last_seen FROM channel_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                thread_id = str(uuid.uuid4())
                self._db.execute(
                    "INSERT INTO channel_users VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, channel, masked, now, now, thread_id),
                )
                self._insert_thread(thread_id, user_id, now)
                self._db.commit()
                return thread_id, "first_contact"
            thread_id, reason = str(row[0]), None
            if idle_hours is not None and _older_than(row[1], current, idle_hours):
                self._db.execute(
                    "UPDATE channel_threads SET closed_at = ? WHERE thread_id = ?", (now, thread_id)
                )
                thread_id, reason = str(uuid.uuid4()), "inactivity"
                self._insert_thread(thread_id, user_id, now)
            self._db.execute(
                "UPDATE channel_users SET last_seen = ?, masked = ?, active_thread_id = ? "
                "WHERE user_id = ?",
                (now, masked, thread_id, user_id),
            )
            self._db.commit()
            return thread_id, reason

    def _insert_thread(self, thread_id: str, user_id: str, now: str) -> None:
        """Hilo nuevo sin presentar (``introduced = 0``); se llama con el candado tomado."""
        self._db.execute(
            "INSERT INTO channel_threads (thread_id, user_id, created_at, started, introduced) "
            "VALUES (?, ?, ?, 0, 0)",
            (thread_id, user_id, now),
        )

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
            self._insert_thread(thread_id, user_id, now)
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

    def is_introduced(self, thread_id: str) -> bool:
        """Spec 032: ``True`` si el hilo ya recibió la presentación (o es anterior a la spec)."""
        with self._lock:
            row = self._db.execute(
                "SELECT introduced FROM channel_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return bool(row is None or row[0])

    def mark_introduced(self, thread_id: str) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET introduced = 1 WHERE thread_id = ?", (thread_id,)
            )
            self._db.commit()

    # -- stickers (spec 034) -----------------------------------------------------------------
    def count_answered(self, thread_id: str) -> int:
        """Suma una respuesta atendida al hilo y devuelve su número (1, 2, …)."""
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET answered_turns = answered_turns + 1 "
                "WHERE thread_id = ?",
                (thread_id,),
            )
            row = self._db.execute(
                "SELECT answered_turns FROM channel_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
            self._db.commit()
        return int(row[0]) if row else 1

    def sticker_usage(self, thread_id: str, turn_no: int) -> ThreadUsage:
        """Stickers del hilo, el último y su situación, y si la persona los apagó (spec 037)."""
        with self._lock:
            rows = self._db.execute(
                "SELECT sticker, turn_no, situation FROM channel_stickers WHERE thread_id = ? "
                "ORDER BY turn_no",
                (thread_id,),
            ).fetchall()
            flag = self._db.execute(
                "SELECT stickers_off FROM channel_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        sent = tuple(str(row[0]) for row in rows)
        last = rows[-1] if rows else None
        return ThreadUsage(
            turn_no=turn_no,
            last_sticker_turn=int(last[1]) if last else None,
            sent=sent,
            last_sticker=str(last[0]) if last else None,
            last_situation=str(last[2]) if last and last[2] else None,
            off=bool(flag and flag[0]),
        )

    def record_sticker(self, thread_id: str, name: str, turn_no: int, situation: str = "") -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO channel_stickers (thread_id, sticker, turn_no, sent_at, situation) "
                "VALUES (?, ?, ?, ?, ?)",
                (thread_id, name, turn_no, self.now().isoformat(), situation or None),
            )
            self._db.commit()

    def set_stickers_off(self, thread_id: str) -> None:
        """Spec 037 (FR-012): la persona pidió no recibir stickers en esta conversación."""
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET stickers_off = 1 WHERE thread_id = ?", (thread_id,)
            )
            self._db.commit()

    def adopt_thread(self, user_id: str, placeholder: str, thread_id: str) -> None:
        """Sustituye el id provisional por el que creó el servicio y lo marca como iniciado."""
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET thread_id = ?, started = 1 WHERE thread_id = ?",
                (thread_id, placeholder),
            )
            self._db.execute(  # spec 034: los stickers siguen al hilo definitivo
                "UPDATE channel_stickers SET thread_id = ? WHERE thread_id = ?",
                (thread_id, placeholder),
            )
            self._db.execute(
                "UPDATE channel_users SET active_thread_id = ? "
                "WHERE user_id = ? AND active_thread_id = ?",
                (thread_id, user_id, placeholder),
            )
            self._db.commit()

    # -- formato de respuesta y ruta anterior (spec 028) ---------------------------------------
    def get_reply_format(self, thread_id: str) -> str:
        with self._lock:
            row = self._db.execute(
                "SELECT reply_format FROM channel_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return str(row[0]) if row and row[0] in REPLY_FORMATS else "auto"

    def set_reply_format(self, thread_id: str, reply_format: str) -> None:
        if reply_format not in REPLY_FORMATS:
            raise ValueError(f"formato inválido: {reply_format}")
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET reply_format = ? WHERE thread_id = ?",
                (reply_format, thread_id),
            )
            self._db.commit()

    def get_last_route(self, thread_id: str) -> str | None:
        with self._lock:
            row = self._db.execute(
                "SELECT last_route FROM channel_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return str(row[0]) if row and row[0] else None

    def set_last_route(self, thread_id: str, route: str | None) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE channel_threads SET last_route = ? WHERE thread_id = ?", (route, thread_id)
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

    # -- spec 031: uso por seudónimo y bloqueados -----------------------------------------------
    def get_usage(self, user_id: str) -> Usage | None:
        with self._lock:
            row = self._db.execute(
                "SELECT window_start, window_count, window_notified, day, day_count, day_notified "
                "FROM channel_usage WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return Usage(
            datetime.fromisoformat(row[0]), int(row[1]), bool(row[2]), str(row[3]), int(row[4]),
            bool(row[5]),
        )  # fmt: skip

    def save_usage(self, user_id: str, usage: Usage) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO channel_usage VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET window_start = excluded.window_start, "
                "window_count = excluded.window_count, "
                "window_notified = excluded.window_notified, day = excluded.day, "
                "day_count = excluded.day_count, day_notified = excluded.day_notified",
                (
                    user_id, usage.window_start.isoformat(), usage.window_count,
                    int(usage.window_notified), usage.day, usage.day_count, int(usage.day_notified),
                ),
            )  # fmt: skip
            self._db.commit()

    def block(self, user_id: str) -> bool:
        """Bloquea un seudónimo; ``False`` si ya estaba bloqueado."""
        with self._lock:
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO channel_blocked VALUES (?, ?)",
                (user_id, self.now().isoformat()),
            )
            self._db.commit()
        return cursor.rowcount > 0

    def unblock(self, user_id: str) -> bool:
        """Desbloquea un seudónimo; ``False`` si no estaba bloqueado."""
        with self._lock:
            cursor = self._db.execute("DELETE FROM channel_blocked WHERE user_id = ?", (user_id,))
            self._db.commit()
        return cursor.rowcount > 0

    def is_blocked(self, user_id: str) -> bool:
        with self._lock:
            row = self._db.execute(
                "SELECT 1 FROM channel_blocked WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def blocked(self) -> list[tuple[str, str]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT user_id, blocked_at FROM channel_blocked ORDER BY blocked_at"
            ).fetchall()
        return [(str(user), str(at)) for user, at in rows]
