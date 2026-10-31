"""E2E: demo and missing-key states are explicit."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)


def test_missing_key_offers_demo_and_demo_is_labeled(page: Page) -> None:
    banner = page.get_by_test_id("demo-banner")
    banner.wait_for()
    assert "Falta la clave" in banner.inner_text()
    page.get_by_role("button", name="Usar modo demostración").click()
    banner = page.get_by_test_id("demo-banner")
    banner.wait_for()
    assert "Modo demostración" in banner.inner_text()
    page.get_by_test_id("question-input").fill("¿Dónde está la casa matriz?")
    page.get_by_test_id("ask-button").click()
    panel = page.get_by_test_id("answer-panel")
    panel.wait_for(timeout=120_000)
    assert "Modo demostración" in banner.inner_text()
