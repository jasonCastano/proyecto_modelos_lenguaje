"""E2E: pestaña WhatsApp (spec 032). El servidor de prueba usa un número ficticio (conftest)."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser, expect

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)


def test_nav_reaches_whatsapp_in_one_click(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(base_url, wait_until="networkidle")
    nav = page.get_by_role("navigation", name="Áreas de la plataforma")
    nav.get_by_role("link", name="WhatsApp").click()
    expect(page).to_have_url(f"{base_url}/whatsapp")
    title = page.get_by_role("heading", level=1, name="Habla con Valer-IA por WhatsApp")
    expect(title).to_be_visible()
    context.close()


def test_open_button_targets_a_new_tab_and_whatsapp_web(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{base_url}/whatsapp", wait_until="networkidle")
    button = page.get_by_test_id("wa-open")
    expect(button).to_be_visible()
    expect(button).to_have_attribute("target", "_blank")
    expect(button).to_have_attribute("rel", "noopener noreferrer")
    assert (button.get_attribute("href") or "").startswith("https://web.whatsapp.com/send?phone=")
    expect(page.get_by_test_id("wa-qr").locator("svg")).to_be_visible()
    notice = "Proyecto académico con IA. No es un canal oficial de Manuelita."
    expect(page.get_by_text(notice)).to_be_visible()
    context.close()


def test_phone_opens_the_app(browser: Browser, base_url: str) -> None:
    iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148"
    context = browser.new_context(viewport={"width": 390, "height": 844}, user_agent=iphone)
    page = context.new_page()
    page.goto(f"{base_url}/whatsapp", wait_until="networkidle")
    href = page.get_by_test_id("wa-open").get_attribute("href") or ""
    assert href.startswith("https://wa.me/")
    context.close()
