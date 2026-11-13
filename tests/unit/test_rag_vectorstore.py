"""Base vectorial Qdrant (rúbrica del Módulo 2, ítem 2.2; ADR 0018)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from proyecto_modelos_lenguaje.rag.hybrid import MetadataFilter
from proyecto_modelos_lenguaje.rag.vectorstore import (
    QdrantSettings,
    build_collection,
    collection_matches,
    connect_vector_store,
    open_client,
)
from tests.agent_helpers import demo_retriever


def _settings(tmp_path: Path) -> QdrantSettings:
    return QdrantSettings(path=tmp_path / "qdrant", collection="pruebas")


def test_collection_mirrors_the_index_with_payload(tmp_path: Path) -> None:
    # Arrange
    base = demo_retriever()
    index = base.semantic.index
    client = open_client(_settings(tmp_path), in_memory=True)

    # Act
    written = build_collection(client, _settings(tmp_path), index, base.units_by_id)
    point = client.retrieve("pruebas", ids=[0], with_payload=True)[0]

    # Assert
    assert written == index.manifest.count
    assert collection_matches(client, _settings(tmp_path), index)
    assert point.payload["unit_id"] == index.fragments[0].unit_id
    assert {"topic_id", "authority", "unit_type", "url", "title"} <= set(point.payload)


def test_qdrant_top_k_matches_numpy_cosine(tmp_path: Path) -> None:
    # Arrange
    base = demo_retriever()
    index = base.semantic.index
    store, note = connect_vector_store(
        index, _settings(tmp_path), units_by_id=base.units_by_id, in_memory=True
    )
    query = index.vectors[3]

    # Act
    hits = store.search(query, limit=5)
    expected = np.argsort(-(index.vectors @ query), kind="stable")[:5]

    # Assert
    assert "Qdrant" in note
    assert hits[0].position == int(expected[0])
    assert {hit.position for hit in hits} == {int(position) for position in expected}


def test_payload_filter_is_applied_inside_qdrant(tmp_path: Path) -> None:
    # Arrange
    base = demo_retriever()
    index = base.semantic.index
    topic = next(unit.topic_id for unit in base.units if unit.topic_id)
    store, _ = connect_vector_store(
        index, _settings(tmp_path), units_by_id=base.units_by_id, in_memory=True
    )

    # Act
    hits = store.search(index.vectors[0], limit=10, topics=[topic])

    # Assert
    assert hits
    assert all(base.units_by_id[hit.unit_id].topic_id == topic for hit in hits)


def test_hybrid_retriever_uses_qdrant_and_its_filter(tmp_path: Path) -> None:
    # Arrange
    base = demo_retriever()
    store, _note = connect_vector_store(
        base.semantic.index, _settings(tmp_path), units_by_id=base.units_by_id, in_memory=True
    )
    retriever = demo_retriever()
    retriever.semantic.vector_store = store
    topic = next(unit.topic_id for unit in base.units if unit.topic_id)

    # Act
    trace = retriever.retrieve("Manuelita azúcar", top_k=5)
    filtered = retriever.retrieve(
        "Manuelita azúcar", top_k=5, metadata_filter=MetadataFilter.of(topics=[topic])
    )

    # Assert
    assert retriever.semantic.filters_in_store
    assert trace.used_unit_ids
    assert all(base.units_by_id[f.unit_id].topic_id == topic for f in filtered.fragments)


def test_missing_local_collection_falls_back_with_a_note(tmp_path: Path) -> None:
    # Arrange
    index = demo_retriever().semantic.index

    # Act
    store, note = connect_vector_store(index, _settings(tmp_path))

    # Assert
    assert store is None
    assert "numpy" in note
