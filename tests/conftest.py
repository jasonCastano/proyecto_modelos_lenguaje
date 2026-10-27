"""Shared fixtures for offline bronze tests."""

from __future__ import annotations

import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.config import AppConfig, load_config, load_coverage_items
from proyecto_modelos_lenguaje.fetchers.http import build_http_fetcher
from proyecto_modelos_lenguaje.pipeline import CampaignRunner
from proyecto_modelos_lenguaje.storage import BronzeStorage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COVERAGE_PATH = PROJECT_ROOT / "config" / "coverage-items.toml"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_: object) -> None:
        return None


@pytest.fixture()
def site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    (root / "sub").mkdir(parents=True)
    (root / "robots.txt").write_text(
        "User-agent: *\nDisallow: /blocked\nAllow: /\n", encoding="utf-8"
    )
    (root / "sitemap.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/</loc></url>
  <url><loc>/about.html</loc></url>
  <url><loc>/doc.pdf</loc></url>
</urlset>
""",
        encoding="utf-8",
    )
    (root / "index.html").write_text(
        """<!doctype html>
<html lang="es">
<head><title>Manuelita | Inicio</title>
<meta name="description" content="Ingenio Manuelita">
<meta property="article:published_time" content="2026-10-01T12:00:00Z">
</head>
<body>
<h1>Ingenio Manuelita</h1>
<p>Somos una empresa agroindustrial con historia y trayectoria en el Valle del Cauca.</p>
<a href="/about.html">Acerca</a>
<a href="/blocked.html">Bloqueada</a>
<a href="/doc.pdf">Documento</a>
<a href="https://example.com/">Externo</a>
<script>var hidden = "no debe aparecer";</script>
</body>
</html>
""",
        encoding="utf-8",
    )
    (root / "about.html").write_text(
        """<!doctype html>
<html lang="es">
<head><title>Misión y visión</title></head>
<body>
<h1>Misión y visión</h1>
<p>Nuestra misión y visión guían la sostenibilidad y el desarrollo.</p>
<p>Productos y servicios: azúcar, etanol y bioenergía.</p>
<p>Nuestros valores y principios incluyen integridad y respeto.</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    (root / "blocked.html").write_text("<html><body>No rastrear</body></html>", encoding="utf-8")
    (root / "doc.pdf").write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    )
    return root


@pytest.fixture()
def server(site: Path):
    handler = functools.partial(_QuietHandler, directory=str(site))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{httpd.server_address[1]}"
    (site / "sitemap.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{base_url}/</loc></url>
  <url><loc>{base_url}/about.html</loc></url>
  <url><loc>{base_url}/doc.pdf</loc></url>
</urlset>
""",
        encoding="utf-8",
    )
    (site / "robots.txt").write_text(
        f"User-agent: *\nDisallow: /blocked\nAllow: /\nSitemap: {base_url}/sitemap.xml\n",
        encoding="utf-8",
    )
    try:
        yield base_url
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


@pytest.fixture()
def write_config(tmp_path: Path):
    def _write(
        base_url: str,
        *,
        limit: int = 10_000_000,
        max_depth: int = 2,
        max_retries: int = 1,
        delay: float = 0.5,
        campaign_domain: str = "127.0.0.1",
        enabled: bool = True,
    ) -> Path:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config = config_dir / "sources.toml"
        config.write_text(
            f"""[settings]
data_root = "data"
storage_limit_bytes = {limit}
user_agent = "ManuelitaRAG-test/0.1 (offline fixtures)"
max_concurrency = 2
max_per_host = 1
default_delay_seconds = {delay}
max_depth = {max_depth}
request_timeout_seconds = 10
max_retries = {max_retries}
retry_backoff_seconds = 0.5
allowed_media_types = ["text/html", "application/pdf", "application/xml", "application/json",
  "text/plain", "text/vtt"]

[[sources]]
id = "fixture"
domain = "{campaign_domain}"
platform = "website"
authority = "first_party"
enabled = {str(enabled).lower()}
priority = 0
seeds = ["{base_url}/"]
sitemaps = ["{base_url}/sitemap.xml"]
follow_links = true
max_depth = {max_depth}
category_hints = ["identity", "offer", "digital_presence", "hard_data"]

[sources.policy]
robots = "respect"
requires_auth = false
excluded_paths = ["/admin"]

[sources.rate_limit]
delay_seconds = {delay}
max_concurrency = 1

[[sources]]
id = "blocked_platform"
domain = "linkedin.com"
platform = "website"
authority = "third_party"
enabled = false
priority = 3
seeds = ["https://www.linkedin.com/company/manuelita/"]
follow_links = false
max_depth = 0

[sources.policy]
robots = "respect"
requires_auth = true

[sources.rate_limit]
delay_seconds = 5.0
max_concurrency = 1
""",
            encoding="utf-8",
        )
        (config_dir / "exclusions.toml").write_text(
            '[exclusions]\nurls = []\ndomains = ["linkedin.com"]\n', encoding="utf-8"
        )
        return config

    return _write


@pytest.fixture()
def app_config(write_config, server) -> AppConfig:
    path = write_config(server)
    return load_config(path, project_root=path.parents[1])


def build_runner(
    config: AppConfig,
    *,
    stop_after: int | None = None,
    max_targets: int | None = None,
) -> tuple[CampaignRunner, Catalog, BronzeStorage]:
    catalog = Catalog(config.settings.bronze_dir / "_meta" / "bronze.sqlite3")
    catalog.init_schema()
    catalog.seed_sources(config.sources)
    catalog.seed_coverage(load_coverage_items(COVERAGE_PATH))
    storage = BronzeStorage(
        config.settings.bronze_dir, limit_bytes=config.settings.storage_limit_bytes
    )
    fetcher = build_http_fetcher(
        user_agent=config.settings.user_agent,
        timeout=config.settings.request_timeout_seconds,
    )
    runner = CampaignRunner(
        config,
        load_coverage_items(COVERAGE_PATH),
        catalog=catalog,
        storage=storage,
        fetcher=fetcher,
        allow_private=True,
        stop_after=stop_after,
        max_targets=max_targets,
    )
    return runner, catalog, storage
