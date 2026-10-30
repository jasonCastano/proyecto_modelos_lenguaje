"""Unit tests for the canonical scrape entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.config import load_config
from proyecto_modelos_lenguaje.entrypoint import (
    CAMPAIGN_PATTERN,
    EffectiveParameters,
    EntryError,
    ScrapeOutcome,
    ScrapeRequest,
    assess_campaign_state,
    main,
    parse_request,
    render_human,
    render_json,
    validate_request,
)


def _config(tmp_path: Path, write_config):
    path = write_config("http://127.0.0.1:1")
    return load_config(path, project_root=tmp_path)


def _catalog(config):
    catalog = Catalog(config.settings.bronze_dir / "_meta" / "bronze.sqlite3")
    catalog.init_schema()
    return catalog


def test_campaign_pattern_accepts_safe_identifiers() -> None:
    assert CAMPAIGN_PATTERN.fullmatch("2026-10-m1-02-smoke")
    assert CAMPAIGN_PATTERN.fullmatch("c001")
    assert not CAMPAIGN_PATTERN.fullmatch("../escape")
    assert not CAMPAIGN_PATTERN.fullmatch("with space")
    assert not CAMPAIGN_PATTERN.fullmatch(".hidden")


def test_parse_request_reads_all_options() -> None:
    request = parse_request(
        [
            "--config",
            "custom.toml",
            "--campaign",
            "c001",
            "--resume",
            "--limit",
            "3",
            "--dry-run",
            "--json",
        ]
    )
    assert request == ScrapeRequest(
        config_path="custom.toml",
        campaign_id="c001",
        resume=True,
        limit=3,
        dry_run=True,
        json_output=True,
    )


def test_parse_request_without_campaign_is_allowed() -> None:
    request = parse_request([])
    assert request.campaign_id is None
    assert request.config_path == "config/sources.toml"


def test_parse_request_rejects_non_integer_limit() -> None:
    with pytest.raises(EntryError) as excinfo:
        parse_request(["--limit", "abc"])
    assert excinfo.value.code == "invalid_limit"


def test_validate_request_rejects_unsafe_campaign() -> None:
    request = ScrapeRequest("config/sources.toml", "../escape", False, None, False, True)
    with pytest.raises(EntryError) as excinfo:
        validate_request(request, project_root=Path.cwd())
    assert excinfo.value.code == "invalid_campaign"


def test_validate_request_rejects_missing_config(tmp_path: Path) -> None:
    request = ScrapeRequest("missing.toml", "c001", False, None, False, True)
    with pytest.raises(EntryError) as excinfo:
        validate_request(request, project_root=tmp_path)
    assert excinfo.value.code == "missing_config"


def test_validate_request_rejects_invalid_config(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("[settings\n", encoding="utf-8")
    request = ScrapeRequest(str(path), "c001", False, None, False, True)
    with pytest.raises(EntryError) as excinfo:
        validate_request(request, project_root=tmp_path)
    assert excinfo.value.code == "invalid_config"


def test_validate_request_rejects_zero_limit(tmp_path: Path, write_config) -> None:
    config = _config(tmp_path, write_config)
    request = ScrapeRequest(str(config.path), "c001", False, 0, False, True)
    with pytest.raises(EntryError) as excinfo:
        validate_request(request, project_root=tmp_path)
    assert excinfo.value.code == "invalid_limit"


@pytest.mark.parametrize(
    ("status", "expected_action"),
    [
        ("planned", "resume"),
        ("paused", "resume"),
        ("failed", "resume"),
        ("running", "campaign_running"),
        ("completed", "noop_completed"),
        ("aborted", "campaign_aborted"),
    ],
)
def test_assess_campaign_state_matrix(
    tmp_path: Path, write_config, status: str, expected_action: str
) -> None:
    config = _config(tmp_path, write_config)
    catalog = _catalog(config)
    try:
        catalog.create_campaign(
            campaign_id=f"c-{status}", config_hash="a" * 64, tool_version="test"
        )
        catalog.set_campaign_status(f"c-{status}", status)
    finally:
        catalog.close()
    assessment = assess_campaign_state(config, f"c-{status}", resume=False)
    assert assessment.action == expected_action


def test_assess_missing_campaign_creates_or_errors(tmp_path: Path, write_config) -> None:
    config = _config(tmp_path, write_config)
    created = assess_campaign_state(config, "c-new", resume=False)
    assert created.action == "create"
    missing_resume = assess_campaign_state(config, "c-new", resume=True)
    assert missing_resume.action == "missing_campaign_for_resume"
    assert missing_resume.exit_code == 2


def _outcome() -> ScrapeOutcome:
    return ScrapeOutcome(
        schema_version="1.0",
        campaign_id="c001",
        status="completed",
        mode="new",
        effective=EffectiveParameters(
            config="config/sources.toml",
            campaign="c001",
            resume=False,
            limit=3,
            dry_run=False,
            mode="new",
        ),
        summary={
            "targets_discovered": 10,
            "artifacts_stored": 3,
            "deduplicated": 1,
            "excluded": 2,
            "failed": 0,
            "deferred": 1,
            "bytes_stored": 1234,
            "storage_limit_bytes": 10000,
            "coverage": {"covered": 1},
            "report_paths": ["data/bronze/reports/c001/coverage.md"],
        },
        policy={
            "allowed": 1,
            "disallowed": 1,
            "unreachable": 0,
            "by_reason": {"allowed_by_robots": 1, "disallowed_by_robots": 1},
        },
        duration_seconds=1.25,
        exit_code=0,
    )


def test_render_human_contains_metrics() -> None:
    text = render_human(_outcome())
    assert "Campaña: c001" in text
    assert "Estado: completed" in text
    assert "Almacenados: 3" in text
    assert "Omitidos: 4" in text
    assert "Duración: 1.25 s" in text
    assert "Políticas: permitidas=1, bloqueadas=1, inalcanzables=0" in text


def test_render_json_is_valid_object() -> None:
    payload = json.loads(render_json(_outcome()))
    assert payload["campaign_id"] == "c001"
    assert payload["mode"] == "new"
    assert payload["summary"]["artifacts_stored"] == 3


def test_main_without_arguments_prints_help(capsys) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "--campaign" in captured.out


def test_main_help_returns_zero(capsys) -> None:
    assert main(["--help"]) == 0
    assert "usage:" in capsys.readouterr().out


def test_main_invalid_campaign_emits_json(capsys) -> None:
    assert main(["--campaign", "../escape", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_campaign"
    assert payload["exit_code"] == 2


def test_main_missing_config_emits_json(tmp_path: Path, capsys) -> None:
    assert (
        main(
            ["--config", "missing.toml", "--campaign", "c001", "--json"],
            project_root=tmp_path,
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"]["code"] == "missing_config"
