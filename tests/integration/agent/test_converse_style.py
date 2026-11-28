"""Estilo caleño de punta a punta en demo y evaluación ``--style`` (spec 036, T026 y T030)."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.agent.converse_eval import (
    STYLE_FILE,
    TurnRecord,
    load_conversations,
    render_style_markdown,
    run_style,
    style_checks,
    write_style_reports,
)
from proyecto_modelos_lenguaje.agent.graph import GraphDeps
from proyecto_modelos_lenguaje.agent.router import rule_decision
from proyecto_modelos_lenguaje.agent.style import find_expressions, level_for
from tests.agent_helpers import agent_config, demo_retriever


def record(answer: str) -> TurnRecord:
    return TurnRecord("hola", answer, "smalltalk", "direct", None, False, "show", [], [], None, 0)


def factory():
    retriever = demo_retriever()
    config = agent_config("guided")

    def build(_mode: str) -> GraphDeps:
        from proyecto_modelos_lenguaje.agent.demo import DemoChatModel

        return GraphDeps(config, retriever, None, DemoChatModel())

    return config, build


def subset(tmp_path: Path, ids: set[str]) -> Path:
    lines = [
        line
        for line in STYLE_FILE.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["id"] in ids
    ]
    path = tmp_path / "caleno.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_style_fixture_has_fourteen_conversations_without_personal_data() -> None:
    cases = load_conversations(STYLE_FILE)
    assert len(cases) == 14
    raw = STYLE_FILE.read_text(encoding="utf-8")
    assert "+57" not in raw and "@" not in raw
    assert any(turn.get("voice") for case in cases for turn in case.turns)


def test_style_checks_flag_banned_excess_off_and_repeat() -> None:
    expect = {
        "no_banned": True,
        "max_expressions": 1,
        "style_off": True,
        "no_style_repeat": True,
        "style_used": True,
    }
    bad = record("Listo pues, parce. ¡Uy, qué nota!")
    checks = style_checks(expect, bad, [record("Listo pues, te cuento.")])
    assert not checks["no_banned"] and not checks["max_expressions"]
    assert not checks["style_off"] and not checks["no_style_repeat"] and checks["style_used"]
    good = record("Con mucho gusto te cuento de Manuelita.")
    assert all(style_checks(expect | {"style_used": False}, good, []).values())


def test_meaning_and_plain_requests_are_conversation_turns() -> None:
    meaning = rule_decision('¿qué significa "ve"?')
    assert meaning is not None and meaning.route == "direct" and meaning.act == "smalltalk"
    plain = rule_decision("habla normal, por favor")
    assert plain is not None and plain.route == "direct"
    company = rule_decision("¿qué es lo que hace Manuelita, pues?")
    assert company is None or company.act != "smalltalk"


def test_low_mood_turns_style_off() -> None:
    class Plan:
        language, sentiment, act, reason, register = "es", "neutral", "smalltalk", None, "formal"

    assert level_for(Plan(), {}, "tuve un día terrible, me siento muy mal") == "off"


def test_demo_style_report_meets_the_targets(tmp_path: Path) -> None:
    config, build = factory()
    path = subset(tmp_path, {"c02", "c08", "c09", "c10", "c14"})
    report = run_style(
        mode="demo", variants=("chain",), config=config, deps_factory=build, path=path
    )
    row = report["summary"]["chain"]
    assert not any(row["flags"].values()), row["flagged_turns"]
    conversations = {c["id"]: c for c in row["conversations"]}
    # «habla normal»: ni ese turno ni los siguientes llevan expresiones (FR-009).
    plain_turns = conversations["c09"]["turns"][1:]
    assert all(not find_expressions(t["assistant"]) for t in plain_turns)
    assert "sin modismos" in plain_turns[0]["assistant"]
    # «¿qué significa "ve"?»: explicación breve y regreso a Manuelita (FR-010).
    meaning = conversations["c08"]["turns"][1]["assistant"]
    assert "Manuelita" in meaning and ("oye" in meaning or "cariño" in meaning)
    markdown = render_style_markdown(report)
    assert "Prueba humana (SC-007)" in markdown and "SC-001" in markdown
    out = tmp_path / "caleno.json"
    write_style_reports(report, out)
    assert json.loads(out.read_text(encoding="utf-8"))["prompts"]["caleno"]["sha256"]
    assert out.with_suffix(".md").exists()
