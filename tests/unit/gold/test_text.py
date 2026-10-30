"""Unit tests for gold text utilities."""

from __future__ import annotations

from proyecto_modelos_lenguaje.gold.text import (
    jaccard,
    normalize_for_hash,
    normalize_for_match,
    normalize_text,
    shingles,
    split_sentences,
)


def test_normalization() -> None:
    assert normalize_text("  Manuelita \n  Agroindustria ") == "Manuelita Agroindustria"
    assert normalize_for_match("Fundación Manuelita") == "fundacion manuelita"
    assert normalize_for_hash("¡Manuelita, S.A.!") == "manuelita s a"


def test_sentence_split_respects_abbreviations() -> None:
    text = (
        "Manuelita S.A.S. es una empresa agroindustrial. "
        "Opera en Colombia, Perú y Chile. "
        "Su misión es generar progreso y bienestar."
    )
    sentences = split_sentences(text, min_chars=20, max_chars=200)
    assert len(sentences) == 3
    assert sentences[0].startswith("Manuelita S.A.S.")


def test_sentence_split_merges_short_and_cuts_long() -> None:
    sentences = split_sentences("Corto. " + "Manuelita " * 100, min_chars=20, max_chars=120)
    assert all(len(sentence) <= 120 for sentence in sentences)
    assert sentences[0].startswith("Corto.")


def test_jaccard_and_shingles() -> None:
    left = shingles("Manuelita transforma recursos naturales en alimentos")
    right = shingles("Manuelita transforma recursos naturales en alimentos")
    assert jaccard(left, right) == 1.0
    assert jaccard(left, shingles("Texto completamente distinto sobre otra empresa")) < 0.2
