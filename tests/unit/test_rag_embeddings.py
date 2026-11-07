"""Pruebas del perfil de embeddings y de los embedders."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from proyecto_modelos_lenguaje.rag.config import (
    EmbeddingConfig,
    load_retrieval_config,
)
from proyecto_modelos_lenguaje.rag.embeddings import (
    EmbeddingProfile,
    FastEmbedEmbedder,
    HashEmbedder,
    load_embedding_profile,
)
from proyecto_modelos_lenguaje.rag.errors import RetrievalConfigError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _profile() -> EmbeddingProfile:
    config = load_retrieval_config(project_root=PROJECT_ROOT)
    return EmbeddingProfile.from_config(config.embedding)


def test_profile_matches_configuration() -> None:
    profile = _profile()

    assert profile.model == "intfloat/multilingual-e5-small"
    assert profile.dimension == 384
    assert profile.normalize is True
    assert profile.max_tokens == 512
    assert profile.query_prefix == "query: "
    assert profile.passage_prefix == "passage: "
    assert profile.created_at


def test_load_embedding_profile_reads_toml() -> None:
    profile = load_embedding_profile(project_root=PROJECT_ROOT)

    assert profile.dimension == 384
    assert profile.matches(_profile())


def test_profile_rejects_empty_model() -> None:
    with pytest.raises(ValueError):
        EmbeddingProfile(
            model=" ",
            dimension=384,
            normalize=True,
            max_tokens=512,
            query_prefix="",
            passage_prefix="",
            created_at="2026-11-06T00:00:00+00:00",
        )


def test_invalid_configuration_is_reported(tmp_path: Path) -> None:
    config = tmp_path / "retrieval.toml"
    config.write_text(
        "[embedding]\nmodel = ''\ndimension = 0\nnormalize = true\nmax_tokens = 512\n"
        "query_prefix = 'q'\npassage_prefix = 'p'\n[index]\npath = 'x'\nbatch_size = 1\n"
        "[hybrid]\nsemantic_top_k = 1\nlexical_top_k = 1\nmin_similarity = 0.3\n"
        "weight_semantic = 0.5\nweight_lexical = 0.5\nboth_bonus = 0.0\ndedup_similarity = 0.9\n",
        encoding="utf-8",
    )

    with pytest.raises(RetrievalConfigError):
        load_retrieval_config(config, project_root=tmp_path)


def test_missing_configuration_is_reported(tmp_path: Path) -> None:
    with pytest.raises(RetrievalConfigError):
        load_retrieval_config(tmp_path / "no-existe.toml", project_root=tmp_path)


def test_hash_embedder_is_deterministic() -> None:
    embedder = HashEmbedder(_profile())

    first = embedder.embed_passages(["Manuelita produce azúcar", "Manuelita produce azúcar"])
    again = embedder.embed_passages(["Manuelita produce azúcar"])

    assert first.shape == (2, 384)
    assert first.dtype == np.float32
    assert np.array_equal(first[0], first[1])
    assert np.array_equal(first[0], again[0])


def test_hash_embedder_returns_unit_norm_vectors() -> None:
    embedder = HashEmbedder(_profile())

    passages = embedder.embed_passages(["agua y vertimientos", "caña de azúcar"])
    query = embedder.embed_query("¿cómo cuida el agua?")

    assert np.allclose(np.linalg.norm(passages, axis=1), 1.0, atol=1e-5)
    assert np.isclose(np.linalg.norm(query), 1.0, atol=1e-5)
    assert query.shape == (384,)


def test_hash_embedder_applies_query_and_passage_prefixes() -> None:
    profile = EmbeddingProfile(
        model="fake",
        dimension=384,
        normalize=True,
        max_tokens=512,
        query_prefix="query: ",
        passage_prefix="passage: ",
        created_at="2026-11-06T00:00:00+00:00",
    )
    without_prefix = EmbeddingProfile(
        model="fake",
        dimension=384,
        normalize=True,
        max_tokens=512,
        query_prefix="",
        passage_prefix="",
        created_at="2026-11-06T00:00:00+00:00",
    )

    assert not np.array_equal(
        HashEmbedder(profile).embed_query("agua"),
        HashEmbedder(without_prefix).embed_query("agua"),
    )
    assert not np.array_equal(
        HashEmbedder(profile).embed_passages(["agua"])[0],
        HashEmbedder(without_prefix).embed_passages(["agua"])[0],
    )


def test_empty_batch_returns_empty_matrix() -> None:
    embedder = HashEmbedder(_profile())

    assert embedder.embed_passages([]).shape == (0, 384)


def test_fastembed_embedder_is_lazy() -> None:
    profile = EmbeddingProfile.from_config(
        EmbeddingConfig(
            model="intfloat/multilingual-e5-small",
            dimension=384,
            normalize=True,
            max_tokens=512,
            query_prefix="query: ",
            passage_prefix="passage: ",
        )
    )
    embedder = FastEmbedEmbedder(profile)

    assert embedder._model is None
    assert embedder.profile.dimension == 384
