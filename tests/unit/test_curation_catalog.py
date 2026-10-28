"""Unit tests for curation catalog invariants and the active view."""

from __future__ import annotations

from proyecto_modelos_lenguaje.utils import utcnow


def test_manual_override_is_not_overwritten(curation_env) -> None:
    catalog = curation_env["catalog"]
    artifact_id = curation_env["ids"]["official"]
    catalog.create_curation_run(
        run_id="manual-run",
        config_hash="a" * 64,
        tool_version="test",
        bytes_before=10,
    )
    assert catalog.upsert_evaluation(
        artifact_id=artifact_id,
        run_id="manual-run",
        decision="keep",
        level="direct",
        score=100,
        explanation="auto",
        content_hash="b" * 64,
        config_hash="a" * 64,
    )
    catalog.set_manual_decision(
        artifact_id=artifact_id, decision="keep", reviewer="tester", note="manual"
    )
    assert not catalog.upsert_evaluation(
        artifact_id=artifact_id,
        run_id="manual-run",
        decision="remove",
        level="none",
        score=0,
        explanation="auto rerun",
        content_hash="b" * 64,
        config_hash="a" * 64,
    )
    evaluation = catalog.get_evaluation(artifact_id)
    assert evaluation["decision"] == "keep"
    assert evaluation["manual_override"] == 1
    assert evaluation["reviewer"] == "tester"


def test_active_view_excludes_removed_after_approval(curation_env) -> None:
    catalog = curation_env["catalog"]
    artifact_id = curation_env["ids"]["generic"]
    catalog.create_curation_run(
        run_id="active-run",
        config_hash="a" * 64,
        tool_version="test",
        bytes_before=10,
    )
    catalog.upsert_evaluation(
        artifact_id=artifact_id,
        run_id="active-run",
        decision="remove",
        level="none",
        score=0,
        explanation="irrelevant",
        content_hash="c" * 64,
        config_hash="a" * 64,
    )
    _, before = catalog.list_artifacts(campaign_id="c001", active_only=True)
    catalog.update_curation_run("active-run", status="approved", approved_by="tester")
    _, after = catalog.list_artifacts(campaign_id="c001", active_only=True)
    assert after == before - 1


def test_audit_and_quarantine_entries_are_idempotent(curation_env) -> None:
    catalog = curation_env["catalog"]
    artifact_id = curation_env["ids"]["generic"]
    catalog.create_curation_run(
        run_id="audit-run",
        config_hash="a" * 64,
        tool_version="test",
        bytes_before=10,
    )
    catalog.add_audit_record(
        run_id="audit-run",
        artifact_id=artifact_id,
        url_canonical="https://www.datos.gov.co/dataset",
        content_hash="c" * 64,
        byte_size=10,
        media_type="text/html",
        source_id="datos_gov",
        reason="test",
        score=0,
        evidence_json="[]",
    )
    catalog.add_audit_record(
        run_id="audit-run",
        artifact_id=artifact_id,
        url_canonical="https://www.datos.gov.co/dataset",
        content_hash="c" * 64,
        byte_size=10,
        media_type="text/html",
        source_id="datos_gov",
        reason="test",
        score=0,
        evidence_json="[]",
    )
    rows = catalog.connection.execute(
        "SELECT COUNT(*) AS n FROM curation_audit WHERE artifact_id = ?", (artifact_id,)
    ).fetchone()
    assert rows["n"] == 1
    catalog.add_quarantine_entry(
        artifact_id=artifact_id,
        run_id="audit-run",
        original_path="raw/datos_gov/c001/file.html",
        quarantine_path="audit-run/1/file.html",
        byte_size=10,
        expires_at=utcnow(),
    )
    catalog.add_quarantine_entry(
        artifact_id=artifact_id,
        run_id="audit-run",
        original_path="raw/datos_gov/c001/file.html",
        quarantine_path="audit-run/1/file.html",
        byte_size=10,
        expires_at=utcnow(),
    )
    count = catalog.connection.execute(
        "SELECT COUNT(*) AS n FROM quarantine_entries WHERE artifact_id = ?", (artifact_id,)
    ).fetchone()
    assert count["n"] == 1
