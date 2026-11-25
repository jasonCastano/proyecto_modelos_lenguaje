"""E2E: axe-core sin violaciones graves ni críticas en las cuatro áreas (spec 026, T064)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Browser

pytestmark = pytest.mark.skipif(
    os.getenv("PML_E2E") != "1",
    reason="Set PML_E2E=1 to run browser E2E.",
)

AXE = Path(__file__).resolve().parents[2] / "web" / "node_modules" / "axe-core" / "axe.min.js"


@pytest.mark.parametrize("route", ["/", "/agente", "/planificacion", "/evidencia"])
def test_no_serious_or_critical_violations(browser: Browser, base_url: str, route: str) -> None:
    if not AXE.is_file():
        pytest.skip("Instala las dependencias web: cd web && npm ci")
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"{base_url}{route}", wait_until="networkidle")
    page.get_by_role("heading", level=1).first.wait_for()
    page.wait_for_timeout(500)
    page.add_script_tag(path=str(AXE))
    violations = page.evaluate(
        """async () => {
            const result = await axe.run(document, { resultTypes: ['violations'] });
            return result.violations
              .filter(v => v.impact === 'serious' || v.impact === 'critical')
              .map(v => `${v.id}: ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`);
        }"""
    )
    context.close()
    assert violations == [], "\n".join(violations)
