"""Spec 024 (US5, T067): las 30 consultas fijas del Módulo 3 son válidas y trazables."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.rag import __main__ as rag_cli
from proyecto_modelos_lenguaje.rag.evaluate import (
    MODULE2_BASELINE,
    EvaluationRun,
    ModeMetrics,
    compare_with_baseline,
    load_module2_baseline,
    load_questions,
    per_query_results,
)

FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "rag"
QUERIES = FIXTURES / "module3_queries.jsonl"
SOURCE = FIXTURES / "eval_questions.jsonl"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_module3_queries_have_30_valid_entries() -> None:
    queries = _jsonl(QUERIES)
    source = {row["question_id"]: row for row in _jsonl(SOURCE)}
    assert len(queries) == 30
    assert len({query["id"] for query in queries}) == 30
    assert len({query["source_question_id"] for query in queries}) == 30
    for query in queries:
        assert query["question"].strip()
        assert len(query["expected_unit_ids"]) >= 1
        assert query["topic_id"]
        origin = source[query["source_question_id"]]
        assert origin["question"] == query["question"]
        assert origin["expected_unit_ids"] == query["expected_unit_ids"]


def test_module3_queries_load_as_scored_questions() -> None:
    questions = load_questions(QUERIES)
    assert len(questions) == 30
    assert all(question.scored for question in questions)


def test_sample_is_reproducible_with_seed_2026() -> None:
    spec = importlib.util.spec_from_file_location(
        "sample_module3_queries", PROJECT_ROOT / "scripts" / "sample_module3_queries.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.sample_queries(_jsonl(SOURCE), seed=2026, size=30) == _jsonl(QUERIES)


def _tmp_project(tmp_path: Path) -> Path:
    """Proyecto mínimo: oro de prueba y config que apunta al índice hash versionado."""
    gold = tmp_path / "data" / "gold"
    gold.mkdir(parents=True)
    (gold / "knowledge_units.jsonl").write_bytes((FIXTURES / "gold_sample.jsonl").read_bytes())
    config = (PROJECT_ROOT / "config" / "retrieval.toml").read_text(encoding="utf-8")
    index = (FIXTURES / "index").as_posix()
    qdrant = (tmp_path / "qdrant").as_posix()
    config = config.replace('path = "data/module2/index"', f'path = "{index}"')
    config = config.replace('path = "data/module2/qdrant"', f'path = "{qdrant}"')
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "retrieval.toml").write_text(config, encoding="utf-8")
    return tmp_path


def test_evaluate_queries_writes_module3_docs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("QDRANT_URL", raising=False)
    root = _tmp_project(tmp_path)
    code = rag_cli.main(
        [
            "evaluate",
            "--queries",
            str(QUERIES),
            "--embedder",
            "hash",
            "--vector-store",
            "numpy",
            "--warmup",
            "0",
            "--write-docs",
        ],
        project_root=root,
    )
    assert code == 0
    payload = json.loads((root / "docs" / "evaluacion_modulo3.json").read_text(encoding="utf-8"))
    assert payload["scored_questions"] == 30
    assert payload["comparison"]["baseline"]["recall_at_10"] == 0.6714
    assert set(payload["comparison"]["metrics"]) == {"recall_at_10", "ndcg_at_10", "mrr"}
    assert len(payload["per_query"]) == 30
    assert all(row["failed"] == (row["recall_at_10"] == 0) for row in payload["per_query"])
    assert "numpy" in payload["backend"]
    markdown = (root / "docs" / "evaluacion_modulo3.md").read_text(encoding="utf-8")
    assert "Módulo 3" in markdown and "línea base del Módulo 2" in markdown


def test_compare_with_baseline_deltas() -> None:
    run = EvaluationRun(
        run_id="t",
        questions=2,
        k_values=(10,),
        modes={
            "hybrid": ModeMetrics(
                mode="hybrid",
                recall_at_k={10: 0.7},
                mrr=0.4,
                citation_coverage=1.0,
                latency_mean_ms=1.0,
                latency_p95_ms=1.0,
                ndcg_at_10=0.5,
            )
        },
        baseline="lexical",
        verdict="",
        per_question={"hybrid": {"a": 1.0, "b": 0.0}},
        per_question_recall={"hybrid": {"a": 1.0, "b": 0.0}},
    )
    comparison = compare_with_baseline(run, MODULE2_BASELINE)
    assert comparison["metrics"]["recall_at_10"]["delta"] == round(0.7 - 0.6714, 4)
    assert comparison["metrics"]["mrr"]["delta"] < 0
    assert comparison["not_worse"] is False
    assert [row["failed"] for row in per_query_results(run)] == [False, True]
    assert load_module2_baseline(PROJECT_ROOT / "docs" / "evaluacion_qdrant.json")["mrr"] == 0.4499
