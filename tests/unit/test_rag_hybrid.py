"""Pruebas de la fusión híbrida: umbral, deduplicación, presupuesto y trazabilidad."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.rag import hybrid as hybrid_module
from proyecto_modelos_lenguaje.rag.config import load_retrieval_config
from proyecto_modelos_lenguaje.rag.embeddings import EmbeddingProfile, HashEmbedder
from proyecto_modelos_lenguaje.rag.hybrid import (
    HybridRetriever,
    RetrievalTrace,
    RetrievedFragment,
    SemanticRetriever,
)
from proyecto_modelos_lenguaje.rag.index import load_index
from proyecto_modelos_lenguaje.retrieval import (
    EntityIndex,
    EvidenceSelection,
    GoldUnit,
    SelectedUnit,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "rag"
FIXTURE_INDEX = FIXTURE_DIR / "index"
GOLD_SAMPLE = FIXTURE_DIR / "gold_sample.jsonl"


@pytest.fixture()
def config():
    return load_retrieval_config(project_root=PROJECT_ROOT)


@pytest.fixture()
def profile(config) -> EmbeddingProfile:
    return EmbeddingProfile.from_config(config.embedding, created_at="2026-11-06T00:00:00+00:00")


@pytest.fixture()
def units() -> tuple[GoldUnit, ...]:
    records = [
        json.loads(line)
        for line in GOLD_SAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return tuple(GoldUnit.from_dict(record) for record in records)


@pytest.fixture()
def retriever(units, profile, config) -> HybridRetriever:
    index = load_index(FIXTURE_INDEX, profile)
    return HybridRetriever(
        units,
        index=index,
        embedder=HashEmbedder(profile),
        entity_index=EntityIndex(),
        config=config,
    )


def _unit(unit_id: str, text: str, *, topic: str = "t1") -> GoldUnit:
    return GoldUnit(
        unit_id=unit_id,
        topic_id=topic,
        topic_title="Tema",
        text=text,
        url="https://example.com",
        title="Título",
    )


def _selection(items: list[tuple[GoldUnit, float]]) -> EvidenceSelection:
    selected = tuple(
        SelectedUnit(label=f"U{index + 1}", unit=unit, score=score, reason="coincidencia léxica")
        for index, (unit, score) in enumerate(items)
    )
    return EvidenceSelection(
        query="q",
        topic_id="t1",
        entities=(),
        selected=selected,
        omitted_unit_ids=(),
        tokens=0,
        budget_tokens=6000,
    )


def test_semantic_search_returns_sorted_candidates(retriever: HybridRetriever) -> None:
    candidates = retriever.semantic.search("agua y vertimientos", top_k=5)

    assert candidates
    assert len(candidates) <= 5
    scores = [fragment.score for fragment in candidates]
    assert scores == sorted(scores, reverse=True)
    assert all(fragment.origin == "semantic" for fragment in candidates)
    assert all(fragment.semantic_score is not None for fragment in candidates)


def test_semantic_search_without_index_returns_empty(units, profile, config) -> None:
    retriever = HybridRetriever(units, index=None, embedder=HashEmbedder(profile), config=config)

    trace = retriever.retrieve("agua")

    assert retriever.semantic_available is False
    assert trace.semantic_available is False
    assert any("Índice no disponible" in note for note in trace.notes)


def test_hybrid_fuses_scores_and_deduplicates(monkeypatch, config) -> None:
    u1 = _unit("u1", "agua " * 20)
    u2 = _unit("u2", "caña " * 20)
    u3 = _unit("u3", "palma " * 20)
    units = (u1, u2, u3)
    config = config.__class__(
        embedding=config.embedding,
        index=config.index,
        hybrid=config.hybrid.__class__(
            semantic_top_k=12,
            lexical_top_k=8,
            min_similarity=0.3,
            weight_semantic=0.65,
            weight_lexical=0.35,
            both_bonus=0.05,
            dedup_similarity=0.98,
        ),
        source=config.source,
    )
    retriever = HybridRetriever(
        units, embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)), config=config
    )

    monkeypatch.setattr(
        SemanticRetriever,
        "search",
        lambda self, question, top_k=None: [
            RetrievedFragment(
                unit_id="u1",
                title="Título",
                url="",
                score=0.8,
                semantic_score=0.8,
                lexical_score=None,
                origin="semantic",
            ),
            RetrievedFragment(
                unit_id="u2",
                title="Título",
                url="",
                score=0.6,
                semantic_score=0.6,
                lexical_score=None,
                origin="semantic",
            ),
        ],
    )
    monkeypatch.setattr(
        hybrid_module,
        "select_evidence",
        lambda *args, **kwargs: _selection([(u1, 10.0), (u3, 5.0)]),
    )

    trace = retriever.retrieve("agua")

    assert trace.mode == "hybrid"
    ids = [fragment.unit_id for fragment in trace.fragments]
    assert ids.count("u1") == 1
    by_id = {fragment.unit_id: fragment for fragment in trace.fragments}
    assert by_id["u1"].origin == "both"
    assert by_id["u1"].score == pytest.approx(0.65 * 0.8 + 0.35 * 1.0 + 0.05, abs=1e-6)
    assert by_id["u2"].score == pytest.approx(0.65 * 0.6, abs=1e-6)
    assert by_id["u3"].score == pytest.approx(0.35 * 0.5, abs=1e-6)
    assert [fragment.score for fragment in trace.fragments] == sorted(
        [fragment.score for fragment in trace.fragments], reverse=True
    )
    assert trace.used_unit_ids == ("u1", "u2", "u3")


def test_below_threshold_semantic_falls_back_to_lexical(monkeypatch, config) -> None:
    u1 = _unit("u1", "agua " * 20)
    u2 = _unit("u2", "palma " * 20)
    retriever = HybridRetriever(
        (u1, u2),
        embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)),
        config=config,
    )
    strict = config.hybrid.__class__(
        semantic_top_k=12,
        lexical_top_k=8,
        min_similarity=0.99,
        weight_semantic=0.65,
        weight_lexical=0.35,
        both_bonus=0.05,
        dedup_similarity=0.98,
    )
    retriever.config = config.__class__(
        embedding=config.embedding, index=config.index, hybrid=strict, source=config.source
    )
    monkeypatch.setattr(
        SemanticRetriever,
        "search",
        lambda self, question, top_k=None: [
            RetrievedFragment(
                unit_id="u1",
                title="Título",
                url="",
                score=0.5,
                semantic_score=0.5,
                lexical_score=None,
                origin="semantic",
            )
        ],
    )
    monkeypatch.setattr(
        hybrid_module, "select_evidence", lambda *args, **kwargs: _selection([(u2, 4.0)])
    )

    trace = retriever.retrieve("palma")

    assert trace.mode == "lexical"
    by_id = {fragment.unit_id: fragment for fragment in trace.fragments}
    assert by_id["u1"].status == "omitted_threshold"
    assert by_id["u1"].reason
    assert by_id["u2"].status == "used"


def test_no_candidates_returns_none_mode(monkeypatch, config) -> None:
    unit = _unit("u1", "texto irrelevante")
    retriever = HybridRetriever(
        (unit,),
        embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)),
        config=config,
    )
    monkeypatch.setattr(SemanticRetriever, "search", lambda self, question, top_k=None: [])
    monkeypatch.setattr(hybrid_module, "select_evidence", lambda *a, **k: _selection([]))

    trace = retriever.retrieve("receta de arepas")

    assert trace.mode == "none"
    assert trace.fragments == ()
    assert trace.used_unit_ids == ()


def test_budget_marks_omitted_fragments(monkeypatch, config) -> None:
    u1 = _unit("u1", "agua " * 200)
    u2 = _unit("u2", "palma " * 200)
    retriever = HybridRetriever(
        (u1, u2),
        embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)),
        config=config,
    )
    monkeypatch.setattr(SemanticRetriever, "search", lambda self, question, top_k=None: [])
    monkeypatch.setattr(
        hybrid_module,
        "select_evidence",
        lambda *a, **k: _selection([(u1, 10.0), (u2, 9.0)]),
    )

    trace = retriever.retrieve("agua", token_budget=50)

    statuses = {fragment.unit_id: fragment.status for fragment in trace.fragments}
    assert "omitted_budget" in statuses.values()
    assert any(fragment.reason for fragment in trace.fragments if fragment.status != "used")


def test_select_maps_used_fragments_to_labels(monkeypatch, config) -> None:
    u1 = _unit("u1", "agua " * 20)
    retriever = HybridRetriever(
        (u1,), embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)), config=config
    )
    monkeypatch.setattr(SemanticRetriever, "search", lambda self, question, top_k=None: [])
    monkeypatch.setattr(hybrid_module, "select_evidence", lambda *a, **k: _selection([(u1, 3.0)]))

    selection, trace = retriever.select("agua")

    assert [item.label for item in selection.selected] == ["U1"]
    assert selection.used_unit_ids == trace.used_unit_ids == ("u1",)


def test_trace_mode_hybrid_when_both_origins(monkeypatch, config) -> None:
    u1 = _unit("u1", "agua " * 20)
    retriever = HybridRetriever(
        (u1,), embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)), config=config
    )
    monkeypatch.setattr(
        SemanticRetriever,
        "search",
        lambda self, question, top_k=None: [
            RetrievedFragment(
                unit_id="u1",
                title="",
                url="",
                score=0.9,
                semantic_score=0.9,
                lexical_score=None,
                origin="semantic",
            )
        ],
    )
    monkeypatch.setattr(hybrid_module, "select_evidence", lambda *a, **k: _selection([(u1, 2.0)]))

    trace = retriever.retrieve("agua")

    assert trace.mode == "hybrid"
    assert trace.fragments[0].origin == "both"


def test_trace_payload_has_contract_fields(monkeypatch, config) -> None:
    u1 = _unit("u1", "agua " * 20)
    retriever = HybridRetriever(
        (u1,), embedder=HashEmbedder(EmbeddingProfile.from_config(config.embedding)), config=config
    )
    monkeypatch.setattr(SemanticRetriever, "search", lambda self, question, top_k=None: [])
    monkeypatch.setattr(hybrid_module, "select_evidence", lambda *a, **k: _selection([(u1, 1.0)]))

    payload = retriever.retrieve("agua").to_dict()

    assert set(payload) == {
        "mode",
        "semantic_available",
        "candidates",
        "threshold",
        "fragments",
        "used_unit_ids",
        "notes",
        "elapsed_ms",
    }


def test_fixture_index_produces_evidence(retriever: HybridRetriever) -> None:
    trace = retriever.retrieve("¿Cómo gestiona Manuelita el agua y los vertimientos?", top_k=5)

    assert isinstance(trace, RetrievalTrace)
    assert trace.semantic_available is True
    assert trace.mode in {"hybrid", "semantic", "lexical"}
    assert trace.used_unit_ids
