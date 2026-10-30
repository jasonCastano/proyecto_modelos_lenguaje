"""Integration tests for the curation lifecycle."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.curation import GuardError, PendingReviewsError


def test_dry_run_writes_nothing(curation_env) -> None:
    summary = curation_env["service"].analyze(apply=False)
    assert summary.dry_run is True
    assert (summary.kept, summary.removed, summary.review) == (2, 2, 2)
    rows = (
        curation_env["catalog"]
        .connection.execute("SELECT COUNT(*) AS n FROM curation_runs")
        .fetchone()
    )
    assert rows["n"] == 0


def test_full_curation_flow(curation_env) -> None:
    service = curation_env["service"]
    catalog = curation_env["catalog"]
    ids = curation_env["ids"]

    summary = service.analyze(apply=True, run_id="curation-test")
    assert summary.artifacts_evaluated == 6
    assert (summary.kept, summary.removed, summary.review) == (2, 2, 2)
    run = catalog.get_curation_run("curation-test")
    assert run is not None and run["status"] == "analyzed"
    official_eval = catalog.get_evaluation(ids["official"])
    assert official_eval["decision"] == "keep"
    assert official_eval["score"] == 100

    with pytest.raises(GuardError):
        service.decide_review(
            artifact_id=ids["official"],
            decision="remove",
            reviewer="tester",
        )

    with pytest.raises(PendingReviewsError):
        service.approve("curation-test", "tester")

    for key in ("incidental", "pdf"):
        service.decide_review(
            artifact_id=ids[key],
            decision="remove",
            reviewer="tester",
            note="Sin relación verificable con la empresa.",
        )
    approved = service.approve("curation-test", "tester")
    assert approved["status"] == "approved"

    quarantined = service.quarantine("curation-test")
    assert quarantined["status"] == "quarantined"
    assert quarantined["bytes_quarantined"] > 0
    _artifacts, active_total = catalog.list_artifacts(campaign_id="c001", active_only=True)
    assert active_total == 2
    audit_rows = catalog.connection.execute(
        "SELECT COUNT(*) AS n FROM curation_audit WHERE run_id = 'curation-test'"
    ).fetchone()
    assert audit_rows["n"] == 4

    service.restore(ids["pdf"], reviewer="tester")
    _, restored_total = catalog.list_artifacts(campaign_id="c001", active_only=True)
    assert restored_total == 3
    restored_eval = catalog.get_evaluation(ids["pdf"])
    assert restored_eval["decision"] == "keep"
    assert restored_eval["manual_override"] == 1

    purged = service.purge("curation-test", now=True)
    assert purged["status"] == "purged"
    assert purged["bytes_freed"] > 0
    assert service.purge("curation-test", now=True)["status"] == "purged"

    audit = catalog.get_audit_record(ids["generic"])
    assert audit is not None and audit["purged_at"] is not None
    restored_audit = catalog.get_audit_record(ids["pdf"])
    assert restored_audit is not None and restored_audit["purged_at"] is None

    from proyecto_modelos_lenguaje.coverage import build_matrix

    matrix = build_matrix(catalog, "c001", active_only=True)
    assert len(matrix) == 24

    reports_dir = curation_env["app"].settings.bronze_dir / "reports" / "curation-test"
    assert (reports_dir / "curation.json").is_file()
    assert (reports_dir / "summary.md").is_file()


def test_purge_waits_for_retention_by_default(curation_env) -> None:
    service = curation_env["service"]
    ids = curation_env["ids"]
    service.analyze(apply=True, run_id="retention-test")
    for key in ("incidental", "pdf"):
        service.decide_review(artifact_id=ids[key], decision="remove", reviewer="tester")
    service.approve("retention-test", "tester")
    service.quarantine("retention-test")
    run = service.purge("retention-test", now=False)
    assert run["status"] == "quarantined"
    assert run["bytes_freed"] == 0
