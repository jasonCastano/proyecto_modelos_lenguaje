"""Source adapter factory."""

from __future__ import annotations

from ..config import SourceConfig
from .base import SeedOnlySource, SourceAdapter
from .news import NewsSource
from .official_site import OfficialSiteSource
from .open_data import OpenDataSource
from .youtube import YoutubeSource


def build_source(source: SourceConfig) -> SourceAdapter:
    if source.platform == "youtube":
        return YoutubeSource(source)
    if source.platform in {"facebook", "instagram"}:
        return SeedOnlySource(source)
    if source.platform == "news":
        return NewsSource(source)
    if source.platform == "open_data":
        return OpenDataSource(source)
    if source.source_id == "official_site":
        return OfficialSiteSource(source)
    return SourceAdapter(source)


__all__ = [
    "NewsSource",
    "OfficialSiteSource",
    "OpenDataSource",
    "SeedOnlySource",
    "SourceAdapter",
    "YoutubeSource",
    "build_source",
]
