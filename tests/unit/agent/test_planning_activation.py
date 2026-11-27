"""Activación del planificador por contexto (spec 028, T041, SC-007)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent.planning_activation import (
    TARGET,
    evaluate,
    load_cases,
    render_markdown,
    summarize,
)


def test_fixture_has_15_planning_15_similar_and_follow_ups() -> None:
    cases = load_cases()
    plain = [case for case in cases if not case.get("follow_up")]
    assert sum(case["expected"] for case in plain) == 15
    assert sum(not case["expected"] for case in plain) == 15
    assert sum(bool(case.get("follow_up")) for case in cases) >= 3


def test_meets_the_target_on_both_sides() -> None:
    summary = summarize(evaluate())
    assert summary["planning_hits"] >= TARGET and summary["non_planning_hits"] >= TARGET
    assert summary["follow_up_hits"] == summary["follow_up_total"]
    assert summary["meets_target"] is True


def test_follow_ups_need_a_previous_planning_turn() -> None:
    for result in evaluate():
        if result.follow_up and result.case_id != "f02":  # «pol de 12» ya es señal propia
            assert not result.activated_without_context, result.case_id


def test_markdown_report_lists_every_case() -> None:
    results = evaluate()
    text = render_markdown(results, summarize(results))
    assert "Resultado: ✅ cumple" in text
    assert all(f"| {r.case_id} |" in text for r in results)
