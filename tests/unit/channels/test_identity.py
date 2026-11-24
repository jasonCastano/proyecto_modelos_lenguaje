"""Seudónimos y máscaras del remitente (spec 024, T013)."""

from __future__ import annotations

import re

import pytest

from proyecto_modelos_lenguaje.channels.identity import (
    SenderError,
    channel_salt,
    mask,
    normalize_sender,
    pseudonym,
)

SALT = "sal-de-prueba-0123456789"
USER_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def test_pseudonym_is_stable_and_valid() -> None:
    first = pseudonym("+573001234567", SALT)
    assert first == pseudonym("+573001234567", SALT)
    assert re.fullmatch(r"wa-[0-9a-f]{16}", first) and USER_ID.match(first)
    assert first != pseudonym("+573001234567", SALT + "x")
    assert first != pseudonym("+573001234568", SALT)


def test_jid_and_e164_give_the_same_pseudonym() -> None:
    assert pseudonym("573001234567@s.whatsapp.net", SALT) == pseudonym("+573001234567", SALT)
    assert normalize_sender("573001234567:12@s.whatsapp.net") == "+573001234567"


@pytest.mark.parametrize("bad", ["", "3001234567x", "+0123456789", "+57", "hola@s.whatsapp.net"])
def test_rejects_invalid_numbers(bad: str) -> None:
    with pytest.raises(SenderError):
        pseudonym(bad, SALT)


def test_mask_keeps_last_four_digits() -> None:
    assert mask("+573001234567") == "+57 ••• ••• 4567"


def test_telegram() -> None:
    assert re.fullmatch(r"tg-[0-9a-f]{16}", pseudonym("tg:123456", SALT, "telegram"))
    assert normalize_sender("123456", "telegram") == "tg:123456"
    with pytest.raises(SenderError):
        normalize_sender("abc", "telegram")


def test_salt_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALERIA_CHANNEL_SALT", raising=False)
    with pytest.raises(SenderError):
        channel_salt()
    monkeypatch.setenv("VALERIA_CHANNEL_SALT", SALT)
    assert channel_salt() == SALT
