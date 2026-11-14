"""Extracción robusta del perfil (rúbrica del Módulo 2, ítem 1.3): regex + LLM con Pydantic."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.actions import (
    detect_write_intent,
    extract_profile,
    extract_profile_llm,
    is_profile_question,
)
from tests.agent_helpers import ScriptedModel


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Me llamo Ana y trabajo en Carvajal", {"name": "Ana", "workplace": "Carvajal"}),
        ("Soy Ana, laboro en Carvajal", {"name": "Ana", "workplace": "Carvajal"}),
        (
            "Hola, soy Pedro Pérez y mi empresa es Bancolombia",
            {"name": "Pedro Pérez", "workplace": "Bancolombia"},
        ),
        ("Soy ingeniera y vivo en Cali", {"city": "Cali"}),
        ("Soy de Palmira", {"city": "Palmira"}),
        ("Me desempeño como analista de datos", {"role": "analista de datos"}),
    ],
)
def test_regex_covers_common_variations(message: str, expected: dict[str, str]) -> None:
    assert extract_profile(message) == expected


@pytest.mark.parametrize(
    "question", ["¿Dónde laboro?", "¿Cuál es mi empresa?", "¿De dónde soy?", "¿A qué me dedico?"]
)
def test_profile_questions_are_recognized(question: str) -> None:
    assert is_profile_question(question)


def test_llm_extracts_what_the_regex_misses_with_validated_json() -> None:
    # Arrange
    model = ScriptedModel(
        reply='{"name": "Lucía", "workplace": "Ingenio Providencia", "role": null, "city": null}'
    )
    message = "Les escribe Lucía, actualmente estoy vinculada a Ingenio Providencia"

    # Act
    intent = detect_write_intent(message, model)

    # Assert
    assert extract_profile(message) == {}
    assert intent is not None and intent.tool == "save_profile"
    assert intent.args == {"name": "Lucía", "workplace": "Ingenio Providencia"}
    assert "<mensaje>" in str(model.seen[0][0].content)


def test_llm_output_that_is_not_json_is_ignored() -> None:
    # Arrange
    model = ScriptedModel(reply="No puedo ayudar con eso.")

    # Act / Assert
    assert extract_profile_llm(model, "estoy vinculada a Providencia y resido allá") == {}


def test_questions_never_call_the_llm_extractor() -> None:
    # Arrange
    model = ScriptedModel(reply='{"name": "X"}')

    # Act
    intent = detect_write_intent("¿Dónde trabajo?", model)

    # Assert
    assert intent is None
    assert model.seen == []
