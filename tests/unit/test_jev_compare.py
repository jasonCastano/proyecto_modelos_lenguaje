"""Comparación sin/con gatekeeper Jev, offline (spec 022, US4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proyecto_modelos_lenguaje.agent.__main__ import main
from proyecto_modelos_lenguaje.agent.config import JevConfig
from proyecto_modelos_lenguaje.agent.jev import FakeJevGate
from proyecto_modelos_lenguaje.agent.jev_eval import (
    SECTION_START,
    compare,
    render_report,
    write_reports,
)
from tests.agent_helpers import ScriptedModel, agent_config

LLM = json.dumps({"route": "documental", "confidence": 0.8, "reason": "narrativa"})


def _care(cfg: Any) -> dict[str, Any]:
    enabled = cfg.jev.enabled
    rows = [
        {
            "variant": "chain",
            "id": "c01",
            "passed": True,
            "skill": "crisis",
            "decided_by": "rules",
            "jev": {"status": "ok", "cost": 0.0001} if enabled else None,
        },
        {
            "variant": "chain",
            "id": "a01",
            "passed": not enabled,
            "skill": "off_topic",
            "decided_by": "jev" if enabled else "llm",
            "jev": {"status": "ok", "cost": 0.0001} if enabled else None,
        },
    ]
    summary = {
        "cases": 2,
        "passed": 2,
        "metrics": {"SC-005_crisis": 1.0, "SC-004_cordial": 1.0},
        "first_word_ms": 900.0,
    }
    return {"summary": {"chain": summary}, "results": rows}


def _data() -> dict[str, Any]:
    return compare(
        FakeJevGate(JevConfig(enabled=True)),
        JevConfig(enabled=True),
        model=ScriptedModel(reply=LLM),
        agent_config=agent_config(),
        care_runner=_care,
        run_id="jev-test",
    )


def test_compare_reports_both_configurations_and_every_metric() -> None:
    data = _data()
    base, jev = data["router"]["baseline"], data["router"]["jev"]
    assert base["cases"] == jev["cases"] == 44
    assert jev["gate"]["calls"] > 0 and jev["gate"]["decided"] > 0
    assert jev["model_calls"] < base["model_calls"]
    assert base["gate"]["calls"] == 0
    assert {"accuracy", "latency_ms_mean", "latency_ms_p95", "no_search"} <= set(jev)
    assert data["validation"]["total"] == 24
    assert data["care"]["jev"]["decided_by_jev"] == 1
    assert data["care"]["baseline"]["gate_calls"] == 0
    assert data["care"]["jev"]["failed_cases"] == ["a01 (jev)"]
    assert data["cost_usd"] >= 0.0002
    meta = data["meta"]
    assert {"run_id", "created_at", "model", "route_threshold", "commit"} <= set(meta)
    assert meta["run_id"] == "jev-test"


def test_reports_are_written_with_the_module2_section(tmp_path: Path) -> None:
    data = _data()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "evaluacion_modulo2.md").write_text("# Evaluación\n", encoding="utf-8")
    write_reports(data, tmp_path)
    write_reports(data, tmp_path)  # idempotente: reemplaza la sección

    module2 = (tmp_path / "docs" / "evaluacion_modulo2.md").read_text(encoding="utf-8")
    assert module2.startswith("# Evaluación") and module2.count(SECTION_START) == 1
    markdown = (tmp_path / "docs" / "evaluacion_jev.md").read_text(encoding="utf-8")
    assert "Sin Jev" in markdown and "Con Jev" in markdown and "Validación en español" in markdown
    assert json.loads((tmp_path / "docs" / "evaluacion_jev.json").read_text(encoding="utf-8"))
    assert render_report(data) == markdown


def test_compare_without_key_exits_with_an_actionable_message(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "proyecto_modelos_lenguaje.agent.jev.read_api_key", lambda environ=None: None
    )
    assert main(["jev", "--compare"]) == 2
    assert "TYPESAFE_API_KEY" in capsys.readouterr().err
    assert main(["jev", "--validate"]) == 2
