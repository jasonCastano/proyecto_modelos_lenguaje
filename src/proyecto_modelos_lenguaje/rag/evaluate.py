"""Evaluación reproducible de la recuperación: Recall@k, nDCG@10, MRR y abstención por modo.

Spec 013 introdujo Recall@k y MRR; la spec 014 (FR-020) añade nDCG@10, Recall@10, la tasa de
abstención en preguntas fuera de corpus, el calentamiento antes de medir latencia y la lista de
consultas en las que el modo híbrido empeora frente a la línea base léxica.

Definiciones (relevancia binaria):

- ``Recall@k`` = |relevantes ∩ top-k| / |relevantes|.
- ``nDCG@k`` = DCG@k / IDCG@k con DCG = Σ rel_i / log2(i + 1).
- ``MRR`` = media de 1 / posición del primer relevante (0 si no aparece).
- ``abstención`` = proporción de preguntas ``out_of_corpus`` sin evidencia devuelta.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..retrieval import select_evidence
from .hybrid import HybridRetriever

K_VALUES = (1, 3, 5, 10)
NDCG_K = 10
MODES = ("semantic", "lexical", "hybrid")
VALID_TYPES = (
    "paraphrase",
    "figure",
    "proper_noun",
    "english",
    "out_of_corpus",
    # Tipos del conjunto de la spec 014 (module2_queries.jsonl).
    "greeting",
    "documental",
    "structured",
    "ambiguous",
    "follow_up",
    "mixed",
)
DEFAULT_WARMUP = 3


@dataclass(frozen=True, slots=True)
class EvaluationQuestion:
    question_id: str
    question: str
    expected_unit_ids: tuple[str, ...]
    type: str = "paraphrase"
    notes: str = ""
    expected_route: str | None = None

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("question no puede estar vacía")
        if self.type not in VALID_TYPES:
            raise ValueError(f"tipo inválido: {self.type}")

    @property
    def scored(self) -> bool:
        """Cuenta para Recall/nDCG/MRR: tiene unidades relevantes etiquetadas.

        Las repreguntas elípticas (``follow_up``) solo tienen sentido con el hilo previo; se
        evalúan en la conversación (SC-006), no en la recuperación aislada.
        """
        return bool(self.expected_unit_ids) and self.type != "follow_up"

    @property
    def must_abstain(self) -> bool:
        """Pregunta fuera de corpus: la recuperación no debería devolver evidencia."""
        return self.type == "out_of_corpus"


def load_questions(path: str | Path) -> tuple[EvaluationQuestion, ...]:
    """Carga un conjunto JSONL (formato de la spec 013 o de la spec 014)."""
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
        # Spec 024: module3_queries.jsonl identifica cada consulta con ``id``.
        identifier = payload.get("question_id", payload.get("query_id", payload.get("id")))
        if identifier is None:
            raise ValueError(f"Falta question_id/query_id/id en {source.name}, línea {number}")
        questions.append(
            EvaluationQuestion(
                question_id=str(identifier),
                question=str(payload["question"]),
                expected_unit_ids=tuple(
                    str(item) for item in payload.get("expected_unit_ids") or ()
                ),
                type=str(payload.get("type", "paraphrase")),
                notes=str(payload.get("notes", "")),
                expected_route=payload.get("expected_route"),
            )
        )
    if not questions:
        raise ValueError("El conjunto de evaluación está vacío.")
    return tuple(questions)


def _dedupe(ranking: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for unit_id in ranking:
        if unit_id not in seen:
            seen.add(unit_id)
            ordered.append(unit_id)
    return ordered


def recall_at_k(ranking: Sequence[str], expected: set[str] | frozenset[str], k: int) -> float:
    """|relevantes ∩ top-k| / |relevantes|; 0 si no hay relevantes."""
    if not expected:
        return 0.0
    hits = expected.intersection(_dedupe(ranking)[:k])
    return len(hits) / len(expected)


def ndcg_at_k(ranking: Sequence[str], expected: set[str] | frozenset[str], k: int) -> float:
    """nDCG@k con relevancia binaria y descuento log2(posición + 1)."""
    if not expected:
        return 0.0
    top = _dedupe(ranking)[:k]
    dcg = sum(
        1.0 / math.log2(position + 1)
        for position, unit_id in enumerate(top, 1)
        if unit_id in expected
    )
    ideal = sum(1.0 / math.log2(position + 1) for position in range(1, min(len(expected), k) + 1))
    return dcg / ideal if ideal else 0.0


def reciprocal_rank(ranking: Sequence[str], expected: set[str] | frozenset[str]) -> float:
    for position, unit_id in enumerate(_dedupe(ranking), start=1):
        if unit_id in expected:
            return 1.0 / position
    return 0.0


def percentile(values: Sequence[float], fraction: float) -> float:
    """Percentil con interpolación lineal sobre la muestra ordenada (corrige el p95 de la 013)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = min(max(fraction, 0.0), 1.0) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


