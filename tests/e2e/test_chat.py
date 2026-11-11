"""E2E de la conversación con memoria, enrutador y aprobación humana (spec 014, T069)."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser, Page

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)

TIMEOUT = 120_000


def _open_chat(page: Page) -> None:
    page.get_by_role("button", name="Usar modo demostración").click()
    page.get_by_role("tab", name="Conversación").click()
    page.get_by_test_id("chat-view").wait_for()


def _send(page: Page, message: str) -> None:
    page.get_by_test_id("chat-input").fill(message)
    page.get_by_test_id("chat-send").click()


def test_two_turn_conversation_shows_route_fragments_and_sources(page: Page) -> None:
    _open_chat(page)

    _send(page, "¿Qué produce Manuelita?")
    page.get_by_test_id("chat-turn").first.wait_for(timeout=TIMEOUT)
    _send(page, "¿Y dónde lo produce?")
    page.get_by_test_id("chat-turn").nth(1).wait_for(timeout=TIMEOUT)

    second = page.get_by_test_id("chat-turn").nth(1)
    assert "Documentos" in second.get_by_test_id("route-chip").inner_text()
    assert second.get_by_test_id("retrieved-fragments").is_visible()
    assert second.get_by_test_id("source-list").is_visible()


def test_write_actions_wait_for_approval_or_rejection(page: Page) -> None:
    _open_chat(page)

    _send(page, "Prefiero respuestas en viñetas")
    card = page.get_by_test_id("approval-card")
    card.wait_for(timeout=TIMEOUT)
    assert page.get_by_test_id("chat-send").is_disabled()
    card.get_by_role("button", name="Aprobar").click()
    page.get_by_text("Guardé tu preferencia").wait_for(timeout=TIMEOUT)
    page.get_by_test_id("preferences").wait_for()

    _send(page, "Exporta la conversación")
    page.get_by_test_id("approval-card").wait_for(timeout=TIMEOUT)
    page.get_by_role("button", name="Rechazar").click()
    page.get_by_text("fue rechazada en la revisión").wait_for(timeout=TIMEOUT)
    assert page.get_by_test_id("approval-card").count() == 0


def test_chat_fits_a_375px_screen(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 375, "height": 812})
    page = context.new_page()
    try:
        page.goto(base_url, wait_until="networkidle")
        _open_chat(page)
        _send(page, "¿Qué produce Manuelita?")
        page.get_by_test_id("chat-turn").first.wait_for(timeout=TIMEOUT)

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 0
    finally:
        context.close()
