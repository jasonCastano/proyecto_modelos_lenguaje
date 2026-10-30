"""Unit tests for section construction."""

from __future__ import annotations

from proyecto_modelos_lenguaje.silver.models import ExtractedBlock
from proyecto_modelos_lenguaje.silver.sections import build_sections


def test_heading_hierarchy() -> None:
    blocks = [
        ExtractedBlock(text="Manuelita", level=1),
        ExtractedBlock(text="Introducción"),
        ExtractedBlock(text="Historia", level=2),
        ExtractedBlock(text="La empresa nació en 1864."),
    ]
    sections, has_headings = build_sections(
        doc_id="doc_0123456789abcdef",
        blocks=blocks,
        document_title="Manuelita",
    )
    assert has_headings is True
    assert [section.title for section in sections] == ["Manuelita", "Historia"]
    assert sections[1].path == ["Manuelita", "Historia"]
    assert sections[0].char_start == 0
    assert sections[0].char_end <= sections[1].char_start


def test_document_without_headings_gets_sin_seccion() -> None:
    blocks = [ExtractedBlock(text="Texto sin encabezados de Manuelita.")]
    sections, has_headings = build_sections(
        doc_id="doc_0123456789abcdef",
        blocks=blocks,
        document_title=None,
    )
    assert has_headings is False
    assert len(sections) == 1
    assert sections[0].title == "sin sección"
    assert sections[0].level == 0


def test_pdf_outline_creates_sections() -> None:
    blocks = [
        ExtractedBlock(text="Contenido de la página uno", page=1),
        ExtractedBlock(text="Contenido de la página dos", page=2),
    ]
    sections, has_headings = build_sections(
        doc_id="doc_0123456789abcdef",
        blocks=blocks,
        document_title="Informe",
        outline=[
            {"title": "Portada", "page": 1, "level": 1},
            {"title": "Resultados", "page": 2, "level": 1},
        ],
    )
    assert has_headings is True
    assert [section.title for section in sections] == ["Portada", "Resultados"]
    assert sections[0].page_start == 1
    assert sections[1].page_start == 2
