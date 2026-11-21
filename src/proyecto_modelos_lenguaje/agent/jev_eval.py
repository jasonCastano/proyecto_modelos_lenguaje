"""Validación en español y comparación del gatekeeper Jev (spec 022, US4).

- ``validate``: 24 consultas nuevas (``tests/fixtures/jev/validation_es.jsonl``), distintas de las
  44 de evaluación; fija el umbral de ruta (research R5, R10; SC-009).
- ``compare``: enrutador sin y con gatekeeper sobre las 44 consultas del Módulo 2, más las baterías
  de atención y conversación con el gatekeeper (research R14).
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from .config import JevConfig
from .jev import ROUTES, GateOutcome, JevGate

VALIDATION_FILE = Path("tests") / "fixtures" / "jev" / "validation_es.jsonl"
THRESHOLDS = (0.6, 0.7, 0.75, 0.8, 0.9)
MIN_ACCURACY = 0.8  # SC-009
REPORT_JSON = Path("docs") / "evaluacion_jev.json"
REPORT_MD = Path("docs") / "evaluacion_jev.md"


@dataclass(frozen=True, slots=True)
class ValidationCase:
    query_id: str
    question: str
    history: tuple[str, ...]
    expected: str


def load_validation_cases(path: str | Path | None = None) -> list[ValidationCase]:
    source = Path(path) if path is not None else PROJECT_ROOT / VALIDATION_FILE
    cases: list[ValidationCase] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["expected_route"] not in ROUTES:
            raise ValueError(f"{row['query_id']}: ruta esperada desconocida")
        cases.append(
            ValidationCase(
                query_id=row["query_id"],
                question=row["question"],
                history=tuple(row.get("history") or ()),
                expected=row["expected_route"],
            )
        )
    return cases


@dataclass(slots=True)
class ValidationReport:
    total: int = 0
    answered: int = 0
    correct: int = 0
    failures: Counter[str] = field(default_factory=Counter)
    confusion: dict[str, Counter[str]] = field(default_factory=dict)
    by_threshold: list[dict[str, Any]] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: list[int] = field(default_factory=list)
    cost: float = 0.0
    model: str | None = None

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        latencies = sorted(self.latency_ms)
        return {
            "total": self.total,
            "answered": self.answered,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "meets_minimum": self.accuracy >= MIN_ACCURACY,
            "failures": dict(self.failures),
            "confusion": {k: dict(v) for k, v in self.confusion.items()},
            "by_threshold": self.by_threshold,
            "latency_ms_mean": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
            "latency_ms_p95": _p95(latencies),
            "cost": round(self.cost, 8),
            "model": self.model,
            "rows": self.rows,
        }


def _p95(values: Sequence[int | float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, round(0.95 * (len(ordered) - 1)))
    return float(ordered[index])


def validate(gate: JevGate, cases: Sequence[ValidationCase]) -> ValidationReport:
    """Envía cada consulta al gatekeeper y mide exactitud y cobertura por umbral."""
    report = ValidationReport(confusion={route: Counter() for route in ROUTES})
    outcomes: list[tuple[ValidationCase, GateOutcome]] = []
    for case in cases:
        outcome = gate.assess(case.question, case.history)
        outcomes.append((case, outcome))
        report.total += 1
        report.latency_ms.append(outcome.latency_ms)
        report.cost += outcome.cost or 0.0
        report.model = outcome.model or report.model
        decision = outcome.decision
        if outcome.status != "ok" or decision is None:
            report.failures[outcome.reason or "unknown"] += 1
            report.rows.append(
                {"query_id": case.query_id, "status": outcome.status, "reason": outcome.reason}
            )
            continue
        report.answered += 1
        report.confusion[case.expected][decision.route] += 1
        hit = decision.route == case.expected
        report.correct += hit
        report.rows.append(
            {
                "query_id": case.query_id,
                "expected": case.expected,
                "predicted": decision.route,
                "confidence": round(decision.confidence, 4),
                "alternative": decision.alternative,
                "correct": hit,
                "latency_ms": outcome.latency_ms,
            }
        )
    for threshold in THRESHOLDS:
        covered = [
            (case, outcome)
            for case, outcome in outcomes
            if outcome.decision is not None and outcome.decision.confidence >= threshold
        ]
        hits = sum(outcome.decision.route == case.expected for case, outcome in covered)  # type: ignore[union-attr]
        report.by_threshold.append(
            {
                "threshold": threshold,
                "coverage": round(len(covered) / len(cases), 4) if cases else 0.0,
                "accuracy": round(hits / len(covered), 4) if covered else None,
                "decided": len(covered),
            }
        )
    return report


def render_validation(report: ValidationReport, config: JevConfig) -> str:
    data = report.to_dict()
    lines = [
        f"Validación en español: {data['correct']}/{data['total']} rutas correctas "
        f"({data['accuracy']:.0%}); mínimo exigido {MIN_ACCURACY:.0%} (SC-009).",
        f"Modelo: {data['model'] or config.model} · latencia media {data['latency_ms_mean']} ms · "
        f"p95 {data['latency_ms_p95']} ms · costo {data['cost']:.6f} USD",
    ]
    if data["failures"]:
        lines.append(f"Fallos: {data['failures']}")
    lines.append("")
    lines.append("| Umbral | Cobertura | Exactitud cubierta | Decide Jev |")
    lines.append("|---:|---:|---:|---:|")
    for row in data["by_threshold"]:
        accuracy = "—" if row["accuracy"] is None else f"{row['accuracy']:.0%}"
        lines.append(
            f"| {row['threshold']:.2f} | {row['coverage']:.0%} | {accuracy} | {row['decided']} |"
        )
    misses = [row for row in data["rows"] if row.get("correct") is False]
    if misses:
        lines.append("")
        lines.append(
            "Errores: "
            + "; ".join(
                f"{row['query_id']} {row['expected']}→{row['predicted']} ({row['confidence']:.2f})"
                for row in misses
            )
        )
    return "\n".join(lines)


def run_metadata(config: JevConfig, run_id: str) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            cwd=PROJECT_ROOT,
        ).stdout.strip()
    except OSError:
        commit = ""
    return {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": config.model,
        "route_threshold": config.route_threshold,
        "crisis_threshold": config.crisis_threshold,
        "signals": list(config.signals),
        "commit": commit,
    }


# ---------------------------------------------------------------- comparación (US4, R14)

SECTION_START = "<!-- jev:start -->"
SECTION_END = "<!-- jev:end -->"
MODULE2_REPORT = Path("docs") / "evaluacion_modulo2.md"
QUERIES_FILE = Path("tests") / "fixtures" / "rag" / "module2_queries.jsonl"


def _care_row(report: dict[str, Any], variant: str) -> dict[str, Any]:
    summary = report["summary"][variant]
    rows = [r for r in report["results"] if r["variant"] == variant]
    traced = [r["jev"] for r in rows if r.get("jev")]
    return {
        "cases": summary["cases"],
        "passed": summary["passed"],
        "crisis": summary["metrics"]["SC-005_crisis"],
        "cordial": summary["metrics"]["SC-004_cordial"],
        "decided_by_jev": sum(r.get("decided_by") == "jev" for r in rows),
        "gate_calls": sum(t.get("status") in {"ok", "failed"} for t in traced),
        "gate_failed": sum(t.get("status") == "failed" for t in traced),
        "gate_cost": round(sum(t.get("cost") or 0.0 for t in traced), 8),
        "first_word_ms": summary.get("first_word_ms"),
        "failed_cases": sorted(
            f"{r['id']} ({r.get('decided_by') or '—'})" for r in rows if not r.get("passed", True)
        ),
    }


def compare(
    gate: JevGate,
    config: JevConfig,
    *,
    root: Path = PROJECT_ROOT,
    run_id: str = "",
    model: Any = None,
    agent_config: Any = None,
    care_runner: Callable[[Any], dict[str, Any]] | None = None,
    variant: str = "chain",
) -> dict[str, Any]:
    """Validación + enrutador sin/con Jev + batería de atención sin/con Jev (research R14)."""
    from dataclasses import replace

    from .config import load_agent_config
    from .evaluate import evaluate_router, load_router_cases

    run_id = run_id or f"jev-{datetime.now(UTC).strftime('%Y-%m-%d')}"
    base = agent_config or load_agent_config(project_root=root)
    if model is None:
        from ..llm import build_chat_model, load_llm_config

        model = build_chat_model(load_llm_config())
    validation = validate(gate, load_validation_cases(root / VALIDATION_FILE))
    cases = load_router_cases(root / QUERIES_FILE)
    min_confidence = base.router.min_confidence
    router_base = evaluate_router(
        cases, model=model, min_confidence=min_confidence, run_id=run_id, mode="real"
    )
    router_jev = evaluate_router(
        cases,
        model=model,
        min_confidence=min_confidence,
        run_id=run_id,
        mode="real",
        gate=gate,
        gate_threshold=config.route_threshold,
    )
    if care_runner is None:
        from .care_eval import run_care

        def care_runner(cfg: Any) -> dict[str, Any]:
            return run_care(mode="real", variants=(variant,), config=cfg)

    off = replace(base, jev=replace(base.jev, enabled=False))
    on = replace(base, jev=replace(config, enabled=True))
    care_base = _care_row(care_runner(off), variant)
    care_jev = _care_row(care_runner(on), variant)
    total_cost = validation.cost + router_jev.gate_cost + care_jev["gate_cost"]
    return {
        "meta": run_metadata(config, run_id),
        "validation": validation.to_dict(),
        "router": {"baseline": router_base.to_dict(), "jev": router_jev.to_dict()},
        "care": {"variant": variant, "baseline": care_base, "jev": care_jev},
        "cost_usd": round(total_cost, 6),
    }


def _pct(value: float) -> str:
    return f"{value * 100:.1f} %".replace(".", ",")


def render_report(data: dict[str, Any]) -> str:
    meta, val = data["meta"], data["validation"]
    base, jev = data["router"]["baseline"], data["router"]["jev"]
    care_base, care_jev = data["care"]["baseline"], data["care"]["jev"]
    cases = base["cases"] or 1
    saved = 1 - jev["model_calls"] / base["model_calls"] if base["model_calls"] else 0.0
    gate = jev["gate"]
    lines = [
        "# Evaluación del gatekeeper System One (Jev)",
        "",
        f"Generado por `agent jev --compare` el {meta['created_at'][:10]} (spec 022). Ejecución "
        f"`{meta['run_id']}`, commit `{meta['commit']}`, modelo `{meta['model']}`, umbral de ruta "
        f"{meta['route_threshold']} y de crisis {meta['crisis_threshold']}. Costo total de Jev: "
        f"{data['cost_usd']:.4f} USD.",
        "",
        "## Validación en español (SC-009)",
        "",
        f"{val['correct']}/{val['total']} rutas correctas ({_pct(val['accuracy'])}) sobre "
        "`tests/fixtures/jev/validation_es.jsonl` (24 consultas nuevas, 4 por ruta). Latencia "
        f"media {val['latency_ms_mean']} ms, p95 {val['latency_ms_p95']} ms.",
        "",
        "| Umbral | Cobertura | Exactitud cubierta |",
        "|---:|---:|---:|",
    ]
    for row in val["by_threshold"]:
        accuracy = "—" if row["accuracy"] is None else _pct(row["accuracy"])
        lines.append(f"| {row['threshold']:.2f} | {_pct(row['coverage'])} | {accuracy} |")
    lines += [
        "",
        "## Enrutador: reglas + LLM frente a reglas + Jev + LLM (SC-001, SC-002)",
        "",
        f"{base['cases']} consultas etiquetadas del Módulo 2 con DeepSeek "
        "(`tests/fixtures/rag/module2_queries.jsonl`).",
        "",
        "| Métrica | Sin Jev | Con Jev |",
        "|---|---:|---:|",
        f"| Exactitud de ruta | {_pct(base['accuracy'])} ({base['correct']}/{base['cases']}) "
        f"| {_pct(jev['accuracy'])} ({jev['correct']}/{jev['cases']}) |",
        f"| Llamadas al LLM por consulta | {base['model_calls'] / cases:.2f} "
        f"| {jev['model_calls'] / cases:.2f} |",
        f"| Llamadas al LLM evitadas | — | {_pct(saved)} |",
        f"| Decisiones de Jev | — | {gate['decided']} ({_pct(gate['decided_share'])}) |",
        f"| Fallos de Jev | — | {gate['failed']} |",
        f"| Latencia media de enrutamiento | {base['latency_ms_mean']:.0f} ms "
        f"| {jev['latency_ms_mean']:.0f} ms |",
        f"| p95 de enrutamiento | {base['latency_ms_p95']:.0f} ms "
        f"| {jev['latency_ms_p95']:.0f} ms |",
        f"| Latencia media de Jev | — | {gate['latency_ms_mean']:.0f} ms |",
        f"| Saludos y fuera de alcance sin búsqueda | {base['no_search']['ok']}/"
        f"{base['no_search']['total']} | {jev['no_search']['ok']}/{jev['no_search']['total']} |",
        "",
        "## Atención (SC-004)",
        "",
        f"Batería de {care_base['cases']} casos de la spec 019, variante "
        f"`{data['care']['variant']}`.",
        "",
        "| Métrica | Sin Jev | Con Jev |",
        "|---|---:|---:|",
        f"| Casos que cumplen | {care_base['passed']}/{care_base['cases']} "
        f"| {care_jev['passed']}/{care_jev['cases']} |",
        f"| Crisis atendidas (Línea 106 y 123) | {_pct(care_base['crisis'])} "
        f"| {_pct(care_jev['crisis'])} |",
        f"| Límite cordial ante insultos | {_pct(care_base['cordial'])} "
        f"| {_pct(care_jev['cordial'])} |",
        f"| Turnos decididos por Jev | — | {care_jev['decided_by_jev']} |",
        f"| Consultas a Jev / fallos | — | {care_jev['gate_calls']} / {care_jev['gate_failed']} |",
        f"| Primera palabra (media) | {care_base['first_word_ms'] or 0:.0f} ms "
        f"| {care_jev['first_word_ms'] or 0:.0f} ms |",
        f"| Casos que no cumplen (decidió) | {', '.join(care_base['failed_cases']) or '—'} "
        f"| {', '.join(care_jev['failed_cases']) or '—'} |",
    ]
    lines += render_end_to_end(data.get("end_to_end"))
    runs = data.get("previous_runs") or []
    if runs:
        lines += ["", "Ejecuciones anteriores del enrutador con Jev (mismo código y umbral):", ""]
        lines += [
            f"- `{run['run_id']}`: exactitud {_pct(run['accuracy'])}, Jev decide "
            f"{_pct(run['decided_share'])}, llamadas al LLM evitadas {_pct(run['saved'])}."
            for run in runs
        ]
    misses = jev.get("misses") or []
    if misses:
        lines += ["", "Errores de ruta con Jev:", ""]
        lines += ["| Consulta | Esperada | Predicha | Confianza | Decidió |"]
        lines += ["|---|---|---|---:|---|"]
        lines += [
            f"| {m['query_id']} | {m['expected']} | {m['predicted']} | {m['confidence']:.2f} "
            f"| {m['decided_by']} |"
            for m in misses
        ]
    return "\n".join(lines) + "\n"


def end_to_end_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Resumen por variante de ``agent evaluate --compare`` (SC-003)."""
    keys = ("latency_ms_mean", "latency_ms_p95", "under_10s", "model_calls_mean", "tokens_mean")
    return {
        "run_id": (payload.get("meta") or {}).get("run_id"),
        "variants": {v["variant"]: {k: v.get(k) for k in keys} for v in payload["variants"]},
    }


