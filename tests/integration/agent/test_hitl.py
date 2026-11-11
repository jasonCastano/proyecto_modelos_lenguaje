"""Human-in-the-Loop para acciones de escritura (T054, FR-017, SC-009)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.memory import (
    build_checkpointer,
    build_store,
    memory_checkpointer,
    memory_store,
    preferences_namespace,
)
from proyecto_modelos_lenguaje.agent.service import ChatError
from tests.agent_helpers import make_service

VARIANTS = ["chain", "agent"]
PREFERENCE = "Prefiero respuestas en viñetas"
USER = "anon-hitl"


def _preferences(store) -> dict[str, str]:
    return {item.key: item.value["value"] for item in store.search(preferences_namespace(USER))}


@pytest.mark.parametrize("variant", VARIANTS)
def test_write_request_pauses_and_survives_a_restart(tmp_path: Path, variant: str) -> None:
    # Arrange
    first = make_service(build_checkpointer(tmp_path), store=build_store(tmp_path))
    paused = first.send(PREFERENCE, user_id=USER, variant=variant)

    # Act: otro proceso (checkpointer y Store nuevos sobre los mismos archivos) aprueba
    restarted = make_service(build_checkpointer(tmp_path), store=build_store(tmp_path))
    view = restarted.thread(paused.thread_id)
    resumed = restarted.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )

    # Assert
    assert paused.status == "pending_approval"
    assert paused.turn.answer == ""
    assert paused.pending_action["tool"] == "save_preference"
    assert paused.pending_action["args"] == {"key": "response_format", "value": "viñetas"}
    assert view["status"] == "pending_approval"
    assert resumed.status == "answered"
    assert "Guardé tu preferencia" in resumed.turn.answer
    assert _preferences(restarted.store) == {"response_format": "viñetas"}
    log = restarted.thread(paused.thread_id)["actions"]
    assert [(a["tool"], a["decision"]) for a in log] == [("save_preference", "approve")]


@pytest.mark.parametrize("variant", VARIANTS)
def test_reject_does_not_execute_and_is_recorded(variant: str) -> None:
    # Arrange
    service = make_service()
    paused = service.send(PREFERENCE, user_id=USER, variant=variant)

    # Act
    resumed = service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="reject"
    )

    # Assert
    assert _preferences(service.store) == {}
    assert "rechaz" in resumed.turn.answer
    view = service.thread(paused.thread_id)
    assert view["status"] == "idle"
    assert view["actions"][-1]["decision"] == "reject"


@pytest.mark.parametrize("variant", VARIANTS)
def test_edit_changes_the_arguments(variant: str) -> None:
    # Arrange
    service = make_service()
    paused = service.send(PREFERENCE, user_id=USER, variant=variant)
    action_id = paused.pending_action["action_id"]

    # Act
    service.resume(
        paused.thread_id,
        action_id=action_id,
        decision="edit",
        args={"key": "response_format", "value": "breve"},
    )

    # Assert
    assert _preferences(service.store) == {"response_format": "breve"}
    assert service.thread(paused.thread_id)["actions"][-1]["args"]["value"] == "breve"


def test_invalid_edits_and_mismatched_actions_are_rejected() -> None:
    # Arrange
    service = make_service()
    paused = service.send(PREFERENCE, user_id=USER)
    action_id = paused.pending_action["action_id"]

    # Act / Assert
    with pytest.raises(ChatError) as invalid:
        service.resume(paused.thread_id, action_id=action_id, decision="edit", args={"key": "x"})
    with pytest.raises(ChatError) as mismatch:
        service.resume(paused.thread_id, action_id="otra", decision="approve")
    with pytest.raises(ChatError) as busy:
        service.send("¿Qué produce Manuelita?", thread_id=paused.thread_id)
    assert (invalid.value.code, invalid.value.status_code) == ("invalid_args", 400)
    assert (mismatch.value.code, mismatch.value.status_code) == ("action_mismatch", 409)
    assert (busy.value.code, busy.value.status_code) == ("thread_pending_approval", 409)
    assert _preferences(service.store) == {}


def test_resume_without_pending_action_is_409() -> None:
    # Arrange
    service = make_service()
    thread_id = service.send("¿Qué produce Manuelita?").thread_id

    # Act / Assert
    with pytest.raises(ChatError) as error:
        service.resume(thread_id, action_id="act", decision="approve")
    assert error.value.code == "no_pending_action"


@pytest.mark.parametrize("variant", VARIANTS)
def test_reading_never_interrupts(variant: str) -> None:
    # Act
    outcome = make_service().send("¿Qué produce Manuelita?", variant=variant)

    # Assert
    assert outcome.status == "answered"
    assert outcome.pending_action is None


@pytest.mark.parametrize("variant", VARIANTS)
def test_forget_memory_and_export_after_approval(variant: str) -> None:
    # Arrange
    store = memory_store()
    store.put(preferences_namespace(USER), "language", {"value": "español"})
    service = make_service(memory_checkpointer(), store=store)
    thread_id = service.send("¿Qué produce Manuelita?", user_id=USER, variant=variant).thread_id

    # Act
    forget = service.send("Olvida mis preferencias", thread_id=thread_id, variant=variant)
    service.resume(thread_id, action_id=forget.pending_action["action_id"], decision="approve")
    export = service.send("Exporta la conversación", thread_id=thread_id, variant=variant)
    exported = service.resume(
        thread_id, action_id=export.pending_action["action_id"], decision="approve"
    )

    # Assert
    assert forget.pending_action["tool"] == "forget_memory"
    assert _preferences(store) == {}
    assert export.pending_action["tool"] == "export_conversation"
    assert "# Conversación con el asistente de Manuelita" in exported.turn.answer
    assert "¿Qué produce Manuelita?" in exported.turn.answer
