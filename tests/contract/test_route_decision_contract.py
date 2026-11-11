"""Contrato de ``RouteDecision`` contra ``contracts/route-decision.schema.json`` (T015)."""

from __future__ import annotations

import json

import jsonschema
import pytest
from pydantic import ValidationError

from proyecto_modelos_lenguaje.agent.models import RouteDecision
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

CONTRACTS = PROJECT_ROOT / "specs" / "014-rag-agent-memory-router" / "contracts"
SCHEMA_PATH = CONTRACTS / "route-decision.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

VALID = [
    {"route": "direct", "confidence": 1.0, "reason": "saludo", "decided_by": "rules"},
    {
        "route": "structured",
        "confidence": 0.82,
        "reason": "pide una lista de países",
        "decided_by": "llm",
        "alternative": "documental",
        "fallback_route": "documental",
    },
    {"route": "clarify", "confidence": 0.4, "reason": "referencia ambigua", "decided_by": "demo"},
]

INVALID = [
    {"route": "documental", "confidence": 1.2, "reason": "x", "decided_by": "llm"},
    {"route": "documental", "confidence": 0.9, "reason": "x" * 201, "decided_by": "llm"},
    {"route": "web", "confidence": 0.9, "reason": "x", "decided_by": "llm"},
    {"route": "documental", "confidence": 0.9, "reason": "x", "decided_by": "llm", "extra": 1},
]


@pytest.mark.parametrize("payload", VALID)
def test_valid_payloads_satisfy_schema_and_model(payload: dict[str, object]) -> None:
    # Act
    decision = RouteDecision.model_validate(payload)
    serialized = decision.model_dump(mode="json")

    # Assert
    jsonschema.validate(serialized, SCHEMA)
    assert serialized["route"] == payload["route"]


@pytest.mark.parametrize("payload", INVALID)
def test_invalid_payloads_are_rejected_by_schema_and_model(payload: dict[str, object]) -> None:
    # Act / Assert
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, SCHEMA)
    with pytest.raises(ValidationError):
        RouteDecision.model_validate(payload)


def test_model_schema_enumerates_the_same_routes_as_the_contract() -> None:
    # Arrange
    model_schema = RouteDecision.model_json_schema()

    # Act
    model_routes = set(model_schema["properties"]["route"]["enum"])

    # Assert
    assert model_routes == set(SCHEMA["properties"]["route"]["enum"])


def test_low_confidence_becomes_clarify_and_keeps_alternative() -> None:
    # Arrange
    decision = RouteDecision(route="structured", confidence=0.45, reason="duda", decided_by="llm")

    # Act
    effective = decision.effective(min_confidence=0.6)

    # Assert
    assert effective.route == "clarify"
    assert effective.alternative == "structured"
    assert decision.effective(min_confidence=0.4).route == "structured"
