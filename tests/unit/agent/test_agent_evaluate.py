"""Pruebas de la evaluación del enrutador y del CLI del agente (T032, T036)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from proyecto_modelos_lenguaje.agent.__main__ import main
from proyecto_modelos_lenguaje.agent.evaluate import (
    SECTION_END,
    SECTION_START,
    evaluate_router,
    load_router_cases,
    render_router_section,
    write_router_section,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.unit.agent.test_structured import ENTITIES, FACTS, UNITS, _write_jsonl

QUERIES = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "module2_queries.jsonl"


def test_follow_ups_carry_their_previous_turn_as_history() -> None:
    # Act
    cases = {case.query_id: case for case in load_router_cases(QUERIES)}

    # Assert
    assert cases["r31"].history == (cases["r09"].question,)
    assert cases["r01"].history == ()


def test_demo_router_meets_no_search_criterion() -> None:
    # Arrange
    cases = load_router_cases(QUERIES)

    # Act
    report = evaluate_router(cases, model=None, min_confidence=0.6, run_id="t", mode="demo")

    # Assert
    assert report.cases == 36
    assert report.no_search_ok == report.no_search_total == 10
    assert report.model_calls == 0
    assert sum(sum(counter.values()) for counter in report.confusion.values()) == 36


def test_router_section_is_replaced_not_duplicated(tmp_path: Path) -> None:
    # Arrange
    report_path = tmp_path / "eval.md"
    report_path.write_text("# Informe\n\nTexto previo.\n", encoding="utf-8")
    cases = load_router_cases(QUERIES)[:6]
    report = evaluate_router(cases, model=None, min_confidence=0.6, run_id="t", mode="demo")

    # Act
    write_router_section(report_path, render_router_section(report))
    write_router_section(report_path, render_router_section(report))
    text = report_path.read_text(encoding="utf-8")

    # Assert
    assert text.startswith("# Informe")
    assert text.count(SECTION_START) == 1 and text.count(SECTION_END) == 1
    assert "Precisión del enrutador | 1.000 (6/6)" in text


def test_cli_build_structured_exit_codes(tmp_path: Path) -> None:
    # Arrange
    root = tmp_path / "repo"
    gold = root / "data" / "gold"
    gold.mkdir(parents=True)
    _write_jsonl(gold / "entities.jsonl", ENTITIES)
    _write_jsonl(gold / "facts.jsonl", FACTS)
    _write_jsonl(gold / "knowledge_units.jsonl", UNITS)
    (gold / "manifest.json").write_text("{}", encoding="utf-8")
    (root / "config").mkdir()
    shutil.copy(PROJECT_ROOT / "config" / "agent.toml", root / "config" / "agent.toml")

    # Act
    first = main(["build-structured"], project_root=root)
    second = main(["build-structured"], project_root=root)
    forced = main(["build-structured", "--force"], project_root=root)

    # Assert
    assert (first, second, forced) == (0, 2, 0)
    manifest = json.loads(
        (root / "data" / "module2" / "structured" / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["fact_count"] == 5


def test_cli_build_structured_without_gold_returns_3(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "config").mkdir()
    shutil.copy(PROJECT_ROOT / "config" / "agent.toml", tmp_path / "config" / "agent.toml")

    # Act / Assert
    assert main(["build-structured"], project_root=tmp_path) == 3
