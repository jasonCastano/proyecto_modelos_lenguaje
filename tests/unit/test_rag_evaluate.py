"""Pruebas de las métricas de evaluación de recuperación."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.rag import evaluate as evaluate_module
from proyecto_modelos_lenguaje.rag.evaluate import (
    EvaluationQuestion,
    evaluate_questions,
    load_questions,
    render_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_FILE = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "eval_questions.jsonl"


QUESTIONS = (
    EvaluationQuestion("q1", "pregunta uno", ("u1",)),
    EvaluationQuestion("q2", "pregunta dos", ("u2",)),
    EvaluationQuestion("q3", "pregunta tres", ("u3",)),
    EvaluationQuestion("q4", "fuera de corpus", (), type="out_of_corpus"),
)

BY_TEXT = {question.question: question.question_id for question in QUESTIONS}

RANKINGS = {
    "q1": ["u1", "u9"],
    "q2": ["u9", "u2"],
    "q3": ["u9", "u8", "u7"],
    "q4": [],
}


def test_recall_mrr_and_coverage(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluate_module,
        "_rankings",
        lambda retriever, question, mode, **kwargs: RANKINGS[BY_TEXT[question]],
    )

    run = evaluate_questions(None, QUESTIONS, modes=("hybrid",), k_values=(1, 3, 5, 8))
    metrics = run.modes["hybrid"]

    assert metrics.recall_at_k[1] == pytest.approx(1 / 3)
    assert metrics.recall_at_k[3] == pytest.approx(2 / 3)
    assert metrics.recall_at_k[5] == pytest.approx(2 / 3)
    assert metrics.recall_at_k[8] == pytest.approx(2 / 3)
    assert metrics.mrr == pytest.approx(0.5)
    assert metrics.citation_coverage == pytest.approx(1.0)
    assert run.questions == 4


def test_out_of_corpus_with_evidence_is_an_error(monkeypatch) -> None:
    rankings = dict(RANKINGS)
    rankings["q4"] = ["u1"]
    monkeypatch.setattr(
        evaluate_module,
        "_rankings",
        lambda retriever, question, mode, **kwargs: rankings[BY_TEXT[question]],
    )

    run = evaluate_questions(None, QUESTIONS, modes=("hybrid",))

    assert any(error["question_id"] == "q4" for error in run.errors)


def test_verdict_compares_against_lexical(monkeypatch) -> None:
    mode_rankings = {
        "hybrid": RANKINGS,
        "lexical": {"q1": ["u9"], "q2": ["u9"], "q3": ["u9"], "q4": []},
    }
    monkeypatch.setattr(
        evaluate_module,
        "_rankings",
        lambda retriever, question, mode, **kwargs: mode_rankings[mode][BY_TEXT[question]],
    )

    run = evaluate_questions(None, QUESTIONS, modes=("lexical", "hybrid"))

    assert run.verdict.startswith("hybrid >= baseline")


def test_verdict_reports_regression(monkeypatch) -> None:
    mode_rankings = {
        "hybrid": {"q1": ["u9"], "q2": ["u9"], "q3": ["u9"], "q4": []},
        "lexical": RANKINGS,
    }
    monkeypatch.setattr(
        evaluate_module,
        "_rankings",
        lambda retriever, question, mode, **kwargs: mode_rankings[mode][BY_TEXT[question]],
    )

    run = evaluate_questions(None, QUESTIONS, modes=("lexical", "hybrid"))

    assert "NO supera" in run.verdict


def test_run_serializes_contract_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluate_module,
        "_rankings",
        lambda retriever, question, mode, **kwargs: RANKINGS[BY_TEXT[question]],
    )
    run = evaluate_questions(None, QUESTIONS, modes=("hybrid",))

    payload = run.to_dict()

    assert set(payload) == {
        "run_id",
        "questions",
        "k_values",
        "modes",
        "baseline",
        "verdict",
        "errors",
    }
    assert set(payload["modes"]["hybrid"]) == {
        "mode",
        "recall_at_k",
        "mrr",
        "citation_coverage",
        "latency_ms",
    }


def test_render_markdown_includes_modes_and_verdict(monkeypatch) -> None:
    monkeypatch.setattr(
        evaluate_module,
        "_rankings",
        lambda retriever, question, mode, **kwargs: RANKINGS[BY_TEXT[question]],
    )
    run = evaluate_questions(None, QUESTIONS, modes=("semantic", "lexical", "hybrid"))

    markdown = render_markdown(run, extra_notes=["nota de prueba"])

    assert "Recall@5" in markdown
    assert "semantic" in markdown
    assert run.verdict in markdown
    assert "nota de prueba" in markdown


def test_evaluation_fixture_has_required_distribution() -> None:
    questions = load_questions(EVAL_FILE)

    assert len(questions) >= 40
    types = {question.type for question in questions}
    assert types == {"paraphrase", "figure", "proper_noun", "english", "out_of_corpus"}
    assert sum(1 for question in questions if not question.expected_unit_ids) == 5
