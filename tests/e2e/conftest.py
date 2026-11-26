"""Playwright fixtures for the web experience."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

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
        "MANUELITA_STATE_DIR": tempfile.mkdtemp(prefix="manuelita-e2e-"),
        # Spec 023: dictado simulado (sin descargar el modelo) salvo que se pida el real.
        "MANUELITA_STT_ENGINE": os.environ.get("PML_E2E_STT_ENGINE", "fake"),
        "MANUELITA_STT_WARMUP": "0",
        # Spec 027: la web abre los cinco perfiles sin autorización; se prueba sin ninguna variable.
        "MANUELITA_PLANNER_WEB": "",
        "MANUELITA_PLANNER_OPEN": "",
        "VALERIA_PLANNERS": "",
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


PITCH_VIDEO = "**/media/pitch-valeria.mp4"


def _pitch_video_missing(route: Route) -> None:
    route.fulfill(status=404, body="")


def skip_pitch_video(context: BrowserContext) -> BrowserContext:
    """Sirve el video del pitch como ausente (spec 028).

    Con el .mp4 real (19 MB) en reproducción automática, la red nunca queda inactiva y
    ``wait_until="networkidle"`` agota el tiempo. Las pruebas del pitch lo controlan por su
    cuenta (``test_pitch.py``) y el archivo real se valida con ``pml pitch check``.
    """
    context.route(PITCH_VIDEO, _pitch_video_missing)
    return context


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
        new_context = instance.new_context
        instance.new_context = lambda *a, **kw: skip_pitch_video(new_context(*a, **kw))  # type: ignore[method-assign]
        yield instance
        instance.close()


@pytest.fixture
def page(browser: Browser, base_url: str) -> Iterator[Page]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    current = context.new_page()
    current.goto(base_url, wait_until="networkidle")
    yield current
    context.close()
