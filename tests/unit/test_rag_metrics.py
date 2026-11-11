"""Pruebas de Recall@k y nDCG@k con valores calculados a mano (T016, spec 014)."""

from __future__ import annotations

import math

import pytest

from proyecto_modelos_lenguaje.rag.evaluate import ndcg_at_k, percentile, recall_at_k

# nDCG binario con descuento log2(posición + 1):
#   DCG@k = sum(rel_i / log2(i + 1)), IDCG@k = DCG del ranking ideal (relevantes primero).


def test_single_relevant_at_first_position() -> None:
    # Arrange
    ranking, expected = ["a", "b", "c"], {"a"}

    # Act / Assert
    assert recall_at_k(ranking, expected, 10) == 1.0
    assert ndcg_at_k(ranking, expected, 10) == 1.0


def test_single_relevant_at_third_position() -> None:
    # Arrange
    ranking, expected = ["x", "y", "a"], {"a"}

    # Act
    ndcg = ndcg_at_k(ranking, expected, 10)

    # Assert: DCG = 1/log2(4) = 0.5, IDCG = 1
    assert recall_at_k(ranking, expected, 2) == 0.0
    assert recall_at_k(ranking, expected, 3) == 1.0
    assert ndcg == pytest.approx(0.5)


def test_two_relevant_one_retrieved() -> None:
    # Arrange
    ranking, expected = ["a", "x", "y"], {"a", "b"}

    # Act
    ndcg = ndcg_at_k(ranking, expected, 10)

    # Assert: recall = 1/2; DCG = 1; IDCG = 1 + 1/log2(3)
    assert recall_at_k(ranking, expected, 10) == pytest.approx(0.5)
    assert ndcg == pytest.approx(1 / (1 + 1 / math.log2(3)))


def test_two_relevant_at_positions_two_and_four() -> None:
    # Arrange
    ranking, expected = ["x", "a", "y", "b"], {"a", "b"}

    # Act
    ndcg = ndcg_at_k(ranking, expected, 10)

    # Assert: DCG = 1/log2(3) + 1/log2(5); IDCG = 1 + 1/log2(3)
    dcg = 1 / math.log2(3) + 1 / math.log2(5)
    idcg = 1 + 1 / math.log2(3)
    assert recall_at_k(ranking, expected, 10) == 1.0
    assert ndcg == pytest.approx(dcg / idcg)
    assert ndcg_at_k(ranking, expected, 2) == pytest.approx((1 / math.log2(3)) / idcg)


def test_no_relevant_documents_scores_zero() -> None:
    # Act / Assert
    assert recall_at_k(["a", "b"], set(), 10) == 0.0
    assert ndcg_at_k(["a", "b"], set(), 10) == 0.0
    assert recall_at_k([], {"a"}, 10) == 0.0
    assert ndcg_at_k([], {"a"}, 10) == 0.0


def test_duplicates_in_ranking_count_once() -> None:
    # Act / Assert
    assert ndcg_at_k(["a", "a", "b"], {"a"}, 10) == 1.0
    assert recall_at_k(["a", "a"], {"a", "b"}, 10) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("values", "fraction", "expected"),
    [
        ([10.0], 0.95, 10.0),
        ([1.0, 2.0, 3.0, 4.0, 5.0], 0.5, 3.0),
        ([1.0, 2.0, 3.0, 4.0, 5.0], 0.95, 4.8),
        ([5.0, 1.0, 3.0], 1.0, 5.0),
        ([], 0.95, 0.0),
    ],
)
def test_percentile_interpolates_on_sorted_sample(
    values: list[float], fraction: float, expected: float
) -> None:
    # Act / Assert
    assert percentile(values, fraction) == pytest.approx(expected)