@dataclass(frozen=True, slots=True)
class ModeMetrics:
    mode: str
    recall_at_k: dict[int, float]
    mrr: float
    citation_coverage: float
    latency_mean_ms: float
    latency_p95_ms: float
    ndcg_at_10: float = 0.0
    abstention_rate: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "recall_at_k": {str(k): round(v, 4) for k, v in self.recall_at_k.items()},
            "ndcg_at_10": round(self.ndcg_at_10, 4),
            "mrr": round(self.mrr, 4),
            "citation_coverage": round(self.citation_coverage, 4),
            "abstention_rate": None
            if self.abstention_rate is None
            else round(self.abstention_rate, 4),
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
    regressions: tuple[dict[str, object], ...] = ()
    scored_questions: int = 0
    warmup: int = 0
    per_question: dict[str, dict[str, float]] = field(default_factory=dict)
    # Spec 024: Recall@10 por consulta y modo (proyección t-SNE y consultas fallidas).
    per_question_recall: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "questions": self.questions,
            "scored_questions": self.scored_questions,
            "warmup": self.warmup,
            "k_values": list(self.k_values),
            "modes": {name: metrics.to_dict() for name, metrics in self.modes.items()},
            "baseline": self.baseline,
            "verdict": self.verdict,
            "errors": list(self.errors),
            "regressions": list(self.regressions),
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


def _verdict(results: dict[str, ModeMetrics]) -> str:
    baseline = results.get("lexical")
    hybrid = results.get("hybrid")
    if baseline is None or hybrid is None:
        return "sin línea base léxica comparable"
    ok = (
        hybrid.recall_at_k.get(10, hybrid.recall_at_k.get(max(hybrid.recall_at_k), 0.0))
        >= baseline.recall_at_k.get(10, baseline.recall_at_k.get(max(baseline.recall_at_k), 0.0))
        and hybrid.ndcg_at_10 >= baseline.ndcg_at_10
        and hybrid.mrr >= baseline.mrr
    )
    if ok:
        return "hybrid >= baseline en Recall@10, nDCG@10 y MRR"
    return "hybrid NO supera la línea base léxica en Recall@10, nDCG@10 o MRR"


