"""E2E: flujos de las historias 1 y 2 sin red ni claves (spec 026, T065)."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser, expect

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)

TIMEOUT = 60_000


def test_b2b_profile_from_the_entrance(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(base_url, wait_until="networkidle")
    example = "Compro azúcar para mi empresa, ¿qué certificaciones tienen?"
    page.get_by_role("button", name=example).click()
    expect(page).to_have_url(f"{base_url}/agente")
    expect(page.get_by_test_id("active-profile")).to_have_text("Perfil: Cliente B2B")
    expect(page.get_by_role("radio", name="Cliente B2B")).to_have_attribute("aria-checked", "true")
    field = page.get_by_test_id("chat-input")
    expect(field).to_have_value("Compro azúcar para mi empresa, ¿qué certificaciones tienen?")
    page.get_by_test_id("chat-send").click()
    turn = page.get_by_test_id("chat-turn").last
    turn.wait_for(timeout=TIMEOUT)
    context.close()


def test_planning_console_calculates_and_saves_with_confirmation(
    browser: Browser, base_url: str
) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{base_url}/planificacion", wait_until="networkidle")
    page.get_by_test_id("cane-flow").wait_for(timeout=TIMEOUT)
    page.get_by_role("spinbutton", name="Caña disponible").fill("-15")
    page.get_by_role("button", name="Calcular plan").click()
    expect(page.locator("[data-band]")).to_have_count(3, timeout=TIMEOUT)
    expect(page.get_by_role("heading", name="Libro de compromisos")).to_be_visible()

    page.get_by_role("button", name="Guardar propuesta").click()
    page.get_by_role("dialog").wait_for()
    page.get_by_role("button", name="No", exact=True).click()
    expect(page.get_by_text("Propuesta descartada")).to_be_visible()

    page.get_by_role("button", name="Guardar propuesta").click()
    page.get_by_role("button", name="Sí, guardar").click()
    expect(page.get_by_text("Propuesta guardada")).to_be_visible()
    context.close()


def test_planning_console_is_keyboard_operable(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{base_url}/planificacion", wait_until="networkidle")
    page.get_by_test_id("cane-flow").wait_for(timeout=TIMEOUT)
    page.get_by_role("spinbutton", name="Caña disponible").focus()
    for _ in range(10):
        width = page.evaluate(
            "() => parseFloat(getComputedStyle(document.activeElement).outlineWidth) || 0"
        )
        tag = page.evaluate("() => document.activeElement.tagName")
        assert tag != "BODY"
        assert width >= 2, tag
        page.keyboard.press("Tab")
    context.close()
