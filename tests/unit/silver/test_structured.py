"""Unit tests for JSON, XML and XLSX extraction."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.silver.extractors.spreadsheet import extract_xlsx
from proyecto_modelos_lenguaje.silver.extractors.structured import extract_json, extract_xml
from tests.fixtures.silver.generate import generate_xlsx

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "silver"


def test_json_is_flattened_deterministically() -> None:
    document = extract_json((FIXTURES / "sample.json").read_bytes())
    text = document.text
    assert "title: Manuelita, manifiesto 2026" in text
    assert "subtitle_kinds.es: manual" in text
    assert document.blocks[0].level == 1
    assert document.skip_reason is None


def test_sitemap_is_skipped() -> None:
    payload = b'<?xml version="1.0"?><urlset><url><loc>https://example.test/</loc></url></urlset>'
    document = extract_xml(payload, url="https://example.test/sitemap.xml")
    assert document.skip_reason == "navigation_artifact"
    assert not document.blocks


def test_xlsx_one_section_per_sheet(tmp_path: Path) -> None:
    path = generate_xlsx(tmp_path / "sample.xlsx")
    document = extract_xlsx(path.read_bytes(), title="Datos Manuelita")
    assert document.skip_reason is None
    assert "Productos" in document.metadata["sheets"]
    assert "Sedes" in document.metadata["sheets"]
    assert "Azucar" in document.text
    assert "Valle del Cauca" in document.text
    assert json.dumps(document.metadata["sheets"], ensure_ascii=False)
