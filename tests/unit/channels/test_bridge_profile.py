"""Perfiles en el canal WhatsApp (spec 025 y spec 028: planificador abierto, atajo oculto)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.config import ChannelsConfig
from proyecto_modelos_lenguaje.channels.bridge import ChannelBridge
from proyecto_modelos_lenguaje.channels.format import to_whatsapp
from proyecto_modelos_lenguaje.channels.store import ChannelStore
from tests.unit.channels.test_bridge import SALT, Clock, FakeService, msg


@pytest.fixture()
def service() -> FakeService:
    return FakeService()


@pytest.fixture()
def bridge(tmp_path: Path, service: FakeService) -> ChannelBridge:
    store = ChannelStore(tmp_path / "channels.sqlite3", clock=Clock())
    return ChannelBridge(
        service,
        store,
        ChannelsConfig(),
        salt=SALT,
        mode="demo",
        log_dir=tmp_path / "logs",
        workspace=tmp_path / "workspace",
    )


@pytest.fixture(autouse=True)
def no_planners(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("VALERIA_PLANNERS", "MANUELITA_PLANNER_OPEN", "MANUELITA_PLANNER_WEB"):
        monkeypatch.delenv(var, raising=False)


def test_list_profiles_marks_the_active_one(bridge: ChannelBridge, service: FakeService) -> None:
    reply = bridge.handle(msg("/perfil", "m1"))
    text = "\n".join(reply.messages)
    for key in ("visitante", "cliente", "proveedor", "colaborador", "planificador"):
        assert f"• {key}" in text
    assert "visitante — Visitante ✅" in text and "solo autorizados" not in text
    assert "/perfil" not in text  # el atajo no se anuncia
    assert service.calls == []  # no llama al agente


def test_activate_profile_applies_on_next_turn(bridge: ChannelBridge, service: FakeService) -> None:
    reply = bridge.handle(msg("/perfil proveedor", "m1"))
    bridge.handle(msg("¿Qué apoyo dan a los proveedores?", "m2"))
    bridge.handle(msg("¿y el control biológico?", "m3"))
    assert "ahora te atiendo como Proveedor" in reply.messages[0]
    assert service.calls[0]["profile"] == "proveedor" and service.calls[0]["channel"] == "whatsapp"
    assert "profile" not in service.calls[1]  # el hilo ya lo conserva


def test_alias_b2b_and_unknown(bridge: ChannelBridge, service: FakeService) -> None:
    bridge.handle(msg("/perfil b2b", "m1"))
    unknown = bridge.handle(msg("/perfil gerente", "m2"))
    bridge.handle(msg("hola", "m3"))
    assert "No conozco ese perfil" in unknown.messages[0]
    assert service.calls[0]["profile"] == "cliente"


def test_planner_is_open_on_whatsapp(bridge: ChannelBridge, service: FakeService) -> None:
    """Spec 028 (D3): cualquier persona usa el planificador en WhatsApp, sin autorización."""
    reply = bridge.handle(msg("/perfil planificador", "m1"))
    bridge.handle(msg("Tenemos 15 % menos caña", "m2"))
    assert "Planificador industrial" in reply.messages[0] and reply.event is None
    assert service.calls[0]["profile"] == "planificador"


def test_trace_shows_profile(bridge: ChannelBridge) -> None:
    bridge.handle(msg("¿Qué produce Manuelita?", "m1"))
    trace = bridge.handle(msg("/traza", "m2"))
    assert "*Perfil:* Visitante" in trace.messages[0]


def test_synthetic_sources_are_listed_apart() -> None:
    messages = to_whatsapp(
        "Plan [S1] y dato público [U1].",
        [
            {"label": "S1", "title": "PO-01 · Prioridad", "url": "", "kind": "synthetic"},
            {"label": "U1", "title": "Informe", "url": "https://manuelita.com"},
        ],
    )
    text = "\n".join(messages)
    assert "Fuentes:\n[2] Informe" in text
    assert "Fuentes sintéticas (demostración):\n[1] PO-01" in text
