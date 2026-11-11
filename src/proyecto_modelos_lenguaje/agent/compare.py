"""Comparación cadena vs. agente sobre el conjunto etiquetado (spec 014, T066, T072).

Cada consulta corre en un hilo nuevo; las repreguntas elípticas (``follow_up_of``) corren en el hilo
de su pregunta previa, después de ella (SC-006). Se mide por variante:

- validez de citas (SC-003): toda respuesta factual cita o declara falta de evidencia;
- abstención fuera de corpus: termina sin buscar (ruta ``out_of_scope``) o con fallo de evidencia;
- repreguntas correctas (SC-006): ruta no ``clarify``, respuesta con citas y alguna unidad esperada
  entre los fragmentos recuperados;
- acierto de evidencia en consultas documentales (alguna unidad esperada recuperada);
- latencia media y p95 (con calentamiento), share < 10 s (SC-007) y llamadas al modelo y a
  herramientas;
- opcional: juez LLM (fidelidad y relevancia) y precisión de contexto con referencia (``judge.py``).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..rag.evaluate import percentile
from .judge import JudgeScores, context_precision, judge_answer
from .service import ChatService

FACTUAL_ROUTES = frozenset({"documental", "structured"})
SECTION_START = "<!-- variants:start -->"
SECTION_END = "<!-- variants:end -->"
LATENCY_TARGET_MS = 10_000
WARMUP_QUESTION = "¿Qué produce Manuelita?"
CONTEXT_CHARS = 1_200


@dataclass(slots=True)
class QueryResult:
    query_id: str
    type: str
    question: str
    expected_route: str
    route: str
    status: str
    fallback: bool
    citations: int
    retrieved_unit_ids: list[str]
    expected_unit_ids: list[str]
    fact_ids: list[str]
    latency_ms: int
    model_calls: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    answer: str
    contexts: list[str] = field(default_factory=list)
    judge: JudgeScores | None = None

    @property
    def factual(self) -> bool:
        return self.route in FACTUAL_ROUTES

    @property
    def evidence_hit(self) -> bool:
        return bool(set(self.expected_unit_ids) & set(self.retrieved_unit_ids))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            key: getattr(self, key)
            for key in (
                "query_id",
                "type",
                "question",
                "expected_route",
                "route",
                "status",
                "fallback",
                "citations",
                "retrieved_unit_ids",
                "expected_unit_ids",
                "fact_ids",
                "latency_ms",
                "model_calls",
                "tool_calls",
                "input_tokens",
                "output_tokens",
                "answer",
            )
        }
        payload["judge"] = None if self.judge is None else self.judge.to_dict()
        return payload


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


@dataclass(slots=True)
class VariantReport:
    variant: str
    results: list[QueryResult]

    def metrics(self) -> dict[str, Any]:
        rows = self.results
        factual = [r for r in rows if r.factual]
        out = [r for r in rows if r.type == "out_of_corpus"]
        follow = [r for r in rows if r.type == "follow_up"]
        documental = [r for r in rows if r.type == "documental"]
        latencies = [float(r.latency_ms) for r in rows]
        judged = [r.judge for r in rows if r.judge is not None]
        precision = [
            context_precision(r.retrieved_unit_ids, r.expected_unit_ids)
            for r in rows
            if r.expected_unit_ids and r.retrieved_unit_ids
        ]
        return {
            "variant": self.variant,
            "queries": len(rows),
            "citation_validity": _rate(
                sum(r.citations > 0 or r.fallback for r in factual), len(factual)
            ),
            "answered_with_citations": _rate(
                sum(r.citations > 0 and not r.fallback for r in factual), len(factual)
            ),
            "out_of_corpus_abstention": _rate(
                sum(r.route == "out_of_scope" or r.fallback for r in out), len(out)
            ),
            "follow_up_correct": _rate(
                sum(r.route != "clarify" and r.citations > 0 and r.evidence_hit for r in follow),
                len(follow),
            ),
            "documental_evidence_hit": _rate(
                sum(r.evidence_hit for r in documental), len(documental)
            ),
            "latency_ms_mean": round(_mean(latencies)),
            "latency_ms_p95": round(percentile(latencies, 95)) if latencies else 0,
            "under_10s": _rate(sum(v < LATENCY_TARGET_MS for v in latencies), len(latencies)),
            "model_calls_mean": round(_mean([r.model_calls for r in rows]), 2),
            "tool_calls_mean": round(_mean([r.tool_calls for r in rows]), 2),
            "tokens_mean": round(_mean([r.input_tokens + r.output_tokens for r in rows])),
            "faithfulness": round(_mean([j.faithfulness for j in judged]), 3) if judged else None,
            "answer_relevancy": round(_mean([j.answer_relevancy for j in judged]), 3)
            if judged
            else None,
            "context_precision": round(_mean(precision), 3) if precision else None,
            "judged": len(judged),
        }


def load_queries(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line
    ]


def _contexts(service: ChatService, mode: str, turn: Any) -> list[str]:
    retriever = service.deps(mode).retriever
    texts: list[str] = []
    for fragment in turn.fragments:
        unit = retriever.units_by_id.get(fragment["unit_id"]) if retriever else None
        if unit is not None:
            texts.append(f"[{fragment['label']}] {unit.text[:CONTEXT_CHARS]}")
    store = service.deps(mode).store
    for row in turn.structured_rows:
        fact = store.get_fact(row["fact_id"]) if store is not None else None
        snippet = f" {fact.snippet}" if fact is not None else ""
        # Mismo texto que la herramienta entrega al modelo (``query_structured_impl``).
        fact_text = f"{row['subject_label']} · {row['attribute']} = {row['value']}."
        texts.append(f"[{row['label']}] {fact_text}{snippet}")
    return texts


def run_variant(
    service: ChatService,
    variant: str,
    queries: Sequence[dict[str, Any]],
    *,
    mode: str,
    user_id: str = "anon-eval",
    judge_model: Any = None,
    progress: Callable[[str], None] | None = None,
) -> VariantReport:
    """Ejecuta el conjunto en una variante (calentamiento descartado)."""
    service.send(WARMUP_QUESTION, user_id=user_id, variant=variant, mode=mode)
    ordered = [q for q in queries if not q.get("follow_up_of")] + [
        q for q in queries if q.get("follow_up_of")
    ]
    threads: dict[str, str] = {}
    results: dict[str, QueryResult] = {}
    for query in ordered:
        parent = query.get("follow_up_of")
        outcome = service.send(
            query["question"],
            thread_id=threads.get(parent) if parent else None,
            user_id=user_id,
            variant=variant,
            mode=mode,
        )
        threads[query["query_id"]] = outcome.thread_id
        turn = outcome.turn
        result = QueryResult(
            query_id=query["query_id"],
            type=query["type"],
            question=query["question"],
            expected_route=query["expected_route"],
            route=turn.route.route,
            status=outcome.status,
            fallback=turn.fallback,
            citations=len(turn.citations),
            retrieved_unit_ids=[f["unit_id"] for f in turn.fragments]
            + [r["unit_id"] for r in turn.structured_rows],
            expected_unit_ids=list(query.get("expected_unit_ids") or []),
            fact_ids=[r["fact_id"] for r in turn.structured_rows],
            latency_ms=turn.metrics.latency_ms,
            model_calls=turn.metrics.model_calls,
            tool_calls=turn.metrics.tool_calls,
            input_tokens=turn.metrics.input_tokens,
            output_tokens=turn.metrics.output_tokens,
            answer=turn.answer,
            contexts=_contexts(service, mode, turn),
        )
        if judge_model is not None and result.factual and not result.fallback and result.contexts:
            result.judge = judge_answer(
                result.question, result.answer, result.contexts, judge_model
            )
        results[query["query_id"]] = result
        if progress:
            progress(f"{variant} {query['query_id']} {result.route} {result.latency_ms} ms")
    return VariantReport(variant, [results[q["query_id"]] for q in queries])


def _fmt(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "—"
    if percent:
        return f"{value * 100:.0f} %"
    return f"{value}"


ROWS = (
    ("Validez de citas (SC-003)", "citation_validity", True),
    ("Respuestas factuales con cita", "answered_with_citations", True),
    ("Abstención fuera de corpus", "out_of_corpus_abstention", True),
    ("Repreguntas correctas (SC-006)", "follow_up_correct", True),
    ("Evidencia esperada recuperada (documentales)", "documental_evidence_hit", True),
    ("Latencia media (ms)", "latency_ms_mean", False),
    ("Latencia p95 (ms)", "latency_ms_p95", False),
    ("Respuestas < 10 s (SC-007)", "under_10s", True),
    ("Llamadas al modelo por consulta", "model_calls_mean", False),
    ("Búsquedas por consulta", "tool_calls_mean", False),
    ("Tokens por consulta", "tokens_mean", False),
    ("Fidelidad (juez LLM)", "faithfulness", False),
    ("Relevancia de la respuesta (juez LLM)", "answer_relevancy", False),
    ("Precisión de contexto (con referencia)", "context_precision", False),
)


def render_variants_section(reports: Sequence[VariantReport], *, run_id: str, mode: str) -> str:
    metrics = [report.metrics() for report in reports]
    header = "| Métrica | " + " | ".join(m["variant"] for m in metrics) + " |"
    lines = [
        SECTION_START,
        "## Cadena vs. agente (T066)",
        "",
        f"**Ejecución**: `{run_id}` · **Modo**: {mode} · **Consultas**: {metrics[0]['queries']} "
        "(cada una en un hilo nuevo; las 6 repreguntas en el hilo de su pregunta previa; "
        "una consulta de calentamiento descartada)",
        "",
        header,
        "|---" * (len(metrics) + 1) + "|",
    ]
    for label, key, percent in ROWS:
        lines.append(
            f"| {label} | " + " | ".join(_fmt(m[key], percent=percent) for m in metrics) + " |"
        )
    judged = ", ".join(f"{m['variant']} {m['judged']}" for m in metrics)
    lines += [
        "",
        f"Respuestas evaluadas por el juez: {judged}. El juez usa `prompts/judge.md` con las "
        "definiciones de Ragas (fidelidad = afirmaciones respaldadas / afirmaciones; "
        "relevancia = qué tan directamente responde); la precisión de contexto usa las unidades "
        "esperadas como referencia.",
        "",
        "Repreguntas por variante:",
        "",
        "| Consulta | " + " | ".join(m["variant"] for m in metrics) + " |",
        "|---" * (len(metrics) + 1) + "|",
    ]
    follow_ids = [r.query_id for r in reports[0].results if r.type == "follow_up"]
    for query_id in follow_ids:
        cells = []
        for report in reports:
            row = next(r for r in report.results if r.query_id == query_id)
            ok = row.route != "clarify" and row.citations > 0 and row.evidence_hit
            cells.append(f"{'✅' if ok else '❌'} {row.route}, {row.citations} citas")
        question = next(r.question for r in reports[0].results if r.query_id == query_id)
        lines.append(f"| {query_id} «{question}» | " + " | ".join(cells) + " |")
    lines += ["", SECTION_END]
    return "\n".join(lines)


def write_section(report_path: Path, section: str) -> None:
    text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    if SECTION_START in text and SECTION_END in text:
        before = text.split(SECTION_START)[0]
        after = text.split(SECTION_END, 1)[1]
        text = before + section + after
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    report_path.write_text(text, encoding="utf-8")
