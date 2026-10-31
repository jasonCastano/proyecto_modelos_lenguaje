"""Contract tests for the web API payloads."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "specs" / "012-manuelita-rag-showcase" / "contracts"


def _schema(name: str) -> Draft202012Validator:
    payload = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return Draft202012Validator(payload)


def _citation() -> dict:
    return {
        "label": "U1",
        "title": "Manuelita — Productos",
        "url": "https://www.manuelita.com/manuelita-productos",
        "section_path": ["Productos"],
        "page": 3,
        "time_start": None,
        "authority": "first_party",
        "snippet": None,
    }


def _answer(status: str) -> dict:
    base = {
        "query_id": "q-1",
        "status": status,
        "answer": "Respuesta de prueba.",
        "citations": [_citation()] if status == "ok" else [],
        "model": "deepseek-flash",
        "provider": "deepseek",
        "prompt_version": "1.0",
        "latency_ms": 123.4,
        "input_tokens": 10,
        "output_tokens": 5,
        "cost_usd": None,
        "review_required": False,
    }
    if status == "error":
        base["error"] = {
            "code": "timeout",
            "message": "El proveedor tardó demasiado.",
            "retryable": True,
            "action": "reintentar",
        }
    return base


def test_answer_schema_accepts_ok_fallback_and_error() -> None:
    validator = _schema("answer.schema.json")
    for status in ("ok", "fallback", "error"):
        validator.validate(_answer(status))


def test_answer_schema_rejects_ok_without_citations() -> None:
    validator = _schema("answer.schema.json")
    payload = _answer("ok")
    payload["citations"] = []
    errors = list(validator.iter_errors(payload))
    assert errors


def test_showcase_schema_accepts_real_payload() -> None:
    validator = _schema("showcase.schema.json")
    payload = {
        "generated_at": "2026-10-31T15:00:00Z",
        "data_status": "complete",
        "sections": [
            {
                "id": "data",
                "order": 2,
                "title": "Corpus",
                "body": "Datos públicos.",
                "status": "done",
                "metrics": [],
                "evidence": [{"label": "Ficha", "href": "docs/data_card.md", "kind": "report"}],
            }
        ],
        "metrics": [
            {
                "key": "units",
                "label": "Unidades",
                "value": 15211,
                "unit": "unidades",
                "source": "data/gold/reports/2026-10-01/quality.json",
                "status": "complete",
            }
        ],
    }
    validator.validate(payload)
