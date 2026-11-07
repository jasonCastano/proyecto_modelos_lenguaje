"""Errores del paquete de recuperación semántica."""

from __future__ import annotations


class RagError(Exception):
    """Base de los errores controlados del Módulo 2."""


class RetrievalConfigError(RagError, ValueError):
    """La configuración de recuperación falta o es inválida."""


class EmbeddingError(RagError, RuntimeError):
    """El modelo de embeddings no está disponible o falló."""


class GoldError(RagError, RuntimeError):
    """La capa de oro falta, está vacía o es ilegible."""


class IndexUnavailableError(RagError, RuntimeError):
    """No existe un índice vectorial utilizable."""


class IndexInvalidError(RagError, RuntimeError):
    """El índice existe pero no es coherente con su manifiesto o la configuración."""


class IndexExistsError(RagError, RuntimeError):
    """Ya existe un índice equivalente y no se pidió reconstruirlo."""
