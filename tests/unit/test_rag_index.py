"""Pruebas del índice vectorial: construcción, troceo, manifiesto y verificación."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from proyecto_modelos_lenguaje.rag.config import load_retrieval_config
from proyecto_modelos_lenguaje.rag.embeddings import EmbeddingProfile, HashEmbedder
from proyecto_modelos_lenguaje.rag.errors import (
    GoldError,
    IndexExistsError,
    IndexInvalidError,
    IndexUnavailableError,
)
from proyecto_modelos_lenguaje.rag.index import (
    Fragment,
    build_fragments,
    build_index,
    chunk_text,
    load_index,
    sha256_file,
    verify_index,
)
from proyecto_modelos_lenguaje.retrieval import GoldUnit
from proyecto_modelos_lenguaje.silver.cleaning import estimate_tokens

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "gold_sample.jsonl"


@pytest.fixture()
def profile() -> EmbeddingProfile:
    config = load_retrieval_config(project_root=PROJECT_ROOT)
    return EmbeddingProfile.from_config(config.embedding, created_at="2026-11-06T00:00:00+00:00")


@pytest.fixture()
def built(tmp_path: Path, profile: EmbeddingProfile) -> tuple[Path, object]:
    index_dir = tmp_path / "index"
    manifest = build_index(FIXTURE, index_dir, HashEmbedder(profile), profile)
    return index_dir, manifest


def test_build_index_counts_match_matrix_and_database(
    built: tuple[Path, object], profile: EmbeddingProfile
) -> None:
    index_dir, manifest = built
    loaded = load_index(index_dir, profile)

    assert manifest.count == 50
    assert loaded.vectors.shape == (50, 384)
    assert len(loaded.fragments) == 50
    assert loaded.manifest.gold_sha256 == sha256_file(FIXTURE)


def test_build_index_is_read_only_over_gold(tmp_path: Path, profile: EmbeddingProfile) -> None:
    before_hash = sha256_file(FIXTURE)
    before_mtime = FIXTURE.stat().st_mtime_ns

    build_index(FIXTURE, tmp_path / "index", HashEmbedder(profile), profile)

    assert sha256_file(FIXTURE) == before_hash
    assert FIXTURE.stat().st_mtime_ns == before_mtime


def test_build_index_publishes_atomically(tmp_path: Path, profile: EmbeddingProfile) -> None:
    index_dir = tmp_path / "index"
    build_index(FIXTURE, index_dir, HashEmbedder(profile), profile)

    leftovers = [item.name for item in tmp_path.iterdir() if item.name.startswith(".index-")]
    assert leftovers == []
    assert (index_dir / "manifest.json").is_file()
    assert (index_dir / "vectors.npy").is_file()
    assert (index_dir / "index.sqlite3").is_file()


def test_existing_equivalent_index_requires_force(
    built: tuple[Path, object], profile: EmbeddingProfile
) -> None:
    index_dir, _ = built

    with pytest.raises(IndexExistsError):
        build_index(FIXTURE, index_dir, HashEmbedder(profile), profile)


def test_rebuild_with_force_replaces_index(
    built: tuple[Path, object], profile: EmbeddingProfile
) -> None:
    index_dir, first = built
    second = build_index(FIXTURE, index_dir, HashEmbedder(profile), profile, force=True)

    assert second.count == first.count
    assert load_index(index_dir, profile).manifest.count == 50


def test_load_index_rejects_other_profile(
    built: tuple[Path, object], profile: EmbeddingProfile
) -> None:
    index_dir, _ = built
    other = EmbeddingProfile.from_config(load_retrieval_config(project_root=PROJECT_ROOT).embedding)
    other = EmbeddingProfile(
        model="otro/modelo",
        dimension=other.dimension,
        normalize=other.normalize,
        max_tokens=other.max_tokens,
        query_prefix=other.query_prefix,
        passage_prefix=other.passage_prefix,
        created_at=other.created_at,
    )

    with pytest.raises(IndexInvalidError):
        load_index(index_dir, other)


def test_load_index_requires_all_artifacts(built: tuple[Path, object]) -> None:
    index_dir, _ = built
    (index_dir / "vectors.npy").unlink()

    with pytest.raises(IndexUnavailableError):
        load_index(index_dir)


def test_verify_reports_missing_index(tmp_path: Path) -> None:
    result = verify_index(tmp_path / "nada")

    assert result.ok is False
    assert result.code == 5


def test_verify_detects_outdated_gold(
    built: tuple[Path, object], profile: EmbeddingProfile, tmp_path: Path
) -> None:
    index_dir, _ = built
    modified = tmp_path / "knowledge_units.jsonl"
    shutil.copyfile(FIXTURE, modified)
    modified.write_text(modified.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    result = verify_index(index_dir, profile, gold_path=modified)

    assert result.code == 6
    assert any("desactualizado" in message for message in result.messages)


def test_verify_accepts_current_index(
    built: tuple[Path, object], profile: EmbeddingProfile
) -> None:
    index_dir, _ = built

    result = verify_index(index_dir, profile, gold_path=FIXTURE)

    assert result.ok is True
    assert result.code == 0


def test_build_rejects_missing_gold(tmp_path: Path, profile: EmbeddingProfile) -> None:
    with pytest.raises(GoldError):
        build_index(tmp_path / "nada.jsonl", tmp_path / "index", HashEmbedder(profile), profile)


def test_build_rejects_empty_gold(tmp_path: Path, profile: EmbeddingProfile) -> None:
    empty = tmp_path / "vacio.jsonl"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(GoldError):
        build_index(empty, tmp_path / "index", HashEmbedder(profile), profile)


def test_short_unit_is_not_chunked(profile: EmbeddingProfile) -> None:
    unit = GoldUnit(
        unit_id="unit_0123456789abcdef", topic_id="t", topic_title="Tema", text="texto corto"
    )

    fragments = build_fragments([unit], profile)

    assert len(fragments) == 1
    assert fragments[0].fragment_id == unit.unit_id
    assert fragments[0].chunk_total == 1


def test_long_unit_is_chunked_with_unit_id(profile: EmbeddingProfile) -> None:
    text = " ".join(["palabra"] * 1200)
    unit = GoldUnit(
        unit_id="unit_0123456789abcdef",
        topic_id="t",
        topic_title="Tema",
        text=text,
    )

    fragments = build_fragments([unit], profile)

    assert len(fragments) > 1
    assert all(fragment.unit_id == unit.unit_id for fragment in fragments)
    assert [fragment.chunk_index for fragment in fragments] == list(range(1, len(fragments) + 1))
    assert all(fragment.chunk_total == len(fragments) for fragment in fragments)
    assert all(estimate_tokens(fragment.text) <= profile.max_tokens for fragment in fragments)
    assert fragments[0].fragment_id.endswith("#1")


def test_chunk_text_keeps_short_text_intact() -> None:
    assert chunk_text("texto breve", max_tokens=512) == ["texto breve"]


def test_chunk_text_handles_text_without_spaces() -> None:
    chunks = chunk_text("x" * 4000, max_tokens=512)

    assert len(chunks) > 1
    assert all(estimate_tokens(chunk) <= 512 for chunk in chunks)


def test_manifest_is_json_serializable(built: tuple[Path, object]) -> None:
    index_dir, _ = built
    payload = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["count"] == 50
    assert payload["dimension"] == 384
    assert len(payload["gold_sha256"]) == 64


def test_fragment_rejects_inconsistent_chunks() -> None:
    with pytest.raises(ValueError):
        Fragment(
            fragment_id="x#2",
            unit_id="x",
            doc_id="d",
            title="",
            url="",
            published_at=None,
            topic=None,
            text="texto",
            tokens=1,
            chunk_index=2,
            chunk_total=1,
        )


def test_index_vectors_are_unit_norm(built: tuple[Path, object], profile: EmbeddingProfile) -> None:
    index_dir, _ = built
    loaded = load_index(index_dir, profile)

    norms = np.linalg.norm(loaded.vectors, axis=1)

    assert np.allclose(norms, 1.0, atol=1e-5)
