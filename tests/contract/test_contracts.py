"""Contract tests for CLI JSON payloads and reports."""

from __future__ import annotations

import asyncio
import json
import tomllib

import jsonschema

from proyecto_modelos_lenguaje.catalog import artifact_payload
from proyecto_modelos_lenguaje.reporting import coverage_payload
from tests.conftest import PROJECT_ROOT, build_runner

CONTRACTS = PROJECT_ROOT / "specs" / "001-bronze-web-scraping" / "contracts"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_artifact_payload_matches_schema(app_config) -> None:
    runner, catalog, _ = build_runner(app_config)
    try:
        asyncio.run(runner.run("c001"))
        artifacts, _ = catalog.list_artifacts(campaign_id="c001", limit=10)
        assert artifacts
        for artifact in artifacts:
            jsonschema.validate(artifact_payload(artifact), _schema("artifact.schema.json"))
    finally:
        catalog.close()


def test_coverage_report_matches_schema(app_config) -> None:
    runner, catalog, _ = build_runner(app_config)
    try:
        asyncio.run(runner.run("c001"))
        payload = coverage_payload(catalog, "c001")
    finally:
        catalog.close()
    jsonschema.validate(payload, _schema("coverage-report.schema.json"))


def test_campaign_report_matches_schema(app_config) -> None:
    runner, catalog, _ = build_runner(app_config)
    try:
        asyncio.run(runner.run("c001"))
    finally:
        catalog.close()
    path = app_config.settings.bronze_dir / "reports" / "c001" / "campaign.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, _schema("campaign-report.schema.json"))


def test_real_config_matches_source_schema() -> None:
    path = PROJECT_ROOT / "config" / "sources.toml"
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    jsonschema.validate(payload, _schema("source-config.schema.json"))
