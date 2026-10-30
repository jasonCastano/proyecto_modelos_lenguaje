"""Integration test for User Story 1: clean citable documents."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.silver.bronze import load_artifacts, read_artifact_bytes
from proyecto_modelos_lenguaje.storage import sha256_bytes
from tests.fixtures.silver.generate import generate_pdf, generate_xlsx
from tests.integration.silver.conftest import SilverEnv

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "silver"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_builds_documents_with_lineage(silver_env: SilverEnv, tmp_path: Path) -> None:
    html = (FIXTURES / "sample.html").read_bytes()
    vtt = (FIXTURES / "sample.vtt").read_bytes()
    metadata = (FIXTURES / "sample.json").read_bytes()
    xlsx = generate_xlsx(tmp_path / "sample.xlsx").read_bytes()
    scanned = generate_pdf(tmp_path / "scanned.pdf", pages=1, text=False).read_bytes()
    sitemap = b'<?xml version="1.0"?><urlset><url><loc>https://example.test/</loc></url></urlset>'

    silver_env.add(html, media_type="text/html", url="https://example.test/a", title="A")
    silver_env.add(vtt, media_type="text/vtt", url="https://example.test/b", title="B")
    silver_env.add(metadata, media_type="application/json", url="https://example.test/c", title="C")
    silver_env.add(
        xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        url="https://example.test/d",
        title="D",
    )
    silver_env.add(scanned, media_type="application/pdf", url="https://example.test/e", title="E")
    silver_env.add(
        sitemap, media_type="application/xml", url="https://example.test/sitemap.xml", title="F"
    )

    artifacts = load_artifacts(silver_env.database)
    before = {
        artifact.artifact_id: sha256_bytes(read_artifact_bytes(artifact, silver_env.bronze_dir))
        for artifact in artifacts
    }
    report = silver_env.pipeline.build("2026-10-silver-01")
    after = {
        artifact.artifact_id: sha256_bytes(read_artifact_bytes(artifact, silver_env.bronze_dir))
        for artifact in artifacts
    }

    assert report["input_artifacts"] == 6
    assert report["processed"] + report["skipped"] + report["failed"] == 6
    assert report["processed"] >= 4
    assert report["skipped"] >= 2
    assert before == after

    documents = _jsonl(silver_env.root / "data" / "silver" / "documents.jsonl")
    assert documents
    for document in documents:
        assert document["artifact_id"]
        assert document["content_hash"]
        assert document["url"]
        assert document["title"]
        assert document["sections"]
        assert all(section["title"] for section in document["sections"])


def test_scanned_pdf_and_sitemap_are_skipped(silver_env: SilverEnv, tmp_path: Path) -> None:
    scanned = generate_pdf(tmp_path / "scanned.pdf", pages=1, text=False).read_bytes()
    sitemap = b'<?xml version="1.0"?><urlset><url><loc>https://example.test/</loc></url></urlset>'
    silver_env.add(scanned, media_type="application/pdf", url="https://example.test/e", title="E")
    silver_env.add(
        sitemap, media_type="application/xml", url="https://example.test/sitemap.xml", title="F"
    )
    report = silver_env.pipeline.build("2026-10-silver-02")
    assert report["skipped"] == 2
    assert report["documents"] == 0
