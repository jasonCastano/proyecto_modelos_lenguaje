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
from pathlib import Path
from typing import Any

from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from .config import MemoryConfig
from .prompts import load_agent_prompt

CHECKPOINT_FILE = "checkpoints.sqlite3"
CHARS_PER_TOKEN = 4
DEMO_SUMMARY_CHARS = 160


def build_checkpointer(state_dir: Path) -> SqliteSaver:
    """Checkpointer SQLite en ``state_dir``; crea el directorio si falta."""
    state_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(state_dir / CHECKPOINT_FILE, check_same_thread=False)
    saver = SqliteSaver(connection)
    saver.setup()
    return saver


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