def evaluate_questions(
    retriever: HybridRetriever,
    questions: Iterable[EvaluationQuestion],
    *,
    modes: Sequence[str] = MODES,
    k_values: Sequence[int] = K_VALUES,
    top_k: int = 12,
    token_budget: int = 6000,
    run_id: str = "",
    warmup: int = 0,
) -> EvaluationRun:
    """Calcula Recall@k, nDCG@10, MRR, cobertura, abstención y latencia por modo.

    ``warmup`` consultas se ejecutan antes de medir en cada modo y se descartan, para que la
    carga del modelo y las cachés no inflen la latencia (revisión del PR #34).
    """
    corpus = tuple(questions)
    scored = [question for question in corpus if question.scored]
    to_abstain = [question for question in corpus if question.must_abstain]
    results: dict[str, ModeMetrics] = {}
    errors: list[dict[str, object]] = []
    per_question: dict[str, dict[str, float]] = {}
    per_question_recall: dict[str, dict[str, float]] = {}

    for mode in modes:
        for question in corpus[: max(0, warmup)]:
            _rankings(retriever, question.question, mode, top_k=top_k, token_budget=token_budget)

        recalls = {k: 0.0 for k in k_values}
        ndcg_total = 0.0
        reciprocal = 0.0
        covered = 0
        abstained = 0
        latencies: list[float] = []
        mode_scores: dict[str, float] = {}
        mode_recalls: dict[str, float] = {}
        for question in corpus:
            begin = time.perf_counter()
            ranking = _rankings(
                retriever, question.question, mode, top_k=top_k, token_budget=token_budget
            )
            latencies.append((time.perf_counter() - begin) * 1000)
            if question.must_abstain:
                if ranking:
                    errors.append(
                        {
                            "question_id": question.question_id,
                            "mode": mode,
                            "type": question.type,
                            "cause": "devolvió evidencia para una pregunta fuera de corpus",
                        }
                    )
                else:
                    abstained += 1
                continue
            if not question.scored:
                continue
            if ranking:
                covered += 1
            expected = set(question.expected_unit_ids)
            for k in k_values:
                recalls[k] += recall_at_k(ranking, expected, k)
            mode_recalls[question.question_id] = recall_at_k(ranking, expected, NDCG_K)
            score = ndcg_at_k(ranking, expected, NDCG_K)
            ndcg_total += score
            mode_scores[question.question_id] = score
            rank_score = reciprocal_rank(ranking, expected)
            reciprocal += rank_score
            if rank_score == 0.0:
                errors.append(
                    {
                        "question_id": question.question_id,
                        "mode": mode,
                        "type": question.type,
                        "cause": "la unidad esperada no apareció en el ranking",
                    }
                )
        total = len(scored) or 1
        per_question[mode] = mode_scores
        per_question_recall[mode] = mode_recalls
        results[mode] = ModeMetrics(
            mode=mode,
            recall_at_k={k: recalls[k] / total for k in k_values},
            mrr=reciprocal / total,
            citation_coverage=covered / total,
            latency_mean_ms=statistics.fmean(latencies) if latencies else 0.0,
            latency_p95_ms=percentile(latencies, 0.95),
            ndcg_at_10=ndcg_total / total,
            abstention_rate=(abstained / len(to_abstain)) if to_abstain else None,
        )

    regressions: list[dict[str, object]] = []
    if "hybrid" in per_question and "lexical" in per_question:
        for question in scored:
            hybrid_score = per_question["hybrid"].get(question.question_id, 0.0)
            lexical_score = per_question["lexical"].get(question.question_id, 0.0)
            if hybrid_score < lexical_score:
                regressions.append(
                    {
                        "question_id": question.question_id,
                        "type": question.type,
                        "ndcg_hybrid": round(hybrid_score, 4),
                        "ndcg_lexical": round(lexical_score, 4),
                    }
                )

    return EvaluationRun(
        run_id=run_id or "eval",
        questions=len(corpus),
        k_values=tuple(k_values),
        modes=results,
        baseline="lexical",
        verdict=_verdict(results),
        errors=tuple(errors),
        regressions=tuple(regressions),
        scored_questions=len(scored),
        warmup=max(0, warmup),
        per_question=per_question,
        per_question_recall=per_question_recall,
    )


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def render_markdown(run: EvaluationRun, *, extra_notes: Iterable[str] = ()) -> str:
    """Render an evaluation run as a Markdown section."""
    header = (
        "| Modo | "
        + " | ".join(f"Recall@{k}" for k in run.k_values)
        + " | nDCG@10 | MRR | Cobertura | Abstención | Latencia media | p95 |"
    )
    separator = "|---" * (len(run.k_values) + 7) + "|"
    lines = [
        "# Evaluación del Módulo 2 — recuperación semántica",
        "",
        f"**Ejecución**: `{run.run_id}` · **Preguntas**: {run.questions} "
        f"({run.scored_questions} con unidades etiquetadas) · **Línea base**: {run.baseline} · "
        f"**Calentamiento**: {run.warmup} consultas descartadas por modo",
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
            f"| {name} | " + " | ".join(cells) + f" | {metrics.ndcg_at_10:.3f} | "
            f"{metrics.mrr:.3f} | {metrics.citation_coverage:.3f} | "
            f"{_fmt(metrics.abstention_rate)} | {metrics.latency_mean_ms:.1f} ms | "
            f"{metrics.latency_p95_ms:.1f} ms |"
        )
    lines.extend(
        [
            "",
            f"**Veredicto**: {run.verdict}",
            "",
            "*Recall@k* = fracción de unidades relevantes en el top-k; *nDCG@10* con relevancia "
            "binaria; *Abstención* = preguntas fuera de corpus sin evidencia devuelta.",
            "",
            "## Consultas donde el híbrido empeora frente al léxico",
            "",
        ]
    )
    if run.regressions:
        lines.append("| Pregunta | Tipo | nDCG@10 híbrido | nDCG@10 léxico |")
        lines.append("|---|---|---|---|")
        for item in run.regressions:
            lines.append(
                f"| {item['question_id']} | {item['type']} | {item['ndcg_hybrid']:.3f} | "
                f"{item['ndcg_lexical']:.3f} |"
            )
    else:
        lines.append("Ninguna: el híbrido iguala o mejora al léxico en todas las consultas.")
    lines.extend(["", "## Análisis de errores", ""])
    if run.errors:
        lines.append("| Pregunta | Modo | Tipo | Causa |")
        lines.append("|---|---|---|---|")
        for error in run.errors[:60]:
            lines.append(
                f"| {error['question_id']} | {error['mode']} | {error['type']} | {error['cause']} |"
            )
        if len(run.errors) > 60:
            lines.append(f"| … | | | {len(run.errors) - 60} errores más en el JSON |")
    else:
        lines.append("Sin errores registrados en esta ejecución.")
    notes = list(extra_notes)
    if notes:
        lines.extend(["", "## Notas", ""])
        lines.extend(f"- {note}" for note in notes)
    lines.append("")
    return "\n".join(lines)


