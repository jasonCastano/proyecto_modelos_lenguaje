"""El informe de ``agent shield`` cumple su esquema (spec 015, shield-report.schema.json)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from proyecto_modelos_lenguaje.agent.shield import run_shield
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

CONTRACTS = PROJECT_ROOT / "specs" / "015-rag-injection-shield-real" / "contracts"
SCHEMA = json.loads((CONTRACTS / "shield-report.schema.json").read_text(encoding="utf-8"))


def test_demo_report_satisfies_schema_and_passes(monkeypatch, tmp_path: Path) -> None:
    # Arrange: modo demo, sin red; el estado no debe escribirse en ningún lado
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    # Act
    report = run_shield(mode="demo", variants=("chain", "agent"), repeat=1, run_id="contract")
    # Assert
    jsonschema.validate(report, SCHEMA)
    assert len(report["results"]) == 12  # 6 casos × 2 variantes
    assert all(result["passed"] for result in report["results"]), report["results"]
    assert not (tmp_path / "state").exists()


def test_baseline_report_marks_no_neutralization(monkeypatch, tmp_path: Path) -> None:
    # Arrange
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    # Act
    report = run_shield(mode="demo", variants=("chain",), neutralize=False, run_id="base")
    # Assert
    jsonschema.validate(report, SCHEMA)
    assert report["neutralize"] is False
    assert all(result["neutralized"] == 0 for result in report["results"])
