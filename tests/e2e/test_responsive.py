"""E2E: responsive matrix without horizontal overflow."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)


@pytest.mark.parametrize(
    ("width", "height"),
    [(360, 640), (390, 844), (768, 1024), (1024, 768), (1440, 900), (1920, 1080)],
)
def test_viewport_has_no_horizontal_scroll(
    browser: Browser, base_url: str, width: int, height: int
) -> None:
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    page.goto(base_url, wait_until="networkidle")
    page.get_by_test_id("hero").wait_for()
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )
    assert page.get_by_test_id("rag-console").is_visible()
    context.close()


def test_reduced_motion_is_respected(browser: Browser, base_url: str) -> None:
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.goto(base_url, wait_until="networkidle")
    duration = page.evaluate(
        """() => {
            const value = getComputedStyle(document.querySelector('.hero-copy')).animationDuration;
            return value.endsWith('ms') ? parseFloat(value) : parseFloat(value) * 1000;
        }"""
    )
    assert duration <= 0.1
    context.close()
