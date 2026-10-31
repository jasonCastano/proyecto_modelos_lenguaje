"""Playwright fixtures for the web experience."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web" / "dist" / "index.html"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def base_url() -> Iterator[str]:
    if not DIST.is_file():
        pytest.skip("Build web first: cd web && npm run build")
    port = _free_port()
    env = {
        **os.environ,
        "DEEPSEEK_API_KEY": "",
        "PYTHONIOENCODING": "utf-8",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "proyecto_modelos_lenguaje.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            try:
                if httpx.get(f"{url}/api/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.25)
        else:
            pytest.skip("No se pudo iniciar la API para E2E")
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch(
                headless=True,
                channel=os.getenv("PML_E2E_BROWSER", "chrome"),
            )
        except Exception as exc:
            pytest.skip(f"Chrome no disponible para E2E: {exc}")
        yield instance
        instance.close()


@pytest.fixture
def page(browser: Browser, base_url: str) -> Iterator[Page]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    current = context.new_page()
    current.goto(base_url, wait_until="networkidle")
    yield current
    context.close()
