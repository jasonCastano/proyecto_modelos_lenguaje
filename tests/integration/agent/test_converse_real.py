"""Conversación guiada con el modelo real (spec 020, T043). Marcada ``network``."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent import converse_eval
from proyecto_modelos_lenguaje.agent.converse_eval import run_converse

pytestmark = pytest.mark.network


def test_converse_with_deepseek_meets_the_hard_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    profiles = converse_eval.load_profiles()[:1]
    monkeypatch.setattr(converse_eval, "load_profiles", lambda: profiles)
    report = run_converse(mode="real", variants=("chain",), simulate=True, repeats=3)
    guided = report["summary"]["chain"]["guided"]
    assert report["meets_hard"], (guided["hard"], guided["violations"])
    assert guided["judged_by"] == "llm"
    assert all("judge_error" not in row for row in guided["simulated"])
    assert all(1 <= score["naturalness"] <= 5 for score in guided["simulated"][0]["scores"])
