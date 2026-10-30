"""Unit tests for gold reporting."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.gold.models import GoldReport
from proyecto_modelos_lenguaje.gold.reporting import render_quality_markdown, write_report


def _report() -> GoldReport:
    return GoldReport(
        schema_version="1.0",
        run_id="2026-10-gold-01",
        started_at="2026-10-30T00:00:00Z",
        finished_at="2026-10-30T00:01:00Z",
        status="completed",
        config_hash="a" * 64,
        input_documents=404,
        input_chunks=3810,
        processed=400,
        skipped=4,
        failed=0,
        units=1000,
        facts=100,
        entities=50,
        conflicts=2,
        coverage={"covered": 20, "partial": 3, "missing": 1},
        context_packs=2,
        tokens=40000,
        duration_seconds=1.5,
        quality_flags={"topic_uncertain": 10},
        skip_reasons={"no_units": 4},
        failure_reasons={},
        report_paths=[],
    )


def test_markdown_contains_counts() -> None:
    markdown = render_quality_markdown(_report())
    assert "# Reporte de calidad" in markdown
    assert "Unidades: 1000" in markdown
    assert "| topic_uncertain | 10 |" in markdown


def test_write_report_creates_files(tmp_path: Path) -> None:
    paths = write_report(_report(), tmp_path)
    assert len(paths) == 2
    assert (tmp_path / "2026-10-gold-01" / "quality.json").is_file()
    assert (tmp_path / "2026-10-gold-01" / "quality.md").is_file()
