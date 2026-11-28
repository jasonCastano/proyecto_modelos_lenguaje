"""Comandos del Módulo 3 del CLI del agente (spec 024, contracts/cli.md).

``agent tools``, ``agent evaluate --tools``, ``agent shield --channel`` y ``agent memory list``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from .config import load_agent_config


def _configure() -> None:
    from ..tasks import _configure_output

    _configure_output()


def _command() -> str:
    return "uv run python -m proyecto_modelos_lenguaje.agent " + " ".join(sys.argv[1:])


# --- agent tools ------------------------------------------------------------------------------


def render_tools_doc() -> str:
    """``docs/herramientas.md`` generado desde el catálogo (fuente única)."""
    from .catalog import catalog

    lines = [
        "# Catálogo de herramientas de Valer-IA Caña",
        "",
        "> Generado con `uv run python -m proyecto_modelos_lenguaje.agent tools --markdown "
        "docs/herramientas.md` desde `src/proyecto_modelos_lenguaje/agent/catalog.py` "
        "(spec 024, ítem 1.1). No editar a mano.",
        "",
        "**26 herramientas: 20 de atención (1–20) + 6 de planificación (21–26).** Regla de oro: "
        "**lectura automática, escritura con aprobación**. Las 15 de lectura marcadas «MCP» "
        "también se exponen por el servidor MCP `valeria-tools` (modo degradado); la "
        "planificación solo existe en el backend (spec 028). Las de escritura piden la "
        "confirmación de la persona, "
        "dicha con sus palabras, en la web y en WhatsApp. Las herramientas 21–26 usan datos "
        "**sintéticos** de demostración y se activan cuando la conversación plantea un problema "
        "de producción (ruta `planning`, para cualquier persona).",
        "",
        "| # | Herramienta | Tipo | Rutas | Fuente | Descripción |",
        "|---:|---|---|---|---|---|",
    ]
    specs = catalog()
    for spec in specs:
        if spec.requires_approval:
            kind = "escritura (HITL)"
        else:
            kind = "lectura (MCP)" if spec.mcp else "lectura (solo backend)"
        lines.append(
            f"| {spec.number} | `{spec.name}` | {kind} | {', '.join(sorted(spec.routes))} | "
            f"{spec.data_source} | {spec.description} |"
        )
    lines += ["", "## Esquemas de argumentos", ""]
    for spec in specs:
        schema = spec.args_schema.model_json_schema()
        lines += [f"### {spec.number}. `{spec.name}`", ""]
        properties = schema.get("properties", {})
        if not properties:
            lines += ["Sin argumentos.", ""]
            continue
        required = set(schema.get("required", []))
        lines += ["| Campo | Tipo | Obligatorio | Descripción |", "|---|---|:-:|---|"]
        for name, prop in properties.items():
            kind = str(prop.get("type") or "")
            if not kind and "anyOf" in prop:
                kind = " o ".join(str(option.get("type", "?")) for option in prop["anyOf"])
            if "enum" in prop:
                kind = " · ".join(str(value) for value in prop["enum"])
            description = str(prop.get("description", "")).replace("|", "/")
            mandatory = "sí" if name in required else "no"
            lines.append(f"| `{name}` | {kind} | {mandatory} | {description} |")
        lines.append("")
    return "\n".join(lines)


def run_tools(args: argparse.Namespace, root: Path) -> int:
    from .catalog import catalog, to_json_schema

    _configure()
    if args.json:
        print(json.dumps(to_json_schema(), ensure_ascii=False, indent=2))
    else:
        for spec in catalog():
            flag = " (requiere aprobación)" if spec.requires_approval else ""
            print(f"{spec.number:>2}. {spec.name} [{spec.kind}]{flag}: {spec.description}")
    if args.markdown:
        path = root / args.markdown
        path.write_text(render_tools_doc(), encoding="utf-8")
        print(f"Escribí {path}")
    return 0


# --- agent evaluate --tools ----------------------------------------------------------------------


def cli_service(root: Path, state_dir: Path) -> Any:
    from .__main__ import _cli_retriever
    from .memory import build_checkpointer, build_store
    from .service import ChatService, build_deps

    config = load_agent_config(project_root=root)
    return ChatService(
        config,
        build_checkpointer(state_dir),
        lambda mode: build_deps(mode, config, _cli_retriever(mode, root)),
        store=build_store(state_dir),
    )


def run_evaluate_tools(args: argparse.Namespace, root: Path) -> int:
    """0 cumple (≥ 90 % y 0 búsquedas en triviales), 1 no cumple."""
    from .channel_eval import (
        evaluate_tools,
        load_tool_cases,
        render_tools_markdown,
        report_payload,
        summarize_tools,
    )

    _configure()
    mode = "demo" if args.fake else args.mode
    service = cli_service(root, Path(tempfile.mkdtemp(prefix="pml-tools-eval-")))

    # Spec 027: la evaluación corre por la «web», donde el planificador es de libre elección.

    def send(question: str, profile: str | None = None) -> Any:
        return service.send(
            question, user_id="eval-tools", variant="agent", mode=mode, profile=profile
        )

    results = evaluate_tools(send, load_tool_cases())
    summary = summarize_tools(results)
    report = report_payload("tools", mode, _command(), results, summary)
    for result in results:
        mark = "ok  " if result.hit else "FALLA"
        print(f"{mark} {result.case_id} esperaba {result.expected_tool} · llamó {result.called}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if mode == "real" or args.json_out:
        default = root / "docs" / "evaluacion_herramientas.json"
        json_out = Path(args.json_out) if args.json_out else default
        json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        json_out.with_suffix(".md").write_text(render_tools_markdown(report), encoding="utf-8")
        print(f"Escribí {json_out} y {json_out.with_suffix('.md')}")
    return 0 if summary["meets_target"] else 1


# --- spec 028: activación del planificador por contexto -------------------------------------------


def run_planning_activation(args: argparse.Namespace, root: Path) -> int:
    """0 cumple SC-007 (≥ 14/15 en cada lado), 1 no cumple."""
    from .planning_activation import evaluate, render_markdown, summarize

    results = evaluate()
    summary = summarize(results)
    for result in results:
        mark = "ok  " if result.hit else "FALLA"
        print(f"{mark} {result.case_id} esperado={result.expected} activó={result.activated}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if getattr(args, "markdown", False):
        target = root / "docs" / "evaluacion_activacion_planificador.md"
        target.write_text(render_markdown(results, summary), encoding="utf-8")
        print(f"Escribí {target}")
    return 0 if summary["meets_target"] else 1


# --- spec 025: agent planning / planning-eval / profiles-eval -----------------------------------


def run_planning(args: argparse.Namespace, root: Path) -> int:
    """0 cumple la meta, 1 no la cumple, 2 error de datos o configuración."""
    from . import planning_eval as pe
    from .planning import PlanningError, Scenario, optimize

    _configure()
    if args.command == "planning":
        try:
            plan = optimize(Scenario.model_validate(json.loads(args.scenario)))
        except (PlanningError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(plan.plan_card)
        return 0
    docs = root / "docs"
    if args.command == "planning-eval":
        cases = pe.load_cases(pe.PLANNING_CASES)
        if args.mode == "direct":
            results = pe.evaluate_planning_direct(cases)
        else:
            service = cli_service(root, Path(tempfile.mkdtemp(prefix="pml-planning-")))

            def send(question: str) -> Any:
                return service.send(
                    question,
                    user_id="eval-planner",
                    variant="agent",
                    mode=args.mode,
                    profile="planificador",
                )

            results = pe.evaluate_planning_agent(send, cases)
        summary = pe.summarize_planning(results, "direct" if args.mode == "direct" else "agent")
        report = pe.build_report("planning", args.mode, _command(), results, summary)
        report["mode"] = "direct" if args.mode == "direct" else args.mode
        markdown = pe.render_planning_markdown(
            {**report, "mode": "direct" if args.mode == "direct" else "agente"}
        )
        name = "evaluacion_planificacion" + ("_directa" if args.mode == "direct" else "")
        target = docs / f"{name}.json"
    else:
        cases = pe.load_cases(pe.PROFILE_CASES)
        service = cli_service(root, Path(tempfile.mkdtemp(prefix="pml-profiles-")))

        def send_profile(question: str, profile: str | None = None) -> Any:
            return service.send(
                question, user_id="eval-profiles", variant="agent", mode=args.mode,
                profile=profile,
            )  # fmt: skip

        results = pe.evaluate_profiles(send_profile, cases)
        summary = pe.summarize_profiles(results)
        report = pe.build_report("profiles", args.mode, _command(), results, summary)
        markdown = pe.render_profiles_markdown(report)
        target = docs / "evaluacion_perfiles.json"
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.write_docs:
        pe.write_report(report, target, markdown)
        print(f"Escribí {target} y {target.with_suffix('.md')}")
    return 0 if report["summary"]["meets_target"] else 1


# --- agent shield --channel ----------------------------------------------------------------------


def run_shield_channel(args: argparse.Namespace, root: Path) -> int:
    """0 sin fallos (SC-009), 1 con fallos."""
    from ..channels.bridge import InboundMessage
    from .adversarial import ADVERSARIAL_ENV, ADVERSARIAL_VALUE
    from .channel_eval import (
        DIRECT_ATTACKS,
        build_channel_bridge,
        indirect_attacks,
        render_shield_markdown,
        report_payload,
        run_channel_attacks,
        summarize_attacks,
    )

    _configure()
    phone = "+570000000999"
    previous = os.environ.get(ADVERSARIAL_ENV)

    def run(adversarial: bool, attacks: Any, kind: str, *, voice: bool = False) -> list[Any]:
        os.environ[ADVERSARIAL_ENV] = ADVERSARIAL_VALUE if adversarial else ""
        bridge = build_channel_bridge(args.mode)

        def handle(message_id: str, text: str) -> Any:
            if voice:  # spec 028: el ataque llega como nota de voz ya transcrita por el gateway
                message = InboundMessage(
                    "whatsapp", message_id, phone, "audio", text, input_mode="voice"
                )
                return bridge.handle(message)
            return bridge.handle(InboundMessage("whatsapp", message_id, phone, "text", text))

        return run_channel_attacks(handle, attacks, kind=kind)

    try:
        results = (
            run(False, DIRECT_ATTACKS, "direct")
            + run(False, DIRECT_ATTACKS, "direct-voice", voice=True)
            + run(True, indirect_attacks(), "indirect")
        )
    finally:
        if previous is None:
            os.environ.pop(ADVERSARIAL_ENV, None)
        else:
            os.environ[ADVERSARIAL_ENV] = previous
    summary = summarize_attacks(results)
    report = report_payload("shield-canal", args.mode, _command(), results, summary)
    for result in results:
        mark = "ok  " if result.passed else "FALLA"
        print(f"{mark} {result.kind} {result.case_id} {result.attack} · {result.status}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.mode == "real" or args.json_out:
        default = root / "docs" / "evaluacion_blindaje_canal.json"
        json_out = Path(args.json_out) if args.json_out else default
        json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        markdown = Path(args.report) if args.report else json_out.with_suffix(".md")
        markdown.write_text(render_shield_markdown(report), encoding="utf-8")
        print(f"Escribí {json_out} y {markdown}")
    return 0 if summary["meets_target"] else 1


# --- agent memory list ---------------------------------------------------------------------------


def list_memory(store: Any, user_id: str) -> list[dict[str, Any]]:
    """Recuerdos de un usuario en ``profile`` y ``preferences``: qué, dónde y cuándo (FR-025)."""
    rows: list[dict[str, Any]] = []
    for space in ("profile", "preferences"):
        namespace = ("users", user_id, space)
        for item in store.search(namespace, limit=100):
            value = (
                item.value.get("value", item.value) if isinstance(item.value, dict) else item.value
            )
            rows.append(
                {
                    "namespace": "/".join(namespace),
                    "key": item.key,
                    "value": value,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
            )
    return rows


def run_memory(args: argparse.Namespace, root: Path) -> int:
    from .config import resolve_state_dir
    from .memory import build_store
    from .service import validate_user_id

    _configure()
    config = load_agent_config(project_root=root)
    user_id = validate_user_id(args.user)
    store = build_store(resolve_state_dir(config.state_env_var, project_root=root))
    rows = list_memory(store, user_id)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif not rows:
        print(f"Sin recuerdos guardados para {user_id}.")
    else:
        for row in rows:
            print(f"{row['namespace']} · {row['key']} = {row['value']} · {row['updated_at']}")
    return 0
