"""E2E del dictado por voz con el micrófono simulado de Chrome (spec 023, T044).

Chrome usa un WAV generado como micrófono (`--use-file-for-fake-audio-capture`) y concede el permiso
solo. El servidor de las pruebas usa el motor de dictado `fake`, que transcribe cualquier voz como
«¿Qué produce Manuelita?». Requiere `PML_E2E=1` y `web/dist`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from playwright.sync_api import Browser, Page

from proyecto_modelos_lenguaje.stt.audio import encode_wav16k

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)

TIMEOUT = 30_000
HEARD = "¿Qué produce Manuelita?"


def _fake_microphone(path: Path) -> Path:
    """0,6 s de silencio, 1,2 s de «voz» (tono) y 2,4 s de silencio; Chrome lo repite en bucle."""
    rate = 16_000
    tone = 0.3 * np.sin(np.linspace(0, 2 * np.pi * 220 * 1.2, int(rate * 1.2)))
    audio = np.concatenate([np.zeros(int(rate * 0.6)), tone, np.zeros(int(rate * 2.4))])
    path.write_bytes(encode_wav16k(audio.astype(np.float32)))
    return path


@pytest.fixture
def mic_page(browser: Browser, base_url: str, tmp_path: Path) -> Iterator[Page]:
    wav = _fake_microphone(tmp_path / "microfono.wav")
    instance = browser.browser_type.launch(
        headless=True,
        channel=os.getenv("PML_E2E_BROWSER", "chrome"),
        args=[
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            f"--use-file-for-fake-audio-capture={wav}",
        ],
    )
    context = instance.new_context(viewport={"width": 1440, "height": 900})
    context.grant_permissions(["microphone"], origin=base_url)
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()
        instance.close()
        wav.unlink(missing_ok=True)


def _open_chat(page: Page, url: str) -> None:
    page.goto(url, wait_until="networkidle")
    demo = page.get_by_role("button", name="Usar modo demostración")
    if demo.count():
        demo.click()
    tab = page.get_by_role("tab", name="Conversación")
    if tab.count():
        tab.click()
    page.get_by_test_id("mic-privacy").wait_for(timeout=TIMEOUT)


def test_dictation_fills_the_field_and_cancel_leaves_it_empty(
    mic_page: Page, base_url: str
) -> None:
    _open_chat(mic_page, base_url)
    mic_page.get_by_test_id("mic-button").click()
    mic_page.wait_for_function(
        "() => document.querySelector('[data-testid=chat-input]').value.length > 0",
        timeout=TIMEOUT,
    )
    assert mic_page.get_by_test_id("chat-input").input_value() == HEARD
    assert mic_page.get_by_test_id("chat-turn").count() == 0  # no se envía solo

    mic_page.get_by_test_id("chat-input").fill("")
    mic_page.get_by_test_id("mic-button").click()
    mic_page.get_by_test_id("mic-cancel").click()
    mic_page.wait_for_timeout(4000)
    assert mic_page.get_by_test_id("chat-input").input_value() == ""


def test_technical_view_shows_the_voice_trace(mic_page: Page, base_url: str) -> None:
    _open_chat(mic_page, f"{base_url}/?vista=tecnica")
    mic_page.get_by_test_id("mic-button").click()
    mic_page.wait_for_function(
        "() => document.querySelector('[data-testid=chat-input]').value.length > 0",
        timeout=TIMEOUT,
    )
    mic_page.get_by_test_id("chat-send").click()
    mic_page.get_by_test_id("turn-input").first.wait_for(timeout=120_000)
    assert "🎙 por voz" in mic_page.get_by_test_id("turn-input").first.inner_text()


def test_mobile_layout_has_the_microphone_without_overflow(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 375, "height": 812})
    page = context.new_page()
    try:
        _open_chat(page, base_url)
        box = page.get_by_test_id("mic-button").bounding_box()
        assert box is not None and box["width"] >= 44 and box["height"] >= 44
        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 0
    finally:
        context.close()
