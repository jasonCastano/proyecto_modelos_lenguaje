"""Unit tests for section-aware chunking."""

from __future__ import annotations

from proyecto_modelos_lenguaje.silver.chunking import chunk_document
from proyecto_modelos_lenguaje.silver.cleaning import estimate_tokens
from proyecto_modelos_lenguaje.silver.config import load_silver_config
from proyecto_modelos_lenguaje.silver.models import ExtractedBlock, SilverDocument
from proyecto_modelos_lenguaje.silver.sections import build_sections

CONFIG = load_silver_config("config/silver.toml")


def _document(text: str) -> SilverDocument:
    blocks = [ExtractedBlock(text=paragraph) for paragraph in text.split("\n\n")]
    doc_id = "doc_0123456789abcdef"
    sections, _ = build_sections(doc_id=doc_id, blocks=blocks, document_title="Manuelita")
    full_text = "\n\n".join(block.text for block in blocks)
    return SilverDocument(
        schema_version="1.0",
        doc_id=doc_id,
        artifact_id=1,
        campaign_id="campaign",
        content_hash="a" * 64,
        text_hash="b" * 64,
        source_id="official_site",
        authority="first_party",
        url="https://example.test/",
        url_canonical="https://example.test/",
        title="Manuelita",
        published_at=None,
        retrieved_at="2026-10-29T00:00:00Z",
        language="es",
        language_method="heuristic",
        category="identity",
        media_type="text/html",
        cleaning_version="1.0.0",
        config_hash="c" * 64,
        status="canonical",
        canonical_doc_id=None,
        duplicate_of=None,
        aliases=[],
        quality_flags=[],
        sections=sections,
        text=full_text,
        char_count=len(full_text),
        token_count=estimate_tokens(full_text),
        license_note="Uso académico.",
        markdown_path=None,
        blocks=blocks,
    )


def test_chunks_respect_limits_and_offsets() -> None:
    paragraph = (
        "Manuelita es una organización agroindustrial que transforma recursos naturales "
        "en alimentos y energía para miles de personas en Colombia, Perú y Chile."
    )
    document = _document("\n\n".join([paragraph] * 40))
    chunks = chunk_document(document, config=CONFIG.chunking)
    assert len(chunks) > 1
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    for chunk in chunks:
        assert chunk.token_count <= CONFIG.chunking.max_tokens
        assert document.text[chunk.char_start : chunk.char_end] == chunk.text
        assert chunk.section_path == ["Manuelita"]


def test_short_section_is_one_chunk() -> None:
    document = _document("Manuelita")
    chunks = chunk_document(document, config=CONFIG.chunking)
    assert len(chunks) == 1
    assert "short_section" in chunks[0].quality_flags


def test_chunking_is_deterministic() -> None:
    paragraph = "La compañía promueve el desarrollo sostenible de las comunidades vecinas."
    document = _document("\n\n".join([paragraph] * 20))
    first = chunk_document(document, config=CONFIG.chunking)
    second = chunk_document(document, config=CONFIG.chunking)
    assert [chunk.to_dict() for chunk in first] == [chunk.to_dict() for chunk in second]
