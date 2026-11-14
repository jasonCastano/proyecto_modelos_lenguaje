"""Identidad por correo de Valer-IA (spec 018, contracts/identity-flow.md)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.identity import (
    KEY_ENV,
    IdentityKeyError,
    IdentityRegistry,
    detect_identity_event,
    extract_name,
    fingerprint,
    load_key,
    looks_like_name,
    mask_email,
    names_match,
    normalize_email,
)
from proyecto_modelos_lenguaje.agent.memory import memory_store

KEY = "k" * 40


def test_normalization_fingerprint_and_mask() -> None:
    assert normalize_email(" Ana@Ejemplo.COM ") == "ana@ejemplo.com"
    first = fingerprint(KEY, "ana@ejemplo.com")
    assert len(first) == 64 and all(char in "0123456789abcdef" for char in first)
    assert fingerprint(KEY, " ANA@ejemplo.com") == first
    assert fingerprint("x" * 40, "ana@ejemplo.com") != first
    assert mask_email("ana@ejemplo.com") == "a***@ejemplo.com"


def test_key_from_env_or_generated_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Arrange / Act / Assert: variable de entorno
    monkeypatch.setenv(KEY_ENV, KEY)
    assert load_key(tmp_path) == KEY
    monkeypatch.setenv(KEY_ENV, "corta")
    with pytest.raises(IdentityKeyError):
        load_key(tmp_path)
    # Sin variable: se genera una vez y se reutiliza
    monkeypatch.delenv(KEY_ENV)
    generated = load_key(tmp_path)
    assert len(generated) >= 32
    assert (tmp_path / "identity.key").read_text(encoding="utf-8") == generated
    assert load_key(tmp_path) == generated


def test_registry_link_lookup_unlink() -> None:
    registry = IdentityRegistry(memory_store())
    fp = fingerprint(KEY, "ana@ejemplo.com")
    assert registry.lookup(fp) is None
    registry.link(fp, "anon-ana")
    assert registry.lookup(fp) == "anon-ana"
    assert registry.unlink_user("anon-ana") == 1
    assert registry.lookup(fp) is None


def test_failures_lock_and_expire() -> None:
    registry = IdentityRegistry(memory_store())
    fp = fingerprint(KEY, "ana@ejemplo.com")
    start = datetime(2026, 11, 14, 10, tzinfo=UTC)
    for minute in range(4):
        registry.record_failure(fp, now=start + timedelta(minutes=minute))
    assert not registry.is_locked(fp, now=start + timedelta(minutes=5))
    registry.record_failure(fp, now=start + timedelta(minutes=6))
    assert registry.is_locked(fp, now=start + timedelta(minutes=7))
    assert not registry.is_locked(fp, now=start + timedelta(hours=2))


@pytest.mark.parametrize(
    ("registered", "given", "expected"),
    [("Ana María", "ana", True), ("Ana", "Ána", True), ("Ana", "Pedro", False), ("Ana", "", False)],
)
def test_names_match(registered: str, given: str, expected: bool) -> None:
    assert names_match(registered, given) is expected


def test_name_helpers() -> None:
    assert extract_name("Me llamo ana maría") == "Ana María"
    assert extract_name("Ana") == "Ana"
    assert looks_like_name("Ana María")
    assert not looks_like_name("¿Qué produce Manuelita?")
    assert not looks_like_name("una frase con demasiadas palabras para ser un nombre")


def test_detect_identity_events() -> None:
    event = detect_identity_event("Hola, soy Ana y mi correo es ana@ejemplo.com", KEY)
    assert event is not None and event.kind == "email"
    assert event.fingerprint == fingerprint(KEY, "ana@ejemplo.com")
    assert event.masked == "a***@ejemplo.com"
    assert "ana@ejemplo.com" not in str(event.to_dict())
    # Correo ajeno o varios correos: no identifican
    assert detect_identity_event("el correo de mi jefe es jefe@ejemplo.com", KEY) is None
    assert detect_identity_event("ana@ejemplo.com y pedro@ejemplo.com", KEY) is None
    # Reinicio
    assert detect_identity_event("empecemos de nuevo", KEY).kind == "reset"
    assert detect_identity_event("soy otra persona", KEY).explicit is True
    not_me = detect_identity_event("No soy Ana", KEY)
    assert not_me.kind == "reset" and not_me.explicit is False
    assert detect_identity_event("no soy experto, ¿qué es el etanol?", KEY) is None
    # Sin clave no hay reconocimiento por correo
    assert detect_identity_event("ana@ejemplo.com", None) is None
