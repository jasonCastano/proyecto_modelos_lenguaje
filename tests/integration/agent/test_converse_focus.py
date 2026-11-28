"""Evaluación ``agent converse --focus`` en modo demo (spec 035, T020)."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.agent.converse_eval import (
    FOCUS_FILE,
    FOCUS_KEYS,
    TurnRecord,
    check_turn,
    load_conversations,
    render_focus_markdown,
    run_focus,
    write_focus_reports,
)
from proyecto_modelos_lenguaje.agent.graph import GraphDeps
from tests.agent_helpers import agent_config, demo_retriever

FOCUS = dict.fromkeys(FOCUS_KEYS, True)


def record(answer: str) -> TurnRecord:
    return TurnRecord("hola", answer, "smalltalk", "direct", None, False, "show", [], [], None, 0)


def factory():
    retriever = demo_retriever()
    config = agent_config("guided")

    def build(_mode: str) -> GraphDeps:
        from proyecto_modelos_lenguaje.agent.demo import DemoChatModel

        return GraphDeps(config, retriever, None, DemoChatModel())

    return config, build


def test_focus_fixture_has_sixteen_pseudonymized_conversations() -> None:
    cases = load_conversations(FOCUS_FILE)
    assert len(cases) == 16
    raw = FOCUS_FILE.read_text(encoding="utf-8")
    assert "+57" not in raw and "Deportivo" not in raw  # sin número ni equipo de la prueba
    first = cases[0]
    assert first.id == "f01" and len(first.turns) == 7
    keys = {key for case in cases for turn in case.turns for key in turn["expect"]}
    assert set(FOCUS_KEYS) <= keys and "max_sentences" in keys


def test_check_turn_supports_the_focus_keys() -> None:
    bad = record("Claro, charlar también se vale. ¿Cómo te fue en el partido?")
    checks = check_turn(FOCUS, bad, [], {})
    assert not checks["no_chat_invite"] and not checks["no_offtopic_question"]
    assert not checks["redirects"] and checks["no_rejection"]
    good = record("¡Qué buen plan! Si quieres, te cuento de la historia de Manuelita.")
    assert all(check_turn(FOCUS, good, [], {}).values())
    again = record("Gracias por contarme. Si quieres, te cuento de la historia de Manuelita.")
    assert not check_turn(FOCUS, again, [good], {})["no_closing_repeat"]
    assert "redirects" not in check_turn({}, bad, [], {})


def test_demo_focus_report_has_zero_flags(tmp_path: Path) -> None:
    fixture = tmp_path / "focus.jsonl"
    lines = FOCUS_FILE.read_text(encoding="utf-8").splitlines()
    fixture.write_text("\n".join(lines[:3]) + "\n", encoding="utf-8")  # f01–f03
    config, build = factory()
    report = run_focus(
        mode="demo", variants=("chain",), config=config, deps_factory=build, path=fixture
    )
    row = report["summary"]["chain"]
    assert set(row["flags"]) == {*FOCUS_KEYS, "max_sentences"}
    assert row["checked"]["redirects"] > 0
    assert report["meets"], row["flagged_turns"]
    assert report["prompts"]["converse"]["version"] == "1.2"
    markdown = render_focus_markdown(report)
    assert "Invitaciones a charlar" in markdown and "cumple" in markdown
    out = tmp_path / "enfoque.json"
    write_focus_reports(report, out)
    assert json.loads(out.read_text(encoding="utf-8"))["meets"] is True
    assert out.with_suffix(".md").exists()
