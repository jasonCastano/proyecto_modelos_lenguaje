"""Integration tests for the three tasks with the offline model (T023, T029, T035, T041)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.retrieval import (
    GoldUnit,
    load_context_pack,
    load_faq_seeds,
    load_gold_units,
)
from proyecto_modelos_lenguaje.tasks import (
    answer_question,
    build_scripted_model,
    generate_faq,
    summarize_corpus,
)
from tests.tasks_helpers import write_gold

QUESTIONS = (
    "¿Qué productos ofrece Manuelita?",
    "¿Dónde está la casa matriz de Manuelita?",
    "¿Cuál es la misión de Manuelita?",
    "¿En qué países tiene presencia Manuelita?",
    "¿Qué filiales tiene el Grupo Manuelita?",
    "¿Cómo gestiona Manuelita su impacto ambiental?",
    "¿Qué certificaciones ambientales tiene Manuelita?",
    "¿Cuántas personas emplea Manuelita?",
    "¿Qué energía comercializa Manuelita?",
    "¿Qué historia tiene Manuelita?",
)

REAL_GOLD = PROJECT_ROOT / "data" / "gold"


def _units(tmp_path: Path) -> tuple[GoldUnit, ...]:
    write_gold(tmp_path)
    return load_gold_units(tmp_path / "data" / "gold")


def test_ten_questions_get_citation_or_fallback(tmp_path: Path) -> None:
    units = _units(tmp_path)
    model = build_scripted_model("qa")
    for question in QUESTIONS:
        result = answer_question(question, model=model, units=units)
        assert result.status in {"ok", "fallback"}
        if result.status == "ok":
            assert result.citations
            assert result.answer.strip()
        else:
            assert result.fallback is True
            assert result.citations == ()


def test_summary_uses_the_real_eight_thousand_pack(tmp_path: Path) -> None:
    units = _units(tmp_path)
    pack = load_context_pack(tmp_path / "data" / "gold", "8000")
    result = summarize_corpus(
        model=build_scripted_model("summary"),
        units=units,
        gold_dir=tmp_path / "data" / "gold",
    )
    assert result.status == "ok"
    assert set(result.used_unit_ids) == set(pack.unit_ids)
    assert 8 <= len(result.citations) <= 12


def test_faq_respects_the_limit_and_the_evidence(tmp_path: Path) -> None:
    gold = write_gold(tmp_path)
    items = generate_faq(limit=12, model=build_scripted_model("faq"), gold_dir=gold)
    assert len(items) == 12
    for item in items:
        assert item.status in {"ready", "review", "missing_evidence"}
        if item.status == "missing_evidence":
            assert item.citations == ()
        else:
            assert item.answer.strip()


def test_every_citation_belongs_to_the_used_units(tmp_path: Path) -> None:
    units = _units(tmp_path)
    qa_result = answer_question(
        "¿Qué productos ofrece Manuelita?",
        model=build_scripted_model("qa"),
        units=units,
    )
    summary_result = summarize_corpus(
        model=build_scripted_model("summary"),
        units=units,
        gold_dir=tmp_path / "data" / "gold",
    )
    for result in (qa_result, summary_result):
        used = set(result.used_unit_ids)
        assert result.citations
        assert all(citation.unit_id in used for citation in result.citations)


def test_faq_citations_belong_to_the_seed_evidence(tmp_path: Path) -> None:
    gold = write_gold(tmp_path)
    items = generate_faq(limit=10, model=build_scripted_model("faq"), gold_dir=gold)
    seeds = load_faq_seeds(tmp_path / "data" / "gold")
    allowed = {unit_id for seed in seeds for unit_id in seed.evidence_unit_ids}
    assert allowed
    for item in items:
        for citation in item.citations:
            assert citation.unit_id in allowed


@pytest.mark.skipif(
    not (REAL_GOLD / "knowledge_units.jsonl").is_file(),
    reason="data/gold no existe: ejecuta el pipeline de oro para probar con datos reales",
)
def test_real_gold_layer_when_available() -> None:
    result = answer_question(
        "¿Qué productos ofrece Manuelita?",
        model=build_scripted_model("qa"),
    )
    assert result.status in {"ok", "fallback"}


def test_environment_variable_points_to_the_gold_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gold = write_gold(tmp_path)
    monkeypatch.setenv("PML_GOLD_DIR", str(gold))
    result = answer_question(
        "¿Qué productos ofrece Manuelita?", model=build_scripted_model("qa")
    )
    assert result.status == "ok"
    assert result.citations
