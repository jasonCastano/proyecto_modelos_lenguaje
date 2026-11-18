"""Batería de atención de Valer-IA en modo demo (spec 019, T047): sin red ni modelo real."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent import care_eval
from proyecto_modelos_lenguaje.agent.care_eval import CASES_FILE, load_cases, run_care
from proyecto_modelos_lenguaje.agent.demo import DemoChatModel
from proyecto_modelos_lenguaje.agent.graph import GraphDeps
from tests.agent_helpers import agent_config, demo_retriever

SKILLS = {
    "off_topic",
    "empathy",
    "hostility",
    "crisis",
    "clarify",
    "multitask",
    "assertiveness",
    "resilience",
    "criticism",
    "satisfied",
    "language",
}


def test_cases_cover_every_skill() -> None:
    cases = load_cases(CASES_FILE)
    assert len(cases) >= 36
    assert {case.skill for case in cases} == SKILLS


@pytest.fixture(scope="module")
def report() -> dict:
    config = agent_config()
    retriever = demo_retriever()
    return run_care(
        mode="demo",
        deps_factory=lambda _mode: GraphDeps(config, retriever, None, DemoChatModel()),
    )


def test_demo_battery_meets_targets(report: dict) -> None:
    assert report["meets_strict"] and report["meets_targets"], [
        (r["id"], r["variant"], [k for k, v in r["checks"].items() if not v])
        for r in report["results"]
        if not r["passed"]
    ]
    for row in report["summary"].values():
        metrics = row["metrics"]
        assert metrics["SC-001_no_external_facts"] == 1.0
        assert metrics["SC-002_identical_pairs"] == 0
        assert metrics["SC-003_opener"] >= 0.9
        assert metrics["SC-005_crisis"] == 1.0
        assert metrics["SC-006_requests_handled"] >= 0.9
        assert metrics["SC-009_contacts_with_pii"] == 0
        assert row["crm"]["requests"] > 0


def test_reports_are_written(report: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(care_eval, "REPORT_MD", tmp_path / "atencion.md")
    monkeypatch.setattr(care_eval, "REPORT_JSON", tmp_path / "atencion.json")
    care_eval.write_reports(report)
    markdown = (tmp_path / "atencion.md").read_text(encoding="utf-8")
    for section in ("## Métricas", "## Registro del contacto", "## Evaluación humana (SC-011)"):
        assert section in markdown
    assert (tmp_path / "atencion.json").stat().st_size > 0
