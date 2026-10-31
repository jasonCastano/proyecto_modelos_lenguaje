"""Unit tests for the brand palette, tokens, contrast and status mapping."""

from __future__ import annotations

from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.brand import (
    STATUS_VARIANTS,
    BrandPalette,
    BrandTokens,
    contrast_failures,
    contrast_ratio,
    status_variant,
)

# --- contraste ---------------------------------------------------------------------------------


def test_contrast_ratio_known_values() -> None:
    assert contrast_ratio("#000000", "#FFFFFF") == 21.0
    assert contrast_ratio("#FFFFFF", "#FFFFFF") == 1.0
    assert contrast_ratio("#FFFFFF", "#000000") == 21.0


def test_every_declared_pair_reaches_its_minimum() -> None:
    assert contrast_failures() == []


def test_contrast_failures_detects_a_broken_pair() -> None:
    tokens = BrandTokens()
    broken = replace(tokens, palette=replace(tokens.palette, ink="#DDDDDD"))
    assert any("ink/white" in failure for failure in contrast_failures(broken))


def test_invalid_colour_is_rejected() -> None:
    with pytest.raises(ValueError):
        BrandPalette(forest="#387c2b")
    with pytest.raises(ValueError):
        contrast_ratio("green", "#FFFFFF")
    with pytest.raises(KeyError):
        BrandPalette().get("turquoise")


# --- tokens ------------------------------------------------------------------------------------


def test_tokens_expose_the_documented_shape() -> None:
    tokens = BrandTokens().to_dict()
    assert set(tokens) == {
        "palette",
        "contrast_pairs",
        "type_scale",
        "font_stack",
        "radius",
        "spacing_unit",
        "brand_name",
        "project_name",
        "tagline",
        "attribution",
        "affiliation_note",
    }
    assert len(tokens["palette"]) == 13
    assert tokens["type_scale"] == {"display": 28, "heading": 22, "body": 16, "caption": 13}
    assert len(tokens["contrast_pairs"]) >= 10


def test_palette_uses_the_official_logo_colours() -> None:
    palette = BrandPalette()
    assert palette.forest == "#387C2B"
    assert palette.orange == "#E86D1F"
    assert palette.lime == "#B0BC22"
    assert palette.yellow == "#FFD200"
    assert palette.orange_light == "#F6A01A"


# --- estados -----------------------------------------------------------------------------------


def test_every_status_maps_to_colour_icon_and_label() -> None:
    for key, variant in STATUS_VARIANTS.items():
        assert key in STATUS_VARIANTS
        assert variant.icon.strip()
        assert variant.label.strip()
        assert variant.color in BrandPalette().to_dict()
        assert variant.text.startswith(variant.icon)


def test_status_mapping_preserves_the_functional_semantics() -> None:
    for key in ("ok", "ready", "review", "fallback", "missing_evidence", "error", "demo"):
        variant = status_variant(key)
        assert variant.icon and variant.label
    assert status_variant("missing_evidence").color == status_variant("fallback").color
    assert status_variant("demo").label == "Modo demo"
    with pytest.raises(KeyError):
        status_variant("unknown")
