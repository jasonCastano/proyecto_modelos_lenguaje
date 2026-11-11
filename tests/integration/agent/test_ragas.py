"""Juez LLM con DeepSeek (T067). Requiere red y ``DEEPSEEK_API_KEY``: ``pytest -m network``."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.judge import judge_answer

pytestmark = pytest.mark.network

CONTEXT = [
    "[U1] Manuelita produce azúcar, bioetanol y energía a partir de la caña en el Valle del Cauca."
]


@pytest.fixture(scope="module")
def deepseek():
    from proyecto_modelos_lenguaje.llm import build_chat_model, load_llm_config

    config = load_llm_config()
    if not config.api_key_present:
        pytest.skip("Falta DEEPSEEK_API_KEY")
    return build_chat_model(config)


def test_supported_answer_scores_high(deepseek) -> None:
    # Act
    scores = judge_answer(
        "¿Qué produce Manuelita?", "Manuelita produce azúcar y bioetanol [U1].", CONTEXT, deepseek
    )

    # Assert
    assert scores is not None
    assert scores.faithfulness >= 0.9
    assert scores.answer_relevancy >= 0.7


def test_invented_figure_lowers_faithfulness(deepseek) -> None:
    # Act
    scores = judge_answer(
        "¿Qué produce Manuelita?",
        "Manuelita produce azúcar [U1] y exporta 3 millones de toneladas de café a Japón [U1].",
        CONTEXT,
        deepseek,
    )

    # Assert
    assert scores is not None
    assert scores.faithfulness < 0.9
    assert scores.unsupported
