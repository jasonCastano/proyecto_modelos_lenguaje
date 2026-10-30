"""Unit tests for coverage inference and the matrix."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import COVERAGE_PATH

from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.config import load_coverage_items
from proyecto_modelos_lenguaje.coverage import infer_evidence, summarize


def test_infer_evidence_finds_identity_and_offer() -> None:
    items = load_coverage_items(COVERAGE_PATH)
    evidence = infer_evidence(
        "Nuestra misión y visión guían los productos y servicios de azúcar y etanol.",
        title="Misión y visión",
        url="https://example.com/about",
        items=items,
    )
    ids = {item.item_id for item in evidence}
    assert "I-01" in ids
    assert "O-01" in ids
    assert all(item.confidence in {"direct", "supporting"} for item in evidence)


def test_unrelated_text_has_no_evidence() -> None:
    items = load_coverage_items(COVERAGE_PATH)
    evidence = infer_evidence(
        "Página de error genérica sin contenido corporativo.",
        title="404",
        url="https://example.com/missing",
        items=items,
    )
    assert evidence == ()


def test_matrix_always_has_24_rows(tmp_path: Path) -> None:
    catalog = Catalog(tmp_path / "bronze.sqlite3")
    try:
        catalog.init_schema()
        catalog.seed_coverage(load_coverage_items(COVERAGE_PATH))
        rows = catalog.coverage_matrix("c1")
    finally:
        catalog.close()
    assert len(rows) == 24
    assert all(row.status == "missing" for row in rows)
    assert all(row.gap_reason for row in rows)
    summary = summarize(rows)
    assert summary == {"covered": 0, "partial": 0, "missing": 24, "total": 24}
