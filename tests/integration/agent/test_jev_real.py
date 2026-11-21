"""Gatekeeper Jev contra el servicio real de TypeSafe (spec 022). Requiere ``TYPESAFE_API_KEY``.

Excluida por defecto y en CI (marcador ``network``)::

    uv run pytest -o addopts="" -m network tests/integration/agent/test_jev_real.py
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.agent.config import load_agent_config
from proyecto_modelos_lenguaje.agent.jev import TypeSafeJevGate, health_check, read_api_key

pytestmark = pytest.mark.network

CASES = {
    "Buenas noches, ¿cómo estás?": "direct",
    "¿Qué hace la Fundación Manuelita por las comunidades?": "documental",
    "¿En qué año se fundó Manuelita?": "structured",
    "¿Quién ganó el partido de la selección anoche?": "out_of_scope",
}


@pytest.fixture(scope="module")
def config():
    if read_api_key() is None:
        pytest.skip("Falta TYPESAFE_API_KEY")
    return replace(load_agent_config().jev, enabled=True, timeout_seconds=10.0)


def test_health_check_confirms_the_pinned_version(config) -> None:
    result = health_check(config)
    assert result["ok"] is True, result["detail"]


@pytest.mark.parametrize(("question", "route"), CASES.items())
def test_real_routes(config, question: str, route: str) -> None:
    gate = TypeSafeJevGate(config, read_api_key() or "")
    outcome = gate.assess(question)
    assert outcome.status == "ok", outcome.reason
    assert outcome.decision is not None and outcome.decision.route == route
    assert outcome.model == config.model
