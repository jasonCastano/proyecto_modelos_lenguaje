"""Spec 026 (design.md §2): pares de contraste de la paleta por producto."""

from __future__ import annotations

from proyecto_modelos_lenguaje.brand import BrandTokens, contrast_failures, contrast_ratio


def test_ink_on_product_colors_reaches_aa() -> None:
    for background in ("#E86D1F", "#B0BC22", "#FFD200"):
        assert contrast_ratio("#14240F", background) >= 4.5, background


def test_white_on_forest_tones_reaches_aa() -> None:
    for background in ("#387C2B", "#173512"):
        assert contrast_ratio("#FFFFFF", background) >= 4.5, background


def test_white_on_orange_is_not_a_text_pair() -> None:
    assert contrast_ratio("#FFFFFF", "#E86D1F") < 4.5
    declared = {(p.text, p.background, p.minimum) for p in BrandTokens().contrast_pairs}
    assert ("white", "orange", 4.5) not in declared


def test_product_pairs_are_declared_and_pass() -> None:
    declared = {(p.text, p.background) for p in BrandTokens().contrast_pairs}
    for pair in [("ink", "orange"), ("ink", "lime"), ("ink", "yellow"), ("white", "forest_deep")]:
        assert pair in declared
    assert contrast_failures() == []
