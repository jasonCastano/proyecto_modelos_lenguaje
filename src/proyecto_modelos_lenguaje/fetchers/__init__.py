"""Fetcher adapters."""

from .base import Fetcher, FetchResponse
from .browser import StealthyBrowserFetcher
from .http import ScraplingFetcher, StdlibFetcher, build_http_fetcher
from .social import SocialContent, parse_social_page, platform_restriction
from .youtube import YoutubeAdapter, YoutubePart, YoutubeResult

__all__ = [
    "FetchResponse",
    "Fetcher",
    "ScraplingFetcher",
    "SocialContent",
    "StdlibFetcher",
    "StealthyBrowserFetcher",
    "YoutubeAdapter",
    "YoutubePart",
    "YoutubeResult",
    "build_http_fetcher",
    "parse_social_page",
    "platform_restriction",
]
