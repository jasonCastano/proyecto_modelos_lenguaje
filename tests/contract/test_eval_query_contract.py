"""Contrato del conjunto etiquetado de la spec 014 (T017, FR-019)."""

from __future__ import annotations

import json
from collections import Counter

import jsonschema
import pytest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.rag.evaluate import load_questions

QUERIES = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "module2_queries.jsonl"
SCHEMA_PATH = (
    PROJECT_ROOT / "specs" / "014-rag-agent-memory-router" / "contracts" / "eval-query.schema.json"
)
ROWS = [json.loads(line) for line in QUERIES.read_text(encoding="utf-8").splitlines() if line]


@pytest.mark.parametrize("row", ROWS, ids=[row["query_id"] for row in ROWS])
def test_every_query_satisfies_the_schema(row: dict[str, object]) -> None:
    # Arrange
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # Act / Assert
    jsonschema.validate(row, schema)


def test_documental_requires_units_and_structured_requires_facts() -> None:
    # Arrange
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    documental = {"query_id": "r99", "question": "¿Qué?", "expected_route": "documental"}
    structured = {"query_id": "r98", "question": "¿Cuánto?", "expected_route": "structured"}

    # Act / Assert
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**documental, "type": "documental"}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**documental, "type": "documental", "expected_unit_ids": []}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**structured, "type": "structured"}, schema)


def test_distribution_matches_tasks_t018() -> None:
    # Act
    by_type = Counter(row["type"] for row in ROWS)
    base = [row for row in ROWS if row["type"] != "follow_up"]

    # Assert
    assert len(base) == 30
    assert by_type == {
        "greeting": 6,
        "documental": 12,
        "structured": 6,
        "out_of_corpus": 4,
        "ambiguous": 2,
        "follow_up": 6,
    }


def test_ids_are_unique_and_follow_ups_point_backwards() -> None:
    # Arrange
    ids = [row["query_id"] for row in ROWS]

    # Act
    follow_ups = [row for row in ROWS if row["type"] == "follow_up"]

    # Assert
    assert len(ids) == len(set(ids))
    for row in follow_ups:
        assert row["follow_up_of"] in ids
        assert ids.index(row["follow_up_of"]) < ids.index(row["query_id"])


def test_loader_scores_only_labeled_non_follow_up_queries() -> None:
    # Act
    questions = load_questions(QUERIES)

    # Assert
    assert sum(question.scored for question in questions) == 18
    assert sum(question.must_abstain for question in questions) == 4
