"""E2E: the Module 1 story is complete and traceable."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)


def test_module_story_has_eight_sections_and_evidence(page: Page) -> None:
    story = page.get_by_test_id("showcase-story")
    story.wait_for()
    assert story.locator("article").count() == 8
    assert "La información estaba dispersa" in story.inner_text()
    assert "Lo que todavía falta" in story.inner_text()
    assert page.locator('[data-testid="showcase-story"] a[href*="github"]').count() >= 4


def test_metrics_and_academic_footer(page: Page) -> None:
    band = page.get_by_test_id("metric-band")
    band.wait_for()
    assert "15.211" in band.inner_text()
    assert "No afiliado oficialmente" in page.locator("footer").inner_text()
