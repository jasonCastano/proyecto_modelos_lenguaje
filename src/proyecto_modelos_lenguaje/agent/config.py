"""Configuración tipada del agente RAG (``config/agent.toml``) y directorio de estado."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT

DEFAULT_CONFIG_PATH = Path("config") / "agent.toml"
STATE_DIR_NAME = "manuelita-rag"


class AgentConfigError(ValueError):
    """La configuración del agente falta, es inválida o apunta a un lugar prohibido."""


@dataclass(frozen=True, slots=True)
class RouterConfig:
    min_confidence: float
    llm_temperature: float


@dataclass(frozen=True, slots=True)
class AgentLimits:
    tool_call_limit: int
    model_call_limit: int
    chain_top_k: int


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    summarize_after_tokens: int
    keep_last_messages: int
    preference_ttl_days: int


@dataclass(frozen=True, slots=True)
class AgentConfig:
    router: RouterConfig
    agent: AgentLimits
    memory: MemoryConfig
    structured_path: Path
    state_env_var: str
    source: Path


def _section(document: dict[str, Any], key: str, source: Path) -> dict[str, Any]:
    section = document.get(key)
    if not isinstance(section, dict):
        raise AgentConfigError(f"Falta la sección [{key}] en {source}.")
    return section


def _number(
    section: dict[str, Any],
    key: str,
    *,
    table: str,
    minimum: float,
    maximum: float | None = None,
) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentConfigError(f"{table}.{key} debe ser un número.")
    if value < minimum or (maximum is not None and value > maximum):
        upper = "" if maximum is None else f" y {maximum}"
        raise AgentConfigError(f"{table}.{key} debe estar entre {minimum}{upper}.")
    return float(value)


def _integer(section: dict[str, Any], key: str, *, table: str, minimum: int = 1) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AgentConfigError(f"{table}.{key} debe ser un entero.")
    if value < minimum:
        raise AgentConfigError(f"{table}.{key} debe ser >= {minimum}.")
    return value


def _string(section: dict[str, Any], key: str, *, table: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AgentConfigError(f"{table}.{key} debe ser un texto no vacío.")
    return value.strip()


def load_agent_config(
    path: str | Path | None = None, *, project_root: Path | None = None
) -> AgentConfig:
    """Lee y valida ``config/agent.toml``."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    source = Path(path) if path is not None else root / DEFAULT_CONFIG_PATH
    if not source.is_file():
        raise AgentConfigError(f"No existe la configuración del agente: {source}")
    try:
        document = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise AgentConfigError(f"TOML inválido en {source}: {exc}") from exc

    router = _section(document, "router", source)
    agent = _section(document, "agent", source)
    memory = _section(document, "memory", source)
    structured = _section(document, "structured", source)
    state = _section(document, "state", source)

    structured_path = Path(_string(structured, "path", table="structured"))
    if not structured_path.is_absolute():
        structured_path = root / structured_path

    return AgentConfig(
        router=RouterConfig(
            min_confidence=_number(
                router, "min_confidence", table="router", minimum=0.0, maximum=1.0
            ),
            llm_temperature=_number(
                router, "llm_temperature", table="router", minimum=0.0, maximum=2.0
            ),
        ),
        agent=AgentLimits(
            tool_call_limit=_integer(agent, "tool_call_limit", table="agent"),
            model_call_limit=_integer(agent, "model_call_limit", table="agent"),
            chain_top_k=_integer(agent, "chain_top_k", table="agent"),
        ),
        memory=MemoryConfig(
            summarize_after_tokens=_integer(memory, "summarize_after_tokens", table="memory"),
            keep_last_messages=_integer(memory, "keep_last_messages", table="memory"),
            preference_ttl_days=_integer(memory, "preference_ttl_days", table="memory"),
        ),
        structured_path=structured_path,
        state_env_var=_string(state, "env_var", table="state"),
        source=source,
    )


def _default_state_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / STATE_DIR_NAME
        return Path.home() / "AppData" / "Local" / STATE_DIR_NAME
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / STATE_DIR_NAME
    return Path.home() / ".local" / "state" / STATE_DIR_NAME


def resolve_state_dir(
    env_var: str = "MANUELITA_STATE_DIR", *, project_root: Path | None = None
) -> Path:
    """Directorio del checkpointer y del Store, siempre fuera del repositorio.

    Regla dura de ``AGENTS.md``: la app no escribe en ``data/`` ni en el repositorio.
    """
    root = (Path(project_root) if project_root is not None else PROJECT_ROOT).resolve()
    configured = os.environ.get(env_var, "").strip()
    target = (Path(configured).expanduser() if configured else _default_state_dir()).resolve()
    if target == root or root in target.parents:
        raise AgentConfigError(
            f"El directorio de estado {target} queda dentro del repositorio; "
            f"define {env_var} con una ruta externa."
        )
    return target
