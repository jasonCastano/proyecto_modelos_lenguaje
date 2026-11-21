"""Evaluación del enrutador sobre el conjunto etiquetado (spec 014, T036, SC-002 y SC-004)."""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel

from .models import Route
from .router import is_smalltalk, route_message

if TYPE_CHECKING:
    from .jev import JevGate

ROUTES: tuple[Route, ...] = (
    "direct",
    "documental",
    "structured",
    "mixed",
    "out_of_scope",
    "clarify",
)
SECTION_START = "<!-- router:start -->"
SECTION_END = "<!-- router:end -->"


@dataclass(frozen=True, slots=True)
class RouterCase:
    query_id: str
    question: str
    expected: str
    type: str
    history: tuple[str, ...] = ()


@dataclass(slots=True)
class RouterReport:
    run_id: str
    mode: str
    cases: int
    correct: int
    model_calls: int
    latency_ms: float
    confusion: dict[str, Counter] = field(default_factory=dict)
    misses: list[dict[str, Any]] = field(default_factory=list)
    no_search_ok: int = 0
    no_search_total: int = 0
    # Spec 021: gatekeeper Jev (consultas, decisiones aceptadas, fallos, latencia y costo).
    latencies: list[float] = field(default_factory=list)
    gate_calls: int = 0
    gate_decided: int = 0
    gate_failed: int = 0
    gate_latency_ms: list[int] = field(default_factory=list)
    gate_cost: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.cases if self.cases else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "cases": self.cases,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "model_calls": self.model_calls,
            "latency_ms_mean": round(self.latency_ms, 1),
            "no_search": {"ok": self.no_search_ok, "total": self.no_search_total},
            "latency_ms_p95": _p95(self.latencies),
            "gate": {
                "calls": self.gate_calls,
                "decided": self.gate_decided,
                "decided_share": round(self.gate_decided / self.cases, 4) if self.cases else 0.0,
                "failed": self.gate_failed,
                "latency_ms_mean": round(sum(self.gate_latency_ms) / len(self.gate_latency_ms), 1)
                if self.gate_latency_ms
                else 0.0,
                "cost": round(self.gate_cost, 8),
            },
            "confusion": {route: dict(counter) for route, counter in self.confusion.items()},
            "misses": self.misses,
        }


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(float(ordered[max(0, round(0.95 * (len(ordered) - 1)))]), 1)


def load_router_cases(path: str | Path) -> list[RouterCase]:
    rows = [
        json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line
    ]
    questions = {row["query_id"]: row["question"] for row in rows}
    return [
        RouterCase(
            query_id=row["query_id"],
            question=row["question"],
            expected=row["expected_route"],
            type=row["type"],
            history=(questions[row["follow_up_of"]],) if row.get("follow_up_of") else (),
        )
        for row in rows
    ]


def evaluate_router(
    cases: Sequence[RouterCase],
    *,
    model: BaseChatModel | None,
    min_confidence: float,
    run_id: str,
    mode: str,
    gate: JevGate | None = None,
    gate_threshold: float = 0.75,
) -> RouterReport:
    """Exactitud del enrutador; con ``gate`` mide reglas → Jev → LLM (spec 021, research R14)."""
    confusion = {route: Counter() for route in ROUTES}
    report = RouterReport(run_id, mode, len(cases), 0, 0, 0.0, confusion)
    latencies = report.latencies
    for case in cases:
        started = time.perf_counter()
        outcome = None
        if gate is not None and not is_smalltalk(case.question):
            outcome = gate.assess(case.question, case.history)
            report.gate_calls += 1
            report.gate_latency_ms.append(outcome.latency_ms)
            report.gate_cost += outcome.cost or 0.0
            report.gate_failed += outcome.status == "failed"
        result = route_message(
            case.question,
            history=case.history,
            model=model,
            min_confidence=min_confidence,
            gate=outcome,
            gate_threshold=gate_threshold,
        )
        latencies.append((time.perf_counter() - started) * 1000)
        report.gate_decided += result.decision.decided_by == "jev"
        predicted = result.decision.route
        report.model_calls += result.model_calls
        confusion[case.expected][predicted] += 1
        if case.expected in ("direct", "out_of_scope"):
            report.no_search_total += 1
            report.no_search_ok += predicted in ("direct", "out_of_scope")
        if predicted == case.expected:
            report.correct += 1
        else:
            report.misses.append(
                {
                    "query_id": case.query_id,
                    "question": case.question,
                    "expected": case.expected,
                    "predicted": predicted,
                    "confidence": result.decision.confidence,
                    "decided_by": result.decision.decided_by,
                    "reason": result.decision.reason,
                }
            )
    report.latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
    return report


def render_router_section(report: RouterReport) -> str:
    lines = [
        SECTION_START,
        "## Enrutador (US2)",
        "",
        f"**Ejecución**: `{report.run_id}` · **Modo**: {report.mode} · **Casos**: {report.cases} "
        "(las repreguntas llevan su turno previo como historial; incluye 5 casos `mixed`)",
        "",
        "| Métrica | Valor | Criterio |",
        "|---|---:|---|",
        f"| Precisión del enrutador | {report.accuracy:.3f} ({report.correct}/{report.cases}) | "
        "SC-002 ≥ 0,90 |",
        "| Saludos y fuera de alcance sin búsqueda | "
        f"{report.no_search_ok}/{report.no_search_total} | SC-004 100 % |",
        f"| Llamadas al modelo | {report.model_calls} | 0 en reglas |",
        f"| Latencia media por decisión | {report.latency_ms:.0f} ms | — |",
        "",
        "Matriz de confusión (filas: esperada; columnas: predicha):",
        "",
        "| Esperada \\ Predicha | " + " | ".join(ROUTES) + " |",
        "|---" * (len(ROUTES) + 1) + "|",
    ]
    for expected in ROUTES:
        counter = report.confusion.get(expected, Counter())
        lines.append(
            f"| {expected} | " + " | ".join(str(counter.get(route, 0)) for route in ROUTES) + " |"
        )
    lines += ["", "Errores:", ""]
    if report.misses:
        lines += ["| Consulta | Esperada | Predicha | Confianza | Decidió | Motivo |"]
        lines += ["|---|---|---|---:|---|---|"]
        for miss in report.misses:
            lines.append(
                f"| {miss['query_id']} «{miss['question']}» | {miss['expected']} | "
                f"{miss['predicted']} | {miss['confidence']:.2f} | {miss['decided_by']} | "
                f"{miss['reason']} |"
            )
    else:
        lines.append("Ninguno.")
    lines += ["", SECTION_END]
    return "\n".join(lines)


def write_router_section(report_path: Path, section: str) -> None:
    """Inserta o reemplaza la sección del enrutador en ``docs/evaluacion_modulo2.md``."""
    text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    if SECTION_START in text and SECTION_END in text:
        before = text.split(SECTION_START)[0]
        after = text.split(SECTION_END, 1)[1]
        text = before + section + after
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    report_path.write_text(text, encoding="utf-8")
