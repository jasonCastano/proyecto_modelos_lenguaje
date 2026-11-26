"""E2E: el video pitch abre la entrada (spec 028, T028).

El `.mp4` real se produce fuera de línea con MAGI-2; aquí se prueba la entrada sin él: la
portada, la transcripción, saltar, la sesión y el movimiento reducido.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, Route, expect

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)

VIDEO = "**/media/pitch-valeria.mp4"
AXE = Path(__file__).resolve().parents[2] / "web" / "node_modules" / "axe-core" / "axe.min.js"


def _missing(route: Route) -> None:
    route.fulfill(status=404, body="")


def _open(browser: Browser, base_url: str, *, width: int = 1440, height: int = 900, **kw) -> Page:
    context = browser.new_context(viewport={"width": width, "height": height}, **kw)
    page = context.new_page()
    page.route(VIDEO, _missing)
    page.goto(base_url, wait_until="networkidle")
    page.get_by_test_id("pitch").wait_for()
    return page


def test_pitch_is_the_first_thing_on_the_entrance(browser: Browser, base_url: str) -> None:
    page = _open(browser, base_url)
    first = page.evaluate("() => document.querySelector('.home').firstElementChild.dataset.testid")
    assert first == "pitch"
    box = page.get_by_test_id("pitch").bounding_box()
    assert box is not None and box["y"] < 300
    expect(page.locator(".pitch__disclaimer")).to_contain_text("Video generado con IA")
    page.context.close()


def test_skip_reaches_the_entrance_in_one_step(browser: Browser, base_url: str) -> None:
    page = _open(browser, base_url)
    page.get_by_test_id("pitch-skip").click()
    expect(page.get_by_test_id("pitch")).to_have_attribute("data-state", "compact")
    expect(page.locator("#hero-title")).to_be_focused()
    page.reload(wait_until="networkidle")
    expect(page.get_by_test_id("pitch")).to_have_attribute("data-state", "compact")
    expect(page.get_by_role("button", name="Ver el video")).to_be_visible()
    page.context.close()


def test_reduced_motion_does_not_autoplay(browser: Browser, base_url: str) -> None:
    page = _open(browser, base_url, reduced_motion="reduce")
    assert page.evaluate("() => document.querySelector('.pitch__video').paused") is True
    expect(page.locator(".pitch__transcript")).to_have_attribute("open", "")
    page.context.close()


def test_missing_video_keeps_the_entrance_working(browser: Browser, base_url: str) -> None:
    page = _open(browser, base_url)
    expect(
        page.get_by_role("status").filter(has_text="El video no está disponible")
    ).to_be_visible()
    expect(page.locator(".pitch__transcript li")).to_have_count(6)
    expect(page.locator("#hero-title")).to_be_visible()
    expect(page.locator(".profile-ledger__row")).to_have_count(5)
    page.context.close()


@pytest.mark.parametrize(("width", "height"), [(360, 640), (768, 1024), (1440, 900), (1920, 1080)])
def test_pitch_has_no_horizontal_scroll(
    browser: Browser, base_url: str, width: int, height: int
) -> None:
    page = _open(browser, base_url, width=width, height=height)
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )
    page.context.close()


def test_pitch_has_no_serious_accessibility_violations(browser: Browser, base_url: str) -> None:
    if not AXE.is_file():
        pytest.skip("Instala las dependencias web: cd web && npm ci")
    page = _open(browser, base_url)
    page.add_script_tag(path=str(AXE))
    violations = page.evaluate(
        """async () => {
            const result = await axe.run('[data-testid=pitch]', { resultTypes: ['violations'] });
            return result.violations
              .filter(v => v.impact === 'serious' || v.impact === 'critical')
              .map(v => `${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`);
        }"""
    )
    page.context.close()
    assert violations == [], "\n".join(violations)
