"""Juez propio con definiciones de Ragas y comparación de variantes (T066, T067)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.compare import (
    SECTION_END,
    SECTION_START,
    render_variants_section,
    run_variant,
)
from proyecto_modelos_lenguaje.agent.judge import context_precision, judge_answer, parse_judgement
from tests.agent_helpers import ScriptedModel, make_service

QUERIES = [
    {"query_id": "r01", "question": "Hola", "expected_route": "direct", "type": "greeting"},
    {
        "query_id": "r09",
        "question": "¿Qué produce Manuelita?",
        "expected_route": "documental",
        "type": "documental",
        "expected_unit_ids": ["unit_f77f231c18db5855"],
    },
    {
        "query_id": "r25",
        "question": "¿Cuál es el precio del dólar hoy?",
        "expected_route": "out_of_scope",
        "type": "out_of_corpus",
    },
    {
        "query_id": "r31",
        "question": "¿Y dónde lo produce?",
        "expected_route": "documental",
        "type": "follow_up",
        "expected_unit_ids": ["unit_f77f231c18db5855"],
        "follow_up_of": "r09",
    },
]


def test_parse_judgement_recomputes_faithfulness_from_counts() -> None:
    # Act
    scores = parse_judgement(
        'Aquí va: {"claims": 4, "supported": 3, "faithfulness": 0.2, '
        '"answer_relevancy": 1.4, "unsupported": ["x"]}'
    )

    # Assert
    assert scores.faithfulness == 0.75
    assert scores.answer_relevancy == 1.0
    assert scores.unsupported == ("x",)
    with pytest.raises(ValueError):
        parse_judgement("sin json")


def test_judge_answer_renders_the_versioned_prompt() -> None:
    # Arrange
    model = ScriptedModel(
        reply='{"claims": 2, "supported": 2, "faithfulness": 1, "answer_relevancy": 0.8}', seen=[]
    )

    # Act
    scores = judge_answer("¿Qué produce?", "Azúcar [U1].", ["[U1] Produce azúcar."], model)

    # Assert
    prompt = str(model.seen[0][0].content)
    assert scores is not None and scores.faithfulness == 1.0
    assert "<contexto>\n[U1] Produce azúcar.\n</contexto>" in prompt
    assert judge_answer("q", "a", ["c"], ScriptedModel(reply="no", seen=[])) is None


@pytest.mark.parametrize(
    ("retrieved", "relevant", "expected"),
    [
        (["a", "b", "c"], ["a"], 1.0),
        (["x", "a", "y", "b"], ["a", "b"], (1 / 2 + 2 / 4) / 2),
        (["x", "y"], ["a"], 0.0),
    ],
)
def test_context_precision_with_reference(retrieved, relevant, expected) -> None:
    # Act / Assert
    assert context_precision(retrieved, relevant) == pytest.approx(expected)


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_run_variant_measures_the_labeled_set(variant: str) -> None:
    # Arrange
    service = make_service()
    judge = ScriptedModel(
        reply='{"claims": 1, "supported": 1, "faithfulness": 1, "answer_relevancy": 0.9}', seen=[]
    )

    # Act
    report = run_variant(service, variant, QUERIES, mode="demo", judge_model=judge)
    metrics = report.metrics()

    # Assert: orden original, repregunta en el hilo de su pregunta previa
    assert [r.query_id for r in report.results] == ["r01", "r09", "r25", "r31"]
    follow = report.results[3]
    assert follow.route == "documental" and follow.citations > 0
    assert metrics["citation_validity"] == 1.0
    assert metrics["out_of_corpus_abstention"] == 1.0
    assert metrics["judged"] == 2
    assert metrics["faithfulness"] == 1.0
    section = render_variants_section([report], run_id="t", mode="demo")
    assert section.startswith(SECTION_START) and section.endswith(SECTION_END)
    assert "r31 «¿Y dónde lo produce?»" in section
