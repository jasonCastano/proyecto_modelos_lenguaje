"""Perfiles en el grafo: autopresentación, «recuerda mi perfil» y herramientas por perfil
(spec 025, T037, US2)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.memory import memory_store, preferences_namespace
from proyecto_modelos_lenguaje.agent.profiles import get_profile
from tests.agent_helpers import make_service

USER = "anon-profile"
WRITES = {
    "save_profile",
    "save_preference",
    "forget_memory",
    "export_conversation",
    "request_human_contact",
}


@pytest.fixture(autouse=True)
def no_planners(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("VALERIA_PLANNERS", "MANUELITA_PLANNER_OPEN", "MANUELITA_PLANNER_WEB"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_self_introduction_activates_profile_and_offers_to_remember(variant: str) -> None:
    service = make_service(store=memory_store())
    first = service.send(
        "Soy proveedor de caña, ¿qué apoyo dan a los proveedores?", user_id=USER, variant=variant
    )
    second = service.send(
        "¿Y qué hacen con el compost?", thread_id=first.thread_id, user_id=USER, variant=variant
    )
    assert first.turn.profile == "proveedor"
    assert "Te atiendo como Proveedor" in first.turn.answer
    assert "recuerda mi perfil" in first.turn.answer
    assert second.turn.profile == "proveedor"  # el hilo conserva el perfil
    assert "Te atiendo como" not in second.turn.answer


def test_remembered_profile_applies_in_a_new_thread() -> None:
    store = memory_store()
    store.put(
        preferences_namespace(USER),
        "audience",
        {"value": "colaborador", "created_at": "2026-11-24T00:00:00+00:00",
         "expires_at": "2099-01-01T00:00:00+00:00"},
    )  # fmt: skip
    service = make_service(store=store)
    outcome = service.send("¿Cómo reporto una situación ética?", user_id=USER, variant="agent")
    assert outcome.turn.profile == "colaborador"


@pytest.mark.parametrize("profile", ["cliente", "proveedor", "colaborador"])
def test_tools_stay_within_the_profile(profile: str) -> None:
    service = make_service(store=memory_store())
    outcome = service.send(
        "¿Qué produce Manuelita?", user_id=USER, variant="agent", profile=profile
    )
    allowed = set(get_profile(profile).tools) | WRITES
    assert {tool["name"] for tool in outcome.turn.tools} <= allowed
    assert outcome.turn.profile == profile


def test_planner_profile_without_authorization_falls_back_to_visitor_in_thread() -> None:
    service = make_service(store=memory_store())
    first = service.send("¿Qué produce Manuelita?", user_id=USER, variant="agent")
    # Un hilo que traía «planificador» (p. ej. autorización retirada) atiende como visitante.
    service.graph("agent", "demo").update_state(
        {"configurable": {"thread_id": first.thread_id}}, {"profile": "planificador"}
    )
    second = service.send(
        "Tenemos 15 % menos caña esta semana, ¿cómo cumplimos los contratos?",
        thread_id=first.thread_id,
        user_id=USER,
        variant="agent",
    )
    assert second.turn.profile == "visitante" and second.turn.route.route != "planning"
    assert "solo para planificadores autorizados" in second.turn.answer