def render_end_to_end(block: dict[str, Any] | None) -> list[str]:
    if not block:
        return []
    base, jev = block["baseline"], block["jev"]
    lines = [
        "",
        "## Extremo a extremo: cadena y agente (SC-003)",
        "",
        "44 consultas por variante con DeepSeek, el mismo día y con el mismo código: "
        f"`{base['run_id']}` (sin Jev) y `{jev['run_id']}` (con Jev). Una ejecución por "
        "configuración; la latencia varía entre ejecuciones.",
        "",
        "| Variante | Métrica | Sin Jev | Con Jev |",
        "|---|---|---:|---:|",
    ]
    for variant in ("chain", "agent"):
        b, j = base["variants"].get(variant), jev["variants"].get(variant)
        if not b or not j:
            continue
        name = "Cadena" if variant == "chain" else "Agente"
        lines += [
            f"| {name} | Respuestas < 10 s | {_pct(b['under_10s'])} | {_pct(j['under_10s'])} |",
            f"| {name} | Latencia media / p95 | {b['latency_ms_mean'] / 1000:.2f} s / "
            f"{b['latency_ms_p95'] / 1000:.1f} s | {j['latency_ms_mean'] / 1000:.2f} s / "
            f"{j['latency_ms_p95'] / 1000:.1f} s |",
            f"| {name} | Llamadas al LLM / tokens | {b['model_calls_mean']:.2f} / "
            f"{b['tokens_mean']:.0f} | {j['model_calls_mean']:.2f} / {j['tokens_mean']:.0f} |",
        ]
    return lines


