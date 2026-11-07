"""Configuración versionada de la recuperación semántica (``config/retrieval.toml``)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from .errors import RetrievalConfigError

DEFAULT_CONFIG_PATH = Path("config") / "retrieval.toml"


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    model: str
    dimension: int
    normalize: bool
    max_tokens: int
    query_prefix: str
    passage_prefix: str


@dataclass(frozen=True, slots=True)
class IndexConfig:
    path: Path
    batch_size: int


@dataclass(frozen=True, slots=True)
class HybridConfig:
    semantic_top_k: int
    lexical_top_k: int
    min_similarity: float
    weight_semantic: float
    weight_lexical: float
    both_bonus: float
    dedup_similarity: float


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    embedding: EmbeddingConfig
    index: IndexConfig
    hybrid: HybridConfig
    source: Path

    @property
    def index_dir(self) -> Path:
        return self.index.path


def _section(document: dict[str, Any], key: str, *, source: Path) -> dict[str, Any]:
    section = document.get(key)
    if not isinstance(section, dict):
        raise RetrievalConfigError(f"Falta la sección [{key}] en {source}.")
    return section


def _string(section: dict[str, Any], key: str, *, table: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RetrievalConfigError(f"[{table}] {key} debe ser texto no vacío.")
    return value


def _integer(section: dict[str, Any], key: str, *, table: str, minimum: int) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RetrievalConfigError(f"[{table}] {key} debe ser un entero >= {minimum}.")
    return value


def _number(
    section: dict[str, Any], key: str, *, table: str, minimum: float, maximum: float | None = None
) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RetrievalConfigError(f"[{table}] {key} debe ser numérico.")
    number = float(value)
    if number < minimum or (maximum is not None and number > maximum):
        upper = f" y <= {maximum}" if maximum is not None else ""
        raise RetrievalConfigError(f"[{table}] {key} debe ser >= {minimum}{upper}.")
    return number


def _boolean(section: dict[str, Any], key: str, *, table: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise RetrievalConfigError(f"[{table}] {key} debe ser booleano.")
    return value


def load_retrieval_config(
    path: str | Path | None = None, *, project_root: Path | None = None
) -> RetrievalConfig:
    """Load and validate the retrieval configuration."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    source = Path(path) if path is not None else root / DEFAULT_CONFIG_PATH
    if not source.is_absolute():
        source = root / source
    if not source.is_file():
        raise RetrievalConfigError(f"No existe la configuración de recuperación: {source}.")
    try:
        document = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise RetrievalConfigError(f"TOML inválido en {source}: {exc}") from exc

    embedding_raw = _section(document, "embedding", source=source)
    index_raw = _section(document, "index", source=source)
    hybrid_raw = _section(document, "hybrid", source=source)

    embedding = EmbeddingConfig(
        model=_string(embedding_raw, "model", table="embedding"),
        dimension=_integer(embedding_raw, "dimension", table="embedding", minimum=1),
        normalize=_boolean(embedding_raw, "normalize", table="embedding"),
        max_tokens=_integer(embedding_raw, "max_tokens", table="embedding", minimum=1),
        query_prefix=_string(embedding_raw, "query_prefix", table="embedding"),
        passage_prefix=_string(embedding_raw, "passage_prefix", table="embedding"),
    )

    index_path = Path(_string(index_raw, "path", table="index"))
    if not index_path.is_absolute():
        index_path = root / index_path
    index = IndexConfig(
        path=index_path,
        batch_size=_integer(index_raw, "batch_size", table="index", minimum=1),
    )

    hybrid = HybridConfig(
        semantic_top_k=_integer(hybrid_raw, "semantic_top_k", table="hybrid", minimum=1),
        lexical_top_k=_integer(hybrid_raw, "lexical_top_k", table="hybrid", minimum=1),
        min_similarity=_number(
            hybrid_raw, "min_similarity", table="hybrid", minimum=0.0, maximum=1.0
        ),
        weight_semantic=_number(
            hybrid_raw, "weight_semantic", table="hybrid", minimum=0.0, maximum=1.0
        ),
        weight_lexical=_number(
            hybrid_raw, "weight_lexical", table="hybrid", minimum=0.0, maximum=1.0
        ),
        both_bonus=_number(hybrid_raw, "both_bonus", table="hybrid", minimum=0.0, maximum=1.0),
        dedup_similarity=_number(
            hybrid_raw, "dedup_similarity", table="hybrid", minimum=0.0, maximum=1.0
        ),
    )

    return RetrievalConfig(embedding=embedding, index=index, hybrid=hybrid, source=source)
