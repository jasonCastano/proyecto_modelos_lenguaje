"""Unit tests for access policies and rate limiting."""

from __future__ import annotations

import asyncio
import dataclasses
import time

import pytest

from proyecto_modelos_lenguaje.fetchers.base import FetchResponse
from proyecto_modelos_lenguaje.models import ReasonCode
from proyecto_modelos_lenguaje.policies import (
    PolicyEngine,
    RateLimiter,
    RobotsCache,
    check_host_safety,
)


class FakeFetcher:
    def __init__(self, responses: dict[str, FetchResponse]) -> None:
        self.responses = responses

    async def fetch(self, url: str, *, timeout: float | None = None) -> FetchResponse:
        return self.responses.get(url, FetchResponse(url, url, 404, {}, b""))

    async def aclose(self) -> None:
        return None


def test_private_addresses_are_blocked_unless_allowed() -> None:
    assert check_host_safety("http://127.0.0.1/") == (False, "private_address")
    assert check_host_safety("http://127.0.0.1/", allow_private=True)[0] is True
    assert check_host_safety("ftp://example.com/") == (False, "unsupported_scheme")
    assert check_host_safety("http://user:pass@example.com/") == (False, "embedded_credentials")


def test_robots_disallow_and_crawl_delay(app_config, server) -> None:
    robots = "User-agent: *\nDisallow: /blocked\nCrawl-delay: 0.75\n"
    fetcher = FakeFetcher(
        {
            f"{server}/robots.txt": FetchResponse(
                f"{server}/robots.txt", server, 200, {}, robots.encode()
            )
        }
    )
    cache = RobotsCache(fetcher, user_agent="ManuelitaRAG-test/0.1", timeout=5, allow_private=True)
    engine = PolicyEngine(app_config, cache, allow_private=True)
    source = app_config.sources[0]

    blocked = asyncio.run(engine.evaluate(f"{server}/blocked", source))
    allowed = asyncio.run(engine.evaluate(f"{server}/about", source))
    assert blocked.allowed is False
    assert blocked.reason_code == ReasonCode.ROBOTS_DISALLOWED.value
    assert blocked.crawl_delay == 0.75
    assert allowed.allowed is True


def test_manual_exclusion_and_auth_required(app_config, server) -> None:
    fetcher = FakeFetcher({})
    cache = RobotsCache(fetcher, user_agent="test-agent", timeout=5, allow_private=True)
    engine = PolicyEngine(app_config, cache, allow_private=True)
    assert engine._manual_exclusion("https://linkedin.com/company/manuelita") is not None

    source = app_config.sources[0]
    auth_source = dataclasses.replace(
        source, policy=dataclasses.replace(source.policy, requires_auth=True)
    )
    decision = asyncio.run(engine.evaluate(f"{server}/about", auth_source))
    assert decision.allowed is False
    assert decision.reason_code == ReasonCode.REQUIRES_AUTH.value


def test_rate_limiter_enforces_delay() -> None:
    async def scenario() -> float:
        limiter = RateLimiter(default_delay=0.05)
        start = time.monotonic()
        await limiter.wait("example.com")
        await limiter.wait("example.com")
        return time.monotonic() - start

    assert asyncio.run(scenario()) >= 0.04


@pytest.mark.parametrize("url", ["http://10.0.0.1/", "http://192.168.1.1/"])
def test_reserved_ranges_are_rejected(url: str) -> None:
    assert check_host_safety(url)[0] is False
