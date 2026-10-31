"""Contract tests for the task results and the versioned prompts (T020, T038–T039)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from proyecto_modelos_lenguaje.retrieval import GoldUnit
from proyecto_modelos_lenguaje.tasks import (
    FALLBACK_ANSWER,
    SCHEMA_VERSION,
    Citation,
    FAQItem,
    TaskResult,
    load_prompt,
)
from tests.tasks_helpers import make_units

SPECS = Path(__file__).resolve().parents[2] / "specs" / "007-langchain-qa-tasks" / "contracts"
TASK_SCHEMA = SPECS / "task-result.schema.json"
FAQ_SCHEMA = SPECS / "faq-item.schema.json"


def _validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


def _citation() -> Citation:
    unit = GoldUnit.from_dict(make_units()[4])
    return Citation.from_unit("U1", unit)


def _base_result(**overrides: object) -> TaskResult:
    payload: dict[str, object] = {
        "task": "qa",
        "status": "ok",
        "answer": "Manuelita produce azúcar [U1].",
        "citations": (_citation(),),
        "used_unit_ids": (_citation().unit_id,),
        "omitted_unit_ids": (),
        "prompt_version": "1.0",
        "prompt_sha256": "a" * 64,
        "model": "llama3.1:8b",
        "latency_seconds": 8.4,
        "input_tokens": 1200,
        "output_tokens": 180,
        "fallback": False,
        "review_required": False,
        "error": None,
    }
    payload.update(overrides)
    return TaskResult(**payload)  # type: ignore[arg-type]


def test_schema_files_are_valid_json() -> None:
    for path in (TASK_SCHEMA, FAQ_SCHEMA):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_success_result_matches_schema() -> None:
    _validator(TASK_SCHEMA).validate(_base_result().to_dict())


def test_fallback_result_matches_schema() -> None:
    result = _base_result(
        status="fallback",
        answer=FALLBACK_ANSWER,
        citations=(),
        used_unit_ids=(),
        input_tokens=0,
        output_tokens=0,
        fallback=True,
    )
    _validator(TASK_SCHEMA).validate(result.to_dict())


def test_error_result_matches_schema() -> None:
    result = _base_result(
        status="error",
        answer="No se pudo generar una respuesta con citas válidas.",
        citations=(),
        review_required=True,
        error="missing_citations",
    )
    _validator(TASK_SCHEMA).validate(result.to_dict())


def test_ok_result_without_citations_is_rejected_by_invariants() -> None:
    with pytest.raises(ValueError):
        _base_result(review_required=True, citations=(), status="ok")


def test_ready_faq_item_matches_schema() -> None:
    item = FAQItem(
        question="¿Qué productos ofrece Manuelita?",
        answer="Manuelita produce azúcar y etanol [U1].",
        citations=(_citation(),),
        topic_id="topic_productos",
        seed_id="faq_0000000000000001",
        coverage_item_id="I-01",
        status="ready",
        prompt_version="1.0",
        model="llama3.1:8b",
    )
    _validator(FAQ_SCHEMA).validate(item.to_dict())


def test_missing_evidence_faq_item_matches_schema() -> None:
    item = FAQItem(
        question="¿Qué premios internacionales ha recibido Manuelita?",
        answer=FALLBACK_ANSWER,
        citations=(),
        topic_id="topic_identidad",
        seed_id=None,
        coverage_item_id=None,
        status="missing_evidence",
        prompt_version="1.0",
        model="llama3.1:8b",
    )
    payload = item.to_dict()
    _validator(FAQ_SCHEMA).validate(payload)
    assert payload["schema_version"] == SCHEMA_VERSION


@pytest.mark.parametrize("task", ["qa", "summary", "faq"])
def test_prompt_sections_satisfy_the_contract(task: str) -> None:
    prompt = load_prompt(task)
    assert set(prompt.sections) == {"rol", "tarea", "contexto", "reglas", "formato", "fallback"}
    assert "<context>" in prompt.text or "{{context}}" in prompt.text
    if task == "qa":
        assert "No hay evidencia suficiente" in prompt.sections["fallback"]
        assert "conocimiento externo" in prompt.sections["reglas"].lower()
