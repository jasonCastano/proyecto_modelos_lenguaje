"""Pruebas de la memoria corta del agente (T037, FR-007, FR-008)."""

from __future__ import annotations

from pathlib import Path

from langchain.agents.middleware import SummarizationMiddleware

from proyecto_modelos_lenguaje.agent.memory import (
    CHECKPOINT_FILE,
    build_checkpointer,
    build_summarization_middleware,
    needs_summary,
    summarize_turns,
)
from tests.agent_helpers import ScriptedModel, agent_config, make_service

URL = "https://www.manuelita.com/historia"


def _turn(question: str, answer: str = "Respuesta [U1].") -> dict:
    return {
        "question": question,
        "answer": answer,
        "citations": [{"label": "U1", "unit_id": "u1", "url": URL, "title": "Historia"}],
    }


def test_sqlite_checkpointer_survives_a_restart(tmp_path: Path) -> None:
    # Arrange
    first = make_service(build_checkpointer(tmp_path))
    thread_id = first.send("¿Qué produce Manuelita?").thread_id

    # Act: otro checkpointer sobre el mismo archivo simula reiniciar el proceso
    second = make_service(build_checkpointer(tmp_path))
    outcome = second.send("¿Y dónde lo produce?", thread_id=thread_id)

    # Assert
    assert (tmp_path / CHECKPOINT_FILE).is_file()
    assert outcome.turn.turn_id == 2
    assert [t["question"] for t in second.thread(thread_id)["turns"]] == [
        "¿Qué produce Manuelita?",
        "¿Y dónde lo produce?",
    ]


def test_threads_are_isolated() -> None:
    # Arrange
    service = make_service()

    # Act
    one = service.send("¿Qué produce Manuelita?").thread_id
    two = service.send("Hola").thread_id
    service.send("¿Y dónde lo produce?", thread_id=one)

    # Assert
    assert len(service.thread(one)["turns"]) == 2
    assert [t["question"] for t in service.thread(two)["turns"]] == ["Hola"]


def test_history_is_summarized_after_the_threshold_keeping_sources() -> None:
    # Arrange: umbral mínimo y dos mensajes recientes (un turno) sin resumir
    service = make_service(config=agent_config(summarize_after_tokens=1, keep_last_messages=2))
    thread_id = service.send("¿Qué produce Manuelita?").thread_id

    # Act
    service.send("¿Y dónde lo produce?", thread_id=thread_id)
    service.send("¿Qué hace la Fundación Manuelita?", thread_id=thread_id)
    view = service.thread(thread_id)

    # Assert: los turnos antiguos quedan en el resumen con sus URL; el último sigue completo
    assert sum(line.startswith("- ") for line in view["summary"].splitlines()) == 2
    assert "¿Qué produce Manuelita?" in view["summary"]
    first_sources = view["turns"][0]["sources"]
    assert first_sources and first_sources[0] in view["summary"]
    assert len(view["turns"]) == 3


def test_summary_prompt_carries_previous_summary_and_citation_urls() -> None:
    # Arrange
    model = ScriptedModel(reply="- Historia: fundada en 1864 (fuente: URL)", seen=[])

    # Act
    summary = summarize_turns("- Tema previo", [_turn("¿Cuándo se fundó?")], model)

    # Assert
    prompt = str(model.seen[0][0].content)
    assert summary.startswith("- Historia")
    assert "Resumen previo:\n- Tema previo" in prompt
    assert URL in prompt
    assert "<conversacion>" in prompt


def test_no_summary_below_threshold_or_with_few_turns() -> None:
    # Arrange
    memory = agent_config().memory

    # Act / Assert
    assert needs_summary([_turn("a"), _turn("b")], 0, memory) is False
    assert needs_summary([_turn("x" * 30_000)] * 4, 0, memory) is True


def test_summarization_middleware_uses_the_versioned_prompt() -> None:
    # Act
    middleware = build_summarization_middleware(agent_config().memory, ScriptedModel(seen=[]))

    # Assert
    assert isinstance(middleware, SummarizationMiddleware)
    assert "{messages}" in middleware.summary_prompt
    assert "Resumen de memoria" in middleware.summary_prompt
