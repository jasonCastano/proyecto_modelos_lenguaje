"""URL canonicalization, HTML extraction and sitemap parsing."""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "igshid",
        "ref",
        "ref_src",
    }
)

_SKIP_TAGS = frozenset({"script", "style", "noscript", "template"})
_DUPLICATE_SLASH_RE = re.compile(r"/{2,}")


@dataclass(slots=True)
class PageMeta:
    title: str | None = None
    description: str | None = None
    lang: str | None = None
    published_at: str | None = None
    site_name: str | None = None


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.content_parts: list[str] = []
        self.lang: str | None = None
        self._skip_stack: list[str] = []
        self._content_stack: list[str] = []
        self._saw_main = False
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag == "html" and self.lang is None:
            self.lang = attributes.get("lang") or None
        if tag in _SKIP_TAGS:
            self._skip_stack.append(tag)
            return
        if tag in {"main", "article"}:
            self._content_stack.append(tag)
            if tag == "main":
                self._saw_main = True
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        elif tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            content = attributes.get("content")
            if key and content and key.lower() not in self.meta:
                self.meta[key.lower()] = content
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
        elif tag in {"main", "article"} and self._content_stack and self._content_stack[-1] == tag:
            self._content_stack.pop()
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if not self._skip_stack and data.strip():
            self.text_parts.append(data)
            if self._saw_main and self._content_stack:
                self.content_parts.append(data)


def decode_body(body: bytes, content_type: str | None = None) -> str:
    if body.startswith(b"\xef\xbb\xbf"):
        body = body[3:]
    charset = "utf-8"
    if content_type:
        match = re.search(r"charset=([\w-]+)", content_type, flags=re.IGNORECASE)
        if match:
            charset = match.group(1)
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def canonicalize_url(url: str, base: str | None = None) -> str:
    """Return a stable canonical URL or raise ``ValueError`` for non-HTTP(S)."""
    candidate = urljoin(base, url.strip()) if base else url.strip()
    parts = urlsplit(candidate)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {scheme!r}")
    if parts.username or parts.password:
        raise ValueError("URLs with embedded credentials are rejected")
    host = (parts.hostname or "").lower()
    if not host:
        raise ValueError("URL has no host")
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"invalid port in URL: {candidate}") from exc
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host_part = f"[{host}]" if ":" in host else host
        netloc = f"{host_part}:{port}"
    else:
        netloc = f"[{host}]" if ":" in host else host
    path = _DUPLICATE_SLASH_RE.sub("/", parts.path) or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def same_site(url: str, domain: str) -> bool:
    host = host_of(url)
    domain = domain.lower()
    return host == domain or host.endswith(f".{domain}")


def extract_links(html: str, base_url: str) -> tuple[str, ...]:
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    found: list[str] = []
    seen: set[str] = set()
    for raw in parser.links:
        try:
            canonical = canonicalize_url(raw, base_url)
        except ValueError:
            continue
        if canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return tuple(found)


def extract_meta(html: str) -> PageMeta:
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    title = " ".join(part.strip() for part in parser.title_parts if part.strip()) or None
    meta = parser.meta
    published = (
        meta.get("article:published_time")
        or meta.get("og:article:published_time")
        or meta.get("date")
        or meta.get("publishdate")
        or meta.get("pubdate")
    )
    return PageMeta(
        title=title or meta.get("og:title"),
        description=meta.get("description") or meta.get("og:description"),
        lang=parser.lang,
        published_at=published,
        site_name=meta.get("og:site_name"),
    )


def visible_text(html: str) -> str:
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    full = re.sub(r"\s+", " ", " ".join(parser.text_parts)).strip()
    if parser._saw_main:
        content = re.sub(r"\s+", " ", " ".join(parser.content_parts)).strip()
        if len(content) >= 200:
            return content
    return full


def sitemap_locations(body: bytes) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return ``(page_urls, child_sitemaps)`` from a sitemap or sitemap index."""
    if body.startswith(b"\x1f\x8b"):
        body = gzip.decompress(body)
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"invalid sitemap XML: {exc}") from exc
    tag = root.tag.split("}")[-1].lower()
    pages: list[str] = []
    sitemaps: list[str] = []
    if tag == "sitemapindex":
        for node in root:
            for child in node:
                if child.tag.split("}")[-1].lower() == "loc" and child.text:
                    sitemaps.append(child.text.strip())
    elif tag == "urlset":
        for node in root:
            for child in node:
                if child.tag.split("}")[-1].lower() == "loc" and child.text:
                    pages.append(child.text.strip())
    return tuple(pages), tuple(sitemaps)


def robots_sitemaps(robots_text: str) -> tuple[str, ...]:
    found: list[str] = []
    for line in robots_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == "sitemap" and value.strip():
            found.append(value.strip())
    return tuple(found)
