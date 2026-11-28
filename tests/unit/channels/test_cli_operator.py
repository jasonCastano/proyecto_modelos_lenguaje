"""Comandos del operador del canal abierto (spec 031, T016, contrato §3)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.channels import __main__ as cli
from proyecto_modelos_lenguaje.channels.identity import pseudonym
from proyecto_modelos_lenguaje.channels.store import ChannelStore

SALT = "sal-de-prueba-0123456789"
NUMBER = "+570000000101"


@pytest.fixture()
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("VALERIA_CHANNEL_SALT", SALT)
    return tmp_path / "state"


def test_pseudonym_prints_only_the_pseudonym(
    state: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["pseudonym", "--sender", NUMBER]) == cli.EXIT_OK
    out = capsys.readouterr().out.strip()
    assert re.fullmatch(r"wa-[0-9a-f]{16}", out)
    assert out == pseudonym(NUMBER, SALT, "whatsapp")
    assert "570000000101" not in out


def test_block_unblock_and_list(state: Path, capsys: pytest.CaptureFixture[str]) -> None:
    user_id = pseudonym(NUMBER, SALT, "whatsapp")
    assert cli.main(["block", "--sender", NUMBER]) == cli.EXIT_OK
    assert cli.main(["block", "--sender", NUMBER]) == cli.EXIT_OK  # no duplica
    store = ChannelStore(state / "channels.sqlite3")
    assert store.is_blocked(user_id)
    store.close()
    assert cli.main(["blocked"]) == cli.EXIT_OK
    assert cli.main(["unblock", "--sender", NUMBER]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "bloqueado " + user_id in out and "Bloqueados: 1" in out
    assert "desbloqueado " + user_id in out
    assert "570000000101" not in out  # nunca el número
    store = ChannelStore(state / "channels.sqlite3")
    assert not store.is_blocked(user_id)
    store.close()


def test_invalid_numbers_fail_without_echoing_them(
    state: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["pseudonym", "--sender", "no-es-un-numero"]) == cli.EXIT_ERROR
    captured = capsys.readouterr()
    assert "no-es-un-numero" not in captured.out


# --- spec 033: bloqueo por seudónimo (T019) ----------------------------------------------------

USER = "wa-0123456789abcdef"


def test_block_and_unblock_by_pseudonym(state: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["block", "--pseudonym", USER]) == cli.EXIT_OK
    store = ChannelStore(state / "channels.sqlite3")
    assert store.is_blocked(USER)
    store.close()
    assert cli.main(["unblock", "--pseudonym", USER]) == cli.EXIT_OK
    out = capsys.readouterr().out
    assert f"bloqueado {USER}" in out and f"desbloqueado {USER}" in out


def test_invalid_pseudonym_fails_without_echo(
    state: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["block", "--pseudonym", "wa-573001234567"]) == cli.EXIT_ERROR
    captured = capsys.readouterr()
    assert "573001234567" not in captured.out + captured.err


def test_sender_and_pseudonym_are_mutually_exclusive(state: Path) -> None:
    with pytest.raises(SystemExit):
        cli.main(["block", "--sender", NUMBER, "--pseudonym", USER])
    with pytest.raises(SystemExit):
        cli.main(["block"])
