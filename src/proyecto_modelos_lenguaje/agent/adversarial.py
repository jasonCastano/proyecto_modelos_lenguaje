"""Corpus adversarial de prueba para el blindaje del RAG (spec 015, research R1–R3).

Un único punto de activación, compartido por la API, la CLI y la evaluación ``agent shield``:

- Se activa con ``MANUELITA_DEMO_CORPUS=malicious`` en el entorno del servidor, tanto en modo demo
  como en modo real. Está apagado por defecto (FR-001, FR-002).
- En modo demo usa el índice hash (sin red); en modo real, el índice construido con el modelo de
  embeddings real (``index_real/``), para que las consultas vectorizadas con e5 se comparen con
  vectores del mismo modelo.
- Qdrant se crea **siempre en memoria** a partir del índice adversarial: nunca se consulta ni se
  modifica la colección del corpus real.

El corpus vive en ``tests/fixtures/rag/malicious/`` y no se mezcla con ``data/gold``.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from ..config import PROJECT_ROOT
from ..rag.config import RetrievalConfig, load_retrieval_config
from ..rag.embeddings import EmbeddingProfile, build_embedder
from ..rag.errors import IndexInvalidError, IndexUnavailableError
from ..rag.hybrid import HybridRetriever
from ..rag.index import load_index
from ..rag.vectorstore import attach_vector_store
from ..retrieval import EntityIndex, GoldUnit

ADVERSARIAL_ENV = "MANUELITA_DEMO_CORPUS"
ADVERSARIAL_VALUE = "malicious"
MALICIOUS_DIR = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "malicious"
GOLD_FILE = MALICIOUS_DIR / "gold_malicious.jsonl"
CASES_FILE = MALICIOUS_DIR / "shield_cases.jsonl"
DEMO_INDEX = MALICIOUS_DIR / "index"
REAL_INDEX = MALICIOUS_DIR / "index_real"
NOTE = "Corpus adversarial (MANUELITA_DEMO_CORPUS=malicious)"

Mode = Literal["demo", "real"]


def adversarial_enabled() -> bool:
    """True si el servidor arrancó con el corpus de prueba adversarial."""
    return os.environ.get(ADVERSARIAL_ENV, "").strip().lower() == ADVERSARIAL_VALUE


def corpus_label(mode: str) -> str:
    """Etiqueta del corpus para trazas: ``adversarial``, ``real`` o ``demo``."""
    return "adversarial" if adversarial_enabled() else mode


def adversarial_units(path: Path = GOLD_FILE) -> tuple[GoldUnit, ...]:
    """Unidades del corpus adversarial (legítimas y de ataque)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return tuple(GoldUnit.from_dict(json.loads(line)) for line in lines if line.strip())


@lru_cache(maxsize=4)
def attack_unit_ids(path: Path = CASES_FILE) -> frozenset[str]:
    """Identificadores de las unidades de ataque declaradas en los casos del blindaje."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return frozenset(json.loads(line)["attack_unit_id"] for line in lines if line.strip())


def adversarial_retriever(mode: Mode, config: RetrievalConfig | None = None) -> HybridRetriever:
    """Recuperador híbrido sobre el corpus adversarial, con el índice adecuado al modo.

    ``demo`` usa embeddings hash (sin red); ``real`` usa el modelo de embeddings real. En ambos
    casos la colección Qdrant se crea en memoria (``demo=True`` en ``attach_vector_store``).
    """
    config = config or load_retrieval_config()
    profile = EmbeddingProfile.from_config(config.embedding)
    notes: list[str] = [NOTE]
    index_dir = REAL_INDEX if mode == "real" else DEMO_INDEX
    try:
        index = load_index(index_dir, profile)
    except (IndexUnavailableError, IndexInvalidError) as exc:
        index = None
        notes.append(f"Índice adversarial no utilizable: {exc}")
    units = adversarial_units()
    vector_store, note = attach_vector_store(index, config.source, units, demo=True)
    if note:
        notes.append(note)
    return HybridRetriever(
        units,
        index=index,
        embedder=build_embedder(profile, kind="fastembed" if mode == "real" else "hash"),
        entity_index=EntityIndex(),
        config=config,
        notes=tuple(notes),
        vector_store=vector_store,
    )
