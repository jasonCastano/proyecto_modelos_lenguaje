"""Pruebas offline del evaluador del Módulo 1 (banco de preguntas, variantes y reporte)."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.module1_eval import (
    VARIANTS,
    EvalRow,
    main,
    parse_question_bank,
    render_report,
    run_evaluation,
    summarize,
)
from proyecto_modelos_lenguaje.retrieval import EntityIndex, GoldUnit
from proyecto_modelos_lenguaje.tasks import build_scripted_model, load_prompt
from tests.tasks_helpers import make_units, write_gold


def _row(**overrides: object) -> EvalRow:
    values: dict[str, object] = {
        "question_id": "P01",
        "variant": "final",
        "question": "¿Qué produce Manuelita?",
        "expected": "D",
        "status": "ok",
        "answer": "Azúcar [U1].",
        "citations": ["U1"],
        "sources": ["https://www.manuelita.com/"],
        "fallback": False,
        "latency_seconds": 1.0,
        "input_tokens": 10,
        "output_tokens": 5,
        "prompt_version": "1.0",
        "model": "scripted-fake",
    }
    values.update(overrides)
    return EvalRow(**values)  # type: ignore[arg-type]


def test_scope_bank_has_forty_approved_questions() -> None:
    questions = parse_question_bank(PROJECT_ROOT / "docs" / "alcance.md")
    assert len(questions) == 40
    assert [question.question_id for question in questions][:2] == ["P01", "P02"]
    assert next(q for q in questions if q.question_id == "P14").expects_fallback is True


def test_both_prompt_variants_load_with_mandatory_sections() -> None:
    prompts = {name: load_prompt("qa", path=path) for name, path in VARIANTS.items()}
    assert set(prompts) == {"zero_shot", "final"}
    assert prompts["zero_shot"].sha256 != prompts["final"].sha256
    assert "dato no confiable" not in prompts["zero_shot"].text
    assert "dato no confiable" in prompts["final"].text


def test_fallback_agreement_respects_expected_codes() -> None:
    assert _row(expected="D", fallback=False).fallback_matches is True
    assert _row(expected="X", fallback=False).fallback_matches is False
    assert _row(expected="X", fallback=True).fallback_matches is True
    assert _row(expected="P,X", fallback=True).fallback_matches is None
    assert _row(status="error").fallback_matches is None


def test_run_evaluation_records_both_variants_offline() -> None:
    questions = parse_question_bank(PROJECT_ROOT / "docs" / "alcance.md")[:2]
    prompts = {name: load_prompt("qa", path=path) for name, path in VARIANTS.items()}
    rows = run_evaluation(
        questions,
        model=build_scripted_model("qa"),
        prompts=prompts,
        units=[GoldUnit.from_dict(item) for item in make_units()],
        entity_index=EntityIndex(),
        project_root=PROJECT_ROOT,
    )
    assert [(row.question_id, row.variant) for row in rows] == [
        ("P01", "zero_shot"),
        ("P01", "final"),
        ("P02", "zero_shot"),
        ("P02", "final"),
    ]
    summary = summarize(rows)
    assert summary["final"]["questions"] == 2
    assert summary["zero_shot"]["error"] == 0


def test_report_leaves_human_columns_empty() -> None:
    rows = [_row(), _row(variant="zero_shot")]
    meta = {
        "run_id": "test",
        "created_at": "2026-11-07T00:00:00+00:00",
        "model": "scripted-fake",
        "mode": "demo",
        "command": "x",
        "json_path": "docs/evaluacion_modulo1.json",
    }
    report = render_report(rows, summarize(rows), meta)
    assert "| P01 | final | D | ok | U1 | Azúcar [U1]. |  |  |  |" in report
    assert "Corrección" in report and "Alucinación" in report


def test_cli_writes_report_and_json(tmp_path: Path) -> None:
    gold = write_gold(tmp_path)
    out, json_out = tmp_path / "eval.md", tmp_path / "eval.json"
    code = main(
        [
            "--fake",
            "--limit",
            "2",
            "--gold-dir",
            str(gold),
            "--out",
            str(out),
            "--json-out",
            str(json_out),
            "--run-id",
            "test-run",
        ]
    )
    assert code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["meta"]["run_id"] == "test-run"
    assert len(payload["rows"]) == 4
    assert out.read_text(encoding="utf-8").startswith("# Evaluación del Módulo 1")
