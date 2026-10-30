"""Unit tests for URL canonicalization, HTML extraction and sitemaps."""

from __future__ import annotations

from proyecto_modelos_lenguaje.extractors.links import (
    canonicalize_url,
    extract_links,
    extract_meta,
    robots_sitemaps,
    sitemap_locations,
    visible_text,
)


def test_canonicalize_url_strips_tracking_fragment_and_default_port() -> None:
    url = "HTTPS://Example.COM:443/a/?utm_source=x&b=2&a=1#section"
    assert canonicalize_url(url) == "https://example.com/a?a=1&b=2"


def test_canonicalize_url_sorts_query_and_keeps_meaningful_params() -> None:
    assert (
        canonicalize_url("https://example.com/search?z=1&a=2&fbclid=abc")
        == "https://example.com/search?a=2&z=1"
    )


def test_canonicalize_url_rejects_non_http_and_credentials() -> None:
    for candidate in ("ftp://example.com/file", "https://user:pass@example.com/"):
        try:
            canonicalize_url(candidate)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {candidate}")


def test_extract_links_resolves_relative_urls() -> None:
    html = '<a href="/about">A</a><a href="../doc.pdf">B</a><a href="mailto:x@y.z">C</a>'
    links = extract_links(html, "https://example.com/news/index.html")
    assert "https://example.com/about" in links
    assert "https://example.com/doc.pdf" in links
    assert all(link.startswith("http") for link in links)


def test_extract_meta_and_visible_text() -> None:
    html = """<html lang="es"><head><title>Mi título</title>
    <meta name="description" content="Descripción">
    <meta property="article:published_time" content="2026-10-01T12:00:00Z">
    </head><body><p>Hola mundo</p><script>oculto</script></body></html>"""
    meta = extract_meta(html)
    assert meta.title == "Mi título"
    assert meta.description == "Descripción"
    assert meta.lang == "es"
    assert meta.published_at == "2026-10-01T12:00:00Z"
    text = visible_text(html)
    assert "Hola mundo" in text
    assert "oculto" not in text


def test_sitemap_urlset_and_index() -> None:
    urlset = b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/a</loc></url>
      <url><loc>https://example.com/b</loc></url>
    </urlset>"""
    pages, children = sitemap_locations(urlset)
    assert pages == ("https://example.com/a", "https://example.com/b")
    assert children == ()

    index = b"""<?xml version="1.0"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.com/one.xml</loc></sitemap>
    </sitemapindex>"""
    pages, children = sitemap_locations(index)
    assert pages == ()
    assert children == ("https://example.com/one.xml",)


def test_robots_sitemaps() -> None:
    text = "User-agent: *\nDisallow: /admin\nSitemap: https://example.com/sitemap.xml\n"
    assert robots_sitemaps(text) == ("https://example.com/sitemap.xml",)
