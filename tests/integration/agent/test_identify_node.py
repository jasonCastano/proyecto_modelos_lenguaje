"""Reconocimiento conversacional por correo en las dos variantes (spec 018, US2)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.identity import (
    IdentityRegistry,
    fingerprint,
    load_key,
)
from proyecto_modelos_lenguaje.agent.memory import memory_checkpointer, memory_store
from proyecto_modelos_lenguaje.agent.prompts import load_conduct
from tests.agent_helpers import ScriptedModel, make_service

VARIANTS = ["chain", "agent"]
EMAIL = "ana@ejemplo.com"


def _register_ana(service, variant: str) -> str:
    """Visitante nuevo que se presenta con correo y acepta que lo recuerden."""
    paused = service.send(f"Soy Ana y mi correo es {EMAIL}", user_id="anon-ana", variant=variant)
    assert paused.status == "pending_approval"
    assert paused.pending_action["tool"] == "remember_client"
    assert paused.pending_action["args"] == {"name": "Ana"}
    done = service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )
    assert done.turn.answer == load_conduct()["identity_saved"].replace("{name}", "Ana")
    assert done.client["recognized"] is True
    return paused.thread_id


@pytest.fixture()
def service():
    return make_service(memory_checkpointer(), store=memory_store())


@pytest.mark.parametrize("variant", VARIANTS)
def test_register_then_recognize_in_another_visit(service, variant: str) -> None:
    conduct = load_conduct()
    _register_ana(service, variant)
    registry = IdentityRegistry(service.store)
    assert registry.lookup(fingerprint(load_key(None), EMAIL)) == "anon-ana"

    # Otra visita (otro user_id, otro hilo)
    asked = service.send(f"hola, mi correo es {EMAIL}", user_id="anon-otra", variant=variant)
    assert asked.turn.answer == conduct["identity_confirm_name"]
    assert asked.client["masked_email"] == "a***@ejemplo.com"
    assert asked.client["user_id"] == "anon-otra"

    recognized = service.send(
        "Ana", thread_id=asked.thread_id, user_id="anon-otra", variant=variant
    )
    assert recognized.turn.answer == conduct["identity_recognized"].replace("{name}", "Ana")
    assert recognized.client == {
        "user_id": "anon-ana",
        "recognized": True,
        "name": "Ana",
        "reset": False,
        "masked_email": None,
    }
    # El siguiente turno ya usa el perfil del cliente reconocido
    greeting = service.send("Hola", thread_id=asked.thread_id, user_id="anon-otra", variant=variant)
    assert greeting.turn.answer == conduct["greeting_named"].replace("{name}", "Ana")


@pytest.mark.parametrize("variant", VARIANTS)
def test_wrong_name_reveals_nothing_and_limits_attempts(service, variant: str) -> None:
    conduct = load_conduct()
    _register_ana(service, variant)
    thread = None
    for _attempt in range(3):
        asked = service.send(
            f"mi correo es {EMAIL}", thread_id=thread, user_id="anon-intruso", variant=variant
        )
        thread = asked.thread_id
        assert asked.turn.answer == conduct["identity_confirm_name"]
        wrong = service.send("Pedro", thread_id=thread, user_id="anon-intruso", variant=variant)
        assert wrong.turn.answer == conduct["identity_neutral"]
        assert "Ana" not in wrong.turn.answer
        assert wrong.client["user_id"] == "anon-intruso"
    # Tras 3 fallos, el hilo ya no procesa correos
    blocked = service.send(f"{EMAIL}", thread_id=thread, user_id="anon-intruso", variant=variant)
    assert blocked.turn.answer == conduct["identity_neutral"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_locked_email_looks_like_a_new_one(service, variant: str) -> None:
    conduct = load_conduct()
    _register_ana(service, variant)
    registry = IdentityRegistry(service.store)
    fp = fingerprint(load_key(None), EMAIL)
    for _ in range(5):
        registry.record_failure(fp)
    asked = service.send(f"mi correo es {EMAIL}", user_id="anon-x", variant=variant)
    assert asked.turn.answer == conduct["identity_ask_name"]  # igual que un correo nuevo


@pytest.mark.parametrize("variant", VARIANTS)
def test_new_email_without_name_asks_and_can_be_declined(service, variant: str) -> None:
    conduct = load_conduct()
    asked = service.send(
        "me puedes recordar? luis@ejemplo.com", user_id="anon-luis", variant=variant
    )
    assert asked.turn.answer == conduct["identity_ask_name"]
    paused = service.send("Luis", thread_id=asked.thread_id, user_id="anon-luis", variant=variant)
    assert paused.pending_action["tool"] == "remember_client"
    declined = service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="reject"
    )
    assert declined.turn.answer == conduct["identity_declined"]
    assert (
        IdentityRegistry(service.store).lookup(fingerprint(load_key(None), "luis@ejemplo.com"))
        is None
    )


@pytest.mark.parametrize("variant", VARIANTS)
def test_reset_and_forget(service, variant: str) -> None:
    conduct = load_conduct()
    thread = _register_ana(service, variant)
    reset = service.send("No soy Ana", thread_id=thread, user_id="anon-ana", variant=variant)
    assert reset.turn.answer == conduct["identity_reset"]
    assert reset.client["reset"] is True
    # «No soy experto» no reinicia a un visitante anónimo
    other = service.send("No soy Pedro, ¿qué produce Manuelita?", user_id="anon-z", variant=variant)
    assert other.client["reset"] is False

    # Olvidar elimina también el vínculo del correo
    paused = service.send("Olvida mis datos", thread_id=thread, user_id="anon-ana", variant=variant)
    service.resume(
        paused.thread_id, action_id=paused.pending_action["action_id"], decision="approve"
    )
    assert IdentityRegistry(service.store).lookup(fingerprint(load_key(None), EMAIL)) is None


@pytest.mark.parametrize("variant", VARIANTS)
def test_model_never_sees_the_email(variant: str) -> None:
    model = ScriptedModel(reply="Manuelita produce azúcar [U1].")
    service = make_service(memory_checkpointer(), store=memory_store(), model=model)
    service.send(
        f"Soy Ana, mi correo es {EMAIL}. ¿Qué produce Manuelita?", user_id="a1", variant=variant
    )
    service.send(f"{EMAIL} ¿qué produce Manuelita?", user_id="a2", variant=variant)
    seen = " ".join(str(message.content) for call in model.seen for message in call)
    assert EMAIL not in seen
