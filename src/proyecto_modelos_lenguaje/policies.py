"""Access policies: allowlists, robots.txt, SSRF protection and rate limiting."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .config import AppConfig, SourceConfig
from .extractors.links import host_of
from .models import ReasonCode


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason_code: str
    detail: str
    crawl_delay: float | None = None


def _is_public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def check_host_safety(url: str, *, allow_private: bool = False) -> tuple[bool, str]:
    """Reject non-HTTP(S), credentials and private/reserved destinations (SSRF guard)."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        return False, "unsupported_scheme"
    if parts.username or parts.password:
        return False, "embedded_credentials"
    host = parts.hostname
    if not host:
        return False, "missing_host"
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror:
        return False, "unresolvable_host"
    addresses = {info[4][0] for info in infos}
    if not allow_private and any(not _is_public_ip(address) for address in addresses):
        return False, "private_address"
    return True, "ok"


class RobotsCache:
    """Fetch and cache robots.txt decisions per host."""

    def __init__(
        self,
        fetcher: object,
        *,
        user_agent: str,
        timeout: float,
        allow_private: bool = False,
    ) -> None:
        self._fetcher = fetcher
        self._user_agent = user_agent
        self._timeout = timeout
        self._allow_private = allow_private
        self._cache: dict[str, tuple[RobotFileParser | None, float | None, str]] = {}

    async def decision(self, url: str) -> tuple[bool, str, float | None]:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._cache:
            self._cache[origin] = await self._load(origin)
        parser, delay, status = self._cache[origin]
        if parser is None:
            # robots.txt absent or unreachable in a permissive way: allow.
            return status != "forbidden", status, delay
        allowed = parser.can_fetch(self._user_agent, url)
        return allowed, "allowed_by_robots" if allowed else "disallowed_by_robots", delay

    async def _load(self, origin: str) -> tuple[RobotFileParser | None, float | None, str]:
        safe, reason = check_host_safety(f"{origin}/robots.txt", allow_private=self._allow_private)
        if not safe:
            return None, None, reason
        response = await self._fetcher.fetch(f"{origin}/robots.txt", timeout=self._timeout)  # type: ignore[attr-defined]
        if response.error:
            return None, None, "robots_unreachable"
        if response.status in {401, 403}:
            return None, None, "forbidden"
        if response.status in {404, 410} or response.status >= 500:
            return None, None, "absent"
        if response.status != 200:
            return None, None, f"http_{response.status}"
        text = response.body.decode("utf-8", errors="replace")
        parser = RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")
        parser.parse(text.splitlines())
        return parser, _crawl_delay(text, self._user_agent), "ok"


def _crawl_delay(robots_text: str, user_agent: str) -> float | None:
    agent = user_agent.split("/", 1)[0].lower()
    delays: dict[str, float] = {}
    current: list[str] = []
    for line in robots_text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            current = [value.lower()]
        elif key == "crawl-delay" and current:
            try:
                parsed = float(value)
            except ValueError:
                continue
            for name in current:
                delays[name] = parsed
    for name in (agent, "*"):
        if name in delays:
            return delays[name]
    return None


class PolicyEngine:
    """Combine manual exclusions, source rules, SSRF checks and robots.txt."""

    def __init__(
        self,
        config: AppConfig,
        robots: RobotsCache,
        *,
        allow_private: bool = False,
    ) -> None:
        self._config = config
        self._robots = robots
        self._allow_private = allow_private
        self._excluded_domains = tuple(domain.lower() for domain in config.exclusions_domains)
        self._excluded_urls = frozenset(config.exclusions_urls)

    def _manual_exclusion(self, url: str) -> str | None:
        if url in self._excluded_urls:
            return "url_excluded"
        host = host_of(url)
        for domain in self._excluded_domains:
            if host == domain or host.endswith(f".{domain}"):
                return f"domain_excluded:{domain}"
        return None

    def _path_rule(self, url: str, source: SourceConfig) -> str | None:
        path = urlsplit(url).path or "/"
        for prefix in source.policy.excluded_paths:
            if prefix and path.startswith(prefix):
                return f"path_excluded:{prefix}"
        if source.policy.allowed_paths and not any(
            path.startswith(prefix) for prefix in source.policy.allowed_paths
        ):
            return "outside_allowed_paths"
        return None

    async def evaluate(self, url: str, source: SourceConfig) -> PolicyDecision:
        safe, safety_reason = check_host_safety(url, allow_private=self._allow_private)
        if not safe:
            return PolicyDecision(False, ReasonCode.OUT_OF_SCOPE, safety_reason)
        excluded = self._manual_exclusion(url)
        if excluded:
            return PolicyDecision(False, ReasonCode.MANUAL_EXCLUSION, excluded)
        if source.policy.requires_auth:
            return PolicyDecision(False, ReasonCode.REQUIRES_AUTH, "source_requires_auth")
        if not source.enabled:
            return PolicyDecision(False, ReasonCode.OUT_OF_SCOPE, "source_disabled")
        path_rule = self._path_rule(url, source)
        if path_rule:
            return PolicyDecision(False, ReasonCode.TOS_RESTRICTED, path_rule)
        if source.policy.robots == "respect":
            allowed, reason, delay = await self._robots.decision(url)
            if not allowed:
                code = (
                    ReasonCode.ROBOTS_DISALLOWED
                    if reason == "disallowed_by_robots"
                    else ReasonCode.TOS_RESTRICTED
                )
                return PolicyDecision(False, code, reason, delay)
            return PolicyDecision(True, "allowed", reason, delay)
        return PolicyDecision(True, "allowed", "robots_ignored")


class RateLimiter:
    """Serialize requests per host and enforce a minimum delay."""

    def __init__(self, *, default_delay: float) -> None:
        self._default_delay = default_delay
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_request: dict[str, float] = {}

    async def wait(self, host: str, delay: float | None = None) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        effective = max(delay or self._default_delay, 0.0)
        async with lock:
            now = time.monotonic()
            previous = self._last_request.get(host, 0.0)
            remaining = previous + effective - now
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_request[host] = time.monotonic()
