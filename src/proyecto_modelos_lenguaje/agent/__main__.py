"""CLI del agente RAG: ``chat``, ``build-structured`` y ``evaluate``.

Uso::

    uv run python -m proyecto_modelos_lenguaje.agent build-structured
    uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo "¿Qué produce Manuelita?"
    uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode demo
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

NOT_IMPLEMENTED_EXIT = 64


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(
        f"El subcomando «{args.command}» aún no está implementado (spec 014, ver tasks.md).",
        file=sys.stderr,
    )
    return NOT_IMPLEMENTED_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
