"""Conducta de Valer-IA con el modelo real (spec 018, T031). Marcada ``network``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.conduct import CASES_FILE, run_conduct

pytestmark = pytest.mark.network

REPRESENTATIVE = {"c05", "c04", "c07", "c13", "c15", "c21"}


def test_representative_cases_with_deepseek(tmp_path: Path) -> None:
    cases = [
        line
        for line in CASES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line)["id"] in REPRESENTATIVE
    ]
    subset = tmp_path / "cases.jsonl"
    subset.write_text("\n".join(cases) + "\n", encoding="utf-8")
    report = run_conduct(mode="real", cases_path=subset)
    leaks = [r for r in report["results"] if r["leaks"]]
    assert not leaks, leaks
    for row in report["summary"].values():
        assert row["leaks"] == 0
