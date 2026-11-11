"""Pruebas de las acciones de escritura y su detección (T055, FR-017)."""

from __future__ import annotations

import json

import pytest

from proyecto_modelos_lenguaje.agent.actions import (
    ActionArgsError,
    detect_write_intent,
    execute_action,
    export_markdown,
    validate_args,
)
from proyecto_modelos_lenguaje.agent.memory import memory_store
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

QUERIES = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "module2_queries.jsonl"


@pytest.mark.parametrize(
    ("message", "tool", "args"),
    [
        ("Olvida mis preferencias, por favor", "forget_memory", {}),
        ("Borra lo que sabes de mí", "forget_memory", {}),
        ("Exporta la conversación", "export_conversation", {"format": "markdown"}),
        (
            "Prefiero respuestas en viñetas",
            "save_preference",
            {"key": "response_format", "value": "viñetas"},
        ),
        ("Respóndeme breve", "save_preference", {"key": "response_format", "value": "breve"}),
        (
            "Quiero que me respondas en inglés",
            "save_preference",
            {"key": "language", "value": "inglés"},
        ),
        (
            "Me interesa la sostenibilidad",
            "save_preference",
            {"key": "topics_of_interest", "value": "sostenibilidad"},
        ),
    ],
)
def test_detects_write_requests(message: str, tool: str, args: dict) -> None:
    # Act
    intent = detect_write_intent(message)

    # Assert
    assert intent is not None
    assert (intent.tool, intent.args) == (tool, args)


def test_evaluation_questions_never_trigger_writes() -> None:
    # Arrange
    questions = [
        json.loads(line)["question"]
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line
    ]

    # Act / Assert
    assert [q for q in questions if detect_write_intent(q) is not None] == []


def test_args_are_validated_against_the_tool_schema() -> None:
    # Act / Assert
    assert validate_args("save_preference", {"key": "language", "value": "inglés"}) == {
        "key": "language",
        "value": "inglés",
    }
    with pytest.raises(ActionArgsError):
        validate_args("save_preference", {"key": "color", "value": "rojo"})
    with pytest.raises(ActionArgsError):
        validate_args("forget_memory", {"user_id": "otro"})
    with pytest.raises(ActionArgsError):
        validate_args("borrar_todo", {})


def test_preferences_are_saved_with_expiry_and_forgotten() -> None:
    # Arrange
    store = memory_store()
    kwargs = {"store": store, "user_id": "anon-1", "turns": [], "ttl_days": 30}

    # Act
    saved = execute_action("save_preference", {"key": "language", "value": "inglés"}, **kwargs)
    item = store.get(("users", "anon-1", "preferences"), "language")
    forgot = execute_action("forget_memory", {}, **kwargs)

    # Assert
    assert "language = inglés" in saved
    assert item.value["value"] == "inglés" and item.value["expires_at"] > item.value["created_at"]
    assert forgot == "Olvidé 1 preferencias guardadas."
    assert store.search(("users", "anon-1", "preferences")) == []


def test_export_lists_questions_answers_and_sources() -> None:
    # Arrange
    turns = [
        {
            "turn_id": 1,
            "question": "¿Qué produce Manuelita?",
            "answer": "Azúcar [U1].",
            "sources": ["https://www.manuelita.com"],
        }
    ]

    # Act
    text = export_markdown(turns)

    # Assert
    assert "**Pregunta 1.** ¿Qué produce Manuelita?" in text
    assert "- Fuente: https://www.manuelita.com" in text
