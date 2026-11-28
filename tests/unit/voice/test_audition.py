"""Audición de voces y expresiones caleñas (spec 036, T017) con el motor simulado."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.style import load_lexicon
from proyecto_modelos_lenguaje.voice.__main__ import AUDITION_VOICES, main


def test_audition_writes_one_wav_per_voice_and_expression(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "audicion"
    assert main(["--audition", "--out", str(out), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    index = (out / "index.txt").read_text(encoding="utf-8").splitlines()
    spoken = [e for e in load_lexicon().approved if e.spoken]
    rows = [line for line in index if "\t" in line]
    assert payload["files"] == len(rows) == len(AUDITION_VOICES) + len(spoken)
    for line in rows:
        file_name = line.split("\t")[2]
        assert file_name == "(no disponible)" or (out / file_name).stat().st_size > 44
    assert any(line.startswith("voz\tRebeca\t") for line in rows)


def test_audition_never_writes_inside_the_repository(capsys: pytest.CaptureFixture[str]) -> None:
    inside = Path(__file__).resolve().parents[3] / "tmp_audicion"
    assert main(["--audition", "--out", str(inside)]) == 1
    assert not inside.exists()
    assert "fuera del repositorio" in capsys.readouterr().err


def test_audition_without_engine_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MANUELITA_VOICE_ENABLED", "0")
    assert main(["--audition", "--out", str(tmp_path / "x")]) == 2
    assert "Voz desactivada" in capsys.readouterr().out
