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
        candidates: list[DiscoveryCandidate] = []
        for seed in self.source.seeds:
            canonical = canonicalize_url(seed)
            if "/watch" in canonical or "/shorts/" in canonical:
                candidates.append(
                    DiscoveryCandidate(
                        url=canonical,
                        title=None,
                        category=self.default_category,
                    )
                )
                continue
            candidates.append(
                DiscoveryCandidate(
                    url=canonical,
                    title="Canal oficial de YouTube",
                    category=self.default_category,
                )
            )
            adapter = self.adapter or YoutubeAdapter(timeout=context.timeout)
            try:
                videos = await asyncio.to_thread(adapter.list_videos, canonical)
            except Exception:
                videos = []
            seen = {canonical}
            for url, title in videos:
                video_url = canonicalize_url(url)
                if video_url in seen:
                    continue
                seen.add(video_url)
                candidates.append(
                    DiscoveryCandidate(
                        url=video_url,
                        title=title or None,
                        category=self.default_category,
                    )
                )
        return candidates
