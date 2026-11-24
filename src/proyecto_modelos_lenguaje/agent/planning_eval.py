"""Evaluaciones de la spec 025: planificación (SC-001, SC-002, SC-004) y perfiles (SC-003).

- ``planning-eval --mode direct``: el optimizador frente al óptimo de referencia de la batería, sin
  LLM (SC-001).
- ``planning-eval --mode real``: el agente con DeepSeek y el perfil planificador; secuencia de
  herramientas, etiqueta sintética, frase de decisión humana y latencia (SC-002, SC-004).
- ``profiles-eval``: perfil detectado o aplicado y herramientas usadas dentro del perfil (SC-003).

Las baterías se fijaron antes de evaluar (principio V). Los informes van a ``docs/``.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from .planning import DECISION_PHRASE, SYNTHETIC_LABEL, Scenario, load_plant, optimize

PLANNING_CASES = PROJECT_ROOT / "tests" / "fixtures" / "agent" / "planning_scenarios.jsonl"
PROFILE_CASES = PROJECT_ROOT / "tests" / "fixtures" / "agent" / "profile_routing.jsonl"
MARGIN_TOLERANCE = 0.99
LATENCY_TARGET_MS = 20_000
SEQUENCE_TARGET = 10
PROFILE_TARGET = 0.9
STATE_TOOLS = frozenset({"get_plant_state", "get_commitments"})
PLAN_TOOLS = frozenset({"optimize_production_plan", "simulate_production_scenario"})


def load_cases(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not rows:
        raise ValueError(f"Sin casos en {path}")
    return rows


def _p95(values: Sequence[int]) -> int:
    ordered = sorted(values) or [0]
    return ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]


def _stamp(kind: str, mode: str) -> tuple[str, str]:
    now = datetime.now(UTC)
    return f"{kind}-{mode}-{now.strftime('%Y%m%dT%H%M%SZ')}", now.isoformat(timespec="seconds")


# --------------------------------------------------------------------------- planificación


@dataclass
class PlanningCaseResult:
    case_id: str
    feasible: bool
    status: str | None = None
    margin: float | None = None
    reference_margin: float | None = None
    ratio: float | None = None
    violations: int = 0
    detected_infeasible: bool | None = None
    tools: list[str] = field(default_factory=list)
    sequence_ok: bool | None = None
    labeled: bool | None = None
    route: str | None = None
    latency_ms: int = 0
    error: str | None = None


def _violations(plan: Any, data: Any) -> int:
    """Restricciones duras incumplidas por un plan óptimo (capacidad o compromiso)."""
    if plan.status != "optimal":
        return 0
    r = plan.resolved
    count = 0
    count += plan.mix["x_s"] + plan.mix["x_e"] > min(r["cane"], r["mill_cap"]) + 1e-6
    count += plan.products["ethanol"] > r["distillery_cap"] + 1e-6
    count += plan.mix["v"] > r["boiler_cap"] + 1e-6
    for product in ("sugar", "ethanol", "power"):
        count += plan.products[product] + 1e-6 < data.required(product)
    return int(count)


def evaluate_planning_direct(cases: Sequence[dict[str, Any]]) -> list[PlanningCaseResult]:
    data = load_plant()
    results: list[PlanningCaseResult] = []
    for case in cases:
        started = time.perf_counter()
        plan = optimize(Scenario(**case["scenario"]), data)
        reference = case.get("reference_margin")
        results.append(
            PlanningCaseResult(
                case["id"],
                bool(case["feasible"]),
                status=plan.status,
                margin=plan.margin,
                reference_margin=reference,
                ratio=(plan.margin / reference) if reference else None,
                violations=_violations(plan, data),
                detected_infeasible=plan.status == "infeasible_relaxed",
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
        )
    return results


def evaluate_planning_agent(
    send: Callable[[str], Any], cases: Sequence[dict[str, Any]]
) -> list[PlanningCaseResult]:
    """``send(question)`` envía la pregunta al agente con el perfil planificador (hilo nuevo)."""
    results: list[PlanningCaseResult] = []
    for case in cases:
        started = time.perf_counter()
        try:
            outcome = send(case["question"])
        except Exception as exc:
            results.append(
                PlanningCaseResult(case["id"], bool(case["feasible"]), error=type(exc).__name__)
            )
            continue
        turn = outcome.turn.model_dump(mode="json")
        tools = [str(item.get("name")) for item in turn.get("tools") or []]
        answer = str(turn.get("answer") or "")
        results.append(
            PlanningCaseResult(
                case["id"],
                bool(case["feasible"]),
                tools=tools,
                sequence_ok=bool(STATE_TOOLS & set(tools)) and bool(PLAN_TOOLS & set(tools)),
                labeled=SYNTHETIC_LABEL.lower() in answer.lower()
                and DECISION_PHRASE.lower().rstrip(".") in answer.lower(),
                route=(turn.get("route") or {}).get("route"),
                latency_ms=round((time.perf_counter() - started) * 1000),
            )
        )
    return results


def summarize_planning(results: Sequence[PlanningCaseResult], mode: str) -> dict[str, Any]:
    feasible = [r for r in results if r.feasible]
    infeasible = [r for r in results if not r.feasible]
    latencies = [r.latency_ms for r in results]
    summary: dict[str, Any] = {
        "cases": len(results),
        "feasible": len(feasible),
        "infeasible": len(infeasible),
        "errors": sum(1 for r in results if r.error),
        "latency_p50_ms": int(statistics.median(latencies)) if latencies else 0,
        "latency_p95_ms": _p95(latencies),
    }
    if mode == "direct":
        within = sum(1 for r in feasible if r.ratio is not None and r.ratio >= MARGIN_TOLERANCE)
        violations = sum(r.violations for r in results)
        detected = sum(1 for r in infeasible if r.detected_infeasible)
        summary.update(
            {
                "within_tolerance": within,
                "min_ratio": round(min((r.ratio or 0) for r in feasible), 6) if feasible else None,
                "violations": violations,
                "infeasible_detected": detected,
                "meets_target": within == len(feasible)
                and violations == 0
                and detected == len(infeasible),
            }
        )
    else:
        sequence = sum(1 for r in results if r.sequence_ok)
        labeled = sum(1 for r in results if r.labeled)
        planning_route = sum(1 for r in results if r.route == "planning")
        summary.update(
            {
                "planning_route": planning_route,
                "sequence_ok": sequence,
                "labeled": labeled,
                "meets_target": sequence >= SEQUENCE_TARGET
                and labeled == len(results)
                and summary["latency_p95_ms"] <= LATENCY_TARGET_MS,
            }
        )
    return summary


def render_planning_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Evaluación del agente de planificación industrial (spec 025, idea 7.4)",
        "",
        f"**Ejecución**: `{report['run_id']}` · **Modo**: {report['mode']} · "
        f"**Fecha**: {report['created_at']} · **Comando**: `{report['command']}`",
        "",
        "> Datos **sintéticos** de demostración (`data/synthetic/planificacion/v1`). La batería "
        "(`tests/fixtures/agent/planning_scenarios.jsonl`) se fijó antes de evaluar, con el "
        "óptimo de referencia calculado por malla (`planning_reference.py`).",
        "",
    ]
    if report["mode"] == "direct":
        lines += [
            f"- **SC-001**: {s['within_tolerance']}/{s['feasible']} escenarios factibles con "
            "margen "
            f"≥ 99 % del óptimo de referencia (mínimo {s['min_ratio']}); violaciones de "
            f"restricciones duras: **{s['violations']}**; sin solución detectados: "
            f"**{s['infeasible_detected']}/{s['infeasible']}**.",
            f"- Tiempo del optimizador p50 / p95: {s['latency_p50_ms']} / {s['latency_p95_ms']} "
            "ms.",
        ]
    else:
        lines += [
            f"- Ruta `planning`: {s['planning_route']}/{s['cases']}.",
            f"- **SC-002**: secuencia estado/compromisos → optimizar en **{s['sequence_ok']}/"
            f"{s['cases']}** (meta ≥ {SEQUENCE_TARGET}); etiqueta sintética y decisión humana en "
            f"**{s['labeled']}/{s['cases']}** (meta {s['cases']}).",
            f"- **SC-004**: latencia p50 / p95 {s['latency_p50_ms']} / **{s['latency_p95_ms']}** "
            "ms "
            f"(meta p95 ≤ {LATENCY_TARGET_MS} ms); errores: {s['errors']}.",
        ]
    lines += ["", f"Veredicto: {'✅ cumple' if s['meets_target'] else '❌ no cumple'}.", ""]
    lines += ["| Caso | Factible | Estado / ruta | Detalle |", "|---|:-:|---|---|"]
    for row in report["results"]:
        if report["mode"] == "direct":
            detail = (
                f"margen/ref {row['ratio']:.5f}" if row.get("ratio") else "faltantes reportados"
            )
            state = row.get("status")
        else:
            detail = ", ".join(row.get("tools") or []) or row.get("error") or "—"
            state = row.get("route")
        lines.append(
            f"| {row['case_id']} | {'sí' if row['feasible'] else 'no'} | {state} | {detail} |"
        )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- perfiles


@dataclass
class ProfileCaseResult:
    case_id: str
    expected_profile: str
    profile: str | None
    profile_ok: bool
    tools: list[str]
    tools_ok: bool
    latency_ms: int
    error: str | None = None


def evaluate_profiles(
    send: Callable[..., Any], cases: Sequence[dict[str, Any]]
) -> list[ProfileCaseResult]:
    """``send(question, profile=None)``; el perfil explícito se usa si el caso lo trae."""
    from .profiles import get_profile

    results: list[ProfileCaseResult] = []
    for case in cases:
        started = time.perf_counter()
        try:
            outcome = send(case["question"], profile=case.get("profile"))
        except Exception as exc:
            results.append(
                ProfileCaseResult(
                    case["id"], case["expected_profile"], None, False, [], False, 0,
                    type(exc).__name__,
                )
            )  # fmt: skip
            continue
        turn = outcome.turn.model_dump(mode="json")
        profile = str(turn.get("profile") or "visitante")
        tools = [str(item.get("name")) for item in turn.get("tools") or []]
        allowed = set(get_profile(profile).tools) | {
            "save_profile",
            "save_preference",
            "forget_memory",
            "export_conversation",
            "request_human_contact",
            "save_production_proposal",
        }
        results.append(
            ProfileCaseResult(
                case["id"],
                case["expected_profile"],
                profile,
                profile == case["expected_profile"],
                tools,
                set(tools) <= allowed,
                round((time.perf_counter() - started) * 1000),
            )
        )
    return results


def summarize_profiles(results: Sequence[ProfileCaseResult]) -> dict[str, Any]:
    total = len(results) or 1
    profile_ok = sum(r.profile_ok for r in results)
    tools_ok = sum(r.tools_ok for r in results)
    return {
        "cases": len(results),
        "profile_ok": profile_ok,
        "profile_accuracy": round(profile_ok / total, 4),
        "tools_ok": tools_ok,
        "tools_accuracy": round(tools_ok / total, 4),
        "errors": sum(1 for r in results if r.error),
        "meets_target": profile_ok / total >= PROFILE_TARGET and tools_ok == len(results),
    }


def render_profiles_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Evaluación de los perfiles de la plataforma (spec 025, SC-003)",
        "",
        f"**Ejecución**: `{report['run_id']}` · **Modo**: {report['mode']} · "
        f"**Fecha**: {report['created_at']} · **Comando**: `{report['command']}`",
        "",
        f"- Perfil correcto (detectado o aplicado): **{s['profile_ok']}/{s['cases']}** "
        f"({s['profile_accuracy']:.0%}; meta ≥ 90 %).",
        f"- Herramientas usadas dentro del perfil: **{s['tools_ok']}/{s['cases']}** (meta 100 %).",
        f"- Errores: {s['errors']}. "
        f"Veredicto: {'✅ cumple' if s['meets_target'] else '❌ no cumple'}.",
        "",
        "| Caso | Esperado | Obtenido | Herramientas |",
        "|---|---|---|---|",
    ]
    for row in report["results"]:
        mark = "✅" if row["profile_ok"] and row["tools_ok"] else "❌"
        lines.append(
            f"| {row['case_id']} {mark} | {row['expected_profile']} | {row['profile']} | "
            f"{', '.join(row['tools']) or row.get('error') or '—'} |"
        )
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- informes


def build_report(
    kind: str, mode: str, command: str, results: Sequence[Any], summary: dict[str, Any]
) -> dict[str, Any]:
    run_id, created = _stamp(kind, mode)
    return {
        "run_id": run_id,
        "mode": mode,
        "created_at": created,
        "command": command,
        "summary": summary,
        "results": [asdict(result) for result in results],
    }


def write_report(report: dict[str, Any], json_path: Path, markdown: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json_path.with_suffix(".md").write_text(markdown, encoding="utf-8")


def enable_planner_for_eval() -> None:
    """La evaluación corre por la «web» del proceso: habilita el planificador solo aquí."""
    os.environ.setdefault("MANUELITA_PLANNER_WEB", "1")
