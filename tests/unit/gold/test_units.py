"""Unit tests for extractive knowledge units."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.gold.config import load_gold_config
from proyecto_modelos_lenguaje.gold.inputs import SilverChunk, SilverDocument
from proyecto_modelos_lenguaje.gold.taxonomy import load_taxonomy
from proyecto_modelos_lenguaje.gold.units import build_units, deduplicate_units

ROOT = Path(__file__).resolve().parents[3]


def _setup():
    config = load_gold_config(
        ROOT / "config" / "gold.toml",
        ROOT / "config" / "gold_taxonomy.toml",
        project_root=ROOT,
    )
    taxonomy = load_taxonomy(
        ROOT / "config" / "gold_taxonomy.toml",
        coverage_path=ROOT / "config" / "coverage-items.toml",
        min_score=config.topics.min_score,
    )
    document = SilverDocument(
        doc_id="doc_0123456789abcdef",
        content_hash="a" * 64,
        text_hash="b" * 64,
        url="https://example.test/manuelita",
        url_canonical="https://example.test/manuelita",
        title="Manuelita",
        authority="first_party",
        language="es",
        published_at="2025-01-01T00:00:00Z",
        retrieved_at="2026-10-30T00:00:00Z",
        source_id="official_site",
    )
    text = (
        "Manuelita es una organización agroindustrial diversificada. "
        "La compañía produce azúcar, etanol y biocombustibles. "
        "Su misión es generar progreso y bienestar en las comunidades."
    )
    chunk = SilverChunk(
        chunk_id="doc_0123456789abcdef-s000-c0000",
        doc_id=document.doc_id,
        artifact_id=1,
        content_hash="a" * 64,
        source_id="official_site",
        authority="first_party",
        url=document.url,
        title=document.title,
        section_id="doc_0123456789abcdef-s000",
        section_title="Manuelita",
        section_path=("Manuelita",),
        chunk_order=0,
        text=text,
        char_start=0,
        char_end=len(text),
        token_count=50,
        page_start=None,
        page_end=None,
        time_start=None,
        time_end=None,
        language="es",
        media_type="text/html",
        quality_flags=(),
        retrieved_at="2026-10-30T00:00:00Z",
        license_note="Uso académico.",
    )
    return config, taxonomy, document, chunk


def test_builds_extractive_units_with_evidence() -> None:
    config, taxonomy, document, chunk = _setup()
    units = build_units(document, [chunk], taxonomy, config.units)
    assert len(units) == 3
    assert all(unit.evidence for unit in units)
    assert any(unit.topic_id == "identidad" for unit in units)
    assert any(unit.topic_id == "productos" for unit in units)
    assert all(unit.text in chunk.text for unit in units)
    assert len({unit.unit_id for unit in units}) == 3


def test_deduplicate_merges_evidence() -> None:
    config, taxonomy, document, chunk = _setup()
    units = build_units(document, [chunk], taxonomy, config.units)
    duplicate = build_units(document, [chunk], taxonomy, config.units)[0]
    duplicate.unit_id = "unit_ffffffffffffffff"
    duplicate.evidence[0].chunk_id = "doc_0123456789abcdef-s000-c0001"
    merged = deduplicate_units([*units, duplicate], threshold=0.90)
    assert len(merged) == len(units)
    target = next(unit for unit in merged if unit.text == duplicate.text)
    assert len(target.evidence) == 2
