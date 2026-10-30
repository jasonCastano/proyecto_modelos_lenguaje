"""Unit tests for text cleaning and token estimation."""

from __future__ import annotations

from proyecto_modelos_lenguaje.silver.cleaning import (
    alpha_ratio,
    clean_document,
    detect_text_language,
    estimate_tokens,
    normalize_whitespace,
    repair_mojibake,
)
from proyecto_modelos_lenguaje.silver.models import ExtractedBlock, ExtractedDocument


def test_token_proxy_uses_ceiling() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("1234567", 3.5) == 2
    assert estimate_tokens("x" * 350, 3.5) == 100


def test_whitespace_and_mojibake_are_normalized() -> None:
    assert normalize_whitespace("a\r\n\r\n\r\n b\t c ") == "a\n\nb c"
    repaired, changed = repair_mojibake("InformaciÃ³n de Manuelita")
    assert changed is True
    assert repaired == "Información de Manuelita"


def test_language_detection() -> None:
    assert (
        detect_text_language(
            "La empresa desarrolla proyectos sostenibles en Colombia y trabaja con las comunidades "
            "para el desarrollo."
        )[0]
        == "es"
    )
    assert (
        detect_text_language(
            "The company develops sustainable projects in Colombia and works with the communities "
            "for development."
        )[0]
        == "en"
    )
    assert detect_text_language("xyz")[0] == "und"


def test_clean_document_marks_short_text() -> None:
    document = ExtractedDocument(
        title=None,
        blocks=[ExtractedBlock(text="Manuelita")],
    )
    cleaned = clean_document(
        document,
        declared_language="es",
        min_text_chars=100,
        min_alpha_ratio=0.5,
        min_tokens=10,
    )
    assert "no_text" in cleaned.flags
    assert cleaned.title == "Manuelita"
    assert alpha_ratio("Manuelita 2026") > 0.5
