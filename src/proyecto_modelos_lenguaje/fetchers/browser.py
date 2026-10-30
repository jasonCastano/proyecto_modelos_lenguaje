"""Optional browser fetcher for JavaScript-heavy public pages."""

from __future__ import annotations

from .base import FetchResponse


class StealthyBrowserFetcher:
    """Adapter over ``scrapling.StealthyFetcher``; disabled unless a source needs it."""

    def __init__(self, *, user_agent: str, timeout: float = 45.0) -> None:
        self._user_agent = user_agent
        self._timeout = timeout

    async def fetch(self, url: str, *, timeout: float | None = None) -> FetchResponse:
        try:
            from scrapling.fetchers import StealthyFetcher
        except Exception as exc:
            return FetchResponse(url, url, 0, {}, b"", error=f"browser_unavailable: {exc}")
        try:
            response = await StealthyFetcher.async_fetch(
                url,
                headless=True,
                timeout=int((timeout or self._timeout) * 1000),
                network_idle=True,
                disable_resources=True,
                useragent=self._user_agent,
            )
        except Exception as exc:
            return FetchResponse(url, url, 0, {}, b"", error=f"{type(exc).__name__}: {exc}")
        body = response.body if isinstance(response.body, bytes) else str(response.body).encode()
        headers = {str(key).lower(): str(value) for key, value in (response.headers or {}).items()}
        return FetchResponse(
            url, str(getattr(response, "url", url)), int(response.status), headers, body
        )

    async def aclose(self) -> None:
        return None
