"""Evaluación reproducible de la recuperación: Recall@k y MRR por modo."""

from __future__ import annotations

import json
import math
import statistics
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..retrieval import select_evidence
from .hybrid import HybridRetriever

K_VALUES = (1, 3, 5, 8)
MODES = ("semantic", "lexical", "hybrid")
VALID_TYPES = ("paraphrase", "figure", "proper_noun", "english", "out_of_corpus")


@dataclass(frozen=True, slots=True)
class EvaluationQuestion:
    question_id: str
    question: str
    expected_unit_ids: tuple[str, ...]
    type: str = "paraphrase"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("question no puede estar vacía")
        if self.type not in VALID_TYPES:
            raise ValueError(f"tipo inválido: {self.type}")


def load_questions(path: str | Path) -> tuple[EvaluationQuestion, ...]:
    """Load an evaluation set from JSONL."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"No existe el conjunto de evaluación: {source}")
    questions: list[EvaluationQuestion] = []
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en {source.name}, línea {number}: {exc}") from exc
        questions.append(
            EvaluationQuestion(
                question_id=str(payload["question_id"]),
                question=str(payload["question"]),
                expected_unit_ids=tuple(
                    str(item) for item in payload.get("expected_unit_ids") or ()
                ),
                type=str(payload.get("type", "paraphrase")),
                notes=str(payload.get("notes", "")),
            )
        )
    if not questions:
        raise ValueError("El conjunto de evaluación está vacío.")
    return tuple(questions)


@dataclass(frozen=True, slots=True)
class ModeMetrics:
    mode: str
    recall_at_k: dict[int, float]
    mrr: float
    citation_coverage: float
    latency_mean_ms: float
    latency_p95_ms: float

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "recall_at_k": {str(k): round(v, 4) for k, v in self.recall_at_k.items()},
            "mrr": round(self.mrr, 4),
            "citation_coverage": round(self.citation_coverage, 4),
            "latency_ms": {
                "mean": round(self.latency_mean_ms, 2),
                "p95": round(self.latency_p95_ms, 2),
            },
        }


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    run_id: str
    questions: int
    k_values: tuple[int, ...]
    modes: dict[str, ModeMetrics]
    baseline: str
    verdict: str
    errors: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "questions": self.questions,
            "k_values": list(self.k_values),
            "modes": {name: metrics.to_dict() for name, metrics in self.modes.items()},
            "baseline": self.baseline,
            "verdict": self.verdict,
            "errors": list(self.errors),
        }


def _rankings(
    retriever: HybridRetriever,
    question: str,
    mode: str,
    *,
    top_k: int,
    token_budget: int,
) -> list[str]:
    if mode == "hybrid":
        trace = retriever.retrieve(question, top_k=top_k, token_budget=token_budget)
        return [fragment.unit_id for fragment in trace.fragments if fragment.status == "used"]
    if mode == "semantic":
        if retriever.semantic is None or not retriever.semantic.available:
            return []
        fragments = retriever.semantic.search(question, top_k=top_k)
        return [
            fragment.unit_id
            for fragment in fragments
            if (fragment.semantic_score or 0.0) >= retriever.config.hybrid.min_similarity
        ]
    selection = select_evidence(
        question,
        retriever.units,
        entity_index=retriever.entity_index,
        top_k=top_k,
        token_budget=token_budget,
    )
    return [item.unit.unit_id for item in selection.selected]


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * (len(ordered) - 1))))
    return float(ordered[index])


def evaluate_questions(
    retriever: HybridRetriever,
    questions: Iterable[EvaluationQuestion],
    *,
    modes: Sequence[str] = MODES,
    k_values: Sequence[int] = K_VALUES,
    top_k: int = 12,
    token_budget: int = 6000,
    run_id: str = "",
) -> EvaluationRun:
    """Compute Recall@k, MRR, coverage and latency for each mode."""
    corpus = tuple(questions)
    in_corpus = [question for question in corpus if question.expected_unit_ids]
    results: dict[str, ModeMetrics] = {}
    errors: list[dict[str, object]] = []

    for mode in modes:
        recalls = {k: 0 for k in k_values}
        reciprocal = 0.0
        covered = 0
        latencies: list[float] = []
        for question in corpus:
            begin = time.perf_counter()
            ranking = _rankings(
                retriever, question.question, mode, top_k=top_k, token_budget=token_budget
            )
            latencies.append((time.perf_counter() - begin) * 1000)
            if not question.expected_unit_ids:
                if ranking:
                    errors.append(
                        {
                            "question_id": question.question_id,
                            "mode": mode,
                            "type": question.type,
                            "cause": "devolvió evidencia para una pregunta fuera de corpus",
                        }
                    )
                continue
            if ranking:
                covered += 1
            expected = set(question.expected_unit_ids)
            for k in k_values:
                if expected.intersection(ranking[:k]):
                    recalls[k] += 1
            position = next(
                (index for index, unit_id in enumerate(ranking, start=1) if unit_id in expected),
                None,
            )
            if position is not None:
                reciprocal += 1.0 / position
            else:
                errors.append(
                    {
                        "question_id": question.question_id,
                        "mode": mode,
                        "type": question.type,
                        "cause": "la unidad esperada no apareció en el ranking",
                    }
                )
        total = len(in_corpus) or 1
        results[mode] = ModeMetrics(
            mode=mode,
            recall_at_k={k: recalls[k] / total for k in k_values},
            mrr=reciprocal / total,
            citation_coverage=covered / total,
            latency_mean_ms=statistics.fmean(latencies) if latencies else 0.0,
            latency_p95_ms=_percentile(latencies, 0.95),
        )

    baseline = results.get("lexical")
    hybrid = results.get("hybrid")
    if baseline is not None and hybrid is not None:
        ok = (
            hybrid.recall_at_k.get(5, 0.0) >= baseline.recall_at_k.get(5, 0.0)
            and hybrid.mrr >= baseline.mrr
        )
        verdict = (
            "hybrid >= baseline en Recall@5 y MRR"
            if ok
            else "hybrid NO supera la línea base léxica en Recall@5 o MRR"
        )
    else:
        verdict = "sin línea base léxica comparable"

    return EvaluationRun(
        run_id=run_id or "eval",
        questions=len(corpus),
        k_values=tuple(k_values),
        modes=results,
        baseline="lexical",
        verdict=verdict,
        errors=tuple(errors),
    )


def render_markdown(run: EvaluationRun, *, extra_notes: Iterable[str] = ()) -> str:
    """Render an evaluation run as a Markdown section."""
    header = (
        "| Modo | "
        + " | ".join(f"Recall@{k}" for k in run.k_values)
        + " | MRR | Cobertura | Latencia media | p95 |"
    )
    separator = "|---" * (len(run.k_values) + 5) + "|"
    lines = [
        "# Evaluación del Módulo 2 — recuperación semántica",
        "",
        f"**Ejecución**: `{run.run_id}` · **Preguntas**: {run.questions} · "
        f"**Línea base**: {run.baseline}",
        "",
        "## Métricas por modo",
        "",
        header,
        separator,
    ]
    for name in ("semantic", "lexical", "hybrid"):
        metrics = run.modes.get(name)
        if metrics is None:
            continue
        cells = [f"{metrics.recall_at_k[k]:.3f}" for k in run.k_values]
        lines.append(
            f"| {name} | " + " | ".join(cells) + f" | {metrics.mrr:.3f} | "
            f"{metrics.citation_coverage:.3f} | {metrics.latency_mean_ms:.1f} ms | "
            f"{metrics.latency_p95_ms:.1f} ms |"
        )
    lines.extend(
        [
            "",
            f"**Veredicto**: {run.verdict}",
            "",
            "## Análisis de errores",
            "",
        ]
    )
    if run.errors:
        lines.append("| Pregunta | Modo | Tipo | Causa |")
        lines.append("|---|---|---|---|")
        for error in run.errors[:40]:
            lines.append(
                f"| {error['question_id']} | {error['mode']} | {error['type']} | {error['cause']} |"
            )
    else:
        lines.append("Sin errores registrados en esta ejecución.")
    notes = list(extra_notes)
    if notes:
        lines.extend(["", "## Notas", ""])
        lines.extend(f"- {note}" for note in notes)
    lines.append("")
    return "\n".join(lines)
