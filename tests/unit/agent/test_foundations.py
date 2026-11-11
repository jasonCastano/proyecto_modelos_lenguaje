"""Fundamentos: modo demo, CLI ``chat`` y fragmento anómalo (T004, T010, T012, T047)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent import __main__ as cli
from proyecto_modelos_lenguaje.agent.__main__ import main
from proyecto_modelos_lenguaje.agent.demo import DEMO_INDEX, build_demo_model
from proyecto_modelos_lenguaje.rag.hybrid import RetrievedFragment
from tests.agent_helpers import demo_retriever


def test_demo_model_is_deterministic_and_offline() -> None:
    # Arrange
    model = build_demo_model(["primera [U1]", "segunda [U2]"])

    # Act
    answers = [model.invoke("hola").content for _ in range(3)]

    # Assert
    assert answers == ["primera [U1]", "segunda [U2]", "primera [U1]"]
    assert (DEMO_INDEX / "manifest.json").is_file()


def _fragment(**overrides: object) -> RetrievedFragment:
    values: dict[str, object] = {
        "unit_id": "unit_0000000000000001",
        "title": "t",
        "url": "https://www.manuelita.com",
        "score": 0.5,
        "semantic_score": 0.5,
        "lexical_score": None,
        "origin": "semantic",
    }
    values.update(overrides)
    return RetrievedFragment(**values)  # type: ignore[arg-type]


def test_anomalous_fragment_serializes_its_reasons() -> None:
    # Act
    payload = _fragment(anomalous=True, anomaly_reasons=("revela_prompt",)).to_dict()

    # Assert
    assert payload["anomalous"] is True
    assert payload["anomaly_reasons"] == ["revela_prompt"]
    assert _fragment().to_dict()["anomaly_reasons"] == []


@pytest.mark.parametrize(
    "overrides",
    [{"anomalous": True}, {"anomaly_reasons": ("revela_prompt",)}],
)
def test_anomaly_flag_and_reasons_must_agree(overrides: dict[str, object]) -> None:
    # Act / Assert
    with pytest.raises(ValueError, match="anomaly_reasons"):
        _fragment(**overrides)


def test_cli_chat_keeps_the_thread_between_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "_cli_retriever", lambda _mode, _root: demo_retriever())

    # Act
    first_code = main(["chat", "--mode", "demo", "--json", "¿Qué produce Manuelita?"])
    thread_id = json.loads(capsys.readouterr().out)["thread_id"]
    second_code = main(["chat", "--mode", "demo", "--thread", thread_id, "¿Y dónde lo produce?"])
    output = capsys.readouterr().out

    # Assert
    assert (first_code, second_code) == (0, 0)
    assert f"hilo {thread_id} · turno 2 · answered" in output
    assert "[U1]" in output


def test_cli_chat_unknown_thread_exits_with_client_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(cli, "_cli_retriever", lambda _mode, _root: demo_retriever())

    # Act
    code = main(["chat", "--mode", "demo", "--thread", "no-existe", "Hola"])

    # Assert
    assert code == 2
    assert "thread_not_found" in capsys.readouterr().err
