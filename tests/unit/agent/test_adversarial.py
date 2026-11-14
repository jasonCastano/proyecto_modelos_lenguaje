"""Corpus adversarial activable en modo demo y real (spec 015, research R1–R3)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent import adversarial
from proyecto_modelos_lenguaje.agent.adversarial import (
    ADVERSARIAL_ENV,
    adversarial_enabled,
    adversarial_retriever,
    adversarial_units,
    attack_unit_ids,
    corpus_label,
)
from proyecto_modelos_lenguaje.rag.embeddings import HashEmbedder

MALICIOUS_UNIT = "unit_ma11c10u5000001"


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.delenv(ADVERSARIAL_ENV, raising=False)
    # Act / Assert
    assert adversarial_enabled() is False
    assert corpus_label("real") == "real"


def test_enabled_with_server_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv(ADVERSARIAL_ENV, "malicious")
    # Act / Assert
    assert adversarial_enabled() is True
    assert corpus_label("real") == "adversarial"


def test_corpus_has_legit_and_attack_units() -> None:
    # Arrange / Act
    units = adversarial_units()
    attacks = attack_unit_ids()
    # Assert: 5 legítimas + 6 de ataque, todas las de ataque presentes en el corpus
    assert len(units) == 11
    assert len(attacks) == 6
    assert attacks <= {unit.unit_id for unit in units}


def test_demo_retriever_finds_the_injected_document() -> None:
    # Arrange
    retriever = adversarial_retriever("demo")
    # Act
    trace = retriever.retrieve("¿Qué produce Manuelita?", top_k=8)
    # Assert
    assert MALICIOUS_UNIT in {fragment.unit_id for fragment in trace.fragments}
    assert adversarial.NOTE in retriever.notes


def test_real_retriever_uses_real_index_and_in_memory_qdrant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange: sin red; se espía qué índice y qué Qdrant pide el modo real
    seen: dict[str, object] = {}
    real_load = adversarial.load_index

    def spy_load(index_dir, profile):
        seen["index_dir"] = index_dir
        return real_load(index_dir, profile)

    def spy_attach(index, source, units, *, demo=False):
        seen["demo"] = demo
        return None, ""

    def fake_embedder(profile, *, kind="fastembed"):
        seen["kind"] = kind
        return HashEmbedder(profile)

    monkeypatch.setattr(adversarial, "load_index", spy_load)
    monkeypatch.setattr(adversarial, "attach_vector_store", spy_attach)
    monkeypatch.setattr(adversarial, "build_embedder", fake_embedder)
    # Act
    adversarial_retriever("real")
    # Assert
    assert seen["index_dir"] == adversarial.REAL_INDEX
    assert seen["kind"] == "fastembed"
    assert seen["demo"] is True  # nunca la colección del corpus real
