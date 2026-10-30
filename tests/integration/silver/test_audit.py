"""Integration test for User Story 4: traceability and bronze immutability."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.silver.bronze import load_artifacts, read_artifact_bytes
from proyecto_modelos_lenguaje.storage import sha256_bytes
from tests.integration.silver.conftest import SilverEnv


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_chunks_trace_to_bronze_and_bronze_is_immutable(silver_env: SilverEnv) -> None:
    html = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita transforma recursos naturales en alimentos y energía. " * 12)
        + "</p></article></body></html>"
    ).encode()
    silver_env.add(html, media_type="text/html", url="https://example.test/a", title="A")
    artifacts = {artifact.artifact_id: artifact for artifact in load_artifacts(silver_env.database)}
    before = {
        artifact_id: sha256_bytes(read_artifact_bytes(artifact, silver_env.bronze_dir))
        for artifact_id, artifact in artifacts.items()
    }
    silver_env.pipeline.build("2026-10-silver-08")
    documents = _jsonl(silver_env.root / "data" / "silver" / "documents.jsonl")
    chunks = _jsonl(silver_env.root / "data" / "silver" / "chunks.jsonl")
    by_id = {document["doc_id"]: document for document in documents}
    assert chunks
    for chunk in chunks[:50]:
        document = by_id[chunk["doc_id"]]
        artifact = artifacts[document["artifact_id"]]
        assert artifact.content_hash == document["content_hash"]
        assert artifact.url_canonical == document["url_canonical"]
        assert document["text"][chunk["char_start"] : chunk["char_end"]] == chunk["text"]
    after = {
        artifact_id: sha256_bytes(read_artifact_bytes(artifact, silver_env.bronze_dir))
        for artifact_id, artifact in artifacts.items()
    }
    assert before == after
