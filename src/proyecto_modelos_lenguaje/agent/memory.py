"""Memoria corta del agente: checkpointer por hilo y resumen del historial (FR-007, FR-008).

- ``build_checkpointer`` persiste cada hilo en ``checkpoints.sqlite3`` dentro de
  ``MANUELITA_STATE_DIR`` (nunca en el repositorio); sobrevive a reinicios del proceso.
- ``summarize_turns`` condensa los turnos antiguos cuando el historial supera
  ``memory.summarize_after_tokens`` y conserva los últimos ``memory.keep_last_messages`` mensajes.
  Las citas vigentes se conservan como URL porque las etiquetas ``[U#]`` se renumeran en cada turno.
- ``build_summarization_middleware`` aplica la misma política dentro de una ejecución del agente.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

from .config import MemoryConfig
from .privacy import redact_pii
from .prompts import load_agent_prompt

CHECKPOINT_FILE = "checkpoints.sqlite3"
STORE_FILE = "memory.sqlite3"
CHARS_PER_TOKEN = 4
DEMO_SUMMARY_CHARS = 160


def build_checkpointer(state_dir: Path) -> SqliteSaver:
    """Checkpointer SQLite en ``state_dir``; crea el directorio si falta."""
    state_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(state_dir / CHECKPOINT_FILE, check_same_thread=False)
    saver = SqliteSaver(connection)
    saver.setup()
    return saver


def build_store(state_dir: Path) -> SqliteStore:
    """Store de memoria larga (preferencias por usuario) en ``state_dir``."""
    state_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        state_dir / STORE_FILE, check_same_thread=False, isolation_level=None
    )
    store = SqliteStore(connection)
    store.setup()
    return store


def memory_store() -> InMemoryStore:
    """Store en memoria para pruebas."""
    return InMemoryStore()


def memory_checkpointer() -> InMemorySaver:
    """Checkpointer en memoria para pruebas."""
    return InMemorySaver()


def estimate_tokens(text: str) -> int:
    return max(0, len(text) // CHARS_PER_TOKEN)


def render_turn(turn: dict[str, Any]) -> str:
    """Un turno como texto de memoria, con las URL de sus citas."""
    sources = sorted({c.get("url", "") for c in turn.get("citations", []) if c.get("url")})
    suffix = f" (fuentes: {', '.join(sources)})" if sources else ""
    return f"Usuario: {turn.get('question', '')}\nAsistente: {turn.get('answer', '')}{suffix}"


def turns_to_keep(memory: MemoryConfig) -> int:
    """Cada turno aporta dos mensajes (usuario y asistente)."""
    return max(1, memory.keep_last_messages // 2)


def needs_summary(turns: Sequence[dict[str, Any]], summarized: int, memory: MemoryConfig) -> bool:
    pending = turns[summarized:]
    if len(pending) <= turns_to_keep(memory):
        return False
    text = "\n".join(render_turn(turn) for turn in pending)
    return estimate_tokens(text) > memory.summarize_after_tokens


def _demo_summary(previous: str, turns: Sequence[dict[str, Any]]) -> str:
    lines = [line for line in previous.splitlines() if line.strip()]
    for turn in turns:
        answer = " ".join(str(turn.get("answer", "")).split())[:DEMO_SUMMARY_CHARS]
        sources = sorted({c.get("url", "") for c in turn.get("citations", []) if c.get("url")})
        suffix = f" (fuente: {', '.join(sources)})" if sources else ""
        lines.append(f"- {turn.get('question', '')}: {answer}{suffix}")
    return "\n".join(lines)


def summarize_turns(
    previous: str,
    turns: Sequence[dict[str, Any]],
    model: BaseChatModel | None,
) -> str:
    """Integra ``turns`` en el resumen ``previous`` (modelo real o resumen extractivo en demo)."""
    if model is None:
        return _demo_summary(previous, turns)
    conversation = "\n\n".join(
        ([f"Resumen previo:\n{previous}"] if previous else [])
        + [render_turn(turn) for turn in turns]
    )
    prompt = load_agent_prompt("memory_summary").render(conversation=conversation)
    response = model.invoke([HumanMessage(content=prompt)])
    return str(response.content).strip() or _demo_summary(previous, turns)


def compact_history(
    turns: list[dict[str, Any]],
    summary: str,
    summarized: int,
    memory: MemoryConfig,
    model: BaseChatModel | None,
) -> tuple[str, int]:
    """Devuelve ``(summary, summarized)`` actualizados si el historial superó el umbral."""
    if not needs_summary(turns, summarized, memory):
        return summary, summarized
    cut = len(turns) - turns_to_keep(memory)
    return summarize_turns(summary, turns[summarized:cut], model), cut


def build_summarization_middleware(
    memory: MemoryConfig, model: BaseChatModel
) -> SummarizationMiddleware:
    """Resumen dentro de una ejecución del agente (mensajes y resultados de herramientas)."""
    template = load_agent_prompt("memory_summary").render(conversation="{messages}")
    return SummarizationMiddleware(
        model,
        trigger=("tokens", memory.summarize_after_tokens),
        keep=("messages", memory.keep_last_messages),
        summary_prompt=template,
    )


# ------------------------------------------------- memoria larga (US5, FR-009, FR-010)

PREFERENCE_KEYS: tuple[str, ...] = ("response_format", "topics_of_interest", "language")
PREFERENCE_LABELS = {
    "response_format": "formato de respuesta",
    "topics_of_interest": "temas de interés",
    "language": "idioma",
}
PREFERENCE_MAX_CHARS = 200
PREFERENCE_SEARCH_LIMIT = 100


class PreferenceError(ValueError):
    """Clave fuera de la lista cerrada o valor inválido."""


def preferences_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id, "preferences")


@dataclass(frozen=True, slots=True)
class PreferenceItem:
    key: str
    value: str
    created_at: str
    expires_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class UserMemory:
    """Preferencias declaradas por usuario: lista cerrada de claves, TTL y redacción de PII."""

    def __init__(self, store: BaseStore, ttl_days: int) -> None:
        self.store = store
        self.ttl_days = ttl_days

    def list(self, user_id: str, *, now: datetime | None = None) -> list[PreferenceItem]:
        """Preferencias vigentes; las expiradas se borran al leer."""
        now = now or datetime.now(UTC)
        namespace = preferences_namespace(user_id)
        items: list[PreferenceItem] = []
        for item in self.store.search(namespace, limit=PREFERENCE_SEARCH_LIMIT):
            value = item.value or {}
            expires_at = str(value.get("expires_at", ""))
            if not expires_at or datetime.fromisoformat(expires_at) <= now:
                self.store.delete(namespace, item.key)
                continue
            items.append(
                PreferenceItem(item.key, str(value["value"]), str(value["created_at"]), expires_at)
            )
        return sorted(items, key=lambda preference: PREFERENCE_KEYS.index(preference.key))

    def save(
        self, user_id: str, key: str, value: str, *, now: datetime | None = None
    ) -> PreferenceItem:
        if key not in PREFERENCE_KEYS:
            raise PreferenceError(f"Clave de preferencia no permitida: {key}.")
        clean = redact_pii(" ".join(str(value).split()))
        if not clean or len(clean) > PREFERENCE_MAX_CHARS:
            raise PreferenceError(f"El valor debe tener 1 a {PREFERENCE_MAX_CHARS} caracteres.")
        now = now or datetime.now(UTC)
        item = PreferenceItem(
            key, clean, now.isoformat(), (now + timedelta(days=self.ttl_days)).isoformat()
        )
        self.store.put(
            preferences_namespace(user_id),
            key,
            {"value": item.value, "created_at": item.created_at, "expires_at": item.expires_at},
        )
        return item

    def forget(self, user_id: str) -> int:
        namespace = preferences_namespace(user_id)
        items = self.store.search(namespace, limit=PREFERENCE_SEARCH_LIMIT)
        for item in items:
            self.store.delete(namespace, item.key)
        return len(items)


def render_preferences(items: Sequence[PreferenceItem]) -> str:
    """Bloque para el system prompt: solo la forma de responder, nunca la evidencia."""
    if not items:
        return ""
    lines = [
        "## Preferencias declaradas por el usuario",
        "",
        "Aplícalas a la forma de responder; nunca cambian la evidencia ni las reglas de cita.",
        "",
    ]
    lines += [f"- {PREFERENCE_LABELS[item.key]}: {item.value}" for item in items]
    return "\n".join(lines)
