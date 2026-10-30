"""Integration test for User Story 2: sections and chunks."""

from __future__ import annotations

import json
from pathlib import Path

from tests.fixtures.silver.generate import generate_pdf
from tests.integration.silver.conftest import SilverEnv


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_sections_and_chunks_are_consistent(silver_env: SilverEnv, tmp_path: Path) -> None:
    paragraph = (
        "Manuelita es una organización agroindustrial que transforma recursos naturales en "
        "alimentos y energía. La compañía opera en Colombia, Perú y Chile y promueve el "
        "desarrollo sostenible de las comunidades vecinas. "
    )
    html = (
        "<html lang='es'><body><article><h1>Manuelita</h1>"
        f"<p>{paragraph * 8}</p><h2>Resultados</h2><p>{paragraph * 8}</p>"
        "</article></body></html>"
    ).encode()
    pdf = generate_pdf(tmp_path / "report.pdf", pages=3).read_bytes()
    silver_env.add(html, media_type="text/html", url="https://example.test/long", title="Manuelita")
    silver_env.add(
        pdf, media_type="application/pdf", url="https://example.test/report", title="Informe"
    )
    report = silver_env.pipeline.build("2026-10-silver-03")
    assert report["chunks"] >= 2
    documents = _jsonl(silver_env.root / "data" / "silver" / "documents.jsonl")
    chunks = _jsonl(silver_env.root / "data" / "silver" / "chunks.jsonl")
    by_id = {document["doc_id"]: document for document in documents}
    assert chunks
    for chunk in chunks:
        document = by_id[chunk["doc_id"]]
        assert chunk["section_path"]
        assert chunk["section_title"]
        assert chunk["token_count"] <= 1000
        assert document["text"][chunk["char_start"] : chunk["char_end"]] == chunk["text"]
        assert chunk["page_start"] is None or chunk["page_end"] >= chunk["page_start"]
    assert any(chunk["page_start"] is not None for chunk in chunks)
    assert any(
        section["title"] == "Resultados"
        for document in documents
        for section in document["sections"]
    )
