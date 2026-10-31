"""E2E: the RAG console answers with evidence or fallback."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)


def _enable_demo(page: Page) -> None:
    banner = page.get_by_test_id("demo-banner")
    if banner.count() and "Usar modo demostración" in banner.inner_text():
        page.get_by_role("button", name="Usar modo demostración").click()
        page.wait_for_timeout(300)


def test_ask_returns_citation_or_fallback(page: Page) -> None:
    _enable_demo(page)
    page.get_by_test_id("question-input").fill("¿Qué productos ofrece Manuelita?")
    page.get_by_test_id("ask-button").click()
    panel = page.get_by_test_id("answer-panel")
    panel.wait_for(timeout=120_000)
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[data-testid="answer-panel"]');
            if (!el) return false;
            const text = el.textContent || '';
            return !text.includes('Buscando evidencia') &&
                (text.includes('[U') || text.includes('No hay evidencia suficiente'));
        }""",
        timeout=120_000,
    )
    text = panel.inner_text()
    assert "[U" in text or "No hay evidencia suficiente" in text
    assert "Fuentes" in text or "No hay evidencia suficiente" in text


def test_switch_to_summary_and_faq(page: Page) -> None:
    _enable_demo(page)
    page.get_by_role("tab", name="Resumen").click()
    page.get_by_role("button", name="Generar resumen").click()
    page.get_by_test_id("answer-panel").wait_for(timeout=120_000)

    page.get_by_role("tab", name="FAQ").click()
    page.get_by_role("button", name="Generar FAQ").click()
    page.wait_for_selector(".faq-item", timeout=120_000)
    assert page.locator(".faq-item").count() >= 10
