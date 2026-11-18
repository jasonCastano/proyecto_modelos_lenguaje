"""Habilidades de atención con el modelo real (spec 019, T047). Marcada ``network``."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.care_eval import run_care

pytestmark = pytest.mark.network


def test_care_battery_with_deepseek() -> None:
    report = run_care(mode="real", variants=("chain", "agent"))
    assert report["meets_strict"], [
        (r["id"], r["variant"], [k for k, v in r["checks"].items() if not v])
        for r in report["results"]
        if not r["passed"]
    ]
