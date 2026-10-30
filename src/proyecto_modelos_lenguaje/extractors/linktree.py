"""Linktree public page parsing."""

from __future__ import annotations

import json
import re
from typing import Any

_NEXT_DATA = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


def parse_linktree(html: str) -> dict[str, Any] | None:
    """Extract the public account and links from a Linktree page."""
    match = _NEXT_DATA.search(html)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    page = data.get("props", {}).get("pageProps", {})
    account = page.get("account", {})
    links = []
    for link in page.get("links", []):
        url = link.get("url")
        if not url:
            continue
        links.append(
            {
                "title": link.get("title"),
                "url": url,
                "position": link.get("position"),
            }
        )
    return {
        "schema_version": "1.0",
        "source": "linktree",
        "username": account.get("username"),
        "page_title": account.get("pageTitle"),
        "description": account.get("description"),
        "profile_picture": account.get("profilePictureUrl"),
        "links": links,
        "social_links": account.get("socialLinks", []),
    }
