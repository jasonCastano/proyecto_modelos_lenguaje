"""Pruebas de los fundamentos restantes: modo demo, CLI y fragmento anómalo (T010, T012, T004)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.__main__ import NOT_IMPLEMENTED_EXIT, main
from proyecto_modelos_lenguaje.agent.demo import DEMO_INDEX, build_demo_model
from proyecto_modelos_lenguaje.rag.hybrid import RetrievedFragment


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


@pytest.mark.parametrize("argv", [["chat", "hola"]])
def test_cli_subcommands_exist_and_report_pending(argv: list[str]) -> None:
    # Act
    code = main(argv)

    # Assert
    assert code == NOT_IMPLEMENTED_EXIT
