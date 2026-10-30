"""Unit tests for exact and near-duplicate detection."""

from __future__ import annotations

from proyecto_modelos_lenguaje.silver.config import load_silver_config
from proyecto_modelos_lenguaje.silver.dedup import deduplicate
from proyecto_modelos_lenguaje.silver.models import SilverDocument

CONFIG = load_silver_config("config/silver.toml")


def _document(
    number: int,
    *,
    text: str,
    url: str,
    authority: str = "first_party",
    version: int = 1,
    language: str = "es",
    retrieved_at: str = "2026-10-29T00:00:00Z",
) -> SilverDocument:
    return SilverDocument(
        schema_version="1.0",
        doc_id=f"doc_{number:016x}",
        artifact_id=number,
        campaign_id="campaign",
        content_hash=f"{number:064x}",
        text_hash=f"{number + 1:064x}",
        source_id="official_site",
        authority=authority,
        url=url,
        url_canonical=url,
        title=f"Documento {number}",
        published_at=None,
        retrieved_at=retrieved_at,
        language=language,
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
        sections=[],
        text=text,
        char_count=len(text),
        token_count=len(text.split()),
        license_note="Uso académico.",
        markdown_path=None,
        version=version,
    )


def test_exact_duplicates_collapse() -> None:
    text = "Manuelita transforma recursos naturales en alimentos y energía."
    first = _document(1, text=text, url="https://a.test/1")
    second = _document(2, text=text, url="https://a.test/2", authority="third_party")
    alias_map, groups = deduplicate([first, second], config=CONFIG.dedup)
    assert len(groups) == 1
    assert groups[0].kind == "exact"
    assert groups[0].canonical_doc_id == first.doc_id
    assert alias_map == {second.doc_id: first.doc_id}


def test_newer_version_wins_for_same_url() -> None:
    old = _document(1, text="Versión antigua de Manuelita.", url="https://a.test/1", version=1)
    new = _document(2, text="Versión nueva de Manuelita.", url="https://a.test/1", version=2)
    alias_map, groups = deduplicate([old, new], config=CONFIG.dedup)
    assert groups[0].canonical_doc_id == new.doc_id
    assert groups[0].reason == "same_url_newer"
    assert alias_map == {old.doc_id: new.doc_id}


def test_languages_are_not_collapsed() -> None:
    spanish = _document(1, text="Manuelita transforma recursos naturales.", url="https://a.test/1")
    english = _document(
        2,
        text="Manuelita transforma recursos naturales.",
        url="https://a.test/2",
        language="en",
    )
    alias_map, groups = deduplicate([spanish, english], config=CONFIG.dedup)
    assert groups == []
    assert alias_map == {}


def test_official_source_wins() -> None:
    third = _document(
        1,
        text="Manuelita transforma recursos naturales en alimentos.",
        url="https://third.test/1",
        authority="third_party",
    )
    official = _document(
        2,
        text="Manuelita transforma recursos naturales en alimentos.",
        url="https://official.test/1",
        authority="first_party",
    )
    _alias_map, groups = deduplicate([third, official], config=CONFIG.dedup)
    assert groups[0].canonical_doc_id == official.doc_id
