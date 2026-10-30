"""News and blog discovery."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SitemapSource


@dataclass(slots=True)
class NewsSource(SitemapSource):
    """Press rooms, news portals and blogs; sitemap-first with shallow pagination."""