def module2_section(data: dict[str, Any]) -> str:
    base, jev = data["router"]["baseline"], data["router"]["jev"]
    return "\n".join(
        [
            SECTION_START,
            "## Gatekeeper System One (Jev, spec 022)",
            "",
            f"Ejecución `{data['meta']['run_id']}` (detalle en `docs/evaluacion_jev.md`): "
            f"exactitud de ruta {_pct(base['accuracy'])} sin Jev y {_pct(jev['accuracy'])} con "
            f"Jev; Jev decide {_pct(jev['gate']['decided_share'])} de las consultas y las "
            f"llamadas al LLM del enrutador bajan de {base['model_calls']} a "
            f"{jev['model_calls']}. Validación en español "
            f"{_pct(data['validation']['accuracy'])}; costo {data['cost_usd']:.4f} USD.",
            SECTION_END,
        ]
    )


def write_reports(data: dict[str, Any], root: Path = PROJECT_ROOT) -> None:
    (root / REPORT_JSON).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / REPORT_MD).write_text(render_report(data), encoding="utf-8")
    path = root / MODULE2_REPORT
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    section = module2_section(data)
    if SECTION_START in text and SECTION_END in text:
        text = text.split(SECTION_START)[0] + section + text.split(SECTION_END, 1)[1]
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    path.write_text(text, encoding="utf-8")


def run_compare(
    gate: JevGate, config: JevConfig, *, root: Path, run_id: str = "", as_json: bool = False
) -> int:
    data = compare(gate, config, root=root, run_id=run_id)
    write_reports(data, root)
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_report(data))
        print(f"informe: {REPORT_MD} y {REPORT_JSON}; sección en {MODULE2_REPORT}")
    return 0
