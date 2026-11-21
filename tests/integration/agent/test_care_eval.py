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


@pytest.mark.parametrize("conversation_mode", ["scripted", "guided"])
def test_battery_runs_in_both_conversation_modes(conversation_mode: str) -> None:
    """Spec 020 (R16, T051): en el modo guiado la batería evalúa intención, no texto literal."""
    config = agent_config(conversation_mode)
    retriever = demo_retriever()
    result = run_care(
        mode="demo",
        variants=("chain",),
        config=config,
        deps_factory=lambda _mode: GraphDeps(config, retriever, None, DemoChatModel()),
    )
    assert result["conversation_mode"] == conversation_mode
    assert result["meets_strict"] and result["meets_targets"], [
        (r["id"], [k for k, v in r["checks"].items() if not v])
        for r in result["results"]
        if not r["passed"]
    ]


def test_guided_checks_accept_intent_instead_of_literal_text() -> None:
    from proyecto_modelos_lenguaje.agent.prompts import load_care

    case = care_eval.CareCase(
        "x", "off_topic", ["¿clima?"], {"mentions": ["clima"], "opener": True}
    )
    answer = "Lamento no poder ayudarte con el pronóstico del tiempo; lo mío es Manuelita."
    literal = care_eval.check(case, [answer], None, load_care(), guided=False)
    guided = care_eval.check(case, [answer], None, load_care(), guided=True)
    assert not literal["mentions"] and not literal["opener"]
    assert guided["mentions"] and guided["opener"]


def test_guided_forbidden_terms_ignore_negations() -> None:
    """Spec 020 (R16): «no me invento los ingredientes» no afirma una receta."""
    from proyecto_modelos_lenguaje.agent.prompts import load_care

    case = care_eval.CareCase(
        "x", "off_topic", ["Dame una receta"], {"forbidden": ["ingredientes"]}
    )
    refused = "Recetas no tengo, así que no me invento los ingredientes. Lo mío es Manuelita."
    recipe = "Necesitas estos ingredientes: harina y azúcar."
    assert care_eval.check(case, [refused], None, load_care(), guided=True)["no_external_facts"]
    assert not care_eval.check(case, [recipe], None, load_care(), guided=True)["no_external_facts"]
    assert not care_eval.check(case, [refused], None, load_care(), guided=False)[
        "no_external_facts"
    ]
