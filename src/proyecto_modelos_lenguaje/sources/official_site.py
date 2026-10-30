"""Official corporate site discovery."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SitemapSource


@dataclass(slots=True)
class OfficialSiteSource(SitemapSource):
    """Manuelita's corporate site: sitemap index first, then bounded link following."""
