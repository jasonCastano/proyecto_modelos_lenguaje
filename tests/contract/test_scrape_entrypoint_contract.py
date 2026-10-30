"""Contract tests for the canonical scrape entry point."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from jsonschema import Draft202012Validator

from proyecto_modelos_lenguaje.entrypoint import (
    EffectiveParameters,
    EntryError,
    ScrapeOutcome,
    build_parser,
    render_json,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "specs" / "005-scrape-empresa-entrypoint" / "contracts"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def _outcome() -> ScrapeOutcome:
    return ScrapeOutcome(
        schema_version="1.0",
        campaign_id="2026-10-m1-02-smoke",
        status="completed",
        mode="new",
        effective=EffectiveParameters(
            config="config/sources.toml",
            campaign="2026-10-m1-02-smoke",
            resume=False,
            limit=3,
            dry_run=False,
            mode="new",
        ),
        summary={
            "targets_discovered": 12,
            "artifacts_stored": 3,
            "deduplicated": 1,
            "excluded": 2,
            "failed": 0,
            "deferred": 0,
            "bytes_stored": 12345,
            "storage_limit_bytes": 10000000,
            "coverage": {"covered": 0, "partial": 0, "missing": 24},
            "report_paths": ["data/bronze/reports/2026-10-m1-02-smoke/coverage.md"],
        },
        policy={
            "allowed": 1,
            "disallowed": 1,
            "unreachable": 0,
            "by_reason": {"allowed_by_robots": 1, "disallowed_by_robots": 1},
        },
        duration_seconds=2.4,
        exit_code=0,
    )


def test_help_documents_every_option() -> None:
    help_text = build_parser().format_help()
    for option in ("--config", "--campaign", "--resume", "--limit", "--dry-run", "--json"):
        assert option in help_text


def test_success_payload_matches_schema() -> None:
    schema = _schema("scrape-summary.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(render_json(_outcome())))


def test_dry_run_payload_matches_schema() -> None:
    base = _outcome()
    outcome = replace(
        base,
        mode="dry_run",
        effective=replace(base.effective, dry_run=True),
        summary={**base.summary, "artifacts_stored": 0},
    )
    schema = _schema("scrape-summary.schema.json")
    Draft202012Validator(schema).validate(json.loads(render_json(outcome)))


def test_error_payload_matches_schema() -> None:
    schema = _schema("error.schema.json")
    Draft202012Validator.check_schema(schema)
    payload = EntryError("invalid_campaign", "Identificador inválido.", 2).to_dict()
    Draft202012Validator(schema).validate(payload)


def test_error_codes_cover_declared_contract() -> None:
    schema = _schema("error.schema.json")
    codes = set(schema["properties"]["error"]["properties"]["code"]["enum"])
    assert {
        "missing_config",
        "invalid_config",
        "invalid_campaign",
        "invalid_limit",
        "missing_campaign_for_resume",
        "campaign_running",
        "campaign_aborted",
        "pipeline_failure",
    } <= codes
