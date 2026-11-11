"""CLI del agente RAG: ``chat``, ``build-structured`` y ``evaluate``.

Uso::

    uv run python -m proyecto_modelos_lenguaje.agent build-structured
    uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo "¿Qué produce Manuelita?"
    uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode demo
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from ..config import PROJECT_ROOT
from .config import AgentConfigError, load_agent_config
from .structured import (
    StructuredExistsError,
    StructuredGoldError,
    StructuredInvalidError,
    build_structured_store,
)

NOT_IMPLEMENTED_EXIT = 64
GOLD_DIR = Path("data") / "gold"
REPORT_PATH = Path("docs") / "evaluacion_modulo2.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m proyecto_modelos_lenguaje.agent",
        description="Agente RAG con memoria y enrutador (Módulo 2).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    chat = sub.add_parser("chat", help="Envía un mensaje a un hilo de conversación.")
    chat.add_argument("message")
    chat.add_argument("--thread", help="Identificador del hilo; si falta se crea uno nuevo.")
    chat.add_argument("--variant", choices=("chain", "agent"), default="chain")
    chat.add_argument("--mode", choices=("demo", "real"), default="demo")
    chat.add_argument("--json", action="store_true", help="Imprime la respuesta en JSON.")

    structured = sub.add_parser(
        "build-structured", help="Construye la tabla SQLite derivada del oro."
    )
    structured.add_argument("--force", action="store_true")

    evaluate = sub.add_parser("evaluate", help="Evalúa enrutador y variantes.")
    evaluate.add_argument("--queries", default="tests/fixtures/rag/module2_queries.jsonl")
    evaluate.add_argument("--variants", nargs="+", choices=("chain", "agent"), default=["chain"])
    evaluate.add_argument("--mode", choices=("demo", "real"), default="demo")
    evaluate.add_argument("--run-id", default="")
    evaluate.add_argument(
        "--report", default=str(REPORT_PATH), help="Markdown donde se escribe la sección."
    )
    evaluate.add_argument("--json-out", default=None)
    return parser


def _build_structured(args: argparse.Namespace, root: Path) -> int:
    try:
        config = load_agent_config(project_root=root)
        manifest = build_structured_store(root / GOLD_DIR, config.structured_path, force=args.force)
    except AgentConfigError as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 5
    except StructuredExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except StructuredGoldError as exc:
        print(f"error de oro: {exc}", file=sys.stderr)
        return 3
    except StructuredInvalidError as exc:
        print(f"manifiesto inválido: {exc}", file=sys.stderr)
        return 5
    print(
        f"tabla estructurada lista en {config.structured_path} · {manifest.entity_count} "
        f"entidades · {manifest.fact_count} hechos · {manifest.citation_count} citas"
    )
    return 0


def _evaluate(args: argparse.Namespace, root: Path) -> int:
    from .evaluate import (
        evaluate_router,
        load_router_cases,
        render_router_section,
        write_router_section,
    )

    config = load_agent_config(project_root=root)
    model = None
    if args.mode == "real":
        from ..llm import build_chat_model, load_llm_config

        model = build_chat_model(load_llm_config())
    run_id = args.run_id or datetime.now(UTC).strftime(f"router-{args.mode}-%Y%m%dT%H%M%SZ")
    report = evaluate_router(
        load_router_cases(root / args.queries),
        model=model,
        min_confidence=config.router.min_confidence,
        run_id=run_id,
        mode=args.mode,
    )
    write_router_section(root / args.report, render_router_section(report))
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"enrutador: {report.correct}/{report.cases} ({report.accuracy:.3f}) · "
        f"sin búsqueda {report.no_search_ok}/{report.no_search_total} · "
        f"{report.model_calls} llamadas al modelo"
    )
    return 0


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    if args.command == "build-structured":
        return _build_structured(args, root)
    if args.command == "evaluate":
        return _evaluate(args, root)
    print(
        f"El subcomando «{args.command}» aún no está implementado (spec 014, ver tasks.md).",
        file=sys.stderr,
    )
    return NOT_IMPLEMENTED_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
