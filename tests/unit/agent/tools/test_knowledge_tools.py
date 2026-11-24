"""Herramientas de conocimiento del catálogo (T031, spec 024).

Índice de prueba de ``tests/fixtures/rag/index`` (embeddings hash, sin red) y, donde hace falta,
un recuperador léxico con unidades sintéticas.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

import pytest

from proyecto_modelos_lenguaje.agent.catalog import ToolArgsError, ToolContext, get_spec, run_read
from proyecto_modelos_lenguaje.agent.structured import normalize
from proyecto_modelos_lenguaje.agent.tools_knowledge import (
    THEME_TERMS,
    THEME_TOPICS,
    TopicId,
    load_faq_seeds,
    rank_faq,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.rag.hybrid import HybridRetriever
from proyecto_modelos_lenguaje.retrieval import GoldUnit
from tests.agent_helpers import demo_retriever
from tests.unit.agent.tools.gold import requires_gold

TOPICS_DIR = PROJECT_ROOT / "data" / "gold" / "topics"
WATER_UNIT = "unit_8537ad9053e21e86"  # vertimientos de aguas residuales (fixture)


@pytest.fixture(scope="module")
def retriever() -> HybridRetriever:
    return demo_retriever()


def _run(name: str, args: dict, retriever) -> tuple[str, ToolContext]:
    ctx = ToolContext(retriever=retriever)
    return run_read(get_spec(name), ctx, args), ctx


def _labels(output: str) -> list[str]:
    return [part.split('"')[0] for part in output.split('<documento id="')[1:]]


# ------------------------------------------------------------------ sustainability_lookup


def test_sustainability_lookup_uses_a_payload_filter_and_cites_units(retriever, monkeypatch):
    # Arrange
    seen = []
    original = retriever.retrieve

    def spy(query, **kwargs):
        seen.append(kwargs["metadata_filter"])
        return original(query, **kwargs)

    monkeypatch.setattr(retriever, "retrieve", spy)

    # Act
    output, ctx = _run("sustainability_lookup", {"theme": "agua", "top_k": 3}, retriever)

    # Assert
    assert seen and seen[0].topics == frozenset(THEME_TOPICS["agua"])
    assert ctx.trace.fragments and len(ctx.trace.fragments) <= 3
    assert _labels(output) == [f"U{i}" for i in range(1, len(ctx.trace.fragments) + 1)]
    assert WATER_UNIT in {fragment.unit_id for fragment in ctx.trace.fragments}
    for fragment in ctx.trace.fragments:
        unit = retriever.units_by_id[fragment.unit_id]
        assert unit.topic_id in THEME_TOPICS["agua"]
        assert THEME_TERMS["agua"].search(normalize(unit.text))


def test_sustainability_lookup_with_query_and_social_theme(retriever) -> None:
    # Act
    output, ctx = _run(
        "sustainability_lookup", {"theme": "social", "query": "programas de educación"}, retriever
    )

    # Assert
    assert ctx.trace.fragments
    assert output.startswith('<documento id="U1"')


@pytest.mark.parametrize(
    "args",
    [
        {"theme": "minería"},
        {"theme": "agua", "top_k": 11},
        {"theme": "agua", "query": "ab"},
        {"theme": "agua", "query": "x" * 201},
    ],
)
def test_sustainability_lookup_rejects_invalid_args(retriever, args: dict) -> None:
    with pytest.raises(ToolArgsError, match="sustainability_lookup"):
        _run("sustainability_lookup", args, retriever)


def test_sustainability_lookup_without_index_is_declared() -> None:
    # Act
    output = run_read(get_spec("sustainability_lookup"), ToolContext(), {"theme": "agua"})

    # Assert
    assert "no está disponible" in output


# ----------------------------------------------------------------------------- faq_lookup


@requires_gold
def test_faq_seeds_of_the_gold_are_ranked_lexically() -> None:
    # Arrange
    seeds = load_faq_seeds()

    # Act
    ranked = rank_faq("¿Qué certificaciones tiene Manuelita?", seeds)

    # Assert
    assert len(seeds) == 53
    assert ranked and ranked[0][1]["topic_id"] == "certificaciones"
    assert rank_faq("zzzz qwerty", seeds) == []


def test_faq_lookup_returns_seed_question_and_cited_evidence(
    retriever, tmp_path: Path, monkeypatch
) -> None:
    # Arrange
    seed = {
        "seed_id": "faq_test",
        "question": "¿Qué hace Manuelita con las aguas residuales y los vertimientos?",
        "topic_id": "sostenibilidad",
        "evidence_unit_ids": [WATER_UNIT, "unit_ffffffffffffffff"],
        "status": "ready",
    }
    other = {**seed, "seed_id": "faq_otro", "question": "¿Qué marcas vende?", "topic_id": "x"}
    (tmp_path / "faq_seeds.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in (seed, other)), encoding="utf-8"
    )
    monkeypatch.setenv("PML_GOLD_DIR", str(tmp_path))

    # Act
    output, ctx = _run("faq_lookup", {"question": "vertimientos de aguas residuales"}, retriever)

    # Assert
    assert seed["question"] in output
    assert "marcas" not in output
    assert [fragment.unit_id for fragment in ctx.trace.fragments] == [WATER_UNIT]
    assert '<documento id="U1"' in output


@requires_gold
def test_faq_lookup_without_match_is_sin_resultados(retriever) -> None:
    # Act
    output, ctx = _run("faq_lookup", {"question": "zzzz qwerty"}, retriever)

    # Assert
    assert output.startswith("Sin resultados")
    assert ctx.trace.fragments == []


@pytest.mark.parametrize("args", [{"question": "ab"}, {"question": "agua", "top_k": 6}])
def test_faq_lookup_rejects_invalid_args(retriever, args: dict) -> None:
    with pytest.raises(ToolArgsError, match="faq_lookup"):
        _run("faq_lookup", args, retriever)


# ------------------------------------------------------------------------ summarize_topic


def test_summarize_topic_only_accepts_the_gold_topics() -> None:
    # Assert
    assert sorted(get_args(TopicId)) == sorted(path.stem for path in TOPICS_DIR.glob("*.md"))


@requires_gold
def test_summarize_topic_returns_units_of_that_topic(retriever) -> None:
    # Act
    output, ctx = _run("summarize_topic", {"topic_id": "sostenibilidad"}, retriever)

    # Assert
    assert output.startswith("Tema: Sostenibilidad")
    assert 1 <= len(ctx.trace.fragments) <= 5
    assert all(
        retriever.units_by_id[f.unit_id].topic_id == "sostenibilidad" for f in ctx.trace.fragments
    )


def test_summarize_topic_rejects_unknown_topics(retriever) -> None:
    with pytest.raises(ToolArgsError, match="summarize_topic"):
        _run("summarize_topic", {"topic_id": "inventado"}, retriever)


# ---------------------------------------------------------------------------- latest_news


def _news(unit_id: str, date: str | None, topic: str = "noticias") -> GoldUnit:
    return GoldUnit(
        unit_id=unit_id,
        topic_id=topic,
        topic_title="Noticias",
        text=f"Noticia {unit_id} de Manuelita.",
        url=f"https://www.manuelita.com/manuelita-noticias/{unit_id}",
        title=f"Noticia {unit_id}",
        published_at=date,
    )


@pytest.fixture()
def news_retriever() -> HybridRetriever:
    return HybridRetriever(
        [
            _news("unit_0000000000000001", "2019-05-01T00:00:00Z"),
            _news("unit_0000000000000002", "2024-03-10T00:00:00Z"),
            _news("unit_0000000000000003", "2022-07-01T00:00:00Z", topic="identidad"),
            _news("unit_0000000000000004", None),
            _news("unit_0000000000000005", "2025-11-01T00:00:00Z"),
        ]
    )


def test_latest_news_orders_by_published_at(news_retriever) -> None:
    # Act
    output, ctx = _run("latest_news", {"limit": 3}, news_retriever)

    # Assert
    assert [f.unit_id[-1] for f in ctx.trace.fragments] == ["5", "2", "3"]
    assert "publicado 2025-11-01" in output


def test_latest_news_since_year_and_empty(news_retriever) -> None:
    # Act
    _, recent = _run("latest_news", {"limit": 5, "since_year": 2023}, news_retriever)
    empty, none = _run("latest_news", {"since_year": 2030}, news_retriever)

    # Assert
    assert [f.unit_id[-1] for f in recent.trace.fragments] == ["5", "2"]
    assert empty.startswith("Sin resultados")
    assert none.trace.fragments == []


@pytest.mark.parametrize("args", [{"limit": 0}, {"limit": 6}, {"since_year": 1990}])
def test_latest_news_rejects_invalid_args(news_retriever, args: dict) -> None:
    with pytest.raises(ToolArgsError, match="latest_news"):
        _run("latest_news", args, news_retriever)


# --------------------------------------------------------------------------- get_fragment


def test_get_fragment_returns_text_url_and_pages(retriever) -> None:
    # Arrange
    unit = retriever.units_by_id[WATER_UNIT]

    # Act
    output, ctx = _run("get_fragment", {"unit_id": WATER_UNIT}, retriever)

    # Assert
    assert [f.unit_id for f in ctx.trace.fragments] == [WATER_UNIT]
    assert unit.url in output
    assert f"p. {unit.page_start}" in output
    assert "vertimientos" in output


def test_get_fragment_unknown_unit_is_sin_resultados(retriever) -> None:
    # Act
    output, ctx = _run("get_fragment", {"unit_id": "unit_ffffffffffffffff"}, retriever)

    # Assert
    assert output.startswith("Sin resultados")
    assert ctx.trace.fragments == []


@pytest.mark.parametrize("unit_id", ["unit_123", "UNIT_8537ad9053e21e86", "8537ad9053e21e86"])
def test_get_fragment_rejects_malformed_ids(retriever, unit_id: str) -> None:
    with pytest.raises(ToolArgsError, match="get_fragment"):
        _run("get_fragment", {"unit_id": unit_id}, retriever)
