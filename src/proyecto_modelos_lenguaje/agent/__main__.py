"""CLI del agente RAG: ``chat``, ``build-structured``, ``evaluate`` y ``shield``.

Uso::

    uv run python -m proyecto_modelos_lenguaje.agent build-structured
    uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo "¿Qué produce Manuelita?"
    uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode demo
    uv run python -m proyecto_modelos_lenguaje.agent shield --mode real --repeat 3
"""

from __future__ import annotations

import argparse
import contextlib
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
    StructuredStore,
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
    evaluate.add_argument(
        "--tools",
        action="store_true",
        help="Spec 024: exactitud de herramienta sobre tool_routing.jsonl (SC-004).",
    )
    evaluate.add_argument(
        "--fake", action="store_true", help="Equivale a --mode demo (sin red ni clave)."
    )
    evaluate.add_argument(
        "--planning-activation",
        action="store_true",
        help="Spec 028: activación del planificador por contexto (SC-007, sin red).",
    )
    evaluate.add_argument(
        "--markdown",
        action="store_true",
        help="Con --planning-activation: escribe docs/evaluacion_activacion_planificador.md.",
    )

    tools_cmd = sub.add_parser(
        "tools", help="Catálogo de herramientas (20 de la spec 024 + 6 de la 025)."
    )
    tools_cmd.add_argument("--json", action="store_true", help="Imprime el catálogo en JSON.")
    tools_cmd.add_argument("--markdown", default=None, help="Escribe docs/herramientas.md.")

    planning_cmd = sub.add_parser(
        "planning", help="Spec 025: optimiza un escenario sintético sin LLM (plan_card)."
    )
    planning_cmd.add_argument("--scenario", default="{}", help="JSON del escenario.")
    planning_cmd.add_argument("--json", action="store_true")
    planning_eval = sub.add_parser(
        "planning-eval", help="Spec 025: batería de planificación (SC-001/002/004)."
    )
    planning_eval.add_argument("--mode", choices=("direct", "real", "demo"), default="direct")
    planning_eval.add_argument("--write-docs", action="store_true")
    profiles_eval = sub.add_parser("profiles-eval", help="Spec 025: batería de perfiles (SC-003).")
    profiles_eval.add_argument("--mode", choices=("demo", "real"), default="demo")
    profiles_eval.add_argument("--write-docs", action="store_true")

    memory_cmd = sub.add_parser("memory", help="Auditoría de la memoria de largo plazo.")
    memory_sub = memory_cmd.add_subparsers(dest="memory_command", required=True)
    memory_list = memory_sub.add_parser("list", help="Recuerdos de un usuario (seudónimo).")
    memory_list.add_argument("--user", required=True, help="Seudónimo, p. ej. wa-0123…")
    memory_list.add_argument("--json", action="store_true")

    shield = sub.add_parser(
        "shield", help="Evalúa el blindaje contra inyección indirecta (spec 015)."
    )
    shield.add_argument("--mode", choices=("demo", "real"), default="demo")
    shield.add_argument(
        "--variants", nargs="+", choices=("chain", "agent"), default=["chain", "agent"]
    )
    shield.add_argument("--cases", default=None, help="JSONL de casos (shield_cases.jsonl).")
    shield.add_argument("--repeat", type=int, default=1, help="Repeticiones por caso (≥ 1).")
    shield.add_argument(
        "--no-neutralize",
        action="store_true",
        help="Línea base: entrega los fragmentos al modelo sin neutralizar.",
    )
    shield.add_argument("--run-id", default="")
    shield.add_argument("--json-out", default=None, help="Informe JSON (por defecto en real).")
    shield.add_argument("--report", default=None, help="Markdown (por defecto en real).")
    shield.add_argument(
        "--channel",
        action="store_true",
        help="Spec 024: ataques directos e indirectos llegados por el canal WhatsApp.",
    )

    conduct = sub.add_parser(
        "conduct", help="Evalúa la conducta de Valer-IA ante situaciones difíciles (spec 018)."
    )
    conduct.add_argument("--mode", choices=("demo", "real"), default="demo")
    conduct.add_argument(
        "--variants", nargs="+", choices=("chain", "agent"), default=["chain", "agent"]
    )
    conduct.add_argument("--cases", default=None, help="JSONL de casos (conduct_cases.jsonl).")
    conduct.add_argument("--json-out", default=None, help="Informe JSON (por defecto en real).")
    care_cmd = sub.add_parser(
        "care", help="Evalúa las habilidades de atención de Valer-IA (spec 019)."
    )
    care_cmd.add_argument("--mode", choices=("demo", "real"), default="demo")
    care_cmd.add_argument(
        "--variants", nargs="+", choices=("chain", "agent"), default=["chain", "agent"]
    )
    care_cmd.add_argument("--cases", default=None, help="JSONL de casos (care_cases.jsonl).")
    care_cmd.add_argument(
        "--baseline", action="store_true", help="Mide además la latencia sin las habilidades."
    )
    care_cmd.add_argument("--json-out", default=None, help="Informe JSON (por defecto en real).")
    care_cmd.add_argument(
        "--conversation-mode",
        choices=("guided", "scripted"),
        default=None,
        help="Spec 020: modo de conversación (por defecto, el de config/agent.toml).",
    )
    converse_cmd = sub.add_parser(
        "converse", help="Evalúa la naturalidad de la conversación guiada (spec 020)."
    )
    converse_cmd.add_argument("--mode", choices=("demo", "real"), default="demo")
    converse_cmd.add_argument(
        "--variants", nargs="+", choices=("chain", "agent"), default=["chain", "agent"]
    )
    converse_cmd.add_argument(
        "--baseline", action="store_true", help="Repite la evaluación en el modo de guiones."
    )
    converse_cmd.add_argument(
        "--simulate",
        action="store_true",
        help="En real, DeepSeek escribe los turnos de los visitantes simulados.",
    )
    converse_cmd.add_argument("--repeats", type=int, default=10, help="Hilos por mensaje.")
    converse_cmd.add_argument(
        "--baseline-delivery",
        action="store_true",
        help="Spec 021: repite la evaluación con la entrega completa (spec 020) para comparar.",
    )
    converse_cmd.add_argument(
        "--json-out", default=None, help="Informe JSON (por defecto en real)."
    )
    converse_cmd.add_argument(
        "--focus",
        action="store_true",
        help="Spec 035: corre focus.jsonl y escribe docs/evaluacion_enfoque.{md,json}.",
    )
    converse_cmd.add_argument(
        "--style",
        action="store_true",
        help="Spec 036: corre caleno.jsonl y escribe docs/evaluacion_caleno.{md,json}.",
    )
    jev_cmd = sub.add_parser(
        "jev", help="Gatekeeper System One Jev (spec 022): chequeo, validación y comparación."
    )
    jev_action = jev_cmd.add_mutually_exclusive_group(required=True)
    jev_action.add_argument("--check", action="store_true", help="Verifica clave, red y versión.")
    jev_action.add_argument(
        "--validate", action="store_true", help="Validación en español (24 consultas nuevas)."
    )
    jev_action.add_argument(
        "--compare", action="store_true", help="Compara el enrutador sin y con gatekeeper."
    )
    jev_cmd.add_argument("--json", action="store_true", help="Imprime el resultado en JSON.")
    jev_cmd.add_argument("--cases", default=None, help="JSONL de validación alternativo.")
    jev_cmd.add_argument("--run-id", default="")
    return parser


