"""Unit tests for deterministic lexical retrieval (T019)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.retrieval import (
    EntityIndex,
    GoldUnit,
    RetrievalError,
    build_context,
    load_context_pack,
    load_faq_seeds,
    load_gold_units,
    normalize_text,
    select_evidence,
    tokenize,
)
from tests.tasks_helpers import make_units, unit_id, write_gold


def _units() -> list[GoldUnit]:
    return [GoldUnit.from_dict(item) for item in make_units()]


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("¿Azúcar, ETANOL y biocombustibles?") == (
        "azucar etanol y biocombustibles"
    )


def test_tokenize_drops_stopwords_and_single_characters() -> None:
    tokens = tokenize("¿Cuáles son los productos de la compañía?")
    assert "productos" in tokens
    assert "compania" in tokens
    assert "los" not in tokens
    assert "de" not in tokens


def test_retrieval_is_deterministic() -> None:
    units = _units()
    first = select_evidence("¿Qué productos ofrece Manuelita?", units)
    second = select_evidence("¿Qué productos ofrece Manuelita?", units)
    assert first == second


def test_relevant_units_rank_first() -> None:
    selection = select_evidence("¿Qué productos ofrece Manuelita?", _units())
    assert selection.selected
    top = selection.selected[0]
    assert "productos" in top.unit.topic_id or "azúcar" in top.unit.text


def test_labels_are_consecutive_and_unique() -> None:
    selection = select_evidence("Manuelita azúcar etanol sostenibilidad", _units())
    labels = [item.label for item in selection.selected]
    assert labels == [f"U{index}" for index in range(1, len(labels) + 1)]


def test_top_k_is_respected() -> None:
    selection = select_evidence("Manuelita azúcar etanol sostenibilidad", _units(), top_k=2)
    assert len(selection.selected) == 2


def test_token_budget_is_respected() -> None:
    selection = select_evidence("Manuelita azúcar etanol sostenibilidad", _units(), token_budget=60)
    assert selection.tokens <= 60
    assert len(selection.selected) < 8
    assert selection.omitted_unit_ids


def test_selection_diversifies_by_topic() -> None:
    selection = select_evidence(
        "Manuelita azúcar etanol sostenibilidad presencia países historia", _units(), top_k=4
    )
    topics = {item.unit.topic_id for item in selection.selected}
    assert len(topics) >= 3


def test_unrelated_question_returns_no_evidence() -> None:
    selection = select_evidence("fútbol baloncesto tenis", _units())
    assert selection.selected == ()
    assert selection.tokens == 0


def test_entity_match_selects_unit_without_lexical_overlap() -> None:
    units = [
        GoldUnit(
            unit_id=unit_id(99),
            topic_id="topic_identidad",
            topic_title="Identidad",
            text="Contenido sin la palabra clave.",
            entity_ids=("ent_00000000000000aa",),
            url="https://example.test/99",
            title="Documento 99",
            section_path=("Identidad",),
        )
    ]
    index = EntityIndex(entries=((("zzzentidad",), "ent_00000000000000aa"),))
    selection = select_evidence("zzzentidad", units, entity_index=index)
    assert len(selection.selected) == 1
    assert "entidad" in selection.selected[0].reason


def test_build_context_marks_each_unit() -> None:
    selection = select_evidence("¿Qué productos ofrece Manuelita?", _units(), top_k=2)
    context = build_context(selection.selected)
    assert context.startswith("<context>")
    assert context.endswith("</context>")
    assert '<unit id="U1">' in context


def test_load_gold_units_drops_units_without_lineage(tmp_path: Path) -> None:
    gold = tmp_path / "gold"
    gold.mkdir()
    complete = make_units()[0]
    broken = dict(make_units()[1])
    broken["url"] = ""
    (gold / "knowledge_units.jsonl").write_text(
        json.dumps(complete, ensure_ascii=False) + "\n" + json.dumps(broken, ensure_ascii=False),
        encoding="utf-8",
    )
    units = load_gold_units(gold)
    assert [unit.unit_id for unit in units] == [complete["unit_id"]]


def test_load_gold_units_rejects_invalid_identifier(tmp_path: Path) -> None:
    gold = tmp_path / "gold"
    gold.mkdir()
    broken = dict(make_units()[0])
    broken["unit_id"] = "unit_invalid"
    (gold / "knowledge_units.jsonl").write_text(
        json.dumps(broken, ensure_ascii=False), encoding="utf-8"
    )
    with pytest.raises(RetrievalError):
        load_gold_units(gold)


def test_load_context_pack_reads_blocks(tmp_path: Path) -> None:
    write_gold(tmp_path)
    pack = load_context_pack(tmp_path / "data" / "gold", "8000")
    assert pack.pack_id == "pack_summary_8000"
    assert pack.blocks
    assert pack.tokens <= pack.budget_tokens
    assert all(block.citation for block in pack.blocks)


def test_load_faq_seeds_reads_evidence(tmp_path: Path) -> None:
    write_gold(tmp_path)
    seeds = load_faq_seeds(tmp_path / "data" / "gold")
    assert seeds
    assert any(seed.evidence_unit_ids for seed in seeds)


def test_missing_gold_file_raises() -> None:
    with pytest.raises(RetrievalError):
        load_context_pack("data/does-not-exist", "8000")
