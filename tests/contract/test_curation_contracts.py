"""Contract tests for curation payloads and schemas."""

from __future__ import annotations

import json
import tomllib

import jsonschema

from tests.conftest import PROJECT_ROOT

CONTRACTS = PROJECT_ROOT / "specs" / "002-manuelita-relevance-filter" / "contracts"


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def _evaluation_payload(catalog, artifact_id: int) -> dict:
    evaluation = catalog.get_evaluation(artifact_id)
    artifact = catalog.get_artifact(artifact_id)
    return {
        "schema_version": "1.0",
        "artifact_id": artifact_id,
        "run_id": evaluation["run_id"],
        "source_id": artifact.source_id,
        "url_canonical": artifact.url_canonical,
        "title": artifact.title,
        "decision": evaluation["decision"],
        "level": evaluation["level"],
        "score": evaluation["score"],
        "method": evaluation["method"],
        "explanation": evaluation["explanation"],
        "content_hash": evaluation["content_hash"],
        "config_hash": evaluation["config_hash"],
        "manual_override": bool(evaluation["manual_override"]),
        "reviewer": evaluation["reviewer"],
        "reviewed_at": evaluation["reviewed_at"],
        "evaluated_at": evaluation["evaluated_at"],
        "evidence": catalog.evidence_for(artifact_id),
    }


def test_evaluation_contract(curation_env) -> None:
    service = curation_env["service"]
    catalog = curation_env["catalog"]
    service.analyze(apply=True, run_id="contract-eval")
    payload = _evaluation_payload(catalog, curation_env["ids"]["official"])
    jsonschema.validate(payload, _schema("relevance-evaluation.schema.json"))


def test_curation_report_contract(curation_env) -> None:
    service = curation_env["service"]
    service.analyze(apply=True, run_id="contract-report")
    path = curation_env["app"].settings.bronze_dir / "reports" / "contract-report" / "curation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(payload, _schema("curation-report.schema.json"))


def test_audit_contract(curation_env) -> None:
    service = curation_env["service"]
    catalog = curation_env["catalog"]
    ids = curation_env["ids"]
    service.analyze(apply=True, run_id="contract-audit")
    for key in ("incidental", "pdf"):
        service.decide_review(artifact_id=ids[key], decision="remove", reviewer="tester")
    service.approve("contract-audit", "tester")
    service.quarantine("contract-audit")
    audit = catalog.get_audit_record(ids["generic"])
    payload = {
        "schema_version": "1.0",
        "audit_id": audit["audit_id"],
        "run_id": audit["run_id"],
        "artifact_id": audit["artifact_id"],
        "url_canonical": audit["url_canonical"],
        "content_hash": audit["content_hash"],
        "byte_size": audit["byte_size"],
        "media_type": audit["media_type"],
        "source_id": audit["source_id"],
        "decision": audit["decision"],
        "reason": audit["reason"],
        "score": audit["score"],
        "evidence": json.loads(audit["evidence_json"]),
        "decided_at": audit["decided_at"],
        "quarantined_at": audit["quarantined_at"],
        "purged_at": audit["purged_at"],
    }
    jsonschema.validate(payload, _schema("audit-record.schema.json"))


def test_relevance_config_contract() -> None:
    path = PROJECT_ROOT / "config" / "relevance.toml"
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    jsonschema.validate(payload, _schema("relevance-config.schema.json"))
