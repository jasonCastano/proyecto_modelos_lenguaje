"""CLI de transcripción para OpenClaw (spec 028, T009, channel-api-v2 §3)."""

from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.channels import transcribe_cli as cli

ENV = {"VALERIA_CHANNEL_TOKEN": "tok", "VALERIA_BACKEND_URL": "http://127.0.0.1:8000"}


@pytest.fixture()
def note(tmp_path: Path) -> Path:
    path = tmp_path / "nota.ogg"
    path.write_bytes(b"OggS-fake")
    return path


def test_uses_the_backend_with_token(note: Path) -> None:
    calls: list[tuple[str, bytes, dict]] = []

    def post(url: str, data: bytes, headers: dict, timeout: float) -> dict:
        calls.append((url, data, headers))
        return {"text": "¿Qué produce Manuelita?", "language": "es"}

    text = cli.transcribe_file(note, ENV, post=post, local=lambda _d: "no")

    assert text == "¿Qué produce Manuelita?"
    url, data, headers = calls[0]
    assert url == "http://127.0.0.1:8000/api/channels/transcriptions" and data == b"OggS-fake"
    assert headers["X-Channel-Token"] == "tok"


def test_falls_back_to_in_process_when_backend_is_down(note: Path) -> None:
    def down(*_args: object) -> dict:
        raise urllib.error.URLError("connection refused")

    assert cli.transcribe_file(note, ENV, post=down, local=lambda _d: "local") == "local"


def test_invalid_audio_is_not_retried_locally(note: Path) -> None:
    def invalid(*_args: object) -> dict:
        raise urllib.error.HTTPError("u", 400, "audio_invalid", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        cli.transcribe_file(note, ENV, post=invalid, local=lambda _d: "no")


def test_refuses_a_non_loopback_backend(note: Path) -> None:
    with pytest.raises(ValueError):
        cli.via_backend(b"x", {"VALERIA_BACKEND_URL": "http://10.0.0.5:8000"})


def test_main_prints_one_line_and_exit_codes(
    note: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "transcribe_file", lambda _p: "Hola\n  Valeria ")
    assert cli.main([str(note)]) == 0
    assert capsys.readouterr().out == "Hola Valeria\n"

    def boom(_p: Path) -> str:
        raise RuntimeError("secreto del audio")

    monkeypatch.setattr(cli, "transcribe_file", boom)
    assert cli.main([str(note)]) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "secreto" not in err
    assert cli.main([]) == 1
