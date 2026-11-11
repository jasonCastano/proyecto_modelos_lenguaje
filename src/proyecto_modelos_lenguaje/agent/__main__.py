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
    chat.add_argument("--user", default="anon-cli", help="Identificador anónimo del usuario.")
    chat.add_argument("--json", action="store_true", help="Imprime la respuesta en JSON.")

    structured = sub.add_parser(
        "build-structured", help="Construye la tabla SQLite derivada del oro."
    )
    structured.add_argument("--force", action="store_true")

    evaluate = sub.add_parser("evaluate", help="Evalúa enrutador y variantes.")
    evaluate.add_argument("--queries", default="tests/fixtures/rag/module2_queries.jsonl")
    evaluate.add_argument(
        "--variants", nargs="+", choices=("chain", "agent"), default=["chain", "agent"]
    )
    evaluate.add_argument(
        "--compare", action="store_true", help="Compara las variantes sobre el conjunto (T066)."
    )
    evaluate.add_argument(
        "--judge", action="store_true", help="Juez LLM de fidelidad y relevancia (T067)."
    )
    evaluate.add_argument(
        "--skip-router", action="store_true", help="No repite la evaluación del enrutador."
    )
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
    from ..tasks import _configure_output

    _configure_output()
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
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload: dict[str, object] = {}
    if not args.skip_router:
        run_id = args.run_id or f"router-{args.mode}-{stamp}"
        report = evaluate_router(
            load_router_cases(root / args.queries),
            model=model,
            min_confidence=config.router.min_confidence,
            run_id=run_id,
            mode=args.mode,
        )
        write_router_section(root / args.report, render_router_section(report))
        payload["router"] = report.to_dict()
        print(
            f"enrutador: {report.correct}/{report.cases} ({report.accuracy:.3f}) · "
            f"sin búsqueda {report.no_search_ok}/{report.no_search_total} · "
            f"{report.model_calls} llamadas al modelo"
        )
    if args.compare:
        payload["variants"] = _compare(args, root, config, model, stamp)
    if args.json_out:
        data = payload.get("router") if list(payload) == ["router"] else payload
        Path(args.json_out).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 0


def _compare(args: argparse.Namespace, root: Path, config, model, stamp: str) -> list[dict]:
    """Cadena vs. agente con estado en memoria (no toca ``MANUELITA_STATE_DIR``)."""
    from .compare import load_queries, render_variants_section, run_variant, write_section
    from .memory import memory_checkpointer, memory_store
    from .service import ChatService, build_deps

    service = ChatService(
        config,
        memory_checkpointer(),
        lambda mode: build_deps(mode, config, _cli_retriever(mode, root)),
        store=memory_store(),
    )
    queries = load_queries(root / args.queries)
    judge_model = model if args.judge else None
    reports = [
        run_variant(
            service,
            variant,
            queries,
            mode=args.mode,
            judge_model=judge_model,
            progress=lambda line: print(line, flush=True),
        )
        for variant in args.variants
    ]
    run_id = args.run_id or f"variants-{args.mode}-{stamp}"
    write_section(
        root / args.report, render_variants_section(reports, run_id=run_id, mode=args.mode)
    )
    summary = []
    for report in reports:
        metrics = report.metrics()
        summary.append({**metrics, "results": [r.to_dict() for r in report.results]})
        print(
            f"{report.variant}: citas {metrics['citation_validity']} · repreguntas "
            f"{metrics['follow_up_correct']} · p95 {metrics['latency_ms_p95']} ms"
        )
    return summary


def _cli_retriever(mode: str, root: Path):
    from ..rag.config import load_retrieval_config
    from ..rag.embeddings import EmbeddingProfile, build_embedder
    from ..rag.errors import IndexInvalidError, IndexUnavailableError
    from ..rag.hybrid import HybridRetriever
    from ..rag.index import load_index
    from ..retrieval import load_entity_index, load_gold_units
    from .demo import DEMO_EMBEDDER_KIND, DEMO_INDEX

    config = load_retrieval_config(project_root=root)
    profile = EmbeddingProfile.from_config(config.embedding)
    index_dir = DEMO_INDEX if mode == "demo" else config.index_dir
    notes: list[str] = []
    try:
        index = load_index(index_dir, profile)
    except (IndexUnavailableError, IndexInvalidError) as exc:
        index = None
        notes.append(f"Índice no utilizable: {exc}")
    gold = root / GOLD_DIR
    return HybridRetriever(
        load_gold_units(gold),
        index=index,
        embedder=build_embedder(
            profile, kind=DEMO_EMBEDDER_KIND if mode == "demo" else "fastembed"
        ),
        entity_index=load_entity_index(gold),
        config=config,
        notes=tuple(notes),
    )


def _print_turn(outcome) -> None:
    turn = outcome.turn
    route = turn.route
    print(f"hilo {outcome.thread_id} · turno {turn.turn_id} · {outcome.status}")
    print(f"ruta {route.route} ({route.confidence:.2f}, {route.decided_by}): {route.reason}")
    print()
    print(turn.answer)
    if turn.citations:
        print()
        for citation in turn.citations:
            title = (citation.get("title") or "").strip().splitlines()[:1]
            print(f"[{citation['label']}] {(title[0] if title else '')[:90]} — {citation['url']}")
    metrics = turn.metrics
    print()
    print(
        f"{metrics.latency_ms} ms · {metrics.model_calls} llamadas al modelo · "
        f"{metrics.tool_calls} búsquedas · {metrics.input_tokens}/{metrics.output_tokens} tokens"
    )


def _chat(args: argparse.Namespace, root: Path) -> int:
    from ..tasks import _configure_output
    from .config import resolve_state_dir
    from .memory import build_checkpointer, build_store
    from .service import ChatError, ChatService, build_deps

    _configure_output()
    try:
        config = load_agent_config(project_root=root)
        state_dir = resolve_state_dir(config.state_env_var, project_root=root)
        checkpointer = build_checkpointer(state_dir)
    except AgentConfigError as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 5
    service = ChatService(
        config,
        checkpointer,
        lambda mode: build_deps(mode, config, _cli_retriever(mode, root)),
        store=build_store(state_dir),
    )
    try:
        outcome = service.send(
            args.message,
            thread_id=args.thread,
            user_id=args.user,
            variant=args.variant,
            mode=args.mode,
        )
    except ChatError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 3 if exc.status_code >= 500 else 2
    if args.json:
        print(json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_turn(outcome)
    return 0


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    if args.command == "build-structured":
        return _build_structured(args, root)
    if args.command == "evaluate":
        return _evaluate(args, root)
    return _chat(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
