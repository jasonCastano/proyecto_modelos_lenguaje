"""Perfiles y generadores de embeddings del Módulo 2.

El generador real usa ``fastembed`` (ONNX Runtime) con un modelo multilingüe pequeño. La suite y el
modo demostración usan :class:`HashEmbedder`, determinista y sin red.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..retrieval import normalize_text, tokenize
from .config import EmbeddingConfig, load_retrieval_config
from .errors import EmbeddingError

FLOAT_DTYPE = np.float32


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Return a float32 matrix whose rows have L2 norm 1 (zero rows stay zero)."""
    values = np.asarray(matrix, dtype=FLOAT_DTYPE)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (values / norms).astype(FLOAT_DTYPE)


@dataclass(frozen=True, slots=True)
class EmbeddingProfile:
    """Identidad del modelo con el que se generaron los vectores."""

    model: str
    dimension: int
    normalize: bool
    max_tokens: int
    query_prefix: str
    passage_prefix: str
    created_at: str

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model no puede estar vacío")
        if self.dimension < 1:
            raise ValueError("dimension debe ser >= 1")
        if self.max_tokens < 1:
            raise ValueError("max_tokens debe ser >= 1")

    @classmethod
    def from_config(
        cls, config: EmbeddingConfig, *, created_at: str | None = None
    ) -> EmbeddingProfile:
        return cls(
            model=config.model,
            dimension=config.dimension,
            normalize=config.normalize,
            max_tokens=config.max_tokens,
            query_prefix=config.query_prefix,
            passage_prefix=config.passage_prefix,
            created_at=created_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> EmbeddingProfile:
        return cls(
            model=str(payload["model"]),
            dimension=int(payload["dimension"]),
            normalize=bool(payload["normalize"]),
            max_tokens=int(payload.get("max_tokens", 512)),
            query_prefix=str(payload.get("query_prefix", "")),
            passage_prefix=str(payload.get("passage_prefix", "")),
            created_at=str(payload.get("created_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "dimension": self.dimension,
            "normalize": self.normalize,
            "max_tokens": self.max_tokens,
            "query_prefix": self.query_prefix,
            "passage_prefix": self.passage_prefix,
            "created_at": self.created_at,
        }

    def matches(self, other: EmbeddingProfile) -> bool:
        return (
            self.model == other.model
            and self.dimension == other.dimension
            and self.normalize == other.normalize
            and self.max_tokens == other.max_tokens
        )


class Embedder(Protocol):
    """Interfaz mínima que consumen el índice y la recuperación."""

    profile: EmbeddingProfile

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


def load_embedding_profile(
    config_path: str | Path | None = None, *, project_root: Path | None = None
) -> EmbeddingProfile:
    """Build the embedding profile from ``config/retrieval.toml``."""
    config = load_retrieval_config(config_path, project_root=project_root)
    return EmbeddingProfile.from_config(config.embedding)


class HashEmbedder:
    """Deterministic, offline embedder used by tests and the demo mode.

    Cada token aporta un peso con signo a una posición derivada de su hash BLAKE2b. No mide
    calidad semántica; solo garantiza determinismo byte a byte y la misma interfaz que el modelo
    real.
    """

    def __init__(self, profile: EmbeddingProfile) -> None:
        self.profile = profile

    def _vector(self, prepared: str) -> np.ndarray:
        dimension = self.profile.dimension
        vector = np.zeros(dimension, dtype=FLOAT_DTYPE)
        tokens = tokenize(prepared, keep_stopwords=True)
        if not tokens:
            tokens = tuple(normalize_text(prepared).split())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            raw = int.from_bytes(digest, "big")
            index = raw % dimension
            sign = 1.0 if (raw >> 8) & 1 else -1.0
            weight = 1.0 + ((raw >> 16) % 100) / 100.0
            vector[index] += sign * weight
        if not np.any(vector):
            vector[0] = 1.0
        return _normalize_rows(vector)[0]

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        prepared = [f"{self.profile.passage_prefix}{text}" for text in texts]
        if not prepared:
            return np.zeros((0, self.profile.dimension), dtype=FLOAT_DTYPE)
        return np.vstack([self._vector(text) for text in prepared]).astype(FLOAT_DTYPE)

    def embed_query(self, text: str) -> np.ndarray:
        prepared = f"{self.profile.query_prefix}{text}"
        return self._vector(prepared)


class FastEmbedEmbedder:
    """Multilingual ONNX embedder backed by ``fastembed``.

    El modelo se carga de forma perezosa: construir el objeto no descarga nada. La descarga ocurre
    en la primera llamada a :meth:`embed_passages` o :meth:`embed_query`.
    """

    def __init__(self, profile: EmbeddingProfile) -> None:
        self.profile = profile
        self._model: Any = None

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from fastembed import TextEmbedding
            from fastembed.common.model_description import ModelSource, PoolingType
        except ImportError as exc:  # pragma: no cover - dependencia declarada
            raise EmbeddingError(
                "fastembed no está instalado. Ejecuta `uv sync` antes de construir el índice."
            ) from exc
        try:
            supported = {item["model"] for item in TextEmbedding.list_supported_models()}
            if self.profile.model not in supported:
                TextEmbedding.add_custom_model(
                    model=self.profile.model,
                    pooling=PoolingType.MEAN,
                    normalization=self.profile.normalize,
                    sources=ModelSource(hf=self.profile.model),
                    dim=self.profile.dimension,
                    model_file="onnx/model.onnx",
                )
            self._model = TextEmbedding(model_name=self.profile.model)
        except Exception as exc:
            raise EmbeddingError(
                f"No se pudo cargar el modelo de embeddings {self.profile.model}: {exc}"
            ) from exc
        return self._model

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        model = self._ensure_model()
        try:
            vectors = np.asarray(list(model.embed(list(texts))), dtype=FLOAT_DTYPE)
        except Exception as exc:
            raise EmbeddingError(f"Falló la generación de embeddings: {exc}") from exc
        if vectors.ndim != 2 or vectors.shape[1] != self.profile.dimension:
            raise EmbeddingError(
                "El modelo devolvió vectores de dimensión "
                f"{vectors.shape[1] if vectors.ndim == 2 else 'desconocida'}; "
                f"se esperaba {self.profile.dimension}."
            )
        return _normalize_rows(vectors) if self.profile.normalize else vectors

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        prepared = [f"{self.profile.passage_prefix}{text}" for text in texts]
        if not prepared:
            return np.zeros((0, self.profile.dimension), dtype=FLOAT_DTYPE)
        return self._embed(prepared)

    def embed_query(self, text: str) -> np.ndarray:
        vectors = self._embed([f"{self.profile.query_prefix}{text}"])
        return vectors[0]


def build_embedder(profile: EmbeddingProfile, *, kind: str = "fastembed") -> Embedder:
    """Create the real or the deterministic embedder for a profile."""
    if kind == "hash":
        return HashEmbedder(profile)
    if kind == "fastembed":
        return FastEmbedEmbedder(profile)
    raise EmbeddingError(f"Tipo de embedder desconocido: {kind}")
