"""Gestión del contexto en conversaciones largas (rúbrica del Módulo 2, ítem 1.2)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent.demo import DemoChatModel
from proyecto_modelos_lenguaje.agent.graph import GraphDeps, _agent_messages, _chain_user_message
from proyecto_modelos_lenguaje.agent.memory import (
    cap_summary,
    compact_history,
    estimate_tokens,
    recent_within_budget,
    summary_budget,
)
from tests.agent_helpers import agent_config

LONG_ANSWER = "Manuelita produce azúcar, bioetanol y energía renovable en el Valle del Cauca. " * 60


def _turns(count: int) -> list[dict[str, object]]:
    return [
        {
            "turn_id": index,
            "question": f"Pregunta número {index} sobre la historia y los productos de Manuelita",
            "answer": LONG_ANSWER,
            "citations": [{"url": f"https://www.manuelita.com/{index}"}],
        }
        for index in range(1, count + 1)
    ]


def _state_after(count: int) -> dict[str, object]:
    config = agent_config()
    turns = _turns(count)
    summary, summarized = "", 0
    # Simula el nodo «finalize» turno a turno: compacta cada vez que se supera el umbral.
    for size in range(1, count + 1):
        summary, summarized = compact_history(
            turns[:size], summary, summarized, config.memory, None
        )
    return {
        "question": "¿Y qué más produce?",
        "turns": turns,
        "summary": summary,
        "summarized": summarized,
        "context": "",
    }


def test_fifty_long_turns_keep_the_chain_prompt_under_the_window() -> None:
    # Arrange
    config = agent_config()
    deps = GraphDeps(config, None, None, DemoChatModel())
    state = _state_after(50)
    window = config.memory.summarize_after_tokens

    # Act
    prompt = _chain_user_message(state, deps)  # type: ignore[arg-type]

    # Assert: resumen acotado + turnos recientes recortados por tokens.
    assert estimate_tokens(prompt) <= window + summary_budget(config.memory)
    assert estimate_tokens(str(state["summary"])) <= summary_budget(config.memory)
    assert "Pregunta número 50" in prompt


def test_fifty_long_turns_keep_the_agent_messages_under_the_window() -> None:
    # Arrange
    config = agent_config()
    deps = GraphDeps(config, None, None, DemoChatModel())
    state = _state_after(50)

    # Act
    messages = _agent_messages(state, deps)  # type: ignore[arg-type]
    total = sum(estimate_tokens(str(message.content)) for message in messages)

    # Assert
    assert total <= config.memory.summarize_after_tokens + summary_budget(config.memory)


def test_recent_turns_are_trimmed_by_tokens_and_start_with_the_user() -> None:
    # Arrange
    turns = _turns(10)

    # Act
    kept = recent_within_budget(turns, max_tokens=2500)

    # Assert
    assert 0 < len(kept) < len(turns)
    assert kept[-1]["turn_id"] == 10


def test_summary_cap_keeps_the_most_recent_lines() -> None:
    # Arrange
    summary = "\n".join(f"- turno {index}: {'dato ' * 40}" for index in range(200))

    # Act
    capped = cap_summary(summary, max_tokens=300)

    # Assert
    assert estimate_tokens(capped) <= 300
    assert capped.splitlines()[-1].startswith("- turno 199")