# --- Spec 024 (US5, T071): evaluación del Módulo 3 frente a la línea base del Módulo 2 ---------

MODULE2_BASELINE_PATH = Path("docs") / "evaluacion_qdrant.json"
# Modo híbrido del Módulo 2 sobre Qdrant (docs/evaluacion_qdrant.json, 35 preguntas puntuables).
MODULE2_BASELINE: dict[str, object] = {
    "source": MODULE2_BASELINE_PATH.as_posix(),
    "run_id": "qdrant-base-2026-11-14",
    "mode": "hybrid",
    "scored_questions": 35,
    "recall_at_10": 0.6714,
    "ndcg_at_10": 0.4986,
    "mrr": 0.4499,
}
COMPARED_METRICS = {"recall_at_10": "Recall@10", "ndcg_at_10": "nDCG@10", "mrr": "MRR"}


def load_module2_baseline(path: str | Path | None = None) -> dict[str, object]:
    """Línea base híbrida del Módulo 2; si el JSON no está, usa los valores registrados."""
    source = Path(path) if path is not None else None
    if source is None or not source.is_file():
        return dict(MODULE2_BASELINE)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        hybrid = payload["modes"]["hybrid"]
        return {
            "source": MODULE2_BASELINE_PATH.as_posix(),
            "run_id": payload.get("run_id", ""),
            "mode": "hybrid",
            "scored_questions": payload.get("scored_questions"),
            "recall_at_10": float(hybrid["recall_at_k"]["10"]),
            "ndcg_at_10": float(hybrid["ndcg_at_10"]),
            "mrr": float(hybrid["mrr"]),
        }
    except OSError, ValueError, KeyError, TypeError:
        return dict(MODULE2_BASELINE)


