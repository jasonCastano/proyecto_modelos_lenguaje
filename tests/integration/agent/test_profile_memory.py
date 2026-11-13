"""Memoria de largo plazo de perfil (rúbrica del Módulo 2, ítem 1.3 y caso 2).

«Me llamo Ana y trabajo en Carvajal» → aprobación humana → el dato vive en el Store
(``("users", user_id, "profile")``) y un hilo nuevo lo recupera con ``search``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.memory import (
    build_checkpointer,
    build_store,
    profile_namespace,
)
from tests.agent_helpers import make_service

VARIANTS = ["chain", "agent"]
USER = "anon-perfil"
INTRO = "Me llamo Ana y trabajo en Carvajal"


def _profile(store) -> dict[str, str]:
    return {item.key: item.value["value"] for item in store.search(profile_namespace(USER))}


@pytest.mark.parametrize("variant", VARIANTS)
def test_profile_is_saved_with_approval_and_recalled_in_a_new_thread(
    tmp_path: Path, variant: str
) -> None:
    # Arrange
    first = make_service(build_checkpointer(tmp_path), store=build_store(tmp_path))
    paused = first.send(INTRO, user_id=USER, variant=variant)

    # Act: se aprueba en un proceso nuevo y se pregunta en otro hilo
    restarted = make_service(build_checkpointer(tmp_path), store=build_store(tmp_path))
    restarted.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )
    fresh = restarted.send("¿Dónde trabajo?", user_id=USER, variant=variant)

    # Assert
    assert paused.status == "pending_approval"
    assert paused.pending_action["tool"] == "save_profile"
    assert paused.pending_action["args"] == {"name": "Ana", "workplace": "Carvajal"}
    assert _profile(restarted.store) == {"name": "Ana", "workplace": "Carvajal"}
    assert fresh.thread_id != paused.thread_id
    assert "Carvajal" in fresh.turn.answer and "largo plazo" in fresh.turn.answer
    assert fresh.turn.route.route == "direct"
    assert fresh.turn.metrics.tool_calls == 0
    assert restarted.preferences(USER)["profile"][0]["key"] == "name"


@pytest.mark.parametrize("variant", VARIANTS)
def test_rejected_profile_lives_only_in_the_thread(variant: str) -> None:
    # Arrange
    service = make_service()
    paused = service.send(INTRO, user_id=USER, variant=variant)
    service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="reject"
    )

    # Act
    same_thread = service.send(
        "¿Dónde trabajo?", thread_id=paused.thread_id, user_id=USER, variant=variant
    )
    other_thread = service.send("¿Dónde trabajo?", user_id=USER, variant=variant)

    # Assert
    assert _profile(service.store) == {}
    assert "Carvajal" in same_thread.turn.answer and "corto plazo" in same_thread.turn.answer
    assert other_thread.turn.answer.startswith("Todavía no sé")
    assert "plazo" not in other_thread.turn.answer


def test_forget_memory_also_clears_the_profile() -> None:
    # Arrange
    service = make_service()
    paused = service.send(INTRO, user_id=USER)
    service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )

    # Act
    forget = service.send("Olvida mis preferencias", thread_id=paused.thread_id, user_id=USER)
    done = service.resume(
        paused.thread_id, action_id=forget.pending_action["action_id"], decision="approve"
    )

    # Assert
    assert _profile(service.store) == {}
    assert "2 datos de tu perfil" in done.turn.answer


def test_mixed_route_retrieves_documents_in_the_chain() -> None:
    # Arrange
    service = make_service()

    # Act
    outcome = service.send(
        "Compara la meta del informe con cuántas toneladas produce Manuelita", user_id=USER
    )

    # Assert
    assert outcome.turn.route.route == "mixed"
    assert outcome.turn.metrics.tool_calls >= 1


def test_greeting_uses_the_stored_name() -> None:
    # Arrange
    service = make_service()
    paused = service.send(INTRO, user_id=USER)
    service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )

    # Act
    greeting = service.send("Hola, buenas tardes", user_id=USER)

    # Assert
    assert greeting.turn.answer.startswith("¡Hola, Ana!")
    assert greeting.turn.metrics.tool_calls == 0
