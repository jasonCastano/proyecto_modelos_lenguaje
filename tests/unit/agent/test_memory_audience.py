"""Preferencia ``audience``: perfil recordado con aprobación (spec 025, T034, R15)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.actions import ActionArgsError, validate_args
from proyecto_modelos_lenguaje.agent.memory import (
    PREFERENCE_KEYS,
    PREFERENCE_LABELS,
    PreferenceError,
    UserMemory,
    memory_store,
)


def test_audience_is_a_closed_preference_key() -> None:
    assert "audience" in PREFERENCE_KEYS
    assert PREFERENCE_LABELS["audience"] == "perfil de atención"
    assert validate_args("save_preference", {"key": "audience", "value": "proveedor"})


def test_audience_value_is_resolved_and_validated() -> None:
    memory = UserMemory(memory_store(), ttl_days=30)
    saved = memory.save("u1", "audience", "B2B")
    assert saved.value == "cliente"
    with pytest.raises(PreferenceError, match="Perfil de atención inválido"):
        memory.save("u1", "audience", "gerente general")


def test_forget_removes_audience() -> None:
    memory = UserMemory(memory_store(), ttl_days=30)
    memory.save("u1", "audience", "colaborador")
    assert memory.forget("u1") >= 1
    assert memory.list("u1") == []


def test_other_keys_are_still_rejected() -> None:
    with pytest.raises(ActionArgsError):
        validate_args("save_preference", {"key": "perfil", "value": "proveedor"})
