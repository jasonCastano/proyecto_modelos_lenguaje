"""Servidor MCP propio ``valeria-tools`` (spec 024, ítem 3.4, research R10).

Expone por stdio **solo las herramientas de lectura** del catálogo (``agent/catalog.py``): las de
escritura requieren aprobación humana y no existen en este servidor (permiso por construcción).
OpenClaw lo registra en ``mcp.servers`` y lo usa su agente nativo en el modo degradado.

    uv run python -m proyecto_modelos_lenguaje.mcp_server          # servidor stdio
    uv run python -m proyecto_modelos_lenguaje.mcp_server --list   # herramientas expuestas

Cada llamada queda en ``$MANUELITA_STATE_DIR/logs/mcp.jsonl`` (herramienta, duración, ok), sin
argumentos de texto libre.
"""

from __future__ import annotations

import argparse
import inspect
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv

from .agent.catalog import ToolArgsError, ToolContext, ToolSpec, read_specs, run_read
from .config import PROJECT_ROOT

SERVER_NAME = "valeria-tools"
INSTRUCTIONS = (
    "Herramientas de solo lectura de Valer-IA Caña sobre la información pública de Manuelita. "
    "Cita siempre las referencias [U#]/[F#] que devuelven; si no hay resultados, dilo."
)


@lru_cache(maxsize=1)
def _context_parts() -> tuple[Any, Any, Any]:
    """Recuperador, tabla estructurada y series: una sola carga por proceso."""
    from . import api
    from .agent.config import load_agent_config
    from .agent.service import default_series, open_store

    return api._retriever("real"), open_store(load_agent_config()), default_series()


def build_context() -> ToolContext:
    retriever, store, series = _context_parts()
    return ToolContext(retriever=retriever, store=store, series=series)


def _log_dir() -> Path | None:
    try:
        from .agent.config import load_agent_config, resolve_state_dir

        return resolve_state_dir(load_agent_config().state_env_var) / "logs"
    except Exception:
        return None


def _log(name: str, ok: bool, duration_ms: int) -> None:
    directory = _log_dir()
    if directory is None:
        return
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "tool": name,
        "ok": ok,
        "duration_ms": duration_ms,
    }
    with (directory / "mcp.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def tool_function(
    spec: ToolSpec, context: Callable[[], ToolContext] = build_context
) -> Callable[..., str]:
    """Función con la firma del esquema Pydantic (el SDK deriva el JSON Schema de ella)."""

    def call(**kwargs: Any) -> str:
        started = time.perf_counter()
        ok = True
        try:
            return run_read(spec, context(), kwargs)
        except ToolArgsError as exc:
            ok = False
            return str(exc)
        finally:
            _log(spec.name, ok, round((time.perf_counter() - started) * 1000))

    parameters = []
    for name, field in spec.args_schema.model_fields.items():
        default = inspect.Parameter.empty if field.is_required() else field.default
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=Annotated[field.annotation, field],
            )
        )
    call.__signature__ = inspect.Signature(parameters, return_annotation=str)  # type: ignore[attr-defined]
    call.__annotations__ = {p.name: p.annotation for p in parameters} | {"return": str}
    call.__name__ = spec.name
    return call


def exposed_specs() -> tuple[ToolSpec, ...]:
    return tuple(spec for spec in read_specs() if spec.mcp)


def build_server(context: Callable[[], ToolContext] = build_context) -> Any:
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(SERVER_NAME, instructions=INSTRUCTIONS)
    for spec in exposed_specs():
        server.add_tool(tool_function(spec, context), name=spec.name, description=spec.description)
    return server


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(prog="python -m proyecto_modelos_lenguaje.mcp_server")
    parser.add_argument("--list", action="store_true", help="lista las herramientas expuestas")
    args = parser.parse_args(argv)
    if args.list:
        for spec in exposed_specs():
            print(f"{spec.number:>2} {spec.name}: {spec.description}")
        return 0
    build_server().run("stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
