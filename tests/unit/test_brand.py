"""Unit tests for the brand identity helpers (T011, T013, T017, T020, T023, T026)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.brand import (
    STATUS_VARIANTS,
    BrandPalette,
    BrandTokens,
    brand_css,
    citation_location,
    contrast_failures,
    contrast_ratio,
    footer_html,
    header_html,
    source_card_html,
    source_cards_html,
    status_bar_html,
    status_variant,
)
from proyecto_modelos_lenguaje.tasks import Citation


def _citation(**overrides: object) -> Citation:
    payload: dict[str, object] = {
        "label": "U1",
        "unit_id": "unit_0123456789abcdef",
        "title": "Manuelita — Productos",
        "url": "https://www.manuelita.com/manuelita-productos",
        "section_path": ("Productos", "Azúcar"),
        "page_start": 3,
        "page_end": None,
        "time_start": None,
        "time_end": None,
        "authority": "first_party",
        "citation": "Manuelita — Productos — https://www.manuelita.com/manuelita-productos",
    }
    payload.update(overrides)
    return Citation(**payload)  # type: ignore[arg-type]


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


# --- estilos -----------------------------------------------------------------------------------


def test_stylesheet_has_no_remote_or_absolute_resources() -> None:
    css = brand_css()
    assert "http://" not in css
    assert "https://" not in css
    assert "url(" not in css
    assert "@font-face" not in css
    assert "C:\\" not in css
    assert "--pml-forest: #387C2B" in css


def test_stylesheet_declares_the_four_type_levels() -> None:
    css = brand_css()
    assert "font-size: 28px" in css
    assert "font-size: 22px" in css
    assert "font-size: 16px" in css
    assert "font-size: 13px" in css


def test_stylesheet_has_no_fixed_max_width() -> None:
    assert "min-width" not in brand_css()


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


# --- fragmentos --------------------------------------------------------------------------------


def test_header_contains_signature_project_and_tagline() -> None:
    markup = header_html()
    assert "pml-header" in markup
    assert "Grupo Manuelita" in markup
    assert "Ingenio Manuelita" in markup
    assert BrandTokens().project_name in markup
    assert BrandTokens().tagline in markup


def test_status_bar_marks_demo_and_escapes_text() -> None:
    markup = status_bar_html([("ok", "✓", "Datos completos"), ("demo", "●", "Modo demo")])
    assert "pml-chip" in markup
    assert "is-demo" in markup
    assert "Datos completos" in markup
    hostile = status_bar_html([("ok", "✓", "<script>alert(1)</script>")])
    assert "<script>" not in hostile
    assert "&lt;script&gt;" in hostile


def test_source_card_contains_label_title_location_and_link() -> None:
    markup = source_card_html(_citation())
    assert "pml-source" in markup
    assert "[U1]" in markup
    assert "Manuelita — Productos" in markup
    assert "sección: Productos &gt; Azúcar" in markup
    assert 'href="https://www.manuelita.com/manuelita-productos"' in markup
    assert 'target="_blank"' in markup


def test_source_card_declares_missing_location() -> None:
    markup = source_card_html(_citation(section_path=(), page_start=None))
    assert "sin sección declarada" in markup


def test_source_cards_render_empty_state() -> None:
    assert "Sin fuentes citadas." in source_cards_html(())
    markup = source_cards_html([_citation(), _citation(label="U2")])
    assert markup.count("pml-source") == 2


def test_citation_location_includes_section_page_and_time() -> None:
    assert citation_location(_citation()) == "sección: Productos > Azúcar, p. 3"
    timed = _citation(section_path=("Video",), page_start=None, time_start=61.5)
    assert citation_location(timed) == "sección: Video, 61 s"


def test_footer_declares_academic_scope_and_attribution() -> None:
    markup = footer_html()
    assert "pml-footer" in markup
    assert "No afiliado" in markup
    assert "titulares" in markup
    assert "Maestría" in markup
