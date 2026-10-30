"""Unit tests for the silver quality report."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.silver.models import RunReport
from proyecto_modelos_lenguaje.silver.reporting import render_quality_markdown, write_report


def _report() -> RunReport:
    return RunReport(
        schema_version="1.0",
        run_id="2026-10-silver-01",
        started_at="2026-10-29T00:00:00Z",
        finished_at="2026-10-29T00:01:00Z",
        status="completed",
        config_hash="a" * 64,
        cleaning_version="1.0.0",
        tool_version="0.2.0",
        git_commit=None,
        input_artifacts=10,
        processed=8,
        skipped=2,
        failed=0,
        documents=8,
        canonical_documents=7,
        alias_documents=1,
        chunks=40,
        duplicates_exact=1,
        duplicates_near=0,
        tokens_in=10000,
        tokens_out=9000,
        bytes_out=50000,
        duration_seconds=1.5,
        by_source={"official_site": 10},
        by_media_type={"text/html": 10},
        by_status={"processed": 8, "skipped": 2},
        skip_reasons={"no_text": 2},
        failure_reasons={},
        quality_flags={"no_text": 2},
        section_coverage={"with_title": 20, "without_title": 2},
        report_paths=[],
    )


def test_markdown_contains_counts() -> None:
    markdown = render_quality_markdown(_report())
    assert "# Reporte de calidad" in markdown
    assert "| official_site | 10 |" in markdown
    assert "| no_text | 2 |" in markdown
    assert "Con título: 20" in markdown


def test_write_report_creates_json_and_markdown(tmp_path: Path) -> None:
    paths = write_report(_report(), tmp_path)
    assert len(paths) == 2
    payload = json.loads((tmp_path / "2026-10-silver-01" / "quality.json").read_text())
    assert payload["documents"] == 8
    assert (tmp_path / "2026-10-silver-01" / "quality.md").is_file()