def _jev(args: argparse.Namespace, root: Path) -> int:
    """``agent jev``: 0 si todo va bien, 1 si no cumple el mínimo, 2 sin clave o configuración."""
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from dataclasses import replace

    from .jev import API_KEY_ENV, TypeSafeJevGate, health_check, read_api_key

    try:
        config = replace(load_agent_config(project_root=root).jev, enabled=True)
    except AgentConfigError as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 2
    if args.check:
        result = health_check(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 2
    api_key = read_api_key()
    if api_key is None:
        print(
            f"Falta {API_KEY_ENV}: añádela a .env (https://console.typesafe.ai) y repite.",
            file=sys.stderr,
        )
        return 2
    gate = TypeSafeJevGate(config, api_key)
    if args.validate:
        from .jev_eval import MIN_ACCURACY, load_validation_cases, render_validation, validate

        report = validate(gate, load_validation_cases(args.cases))
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(render_validation(report, config))
        return 0 if report.accuracy >= MIN_ACCURACY else 1
    from .jev_eval import run_compare

    return run_compare(gate, config, root=root, run_id=args.run_id, as_json=args.json)


def _care(args: argparse.Namespace) -> int:
    """``agent care``: 0 si cumple las metas, 1 si falla un criterio, 2 por configuración."""
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .care_eval import CASES_FILE, REPORT_JSON, render_markdown, run_care, write_reports

    try:
        report = run_care(
            mode=args.mode,
            variants=tuple(args.variants),
            cases_path=Path(args.cases) if args.cases else CASES_FILE,
            baseline=args.baseline,
            conversation_mode=args.conversation_mode,
        )
    except Exception as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 2
    for variant, row in report["summary"].items():
        print(f"{variant}: {row['passed']}/{row['cases']} casos cumplen")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.mode == "real":
        write_reports(report)
        print(f"informe: {REPORT_JSON} y su Markdown")
    else:
        print(render_markdown(report))
    if not report["meets_strict"]:
        return 1
    return 0 if report["meets_targets"] else 1


def _converse(args: argparse.Namespace) -> int:
    """``agent converse``: 0 si cumple las metas duras, 1 si falla alguna, 2 por configuración."""
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .converse_eval import REPORT_JSON, render_markdown, run_converse, write_reports

    if args.repeats < 1:
        print("error de configuración: --repeats debe ser >= 1", file=sys.stderr)
        return 2
    if getattr(args, "focus", False):
        return _converse_focus(args)
    if getattr(args, "style", False):
        return _converse_style(args)
    try:
        report = run_converse(
            mode=args.mode,
            variants=tuple(args.variants),
            baseline=args.baseline,
            simulate=args.simulate,
            repeats=args.repeats,
            baseline_delivery=args.baseline_delivery,
        )
    except Exception as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 2
    for variant, row in report["summary"].items():
        hard = row["guided"]["hard"]
        skip = row["guided"].get("informative") or []
        failed = [key for key, ok in hard.items() if not ok and key not in skip]
        status = "cumple las metas duras" if not failed else f"falla {', '.join(failed)}"
        print(f"{variant}: {status}; juez {row['guided']['judge']}")
    if args.json_out:
        write_reports(report, Path(args.json_out))
        print(f"informe: {args.json_out} y {REPORT_JSON.with_suffix('.md').name}")
    elif args.mode == "real":
        write_reports(report)
        print(f"informe: {REPORT_JSON} y su Markdown")
    else:
        print(render_markdown(report))
    return 0 if report["meets_hard"] else 1


def _converse_style(args: argparse.Namespace) -> int:
    """``agent converse --style`` (spec 036): 0 si cumple, 1 si no, 2 por error."""
    from .converse_eval import (
        STYLE_JSON,
        render_style_markdown,
        run_style,
        write_style_reports,
    )

    try:
        report = run_style(mode=args.mode, variants=tuple(args.variants))
    except Exception as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 2
    for variant, row in report["summary"].items():
        flags = {k: v for k, v in row["flags"].items() if v}
        status = "0 turnos marcados" if not flags else f"marcados {flags}"
        print(
            f"{variant}: uso {row['usage_rate']:.0%}; {status}; juez {row['judge']} "
            f"({row['judged_by']})"
        )
    if args.json_out:
        write_style_reports(report, Path(args.json_out))
        print(f"informe: {args.json_out}")
    elif args.mode == "real":
        write_style_reports(report)
        print(f"informe: {STYLE_JSON} y su Markdown")
    else:
        print(render_style_markdown(report))
    return 0 if report["meets"] else 1


def _converse_focus(args: argparse.Namespace) -> int:
    """``agent converse --focus`` (spec 035): 0 sin turnos marcados, 1 si hay, 2 por error."""
    from .converse_eval import (
        FOCUS_JSON,
        render_focus_markdown,
        run_focus,
        write_focus_reports,
    )

    try:
        report = run_focus(mode=args.mode, variants=tuple(args.variants))
    except Exception as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 2
    for variant, row in report["summary"].items():
        flags = {k: v for k, v in row["flags"].items() if v}
        status = "0 turnos marcados" if not flags else f"marcados {flags}"
        print(f"{variant}: {status}; empatía {row['empathy']} ({row['judged_by']})")
    if args.json_out:
        write_focus_reports(report, Path(args.json_out))
        print(f"informe: {args.json_out}")
    elif args.mode == "real":
        write_focus_reports(report)
        print(f"informe: {FOCUS_JSON} y su Markdown")
    else:
        print(render_focus_markdown(report))
    return 0 if report["meets"] else 1


def _conduct(args: argparse.Namespace) -> int:
    """``agent conduct``: 0 si cumple las metas, 1 si no, 2 por error de configuración."""
    with contextlib.suppress(AttributeError, ValueError):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from .conduct import CASES_FILE, REPORT_JSON, render_markdown, run_conduct, write_reports

    try:
        report = run_conduct(
            mode=args.mode,
            variants=tuple(args.variants),
            cases_path=Path(args.cases) if args.cases else CASES_FILE,
        )
    except Exception as exc:
        print(f"error de configuración: {exc}", file=sys.stderr)
        return 2
    for variant, row in report["summary"].items():
        print(
            f"{variant}: {row['passed']}/{row['cases']} cumplen "
            f"({row['compliance']:.0%}) · fugas {row['leaks']}"
        )
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif args.mode == "real":
        write_reports(report)
        print(f"informe: {REPORT_JSON} y su Markdown")
    if args.mode != "real" and not args.json_out:
        print(render_markdown(report))
    return 0 if report["meets_targets"] else 1


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
    with StructuredStore(config.structured_path, gold_dir=root / GOLD_DIR) as store:
        facts_csv, entities_json = store.export_tables(config.structured_path)
    print(f"exportada como {facts_csv.name} y {entities_json.name} (misma tabla, solo lectura)")
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
        payload["meta"] = {
            "run_id": args.run_id or f"variants-{args.mode}-{stamp}",
            "mode": args.mode,
            "judge": bool(args.judge),
            "created_at": stamp,
        }
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
    from .adversarial import adversarial_enabled, adversarial_retriever
    from .demo import DEMO_EMBEDDER_KIND, DEMO_INDEX

    if adversarial_enabled():
        # Corpus de prueba del blindaje (spec 015), en modo demo o real.
        return adversarial_retriever("real" if mode == "real" else "demo")

    config = load_retrieval_config(project_root=root)
    profile = EmbeddingProfile.from_config(config.embedding)
    index_dir = DEMO_INDEX if mode == "demo" else config.index_dir
    notes: list[str] = []
    try:
        index = load_index(index_dir, profile)
    except (IndexUnavailableError, IndexInvalidError) as exc:
        index = None
        notes.append(f"Índice no utilizable: {exc}")
    from ..rag.vectorstore import attach_vector_store

    gold = root / GOLD_DIR
    units = load_gold_units(gold)
    vector_store, note = attach_vector_store(index, config.source, units, demo=mode == "demo")
    if note:
        notes.append(note)
    return HybridRetriever(
        units,
        index=index,
        embedder=build_embedder(
            profile, kind=DEMO_EMBEDDER_KIND if mode == "demo" else "fastembed"
        ),
        entity_index=load_entity_index(gold),
        config=config,
        notes=tuple(notes),
        vector_store=vector_store,
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


def _shield(args: argparse.Namespace, root: Path) -> int:
    """Batería de inyección indirecta; 0 todo pasa, 1 hay fallos, 2 sin configuración/clave."""
    from ..tasks import _configure_output
    from .shield import (
        REPORT_MD,
        ShieldError,
        default_json_path,
        run_shield,
        write_report_section,
    )

    _configure_output()
    neutralize = not args.no_neutralize
    command = "uv run python -m proyecto_modelos_lenguaje.agent " + " ".join(sys.argv[1:])

    def show(result) -> None:
        mark = "ok  " if result.passed else "FALLA"
        print(
            f"{mark} {result.case_id} {result.attack:<20} {result.variant:<5} rep {result.repeat} "
            f"· {result.status} · marcado={result.flagged} · neutralizadas={result.neutralized}"
        )

    try:
        kwargs = {"cases_path": Path(args.cases)} if args.cases else {}
        report = run_shield(
            mode=args.mode,
            variants=args.variants,
            repeat=args.repeat,
            neutralize=neutralize,
            run_id=args.run_id,
            config=load_agent_config(project_root=root),
            command=command.strip(),
            on_result=show,
            **kwargs,
        )
    except (ShieldError, AgentConfigError) as exc:
        print(f"no se puede evaluar: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # p. ej., configuración del proveedor inválida
        print(f"no se puede evaluar: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    results = report["results"]
    if results and all(r["status"] == "error" for r in results):
        print("el proveedor no respondió en ningún caso; no se escribe el informe", file=sys.stderr)
        return 2
    json_out = args.json_out or (default_json_path(neutralize) if args.mode == "real" else None)
    md_out = args.report or (REPORT_MD if args.mode == "real" else None)
    if json_out:
        path = root / json_out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"informe JSON: {path}")
    if md_out:
        write_report_section(root / md_out, report)
        print(f"informe Markdown: {root / md_out}")
    for variant, stats in report["summary"]["by_variant"].items():
        print(
            f"{variant}: {stats['passed']}/{stats['cases']} pasan · obedeció {stats['obeyed']} · "
            f"filtró {stats['leaked']} · escrituras {stats['write_attempts']} · "
            f"útil {stats['useful_rate']:.0%}"
        )
    return 0 if all(r["passed"] for r in results) else 1


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
    if args.command in {"planning", "planning-eval", "profiles-eval"}:
        from . import cli_m3

        return cli_m3.run_planning(args, root)
    if getattr(args, "planning_activation", False):
        from . import cli_m3

        return cli_m3.run_planning_activation(args, root)
    if args.command in {"tools", "memory"} or getattr(args, "tools", False):
        from . import cli_m3

        if args.command == "tools":
            return cli_m3.run_tools(args, root)
        if args.command == "memory":
            return cli_m3.run_memory(args, root)
        return cli_m3.run_evaluate_tools(args, root)
    if args.command == "shield" and args.channel:
        from . import cli_m3

        return cli_m3.run_shield_channel(args, root)
    if args.command == "evaluate":
        return _evaluate(args, root)
    if args.command == "shield":
        return _shield(args, root)
    if args.command == "conduct":
        return _conduct(args)
    if args.command == "care":
        return _care(args)
    if args.command == "converse":
        return _converse(args)
    if args.command == "jev":
        return _jev(args, root)
    return _chat(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
