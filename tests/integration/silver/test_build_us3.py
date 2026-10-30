"""Integration test for User Story 3: deduplication and canonical versions."""

from __future__ import annotations

import json
from pathlib import Path

from tests.integration.silver.conftest import SilverEnv


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_duplicates_and_versions_are_resolved(silver_env: SilverEnv) -> None:
    text = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita transforma recursos naturales en alimentos y energía. " * 12)
        + "</p></article></body></html>"
    ).encode()
    newer = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita transforma recursos naturales en alimentos, energía y bioinsumos. " * 12)
        + "</p></article></body></html>"
    ).encode()
    older = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita presenta su informe anterior y sus avances en el sector. " * 12)
        + "</p></article></body></html>"
    ).encode()
    silver_env.add(text, media_type="text/html", url="https://example.test/a", title="A")
    silver_env.add(
        text + b" ",
        media_type="text/html",
        url="https://third.test/a",
        title="A",
        source_id="elpais",
        authority="third_party",
    )
    silver_env.add(
        older, media_type="text/html", url="https://example.test/version", title="V", version=1
    )
    silver_env.add(
        newer,
        media_type="text/html",
        url="https://example.test/version",
        title="V",
        version=2,
    )
    report = silver_env.pipeline.build("2026-10-silver-04")
    assert report["documents"] == 4
    assert report["alias_documents"] == 2
    assert report["duplicates_exact"] >= 1
    assert report["duplicates_near"] >= 1

    documents = _jsonl(silver_env.root / "data" / "silver" / "documents.jsonl")
    chunks = _jsonl(silver_env.root / "data" / "silver" / "chunks.jsonl")
    canonical = {document["doc_id"] for document in documents if document["status"] == "canonical"}
    aliases = {
        document["doc_id"]: document for document in documents if document["status"] == "alias"
    }
    assert len(aliases) == 2
    assert all(alias["canonical_doc_id"] in canonical for alias in aliases.values())
    assert all(chunk["doc_id"] in canonical for chunk in chunks)

    version_docs = [
        document
        for document in documents
        if document["url_canonical"] == "https://example.test/version"
    ]
    version_canonical = next(
        document for document in version_docs if document["status"] == "canonical"
    )
    assert "bioinsumos" in version_canonical["text"]
