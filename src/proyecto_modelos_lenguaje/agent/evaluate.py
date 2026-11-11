"""Evaluación del enrutador sobre el conjunto etiquetado (spec 014, T036, SC-002 y SC-004)."""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from .models import Route
from .router import route_message

ROUTES: tuple[Route, ...] = ("direct", "documental", "structured", "out_of_scope", "clarify")
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
            "confusion": {route: dict(counter) for route, counter in self.confusion.items()},
            "misses": self.misses,
        }


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
) -> RouterReport:
    confusion = {route: Counter() for route in ROUTES}
    report = RouterReport(run_id, mode, len(cases), 0, 0, 0.0, confusion)
    latencies: list[float] = []
    for case in cases:
        started = time.perf_counter()
        result = route_message(
            case.question, history=case.history, model=model, min_confidence=min_confidence
        )
        latencies.append((time.perf_counter() - started) * 1000)
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
        "(30 consultas + 6 repreguntas con su turno previo como historial)",
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
