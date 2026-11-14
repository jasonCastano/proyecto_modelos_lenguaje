"""Trazas marcadas con el corpus usado (spec 015, FR-003)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent.observability import run_config, turn_record


def test_run_config_tags_the_adversarial_corpus() -> None:
    # Act
    config = run_config("t-1", "chain", "real", corpus="adversarial")
    # Assert
    assert "corpus:adversarial" in config["tags"]
    assert config["metadata"]["corpus"] == "adversarial"


def test_run_config_without_adversarial_corpus_has_no_tag() -> None:
    # Act
    config = run_config("t-1", "agent", "real")
    # Assert
    assert not any(tag.startswith("corpus:") for tag in config["tags"])
    assert config["metadata"]["corpus"] == "real"


def test_turn_record_includes_the_corpus() -> None:
    # Arrange
    outcome = {"thread_id": "t-1", "status": "answered", "turn": {"turn_id": 1}}
    # Act
    record = turn_record(outcome, variant="chain", mode="real", corpus="adversarial")
    default = turn_record(outcome, variant="chain", mode="demo")
    # Assert
    assert record["corpus"] == "adversarial"
    assert default["corpus"] == "demo"
