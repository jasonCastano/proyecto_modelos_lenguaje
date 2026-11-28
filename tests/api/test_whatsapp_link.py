"""Contrato de ``GET /api/channels/whatsapp`` (spec 032, contracts/api-whatsapp.md).

Público, sin ``X-Channel-Token``; solo números ficticios armados en la prueba.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import proyecto_modelos_lenguaje.api as api

FAKE_DIGITS = "57" + "3" + "1" * 9
URL = "/api/channels/whatsapp"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path / "openclaw"))
    monkeypatch.delenv("VALERIA_WHATSAPP_NUMBER", raising=False)
    monkeypatch.delenv("VALERIA_CHANNEL_TOKEN", raising=False)
    return TestClient(api.app)


def _gateway(tmp_path: Path, policy: str) -> None:
    state = tmp_path / "openclaw"
    state.mkdir(parents=True, exist_ok=True)
    (state / ".env").write_text(f"WA_DM_POLICY={policy}\n", encoding="utf-8")


def test_available_without_channel_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VALERIA_WHATSAPP_NUMBER", "+" + FAKE_DIGITS)
    response = client.get(URL)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["available"] is True
    assert body["message"] == "Hola, Valer-IA"
    assert body["web_url"].startswith(f"https://web.whatsapp.com/send?phone={FAKE_DIGITS}&text=")
    assert body["app_url"].startswith(f"https://wa.me/{FAKE_DIGITS}?text=")
    assert body["qr_svg"].startswith("<svg")
    assert set(body) == {"available", "mode", "message", "web_url", "app_url", "qr_svg"}


@pytest.mark.parametrize("value", [None, "", "  ", FAKE_DIGITS, "+57abc"])
def test_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is not None:
        monkeypatch.setenv("VALERIA_WHATSAPP_NUMBER", value)
    response = client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["web_url"] is None and body["app_url"] is None and body["qr_svg"] is None


@pytest.mark.parametrize(("policy", "mode"), [("open", "open"), ("allowlist", "closed")])
def test_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, policy: str, mode: str
) -> None:
    monkeypatch.setenv("VALERIA_WHATSAPP_NUMBER", "+" + FAKE_DIGITS)
    _gateway(tmp_path, policy)
    assert client.get(URL).json()["mode"] == mode


def test_mode_unknown_without_gateway_env(client: TestClient) -> None:
    assert client.get(URL).json()["mode"] == "unknown"
