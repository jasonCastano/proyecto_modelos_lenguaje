"""Integration tests for User Story 4: idempotency and audit."""

from __future__ import annotations

import json
from pathlib import Path

from tests.fixtures.silver.generate import generate_pdf
from tests.integration.silver.conftest import SilverEnv


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_idempotent_runs_and_audit(silver_env: SilverEnv, tmp_path: Path) -> None:
    html = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita transforma recursos naturales en alimentos y energía. " * 12)
        + "</p></article></body></html>"
    ).encode()
    pdf = generate_pdf(tmp_path / "report.pdf", pages=2).read_bytes()
    silver_env.add(html, media_type="text/html", url="https://example.test/a", title="A")
    silver_env.add(pdf, media_type="application/pdf", url="https://example.test/b", title="B")

    first = silver_env.pipeline.build("2026-10-silver-05")
    documents_path = silver_env.root / "data" / "silver" / "documents.jsonl"
    chunks_path = silver_env.root / "data" / "silver" / "chunks.jsonl"
    documents_bytes = documents_path.read_bytes()
    chunks_bytes = chunks_path.read_bytes()
    first_ids = {document["doc_id"] for document in _jsonl(documents_path)}

    second = silver_env.pipeline.build("2026-10-silver-06")
    assert first["documents"] == second["documents"]
    assert first["chunks"] == second["chunks"]
    assert documents_path.read_bytes() == documents_bytes
    assert chunks_path.read_bytes() == chunks_bytes

    verified = silver_env.pipeline.verify_run("2026-10-silver-06", sample=50, seed=1)
    assert verified["passed"] is True
    assert verified["sampled"] == first["documents"]
    assert verified["failures"] == []

    forced = silver_env.pipeline.build("2026-10-silver-07", force=True)
    assert forced["documents"] == first["documents"]
    assert documents_path.read_bytes() == documents_bytes

    newer = (
        "<html lang='es'><body><article><h1>Manuelita</h1><p>"
        + ("Manuelita transforma recursos naturales en alimentos, energía y bioinsumos. " * 12)
        + "</p></article></body></html>"
    ).encode()
    silver_env.add(
        newer,
        media_type="text/html",
        url="https://example.test/a",
        title="A",
        version=2,
    )
    incremental = silver_env.pipeline.build("2026-10-silver-08")
    assert incremental["input_artifacts"] == 3
    after_documents = _jsonl(documents_path)
    after_ids = {document["doc_id"] for document in after_documents}
    assert len(after_documents) == 3
    assert first_ids <= after_ids
    assert len(after_ids - first_ids) == 1
