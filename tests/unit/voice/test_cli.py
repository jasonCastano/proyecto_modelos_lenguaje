"""CLI ``python -m proyecto_modelos_lenguaje.voice`` con el motor simulado (spec 016)."""

from __future__ import annotations

import io
import json
import wave
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.voice.__main__ import main


def test_check_json_with_fake_engine(capsys: pytest.CaptureFixture[str]) -> None:
    # Act
    code = main(["--check", "--json"])
    # Assert
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["engine"] == "fake"
    assert payload["state"] == "ready"
    assert payload["audio_ms"] > 0


def test_say_writes_valid_wav(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Arrange
    target = tmp_path / "prueba.wav"
    # Act
    code = main(["--say", "Manuelita produce azúcar [U2].", "-o", str(target), "--json"])
    # Assert
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["text"] == "Manuelita produce azúcar."
    with wave.open(io.BytesIO(target.read_bytes())) as handle:
        assert handle.getnchannels() == 1 and handle.getnframes() > 0


def test_check_disabled_exits_2(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("MANUELITA_VOICE_ENABLED", "0")
    assert main(["--check"]) == 2
    assert "Voz desactivada" in capsys.readouterr().out


def test_list_voices_marks_configured(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--list-voices", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    configured = [row["name"] for row in rows if row["configured"]]
    assert configured == ["Rebeca"]
    assert sum(row["gender"] == "female" for row in rows) == 13


def test_voice_override_and_unknown_voice(tmp_path: Path, capsys) -> None:
    assert (
        main(["--say", "Hola.", "--voice", "Regina", "-o", str(tmp_path / "a.wav"), "--json"]) == 0
    )
    assert json.loads(capsys.readouterr().out)["voice"] == "Regina"
    assert main(["--say", "Hola.", "--voice", "Nadie", "-o", str(tmp_path / "b.wav")]) == 1


def test_never_writes_inside_data(capsys: pytest.CaptureFixture[str]) -> None:
    from proyecto_modelos_lenguaje.config import PROJECT_ROOT

    target = PROJECT_ROOT / "data" / "voz.wav"
    assert main(["--say", "Hola.", "-o", str(target)]) == 1
    assert not target.exists()


def test_invalid_arguments_exit_1() -> None:
    assert main([]) == 1
    assert main(["--say", "[U1]"]) == 1
