"""E2E: las cuatro áreas de la plataforma sin desplazamiento horizontal (spec 026, T063)."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)

ROUTES = {
    "/": "Agentes de IA para consultar a Manuelita",
    "/agente": "Habla con Valer-IA",
    "/planificacion": "Planificación industrial",
    "/evidencia": "Evidencia técnica",
}


@pytest.mark.parametrize(("width", "height"), [(360, 640), (768, 1024), (1440, 900), (1920, 1080)])
@pytest.mark.parametrize("route", list(ROUTES))
def test_area_has_no_horizontal_scroll(
    browser: Browser, base_url: str, route: str, width: int, height: int
) -> None:
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    page.goto(f"{base_url}{route}", wait_until="networkidle")
    page.get_by_role("heading", level=1, name=ROUTES[route]).wait_for()
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )
    # Spec 027 (SC-004): ningún perfil aparece bloqueado en ningún ancho.
    text = page.inner_text("body").lower()
    assert "solo autorizados" not in text and "solo equipo de planta autorizado" not in text
    context.close()


def test_reduced_motion_disables_the_cane_flow_animation(browser: Browser, base_url: str) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    page.goto(f"{base_url}/planificacion", wait_until="networkidle")
    page.get_by_test_id("cane-flow").wait_for()
    assert page.locator(".cane-flow--animate").count() == 0
    assert page.evaluate("() => document.getAnimations().length") == 0
    context.close()