def compare_with_baseline(
    run: EvaluationRun, baseline: dict[str, object] | None = None, *, mode: str = "hybrid"
) -> dict[str, object]:
    """Diferencias (actual − línea base) en Recall@10, nDCG@10 y MRR del modo indicado."""
    reference = baseline or MODULE2_BASELINE
    metrics = run.modes.get(mode)
    if metrics is None:
        return {"mode": mode, "baseline": reference, "available": False}
    current = {
        "recall_at_10": metrics.recall_at_k.get(NDCG_K, 0.0),
        "ndcg_at_10": metrics.ndcg_at_10,
        "mrr": metrics.mrr,
    }
    rows: dict[str, dict[str, float]] = {}
    for name in COMPARED_METRICS:
        before = float(reference[name])  # type: ignore[arg-type]
        rows[name] = {
            "baseline": round(before, 4),
            "current": round(current[name], 4),
            "delta": round(current[name] - before, 4),
        }
    return {
        "mode": mode,
        "available": True,
        "baseline": reference,
        "metrics": rows,
        "not_worse": all(row["delta"] >= 0 for row in rows.values()),
    }


def per_query_results(run: EvaluationRun, *, mode: str = "hybrid") -> list[dict[str, object]]:
    """Recall@10 y nDCG@10 por consulta; ``failed`` = Recall@10 igual a 0."""
    recalls = run.per_question_recall.get(mode, {})
    ndcg = run.per_question.get(mode, {})
    return [
        {
            "id": question_id,
            "recall_at_10": round(recall, 4),
            "ndcg_at_10": round(ndcg.get(question_id, 0.0), 4),
            "failed": recall == 0.0,
        }
        for question_id, recall in recalls.items()
    ]


def module3_payload(
    run: EvaluationRun,
    *,
    queries_path: str,
    backend: str,
    baseline: dict[str, object] | None = None,
) -> dict[str, object]:
    """JSON de ``docs/evaluacion_modulo3.json``: métricas, comparación y resultado por consulta."""
    return {
        "spec": "024",
        "queries": queries_path,
        "backend": backend,
        **run.to_dict(),
        "comparison": compare_with_baseline(run, baseline),
        "per_query": per_query_results(run),
    }


def render_module3_markdown(
    payload: dict[str, object], run: EvaluationRun, *, extra_notes: Iterable[str] = ()
) -> str:
    """Informe del Módulo 3: métricas por modo, comparación con el Módulo 2 y consultas fallidas."""
    base = render_markdown(run, extra_notes=extra_notes).replace(
        "# Evaluación del Módulo 2 — recuperación semántica",
        "# Evaluación del Módulo 3 — recuperación sobre Qdrant",
        1,
    )
    comparison = payload["comparison"]
    assert isinstance(comparison, dict)
    lines = [
        base.rstrip(),
        "",
        "## Comparación con la línea base del Módulo 2 (híbrido)",
        "",
        f"**Consultas**: `{payload['queries']}` · **Búsqueda vectorial**: {payload['backend']}",
        "",
    ]
    if comparison.get("available"):
        reference = comparison["baseline"]
        metrics = comparison["metrics"]
        assert isinstance(reference, dict) and isinstance(metrics, dict)
        lines.extend(["| Métrica | Módulo 2 | Módulo 3 | Δ |", "|---|---|---|---|"])
        for name, label in COMPARED_METRICS.items():
            row = metrics[name]
            lines.append(
                f"| {label} | {row['baseline']:.3f} | {row['current']:.3f} | {row['delta']:+.3f} |"
            )
        verdict = "no empeora" if comparison.get("not_worse") else "empeora en alguna métrica"
        lines.extend(
            [
                "",
                f"**Lectura**: el Módulo 3 {verdict} frente a la línea base "
                f"(`{reference.get('source')}`, {reference.get('scored_questions')} preguntas "
                "puntuables). Las consultas son una muestra fija (semilla 2026) de esas "
                "preguntas, elegida antes de evaluar; la comparación es indicativa.",
            ]
        )
    else:
        lines.append("Sin modo híbrido en esta ejecución: no hay comparación.")
    per_query = payload.get("per_query") or []
    assert isinstance(per_query, list)
    failed = [row for row in per_query if row["failed"]]
    lines.extend(["", "## Consultas fallidas (Recall@10 = 0, híbrido)", ""])
    if failed:
        lines.extend(f"- `{row['id']}`" for row in failed)
    else:
        lines.append("Ninguna.")
    lines.append("")
    return "\n".join(lines)
