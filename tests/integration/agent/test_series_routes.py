"""Casos 3 y 4 de la rúbrica de punta a punta en modo demo: dato estructurado y ruta mixta."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.series import load_series
from tests.agent_helpers import make_service

USER = "series-user"


@pytest.fixture(scope="module")
def series():
    return load_series()


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_structured_question_is_answered_from_the_curated_series(series, variant: str) -> None:
    # Arrange
    service = make_service(series=series)

    # Act
    outcome = service.send(
        "¿Cuánto vendió Manuelita en total entre 2019 y 2022?", user_id=USER, variant=variant
    )

    # Assert
    turn = outcome.turn
    assert turn.route.route == "structured"
    assert "7.476.475" in turn.answer
    assert [c["label"] for c in turn.citations] == ["F1"]
    assert turn.citations[0]["url"].endswith("Informe_Sostenibilidad_Manuelita-2021-2022.pdf")


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_mixed_question_cites_a_fact_and_a_document(series, variant: str) -> None:
    # Arrange
    service = make_service(series=series)

    # Act
    outcome = service.send(
        "Compara el crecimiento de la producción de biodiésel con lo que dice el informe sobre "
        "sostenibilidad",
        user_id=USER,
        variant=variant,
    )

    # Assert
    labels = {c["label"][0] for c in outcome.turn.citations}
    assert outcome.turn.route.route == "mixed"
    assert labels == {"F", "U"}
    assert outcome.turn.structured_rows and outcome.turn.fragments


def test_quarterly_question_declares_the_annual_limit(series) -> None:
    # Arrange
    service = make_service(series=series)

    # Act
    outcome = service.send(
        "¿Cuántas toneladas de azúcar se produjeron en el tercer trimestre de 2022?", user_id=USER
    )

    # Assert
    assert "no publican cifras trimestrales" in outcome.turn.answer
    assert "395.663" in outcome.turn.answer
