"""Memoria larga por usuario: claves, longitud, PII y expiración (T060, FR-009, FR-010)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from proyecto_modelos_lenguaje.agent.memory import (
    PreferenceError,
    UserMemory,
    memory_store,
    preferences_namespace,
    render_preferences,
)
from proyecto_modelos_lenguaje.agent.privacy import build_pii_middleware, redact_pii

NOW = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture()
def memory() -> UserMemory:
    return UserMemory(memory_store(), ttl_days=30)


def test_preferences_live_in_the_user_namespace(memory: UserMemory) -> None:
    # Act
    memory.save("anon-1", "response_format", "viñetas", now=NOW)

    # Assert
    stored = memory.store.get(preferences_namespace("anon-1"), "response_format")
    assert preferences_namespace("anon-1") == ("users", "anon-1", "preferences")
    assert stored.value["value"] == "viñetas"
    assert memory.list("anon-2", now=NOW) == []


@pytest.mark.parametrize(
    ("key", "value"),
    [("color_favorito", "rojo"), ("response_format", ""), ("language", "x" * 201)],
)
def test_closed_key_list_and_length_limit(memory: UserMemory, key: str, value: str) -> None:
    # Act / Assert
    with pytest.raises(PreferenceError):
        memory.save("anon-1", key, value, now=NOW)


@pytest.mark.parametrize(
    ("value", "secret"),
    [
        ("escríbeme a ana.perez@correo.com", "ana.perez@correo.com"),
        ("llámame al 310 555 1234", "310 555 1234"),
        ("mi cédula es 1.144.123.456", "1.144.123.456"),
        ("pago con 4111 1111 1111 1111", "4111 1111 1111 1111"),
    ],
)
def test_personal_data_is_redacted_before_saving(
    memory: UserMemory, value: str, secret: str
) -> None:
    # Act
    item = memory.save("anon-1", "topics_of_interest", value, now=NOW)

    # Assert
    assert secret not in item.value
    assert "[REDACTED_" in item.value
    stored = memory.store.get(preferences_namespace("anon-1"), item.key).value
    assert secret not in str(stored)


def test_preferences_expire_after_the_ttl(memory: UserMemory) -> None:
    # Arrange
    item = memory.save("anon-1", "language", "inglés", now=NOW)

    # Act
    alive = memory.list("anon-1", now=NOW + timedelta(days=29))
    expired = memory.list("anon-1", now=NOW + timedelta(days=30, seconds=1))

    # Assert
    assert item.expires_at == (NOW + timedelta(days=30)).isoformat()
    assert [preference.key for preference in alive] == ["language"]
    assert expired == []
    assert memory.store.search(preferences_namespace("anon-1")) == []


def test_render_preferences_for_the_system_prompt(memory: UserMemory) -> None:
    # Arrange
    memory.save("anon-1", "language", "inglés", now=NOW)
    memory.save("anon-1", "response_format", "viñetas", now=NOW)

    # Act
    block = render_preferences(memory.list("anon-1", now=NOW))

    # Assert
    assert block.splitlines()[-2:] == ["- formato de respuesta: viñetas", "- idioma: inglés"]
    assert render_preferences([]) == ""


def test_redaction_keeps_business_figures() -> None:
    # Act / Assert
    assert redact_pii("Manuelita produjo 1.864 toneladas en 2023") == (
        "Manuelita produjo 1.864 toneladas en 2023"
    )
    assert len(build_pii_middleware()) == 4
