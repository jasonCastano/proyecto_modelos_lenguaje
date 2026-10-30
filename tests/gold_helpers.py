"""Helpers to build a temporary silver corpus for gold tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.gold.pipeline import GoldPipeline
from proyecto_modelos_lenguaje.silver.cleaning import estimate_tokens


def make_document(
    doc_id: str,
    *,
    title: str,
    url: str,
    text_hash: str,
    authority: str = "first_party",
    language: str = "es",
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "doc_id": doc_id,
        "artifact_id": 1,
        "campaign_id": "silver-test",
        "content_hash": text_hash,
        "text_hash": text_hash,
        "source_id": "official_site" if authority == "first_party" else "elpais",
        "authority": authority,
        "url": url,
        "url_canonical": url,
        "title": title,
        "published_at": "2025-01-01T00:00:00Z",
        "retrieved_at": "2026-10-30T00:00:00Z",
        "language": language,
        "language_method": "heuristic",
        "category": "identity",
        "media_type": "text/html",
        "cleaning_version": "1.0.0",
        "config_hash": "c" * 64,
        "status": "canonical",
        "canonical_doc_id": None,
        "duplicate_of": None,
        "aliases": [],
        "quality_flags": [],
        "sections": [],
        "text": "",
        "char_count": 0,
        "token_count": 0,
        "license_note": "Uso académico.",
        "markdown_path": None,
    }


def make_chunk(
    doc_id: str,
    *,
    chunk_id: str,
    text: str,
    title: str,
    url: str,
    section_title: str,
    authority: str = "first_party",
    language: str = "es",
    chunk_order: int = 0,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "chunk_id": chunk_id,
        "doc_id": doc_id,
        "artifact_id": 1,
        "content_hash": "a" * 64,
        "source_id": "official_site" if authority == "first_party" else "elpais",
        "authority": authority,
        "url": url,
        "title": title,
        "section_id": f"{doc_id}-s000",
        "section_title": section_title,
        "section_path": [section_title],
        "section_level": 1,
        "chunk_order": chunk_order,
        "text": text,
        "char_start": 0,
        "char_end": len(text),
        "token_count": estimate_tokens(text),
        "page_start": None,
        "page_end": None,
        "time_start": None,
        "time_end": None,
        "language": language,
        "media_type": "text/html",
        "quality_flags": [],
        "duplicate_of": None,
        "retrieved_at": "2026-10-30T00:00:00Z",
        "license_note": "Uso académico.",
    }


def write_silver(root: Path, documents: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> Path:
    silver = root / "data" / "silver"
    silver.mkdir(parents=True, exist_ok=True)
    for document in documents:
        text = "\n\n".join(
            chunk["text"] for chunk in chunks if chunk["doc_id"] == document["doc_id"]
        )
        document["text"] = text
        document["text_hash"] = document["text_hash"] or str(abs(hash(text)))
        document["char_count"] = len(text)
        document["token_count"] = estimate_tokens(text)
    with (silver / "documents.jsonl").open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(json.dumps(document, ensure_ascii=False) + "\n")
    with (silver / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return silver


def build_gold_pipeline(root: Path, silver: Path) -> GoldPipeline:
    return GoldPipeline.from_paths(
        silver_dir=silver,
        config_path=PROJECT_ROOT / "config" / "gold.toml",
        taxonomy_path=PROJECT_ROOT / "config" / "gold_taxonomy.toml",
        project_root=root,
    )
