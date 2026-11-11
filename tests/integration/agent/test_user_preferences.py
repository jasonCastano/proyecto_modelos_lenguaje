"""Preferencias aplicadas entre hilos y sin datos personales persistidos (US5)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.memory import memory_checkpointer, memory_store
from tests.agent_helpers import ScriptedModel, make_service

USER = "anon-prefs"


def _save_bullets(service, variant: str) -> None:
    paused = service.send("Prefiero respuestas en viñetas", user_id=USER, variant=variant)
    service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_preference_applies_in_another_thread_and_stops_after_forgetting(variant: str) -> None:
    # Arrange
    service = make_service(memory_checkpointer(), store=memory_store())
    _save_bullets(service, variant)

    # Act: otro hilo del mismo usuario
    with_pref = service.send("¿Qué produce Manuelita?", user_id=USER, variant=variant)
    forget = service.send(
        "Olvida mis preferencias", thread_id=with_pref.thread_id, user_id=USER, variant=variant
    )
    service.resume(
        with_pref.thread_id, action_id=forget.pending_action["action_id"], decision="approve"
    )
    without = service.send("¿Qué produce Manuelita?", user_id=USER, variant=variant)

    # Assert: el modo demo responde en viñetas solo mientras la preferencia existe
    assert with_pref.turn.answer.splitlines()[1].startswith("- ")
    assert "\n- " not in without.turn.answer
    assert service.preferences(USER)["items"] == []


def test_preferences_reach_the_system_prompt() -> None:
    # Arrange
    store = memory_store()
    _save_bullets(make_service(memory_checkpointer(), store=store), "chain")
    model = ScriptedModel(reply="Manuelita produce azúcar [U1].", seen=[])
    service = make_service(memory_checkpointer(), store=store, model=model)

    # Act
    service.send("¿Qué produce Manuelita?", user_id=USER)

    # Assert
    system = str(model.seen[0][0].content)
    assert "## Preferencias declaradas por el usuario" in system
    assert "- formato de respuesta: viñetas" in system


def test_personal_data_is_never_persisted_in_the_thread() -> None:
    # Arrange
    service = make_service()

    # Act
    outcome = service.send("Hola, mi correo es ana.perez@correo.com y mi celular 3105551234")
    view = service.thread(outcome.thread_id)

    # Assert
    stored = str(view["turns"])
    assert "ana.perez@correo.com" not in stored
    assert "3105551234" not in stored
    assert "[REDACTED_EMAIL]" in view["turns"][0]["question"]
