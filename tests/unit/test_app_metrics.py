"""Unit and contract tests for the app metrics."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from jsonschema import Draft202012Validator

from proyecto_modelos_lenguaje.app_metrics import (
    format_metric,
    load_app_metrics,
    metric_rows,
    response_rows,
    status_rows,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

SCHEMA = PROJECT_ROOT / "specs" / "008-streamlit-qa-app" / "contracts" / "app-metrics.schema.json"


def _make_data(root: Path) -> None:
    gold = root / "data" / "gold"
    silver = root / "data" / "silver"
    bronze = root / "data" / "bronze" / "_meta"
    (gold / "reports" / "2026-10-gold-01").mkdir(parents=True)
    (silver / "reports" / "2026-10-silver-01").mkdir(parents=True)
    bronze.mkdir(parents=True)
    (gold / "knowledge_units.jsonl").write_text("{}\n", encoding="utf-8")
    (gold / "context_8000.json").write_text('{"blocks": []}', encoding="utf-8")
    (gold / "faq_seeds.jsonl").write_text("{}\n", encoding="utf-8")
    coverage = {
        "items": [{"item_id": f"I-{index:02d}", "status": "covered"} for index in range(1, 25)]
    }
    (gold / "coverage.json").write_text(json.dumps(coverage), encoding="utf-8")
    manifest = {
        "run_id": "2026-10-gold-01",
        "knowledge_units": 15211,
        "facts": 381,
        "entities": 15,
        "conflicts": 38,
        "files": [],
    }
    (gold / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    gold_report = {
        "run_id": "2026-10-gold-01",
        "units": 15211,
        "facts": 381,
        "entities": 15,
        "conflicts": 38,
        "tokens": 1000109,
    }
    (gold / "reports" / "2026-10-gold-01" / "quality.json").write_text(
        json.dumps(gold_report), encoding="utf-8"
    )
    silver_report = {
        "run_id": "2026-10-silver-01",
        "canonical_documents": 404,
        "alias_documents": 92,
        "chunks": 3810,
        "tokens_out": 1447841,
        "skipped": 61,
        "skip_reasons": {
            "no_text": 35,
            "scanned_pdf": 10,
            "encrypted_pdf": 6,
            "navigation_artifact": 10,
        },
    }
    (silver / "reports" / "2026-10-silver-01" / "quality.json").write_text(
        json.dumps(silver_report), encoding="utf-8"
    )
    connection = sqlite3.connect(bronze / "bronze.sqlite3")
    try:
        connection.execute("CREATE TABLE v_active_artifacts (id INTEGER)")
        connection.executemany("INSERT INTO v_active_artifacts (id) VALUES (?)", [(1,), (2,)])
        connection.commit()
    finally:
        connection.close()


def test_loads_complete_metrics(tmp_path: Path) -> None:
    _make_data(tmp_path)
    metrics = load_app_metrics(project_root=tmp_path)
    assert metrics.data_status == "complete"
    assert metrics.active_artifacts == 2
    assert metrics.canonical_documents == 404
    assert metrics.aliases == 92
    assert metrics.chunks == 3810
    assert metrics.units == 15211
    assert metrics.facts == 381
    assert metrics.entities == 15
    assert metrics.conflicts == 38
    assert metrics.coverage_covered == 24
    assert metrics.coverage_total == 24
    assert metrics.silver_tokens == 1447841
    assert metrics.gold_tokens == 1000109
    assert metrics.skipped == 61
    assert metrics.omissions == 61
    assert metrics.silver_run == "2026-10-silver-01"
    assert metrics.gold_run == "2026-10-gold-01"
    assert metrics.detail is None


def test_lfs_pointer_marks_data_incomplete(tmp_path: Path) -> None:
    _make_data(tmp_path)
    (tmp_path / "data" / "gold" / "knowledge_units.jsonl").write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 10\n",
        encoding="utf-8",
    )
    metrics = load_app_metrics(project_root=tmp_path)
    assert metrics.data_status == "incomplete"
    assert metrics.detail is not None
    assert "puntero LFS" in metrics.detail


def test_missing_report_marks_data_incomplete(tmp_path: Path) -> None:
    _make_data(tmp_path)
    (tmp_path / "data" / "silver" / "reports" / "2026-10-silver-01" / "quality.json").unlink()
    metrics = load_app_metrics(project_root=tmp_path)
    assert metrics.data_status == "incomplete"
    assert "reporte de plata" in (metrics.detail or "")


def test_metric_rows_and_status_rows(tmp_path: Path) -> None:
    _make_data(tmp_path)
    metrics = load_app_metrics(project_root=tmp_path)
    rows = metric_rows(metrics)
    assert len(rows) >= 8
    assert any(row.label == "Artefactos activos" for row in rows)
    status = status_rows(metrics, model_status="demo", demo_mode=True)
    assert any(row.label == "Datos" for row in status)
    assert any(row.label == "Modelo" for row in status)
    assert format_metric(15211) == "15.211"


def test_response_rows_have_seven_metrics() -> None:
    rows = response_rows(
        model="llama3.1:8b",
        prompt_version="1.0.0",
        latency_seconds=1.234,
        citations=3,
        status="ok",
        input_tokens=1200,
        output_tokens=240,
    )
    assert [row.label for row in rows] == [
        "Modelo",
        "Prompt",
        "Latencia",
        "Citas",
        "Estado",
        "Tokens entrada",
        "Tokens salida",
    ]
    assert rows[2].value == "1.23 s"
    assert rows[3].value == "3"
    assert rows[5].value == "1.200"


def test_manifest_mismatch_marks_data_incomplete(tmp_path: Path) -> None:
    _make_data(tmp_path)
    (tmp_path / "data" / "gold" / "manifest.json").write_text(
        json.dumps({"run_id": "2026-10-gold-99"}), encoding="utf-8"
    )
    metrics = load_app_metrics(project_root=tmp_path)
    assert metrics.data_status == "incomplete"
    assert "manifest.json" in (metrics.detail or "")


def test_metrics_match_contract(tmp_path: Path) -> None:
    _make_data(tmp_path)
    metrics = load_app_metrics(project_root=tmp_path)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(metrics.to_dict())
