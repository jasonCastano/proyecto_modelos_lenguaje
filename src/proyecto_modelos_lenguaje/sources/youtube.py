"""YouTube channel and video discovery."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..extractors.links import canonicalize_url
from ..fetchers.youtube import YoutubeAdapter
from .base import DiscoveryCandidate, DiscoveryContext, SourceAdapter


@dataclass(slots=True)
class YoutubeSource(SourceAdapter):
    adapter: YoutubeAdapter | None = None

    async def discover(self, context: DiscoveryContext) -> list[DiscoveryCandidate]:
        adapter = self.adapter or YoutubeAdapter(timeout=context.timeout)
        candidates: list[DiscoveryCandidate] = []
        for seed in self.source.seeds:
            try:
                videos = await asyncio.to_thread(adapter.list_videos, seed)
            except Exception:
                videos = []
            if not videos:
                candidates.append(
                    DiscoveryCandidate(url=canonicalize_url(seed), category=self.default_category)
                )
                continue
            for url, title in videos:
                candidates.append(
                    DiscoveryCandidate(
                        url=canonicalize_url(url),
                        title=title or None,
                        category=self.default_category,
                    )
                )
        return candidates
