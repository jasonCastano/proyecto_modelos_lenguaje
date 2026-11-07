"""Recuperación semántica (RAG) del Módulo 2.

Expone el perfil de embeddings, los generadores, el índice reproducible y la fusión híbrida con
trazabilidad. El paquete no escribe en las capas medallion: solo lee ``data/gold`` y publica su
artefacto en ``data/module2``.
"""

from __future__ import annotations

from .config import (
    EmbeddingConfig,
    HybridConfig,
    IndexConfig,
    RetrievalConfig,
    load_retrieval_config,
)
from .embeddings import (
    Embedder,
    EmbeddingProfile,
    FastEmbedEmbedder,
    HashEmbedder,
    build_embedder,
    load_embedding_profile,
)
from .errors import (
    EmbeddingError,
    GoldError,
    IndexExistsError,
    IndexInvalidError,
    IndexUnavailableError,
    RagError,
    RetrievalConfigError,
)
from .hybrid import (
    HybridRetriever,
    RetrievalTrace,
    RetrievedFragment,
    SemanticRetriever,
)
from .index import (
    Fragment,
    IndexManifest,
    LoadedIndex,
    VerificationResult,
    build_index,
    chunk_text,
    load_index,
    sha256_file,
    verify_index,
)

__all__ = [
    "Embedder",
    "EmbeddingConfig",
    "EmbeddingError",
    "EmbeddingProfile",
    "FastEmbedEmbedder",
    "Fragment",
    "GoldError",
    "HashEmbedder",
    "HybridConfig",
    "HybridRetriever",
    "IndexConfig",
    "IndexExistsError",
    "IndexInvalidError",
    "IndexManifest",
    "IndexUnavailableError",
    "LoadedIndex",
    "RagError",
    "RetrievalConfig",
    "RetrievalConfigError",
    "RetrievalTrace",
    "RetrievedFragment",
    "SemanticRetriever",
    "VerificationResult",
    "build_embedder",
    "build_index",
    "chunk_text",
    "load_embedding_profile",
    "load_index",
    "load_retrieval_config",
    "sha256_file",
    "verify_index",
]
