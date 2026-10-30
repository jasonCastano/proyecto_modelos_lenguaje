"""End-to-end campaign tests against a local fixture server."""

from __future__ import annotations

import asyncio
import json

from tests.conftest import build_runner

from proyecto_modelos_lenguaje.catalog import Catalog


def test_campaign_stores_artifacts_and_reports(app_config) -> None:
    runner, catalog, storage = build_runner(app_config)
    try:
        summary = asyncio.run(runner.run("c001"))
        assert summary.status == "completed"
        assert summary.artifacts_stored >= 3
        assert summary.excluded >= 1  # /blocked.html denied by robots.txt
        assert summary.bytes_stored <= app_config.settings.storage_limit_bytes

        artifacts, total = catalog.list_artifacts(campaign_id="c001", limit=1000)
        assert total == len(artifacts) >= 3
        for artifact in artifacts:
            assert artifact.url_canonical.startswith("http://127.0.0.1")
            assert artifact.content_hash
            assert artifact.retrieved_at.endswith("Z")
            assert artifact.category
            assert storage.verify(artifact.storage_path, artifact.content_hash)

        manifest = app_config.settings.bronze_dir / "manifests" / "c001.jsonl"
        assert manifest.is_file()
        assert len(manifest.read_text(encoding="utf-8").splitlines()) == len(artifacts)

        coverage_path = app_config.settings.bronze_dir / "reports" / "c001" / "coverage.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        assert len(coverage["items"]) == 24
        assert coverage["summary"]["total"] == 24
        assert any(item["status"] in {"covered", "partial"} for item in coverage["items"])
    finally:
        catalog.close()


def _raw_bytes(bronze) -> int:
    return sum(path.stat().st_size for path in (bronze / "raw").rglob("*") if path.is_file())


def test_second_campaign_deduplicates_content(app_config) -> None:
    first, catalog, _storage = build_runner(app_config)
    try:
        asyncio.run(first.run("c001"))
        first_bytes = _raw_bytes(app_config.settings.bronze_dir)
        first_artifacts, first_total = catalog.list_artifacts(campaign_id="c001", limit=1000)
        assert first_total >= 3
    finally:
        catalog.close()

    second, catalog2, _storage2 = build_runner(app_config)
    try:
        asyncio.run(second.run("c002"))
        second_bytes = _raw_bytes(app_config.settings.bronze_dir)
        unique_hashes = {
            artifact.content_hash
            for artifact in catalog2.list_artifacts(campaign_id="c002", limit=1000)[0]
        }
    finally:
        catalog2.close()

    assert second_bytes == first_bytes
    assert unique_hashes == {artifact.content_hash for artifact in first_artifacts}


def test_resume_after_interruption(app_config) -> None:
    runner, catalog, _ = build_runner(app_config, stop_after=1)
    try:
        first = asyncio.run(runner.run("resume1"))
        assert first.status == "paused"
        before = catalog.list_artifacts(campaign_id="resume1", limit=1000)[1]
        assert before >= 1
    finally:
        catalog.close()

    resumed, catalog2, storage2 = build_runner(app_config)
    try:
        summary = asyncio.run(resumed.run("resume1", resume=True))
        assert summary.status == "completed"
        artifacts, total = catalog2.list_artifacts(campaign_id="resume1", limit=1000)
        assert total >= max(before, 3)
        for artifact in artifacts:
            assert storage2.verify(artifact.storage_path, artifact.content_hash)
    finally:
        catalog2.close()


def test_storage_cap_pauses_campaign(app_config) -> None:
    runner, catalog, _ = build_runner(app_config, stop_after=None)
    runner.storage.limit_bytes = 500  # force the guard after the first artifact
    try:
        summary = asyncio.run(runner.run("cap1"))
        artifacts, _ = catalog.list_artifacts(campaign_id="cap1", limit=1000)
        assert sum(artifact.byte_size for artifact in artifacts) <= 500
        assert summary.status in {"paused", "completed"}
        assert summary.deferred >= 1 or summary.artifacts_stored == 0
    finally:
        catalog.close()


def test_status_queries_are_persisted(app_config) -> None:
    runner, catalog, _ = build_runner(app_config)
    try:
        asyncio.run(runner.run("c001"))
    finally:
        catalog.close()
    reopened = Catalog(app_config.settings.bronze_dir / "_meta" / "bronze.sqlite3")
    try:
        campaign = reopened.get_campaign("c001")
        assert campaign is not None
        assert campaign.status == "completed"
        assert campaign.artifact_count >= 3
        assert reopened.target_counts("c001")["excluded"] >= 1
    finally:
        reopened.close()
