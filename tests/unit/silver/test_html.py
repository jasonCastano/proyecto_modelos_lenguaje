"""Unit tests for HTML extraction."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.silver.extractors.html import extract_html

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "silver"


def test_extracts_main_article_and_headings() -> None:
    document = extract_html((FIXTURES / "sample.html").read_bytes(), url="https://example.test")
    text = document.text
    assert "Manuelita avanza en sostenibilidad" in text
    assert "Los proyectos" in text
    assert "Usamos cookies" not in text
    assert "Artículos relacionados" not in text
    levels = [block.level for block in document.blocks if block.level]
    assert levels[:3] == [1, 2, 3]
    assert document.skip_reason is None


def test_empty_html_is_skipped() -> None:
    document = extract_html(b"<html><body><nav>Inicio</nav></body></html>")
    assert document.skip_reason == "no_text"
    assert not document.blocks
