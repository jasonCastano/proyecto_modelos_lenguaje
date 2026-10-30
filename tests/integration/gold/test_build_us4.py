"""Integration test for User Story 4: context packs and FAQ seeds."""

from __future__ import annotations

import json
from pathlib import Path

from tests.gold_helpers import (
    build_gold_pipeline,
    make_chunk,
    make_document,
    write_silver,
)


def test_builds_context_packs_and_faq(tmp_path: Path) -> None:
    doc_id = "doc_0123456789abcdef"
    text = (
        "Manuelita produce azúcar, etanol y biocombustibles en el Valle del Cauca. "
        "La compañía tiene una capacidad de 125.000 toneladas de azúcar. "
        "Su misión es generar progreso y bienestar en las comunidades. "
        "La empresa cuenta con certificación ISO y BASC."
    )
    document = make_document(
        doc_id, title="Manuelita", url="https://example.test/a", text_hash="b" * 64
    )
    chunk = make_chunk(
        doc_id,
        chunk_id=f"{doc_id}-s000-c0000",
        text=text,
        title="Manuelita",
        url="https://example.test/a",
        section_title="Manuelita",
    )
    silver = write_silver(tmp_path, [document], [chunk])
    report = build_gold_pipeline(tmp_path, silver).build("2026-10-gold-04")
    assert report["context_packs"] == 2
    gold = tmp_path / "data" / "gold"
    for budget in (8000, 32000):
        markdown = gold / f"context_{budget}.md"
        payload = json.loads((gold / f"context_{budget}.json").read_text(encoding="utf-8"))
        assert markdown.is_file()
        assert payload["tokens"] <= budget
        assert all(block["citation"] for block in payload["blocks"])
        assert len(set(payload["unit_ids"])) == len(payload["unit_ids"])
    small = json.loads((gold / "context_8000.json").read_text(encoding="utf-8"))
    large = json.loads((gold / "context_32000.json").read_text(encoding="utf-8"))
    assert set(small["unit_ids"]) <= set(large["unit_ids"])
    faq = [
        json.loads(line)
        for line in (gold / "faq_seeds.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert faq
    assert all(seed["evidence_unit_ids"] for seed in faq)
