"""Contract tests for silver JSONL records and run report."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tests.contract.silver.conftest import load_schema
from tests.integration.silver.conftest import SilverEnv


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_generated_records_match_contracts(silver_env: SilverEnv) -> None:
    html = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita transforma recursos naturales en alimentos y energía. " * 12)
        + "</p></article></body></html>"
    ).encode()
    silver_env.add(html, media_type="text/html", url="https://example.test/a", title="A")
    silver_env.add(html + b" ", media_type="text/html", url="https://example.test/b", title="B")
    silver_env.pipeline.build("2026-10-silver-09")

    documents = _jsonl(silver_env.root / "data" / "silver" / "documents.jsonl")
    chunks = _jsonl(silver_env.root / "data" / "silver" / "chunks.jsonl")
    report = json.loads(
        (
            silver_env.root / "data" / "silver" / "reports" / "2026-10-silver-09" / "quality.json"
        ).read_text(encoding="utf-8")
    )
    document_validator = Draft202012Validator(load_schema("document.schema.json"))
    chunk_validator = Draft202012Validator(load_schema("chunk.schema.json"))
    report_validator = Draft202012Validator(load_schema("run-report.schema.json"))

    for document in documents:
        document_validator.validate(document)
    for chunk in chunks:
        chunk_validator.validate(chunk)
    report_validator.validate(report)
    assert any(document["status"] == "alias" for document in documents)
    assert any(document["status"] == "canonical" for document in documents)
