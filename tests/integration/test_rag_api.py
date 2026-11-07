"""Integración del RAG con la API: traza, citas, fallback y demo offline."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from proyecto_modelos_lenguaje import api
from proyecto_modelos_lenguaje.rag.config import load_retrieval_config
from proyecto_modelos_lenguaje.rag.embeddings import EmbeddingProfile, HashEmbedder
from proyecto_modelos_lenguaje.rag.hybrid import HybridRetriever
from proyecto_modelos_lenguaje.rag.index import load_index
from proyecto_modelos_lenguaje.retrieval import EntityIndex, EvidenceSelection, GoldUnit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "rag"
FIXTURE_INDEX = FIXTURE_DIR / "index"
GOLD_SAMPLE = FIXTURE_DIR / "gold_sample.jsonl"


def _units() -> tuple[GoldUnit, ...]:
    records = [
        json.loads(line)
        for line in GOLD_SAMPLE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return tuple(GoldUnit.from_dict(record) for record in records)


@pytest.fixture()
def client(monkeypatch) -> TestClient:
    config = load_retrieval_config(project_root=PROJECT_ROOT)
    profile = EmbeddingProfile.from_config(config.embedding, created_at="2026-11-06T00:00:00+00:00")
    units = _units()
    retriever = HybridRetriever(
        units,
        index=load_index(FIXTURE_INDEX, profile),
        embedder=HashEmbedder(profile),
        entity_index=EntityIndex(),
        config=config,
    )
    monkeypatch.setattr(api, "_units", lambda: units)
    monkeypatch.setattr(api, "_entity_index", lambda: EntityIndex())
    monkeypatch.setattr(api, "_retriever", lambda mode: retriever)
    monkeypatch.setattr(api, "_cost", lambda *args: None)
    return TestClient(api.app)


def test_ask_demo_returns_citations_and_trace(client: TestClient) -> None:
    response = client.post(
        "/api/ask",
        json={"question": "¿Cómo gestiona Manuelita el agua y los vertimientos?", "mode": "demo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["citations"]
    trace = payload["retrieval"]
    assert trace is not None
    assert trace["mode"] in {"hybrid", "semantic", "lexical"}
    assert trace["semantic_available"] is True
    assert trace["used_unit_ids"]
    assert trace["used_unit_ids"] == [
        fragment["unit_id"] for fragment in trace["fragments"] if fragment["status"] == "used"
    ]


def test_ask_demo_has_no_duplicate_units(client: TestClient) -> None:
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué productos de azúcar produce Manuelita?", "mode": "demo"},
    )

    trace = response.json()["retrieval"]
    ids = [fragment["unit_id"] for fragment in trace["fragments"]]
    assert len(ids) == len(set(ids))


class _EmptyRetriever:
    """Retriever stub for the no-evidence path (avoids hash-embedder false positives)."""

    def select(self, question, *, top_k=8, token_budget=6000, min_score=0.0):
        from proyecto_modelos_lenguaje.rag.hybrid import RetrievalTrace

        selection = EvidenceSelection(
            query=question,
            topic_id="",
            entities=(),
            selected=(),
            omitted_unit_ids=(),
            tokens=0,
            budget_tokens=token_budget,
        )
        trace = RetrievalTrace(
            mode="none",
            semantic_available=True,
            candidates=0,
            threshold=0.3,
            fragments=(),
            notes=(),
            elapsed_ms=0.0,
        )
        return selection, trace


def test_ask_out_of_corpus_falls_back(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(api, "_retriever", lambda mode: _EmptyRetriever())

    response = client.post(
        "/api/ask",
        json={"question": "¿Cuál es la receta de arepas de la abuela?", "mode": "demo"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fallback"
    assert payload["citations"] == []
    assert payload["retrieval"]["mode"] == "none"
    assert payload["retrieval"]["fragments"] == []


def test_ask_demo_works_without_network(client: TestClient, monkeypatch) -> None:
    original_connect = socket.socket.connect

    def guarded(sock, address):
        host = address[0] if isinstance(address, tuple) else ""
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("la demo no debe abrir conexiones de red externas")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)

    response = client.post(
        "/api/ask",
        json={"question": "¿Qué certificaciones tiene Manuelita?", "mode": "demo"},
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "fallback"}


def test_ask_without_retriever_still_answers(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(api, "_retriever", lambda mode: None)

    response = client.post("/api/ask", json={"question": "¿Qué hace Manuelita?", "mode": "demo"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval"] is None
    assert payload["status"] in {"ok", "fallback"}
