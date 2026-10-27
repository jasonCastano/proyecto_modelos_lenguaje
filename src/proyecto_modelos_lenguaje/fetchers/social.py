"""Public social-page helpers and platform access policy."""

from __future__ import annotations

from dataclasses import dataclass

from ..extractors.links import PageMeta, extract_meta, visible_text
from ..models import ReasonCode

# Platforms that require authentication or explicitly prohibit automated access.
AUTH_REQUIRED_PLATFORMS = {
    "x": ReasonCode.REQUIRES_AUTH,
    "linkedin": ReasonCode.REQUIRES_AUTH,
    "twitter": ReasonCode.REQUIRES_AUTH,
}


@dataclass(frozen=True, slots=True)
class SocialContent:
    title: str | None
    description: str | None
    published_at: str | None
    text: str
    language_html: str | None


def platform_restriction(platform: str) -> str | None:
    return AUTH_REQUIRED_PLATFORMS.get(platform.lower())


def parse_social_page(html: str) -> SocialContent:
    meta: PageMeta = extract_meta(html)
    return SocialContent(
        title=meta.title,
        description=meta.description,
        published_at=meta.published_at,
        text=visible_text(html),
        language_html=meta.lang,
    )
