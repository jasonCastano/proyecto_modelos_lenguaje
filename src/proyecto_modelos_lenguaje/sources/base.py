"""Source discovery adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from ..config import SourceConfig
from ..extractors.links import (
    canonicalize_url,
    decode_body,
    host_of,
    robots_sitemaps,
    sitemap_locations,
)
from ..fetchers.base import Fetcher, FetchResponse
from ..models import Category
from ..policies import PolicyEngine, RateLimiter


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    url: str
    title: str | None = None
    category: str | None = None
    depth: int = 0


@dataclass(slots=True)
class DiscoveryContext:
    fetcher: Fetcher
    policy: PolicyEngine
    limiter: RateLimiter
    timeout: float = 30.0
    max_sitemaps: int = 100

    async def fetch_allowed(
        self,
        url: str,
        source: SourceConfig,
        *,
        timeout: float | None = None,
    ) -> FetchResponse | None:
        decision = await self.policy.evaluate(url, source)
        if not decision.allowed:
            return None
        delay = decision.crawl_delay or source.delay_seconds
        await self.limiter.wait(host_of(url), delay)
        return await self.fetcher.fetch(url, timeout=timeout or self.timeout)


@dataclass(slots=True)
class SourceAdapter:
    """Generic adapter: seeds, robots sitemaps and configured sitemaps."""

    source: SourceConfig

    @property
    def default_category(self) -> str:
        return (
            self.source.category_hints[0] if self.source.category_hints else Category.IDENTITY.value
        )

    async def discover(self, context: DiscoveryContext) -> list[DiscoveryCandidate]:
        candidates: list[DiscoveryCandidate] = [
            DiscoveryCandidate(url=canonicalize_url(seed), category=self.default_category)
            for seed in self.source.seeds
        ]
        sitemap_urls: list[str] = list(self.source.sitemaps)
        if self.source.policy.robots == "respect":
            robots_url = self._origin(self.source.seeds[0]) + "/robots.txt"
            response = await context.fetch_allowed(robots_url, self.source)
            if response and response.status == 200:
                sitemap_urls.extend(robots_sitemaps(decode_body(response.body)))
        seen_sitemaps: set[str] = set()
        for sitemap in sitemap_urls:
            if len(seen_sitemaps) >= context.max_sitemaps:
                break
            try:
                canonical = canonicalize_url(sitemap)
            except ValueError:
                continue
            if canonical in seen_sitemaps:
                continue
            await self._collect_sitemap(context, canonical, candidates, seen_sitemaps, depth=0)
        return candidates

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    async def _collect_sitemap(
        self,
        context: DiscoveryContext,
        url: str,
        candidates: list[DiscoveryCandidate],
        seen: set[str],
        *,
        depth: int,
    ) -> None:
        if depth > 3 or len(seen) >= context.max_sitemaps or url in seen:
            return
        seen.add(url)
        response = await context.fetch_allowed(url, self.source)
        if response is None or response.status != 200:
            return
        try:
            pages, children = sitemap_locations(response.body)
        except ValueError:
            return
        for page in pages:
            try:
                canonical = canonicalize_url(page)
            except ValueError:
                continue
            candidates.append(
                DiscoveryCandidate(url=canonical, category=self.default_category, depth=1)
            )
        for child in children:
            try:
                child_url = canonicalize_url(child)
            except ValueError:
                continue
            await self._collect_sitemap(context, child_url, candidates, seen, depth=depth + 1)


@dataclass(slots=True)
class SeedOnlySource(SourceAdapter):
    """Sources without link following (social profiles)."""

    async def discover(self, context: DiscoveryContext) -> list[DiscoveryCandidate]:
        return [
            DiscoveryCandidate(url=canonicalize_url(seed), category=self.default_category)
            for seed in self.source.seeds
        ]


@dataclass(slots=True)
class SitemapSource(SourceAdapter):
    """Official/news sites: sitemap-first with bounded link following."""

    extra_sitemaps: tuple[str, ...] = field(default_factory=tuple)

    async def discover(self, context: DiscoveryContext) -> list[DiscoveryCandidate]:
        candidates = await super().discover(context)
        seen = {candidate.url for candidate in candidates}
        for extra in self.extra_sitemaps:
            try:
                canonical = canonicalize_url(extra)
            except ValueError:
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            await self._collect_sitemap(context, canonical, candidates, seen, depth=0)
        return candidates
