"""Contrato del manifiesto del índice y de la traza de recuperación."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError

from proyecto_modelos_lenguaje.api_models import RetrievalTraceModel
from proyecto_modelos_lenguaje.rag.hybrid import RetrievalTrace, RetrievedFragment

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (
    PROJECT_ROOT / "specs" / "013-semantic-rag-chatbot" / "contracts" / "index-manifest.schema.json"
)
MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "index" / "manifest.json"


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_schema_is_valid() -> None:
    Draft202012Validator.check_schema(json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_fixture_manifest_matches_schema() -> None:
    _validator().validate(json.loads(MANIFEST.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "payload",
    [
        {
            "schema_version": 2,
            "model": "m",
            "dimension": 384,
            "normalize": True,
            "max_tokens": 512,
            "count": 0,
            "gold_sha256": "0" * 64,
            "created_at": "2026-11-06T00:00:00Z",
        },
        {
            "schema_version": 1,
            "model": "",
            "dimension": 384,
            "normalize": True,
            "max_tokens": 512,
            "count": 0,
            "gold_sha256": "0" * 64,
            "created_at": "2026-11-06T00:00:00Z",
        },
        {
            "schema_version": 1,
            "model": "m",
            "dimension": 0,
            "normalize": True,
            "max_tokens": 512,
            "count": 0,
            "gold_sha256": "0" * 64,
            "created_at": "2026-11-06T00:00:00Z",
        },
        {
            "schema_version": 1,
            "model": "m",
            "dimension": 384,
            "normalize": True,
            "max_tokens": 512,
            "count": 0,
            "gold_sha256": "xyz",
            "created_at": "2026-11-06T00:00:00Z",
        },
    ],
)
def test_invalid_manifests_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _validator().validate(payload)


def _fragment(unit_id: str, score: float, status: str = "used", reason: str | None = None):
    return RetrievedFragment(
        unit_id=unit_id,
        title="Título",
        url="https://example.com",
        score=score,
        semantic_score=score,
        lexical_score=None,
        origin="semantic",
        status=status,
        reason=reason,
    )


def test_trace_used_ids_match_used_fragments() -> None:
    trace = RetrievalTrace(
        mode="semantic",
        semantic_available=True,
        candidates=2,
        threshold=0.3,
        fragments=(
            _fragment("u1", 0.9),
            _fragment("u2", 0.2, status="omitted_threshold", reason="bajo umbral"),
        ),
        notes=(),
        elapsed_ms=1.5,
    )

    assert trace.used_unit_ids == ("u1",)
    assert trace.omitted_unit_ids == ("u2",)
    payload = trace.to_dict()
    assert payload["used_unit_ids"] == ["u1"]


def test_trace_requires_descending_scores() -> None:
    with pytest.raises(ValueError):
        RetrievalTrace(
            mode="semantic",
            semantic_available=True,
            candidates=2,
            threshold=0.3,
            fragments=(_fragment("u1", 0.1), _fragment("u2", 0.9)),
            notes=(),
            elapsed_ms=1.0,
        )


def test_omitted_fragment_requires_reason() -> None:
    with pytest.raises(ValueError):
        _fragment("u1", 0.1, status="omitted_budget")


def _api_trace(used_unit_ids: list[str]) -> RetrievalTraceModel:
    return RetrievalTraceModel(
        mode="semantic",
        semantic_available=True,
        candidates=1,
        threshold=0.3,
        fragments=[
            {
                "unit_id": "u1",
                "title": "Título",
                "url": "",
                "score": 0.9,
                "semantic_score": 0.9,
                "lexical_score": None,
                "origin": "semantic",
                "status": "used",
                "reason": None,
            }
        ],
        used_unit_ids=used_unit_ids,
        notes=[],
        elapsed_ms=1.0,
    )


def test_api_trace_accepts_consistent_used_ids() -> None:
    assert _api_trace(["u1"]).used_unit_ids == ["u1"]


def test_api_trace_rejects_inconsistent_used_ids() -> None:
    with pytest.raises(PydanticValidationError):
        _api_trace(["u2"])
