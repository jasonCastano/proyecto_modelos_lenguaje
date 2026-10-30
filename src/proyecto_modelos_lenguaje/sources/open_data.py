"""Open-data and public-registry discovery."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SitemapSource


@dataclass(slots=True)
class OpenDataSource(SitemapSource):
    """Superintendencia, SECOP, datos.gov.co and business registries."""
