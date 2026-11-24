"""Spec 024 (US5, T066): proyección t-SNE pura, determinista y con salidas PNG + JSON."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.rag import __main__ as rag_cli
from proyecto_modelos_lenguaje.rag.project import (
    JSON_NAME,
    PNG_NAME,
    FragmentInfo,
    QueryInfo,
    dense_recall_at_10,
    project,
    stratified_sample,
    write_outputs,
)

TOPICS = ("agua", "azucar", "palma", "fundacion")


def _synthetic(seed: int = 7) -> tuple[np.ndarray, list[FragmentInfo], np.ndarray, list[QueryInfo]]:
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(len(TOPICS), 16)) * 4
    vectors = []
    fragments = []
    for number in range(200):
        topic = number % len(TOPICS)
        vectors.append(centers[topic] + rng.normal(size=16))
        fragments.append(
            FragmentInfo(
                id=f"frag_{number:03d}", unit_id=f"unit_{number:03d}", topic_id=TOPICS[topic]
            )
        )
    queries = [
        QueryInfo(id=f"m3-{number:02d}", topic_id=TOPICS[number % 4], recall_at_10=recall)
        for number, recall in enumerate((1.0, 0.0, 0.5, 1.0, 0.0), start=1)
    ]
    query_vectors = np.vstack([centers[number % 4] + rng.normal(size=16) for number in range(1, 6)])
    return np.vstack(vectors), fragments, query_vectors, queries


def test_project_returns_fragment_and_query_points() -> None:
    vectors, fragments, query_vectors, queries = _synthetic()
    points = project(vectors, fragments, query_vectors, queries, seed=2026)

    assert len(points) == 205
    kinds = [point.kind for point in points]
    assert kinds.count("fragment") == 200 and kinds.count("query") == 5
    fragment = next(point for point in points if point.kind == "fragment")
    assert fragment.unit_id and fragment.topic_id in TOPICS and fragment.failed is None
    query_points = [point for point in points if point.kind == "query"]
    assert [point.failed for point in query_points] == [False, True, False, False, True]
    assert [point.recall_at_10 for point in query_points] == [1.0, 0.0, 0.5, 1.0, 0.0]
    assert all(np.isfinite(point.x) and np.isfinite(point.y) for point in points)


def test_project_is_deterministic_with_seed() -> None:
    vectors, fragments, query_vectors, queries = _synthetic()
    first = project(vectors, fragments, query_vectors, queries, seed=2026)
    second = project(vectors, fragments, query_vectors, queries, seed=2026)
    assert first == second


def test_project_samples_and_clamps_perplexity() -> None:
    vectors, fragments, query_vectors, queries = _synthetic()
    points = project(vectors[:10], fragments[:10], query_vectors, queries, sample=8, seed=2026)
    assert sum(point.kind == "fragment" for point in points) == 8
    assert sum(point.kind == "query" for point in points) == 5


def test_stratified_sample_keeps_every_topic() -> None:
    topics = ["a"] * 90 + ["b"] * 9 + ["c"]
    chosen = stratified_sample(topics, 20, 2026)
    assert len(chosen) == 20
    assert {topics[i] for i in chosen} == {"a", "b", "c"}
    assert chosen == stratified_sample(topics, 20, 2026)
    assert stratified_sample(topics, 500, 2026) == list(range(100))


def test_write_outputs_png_and_json(tmp_path: Path) -> None:
    vectors, fragments, query_vectors, queries = _synthetic()
    points = project(vectors, fragments, query_vectors, queries, seed=2026)
    png, target = write_outputs(points, tmp_path, metadata={"seed": 2026})

    assert png == tmp_path / PNG_NAME and target == tmp_path / JSON_NAME
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert png.stat().st_size < 1_000_000
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["fragments"] == 200 and payload["queries"] == 5
    assert payload["failed_queries"] == 2
    keys = {"id", "kind", "x", "y", "topic_id", "unit_id", "recall_at_10", "failed"}
    assert all(keys <= set(point) for point in payload["points"])


def test_dense_recall_at_10() -> None:
    index = np.eye(12, dtype=np.float32)
    unit_ids = [f"u{i}" for i in range(12)]
    queries = np.vstack([index[0], index[11]])
    recalls = dense_recall_at_10(queries, [["u0"], ["u11", "missing"]], index, unit_ids)
    assert recalls == [1.0, 0.5]


def test_cli_project_with_fixture_index(tmp_path: Path) -> None:
    fixtures = PROJECT_ROOT / "tests" / "fixtures" / "rag"
    code = rag_cli.main(
        [
            "project",
            "--index-dir",
            str(fixtures / "index"),
            "--gold",
            str(fixtures / "gold_sample.jsonl"),
            "--queries",
            str(fixtures / "module3_queries.jsonl"),
            "--embedder",
            "hash",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert code == 0
    payload = json.loads((tmp_path / JSON_NAME).read_text(encoding="utf-8"))
    assert payload["queries"] == 30
    assert payload["fragments"] == payload["index_fragments"]
    assert (tmp_path / PNG_NAME).stat().st_size < 1_000_000


def test_project_rejects_mismatched_inputs() -> None:
    vectors, fragments, query_vectors, queries = _synthetic()
    with pytest.raises(ValueError):
        project(vectors, fragments[:-1], query_vectors, queries)
