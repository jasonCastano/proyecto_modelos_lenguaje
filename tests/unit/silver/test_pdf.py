"""Unit tests for PDF extraction."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.silver.extractors.pdf import extract_pdf
from tests.fixtures.silver.generate import generate_pdf


def test_extracts_pages_outline_and_removes_repeated_lines(tmp_path: Path) -> None:
    path = generate_pdf(tmp_path / "sample.pdf", pages=2)
    document = extract_pdf(path.read_bytes())
    assert document.skip_reason is None
    assert [block.page for block in document.blocks] == [1, 2]
    assert "Manuelita" in document.text
    assert "Codigo: FR-PP-001" not in document.text
    assert "Pagina 1 de 2" not in document.text
    assert len(document.metadata["outline"]) >= 1
    assert document.title


def test_scanned_pdf_is_flagged(tmp_path: Path) -> None:
    path = generate_pdf(tmp_path / "blank.pdf", pages=1, text=False)
    document = extract_pdf(path.read_bytes())
    assert document.skip_reason == "scanned_pdf"
    assert "scanned_pdf" in document.flags


def test_encrypted_pdf_is_skipped(tmp_path: Path) -> None:
    from tests.fixtures.silver.generate import generate_encrypted_pdf

    path = generate_encrypted_pdf(tmp_path / "encrypted.pdf")
    document = extract_pdf(path.read_bytes())
    assert document.skip_reason == "encrypted_pdf"
    assert "encrypted_pdf" in document.flags


def test_large_pdf_completes(tmp_path: Path) -> None:
    path = generate_pdf(tmp_path / "large.pdf", pages=101)
    document = extract_pdf(path.read_bytes())
    assert document.metadata["pages"] == 101
    assert document.skip_reason is None
    assert len(document.blocks) == 101
