"""Versión servida y política de caché (make app muestra la versión actual)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from proyecto_modelos_lenguaje import api


def test_version_reports_commit_and_web_build() -> None:
    body = TestClient(api.app).get("/api/version").json()
    assert set(body) == {"commit", "web", "web_build"}
    assert body["commit"] == api.APP_COMMIT
    assert body["web"] in {"ok", "stale", "missing"}


def test_api_responses_keep_their_cache_headers() -> None:
    response = TestClient(api.app).get("/api/version")
    assert response.headers.get("cache-control") is None


def test_pages_are_never_cached() -> None:
    """index.html sin caché: el navegador pide siempre la versión actual."""
    response = TestClient(api.app).get("/agente")
    assert response.headers["cache-control"] == "no-cache"
