"""scrapling-based HTTP fetcher with a stdlib fallback."""

from __future__ import annotations

import asyncio
import urllib.error
import urllib.request

from .base import FetchResponse

_MAX_BODY = 200 * 1024 * 1024


class ScraplingFetcher:
    """Concurrent HTTP fetcher backed by ``scrapling.AsyncFetcher``."""

    def __init__(self, *, user_agent: str, timeout: float = 30.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout

    async def fetch(self, url: str, *, timeout: float | None = None) -> FetchResponse:
        from scrapling.fetchers import AsyncFetcher

        try:
            response = await AsyncFetcher.get(
                url,
                timeout=timeout or self._timeout,
                headers={"User-Agent": self._user_agent},
                follow_redirects=True,
                stealthy_headers=True,
            )
        except Exception as exc:  # network and TLS failures are data, not crashes
            return FetchResponse(url, url, 0, {}, b"", error=f"{type(exc).__name__}: {exc}")
        body = response.body if isinstance(response.body, bytes) else str(response.body).encode()
        if len(body) > _MAX_BODY:
            return FetchResponse(
                url, url, int(response.status), {}, b"", error="response_too_large"
            )
        headers = {str(key).lower(): str(value) for key, value in (response.headers or {}).items()}
        return FetchResponse(
            url=url,
            final_url=str(getattr(response, "url", url)),
            status=int(response.status),
            headers=headers,
            body=body,
        )

    async def aclose(self) -> None:
        return None


class StdlibFetcher:
    """Minimal fallback used when scrapling extras are unavailable."""

    def __init__(self, *, user_agent: str, timeout: float = 30.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout

    async def fetch(self, url: str, *, timeout: float | None = None) -> FetchResponse:
        return await asyncio.to_thread(self._fetch_sync, url, timeout or self._timeout)

    def _fetch_sync(self, url: str, timeout: float) -> FetchResponse:
        request = urllib.request.Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(_MAX_BODY + 1)
                if len(body) > _MAX_BODY:
                    return FetchResponse(
                        url, url, response.status, {}, b"", error="response_too_large"
                    )
                headers = {key.lower(): value for key, value in response.headers.items()}
                return FetchResponse(
                    url=url,
                    final_url=response.geturl(),
                    status=int(response.status),
                    headers=headers,
                    body=body,
                )
        except urllib.error.HTTPError as exc:
            return FetchResponse(
                url, url, int(exc.code), dict(exc.headers.items()) if exc.headers else {}, b""
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return FetchResponse(url, url, 0, {}, b"", error=f"{type(exc).__name__}: {exc}")

    async def aclose(self) -> None:
        return None


def build_http_fetcher(
    *, user_agent: str, timeout: float = 30.0
) -> ScraplingFetcher | StdlibFetcher:
    try:
        from scrapling.fetchers import AsyncFetcher  # noqa: F401
    except Exception:
        return StdlibFetcher(user_agent=user_agent, timeout=timeout)
    return ScraplingFetcher(user_agent=user_agent, timeout=timeout)
